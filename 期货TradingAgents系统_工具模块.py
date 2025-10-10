#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 工具模块
提供各种辅助功能和实用工具

功能包括：
1. DeepSeek API调用封装
2. 数据验证和清洗
3. 文件操作工具
4. 时间处理工具
5. 数据格式转换
6. 缓存管理
7. 错误处理装饰器

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import aiohttp
import hashlib
import pickle
import time
import functools
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import asdict

# ============================================================================
# 1. DeepSeek API调用封装
# ============================================================================

class DeepSeekAPIClient:
    """DeepSeek API客户端封装"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
        self.logger = logging.getLogger("DeepSeekAPI")
        
    async def __aenter__(self):
        # 增加连接超时和DNS解析超时设置
        timeout = aiohttp.ClientTimeout(
            total=600,  # 总超时10分钟（增加）
            connect=30,  # 连接超时30秒
            sock_read=180,  # 读取超时180秒（增加到3分钟，适应复杂分析）
            sock_connect=30  # socket连接超时30秒
        )
        
        # 创建连接器，增加DNS缓存和连接池设置
        connector = aiohttp.TCPConnector(
            limit=100,  # 连接池大小
            limit_per_host=30,  # 每个主机的连接数
            ttl_dns_cache=300,  # DNS缓存5分钟
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout,
            connector=connector
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def ensure_session(self):
        """确保session已初始化"""
        if self.session is None or self.session.closed:
            # 使用与__aenter__相同的超时和连接器配置
            timeout = aiohttp.ClientTimeout(
                total=600,  # 总超时10分钟（增加）
                connect=30,  # 连接超时30秒
                sock_read=180,  # 读取超时180秒（增加到3分钟，适应复杂分析）
                sock_connect=30  # socket连接超时30秒
            )
            
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=timeout,
                connector=connector
            )

    async def close_session(self):
        """关闭session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        try:
            await self.close_session()
        except Exception as e:
            # 忽略事件循环关闭时的清理错误
            if "Event loop is closed" not in str(e):
                self.logger.warning(f"关闭session时出现异常: {e}")

    async def chat_completion(self, messages: List[Dict], model: str = "deepseek-chat",
                            temperature: float = 0.1, max_tokens: int = 4000, max_retries: int = 5) -> Dict:
        """聊天补全API调用（带重试机制）"""

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        # 重试机制
        for attempt in range(max_retries):
            try:
                # 确保session已初始化
                await self.ensure_session()

                # 直接使用session，不使用async with
                response = await self.session.post(url, json=payload)

                try:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "content": result["choices"][0]["message"]["content"],
                            "usage": result.get("usage", {}),
                            "model": model
                        }
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"API调用失败 (尝试 {attempt+1}/{max_retries}): {response.status} - {error_text}")

                        # 如果是最后一次尝试，返回错误
                        if attempt == max_retries - 1:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}: {error_text}",
                                "model": model
                            }

                finally:
                    response.close()  # 确保响应被正确关闭

                # 等待后重试，使用指数退避
                delay = min(2 ** attempt, 30)  # 最大延迟30秒
                await asyncio.sleep(delay)

            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"API调用异常 (尝试 {attempt+1}/{max_retries}): {error_msg}")
                
                # 对于DNS或连接问题，给出更详细的错误信息
                if "DNS" in error_msg or "Timeout" in error_msg or "Cannot connect" in error_msg:
                    self.logger.warning(f"网络连接问题，将在 {min(2 ** attempt, 30)} 秒后重试...")

                # 如果是最后一次尝试，返回错误
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"API调用失败 (重试{max_retries}次后): {error_msg}",
                        "model": model
                    }

                # 等待后重试，使用指数退避
                delay = min(2 ** attempt, 30)  # 最大延迟30秒
                await asyncio.sleep(delay)
    
    async def reasoning_completion(self, prompt: str, model: str = "deepseek-reasoner",
                                 temperature: float = 0.1, max_tokens: int = 4000) -> Dict:
        """推理模式API调用"""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        return await self.chat_completion(messages, model, temperature, max_tokens)
    
    async def analyze_with_context(self, system_prompt: str, user_prompt: str,
                                 context_data: Dict = None, model: str = "deepseek-chat") -> Dict:
        """带上下文的分析调用"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加上下文数据
        if context_data:
            context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
            user_prompt = f"{user_prompt}\n\n## 上下文数据\n```json\n{context_str}\n```"
        
        messages.append({"role": "user", "content": user_prompt})
        
        return await self.chat_completion(messages, model)

# ============================================================================
# 2. 数据验证和清洗工具
# ============================================================================

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_commodity_code(commodity: str) -> bool:
        """验证商品代码格式"""
        if not isinstance(commodity, str):
            return False
        
        # 期货商品代码通常是2-3个大写字母
        return len(commodity) in [2, 3] and commodity.isupper() and commodity.isalpha()
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """验证日期格式 YYYY-MM-DD"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_analysis_result(result: Dict) -> Dict:
        """验证分析结果格式"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 检查必需字段
        required_fields = ["commodity", "analysis_date", "analysis_type"]
        for field in required_fields:
            if field not in result:
                validation_result["errors"].append(f"缺少必需字段: {field}")
                validation_result["is_valid"] = False
        
        # 检查信心分数
        if "confidence_score" in result:
            confidence = result["confidence_score"]
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                validation_result["errors"].append("confidence_score必须是0-1之间的数值")
                validation_result["is_valid"] = False
        
        # 检查时间戳
        if "timestamp" in result:
            if not DataValidator.validate_date_format(result["timestamp"][:10]):
                validation_result["warnings"].append("时间戳格式可能不正确")
        
        return validation_result
    
    @staticmethod
    def clean_numeric_data(data: Any) -> Optional[float]:
        """清洗数值数据"""
        if data is None or data == "":
            return None
        
        if isinstance(data, (int, float)):
            return float(data)
        
        if isinstance(data, str):
            # 移除常见的非数字字符
            cleaned = data.replace(",", "").replace("%", "").replace("元", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def normalize_commodity_name(name: str) -> str:
        """标准化商品名称"""
        name_mapping = {
            "螺纹钢": "RB", "热轧卷板": "HC", "铁矿石": "I", "焦炭": "J", "焦煤": "JM",
            "沪铜": "CU", "沪铝": "AL", "沪锌": "ZN", "沪镍": "NI", "沪锡": "SN",
            "黄金": "AU", "白银": "AG", "橡胶": "RU", "原油": "SC", "燃油": "FU",
            "白糖": "SR", "棉花": "CF", "豆粕": "M", "菜粕": "RM", "豆油": "Y"
        }
        
        return name_mapping.get(name, name.upper())

# ============================================================================
# 3. 文件操作工具
# ============================================================================

class FileManager:
    """文件管理器"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger("FileManager")
        
    def ensure_dir(self, path: Union[str, Path]) -> Path:
        """确保目录存在"""
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def save_json(self, data: Any, file_path: Union[str, Path], 
                  ensure_dir: bool = True) -> bool:
        """保存JSON数据"""
        try:
            file_path = Path(file_path)
            
            if ensure_dir:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def load_json(self, file_path: Union[str, Path]) -> Optional[Dict]:
        """加载JSON数据"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"加载JSON文件失败: {e}")
            return None
    
    def save_dataframe(self, df: pd.DataFrame, file_path: Union[str, Path],
                      format: str = "csv") -> bool:
        """保存DataFrame"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "csv":
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif format.lower() == "excel":
                df.to_excel(file_path, index=False)
            elif format.lower() == "parquet":
                df.to_parquet(file_path, index=False)
            else:
                raise ValueError(f"不支持的格式: {format}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存DataFrame失败: {e}")
            return False
    
    def load_dataframe(self, file_path: Union[str, Path]) -> Optional[pd.DataFrame]:
        """加载DataFrame"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return None
            
            suffix = file_path.suffix.lower()
            
            if suffix == ".csv":
                return pd.read_csv(file_path, encoding='utf-8-sig')
            elif suffix in [".xlsx", ".xls"]:
                return pd.read_excel(file_path)
            elif suffix == ".parquet":
                return pd.read_parquet(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {suffix}")
                
        except Exception as e:
            self.logger.error(f"加载DataFrame失败: {e}")
            return None
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict:
        """获取文件信息"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"exists": False}
        
        stat = file_path.stat()
        
        return {
            "exists": True,
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "created_time": datetime.fromtimestamp(stat.st_ctime),
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
            "extension": file_path.suffix
        }

