#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 工具函数模块
作者：7haoge
邮箱：953534947@qq.com
"""

import os
import requests
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import LOG_CONFIG, NETWORK_CONFIG, DATA_CONFIG

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG['level']),
    format=LOG_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOG_CONFIG['file'], encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, LOG_CONFIG['level']),
        format=LOG_CONFIG['format'],
        handlers=[
            logging.FileHandler(LOG_CONFIG['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_directory(directory: str) -> bool:
    """确保目录存在"""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
        return True
    except Exception as e:
        logging.error(f"创建目录失败 {directory}: {str(e)}")
        return False

def test_network_connectivity() -> Dict[str, Any]:
    """
    测试网络连接状态
    :return: 测试结果字典
    """
    results = {
        'success': True,
        'total_tests': len(NETWORK_CONFIG['test_urls']),
        'passed_tests': 0,
        'details': []
    }
    
    for url in NETWORK_CONFIG['test_urls']:
        try:
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=10,
                headers=NETWORK_CONFIG['headers']
            )
            end_time = time.time()
            
            if response.status_code == 200:
                results['passed_tests'] += 1
                results['details'].append({
                    'url': url,
                    'success': True,
                    'response_time': end_time - start_time,
                    'error': None
                })
            else:
                results['details'].append({
                    'url': url,
                    'success': False,
                    'response_time': end_time - start_time,
                    'error': f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            results['details'].append({
                'url': url,
                'success': False,
                'response_time': 0,
                'error': str(e)
            })
    
    results['success'] = results['passed_tests'] > 0
    return results

def validate_date_format(date_str: str) -> bool:
    """
    验证日期格式是否为YYYYMMDD
    :param date_str: 日期字符串
    :return: 是否有效
    """
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def get_trading_dates(start_date: str, end_date: str) -> List[str]:
    """获取交易日期列表（排除周末）"""
    try:
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        trading_dates = []
        current = start
        
        while current <= end:
            # 排除周末（周六=5，周日=6）
            if current.weekday() < 5:
                trading_dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        
        return trading_dates
    except Exception as e:
        logging.error(f"获取交易日期失败: {str(e)}")
        return []

def get_recent_trading_date(days_back: int = 1) -> str:
    """
    获取最近的交易日期（简单实现，不考虑节假日）
    :param days_back: 往前推几天
    :return: 日期字符串 YYYYMMDD
    """
    date = datetime.now() - timedelta(days=days_back)
    # 简单处理：如果是周末，继续往前推
    while date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        date -= timedelta(days=1)
    return date.strftime('%Y%m%d')

def clean_numeric_data(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """清理数值型数据"""
    df_cleaned = df.copy()
    
    for col in columns:
        if col in df_cleaned.columns:
            # 移除逗号和空格，转换为数值
            df_cleaned[col] = pd.to_numeric(
                df_cleaned[col].astype(str).str.replace(',', '').str.replace(' ', ''),
                errors='coerce'
            )
            # 填充NaN为0
            df_cleaned[col] = df_cleaned[col].fillna(0)
    
    return df_cleaned

def extract_symbol_from_contract(contract: str) -> str:
    """从合约名称中提取品种代码"""
    try:
        # 处理不同格式的合约名称
        if '_' in contract:
            symbol_part = contract.split('_')[-1]
        else:
            symbol_part = contract
        
        # 提取字母部分作为品种代码
        symbol = ''.join(c for c in symbol_part if c.isalpha()).upper()
        return symbol if symbol else contract
    except Exception:
        return contract

def format_number(number: float, precision: int = 2) -> str:
    """格式化数字显示"""
    try:
        if abs(number) >= 1e8:
            return f"{number/1e8:.{precision}f}亿"
        elif abs(number) >= 1e4:
            return f"{number/1e4:.{precision}f}万"
        else:
            return f"{number:.{precision}f}"
    except Exception:
        return str(number)

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    计算百分比变化
    :param old_value: 原值
    :param new_value: 新值
    :return: 百分比变化
    """
    try:
        if old_value == 0:
            return 0.0
        return ((new_value - old_value) / old_value) * 100
    except:
        return 0.0

