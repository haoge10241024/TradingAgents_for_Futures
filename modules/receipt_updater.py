#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仓单数据更新器
与库存数据类似，但使用仓单接口
"""

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import random
import json
from typing import Dict, List, Optional, Tuple

# 品种映射配置（与库存相同）
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
    'WR': '线材', 'Y': '豆油', 'ZN': '沪锌', 'ZC': '动力煤'
}

class ReceiptDataUpdater:
    """仓单数据更新器"""
    
    def __init__(self, database_path: str = "qihuo/database/receipt"):
        """
        初始化仓单数据更新器
        
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
            "new_varieties": [],
            "failed_varieties": [],
            "skipped_varieties": [],
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
        print("🔍 检查现有仓单数据状态...")
        
        varieties = []
        variety_info = {}
        
        # 扫描品种文件夹
        variety_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            receipt_file = folder / "receipt.csv"
            
            if receipt_file.exists():
                try:
                    df = pd.read_csv(receipt_file)
                    if not df.empty and 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # 兼容不同列名
                        record_col = 'receipt'
                        if 'receipt' not in df.columns and 'value' in df.columns:
                            record_col = 'value'
                        
                        if record_col in df.columns:
                            varieties.append(variety)
                            variety_info[variety] = {
                                "records": len(df),
                                "latest_date": df['date'].max(),
                                "earliest_date": df['date'].min()
                            }
                            print(f"   ✅ {variety}: {len(df)} 条记录，最新 {df['date'].max().strftime('%Y-%m-%d')}")
                        else:
                            print(f"   ⚠️ {variety}: 缺少数据列")
                except Exception as e:
                    print(f"   ⚠️ {variety}: 读取失败 - {str(e)}")
        
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
            处理后的DataFrame或None
        """
        for attempt in range(retries):
            try:
                print(f"   📥 获取 {symbol} 数据...")
                time.sleep(random.uniform(0.5, 1.5))
                
                # 获取仓单数据（使用与库存相同的接口）
                raw_df = ak.futures_inventory_em(symbol=series_cn)
                
                if raw_df is None or raw_df.empty:
                    print(f"    ⚠️ 无数据返回")
                    return None
                
                print(f"    ✅ 获取到 {len(raw_df)} 条原始数据")
                
                # 标准化列名 - 仓单数据应该使用receipt和change
                # akshare可能返回不同的列名，需要智能识别
                column_mapping = {}
                for col in raw_df.columns:
                    col_lower = col.lower()
                    if '日期' in col or 'date' in col_lower:
                        column_mapping[col] = 'date'
                    elif '仓单' in col or 'receipt' in col_lower or '库存' in col:
                        column_mapping[col] = 'receipt'
                    elif '增减' in col or 'change' in col_lower or '变化' in col:
                        column_mapping[col] = 'change'
                
                new_df = raw_df.rename(columns=column_mapping)
                
                # 确保必需列存在
                if 'date' not in new_df.columns:
                    new_df['date'] = raw_df.iloc[:, 0]  # 使用第一列作为日期
                if 'receipt' not in new_df.columns:
                    # 尝试从其他列推断
                    numeric_cols = raw_df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        new_df['receipt'] = raw_df[numeric_cols[0]]
                    else:
                        # 尝试转换第二列
                        new_df['receipt'] = pd.to_numeric(raw_df.iloc[:, 1], errors='coerce')
                
                # 处理数据类型
                new_df["date"] = pd.to_datetime(new_df["date"])
                new_df["receipt"] = pd.to_numeric(new_df["receipt"], errors="coerce")
                
                # 计算增减（如果没有change列）
                if 'change' not in new_df.columns or new_df['change'].isna().all():
                    new_df = new_df.sort_values('date')
                    new_df['change'] = new_df['receipt'].diff()
                else:
                    new_df["change"] = pd.to_numeric(new_df["change"], errors="coerce")
                
                # 只保留需要的列
                new_df = new_df[['date', 'receipt', 'change']]
                
                # 去除空值
                new_df = new_df.dropna(subset=["date", "receipt"])
                
                if new_df.empty:
                    print(f"    ⚠️ 清洗后无有效数据")
                    return None
                
                # 过滤到目标日期
                new_df = new_df[new_df['date'] <= target_date]
                
                if new_df.empty:
                    print(f"    ⚠️ 截止日期前无有效数据")
                    return None
                
                new_start = new_df['date'].min().strftime('%Y-%m-%d')
                new_end = new_df['date'].max().strftime('%Y-%m-%d')
                print(f"    📅 数据范围: {new_start} ~ {new_end}")
                
                return new_df
                
            except Exception as e:
                print(f"    ❌ 第 {attempt+1}/{retries} 次尝试失败: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    return None
    
    def update_to_date(self, target_date_str: str, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        智能增量更新到指定日期
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            specific_varieties: 指定品种列表，None表示全部品种
        
        Returns:
            更新统计信息
        """
        self.update_stats["start_time"] = datetime.now()
        self.update_stats["target_date"] = target_date_str
        
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        
        print(f"\n🎯 目标日期: {target_date_str}")
        print("=" * 80)
        
        # 确定要更新的品种
        if specific_varieties:
            varieties_to_update = [(code.upper(), SYMBOL_MAPPING.get(code.upper(), code)) 
                                  for code in specific_varieties if code.upper() in SYMBOL_MAPPING]
        else:
            varieties_to_update = list(SYMBOL_MAPPING.items())
        
        print(f"📋 计划更新 {len(varieties_to_update)} 个品种")
        print("=" * 80)
        
        # 更新每个品种
        for idx, (symbol, series_cn) in enumerate(varieties_to_update, 1):
            print(f"\n[{idx}/{len(varieties_to_update)}] 处理品种: {symbol} ({series_cn})")
            print("-" * 80)
            
            variety_dir = self.base_dir / symbol
            variety_dir.mkdir(exist_ok=True)
            receipt_file = variety_dir / "receipt.csv"
            
            # 获取新数据
            new_data = self.fetch_variety_data(symbol, series_cn, target_date)
            
            if new_data is None:
                print(f"   ⏭️ 跳过 {symbol}")
                self.update_stats["skipped_varieties"].append(symbol)
                continue
            
            # 智能合并：如果已有数据，进行合并
            if receipt_file.exists():
                try:
                    old_data = pd.read_csv(receipt_file)
                    
                    # 兼容不同的列名格式
                    if 'receipt' not in old_data.columns:
                        if 'value' in old_data.columns:
                            old_data = old_data.rename(columns={'value': 'receipt'})
                    if 'change' not in old_data.columns:
                        if '增减' in old_data.columns:
                            old_data = old_data.rename(columns={'增减': 'change'})
                    
                    # 确保有必需的列
                    old_data['date'] = pd.to_datetime(old_data['date'])
                    if 'receipt' in old_data.columns:
                        old_data['receipt'] = pd.to_numeric(old_data['receipt'], errors='coerce')
                    if 'change' in old_data.columns:
                        old_data['change'] = pd.to_numeric(old_data['change'], errors='coerce')
                    
                    # 只保留需要的列
                    old_data = old_data[['date', 'receipt', 'change']]
                    
                    # 合并并去重
                    combined = pd.concat([old_data, new_data], ignore_index=True)
                    combined = combined.drop_duplicates(subset=['date'], keep='last')
                    combined = combined.sort_values('date')
                    
                    new_records = len(combined) - len(old_data)
                    
                    combined.to_csv(receipt_file, index=False, encoding='utf-8-sig')
                    
                    print(f"   ✅ 更新成功: 新增 {new_records} 条记录")
                    self.update_stats["updated_varieties"].append(symbol)
                    self.update_stats["total_new_records"] += new_records
                    
                except Exception as e:
                    print(f"   ❌ 更新失败: {str(e)}")
                    self.update_stats["failed_varieties"].append(symbol)
            else:
                # 首次创建
                try:
                    new_data.to_csv(receipt_file, index=False, encoding='utf-8-sig')
                    print(f"   🆕 创建新文件: {len(new_data)} 条记录")
                    self.update_stats["new_varieties"].append(symbol)
                    self.update_stats["total_new_records"] += len(new_data)
                except Exception as e:
                    print(f"   ❌ 创建失败: {str(e)}")
                    self.update_stats["failed_varieties"].append(symbol)
        
        self.update_stats["end_time"] = datetime.now()
        
        # 打印统计
        print("\n" + "=" * 80)
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
    print("📜 仓单数据更新器")
    print("=" * 80)
    
    updater = ReceiptDataUpdater()
    
    # 获取现有数据状态
    print("\n🔍 正在检查现有数据状态...")
    varieties, info = updater.get_existing_data_status()
    
    print(f"\n📦 已有品种数量: {len(varieties)} 个")
    if varieties:
        print(f"   品种列表: {', '.join(sorted(varieties)[:20])}{'...' if len(varieties) > 20 else ''}")
        
        # 显示最新日期
        if info:
            latest_dates = {}
            for v, v_info in info.items():
                if v_info.get('latest_date'):
                    latest_dates[v] = v_info['latest_date']
            if latest_dates:
                overall_latest = max(latest_dates.values())
                print(f"📅 当前最新数据日期: {overall_latest.strftime('%Y-%m-%d')}")
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
    print(f"   更新模式: 智能增量更新（只更新缺失的数据）")
    print("=" * 80)
    
    confirm = input("\n确认开始更新？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消更新")
        return
    
    # 执行更新
    print("\n🚀 开始更新...")
    result = updater.update_to_date(target_date, specific_varieties)
    
    print(f"\n" + "=" * 80)
    print("🎯 更新完成!")
    print("=" * 80)

if __name__ == "__main__":
    main()

