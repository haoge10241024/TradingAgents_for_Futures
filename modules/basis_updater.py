#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基差数据更新器
基于最终修复版基差数据更新器的逻辑，支持增量更新
"""

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import random
import json
from typing import Dict, List, Optional, Tuple

class BasisDataUpdater:
    """基差数据更新器"""
    
    def __init__(self, database_path: str = "qihuo/database/basis"):
        """
        初始化基差数据更新器
        
        Args:
            database_path: 数据库路径
        """
        self.base_dir = Path(database_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_stats = {
            "start_time": None,
            "end_time": None,
            "target_date": None,
            "updated_varieties": [],
            "failed_varieties": [],
            "skipped_varieties": [],
            "total_new_records": 0,
            "error_messages": []
        }
    
    def get_existing_data_status(self) -> Tuple[Optional[datetime], List[str], Dict]:
        """
        获取现有数据状态
        
        Returns:
            latest_date: 最新数据日期
            varieties: 现有品种列表
            variety_info: 各品种详细信息
        """
        print("🔍 检查现有基差数据状态...")
        
        latest_date = None
        varieties = []
        variety_info = {}
        
        if not self.base_dir.exists():
            return None, [], {}
        
        variety_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            basis_file = folder / "basis_data.csv"
            
            if basis_file.exists():
                try:
                    df = pd.read_csv(basis_file)
                    if len(df) > 0 and 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        variety_latest = df['date'].max()
                        variety_earliest = df['date'].min()
                        record_count = len(df)
                        
                        variety_info[variety] = {
                            "earliest_date": variety_earliest,
                            "latest_date": variety_latest,
                            "record_count": record_count
                        }
                        
                        varieties.append(variety)
                        
                        if latest_date is None or variety_latest > latest_date:
                            latest_date = variety_latest
                        
                        print(f"  {variety}: {record_count} 条记录 ({variety_earliest.strftime('%Y-%m-%d')} ~ {variety_latest.strftime('%Y-%m-%d')})")
                        
                except Exception as e:
                    print(f"  ❌ {variety}: 读取失败 - {str(e)[:50]}")
                    self.update_stats["error_messages"].append(f"{variety}: 数据读取失败 - {str(e)}")
        
        if latest_date:
            print(f"\n📅 整体最新数据日期: {latest_date.strftime('%Y-%m-%d')}")
        else:
            print("\n⚠️ 未找到有效的基差数据")
        
        return latest_date, varieties, variety_info
    
    def calculate_update_dates(self, latest_date: Optional[datetime], target_date: datetime) -> List[str]:
        """
        计算需要更新的日期列表
        
        Args:
            latest_date: 现有数据的最新日期
            target_date: 目标更新日期
        
        Returns:
            需要更新的日期列表 (YYYYMMDD格式)
        """
        update_dates = []
        
        if latest_date is None:
            # 没有现有数据，获取最近5个交易日
            print("⚠️ 未找到现有数据，将获取最近5个交易日数据")
            current = target_date
            while len(update_dates) < 5:
                current -= timedelta(days=1)
                if current.weekday() < 5:  # 工作日
                    update_dates.append(current.strftime('%Y%m%d'))
            update_dates.reverse()
        else:
            # 计算需要更新的交易日
            next_date = latest_date + timedelta(days=1)
            current = next_date
            
            while current.date() <= target_date.date():
                if current.weekday() < 5:  # 工作日
                    update_dates.append(current.strftime('%Y%m%d'))
                current += timedelta(days=1)
        
        return update_dates
    
    def fetch_daily_data(self, date_str: str, retry_count: int = 3) -> Optional[pd.DataFrame]:
        """
        获取指定日期的基差数据
        
        Args:
            date_str: 日期字符串 (YYYYMMDD格式)
            retry_count: 重试次数
        
        Returns:
            数据DataFrame或None
        """
        print(f"  📡 获取 {date_str} 的基差数据...")
        
        for attempt in range(retry_count):
            try:
                # 获取数据
                df = ak.futures_spot_price(date_str)
                
                if df is None or df.empty:
                    print(f"    ❌ 第{attempt+1}次尝试: 无数据返回")
                    if attempt < retry_count - 1:
                        time.sleep(random.uniform(1, 3))
                    continue
                
                print(f"    ✅ 获取到 {len(df)} 个品种的数据")
                
                # 检查品种列名（适应不同版本的akshare）
                variety_col = None
                if 'var' in df.columns:
                    variety_col = 'var'
                elif 'symbol' in df.columns:
                    variety_col = 'symbol'
                else:
                    print(f"    ❌ 未找到品种列（var或symbol）")
                    continue
                
                # 数据标准化
                df = df.copy()
                df['date'] = pd.to_datetime(date_str, format='%Y%m%d')
                
                return df, variety_col
                
            except Exception as e:
                print(f"    ❌ 第{attempt+1}次尝试失败: {str(e)[:100]}")
                if attempt < retry_count - 1:
                    time.sleep(random.uniform(1, 3))
        
        print(f"    ❌ 所有尝试失败")
        return None, None
    
    def save_variety_data(self, variety: str, new_data: pd.DataFrame) -> bool:
        """
        保存品种数据
        
        Args:
            variety: 品种代码
            new_data: 新数据
        
        Returns:
            是否保存成功
        """
        try:
            variety_dir = self.base_dir / variety
            variety_dir.mkdir(parents=True, exist_ok=True)
            
            basis_file = variety_dir / "basis_data.csv"
            summary_file = variety_dir / "basis_summary.json"
            
            # 读取现有数据
            if basis_file.exists():
                existing_df = pd.read_csv(basis_file)
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                
                # 合并数据
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                
                new_records = len(combined_df) - len(existing_df)
                if new_records > 0:
                    print(f"    ✅ {variety}: 新增 {new_records} 条记录")
                    self.update_stats["total_new_records"] += new_records
                else:
                    print(f"    ℹ️ {variety}: 无新数据")
                    self.update_stats["skipped_varieties"].append(variety)
                    return True
            else:
                combined_df = new_data
                print(f"    ✅ {variety}: 创建 {len(new_data)} 条记录")
                self.update_stats["total_new_records"] += len(new_data)
            
            # 保存CSV数据
            combined_df.to_csv(basis_file, index=False, encoding='utf-8')
            
            # 更新摘要信息
            summary_info = {
                "symbol": variety,
                "record_count": len(combined_df),
                "date_range": {
                    "start": combined_df['date'].min().isoformat(),
                    "end": combined_df['date'].max().isoformat()
                },
                "last_updated": datetime.now().isoformat(),
                "columns": list(combined_df.columns)
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_info, f, ensure_ascii=False, indent=2)
            
            self.update_stats["updated_varieties"].append(variety)
            return True
            
        except Exception as e:
            print(f"    ❌ {variety}: 保存失败 - {str(e)}")
            self.update_stats["failed_varieties"].append(variety)
            self.update_stats["error_messages"].append(f"{variety}: 保存失败 - {str(e)}")
            return False
    
    def update_to_date(self, target_date_str: str, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        更新数据到指定日期
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            specific_varieties: 指定品种列表，None表示全部品种
        
        Returns:
            更新结果统计
        """
        print(f"🚀 基差数据更新器")
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
        
        print(f"📅 目标更新日期: {target_date.strftime('%Y-%m-%d')}")
        
        # 获取现有数据状态
        latest_date, existing_varieties, variety_info = self.get_existing_data_status()
        
        # 计算更新日期
        update_dates = self.calculate_update_dates(latest_date, target_date)
        
        if not update_dates:
            print("✅ 数据已是最新，无需更新")
            self.update_stats["end_time"] = datetime.now()
            return self.update_stats
        
        print(f"📋 需要更新的日期: {update_dates}")
        
        # 执行更新
        success_count = 0
        total_attempts = 0
        
        for i, date_str in enumerate(update_dates):
            print(f"\n[{i+1}/{len(update_dates)}] 处理日期: {date_str}")
            total_attempts += 1
            
            # 获取当日数据
            result = self.fetch_daily_data(date_str)
            if result is None or result[0] is None:
                print(f"  ❌ 跳过 {date_str}: 数据获取失败")
                continue
            
            df, variety_col = result
            success_count += 1
            
            # 按品种处理数据
            variety_success = 0
            variety_total = 0
            
            for _, row in df.iterrows():
                variety = str(row[variety_col]).upper()
                variety_total += 1
                
                # 如果指定了品种，只处理指定的品种
                if specific_varieties and variety not in specific_varieties:
                    continue
                
                # 构造该品种的数据
                variety_data = pd.DataFrame([{
                    'date': row['date'],
                    'symbol': variety,
                    'spot_price': row.get('现货价格', 0),
                    'near_contract': row.get('近月合约', ''),
                    'near_contract_price': row.get('近月价格', 0),
                    'dominant_contract': row.get('主力合约', ''),
                    'dominant_contract_price': row.get('主力价格', 0),
                    'near_month': row.get('近月月份', 0),
                    'dominant_month': row.get('主力月份', 0),
                    'near_basis': row.get('近月基差', 0),
                    'dom_basis': row.get('主力基差', 0),
                    'near_basis_rate': row.get('近月基差率', 0),
                    'dom_basis_rate': row.get('主力基差率', 0)
                }])
                
                if self.save_variety_data(variety, variety_data):
                    variety_success += 1
            
            print(f"  📊 品种更新: 成功 {variety_success}/{variety_total}")
            
            # 添加随机延迟避免请求过快
            if i < len(update_dates) - 1:
                delay = random.uniform(0.5, 2.0)
                time.sleep(delay)
        
        # 完成统计
        self.update_stats["end_time"] = datetime.now()
        
        print(f"\n📊 更新完成统计:")
        print(f"  ✅ 成功更新品种: {len(self.update_stats['updated_varieties'])} 个")
        print(f"  ❌ 失败品种: {len(self.update_stats['failed_varieties'])} 个")
        print(f"  ⏭️ 跳过品种: {len(self.update_stats['skipped_varieties'])} 个")
        print(f"  📈 新增记录总数: {self.update_stats['total_new_records']} 条")
        print(f"  ⏱️ 耗时: {(self.update_stats['end_time'] - self.update_stats['start_time']).total_seconds():.1f} 秒")
        
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
    updater = BasisDataUpdater()
    
    # 获取现有数据状态
    latest_date, varieties, info = updater.get_existing_data_status()
    
    # 模拟更新到今天
    target_date = datetime.now().strftime('%Y-%m-%d')
    result = updater.update_to_date(target_date)
    
    print(f"\n🎯 更新结果: {result}")

if __name__ == "__main__":
    main()