# ============================================================================
# 4. 缓存管理
# ============================================================================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str, expire_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.expire_hours = expire_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("CacheManager")
    
    def _get_cache_key(self, key: str) -> str:
        """生成缓存键的哈希值"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        cache_key = self._get_cache_key(key)
        return self.cache_dir / f"{cache_key}.cache"
    
    def set(self, key: str, data: Any, expire_hours: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            cache_path = self._get_cache_path(key)
            expire_time = datetime.now() + timedelta(hours=expire_hours or self.expire_hours)
            
            cache_data = {
                "data": data,
                "expire_time": expire_time,
                "created_time": datetime.now(),
                "key": key
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查是否过期
            if datetime.now() > cache_data["expire_time"]:
                cache_path.unlink()  # 删除过期缓存
                return None
            
            return cache_data["data"]
            
        except Exception as e:
            self.logger.error(f"获取缓存失败: {e}")
            return None
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在且未过期"""
        return self.get(key) is not None
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            return True
        except Exception as e:
            self.logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        cleared_count = 0
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                
                if datetime.now() > cache_data["expire_time"]:
                    cache_file.unlink()
                    cleared_count += 1
                    
            except Exception as e:
                # 无法读取的缓存文件也删除
                cache_file.unlink()
                cleared_count += 1
        
        self.logger.info(f"清理了 {cleared_count} 个过期缓存文件")
        return cleared_count

