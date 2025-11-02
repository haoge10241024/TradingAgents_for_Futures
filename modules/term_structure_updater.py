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
                # 大商所使用不同的接口
                df = ak.futures_zh_daily_sina(symbol="all", start_date=start_date, end_date=end_date)
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
            
            # 处理日期
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
            
            # 按品种分组
            for symbol, group in df.groupby('symbol'):
                try:
                    # 提取品种代码（去除合约月份）
                    if len(symbol) >= 4:
                        variety = symbol[:-4].upper()  # 移除最后4位数字
                    else:
                        continue
                    
                    # 整理数据
                    processed_group = group[['date', 'symbol', 'close', 'volume', 'open_interest']].copy()
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
    
    def save_variety_data(self, variety: str, new_data: pd.DataFrame, existing_info: Optional[Dict] = None) -> bool:
        """
        保存品种数据（增量更新）
        
        Args:
            variety: 品种代码
            new_data: 新数据
            existing_info: 现有数据信息
        
        Returns:
            是否保存成功
        """
        try:
            variety_dir = self.base_dir / variety
            variety_dir.mkdir(parents=True, exist_ok=True)
            
            ts_file = variety_dir / "term_structure.csv"
            
            if existing_info and ts_file.exists():
                # 读取现有数据
                existing_df = pd.read_csv(ts_file)
                
                # 合并数据
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date', 'symbol']).sort_values(['date', 'symbol']).reset_index(drop=True)
                
                new_records = len(combined_df) - len(existing_df)
                if new_records > 0:
                    print(f"    ✅ {variety}: 新增 {new_records} 条记录")
                    self.update_stats["updated_varieties"].append(variety)
                    self.update_stats["total_new_records"] += new_records
                else:
                    print(f"    ℹ️ {variety}: 无新数据")
                    self.update_stats["skipped_varieties"].append(variety)
                    return True
            else:
                # 新品种或无现有数据
                combined_df = new_data
                print(f"    ✅ {variety}: 创建 {len(new_data)} 条记录")
                self.update_stats["new_varieties"].append(variety)
                self.update_stats["total_new_records"] += len(new_data)
            
            # 保存数据
            combined_df.to_csv(ts_file, index=False, encoding='utf-8')
            return True
            
        except Exception as e:
            print(f"    ❌ {variety}: 保存失败 - {str(e)}")
            self.update_stats["failed_varieties"].append(variety)
            self.update_stats["error_messages"].append(f"{variety}: 保存失败 - {str(e)}")
            return False
    
    def update_to_date(self, target_date_str: str, update_days: int = 5, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        更新数据到指定日期
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            update_days: 更新天数
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
        self.update_stats["update_days"] = update_days
        
        # 计算日期范围
        start_date = target_date - timedelta(days=update_days + 2)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = target_date.strftime('%Y%m%d')
        
        print(f"📅 更新日期范围: {start_date_str} - {end_date_str}")
        print(f"📊 计划更新天数: {update_days}")
        
        # 获取现有数据状态
        existing_varieties, variety_info = self.get_existing_data_status()
        
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
                if self.save_variety_data(variety, variety_df, existing_info):
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
    """测试主函数"""
    updater = TermStructureUpdater()
    
    # 获取现有数据状态
    varieties, info = updater.get_existing_data_status()
    
    # 模拟更新到今天
    target_date = datetime.now().strftime('%Y-%m-%d')
    result = updater.update_to_date(target_date, update_days=3)
    
    print(f"\n🎯 更新结果: {result}")

if __name__ == "__main__":
    main()
