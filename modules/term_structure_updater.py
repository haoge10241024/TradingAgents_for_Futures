#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期限结构数据更新器
基于期限结构数据更新程序，支持多交易所数据获取和增量更新
"""

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import random
import json
import warnings
import re
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings('ignore')

class TermStructureUpdater:
    """期限结构数据更新器"""
    
    def __init__(self, database_path: str = "qihuo/database/term_structure"):
        """
        初始化期限结构数据更新器
        
        Args:
            database_path: 数据库路径
        """
        self.base_dir = Path(database_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 交易所配置
        self.exchanges = [
            {"market": "DCE", "name": "大商所"},
            {"market": "CZCE", "name": "郑商所"},
            {"market": "SHFE", "name": "上期所"},
            {"market": "INE", "name": "上海国际能源交易中心"},
            {"market": "GFEX", "name": "广期所"}
        ]
        
        self.update_stats = {
            "start_time": None,
            "end_time": None,
            "target_date": None,
            "update_days": 0,
            "updated_varieties": [],
            "failed_varieties": [],
            "skipped_varieties": [],
            "new_varieties": [],
            "total_new_records": 0,
            "exchange_stats": {},
            "error_messages": []
        }
    
    def get_existing_data_status(self) -> Tuple[List[str], Dict]:
        """
        获取现有数据状态
        
        Returns:
            varieties: 现有品种列表
            variety_info: 各品种详细信息
        """
        print("🔍 检查现有期限结构数据状态...")
        
        varieties = []
        variety_info = {}
        
        if not self.base_dir.exists():
            return [], {}
        
        variety_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            ts_file = folder / "term_structure.csv"
            
            if ts_file.exists():
                try:
                    df = pd.read_csv(ts_file)
                    if len(df) > 0 and 'date' in df.columns:
                        # 处理日期列（可能是多种格式）
                        try:
                            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                        except:
                            df['date'] = pd.to_datetime(df['date'])
                        
                        variety_latest = df['date'].max()
                        variety_earliest = df['date'].min()
                        record_count = len(df)
                        
                        variety_info[variety] = {
                            "earliest_date": variety_earliest,
                            "latest_date": variety_latest,
                            "record_count": record_count,
                            "file_path": ts_file
                        }
                        
                        varieties.append(variety)
                        print(f"  {variety}: {record_count} 条记录 ({variety_earliest.strftime('%Y-%m-%d')} ~ {variety_latest.strftime('%Y-%m-%d')})")
                        
                except Exception as e:
                    print(f"  ❌ {variety}: 读取失败 - {str(e)[:50]}")
                    self.update_stats["error_messages"].append(f"{variety}: 数据读取失败 - {str(e)}")
        
        print(f"\n📊 总计: {len(varieties)} 个有效品种")
        return varieties, variety_info
    
    def calculate_roll_yield(self, current_contract: str, next_contract: str, current_price: float, next_price: float) -> float:
        """
        计算展期收益率
        
        Args:
            current_contract: 当前合约
            next_contract: 下一个合约
            current_price: 当前合约价格
            next_price: 下一个合约价格
        
        Returns:
            展期收益率
        """
        try:
            if current_price <= 0 or next_price <= 0:
                return 0.0
            
            # 提取合约月份
            current_month = int(current_contract[-4:])
            next_month = int(next_contract[-4:])
            
            # 计算月份差
            if next_month > current_month:
                month_diff = next_month - current_month
            else:
                # 跨年情况
                month_diff = (next_month + 1200) - current_month
            
            if month_diff == 0:
                return 0.0
            
            # 计算年化收益率
            roll_yield = ((next_price / current_price - 1) / month_diff) * 12
            return roll_yield
            
        except:
            return 0.0
    
    def fetch_exchange_data(self, exchange: Dict, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取交易所数据
        
        Args:
            exchange: 交易所配置
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            数据DataFrame或None
        """
        print(f"  📡 获取 {exchange['name']} 数据 ({start_date} ~ {end_date})...")
        
        try:
            if exchange['market'] == 'DCE':
                # 大商所需要按品种获取（futures_main_sina支持日期参数）
                dce_varieties = ['A', 'B', 'C', 'CS', 'I', 'J', 'JD', 'JM', 'L', 'LH', 'M', 'P', 'PG', 'PP', 'V', 'Y', 'EB', 'EG', 'RR']
                all_dce_data = []
                
                for variety in dce_varieties:
                    try:
                        variety_df = ak.futures_main_sina(
                            symbol=f"{variety}0",  # 主力合约，如A0
                            start_date=start_date,
                            end_date=end_date
                        )
                        if variety_df is not None and not variety_df.empty:
                            # 添加品种代码列（如果没有的话）
                            if 'symbol' not in variety_df.columns:
                                variety_df['symbol'] = f"{variety}0"
                            all_dce_data.append(variety_df)
                    except Exception as e:
                        # 单个品种失败不影响其他品种
                        pass
                
                if all_dce_data:
                    df = pd.concat(all_dce_data, ignore_index=True)
                else:
                    print(f"    ❌ {exchange['name']}: 所有品种均获取失败")
                    return None
            else:
                # 其他交易所使用通用接口
                df = ak.get_futures_daily(start_date=start_date, end_date=end_date, market=exchange['market'])
            
            if df is None or df.empty:
                print(f"    ❌ {exchange['name']}: 无数据返回")
                return None
            
            print(f"    ✅ {exchange['name']}: 获取到 {len(df)} 条原始记录")
            return df
            
        except Exception as e:
            print(f"    ❌ {exchange['name']}: 获取失败 - {str(e)[:100]}")
            self.update_stats["error_messages"].append(f"{exchange['name']}: 数据获取失败 - {str(e)}")
            return None
    
    def process_exchange_data(self, df: pd.DataFrame, exchange: Dict) -> Dict[str, pd.DataFrame]:
        """
        处理交易所数据，按品种分组
        
        Args:
            df: 原始数据
            exchange: 交易所配置
        
        Returns:
            按品种分组的数据字典
        """
        variety_data = {}
        
        try:
            # 标准化列名
            column_mapping = {
                'symbol': 'symbol', 'code': 'symbol', '合约代码': 'symbol',
                'date': 'date', '日期': 'date',
                'close': 'close', '收盘价': 'close',
                'volume': 'volume', '成交量': 'volume',
                'open_interest': 'open_interest', '持仓量': 'open_interest'
            }
            
            # 重命名列
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # 确保必要的列存在
            required_columns = ['symbol', 'date', 'close']
            if not all(col in df.columns for col in required_columns):
                print(f"    ❌ {exchange['name']}: 缺少必要列，跳过处理")
                return variety_data
            
            # 🔧 修复：正确处理日期（避免int64被当作纳秒时间戳）
            # 关键：统一转换为datetime类型
            if df['date'].dtype in ['int64', 'float64', 'int32']:
                # 整数类型（如20251114）：先转字符串，再指定格式解析
                df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
            elif df['date'].dtype == 'object':
                # 对象类型：可能是字符串、datetime.date等
                # 尝试智能解析（pandas会自动识别格式）
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            else:
                # 其他类型（如datetime64）：直接转换
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # 过滤无效日期（NaT或早于2000年的异常数据）
            df = df[df['date'].notna()]
            df = df[df['date'] >= '2000-01-01']
            
            # 转换为YYYYMMDD格式
            df['date'] = df['date'].dt.strftime('%Y%m%d')
            
            # 按品种分组
            for symbol, group in df.groupby('symbol'):
                try:
                    # 提取品种代码（去除合约月份）
                    # 正确方法：找到第一个数字的位置，之前的部分就是品种代码
                    match = re.match(r'([A-Za-z]+)(\d+)', str(symbol))
                    if not match:
                        continue
                    variety = match.group(1).upper()  # 提取字母部分作为品种代码
                    month_code = match.group(2)  # 提取月份代码
                    
                    # 标准化合约代码：郑商所3位月份补齐为4位
                    # 如FG511 → FG2511, AP603 → AP2603
                    # 特殊处理：主力合约标识"0"保持不变
                    if month_code == '0':
                        pass  # 主力合约，保持"0"不变
                    elif len(month_code) == 3:
                        month_code = '2' + month_code  # 在第一位前加2补齐为4位
                    elif len(month_code) == 4:
                        pass  # 已经是4位，不需要处理
                    else:
                        continue  # 非3位或4位的异常格式，跳过
                    
                    # 生成标准化的合约代码
                    standardized_symbol = variety + month_code
                    
                    # 整理数据
                    processed_group = group[['date', 'symbol', 'close', 'volume', 'open_interest']].copy()
                    # 使用标准化的合约代码
                    processed_group['symbol'] = standardized_symbol
                    processed_group['close'] = pd.to_numeric(processed_group['close'], errors='coerce')
                    processed_group['volume'] = pd.to_numeric(processed_group['volume'], errors='coerce')
                    processed_group['open_interest'] = pd.to_numeric(processed_group['open_interest'], errors='coerce')
                    
                    # 去除无效数据
                    processed_group = processed_group.dropna(subset=['close'])
                    
                    if not processed_group.empty:
                        if variety not in variety_data:
                            variety_data[variety] = []
                        variety_data[variety].append(processed_group)
                        
                except Exception as e:
                    continue
            
            print(f"    📊 {exchange['name']}: 处理得到 {len(variety_data)} 个品种")
            
        except Exception as e:
            print(f"    ❌ {exchange['name']}: 数据处理失败 - {str(e)[:100]}")
        
        return variety_data
    
    def calculate_term_structure_metrics(self, variety_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算期限结构指标
        
        Args:
            variety_df: 品种数据
        
        Returns:
            带期限结构指标的数据
        """
        try:
            # 按日期分组，计算展期收益率
            result_data = []
            
            for date, group in variety_df.groupby('date'):
                # 按合约月份排序
                group = group.sort_values('symbol')
                
                for i, (_, row) in enumerate(group.iterrows()):
                    # 计算展期收益率（相对于下一个合约）
                    roll_yield = 0.0
                    if i < len(group) - 1:
                        next_row = group.iloc[i + 1]
                        roll_yield = self.calculate_roll_yield(
                            row['symbol'], next_row['symbol'],
                            row['close'], next_row['close']
                        )
                    
                    result_data.append({
                        'date': date,
                        'symbol': row['symbol'],
                        'close': row['close'],
                        'volume': row.get('volume', 0),
                        'open_interest': row.get('open_interest', 0),
                        'roll_yield': roll_yield
                    })
            
            return pd.DataFrame(result_data)
            
        except Exception as e:
            print(f"      ❌ 期限结构指标计算失败: {str(e)[:50]}")
            return variety_df
    
    def save_variety_data(self, variety: str, new_data: pd.DataFrame, existing_info: Optional[Dict] = None, target_date: datetime = None) -> bool:
        """
        保存品种数据（智能增量更新）
        
        Args:
            variety: 品种代码
            new_data: 新数据
            existing_info: 现有数据信息
            target_date: 目标日期
        
        Returns:
            是否保存成功
        """
        try:
            # 🔒 验证品种代码：过滤无效的单字母品种
            if len(variety) == 1:
                print(f"    ⚠️ {variety}: 单字母品种代码无效，跳过（可能是错误提取）")
                self.update_stats["skipped_varieties"].append(variety)
                return True
            
            # 🔒 验证数据：过滤1970年的异常数据
            new_data['date_dt'] = pd.to_datetime(new_data['date'], format='%Y%m%d', errors='coerce')
            new_data = new_data[new_data['date_dt'].notna()]  # 过滤解析失败的日期
            new_data = new_data[new_data['date_dt'] >= '2000-01-01']  # 过滤2000年之前的数据
            
            if len(new_data) == 0:
                print(f"    ⚠️ {variety}: 过滤后无有效数据（可能全是1970异常数据）")
                self.update_stats["skipped_varieties"].append(variety)
                return True
            
            variety_dir = self.base_dir / variety
            variety_dir.mkdir(parents=True, exist_ok=True)
            
            ts_file = variety_dir / "term_structure.csv"
            
            if existing_info and ts_file.exists():
                # 读取现有数据
                existing_df = pd.read_csv(ts_file)
                
                # 🔒 清理现有数据中的1970异常数据
                existing_df['date_dt'] = pd.to_datetime(existing_df['date'], format='%Y%m%d', errors='coerce')
                existing_df = existing_df[existing_df['date_dt'].notna()]
                existing_df = existing_df[existing_df['date_dt'] >= '2000-01-01']
                existing_df = existing_df.drop(columns=['date_dt'])
                
                if len(existing_df) == 0:
                    # 如果现有数据清理后为空，视为新品种
                    print(f"    ⚠️ {variety}: 现有数据全是异常数据，已清理")
                    existing_info = None
                
                latest_date = existing_info['latest_date'] if existing_info else None
                
                # 🎯 智能过滤：只保留比现有最新日期更新的数据
                if latest_date:
                    filtered_new_data = new_data[new_data['date_dt'] > latest_date].copy()
                else:
                    filtered_new_data = new_data.copy()
                filtered_new_data = filtered_new_data.drop(columns=['date_dt'])
                
                if len(filtered_new_data) > 0:
                    # 合并数据
                    combined_df = pd.concat([existing_df, filtered_new_data], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date', 'symbol']).sort_values(['date', 'symbol']).reset_index(drop=True)
                    
                    new_records = len(combined_df) - len(existing_df)
                    if new_records > 0:
                        # 计算日期范围
                        filtered_new_data['date_dt'] = pd.to_datetime(filtered_new_data['date'], format='%Y%m%d')
                        new_min = filtered_new_data['date_dt'].min().strftime('%Y-%m-%d')
                        new_max = filtered_new_data['date_dt'].max().strftime('%Y-%m-%d')
                        
                        print(f"    ✅ {variety}: 新增 {new_records} 条 ({new_min} ~ {new_max})")
                        self.update_stats["updated_varieties"].append(variety)
                        self.update_stats["total_new_records"] += new_records
                        
                        # 保存数据
                        combined_df.to_csv(ts_file, index=False, encoding='utf-8-sig')
                        return True
                    else:
                        print(f"    ℹ️ {variety}: 去重后无新数据")
                        self.update_stats["skipped_varieties"].append(variety)
                        return True
                else:
                    print(f"    ℹ️ {variety}: 已是最新 (现有: {latest_date.strftime('%Y-%m-%d')})")
                    self.update_stats["skipped_varieties"].append(variety)
                    return True
            else:
                # 新品种或无现有数据
                combined_df = new_data.drop(columns=['date_dt'])
                print(f"    ✅ {variety}: 创建 {len(combined_df)} 条记录 (新品种)")
                self.update_stats["new_varieties"].append(variety)
                self.update_stats["total_new_records"] += len(combined_df)
                
                # 保存数据
                combined_df.to_csv(ts_file, index=False, encoding='utf-8-sig')
                return True
            
        except Exception as e:
            print(f"    ❌ {variety}: 保存失败 - {str(e)}")
            self.update_stats["failed_varieties"].append(variety)
            self.update_stats["error_messages"].append(f"{variety}: 保存失败 - {str(e)}")
            return False
    
    def update_to_date(self, target_date_str: str, update_days: Optional[int] = None, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        更新数据到指定日期（支持智能增量更新）
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            update_days: 更新天数（可选，如果不指定则自动计算）
            specific_varieties: 指定品种列表，None表示全部品种
        
        Returns:
            更新结果统计
        """
        print(f"🚀 期限结构数据更新器")
        print("=" * 60)
        
        # 解析目标日期
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        except ValueError:
            try:
                target_date = datetime.strptime(target_date_str, '%Y%m%d')
            except ValueError:
                raise ValueError(f"日期格式错误: {target_date_str}，请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
        
        self.update_stats["start_time"] = datetime.now()
        self.update_stats["target_date"] = target_date_str
        
        # 获取现有数据状态
        existing_varieties, variety_info = self.get_existing_data_status()
        
        # 🎯 智能计算更新天数：找出最旧的品种日期，确保覆盖所有品种
        if update_days is None:
            latest_dates = [info['latest_date'] for info in variety_info.values() if info.get('latest_date')]
            if latest_dates:
                # 找出最旧的日期（需要更新最多天数的品种）
                oldest_date = min(latest_dates)
                newest_date = max(latest_dates)
                calculated_days = (target_date.date() - oldest_date.date()).days
                
                print(f"📊 智能更新模式:")
                print(f"   最新品种: {newest_date.strftime('%Y-%m-%d')} (已是最新或需少量更新)")
                print(f"   最旧品种: {oldest_date.strftime('%Y-%m-%d')} (需更新 {calculated_days} 天)")
                print(f"   目标日期: {target_date_str}")
                print(f"   策略: 一次性获取 {calculated_days + 5} 天数据，各品种按需保存")
                
                # 从最旧的日期开始更新，加5天缓冲
                update_days = max(calculated_days + 5, 7)  # 至少7天
            else:
                print(f"📊 首次更新: 获取最近90天数据")
                update_days = 90
        else:
            print(f"📊 手动指定: 更新最近 {update_days} 天")
        
        self.update_stats["update_days"] = update_days
        
        # 计算日期范围
        start_date = target_date - timedelta(days=update_days)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = target_date.strftime('%Y%m%d')
        
        print(f"📅 数据获取范围: {start_date_str} ~ {end_date_str} ({update_days} 天)")
        print(f"💡 说明: 获取较长时间窗口数据，各品种根据自己的最新日期智能保存缺失部分\n")
        
        # 按交易所获取数据
        all_variety_data = {}
        
        for exchange in self.exchanges:
            print(f"\n🔄 处理 {exchange['name']}...")
            
            # 获取交易所数据
            exchange_df = self.fetch_exchange_data(exchange, start_date_str, end_date_str)
            if exchange_df is None:
                self.update_stats["exchange_stats"][exchange['name']] = {"status": "failed", "varieties": 0}
                continue
            
            # 处理数据
            variety_data = self.process_exchange_data(exchange_df, exchange)
            
            # 合并到总数据中
            for variety, data_list in variety_data.items():
                if specific_varieties and variety not in specific_varieties:
                    continue
                    
                if variety not in all_variety_data:
                    all_variety_data[variety] = []
                all_variety_data[variety].extend(data_list)
            
            self.update_stats["exchange_stats"][exchange['name']] = {
                "status": "success", 
                "varieties": len(variety_data)
            }
            
            # 添加延迟
            time.sleep(random.uniform(1, 2))
        
        # 处理并保存各品种数据
        print(f"\n💾 保存各品种数据...")
        processed_count = 0
        
        for variety, data_list in all_variety_data.items():
            print(f"\n  处理品种: {variety}")
            
            try:
                # 合并该品种的所有数据
                variety_df = pd.concat(data_list, ignore_index=True)
                
                # 计算期限结构指标
                variety_df = self.calculate_term_structure_metrics(variety_df)
                
                if variety_df.empty:
                    print(f"    ⚠️ {variety}: 无有效数据")
                    continue
                
                # 保存数据
                existing_info = variety_info.get(variety)
                if self.save_variety_data(variety, variety_df, existing_info, target_date):
                    processed_count += 1
                    
            except Exception as e:
                print(f"    ❌ {variety}: 处理失败 - {str(e)[:50]}")
                self.update_stats["failed_varieties"].append(variety)
        
        # 完成统计
        self.update_stats["end_time"] = datetime.now()
        
        print(f"\n📊 更新完成统计:")
        print(f"  ✅ 成功更新品种: {len(self.update_stats['updated_varieties'])} 个")
        print(f"  🆕 新增品种: {len(self.update_stats['new_varieties'])} 个")
        print(f"  ❌ 失败品种: {len(self.update_stats['failed_varieties'])} 个")
        print(f"  ⏭️ 跳过品种: {len(self.update_stats['skipped_varieties'])} 个")
        print(f"  📈 新增记录总数: {self.update_stats['total_new_records']} 条")
        print(f"  ⏱️ 耗时: {(self.update_stats['end_time'] - self.update_stats['start_time']).total_seconds():.1f} 秒")
        
        # 交易所统计
        print(f"\n📋 交易所数据获取统计:")
        for exchange_name, stats in self.update_stats["exchange_stats"].items():
            status_icon = "✅" if stats["status"] == "success" else "❌"
            print(f"  {status_icon} {exchange_name}: {stats['varieties']} 个品种")
        
        if self.update_stats["failed_varieties"]:
            print(f"  ⚠️ 失败品种列表: {', '.join(self.update_stats['failed_varieties'])}")
        
        return self.update_stats
    
    def update_data(self, target_date_str: str, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        更新数据到指定日期（与update_to_date相同，为兼容统一更新器接口）
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            specific_varieties: 指定品种列表，None表示全部品种
        
        Returns:
            更新结果统计
        """
        return self.update_to_date(target_date_str, specific_varieties)

def main():
    """交互式主函数"""
    print("=" * 80)
    print("📈 期限结构数据更新器")
    print("=" * 80)
    
    updater = TermStructureUpdater()
    
    # 获取现有数据状态
    print("\n🔍 正在检查现有数据状态...")
    varieties, info = updater.get_existing_data_status()
    
    print(f"\n📦 已有品种数量: {len(varieties)} 个")
    if varieties:
        print(f"   品种列表: {', '.join(sorted(varieties)[:20])}{'...' if len(varieties) > 20 else ''}")
    else:
        print("📅 当前暂无数据")
    
    # 用户输入更新参数
    print("\n" + "=" * 80)
    print("请输入更新参数:")
    print("-" * 80)
    
    # 输入目标日期
    default_date = datetime.now().strftime('%Y-%m-%d')
    target_date_input = input(f"📅 目标日期 (格式: YYYY-MM-DD, 直接回车使用今天 {default_date}): ").strip()
    target_date = target_date_input if target_date_input else default_date
    
    # 验证日期格式
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ 日期格式错误，使用默认日期: {default_date}")
        target_date = default_date
    
    # 输入品种
    varieties_input = input(f"🎯 要更新的品种 (输入品种代码用逗号分隔，如 RB,CU,AL；直接回车更新全部): ").strip()
    
    if varieties_input:
        specific_varieties = [v.strip().upper() for v in varieties_input.split(',')]
        print(f"\n✅ 将更新指定品种: {', '.join(specific_varieties)}")
    else:
        specific_varieties = None
        print(f"\n✅ 将更新所有品种")
    
    # 确认
    print("\n" + "=" * 80)
    print(f"📋 更新配置:")
    print(f"   目标日期: {target_date}")
    print(f"   更新品种: {'全部' if not specific_varieties else ', '.join(specific_varieties)}")
    print(f"   更新模式: 智能增量更新（自动计算需要更新的天数）")
    print("=" * 80)
    
    confirm = input("\n确认开始更新？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消更新")
        return
    
    # 执行更新（不传入update_days，使用智能计算）
    print("\n🚀 开始更新...")
    result = updater.update_to_date(target_date, specific_varieties=specific_varieties)
    
    print(f"\n" + "=" * 80)
    print("🎯 更新完成!")
    print("=" * 80)

if __name__ == "__main__":
    main()