# ============================================================================
# 5. 错误处理装饰器
# ============================================================================

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, 
                    backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logging.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}，{wait_time:.1f}秒后重试")
                        await asyncio.sleep(wait_time)
                    else:
                        logging.error(f"函数 {func.__name__} 在 {max_retries + 1} 次尝试后仍然失败")
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logging.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}，{wait_time:.1f}秒后重试")
                        time.sleep(wait_time)
                    else:
                        logging.error(f"函数 {func.__name__} 在 {max_retries + 1} 次尝试后仍然失败")
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def log_execution_time(logger: Optional[logging.Logger] = None):
    """执行时间记录装饰器"""
    def decorator(func: Callable) -> Callable:
        log = logger or logging.getLogger(func.__module__)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                log.info(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.2f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                log.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                log.info(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.2f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                log.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# ============================================================================
# 6. 时间处理工具
# ============================================================================

class TimeUtils:
    """时间处理工具类"""
    
    @staticmethod
    def get_trading_days(start_date: str, end_date: str, 
                        exclude_weekends: bool = True) -> List[str]:
        """获取交易日列表"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        trading_days = []
        current = start
        
        while current <= end:
            if not exclude_weekends or current.weekday() < 5:  # 周一到周五
                trading_days.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return trading_days
    
    @staticmethod
    def get_recent_trading_day(offset_days: int = 0) -> str:
        """获取最近的交易日"""
        current = datetime.now() - timedelta(days=offset_days)
        
        # 如果是周末，回退到周五
        while current.weekday() >= 5:
            current -= timedelta(days=1)
        
        return current.strftime("%Y-%m-%d")
    
    @staticmethod
    def format_timestamp(timestamp: Optional[datetime] = None, 
                        format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间戳"""
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime(format_str)
    
    @staticmethod
    def parse_date_string(date_str: str, formats: List[str] = None) -> Optional[datetime]:
        """解析日期字符串"""
        if formats is None:
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d", 
                "%Y.%m.%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S"
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

# ============================================================================
# 7. 数据格式转换工具
# ============================================================================

class DataConverter:
    """数据格式转换工具"""
    
    @staticmethod
    def dict_to_dataframe(data_dict: Dict, orient: str = "records") -> pd.DataFrame:
        """字典转DataFrame"""
        try:
            if orient == "records":
                return pd.DataFrame(data_dict)
            elif orient == "index":
                return pd.DataFrame.from_dict(data_dict, orient="index")
            elif orient == "columns":
                return pd.DataFrame.from_dict(data_dict, orient="columns")
            else:
                raise ValueError(f"不支持的orient参数: {orient}")
        except Exception as e:
            logging.error(f"字典转DataFrame失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def dataframe_to_dict(df: pd.DataFrame, orient: str = "records") -> Dict:
        """DataFrame转字典"""
        try:
            return df.to_dict(orient=orient)
        except Exception as e:
            logging.error(f"DataFrame转字典失败: {e}")
            return {}
    
    @staticmethod
    def flatten_dict(nested_dict: Dict, separator: str = ".") -> Dict:
        """扁平化嵌套字典"""
        def _flatten(obj, parent_key=""):
            items = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value, new_key).items())
            else:
                return {parent_key: obj}
            return dict(items)
        
        return _flatten(nested_dict)
    
    @staticmethod
    def unflatten_dict(flat_dict: Dict, separator: str = ".") -> Dict:
        """反扁平化字典"""
        nested_dict = {}
        
        for key, value in flat_dict.items():
            keys = key.split(separator)
            current = nested_dict
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            current[keys[-1]] = value
        
        return nested_dict

# ============================================================================
# 8. 测试工具模块功能
# ============================================================================

async def test_tools():
    """测试工具模块功能"""
    
    print("🔧 测试期货Trading Agents工具模块...")
    
    # 1. 测试数据验证器
    print("\n1. 测试数据验证器...")
    validator = DataValidator()
    
    print(f"   商品代码验证 'RB': {validator.validate_commodity_code('RB')}")
    print(f"   商品代码验证 'invalid': {validator.validate_commodity_code('invalid')}")
    print(f"   日期格式验证 '2025-01-19': {validator.validate_date_format('2025-01-19')}")
    
    # 2. 测试文件管理器
    print("\n2. 测试文件管理器...")
    file_manager = FileManager("./test_data")
    
    test_data = {"test": "data", "timestamp": datetime.now()}
    success = file_manager.save_json(test_data, "./test_data/test.json")
    print(f"   JSON保存: {success}")
    
    loaded_data = file_manager.load_json("./test_data/test.json")
    print(f"   JSON加载: {loaded_data is not None}")
    
    # 3. 测试缓存管理器
    print("\n3. 测试缓存管理器...")
    cache = CacheManager("./test_cache")
    
    cache.set("test_key", {"cached": "data"}, expire_hours=1)
    cached_data = cache.get("test_key")
    print(f"   缓存设置和获取: {cached_data is not None}")
    
    # 4. 测试时间工具
    print("\n4. 测试时间工具...")
    time_utils = TimeUtils()
    
    recent_day = time_utils.get_recent_trading_day()
    trading_days = time_utils.get_trading_days("2025-01-15", "2025-01-19")
    print(f"   最近交易日: {recent_day}")
    print(f"   交易日列表: {trading_days}")
    
    # 5. 测试数据转换器
    print("\n5. 测试数据转换器...")
    converter = DataConverter()
    
    test_dict = {"a": {"b": {"c": 1}}, "d": 2}
    flat_dict = converter.flatten_dict(test_dict)
    unflat_dict = converter.unflatten_dict(flat_dict)
    print(f"   字典扁平化: {flat_dict}")
    print(f"   字典反扁平化: {unflat_dict}")
    
    print("\n✅ 工具模块测试完成！")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_tools())