def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """安全除法"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except Exception:
        return default

def filter_top_n(data: List[Dict], key: str, n: int = 10, reverse: bool = True) -> List[Dict]:
    """筛选前N名数据"""
    try:
        return sorted(data, key=lambda x: x.get(key, 0), reverse=reverse)[:n]
    except Exception:
        return data[:n] if len(data) > n else data

def merge_dataframes(dfs: List[pd.DataFrame], on: str = None) -> pd.DataFrame:
    """合并多个DataFrame"""
    try:
        if not dfs:
            return pd.DataFrame()
        
        if len(dfs) == 1:
            return dfs[0]
        
        if on:
            result = dfs[0]
            for df in dfs[1:]:
                result = pd.merge(result, df, on=on, how='outer')
            return result
        else:
            return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        logging.error(f"合并DataFrame失败: {str(e)}")
        return pd.DataFrame()

def export_to_excel(data: Dict[str, pd.DataFrame], filename: str) -> bool:
    """导出数据到Excel"""
    try:
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            for sheet_name, df in data.items():
                # 清理sheet名称
                clean_name = sheet_name[:31].replace("/", "-").replace("*", "")
                df.to_excel(writer, sheet_name=clean_name, index=False)
        return True
    except Exception as e:
        logging.error(f"导出Excel失败: {str(e)}")
        return False

def load_from_excel(filename: str) -> Dict[str, pd.DataFrame]:
    """从Excel加载数据"""
    try:
        return pd.read_excel(filename, sheet_name=None)
    except Exception as e:
        logging.error(f"加载Excel失败: {str(e)}")
        return {}

def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logging.warning(f"第{attempt + 1}次尝试失败，{delay}秒后重试: {str(e)}")
                    import time
                    time.sleep(delay)
                else:
                    logging.error(f"所有重试都失败了: {str(e)}")
        
        raise last_exception
    
    return wrapper

def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """验证DataFrame是否包含必需的列"""
    try:
        if df.empty:
            return False
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logging.warning(f"缺少必需的列: {missing_columns}")
            return False
        
        return True
    except Exception:
        return False

def get_file_size(filepath: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(filepath)
    except Exception:
        return 0

def clean_old_files(directory: str, days: int = 7) -> int:
    """清理旧文件"""
    try:
        if not os.path.exists(directory):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_time:
                    try:
                        os.remove(filepath)
                        cleaned_count += 1
                        logging.info(f"删除旧文件: {filepath}")
                    except Exception as e:
                        logging.error(f"删除文件失败 {filepath}: {str(e)}")
        
        return cleaned_count
    except Exception as e:
        logging.error(f"清理旧文件失败: {str(e)}")
        return 0

def extract_variety_from_contract(contract: str) -> str:
    """
    从合约名称中提取品种代码
    :param contract: 合约名称
    :return: 品种代码
    """
    try:
        # 处理各种格式的合约名称
        if '_' in contract:
            # 处理格式：交易所_合约代码
            symbol_part = contract.split('_')[-1]
        else:
            symbol_part = contract
        
        # 提取字母部分作为品种代码
        symbol = ''.join(c for c in symbol_part if c.isalpha()).upper()
        
        # 处理特殊情况
        if symbol == 'PTA':
            return 'PTA'
        elif symbol.startswith('TA') and len(symbol) > 2:
            return 'TA'
        elif symbol == 'OI':
            return 'OI'
        elif symbol.lower() in ['cu', 'al', 'zn', 'pb', 'ni', 'sn', 'au', 'ag', 'rb', 'wr', 'hc', 'ss', 'fu', 'bu', 'ru', 'nr', 'sp', 'lu', 'bc', 'ao', 'ec']:
            # 上期所品种保持小写转大写
            return symbol.upper()
        elif symbol.lower() in ['si', 'ps']:
            # 广期所品种
            return symbol.upper()
        else:
            return symbol
    except:
        return contract

def clean_numeric_string(value: str) -> float:
    """
    清理数字字符串，去除逗号等格式字符
    :param value: 字符串值
    :return: 数字值
    """
    try:
        if isinstance(value, (int, float)):
            return float(value)
        
        # 去除逗号、空格等
        cleaned = str(value).replace(',', '').replace(' ', '').strip()
        
        # 处理空值
        if cleaned in ['', 'nan', 'NaN', 'None', 'null']:
            return 0.0
        
        return float(cleaned)
    except:
        return 0.0

def validate_retail_seats(seats: List[str]) -> bool:
    """
    验证家人席位配置是否有效
    :param seats: 席位列表
    :return: 是否有效
    """
    if not isinstance(seats, list):
        return False
    
    if len(seats) == 0:
        return False
    
    # 检查是否有重复
    if len(seats) != len(set(seats)):
        return False
    
    # 检查每个席位名称是否有效
    for seat in seats:
        if not isinstance(seat, str) or len(seat.strip()) == 0:
            return False
    
    return True

def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    :return: 系统信息字典
    """
    import platform
    import sys
    
    return {
        'platform': platform.platform(),
        'python_version': sys.version,
        'architecture': platform.architecture(),
        'processor': platform.processor(),
        'memory_info': get_memory_info()
    }

def get_memory_info() -> Dict[str, Any]:
    """
    获取内存信息
    :return: 内存信息字典
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'used': memory.used,
            'free': memory.free
        }
    except ImportError:
        return {'error': 'psutil not installed'}
    except Exception as e:
        return {'error': str(e)}

def log_analysis_start(trade_date: str, retail_seats: List[str]):
    """
    记录分析开始
    :param trade_date: 交易日期
    :param retail_seats: 家人席位配置
    """
    logger.info(f"开始分析 - 日期: {trade_date}, 家人席位: {', '.join(retail_seats)}")

def log_analysis_end(trade_date: str, success: bool, duration: float, contracts_count: int = 0):
    """
    记录分析结束
    :param trade_date: 交易日期
    :param success: 是否成功
    :param duration: 耗时（秒）
    :param contracts_count: 合约数量
    """
    status = "成功" if success else "失败"
    logger.info(f"分析结束 - 日期: {trade_date}, 状态: {status}, 耗时: {duration:.2f}秒, 合约数: {contracts_count}")

def create_backup_filename(base_filename: str) -> str:
    """
    创建备份文件名
    :param base_filename: 基础文件名
    :return: 备份文件名
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(base_filename)
    return f"{name}_backup_{timestamp}{ext}"

# 导出主要函数
__all__ = [
    'test_network_connectivity',
    'ensure_directory',
    'validate_date_format',
    'get_recent_trading_date',
    'format_number',
    'calculate_percentage_change',
    'extract_variety_from_contract',
    'safe_divide',
    'clean_numeric_string',
    'validate_retail_seats',
    'get_system_info',
    'get_memory_info',
    'log_analysis_start',
    'log_analysis_end',
    'create_backup_filename',
    'logger'
]

# 初始化日志
logger = setup_logging() 