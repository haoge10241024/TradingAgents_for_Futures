#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓数据更新器
基于comprehensive_positioning_data_system的逻辑，支持多数据源和增量更新
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

# 品种名称映射
SYMBOL_NAMES = {
    'A': '豆一', 'AG': '白银', 'AL': '铝', 'AU': '黄金', 'B': '豆二',
    'BU': '沥青', 'C': '玉米', 'CF': '棉花', 'CU': '铜', 'CY': '棉纱',
    'EB': '苯乙烯', 'EG': '乙二醇', 'FG': '玻璃', 'FU': '燃油', 'HC': '热卷',
    'I': '铁矿石', 'J': '焦炭', 'JD': '鸡蛋', 'JM': '焦煤', 'L': '聚乙烯',
    'LC': '碳酸锂', 'LH': '生猪', 'LU': '低硫燃料油', 'M': '豆粕', 'MA': '甲醇',
    'NI': '镍', 'NR': '20号胶', 'OI': '菜籽油', 'P': '棕榈油', 'PB': '铅',
    'PF': '短纤', 'PG': '液化石油气', 'PP': '聚丙烯', 'PR': '瓶片', 'PS': '多晶硅',
    'PX': '对二甲苯', 'RB': '螺纹钢', 'RM': '菜籽粕', 'RU': '天然橡胶', 'SA': '纯碱',
    'SF': '硅铁', 'SI': '工业硅', 'SM': '锰硅', 'SN': '锡', 'SP': '纸浆',
    'SR': '白糖', 'SS': '不锈钢', 'TA': 'PTA', 'UR': '尿素', 'V': 'PVC',
    'Y': '豆油', 'ZN': '锌'
}

