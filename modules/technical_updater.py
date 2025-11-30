#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析数据更新器
基于智能技术分析数据更新器，支持OHLC数据获取和技术指标计算
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
try:
    import talib
    import numpy as np
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️ 警告: talib库未安装，技术指标计算功能将被禁用")
    print("   安装方法: pip install TA-Lib")

warnings.filterwarnings('ignore')

# 品种合约映射
SYMBOL_MAPPING = {
    'A': 'a2409', 'AG': 'ag2412', 'AL': 'al2411', 'AO': 'ao2412', 'AP': 'AP501', 'AU': 'au2412', 'B': 'b2409',
    'BU': 'bu2412', 'C': 'c2409', 'CF': 'CF409', 'CJ': 'CJ501', 'CS': 'cs2409', 'CU': 'cu2411', 'CY': 'CY409',
    'EB': 'eb2411', 'EG': 'eg2411', 'FG': 'FG409', 'FU': 'fu2409', 'HC': 'hc2410',
    'I': 'i2409', 'J': 'j2409', 'JD': 'jd2409', 'JM': 'jm2409', 'L': 'l2409',
    'LC': 'lc2409', 'LG': 'LG501', 'LH': 'lh2409', 'LU': 'lu2409', 'M': 'm2409', 'MA': 'MA409', 'NI': 'ni2411', 'NR': 'nr2407',
    'OI': 'OI409', 'P': 'p2409', 'PB': 'pb2411', 'PF': 'PF409', 'PG': 'pg2411', 'PK': 'PK409',
    'PP': 'pp2409', 'PR': 'PR501', 'PS': 'ps2409', 'PX': 'PX409', 'RB': 'rb2410', 'RM': 'RM409', 'RS': 'RS501', 'RU': 'ru2409', 
    'SA': 'SA409', 'SC': 'sc2412', 'SF': 'sf2411', 'SH': 'SH501', 'SI': 'si2409', 'SM': 'sm2409', 'SN': 'sn2411', 'SP': 'sp2409',
    'SR': 'SR409', 'SS': 'ss2410', 'TA': 'TA409', 'UR': 'UR409', 'V': 'v2409',
    'Y': 'y2409', 'ZN': 'zn2411'
}

