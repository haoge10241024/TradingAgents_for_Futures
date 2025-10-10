#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库存数据更新器
基于增量更新库存数据逻辑，支持智能数据合并
"""

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import random
import json
from typing import Dict, List, Optional, Tuple

# 品种映射配置
SYMBOL_MAPPING = {
    'A': '豆一', 'AG': '沪银', 'AL': '沪铝', 'AO': '氧化铝', 'AP': '苹果',
    'AU': '沪金', 'B': '豆二', 'BR': '丁二烯橡胶', 'BU': '沥青', 'C': '玉米',
    'CF': '郑棉', 'CJ': '红枣', 'CS': '玉米淀粉', 'CU': '沪铜', 'CY': '棉纱',
    'EB': '苯乙烯', 'EG': '乙二醇', 'FG': '玻璃', 'FU': '燃油', 'HC': '热卷',
    'I': '铁矿石', 'J': '焦炭', 'JD': '鸡蛋', 'JM': '焦煤', 'L': '塑料',
    'LC': '碳酸锂', 'LG': '原木', 'LH': '生猪', 'LU': '低硫燃料油', 'M': '豆粕',
    'MA': '甲醇', 'NI': '镍', 'NR': '20号胶', 'OI': '菜油', 'P': '棕榈',
    'PB': '沪铅', 'PF': '短纤', 'PG': '液化石油气', 'PK': '花生', 'PP': '聚丙烯',
    'PR': '瓶片', 'PS': '多晶硅', 'PTA': 'PTA', 'PX': '对二甲苯', 'RB': '螺纹钢',
    'RM': '菜粕', 'RS': '菜籽', 'RU': '橡胶', 'SA': '纯碱', 'SF': '硅铁',
    'SH': '烧碱', 'SI': '工业硅', 'SM': '锰硅', 'SN': '锡', 'SP': '纸浆',
    'SR': '白糖', 'SS': '不锈钢', 'TA': 'PTA', 'UR': '尿素', 'V': 'PVC',
    'Y': '豆油', 'ZN': '沪锌'
}

class InventoryDataUpdater:
    """库存数据更新器"""
    
    def __init__(self, database_path: str = "D:/Cursor/cursor项目/TradingAgent/qihuo/database/inventory"):
        """
        初始化库存数据更新器
        
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
            "new_varieties": [],
            "total_new_records": 0,
            "error_messages": []
        }
    
    def get_existing_data_status(self) -> Tuple[List[str], Dict]:
        """
        获取现有数据状态
        
        Returns:
            varieties: 现有品种列表
            variety_info: 各品种详细信息
        """
        print("🔍 检查现有库存数据状态...")
        
        varieties = []
        variety_info = {}
        
        if not self.base_dir.exists():
            return [], {}
        
        variety_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            inventory_file = folder / "inventory.csv"
            
            if inventory_file.exists():
                try:
                    df = pd.read_csv(inventory_file)
                    if len(df) > 0 and 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        variety_latest = df['date'].max()
                        variety_earliest = df['date'].min()
                        record_count = len(df)
                        
                        variety_info[variety] = {
                            "earliest_date": variety_earliest,
                            "latest_date": variety_latest,
                            "record_count": record_count,
                            "file_path": inventory_file
                        }
                        
                        varieties.append(variety)
                        print(f"  {variety}: {record_count} 条记录 ({variety_earliest.strftime('%Y-%m-%d')} ~ {variety_latest.strftime('%Y-%m-%d')})")
                        
                except Exception as e:
                    print(f"  ❌ {variety}: 读取失败 - {str(e)[:50]}")
                    self.update_stats["error_messages"].append(f"{variety}: 数据读取失败 - {str(e)}")
        
        print(f"\n📊 总计: {len(varieties)} 个有效品种")
        return varieties, variety_info
    
    def fetch_variety_data(self, symbol: str, series_cn: str, target_date: datetime, retries: int = 3) -> Optional[pd.DataFrame]:
        """
        获取品种数据
        
        Args:
            symbol: 品种代码
            series_cn: 中文品种名称
            target_date: 目标日期（用于数据过滤）
            retries: 重试次数
        
        Returns:
            数据DataFrame或None
        """
        print(f"  📡 获取 {symbol} ({series_cn}) 的库存数据...")
        
        for attempt in range(retries):
            try:
                # 获取数据（注意：库存数据接口不支持日期参数，会返回所有历史数据）
                raw_df = ak.futures_inventory_em(symbol=series_cn)
                
                if raw_df is None or raw_df.empty:
                    print(f"    ❌ 第{attempt+1}次尝试: 无数据返回")
                    if attempt < retries - 1:
                        time.sleep(random.uniform(1, 3))
                    continue
                
                # 标准化数据
                new_df = raw_df.rename(columns={"日期": "date", "库存": "value"})
                new_df["date"] = pd.to_datetime(new_df["date"])
                new_df["value"] = pd.to_numeric(new_df["value"], errors="coerce")
                
                # 计算增减列（基于前一日数据计算）
                new_df = new_df.sort_values('date').reset_index(drop=True)
                new_df["增减"] = new_df["value"].diff().fillna(0)
                
                new_df = new_df.dropna(subset=["value"]).drop_duplicates(subset=["date"]).sort_values("date")
                
                # 过滤到目标日期（库存数据特殊处理）
                new_df = new_df[new_df['date'] <= target_date]
                
                if new_df.empty:
                    print(f"    ⚠️ 截止日期前无有效数据")
                    return None
                
                new_start = new_df['date'].min().strftime('%Y-%m-%d')
                new_end = new_df['date'].max().strftime('%Y-%m-%d')
                print(f"    ✅ 获取到 {len(new_df)} 条记录 ({new_start} ~ {new_end})")
                
                return new_df
                
            except Exception as e:
                print(f"    ❌ 第{attempt+1}次尝试失败: {str(e)[:50]}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(1, 3))
        
        print(f"    ❌ 所有尝试失败")
        return None
    
    def save_variety_data(self, symbol: str, new_data: pd.DataFrame, existing_info: Optional[Dict] = None) -> bool:
        """
        保存品种数据（智能合并）
        
        Args:
            symbol: 品种代码
            new_data: 新数据
            existing_info: 现有数据信息
        
        Returns:
            是否保存成功
        """
        try:
            variety_dir = self.base_dir / symbol
            variety_dir.mkdir(parents=True, exist_ok=True)
            
            inventory_file = variety_dir / "inventory.csv"
            
            if existing_info and inventory_file.exists():
                # 读取现有数据
                existing_df = pd.read_csv(inventory_file)
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                
                # 计算新增数据
                existing_dates = set(existing_df['date'].dt.date)
                new_dates = set(new_data['date'].dt.date)
                added_dates = new_dates - existing_dates
                
                if added_dates:
                    # 有新数据，合并
                    combined_df = pd.concat([existing_df, new_data]).drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                    
                    # 重新计算全部增减值
                    combined_df["增减"] = combined_df["value"].diff().fillna(0)
                    
                    latest_added = max(added_dates).strftime('%Y-%m-%d')
                    print(f"    ✅ {symbol}: 新增 {len(added_dates)} 条记录 (至 {latest_added})")
                    self.update_stats["updated_varieties"].append(symbol)
                    self.update_stats["total_new_records"] += len(added_dates)
                else:
                    # 无新数据
                    combined_df = existing_df
                    print(f"    ℹ️ {symbol}: 无新数据")
                    self.update_stats["skipped_varieties"].append(symbol)
                    return True
            else:
                # 新品种或无现有数据
                combined_df = new_data
                data_span = f"{new_data['date'].min().strftime('%Y-%m-%d')} ~ {new_data['date'].max().strftime('%Y-%m-%d')}"
                print(f"    ✅ {symbol}: 创建 {len(new_data)} 条记录 ({data_span})")
                self.update_stats["new_varieties"].append(symbol)
                self.update_stats["total_new_records"] += len(new_data)
            
            # 保存数据
            combined_df.to_csv(inventory_file, index=False, encoding='utf-8')
            return True
            
        except Exception as e:
            print(f"    ❌ {symbol}: 保存失败 - {str(e)}")
            self.update_stats["failed_varieties"].append(symbol)
            self.update_stats["error_messages"].append(f"{symbol}: 保存失败 - {str(e)}")
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
        print(f"🚀 库存数据更新器")
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
        print(f"⚠️ 注意: 库存数据接口无法选择日期范围，会获取完整历史数据然后过滤")
        
        # 获取现有数据状态
        existing_varieties, variety_info = self.get_existing_data_status()
        
        # 确定要更新的品种
        if specific_varieties:
            target_symbols = [(s, SYMBOL_MAPPING.get(s, s)) for s in specific_varieties if s in SYMBOL_MAPPING]
            print(f"🎯 指定更新品种: {len(target_symbols)} 个")
        else:
            target_symbols = list(SYMBOL_MAPPING.items())
            print(f"🎯 全品种更新: {len(target_symbols)} 个")
        
        # 执行更新
        processed_count = 0
        
        for i, (symbol, series_cn) in enumerate(target_symbols):
            print(f"\n[{i+1}/{len(target_symbols)}] 处理品种: {symbol} ({series_cn})")
            
            # 获取品种数据
            new_data = self.fetch_variety_data(symbol, series_cn, target_date)
            
            if new_data is None or new_data.empty:
                print(f"  ❌ 跳过 {symbol}: 数据获取失败")
                self.update_stats["failed_varieties"].append(symbol)
                continue
            
            # 保存数据
            existing_info = variety_info.get(symbol)
            if self.save_variety_data(symbol, new_data, existing_info):
                processed_count += 1
            
            # 添加随机延迟避免请求过快
            if i < len(target_symbols) - 1:
                delay = random.uniform(0.5, 1.5)
                time.sleep(delay)
        
        # 完成统计
        self.update_stats["end_time"] = datetime.now()
        
        print(f"\n📊 更新完成统计:")
        print(f"  ✅ 成功更新品种: {len(self.update_stats['updated_varieties'])} 个")
        print(f"  🆕 新增品种: {len(self.update_stats['new_varieties'])} 个")
        print(f"  ❌ 失败品种: {len(self.update_stats['failed_varieties'])} 个")
        print(f"  ⏭️ 跳过品种: {len(self.update_stats['skipped_varieties'])} 个")
        print(f"  📈 新增记录总数: {self.update_stats['total_new_records']} 条")
        print(f"  ⏱️ 耗时: {(self.update_stats['end_time'] - self.update_stats['start_time']).total_seconds():.1f} 秒")
        
        if self.update_stats["failed_varieties"]:
            print(f"  ⚠️ 失败品种列表: {', '.join(self.update_stats['failed_varieties'])}")
        
        return self.update_stats

def main():
    """测试主函数"""
    updater = InventoryDataUpdater()
    
    # 获取现有数据状态
    varieties, info = updater.get_existing_data_status()
    
    # 模拟更新前3个品种到今天
    target_date = datetime.now().strftime('%Y-%m-%d')
    test_varieties = ['RB', 'CU', 'AL'] if varieties else None
    
    result = updater.update_to_date(target_date, test_varieties)
    
    print(f"\n🎯 更新结果: {result}")

if __name__ == "__main__":
    main()