class PositioningDataUpdater:
    """持仓数据更新器"""
    
    def __init__(self, database_path: str = "D:/Cursor/cursor项目/TradingAgent/qihuo/database/positioning"):
        """
        初始化持仓数据更新器
        
        Args:
            database_path: 数据库路径
        """
        self.database_path = Path(database_path)
        self.database_path.mkdir(parents=True, exist_ok=True)
        
        self.update_stats = {
            "start_time": None,
            "end_time": None,
            "target_date": None,
            "lookback_days": 0,
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
        print("🔍 检查现有持仓数据状态...")
        
        varieties = []
        variety_info = {}
        
        if not self.database_path.exists():
            return [], {}
        
        variety_folders = [d for d in self.database_path.iterdir() if d.is_dir()]
        print(f"📂 发现 {len(variety_folders)} 个品种文件夹")
        
        for folder in variety_folders:
            variety = folder.name
            
            # 检查各类持仓数据文件
            files_info = {
                "long_position_ranking.csv": None,
                "short_position_ranking.csv": None,
                "volume_ranking.csv": None,
                "positioning_summary.json": None
            }
            
            has_data = False
            total_records = 0
            date_range = {"earliest": None, "latest": None}
            
            for filename in files_info.keys():
                file_path = folder / filename
                if file_path.exists():
                    try:
                        if filename.endswith('.csv'):
                            df = pd.read_csv(file_path)
                            if len(df) > 0 and 'date' in df.columns:
                                df['date'] = pd.to_datetime(df['date'])
                                file_earliest = df['date'].min()
                                file_latest = df['date'].max()
                                file_records = len(df)
                                
                                files_info[filename] = {
                                    "records": file_records,
                                    "earliest": file_earliest,
                                    "latest": file_latest
                                }
                                
                                total_records += file_records
                                has_data = True
                                
                                # 更新品种整体日期范围
                                if date_range["earliest"] is None or file_earliest < date_range["earliest"]:
                                    date_range["earliest"] = file_earliest
                                if date_range["latest"] is None or file_latest > date_range["latest"]:
                                    date_range["latest"] = file_latest
                        
                        elif filename.endswith('.json'):
                            files_info[filename] = {"exists": True}
                            
                    except Exception as e:
                        files_info[filename] = {"error": str(e)[:50]}
            
            if has_data:
                variety_info[variety] = {
                    "files": files_info,
                    "total_records": total_records,
                    "date_range": date_range
                }
                varieties.append(variety)
                
                earliest_str = date_range["earliest"].strftime('%Y-%m-%d') if date_range["earliest"] else "无"
                latest_str = date_range["latest"].strftime('%Y-%m-%d') if date_range["latest"] else "无"
                print(f"  {variety}: {total_records} 条记录 ({earliest_str} ~ {latest_str})")
        
        print(f"\n📊 总计: {len(varieties)} 个有效品种")
        return varieties, variety_info
    
    def generate_trading_dates(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        生成交易日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            交易日列表 (YYYYMMDD格式)
        """
        dates = []
        current = start_date
        
        while current <= end_date:
            # 简单的工作日判断（不考虑节假日）
            if current.weekday() < 5:
                dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        
        return dates
    
    def get_dominant_contracts(self, symbol: str, start_date: datetime, end_date: datetime) -> Dict[str, str]:
        """
        获取主力合约信息（模拟实现）
        
        Args:
            symbol: 品种代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            日期到主力合约的映射
        """
        # 简化实现：生成当前年份的主要合约月份
        current_year = datetime.now().year
        year_suffix = str(current_year)[-2:]
        
        # 常见的主力合约月份
        main_months = ['01', '03', '05', '07', '09', '11']
        
        # 构造主力合约代码
        contracts = [f"{symbol.lower()}{year_suffix}{month}" for month in main_months]
        
        # 为每个交易日分配主力合约（简化逻辑）
        trading_dates = self.generate_trading_dates(start_date, end_date)
        contract_map = {}
        
        for date_str in trading_dates:
            # 根据日期选择合约（简化逻辑）
            month = int(date_str[4:6])
            contract_index = min(month // 2, len(contracts) - 1)
            contract_map[date_str] = contracts[contract_index]
        
        return contract_map
    
    def fetch_positioning_data_by_contracts(self, dominant_contracts: Dict[str, Dict[str, str]], 
                                          start_date: datetime, target_date: datetime) -> Dict[str, List]:
        """
        基于主力合约获取持仓数据
        
        Args:
            dominant_contracts: {symbol: {date: contract}} 主力合约信息
            start_date: 开始日期
            target_date: 结束日期
        
        Returns:
            按品种分组的持仓数据
        """
        print(f"    📡 基于主力合约获取持仓数据...")
        print(f"    📅 数据时间范围: {start_date.strftime('%Y-%m-%d')} ~ {target_date.strftime('%Y-%m-%d')}")
        
        # 生成交易日列表
        trading_dates = self.generate_trading_dates(start_date, target_date)
        print(f"    📅 交易日数量: {len(trading_dates)} 天")
        
        # 持仓数据类型
        position_types = ["成交量", "多单持仓", "空单持仓"]
        
        all_positioning_data = {}  # {symbol: [data_list]}
        total_requests = 0
        successful_requests = 0
        
        for symbol, contracts_dict in dominant_contracts.items():
            print(f"\n    🔍 处理品种: {symbol} ({SYMBOL_NAMES.get(symbol, symbol)})")
            
            symbol_data = []
            symbol_requests = 0
            symbol_success = 0
            
            for date_str in trading_dates:
                if date_str not in contracts_dict:
                    continue
                
                contract = contracts_dict[date_str]
                print(f"      📅 {date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} | {contract}", end=" ")
                
                daily_success = 0
                
                # 获取三种类型的持仓数据
                for position_type in position_types:
                    try:
                        df = ak.futures_hold_pos_sina(
                            symbol=position_type, 
                            contract=contract, 
                            date=date_str
                        )
                        
                        symbol_requests += 1
                        total_requests += 1
                        
                        if df is not None and not df.empty:
                            # 添加元数据
                            df = df.copy()
                            df['date'] = date_str
                            df['contract'] = contract
                            df['position_type'] = position_type
                            df['symbol'] = symbol
                            
                            # 标准化列名
                            if len(df.columns) >= 4:
                                if position_type == "多单持仓":
                                    df.columns = ['排名', '会员简称', '持仓量', '比上交易增减', 'date', 'contract', 'position_type', 'symbol']
                                elif position_type == "空单持仓":
                                    df.columns = ['排名', '会员简称', '持仓量', '比上交易增减', 'date', 'contract', 'position_type', 'symbol']
                                elif position_type == "成交量":
                                    df.columns = ['排名', '会员简称', '成交量', '比上交易增减', 'date', 'contract', 'position_type', 'symbol']
                            
                            symbol_data.append(df)
                            symbol_success += 1
                            successful_requests += 1
                            daily_success += 1
                        
                        # 避免请求过快
                        time.sleep(random.uniform(0.5, 1.0))
                        
                    except Exception as e:
                        print(f"❌{position_type[:2]}", end="")
                        continue
                
                if daily_success > 0:
                    print(f" ✅({daily_success}/3)")
                else:
                    print(" ❌")
            
            if symbol_data:
                all_positioning_data[symbol] = symbol_data
                success_rate = symbol_success / symbol_requests * 100 if symbol_requests > 0 else 0
                print(f"      ✅ {symbol}: 获取 {len(symbol_data)} 批数据 (成功率: {success_rate:.1f}%)")
            else:
                print(f"      ❌ {symbol}: 未获取到任何数据")
        
        overall_success_rate = successful_requests / total_requests * 100 if total_requests > 0 else 0
        print(f"    📊 总体统计: {successful_requests}/{total_requests} 请求成功 (成功率: {overall_success_rate:.1f}%)")
        
        return all_positioning_data
    
    def load_dominant_contracts_from_basis(self, start_date: datetime, target_date: datetime) -> Dict[str, Dict[str, str]]:
        """
        从基差数据中提取各品种的主力合约信息
        
        Args:
            start_date: 开始日期
            target_date: 结束日期
            
        Returns:
            {symbol: {date: contract}} 主力合约信息
        """
        print(f"    📖 从基差数据中提取主力合约信息...")
        
        # 基差数据目录
        basis_root = self.database_path.parent / "basis"
        
        dominant_contracts = {}
        
        for symbol in SYMBOL_NAMES.keys():
            basis_file = basis_root / symbol / "basis_data.csv"
            
            if not basis_file.exists():
                print(f"      ⚠️ {symbol}: 基差数据文件不存在")
                continue
            
            try:
                df = pd.read_csv(basis_file)
                
                if 'date' not in df.columns or 'dominant_contract' not in df.columns:
                    print(f"      ⚠️ {symbol}: 基差数据格式不正确")
                    continue
                
                # 转换日期格式
                df['date'] = pd.to_datetime(df['date'])
                
                # 筛选时间范围
                mask = (df['date'] >= start_date) & (df['date'] <= target_date)
                filtered_df = df[mask].copy()
                
                if len(filtered_df) == 0:
                    print(f"      ⚠️ {symbol}: 指定时间范围内无基差数据")
                    continue
                
                # 提取主力合约信息
                contracts_dict = {}
                for _, row in filtered_df.iterrows():
                    date_str = row['date'].strftime('%Y%m%d')
                    contract = str(row['dominant_contract']).strip()
                    if contract and contract != 'nan':
                        # 修复合约代码格式：3位数字的合约需要在英文后补2
                        # 例如：CY511 -> CY2511
                        if len(contract) >= 5:  # 至少要有字母+数字
                            # 找到字母和数字的分界点
                            alpha_part = ""
                            num_part = ""
                            for i, char in enumerate(contract):
                                if char.isalpha():
                                    alpha_part += char
                                elif char.isdigit():
                                    num_part = contract[i:]
                                    break
                            
                            # 如果数字部分是3位，在前面补2
                            if len(num_part) == 3 and num_part.isdigit():
                                contract = alpha_part + "2" + num_part
                                print(f"        🔧 修正合约代码: {row['dominant_contract']} -> {contract}")
                        
                        contracts_dict[date_str] = contract
                
                dominant_contracts[symbol] = contracts_dict
                print(f"      ✅ {symbol}: 提取了 {len(contracts_dict)} 个交易日的主力合约")
                
            except Exception as e:
                print(f"      ❌ {symbol}: 处理基差数据失败 - {str(e)[:50]}")
                continue
        
        print(f"    ✅ 主力合约信息提取完成，共 {len(dominant_contracts)} 个品种")
        return dominant_contracts
    
    def _extract_symbol_from_contract(self, contract: str) -> str:
        """从合约代码中提取品种代码"""
        import re
        
        # 移除数字，保留字母
        symbol = re.sub(r'\d+', '', str(contract).upper())
        
        # 处理特殊情况
        if symbol in ['IF', 'IH', 'IC', 'IM', 'TS', 'TF', 'T']:  # 中金所品种
            return symbol
        elif len(symbol) >= 1:
            return symbol
        else:
            return str(contract)[:2].upper()
    
    def _process_contract_positioning_data(self, contract_data: pd.DataFrame, 
                                         contract: str, symbol: str, date_str: str,
                                         exchange_name: str, all_data: Dict):
        """处理单个合约的持仓数据"""
        
        # 不同交易所的列名映射
        column_mappings = {
            "中金所": {
                "long_party_name": "会员简称",
                "long_open_interest": "持仓量", 
                "long_open_interest_chg": "比上交易增减",
                "short_party_name": "会员简称",
                "short_open_interest": "持仓量",
                "short_open_interest_chg": "比上交易增减",
                "vol_party_name": "会员简称",
                "vol": "成交量",
                "vol_chg": "比上交易增减"
            },
            "郑商所": {
                "long_party_name": "会员简称",
                "long_open_interest": "持仓量",
                "long_open_interest_chg": "比上交易增减", 
                "short_party_name": "会员简称",
                "short_open_interest": "持仓量",
                "short_open_interest_chg": "比上交易增减",
                "vol_party_name": "会员简称",
                "vol": "成交量"
            },
            "上期所": {
                "long_party_name": "会员简称",
                "long_open_interest": "持仓量",
                "long_open_interest_chg": "比上交易增减",
                "short_party_name": "会员简称", 
                "short_open_interest": "持仓量",
                "short_open_interest_chg": "比上交易增减",
                "vol_party_name": "会员简称",
                "vol": "成交量"
            },
            "广期所": {
                "long_party_name": "会员简称",
                "long_open_interest": "持仓量",
                "short_party_name": "会员简称",
                "short_open_interest": "持仓量", 
                "vol_party_name": "会员简称",
                "vol": "成交量"
            }
        }
        
        mapping = column_mappings.get(exchange_name, {})
        
        # 处理多头持仓
        if 'long_party_name' in contract_data.columns:
            for i, (_, row) in enumerate(contract_data.iterrows()):
                if i >= 20:  # 限制数量
                    break
                    
                all_data['long_positions'].append({
                    "排名": i + 1,
                    "会员简称": str(row.get('long_party_name', f'会员{i+1}')),
                    "持仓量": self._parse_int_with_comma(row.get('long_open_interest', 0)),
                    "比上交易增减": self._parse_int_with_comma(row.get('long_open_interest_chg', 0)),
                    "date": date_str,
                    "contract": contract,
                    "position_type": "多单持仓",
                    "symbol": symbol,
                    "exchange": exchange_name
                })
        
        # 处理空头持仓
        if 'short_party_name' in contract_data.columns:
            for i, (_, row) in enumerate(contract_data.iterrows()):
                if i >= 20:  # 限制数量
                    break
                    
                all_data['short_positions'].append({
                    "排名": i + 1,
                    "会员简称": str(row.get('short_party_name', f'会员{i+1}')),
                    "持仓量": self._parse_int_with_comma(row.get('short_open_interest', 0)),
                    "比上交易增减": self._parse_int_with_comma(row.get('short_open_interest_chg', 0)),
                    "date": date_str,
                    "contract": contract,
                    "position_type": "空单持仓", 
                    "symbol": symbol,
                    "exchange": exchange_name
                })
        
        # 处理成交量排名
        if 'vol_party_name' in contract_data.columns:
            for i, (_, row) in enumerate(contract_data.iterrows()):
                if i >= 20:  # 限制数量
                    break
                    
                all_data['volume_rankings'].append({
                    "排名": i + 1,
                    "会员简称": str(row.get('vol_party_name', f'会员{i+1}')),
                    "成交量": self._parse_int_with_comma(row.get('vol', 0)),
                    "比上交易增减": self._parse_int_with_comma(row.get('vol_chg', 0)),
                    "date": date_str,
                    "contract": contract,
                    "symbol": symbol,
                    "exchange": exchange_name
                })
    
    def _parse_int_with_comma(self, value):
        """解析可能包含逗号的数字字符串"""
        if value is None or value == '':
            return 0
        
        try:
            # 如果是数字，直接返回
            if isinstance(value, (int, float)):
                return int(value)
            
            # 如果是字符串，移除逗号后转换
            if isinstance(value, str):
                # 移除逗号和空格
                clean_value = value.replace(',', '').replace(' ', '').strip()
                if clean_value == '' or clean_value == '-':
                    return 0
                return int(float(clean_value))
            
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    def _fetch_dce_data_with_fallback(self, date: str):
        """
        大商所数据获取（多种备用策略）
        
        Args:
            date: 日期字符串 (YYYYMMDD)
            
        Returns:
            大商所持仓数据字典，格式与其他交易所一致
        """
        print(f"        🏢 大商所数据获取 (多策略)...")
        
        strategies = [
            {
                "name": "主接口",
                "func": ak.futures_dce_position_rank,
                "params": {"date": date}
            },
            {
                "name": "备用接口", 
                "func": ak.futures_dce_position_rank_other,
                "params": {"date": date}
            },
            {
                "name": "排名表接口",
                "func": ak.get_dce_rank_table,
                "params": {"date": date}
            }
        ]
        
        for strategy in strategies:
            try:
                print(f"          🔄 尝试{strategy['name']}...", end="")
                data = strategy['func'](**strategy['params'])
                
                if data and isinstance(data, dict) and len(data) > 0:
                    print(f" ✅ 成功 ({len(data)}个合约)")
                    return data
                else:
                    print(f" ❌ 无数据")
                    
            except Exception as e:
                print(f" ❌ 失败: {str(e)[:30]}...")
                continue
        
        # 如果所有策略都失败，记录问题并返回空字典
        print(f"        ⚠️ 大商所数据暂时无法获取，原因:")
        print(f"          - 主接口: 数据源可能存在问题")
        print(f"          - 备用接口: 网站结构可能已变化")
        print(f"          - 排名表接口: 接口可能已停用")
        print(f"        📝 建议: 大商所数据将在接口修复后自动恢复")
        
        # 返回空字典，与其他接口保持一致的格式
        return {}
    

    
    def save_positioning_data(self, symbol: str, all_data: List[pd.DataFrame]) -> Tuple[bool, int]:
        """
        保存单个品种的持仓数据
        
        Args:
            symbol: 品种代码
            all_data: 该品种的所有持仓数据列表
            
        Returns:
            (是否成功, 总记录数)
        """
        try:
            # 创建品种目录
            symbol_dir = self.database_path / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            
            # 持仓数据类型
            position_types = ["成交量", "多单持仓", "空单持仓"]
            
            total_records = 0
            
            # 按数据类型分别保存
            for position_type in position_types:
                type_data = [df for df in all_data if not df.empty and df.iloc[0]['position_type'] == position_type]
                
                if not type_data:
                    continue
                    
                # 合并同类型数据
                combined_df = pd.concat(type_data, ignore_index=True)
                
                # 转换日期格式
                combined_df['date'] = pd.to_datetime(combined_df['date'], format='%Y%m%d')
                
                # 按日期排序
                combined_df = combined_df.sort_values(['date', '排名']).reset_index(drop=True)
                
                # 保存文件
                filename_map = {
                    "成交量": "volume_ranking.csv",
                    "多单持仓": "long_position_ranking.csv", 
                    "空单持仓": "short_position_ranking.csv"
                }
                
                file_path = symbol_dir / filename_map[position_type]
                combined_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                total_records += len(combined_df)
                print(f"      💾 {position_type}: {len(combined_df)} 条记录已保存")
            
            # 保存汇总信息
            summary_data = {
                'symbol': symbol,
                'symbol_name': SYMBOL_NAMES.get(symbol, symbol),
                'total_records': total_records,
                'position_types': position_types,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            summary_file = symbol_dir / "positioning_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            return True, total_records
            
        except Exception as e:
            print(f"      ❌ 保存失败: {e}")
            return False, 0
    
    def save_variety_data(self, symbol: str, new_data: Dict, existing_info: Optional[Dict] = None) -> bool:
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
            variety_dir = self.database_path / symbol
            variety_dir.mkdir(parents=True, exist_ok=True)
            
            new_records_count = 0
            
            # 保存各类数据
            for data_type, file_name in [
                ("long_positions", "long_position_ranking.csv"),
                ("short_positions", "short_position_ranking.csv"),
                ("volume_rankings", "volume_ranking.csv")
            ]:
                if data_type not in new_data or not new_data[data_type]:
                    continue
                
                file_path = variety_dir / file_name
                new_df = pd.DataFrame(new_data[data_type])
                
                if file_path.exists():
                    # 合并数据
                    existing_df = pd.read_csv(file_path)
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    
                    # 去重
                    key_columns = ['date', 'contract'] + (['-name'] if '会员简称' in combined_df.columns else [])
                    if '会员简称' in combined_df.columns:
                        key_columns = ['date', 'contract', '会员简称']
                    combined_df = combined_df.drop_duplicates(subset=key_columns).reset_index(drop=True)
                    
                    new_records_count += len(combined_df) - len(existing_df)
                else:
                    # 新文件
                    combined_df = new_df
                    new_records_count += len(new_df)
                
                combined_df.to_csv(file_path, index=False, encoding='utf-8')
            
            # 保存摘要信息
            summary_file = variety_dir / "positioning_summary.json"
            summary_info = {
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol, symbol),
                "last_updated": datetime.now().isoformat(),
                "files": {
                    "long_position_ranking": len(new_data.get("long_positions", [])),
                    "short_position_ranking": len(new_data.get("short_positions", [])),
                    "volume_ranking": len(new_data.get("volume_rankings", []))
                }
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_info, f, ensure_ascii=False, indent=2)
            
            if new_records_count > 0:
                print(f"    ✅ {symbol}: 新增 {new_records_count} 条记录")
                self.update_stats["updated_varieties"].append(symbol)
                self.update_stats["total_new_records"] += new_records_count
            else:
                print(f"    ℹ️ {symbol}: 无新数据")
                self.update_stats["skipped_varieties"].append(symbol)
            
            return True
            
        except Exception as e:
            print(f"    ❌ {symbol}: 保存失败 - {str(e)}")
            self.update_stats["failed_varieties"].append(symbol)
            self.update_stats["error_messages"].append(f"{symbol}: 保存失败 - {str(e)}")
            return False
    
    def update_to_date(self, target_date_str: str, lookback_days: int = 5, specific_varieties: Optional[List[str]] = None) -> Dict:
        """
        更新数据到指定日期
        
        Args:
            target_date_str: 目标日期 (YYYY-MM-DD格式)
            lookback_days: 回望天数
            specific_varieties: 指定品种列表，None表示全部品种
        
        Returns:
            更新结果统计
        """
        print(f"🚀 持仓数据更新器")
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
        self.update_stats["lookback_days"] = lookback_days
        
        # 计算日期范围
        start_date = target_date - timedelta(days=lookback_days)
        
        print(f"📅 更新日期范围: {start_date.strftime('%Y-%m-%d')} ~ {target_date.strftime('%Y-%m-%d')}")
        print(f"📊 回望天数: {lookback_days}")
        
        # 获取现有数据状态
        existing_varieties, variety_info = self.get_existing_data_status()
        
        # 确定要更新的品种
        if specific_varieties:
            target_symbols = [s for s in specific_varieties if s.upper() in SYMBOL_NAMES]
            print(f"🎯 指定更新品种: {len(target_symbols)} 个")
        else:
            target_symbols = list(SYMBOL_NAMES.keys())
            print(f"🎯 全品种更新: {len(target_symbols)} 个")
        
        # 生成交易日期
        trading_dates = self.generate_trading_dates(start_date, target_date)
        print(f"📅 计划处理 {len(trading_dates)} 个交易日")
        
        # 执行更新 - 基于主力合约获取持仓数据
        processed_count = 0
        
        print(f"\n🔄 开始基于主力合约获取持仓数据...")
        
        # 1. 从基差数据中提取主力合约信息
        dominant_contracts = self.load_dominant_contracts_from_basis(start_date, target_date)
        
        if not dominant_contracts:
            print("❌ 无法获取主力合约信息，无法更新持仓数据")
            self.update_stats["end_time"] = datetime.now()
            return
        
        # 如果指定了品种，只处理指定品种
        if specific_varieties:
            filtered_contracts = {}
            for symbol in specific_varieties:
                if symbol in dominant_contracts:
                    filtered_contracts[symbol] = dominant_contracts[symbol]
            dominant_contracts = filtered_contracts
        
        if not dominant_contracts:
            print("❌ 指定的品种都没有主力合约信息")
            self.update_stats["end_time"] = datetime.now()
            return
        
        # 2. 基于主力合约获取持仓数据
        all_positioning_data = self.fetch_positioning_data_by_contracts(
            dominant_contracts, start_date, target_date
        )
        
        print(f"\n💾 开始保存品种数据...")
        
        # 3. 保存各品种数据
        for symbol, symbol_data in all_positioning_data.items():
            print(f"\n  处理品种: {symbol} ({SYMBOL_NAMES.get(symbol, symbol)})")
            
            if symbol_data:
                success, record_count = self.save_positioning_data(symbol, symbol_data)
                if success:
                    processed_count += 1
                    print(f"    ✅ {symbol}: 成功保存 {record_count} 条记录")
                    self.update_stats["updated_varieties"].append(symbol)
                else:
                    print(f"    ❌ {symbol}: 保存失败")
                    self.update_stats["failed_varieties"].append(symbol)
            else:
                print(f"    ❌ {symbol}: 无有效数据")
                self.update_stats["failed_varieties"].append(symbol)
        
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
    updater = PositioningDataUpdater()
    
    # 获取现有数据状态
    varieties, info = updater.get_existing_data_status()
    
    # 模拟更新前3个品种到今天
    target_date = datetime.now().strftime('%Y-%m-%d')
    test_varieties = ['RB', 'CU', 'AL'] if varieties else None
    
    result = updater.update_to_date(target_date, lookback_days=3, specific_varieties=test_varieties)
    
    print(f"\n🎯 更新结果: {result}")

if __name__ == "__main__":
    main()