class TechnicalDataUpdater:
    """技术分析数据更新器"""
    
    def __init__(self, database_path: str = "qihuo/database/technical_analysis"):
        """
        初始化技术分析数据更新器
        
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
        print("🔍 检查现有技术分析数据状态...")
        
        varieties = []
        variety_info = {}
        
        if not self.base_dir.exists():
            return [], {}
        
        variety_folders = [d for d in self.base_dir.iterdir() if d.is_dir()]
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            ohlc_file = folder / "ohlc_data.csv"
            
            if ohlc_file.exists():
                try:
                    df = pd.read_csv(ohlc_file)
                    if len(df) > 0 and '时间' in df.columns:
                        df['时间'] = pd.to_datetime(df['时间'])
                        variety_latest = df['时间'].max()
                        variety_earliest = df['时间'].min()
                        record_count = len(df)
                        
                        variety_info[variety] = {
                            "earliest_date": variety_earliest,
                            "latest_date": variety_latest,
                            "record_count": record_count,
                            "ohlc_file": ohlc_file
                        }
                        
                        varieties.append(variety)
                        print(f"  {variety}: {record_count} 条记录 ({variety_earliest.strftime('%Y-%m-%d')} ~ {variety_latest.strftime('%Y-%m-%d')})")
                        
                except Exception as e:
                    print(f"  ❌ {variety}: 读取失败 - {str(e)[:50]}")
                    self.update_stats["error_messages"].append(f"{variety}: 数据读取失败 - {str(e)}")
        
        print(f"\n📊 总计: {len(varieties)} 个有效品种")
        return varieties, variety_info
    
    def fetch_ohlc_data(self, symbol: str, contract_name: str, start_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        获取OHLC数据 - 使用中文主连合约名称
        
        Args:
            symbol: 品种代码
            contract_name: 合约名称
            start_date: 开始日期（用于增量更新）
        
        Returns:
            数据DataFrame或None
        """
        # 品种代码到中文主连合约名称的映射
        SYMBOL_TO_CHINESE = {
            # 钢铁建材
            "RB": "螺纹钢主连", "HC": "热卷主连", "I": "铁矿石主连", "J": "焦炭主连", 
            "JM": "焦煤主连", "SS": "不锈钢主连",
            # 有色金属  
            "CU": "沪铜主连", "AL": "沪铝主连", "ZN": "沪锌主连", "NI": "沪镍主连", 
            "SN": "沪锡主连", "PB": "沪铅主连", "AO": "氧化铝主连",
            # 贵金属
            "AU": "沪金主连", "AG": "沪银主连",
            # 化工能源
            "RU": "橡胶主连", "NR": "20号胶主连", "BU": "沥青主连", "FU": "燃油主连",
            "LU": "低硫燃油主连", "PG": "LPG主连", "EB": "苯乙烯主连", 
            "EG": "乙二醇主连", "MA": "甲醇主连", "TA": "PTA主连", "PX": "对二甲苯主连", 
            "PL": "聚烯烃主连", "PF": "短纤主连", "CY": "棉纱主连", "PR": "瓶片主连",
            "SH": "烧碱主连", "SC": "原油主连",
            # 农产品
            "SR": "白糖主连", "CF": "棉花主连", "AP": "苹果主连", "CJ": "红枣主连", 
            "SP": "纸浆主连", "P": "棕榈油主连", "Y": "豆油主连", "M": "豆粕主连", 
            "RM": "菜粕主连", "OI": "菜油主连", "RS": "菜籽主连", "PK": "花生主连", 
            "A": "豆一主连", "B": "豆二主连", "C": "玉米主连", "CS": "淀粉主连", 
            "JD": "鸡蛋主连", "LH": "生猪主连", "LG": "原木主连",
            # 玻璃
            "FG": "玻璃主连", "SA": "纯碱主连",
            # 塑料
            "L": "塑料主连", "PP": "聚丙烯主连", "V": "PVC主连", "UR": "尿素主连",
            # 纺织
            "SF": "硅铁主连", "SM": "锰硅主连",
            # 新能源
            "LC": "碳酸锂主连", "SI": "工业硅主连", "PS": "多晶硅主连"
        }
        
        chinese_name = SYMBOL_TO_CHINESE.get(symbol, f"{symbol}主连")
        print(f"  📡 获取 {symbol} ({chinese_name}) 的OHLC数据...")
        
        # 方法1: 使用中文主连合约名称调用futures_hist_em
        try:
            print(f"    📡 方法1: futures_hist_em({chinese_name})")
            df = ak.futures_hist_em(symbol=chinese_name, period="daily")
            
            if df is not None and not df.empty:
                print(f"    ✅ 东方财富接口成功: {len(df)} 条记录")
                processed_df = self._process_em_data(df, symbol, start_date)
                if not processed_df.empty:
                    return processed_df
            else:
                print(f"    ⚠️ 东方财富接口返回空数据")
                
        except Exception as e:
            print(f"    ⚠️ 东方财富接口失败: {str(e)[:50]}")
        
        # 方法2: 尝试新浪日线接口
        try:
            print(f"    📡 方法2: futures_zh_daily_sina({symbol})")
            df = ak.futures_zh_daily_sina(symbol=symbol)
            
            if df is not None and not df.empty:
                print(f"    ✅ 新浪日线接口成功: {len(df)} 条记录")
                processed_df = self._process_sina_daily_data(df, symbol, start_date)
                if not processed_df.empty:
                    return processed_df
            else:
                print(f"    ⚠️ 新浪日线接口返回空数据")
                
        except Exception as e:
            print(f"    ⚠️ 新浪日线接口失败: {str(e)[:50]}")
        
        # 方法3: 尝试新浪主力合约接口
        try:
            print(f"    📡 方法3: futures_main_sina({symbol})")
            df = ak.futures_main_sina(symbol=symbol)
            
            if df is not None and not df.empty:
                print(f"    ✅ 新浪主力接口成功: {len(df)} 条记录")
                processed_df = self._process_sina_main_data(df, symbol, start_date)
                if not processed_df.empty:
                    return processed_df
            else:
                print(f"    ⚠️ 新浪主力接口返回空数据")
                
        except Exception as e:
            print(f"    ⚠️ 新浪主力接口失败: {str(e)[:50]}")
        
        # 方法4: 使用get_futures_daily接口（按交易所获取）
        try:
            print(f"    📡 方法4: get_futures_daily(按交易所)")
            
            # 品种到交易所的映射
            VARIETY_TO_EXCHANGE = {
                'CU': 'SHFE', 'AL': 'SHFE', 'ZN': 'SHFE', 'PB': 'SHFE', 'NI': 'SHFE', 
                'SN': 'SHFE', 'AU': 'SHFE', 'AG': 'SHFE', 'RB': 'SHFE', 'WR': 'SHFE', 
                'HC': 'SHFE', 'FU': 'SHFE', 'BU': 'SHFE', 'RU': 'SHFE', 'AO': 'SHFE',
                'A': 'DCE', 'B': 'DCE', 'C': 'DCE', 'CS': 'DCE', 'M': 'DCE', 'Y': 'DCE', 
                'P': 'DCE', 'L': 'DCE', 'V': 'DCE', 'PP': 'DCE', 'J': 'DCE', 'JM': 'DCE', 
                'I': 'DCE', 'JD': 'DCE', 'LH': 'DCE', 'EB': 'DCE', 'EG': 'DCE', 'PG': 'DCE', 'RR': 'DCE',
                'SR': 'CZCE', 'CF': 'CZCE', 'TA': 'CZCE', 'MA': 'CZCE', 'FG': 'CZCE', 
                'RM': 'CZCE', 'OI': 'CZCE', 'CY': 'CZCE', 'AP': 'CZCE', 'CJ': 'CZCE', 
                'UR': 'CZCE', 'SA': 'CZCE', 'PF': 'CZCE', 'PK': 'CZCE', 'SF': 'CZCE', 
                'SM': 'CZCE', 'ZC': 'CZCE', 'RS': 'CZCE', 'PX': 'CZCE', 'PR': 'CZCE', 
                'SH': 'CZCE', 'PL': 'CZCE', 'JR': 'CZCE', 'LR': 'CZCE', 'WH': 'CZCE', 
                'PM': 'CZCE', 'RI': 'CZCE', 'LG': 'CZCE',
                'SC': 'INE', 'LU': 'INE', 'NR': 'INE', 'BC': 'INE', 'EC': 'INE',
                'LC': 'GFEX', 'SI': 'GFEX', 'SP': 'GFEX', 'SS': 'GFEX', 'AD': 'GFEX', 
                'OP': 'GFEX', 'PS': 'GFEX', 'BR': 'GFEX'
            }
            
            exchange = VARIETY_TO_EXCHANGE.get(symbol)
            if exchange:
                # 计算日期范围（最近10天）
                from datetime import datetime, timedelta
                end = datetime.now()
                start = start_date if start_date else (end - timedelta(days=10))
                start_str = start.strftime('%Y%m%d')
                end_str = end.strftime('%Y%m%d')
                
                df = ak.get_futures_daily(start_date=start_str, end_date=end_str, market=exchange)
                
                if df is not None and not df.empty:
                    # 筛选该品种的数据
                    if 'variety' in df.columns:
                        df_variety = df[df['variety'] == symbol].copy()
                        if not df_variety.empty:
                            print(f"    ✅ get_futures_daily成功: {len(df_variety)} 条记录")
                            processed_df = self._process_get_futures_daily_data(df_variety, symbol, start_date)
                            if not processed_df.empty:
                                return processed_df
                print(f"    ⚠️ get_futures_daily: 无该品种数据")
            else:
                print(f"    ⚠️ 未找到品种对应的交易所")
                
        except Exception as e:
            print(f"    ⚠️ get_futures_daily失败: {str(e)[:50]}")
        
        # 方法5: 对于某些品种，尝试按品种调用futures_main_sina（带日期参数）
        # 包括：大商所品种 + 广期所的SP/SS + 部分郑商所小众品种（CJ/LG）
        if symbol in ['A', 'B', 'C', 'CS', 'M', 'Y', 'P', 'L', 'V', 'PP', 'J', 'JM', 'I', 'JD', 'LH', 'EB', 'EG', 'PG', 'RR', 'SP', 'SS', 'CJ', 'LG']:
            try:
                print(f"    📡 方法5: futures_main_sina({symbol}0, 带日期)")
                from datetime import datetime, timedelta
                end = datetime.now()
                start = start_date if start_date else (end - timedelta(days=10))
                start_str = start.strftime('%Y%m%d')
                end_str = end.strftime('%Y%m%d')
                
                df = ak.futures_main_sina(symbol=f"{symbol}0", start_date=start_str, end_date=end_str)
                
                if df is not None and not df.empty:
                    print(f"    ✅ futures_main_sina(带日期)成功: {len(df)} 条记录")
                    processed_df = self._process_sina_main_data(df, symbol, start_date)
                    if not processed_df.empty:
                        return processed_df
                        
            except Exception as e:
                print(f"    ⚠️ futures_main_sina(带日期)失败: {str(e)[:50]}")
        
        print(f"    ❌ 所有接口都失败")
        return None
    
    def _process_em_data(self, df: pd.DataFrame, symbol: str, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """处理东方财富数据"""
        try:
            print(f"    🔧 处理东方财富数据...")
            
            # 标准化列名 - 东方财富返回的列名
            column_mapping = {
                '时间': '时间', '开盘': '开盘', '收盘': '收盘',
                '最高': '最高', '最低': '最低', '成交量': '成交量',
                '成交额': '成交额', '持仓量': '持仓量',
                '涨跌': '涨跌', '涨跌幅': '涨跌幅'
            }
            
            # 确保数据是DataFrame格式
            if not isinstance(df, pd.DataFrame):
                print(f"    ❌ 数据不是DataFrame格式: {type(df)}")
                return pd.DataFrame()
            
            # 处理日期格式
            if '时间' not in df.columns:
                print(f"    ❌ 未找到时间列，可用列: {list(df.columns)}")
                return pd.DataFrame()
            
            try:
                df['时间'] = pd.to_datetime(df['时间'])
            except Exception as time_error:
                print(f"    ❌ 时间格式转换失败: {time_error}")
                return pd.DataFrame()
            
            # 如果指定了开始日期，过滤数据
            if start_date:
                df = df[df['时间'] > start_date]
            
            if df.empty:
                print(f"    ℹ️ 无新数据需要更新")
                return pd.DataFrame()
            
            # 排序并重置索引
            df = df.sort_values('时间').reset_index(drop=True)
            
            print(f"    ✅ 东方财富数据处理完成: {len(df)} 条记录")
            if len(df) > 0:
                print(f"    📅 日期范围: {df['时间'].min().strftime('%Y-%m-%d')} ~ {df['时间'].max().strftime('%Y-%m-%d')}")
            
            return df
            
        except Exception as e:
            print(f"    ❌ 东方财富数据处理失败: {e}")
            return pd.DataFrame()
    
    def _process_sina_daily_data(self, df: pd.DataFrame, symbol: str, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """处理新浪日线数据"""
        try:
            print(f"    🔧 处理新浪日线数据...")
            
            # 处理日期（通常在索引中）
            if hasattr(df.index, 'to_series'):
                df = df.reset_index()
                df['时间'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'], errors='coerce')
            
            # 标准化列名
            column_mapping = {
                'date': '时间', 'open': '开盘', 'high': '最高', 'low': '最低', 
                'close': '收盘', 'volume': '成交量', 'hold': '持仓量'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # 确保时间格式
            if '时间' not in df.columns:
                # 尝试其他可能的时间列名
                time_cols = [col for col in df.columns if any(name in col.lower() for name in ['time', 'date', '时间', '日期'])]
                if time_cols:
                    df = df.rename(columns={time_cols[0]: '时间'})
                else:
                    print(f"    ❌ 未找到时间列")
                    return pd.DataFrame()
            
            try:
                df['时间'] = pd.to_datetime(df['时间'])
            except Exception as time_error:
                print(f"    ❌ 时间格式转换失败: {time_error}")
                return pd.DataFrame()
            
            # 如果指定了开始日期，过滤数据
            if start_date:
                df = df[df['时间'] > start_date]
            
            if df.empty:
                print(f"    ℹ️ 无新数据需要更新")
                return pd.DataFrame()
            
            # 排序并重置索引
            df = df.sort_values('时间').reset_index(drop=True)
            
            print(f"    ✅ 新浪日线数据处理完成: {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"    ❌ 新浪日线数据处理失败: {e}")
            return pd.DataFrame()
    
    def _process_sina_main_data(self, df: pd.DataFrame, symbol: str, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """处理新浪主力合约数据"""
        try:
            print(f"    🔧 处理新浪主力数据...")
            
            # 标准化列名
            column_mapping = {
                '日期': '时间', 'Date': '时间', 'date': '时间',
                '开盘价': '开盘', 'Open': '开盘', 'open': '开盘',
                '最高价': '最高', 'High': '最高', 'high': '最高',
                '最低价': '最低', 'Low': '最低', 'low': '最低',
                '收盘价': '收盘', 'Close': '收盘', 'close': '收盘',
                '成交量': '成交量', 'Volume': '成交量', 'volume': '成交量',
                '持仓量': '持仓量', 'OpenInterest': '持仓量', 'open_interest': '持仓量'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # 处理日期
            if '时间' not in df.columns:
                # 尝试从索引获取日期
                if hasattr(df.index, 'to_series'):
                    df = df.reset_index()
                    df['时间'] = pd.to_datetime(df.index, errors='coerce')
                else:
                    print(f"    ❌ 无法找到时间列")
                    return pd.DataFrame()
            
            df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
            df = df.dropna(subset=['时间'])
            
            if start_date:
                df = df[df['时间'] > start_date]
            
            if df.empty:
                print(f"    ℹ️ 无新数据需要更新")
                return pd.DataFrame()
            
            df = df.sort_values('时间').reset_index(drop=True)
            
            print(f"    ✅ 新浪主力数据处理完成: {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"    ❌ 新浪主力数据处理失败: {e}")
            return pd.DataFrame()
    
    def _process_get_futures_daily_data(self, df: pd.DataFrame, symbol: str, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """处理get_futures_daily返回的数据"""
        try:
            print(f"    🔧 处理get_futures_daily数据...")
            
            # get_futures_daily返回的是多个合约的数据，需要聚合成主力合约
            # 按日期分组，选择成交量最大的合约作为当日主力
            if '时间' not in df.columns and 'date' in df.columns:
                # 转换日期格式
                if df['date'].dtype in ['int64', 'float64', 'int32']:
                    df['时间'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
                else:
                    df['时间'] = pd.to_datetime(df['date'], errors='coerce')
            elif '时间' not in df.columns:
                print(f"    ❌ 未找到日期列")
                return pd.DataFrame()
            
            # 确保数值列是数值类型
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'open_interest']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按日期分组，选择成交量最大的合约
            result_data = []
            for date, group in df.groupby('时间'):
                # 选择成交量最大的记录
                if 'volume' in group.columns:
                    main_contract = group.loc[group['volume'].idxmax()]
                else:
                    main_contract = group.iloc[0]
                result_data.append(main_contract)
            
            if not result_data:
                print(f"    ℹ️ 无有效数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(result_data)
            
            # 标准化列名
            column_mapping = {
                'open': '开盘', 'high': '最高', 'low': '最低', 
                'close': '收盘', 'volume': '成交量', 'open_interest': '持仓量'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # 确保时间格式
            df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
            df = df.dropna(subset=['时间'])
            
            # 如果指定了开始日期，过滤数据
            if start_date:
                df = df[df['时间'] > start_date]
            
            if df.empty:
                print(f"    ℹ️ 无新数据需要更新")
                return pd.DataFrame()
            
            # 排序并重置索引
            df = df.sort_values('时间').reset_index(drop=True)
            
            print(f"    ✅ get_futures_daily数据处理完成: {len(df)} 条记录")
            if len(df) > 0:
                print(f"    📅 日期范围: {df['时间'].min().strftime('%Y-%m-%d')} ~ {df['时间'].max().strftime('%Y-%m-%d')}")
            
            return df
            
        except Exception as e:
            print(f"    ❌ get_futures_daily数据处理失败: {e}")
            return pd.DataFrame()
    
    def _process_general_data(self, df: pd.DataFrame, symbol: str, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """处理通用期货数据"""
        try:
            print(f"    🔧 处理通用期货数据...")
            
            # 标准化列名
            column_mapping = {
                'date': '时间', 'trade_date': '时间',
                'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘',
                'volume': '成交量', 'open_interest': '持仓量'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            if '时间' not in df.columns:
                print(f"    ❌ 无法找到时间列")
                return pd.DataFrame()
            
            df['时间'] = pd.to_datetime(df['时间'], errors='coerce')
            df = df.dropna(subset=['时间'])
            
            if start_date:
                df = df[df['时间'] > start_date]
            
            if df.empty:
                print(f"    ℹ️ 无新数据需要更新")
                return pd.DataFrame()
            
            df = df.sort_values('时间').reset_index(drop=True)
            
            print(f"    ✅ 通用数据处理完成: {len(df)} 条记录")
            return df
            
        except Exception as e:
            print(f"    ❌ 通用数据处理失败: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标 - 安全版本，避免数据类型错误
        
        Args:
            df: OHLC数据
        
        Returns:
            带技术指标的数据
        """
        try:
            print("      🔧 开始安全指标计算...")
            
            # 确保数据按时间排序
            df = df.sort_values('时间').reset_index(drop=True)
            
            # 强制数据类型转换和清理
            close = pd.to_numeric(df["收盘"], errors='coerce')
            high = pd.to_numeric(df["最高"], errors='coerce') 
            low = pd.to_numeric(df["最低"], errors='coerce')
            open_ = pd.to_numeric(df.get("开盘", close), errors='coerce')
            volume = pd.to_numeric(df.get("成交量", pd.Series(0, index=close.index)), errors='coerce')
            
            # 使用前向填充处理NaN，然后用0填充剩余的NaN
            close = close.ffill().bfill().fillna(0)
            high = high.ffill().bfill().fillna(0)
            low = low.ffill().bfill().fillna(0) 
            open_ = open_.ffill().bfill().fillna(0)
            volume = volume.fillna(0)
            
            # 确保价格逻辑正确
            high = np.maximum(high, np.maximum(open_, close))
            low = np.minimum(low, np.minimum(open_, close))
            
            print("        ✅ 数据预处理完成")
            
            # ========== 基础指标 ==========
            
            # 移动平均线
            df["MA5"] = close.rolling(5, min_periods=1).mean()
            df["MA10"] = close.rolling(10, min_periods=1).mean()
            df["MA20"] = close.rolling(20, min_periods=1).mean()
            df["MA60"] = close.rolling(60, min_periods=1).mean()
            df["EMA20"] = close.ewm(span=20, adjust=False, min_periods=1).mean()
            
            # ATR
            tr1 = (high - low).abs()
            tr2 = (high - close.shift(1)).abs().fillna(0)
            tr3 = (low - close.shift(1)).abs().fillna(0)
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["ATR14"] = tr.rolling(14, min_periods=1).mean()
            
            # RSI
            delta = close.diff().fillna(0)
            gain = delta.where(delta > 0, 0).rolling(14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
            rs = gain / loss.replace(0, 1e-10)  # 避免除零
            df["RSI14"] = 100 - (100 / (1 + rs))
            
            # MACD
            ema12 = close.ewm(span=12, adjust=False, min_periods=1).mean()
            ema26 = close.ewm(span=26, adjust=False, min_periods=1).mean()
            df["MACD"] = ema12 - ema26
            df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False, min_periods=1).mean()
            df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
            
            # 布林带
            ma20 = df["MA20"]
            std20 = close.rolling(20, min_periods=1).std().fillna(0)
            df["BOLL_UP"] = ma20 + 2 * std20
            df["BOLL_LOW"] = ma20 - 2 * std20
            df["BOLL_MID"] = ma20
            df["BOLL_WIDTH"] = df["BOLL_UP"] - df["BOLL_LOW"]
            
            print("        ✅ 基础指标完成")
            
            # ========== 高级指标 ==========
            
            # KDJ
            n = 9
            llv_n = low.rolling(n, min_periods=1).min()
            hhv_n = high.rolling(n, min_periods=1).max()
            rsv = 100 * (close - llv_n) / (hhv_n - llv_n).replace(0, 1e-10)
            k = rsv.ewm(alpha=1/3, adjust=False, min_periods=1).mean()
            d = k.ewm(alpha=1/3, adjust=False, min_periods=1).mean()
            j = 3 * k - 2 * d
            df["KDJ_K"] = k
            df["KDJ_D"] = d
            df["KDJ_J"] = j
            
            # Williams %R
            hhv14 = high.rolling(14, min_periods=1).max()
            llv14 = low.rolling(14, min_periods=1).min()
            df["WILLIAMS_R14"] = -100 * (hhv14 - close) / (hhv14 - llv14).replace(0, 1e-10)
            
            # CCI - 简化版本
            tp = (high + low + close) / 3
            sma = tp.rolling(20, min_periods=1).mean()
            std = tp.rolling(20, min_periods=1).std().fillna(1)
            df["CCI20"] = (tp - sma) / (0.02 * std)
            
            # Stochastic RSI
            rsi = df["RSI14"]
            stoch_rsi = 100 * (rsi - rsi.rolling(14, min_periods=1).min()) / (
                rsi.rolling(14, min_periods=1).max() - rsi.rolling(14, min_periods=1).min()
            ).replace(0, 1e-10)
            df["STOCH_RSI"] = stoch_rsi
            
            print("        ✅ 高级指标完成")
            
            # ========== 成交量指标 ==========
            
            df["VOL_MA20"] = volume.rolling(20, min_periods=1).mean()
            price_change = close.diff().fillna(0)
            sign = pd.Series(np.where(price_change > 0, 1, np.where(price_change < 0, -1, 0)), index=close.index)
            df["OBV"] = (sign * volume).cumsum()
            
            print("        ✅ 成交量指标完成")
            
            # ========== 持仓量指标 ==========
            
            if "持仓量" in df.columns:
                oi = pd.to_numeric(df["持仓量"], errors='coerce').fillna(0)
                
                df["OI_MA20"] = oi.rolling(20, min_periods=1).mean()
                df["OI_CHANGE"] = oi.diff().fillna(0)
                df["OI_CHANGE_PCT"] = oi.pct_change().fillna(0) * 100
                
                print("        ✅ 持仓量指标完成")
            
            # 统计指标数量
            original_cols = ['时间', '开盘', '最高', '最低', '收盘', '成交量', '持仓量']
            indicator_cols = [col for col in df.columns if col not in original_cols]
            
            print(f"      ✅ 安全指标计算完成: {len(indicator_cols)} 个指标")
            
            return df
            
        except Exception as e:
            print(f"      ❌ 技术指标计算失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return df
    
    def save_variety_data(self, symbol: str, new_data: pd.DataFrame, existing_info: Optional[Dict] = None) -> bool:
        """
        保存品种数据
        
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
            
            ohlc_file = variety_dir / "ohlc_data.csv"
            
            if existing_info and ohlc_file.exists():
                # 读取现有数据
                existing_df = pd.read_csv(ohlc_file)
                existing_df['时间'] = pd.to_datetime(existing_df['时间'])
                
                # 合并数据
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['时间']).sort_values('时间').reset_index(drop=True)
                
                new_records = len(combined_df) - len(existing_df)
                if new_records > 0:
                    print(f"    ✅ {symbol}: 新增 {new_records} 条记录")
                    self.update_stats["updated_varieties"].append(symbol)
                    self.update_stats["total_new_records"] += new_records
                else:
                    print(f"    ℹ️ {symbol}: 无新数据")
                    self.update_stats["skipped_varieties"].append(symbol)
                    return True
            else:
                # 新品种或无现有数据
                combined_df = new_data
                print(f"    ✅ {symbol}: 创建 {len(new_data)} 条记录")
                self.update_stats["new_varieties"].append(symbol)
                self.update_stats["total_new_records"] += len(new_data)
            
            # 重新计算技术指标（基于完整数据）
            combined_df = self.calculate_technical_indicators(combined_df)
            
            # 保存数据
            combined_df.to_csv(ohlc_file, index=False, encoding='utf-8')
            
            # 另外保存技术指标数据
            tech_file = variety_dir / "technical_indicators.csv"
            # 排除基础OHLC列和无用的原始数据列
            excluded_cols = [
                '时间', '开盘', '最高', '最低', '收盘', '成交量', '持仓量',
                'date', 'symbol', 'pre_settle', 'settle', 'turnover', 'index',
                '涨跌', '涨跌幅', '成交额', 'variety', 'open', 'high', 'low', 'close', 'volume', 'open_interest'
            ]
            tech_columns = [col for col in combined_df.columns if col not in excluded_cols]
            
            if tech_columns:
                tech_df = combined_df[['时间'] + tech_columns]
                tech_df.to_csv(tech_file, index=False, encoding='utf-8')
            
            # 保存主要指标数据（OHLC + 常用核心指标）
            main_file = variety_dir / "main_indicators.csv"
            main_indicator_columns = [
                'MA5', 'MA10', 'MA20', 'MA60',  # 均线
                'MACD', 'MACD_SIGNAL', 'MACD_HIST',  # MACD
                'RSI14',  # RSI
                'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER',  # 布林带
                'ATR14', 'CCI20',  # ATR和CCI
                'VOL_MA20', 'OBV',  # 成交量指标
                'OI_MA20', 'OI_CHANGE', 'OI_CHANGE_PCT'  # 持仓量指标
            ]
            
            # 选择存在的列
            available_main_cols = [col for col in main_indicator_columns if col in combined_df.columns]
            base_cols = ['时间', '开盘', '最高', '最低', '收盘', '成交量']
            if '持仓量' in combined_df.columns:
                base_cols.append('持仓量')
            
            main_df = combined_df[base_cols + available_main_cols]
            main_df.to_csv(main_file, index=False, encoding='utf-8')
            
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
        print(f"🚀 技术分析数据更新器")
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
        existing_varieties, variety_info = self.get_existing_data_status()
        
        # 确定要更新的品种
        if specific_varieties:
            target_symbols = [s for s in specific_varieties if s.upper() in SYMBOL_MAPPING]
            print(f"🎯 指定更新品种: {len(target_symbols)} 个")
        else:
            target_symbols = list(SYMBOL_MAPPING.keys())
            print(f"🎯 全品种更新: {len(target_symbols)} 个")
        
        # 执行更新
        processed_count = 0
        
        for i, symbol in enumerate(target_symbols):
            print(f"\n[{i+1}/{len(target_symbols)}] 处理品种: {symbol}")
            
            contract_name = SYMBOL_MAPPING[symbol]
            existing_info = variety_info.get(symbol)
            
            # 确定起始日期（用于增量更新）
            start_date = None
            if existing_info:
                latest_date = existing_info["latest_date"]
                days_gap = (target_date.date() - latest_date.date()).days
                
                if days_gap <= 1:
                    print(f"    ℹ️ 数据已是最新 (最新: {latest_date.strftime('%Y-%m-%d')})")
                    self.update_stats["skipped_varieties"].append(symbol)
                    continue
                
                print(f"    📅 最新数据: {latest_date.strftime('%Y-%m-%d')}, 缺口: {days_gap}天")
                start_date = latest_date
            else:
                print(f"    🆕 新品种，将创建完整数据")
            
            # 获取数据
            new_data = self.fetch_ohlc_data(symbol, contract_name, start_date)
            
            if new_data is None:
                print(f"    ❌ {symbol}: 数据获取失败")
                self.update_stats["failed_varieties"].append(symbol)
                continue
            
            if new_data.empty:
                print(f"    ℹ️ {symbol}: 无新数据")
                self.update_stats["skipped_varieties"].append(symbol)
                continue
            
            # 保存数据
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
    print("📊 技术分析数据更新器")
    print("=" * 80)
    
    updater = TechnicalDataUpdater()
    
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
    print(f"   更新模式: 智能增量更新（自动从最新数据补全到目标日期）")
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
