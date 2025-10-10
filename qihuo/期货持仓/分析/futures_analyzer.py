#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 核心分析模块
整合所有分析策略和数据获取功能
作者：7haoge
邮箱：953534947@qq.com
"""

import akshare as ak
import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Dict, List, Tuple, Optional, Any
import re

warnings.filterwarnings('ignore')

class FuturesDataManager:
    """期货数据管理器 - 负责数据获取和缓存"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.ensure_data_directory()
        
        # 交易所配置
        self.exchange_config = {
            "大商所": {
                "func": ak.futures_dce_position_rank,
                "filename": "大商所持仓.xlsx",
                "priority": 1
            },
            "中金所": {
                "func": ak.get_cffex_rank_table,
                "filename": "中金所持仓.xlsx",
                "priority": 2
            },
            "郑商所": {
                "func": ak.get_czce_rank_table,
                "filename": "郑商所持仓.xlsx",
                "priority": 3
            },
            "上期所": {
                "func": ak.get_shfe_rank_table,
                "filename": "上期所持仓.xlsx",
                "priority": 4
            },
            "广期所": {
                "func": ak.futures_gfex_position_rank,
                "filename": "广期所持仓.xlsx",
                "priority": 5
            }
        }
        
        # 期货行情交易所配置 - 包含所有交易所，增强超时处理
        self.price_exchanges = [
            {"market": "DCE", "name": "大商所"},
            {"market": "CFFEX", "name": "中金所"},
            {"market": "CZCE", "name": "郑商所"},
            {"market": "SHFE", "name": "上期所"},
            {"market": "GFEX", "name": "广期所"},  # 保留广期所，使用增强超时处理
        ]
    
    def ensure_data_directory(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def fetch_position_data(self, trade_date: str, progress_callback=None) -> bool:
        """
        获取持仓数据
        :param trade_date: 交易日期 YYYYMMDD
        :param progress_callback: 进度回调函数
        :return: 是否成功
        """
        success_count = 0
        total_exchanges = len(self.exchange_config)
        
        for i, (exchange_name, config) in enumerate(self.exchange_config.items()):
            try:
                if progress_callback:
                    progress_callback(f"正在获取{exchange_name}数据...", (i + 1) / total_exchanges * 0.6)
                
                # 获取数据
                data_dict = config["func"](date=trade_date)
                
                if data_dict:
                    # 保存到Excel
                    save_path = os.path.join(self.data_dir, config['filename'])
                    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                        for sheet_name, df in data_dict.items():
                            # 清理sheet名称
                            clean_name = sheet_name[:31].replace("/", "-").replace("*", "")
                            df.to_excel(writer, sheet_name=clean_name, index=False)
                    
                    success_count += 1
                    
            except Exception as e:
                print(f"获取{exchange_name}数据失败: {str(e)}")
                continue
        
        if progress_callback:
            progress_callback("持仓数据获取完成", 0.6)
        
        return success_count > 0
    
    def fetch_price_data(self, trade_date: str, progress_callback=None) -> pd.DataFrame:
        """
        获取期货行情数据，包含智能自动跳过功能
        :param trade_date: 交易日期 YYYYMMDD
        :param progress_callback: 进度回调函数
        :return: 合并后的价格数据
        """
        all_data = []
        success_count = 0
        
        # 使用所有配置的交易所，包含增强的超时处理
        for i, exchange in enumerate(self.price_exchanges):
            try:
                if progress_callback:
                    progress_callback(f"正在获取{exchange['name']}行情数据...", 0.6 + (i / len(self.price_exchanges)) * 0.2)
                
                # 记录开始时间
                start_time = time.time()
                
                # 对广期所使用增强的超时控制
                if exchange['name'] == '广期所':
                    print("⚠️ 广期所行情数据获取中，如遇问题将自动跳过...")
                    
                    try:
                        # 使用线程和严格超时控制
                        import threading
                        import queue
                        
                        result_queue = queue.Queue()
                        
                        def fetch_gfex_data():
                            try:
                                result = ak.get_futures_daily(
                                    start_date=trade_date, 
                                    end_date=trade_date, 
                                    market=exchange["market"]
                                )
                                result_queue.put(('success', result))
                            except Exception as e:
                                result_queue.put(('error', str(e)))
                        
                        # 启动获取线程
                        fetch_thread = threading.Thread(target=fetch_gfex_data)
                        fetch_thread.daemon = True
                        fetch_thread.start()
                        
                        # 等待结果，最多等待15秒
                        fetch_thread.join(timeout=15)
                        
                        if fetch_thread.is_alive():
                            # 超时了，自动跳过
                            print("⚠️ 广期所行情数据获取超时(15秒)，自动跳过")
                            continue
                        
                        # 获取结果
                        try:
                            status, df = result_queue.get_nowait()
                            if status == 'error':
                                raise Exception(df)
                        except queue.Empty:
                            print("⚠️ 广期所行情数据获取无响应，自动跳过")
                            continue
                            
                    except Exception as e:
                        print(f"⚠️ 广期所行情数据获取失败，自动跳过: {str(e)}")
                        continue
                else:
                    # 其他交易所使用标准获取方式
                    df = ak.get_futures_daily(start_date=trade_date, end_date=trade_date, market=exchange["market"])
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                if df is not None and not df.empty:
                    df['exchange'] = exchange["name"]
                    all_data.append(df)
                    print(f"✅ {exchange['name']} 行情数据获取成功 (耗时: {elapsed_time:.1f}秒)")
                    success_count += 1
                else:
                    print(f"⚠️ {exchange['name']} 行情数据为空，跳过")
                    
            except Exception as e:
                error_msg = str(e)
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                print(f"获取{exchange['name']}行情数据失败，跳过: {error_msg}")
                continue
        
        if progress_callback:
            progress_callback("行情数据获取完成", 0.8)
        
        # 显示获取结果统计
        total_exchanges = len(self.price_exchanges)
        if success_count >= 3:
            print(f"✅ 成功获取 {success_count}/{total_exchanges} 个交易所行情数据")
        elif success_count > 0:
            print(f"⚠️ 仅获取到 {success_count}/{total_exchanges} 个交易所行情数据")
        else:
            print("⚠️ 未能获取到任何行情数据，将使用基础分析")
        
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    
    def load_position_data(self) -> Dict[str, pd.DataFrame]:
        """加载已保存的持仓数据"""
        all_data = {}
        
        for exchange_name, config in self.exchange_config.items():
            file_path = os.path.join(self.data_dir, config['filename'])
            if os.path.exists(file_path):
                try:
                    data_dict = pd.read_excel(file_path, sheet_name=None)
                    for sheet_name, df in data_dict.items():
                        contract_key = f"{exchange_name}_{sheet_name}"
                        all_data[contract_key] = df
                except Exception as e:
                    print(f"读取{exchange_name}数据失败: {str(e)}")
                    continue
        
        return all_data

class StrategyAnalyzer:
    """策略分析器 - 包含所有分析策略"""
    
    def __init__(self, retail_seats: List[str] = None):
        # 家人席位定义：可配置
        if retail_seats is None:
            from config import STRATEGY_CONFIG
            self.retail_seats = STRATEGY_CONFIG["家人席位反向操作策略"]["default_retail_seats"]
        else:
            self.retail_seats = retail_seats
    
    def update_retail_seats(self, retail_seats: List[str]):
        """更新家人席位配置"""
        self.retail_seats = retail_seats
    
    def process_position_data(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        处理单个合约的持仓数据
        :param df: 原始持仓数据
        :return: 处理后的数据字典
        """
        try:
            # 自动适配不同交易所的列名
            df = self._standardize_columns(df)
            
            required_columns = ['long_party_name', 'long_open_interest', 'long_open_interest_chg',
                              'short_party_name', 'short_open_interest', 'short_open_interest_chg', 'vol']
            
            if not all(col in df.columns for col in required_columns):
                return None
            
            # 数据类型转换 - 处理所有数据，不限制前20名
            df = df.copy()
            numeric_columns = ['long_open_interest', 'long_open_interest_chg',
                             'short_open_interest', 'short_open_interest_chg', 'vol']
            
            for col in numeric_columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace(' ', '').replace({'nan': None})
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 计算汇总数据
            total_long = df['long_open_interest'].sum()
            total_short = df['short_open_interest'].sum()
            total_long_chg = df['long_open_interest_chg'].sum()
            total_short_chg = df['short_open_interest_chg'].sum()
            
            return {
                'total_long': total_long,
                'total_short': total_short,
                'total_long_chg': total_long_chg,
                'total_short_chg': total_short_chg,
                'raw_data': df
            }
            
        except Exception as e:
            print(f"处理持仓数据失败: {str(e)}")
            return None
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 郑商所列名映射
        if 'g_party_n' in df.columns:
            df = df.rename(columns={
                'g_party_n': 'long_party_name',
                'open_inten': 'long_open_interest',
                'inten_intert': 'long_open_interest_chg',
                't_party_n': 'short_party_name',
                'open_inten.1': 'short_open_interest',
                'inten_intert.1': 'short_open_interest_chg',
                'vol': 'vol'
            })
        
        return df
    
    def analyze_power_change(self, data: Dict[str, Any]) -> Tuple[str, str, float]:
        """多空力量变化策略"""
        try:
            long_chg = float(data['total_long_chg'])
            short_chg = float(data['total_short_chg'])
            
            # 计算信号强度
            strength = abs(long_chg) + abs(short_chg)
            
            if long_chg > 0 and short_chg < 0:
                return "看多", f"多单增加{long_chg:.0f}手，空单减少{abs(short_chg):.0f}手", strength
            elif long_chg < 0 and short_chg > 0:
                return "看空", f"多单减少{abs(long_chg):.0f}手，空单增加{short_chg:.0f}手", strength
            else:
                return "中性", f"多单变化{long_chg:.0f}手，空单变化{short_chg:.0f}手", 0
                
        except Exception as e:
            return "错误", f"数据处理错误：{str(e)}", 0
    
    def analyze_spider_web(self, data: Dict[str, Any]) -> Tuple[str, str, float]:
        """蜘蛛网策略"""
        try:
            df = data['raw_data']
            
            # 找出有效席位
            valid_seats = df[
                (df['vol'].notna()) & (df['vol'] > 0) &
                (df['long_open_interest'].notna()) & 
                (df['short_open_interest'].notna())
            ].copy()
            
            if len(valid_seats) < 5:
                return "中性", "有效席位数据不足", 0
            
            # 计算知情度指标
            valid_seats['stat'] = (valid_seats['long_open_interest'] + valid_seats['short_open_interest']) / valid_seats['vol']
            
            # 划分知情者和非知情者
            sorted_seats = valid_seats.sort_values('stat', ascending=False)
            cutoff_index = max(2, int(len(sorted_seats) * 0.4))
            
            its = sorted_seats.iloc[:cutoff_index]
            uts = sorted_seats.iloc[cutoff_index:]
            
            # 计算ITS和UTS
            its_values = []
            uts_values = []
            
            for _, row in its.iterrows():
                total_pos = row['long_open_interest'] + row['short_open_interest']
                if total_pos > 0:
                    its_val = (row['long_open_interest'] - row['short_open_interest']) / total_pos
                    its_values.append(its_val)
            
            for _, row in uts.iterrows():
                total_pos = row['long_open_interest'] + row['short_open_interest']
                if total_pos > 0:
                    uts_val = (row['long_open_interest'] - row['short_open_interest']) / total_pos
                    uts_values.append(uts_val)
            
            if not its_values or not uts_values:
                return "中性", "计算数据不足", 0
            
            # 计算MSD
            msd = np.mean(its_values) - np.mean(uts_values)
            
            if msd > 0.05:
                return "看多", f"MSD={msd:.4f}，知情者明显看多", abs(msd)
            elif msd < -0.05:
                return "看空", f"MSD={msd:.4f}，知情者明显看空", abs(msd)
            else:
                return "中性", f"MSD={msd:.4f}，无明显信号", abs(msd)
                
        except Exception as e:
            return "错误", f"数据处理错误：{str(e)}", 0
    
    def analyze_retail_reverse(self, data: Dict[str, Any]) -> Tuple[str, str, float, List[Dict]]:
        """家人席位反向操作策略 - 按照精确逻辑实现"""
        try:
            df = data['raw_data']
            
            # 统计家人席位的多空变化（合并同一席位）
            seat_stats = {name: {'long_chg': 0, 'short_chg': 0, 'long_pos': 0, 'short_pos': 0} for name in self.retail_seats}
            
            for _, row in df.iterrows():
                if row['long_party_name'] in self.retail_seats:
                    seat_stats[row['long_party_name']]['long_chg'] += row['long_open_interest_chg'] if pd.notna(row['long_open_interest_chg']) else 0
                    seat_stats[row['long_party_name']]['long_pos'] += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
                if row['short_party_name'] in self.retail_seats:
                    seat_stats[row['short_party_name']]['short_chg'] += row['short_open_interest_chg'] if pd.notna(row['short_open_interest_chg']) else 0
                    seat_stats[row['short_party_name']]['short_pos'] += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0
            
            # 只保留有持仓的席位（多单或空单有持仓）
            active_seats = []
            for seat, stats in seat_stats.items():
                if stats['long_pos'] > 0 or stats['short_pos'] > 0:
                    active_seats.append({
                        'seat_name': seat, 
                        'long_chg': stats['long_chg'], 
                        'short_chg': stats['short_chg'],
                        'long_pos': stats['long_pos'],
                        'short_pos': stats['short_pos']
                    })
            
            if not active_seats:
                return "中性", "未发现家人席位持仓", 0, []
            
            # 按照新的逻辑判断信号
            # 看多信号：所有家人席位的空单持仓量变化为正，且多单持仓量变化为负或0
            # 看空信号：所有家人席位的多单持仓量变化为正，且空单持仓量变化为负或0
            
            long_signal_conditions = []  # 看多信号条件
            short_signal_conditions = []  # 看空信号条件
            
            for seat in active_seats:
                long_chg = seat['long_chg']
                short_chg = seat['short_chg']
                
                # 看多信号条件：空单增加(>0) 且 多单减少或不变(<=0)
                long_condition = short_chg > 0 and long_chg <= 0
                long_signal_conditions.append(long_condition)
                
                # 看空信号条件：多单增加(>0) 且 空单减少或不变(<=0)
                short_condition = long_chg > 0 and short_chg <= 0
                short_signal_conditions.append(short_condition)
            
            # 计算持仓占比
            total_position = df['long_open_interest'].sum() + df['short_open_interest'].sum()
            retail_position = sum([seat['long_pos'] + seat['short_pos'] for seat in active_seats])
            position_ratio = retail_position / total_position if total_position > 0 else 0
            
            # 判断信号
            if len(active_seats) > 0 and all(long_signal_conditions):
                # 所有家人席位都满足看多条件
                total_short_increase = sum([seat['short_chg'] for seat in active_seats if seat['short_chg'] > 0])
                return "看多", f"家人席位空单增加{total_short_increase:.0f}手，多单减少或不变，持仓占比{position_ratio:.2%}", position_ratio, active_seats
            elif len(active_seats) > 0 and all(short_signal_conditions):
                # 所有家人席位都满足看空条件
                total_long_increase = sum([seat['long_chg'] for seat in active_seats if seat['long_chg'] > 0])
                return "看空", f"家人席位多单增加{total_long_increase:.0f}手，空单减少或不变，持仓占比{position_ratio:.2%}", position_ratio, active_seats
            else:
                # 不满足条件
                reason_parts = []
                for seat in active_seats:
                    if seat['long_chg'] != 0 or seat['short_chg'] != 0:
                        reason_parts.append(f"{seat['seat_name']}(多{seat['long_chg']:+.0f},空{seat['short_chg']:+.0f})")
                
                reason = f"家人席位持仓变化不符合策略条件: {', '.join(reason_parts)}" if reason_parts else "家人席位无明显变化"
                return "中性", reason, 0, active_seats
                
        except Exception as e:
            return "错误", f"数据处理错误：{str(e)}", 0, []

class TermStructureAnalyzer:
    """期限结构分析器"""
    
    def analyze_term_structure(self, price_data: pd.DataFrame) -> List[Tuple[str, str, List[str], List[float]]]:
        """
        分析期限结构
        :param price_data: 价格数据
        :return: 分析结果列表
        """
        try:
            if price_data.empty:
                return []
            
            required_columns = ['symbol', 'close', 'variety']
            if not all(col in price_data.columns for col in required_columns):
                return []
            
            results = []
            varieties = price_data['variety'].unique()
            
            for variety in varieties:
                variety_data = price_data[price_data['variety'] == variety].copy()
                
                # 过滤有效数据
                variety_data = variety_data[
                    (variety_data['close'] > 0) & 
                    (variety_data['close'].notna())
                ]
                
                if len(variety_data) < 2:
                    continue
                
                # 按合约月份排序（从近月到远月）
                variety_data = self._sort_contracts_by_month(variety_data)
                
                if len(variety_data) < 2:
                    continue
                
                contracts = variety_data['symbol'].tolist()
                closes = variety_data['close'].tolist()
                
                # 判断期限结构
                structure = self._determine_structure_strict(closes)
                results.append((variety, structure, contracts, closes))
            
            return results
            
        except Exception as e:
            print(f"期限结构分析失败: {str(e)}")
            return []
    
    def _sort_contracts_by_month(self, variety_data: pd.DataFrame) -> pd.DataFrame:
        """按合约月份排序（从近月到远月）"""
        try:
            # 提取合约月份信息
            def extract_month_info(symbol):
                # 匹配合约代码中的年月信息
                match = re.search(r'(\d{4})$', symbol)  # 匹配末尾的4位数字（YYMM）
                if match:
                    yymm = match.group(1)
                    year = int(yymm[:2])
                    month = int(yymm[2:])
                    
                    # 处理年份（假设20xx年）
                    if year < 50:  # 假设小于50的是20xx年
                        year += 2000
                    else:
                        year += 1900
                    
                    return year * 100 + month
                return 999999  # 无法解析的放到最后
            
            variety_data['sort_key'] = variety_data['symbol'].apply(extract_month_info)
            variety_data = variety_data.sort_values('sort_key')
            variety_data = variety_data.drop('sort_key', axis=1)
            
            return variety_data
            
        except Exception as e:
            print(f"合约排序失败: {str(e)}")
            return variety_data.sort_values('symbol')  # 降级为按symbol排序
    
    def _determine_structure_strict(self, prices: List[float]) -> str:
        """严格判断期限结构类型"""
        if len(prices) < 2:
            return "flat"
        
        # 严格判断：必须是严格递减或递增
        is_strictly_decreasing = True
        is_strictly_increasing = True
        
        for i in range(len(prices) - 1):
            if prices[i] <= prices[i+1]:  # 不是严格递减
                is_strictly_decreasing = False
            if prices[i] >= prices[i+1]:  # 不是严格递增
                is_strictly_increasing = False
        
        if is_strictly_decreasing:
            return "back"  # 近强远弱（严格递减）
        elif is_strictly_increasing:
            return "contango"  # 近弱远强（严格递增）
        else:
            return "flat"  # 不符合严格递减或递增的为平坦

class FuturesAnalysisEngine:
    """期货分析引擎 - 主控制器"""
    
    def __init__(self, data_dir: str = "data", retail_seats: List[str] = None):
        self.data_manager = FuturesDataManager(data_dir)
        self.strategy_analyzer = StrategyAnalyzer(retail_seats)
        self.term_analyzer = TermStructureAnalyzer()
    
    def update_retail_seats(self, retail_seats: List[str]):
        """更新家人席位配置"""
        self.strategy_analyzer.update_retail_seats(retail_seats)
    
    def full_analysis(self, trade_date: str, progress_callback=None) -> Dict[str, Any]:
        """
        完整分析流程 - 总是包含期限结构分析
        :param trade_date: 交易日期 YYYYMMDD
        :param progress_callback: 进度回调函数
        :return: 分析结果
        """
        results = {
            'position_analysis': {},
            'term_structure': [],
            'summary': {},
            'metadata': {
                'trade_date': trade_date,
                'analysis_time': datetime.now().isoformat(),
                'include_term_structure': True,  # 总是包含期限结构分析
                'retail_seats': self.strategy_analyzer.retail_seats  # 记录使用的家人席位
            }
        }
        
        try:
            # 1. 获取持仓数据
            if progress_callback:
                progress_callback("开始获取持仓数据...", 0.1)
            
            if not self.data_manager.fetch_position_data(trade_date, progress_callback):
                return None
            
            # 2. 获取期货行情数据
            if progress_callback:
                progress_callback("开始获取期货行情数据...", 0.6)
            
            price_data = self.data_manager.fetch_price_data(trade_date, progress_callback)
            
            # 3. 分析持仓数据
            if progress_callback:
                progress_callback("开始分析持仓数据...", 0.8)
            
            position_data = self.data_manager.load_position_data()
            position_results = self._analyze_positions(position_data, progress_callback)
            results['position_analysis'] = position_results
            
            # 4. 期限结构分析
            if progress_callback:
                progress_callback("开始期限结构分析...", 0.9)
            
            if not price_data.empty:
                term_results = self.term_analyzer.analyze_term_structure(price_data)
                results['term_structure'] = term_results
            
            # 5. 生成总结
            if progress_callback:
                progress_callback("生成分析总结...", 0.95)
            
            results['summary'] = self._generate_summary(results)
            
            if progress_callback:
                progress_callback("分析完成", 1.0)
            
            return results
            
        except Exception as e:
            print(f"分析过程出错: {str(e)}")
            return None
    
    def _analyze_positions(self, position_data: Dict[str, pd.DataFrame], progress_callback=None) -> Dict[str, Any]:
        """分析持仓数据"""
        results = {}
        total_contracts = len(position_data)
        
        for i, (contract_name, df) in enumerate(position_data.items()):
            if progress_callback:
                progress = 0.8 + (i / total_contracts) * 0.1
                progress_callback(f"分析合约 {contract_name}...", progress)
            
            # 处理数据
            processed_data = self.strategy_analyzer.process_position_data(df)
            if not processed_data:
                continue
            
            # 应用各种策略
            strategies = {}
            
            # 多空力量变化策略
            signal, reason, strength = self.strategy_analyzer.analyze_power_change(processed_data)
            strategies['多空力量变化策略'] = {
                'signal': signal,
                'reason': reason,
                'strength': strength
            }
            
            # 蜘蛛网策略
            signal, reason, strength = self.strategy_analyzer.analyze_spider_web(processed_data)
            strategies['蜘蛛网策略'] = {
                'signal': signal,
                'reason': reason,
                'strength': strength
            }
            
            # 家人席位反向操作策略
            signal, reason, strength, seat_details = self.strategy_analyzer.analyze_retail_reverse(processed_data)
            strategies['家人席位反向操作策略'] = {
                'signal': signal,
                'reason': reason,
                'strength': strength,
                'seat_details': seat_details
            }
            
            results[contract_name] = {
                'strategies': strategies,
                'raw_data': processed_data['raw_data'],
                'summary_data': {
                    'total_long': processed_data['total_long'],
                    'total_short': processed_data['total_short'],
                    'total_long_chg': processed_data['total_long_chg'],
                    'total_short_chg': processed_data['total_short_chg']
                }
            }
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析总结"""
        summary = {
            'strategy_signals': {},
            'signal_resonance': {},
            'statistics': {}
        }
        
        position_results = results.get('position_analysis', {})
        
        # 统计各策略信号
        strategy_names = ['多空力量变化策略', '蜘蛛网策略', '家人席位反向操作策略']
        
        for strategy_name in strategy_names:
            long_signals = []
            short_signals = []
            
            for contract, data in position_results.items():
                if strategy_name in data['strategies']:
                    strategy_data = data['strategies'][strategy_name]
                    if strategy_data['signal'] == '看多':
                        long_signals.append({
                            'contract': contract,
                            'strength': strategy_data['strength'],
                            'reason': strategy_data['reason']
                        })
                    elif strategy_data['signal'] == '看空':
                        short_signals.append({
                            'contract': contract,
                            'strength': strategy_data['strength'],
                            'reason': strategy_data['reason']
                        })
            
            # 按强度排序
            long_signals.sort(key=lambda x: x['strength'], reverse=True)
            short_signals.sort(key=lambda x: x['strength'], reverse=True)
            
            summary['strategy_signals'][strategy_name] = {
                'long': long_signals,
                'short': short_signals
            }
        
        # 计算信号共振
        summary['signal_resonance'] = self._calculate_signal_resonance(summary['strategy_signals'])
        
        # 统计信息
        total_contracts = len(position_results)
        total_long_signals = sum(len(signals['long']) for signals in summary['strategy_signals'].values())
        total_short_signals = sum(len(signals['short']) for signals in summary['strategy_signals'].values())
        
        summary['statistics'] = {
            'total_contracts': total_contracts,
            'total_long_signals': total_long_signals,
            'total_short_signals': total_short_signals,
            'resonance_long_count': len(summary['signal_resonance']['long']),
            'resonance_short_count': len(summary['signal_resonance']['short'])
        }
        
        return summary
    
    def _calculate_signal_resonance(self, strategy_signals: Dict[str, Any]) -> Dict[str, Any]:
        """计算信号共振"""
        def extract_symbol(contract: str) -> str:
            """提取品种代码"""
            try:
                if '_' in contract:
                    symbol_part = contract.split('_')[-1]
                else:
                    symbol_part = contract
                
                symbol = ''.join(c for c in symbol_part if c.isalpha()).upper()
                return symbol if symbol else contract
            except:
                return contract
        
        long_symbol_count = {}
        short_symbol_count = {}
        
        # 统计各品种在不同策略中的出现次数
        for strategy_name, signals in strategy_signals.items():
            for signal in signals['long'][:10]:  # 只考虑前10个信号
                symbol = extract_symbol(signal['contract'])
                if symbol not in long_symbol_count:
                    long_symbol_count[symbol] = {'count': 0, 'strategies': [], 'contracts': []}
                long_symbol_count[symbol]['count'] += 1
                long_symbol_count[symbol]['strategies'].append(strategy_name)
                long_symbol_count[symbol]['contracts'].append(signal['contract'])
            
            for signal in signals['short'][:10]:
                symbol = extract_symbol(signal['contract'])
                if symbol not in short_symbol_count:
                    short_symbol_count[symbol] = {'count': 0, 'strategies': [], 'contracts': []}
                short_symbol_count[symbol]['count'] += 1
                short_symbol_count[symbol]['strategies'].append(strategy_name)
                short_symbol_count[symbol]['contracts'].append(signal['contract'])
        
        # 筛选共振信号（出现在2个及以上策略中）
        resonance_long = {symbol: info for symbol, info in long_symbol_count.items() if info['count'] >= 2}
        resonance_short = {symbol: info for symbol, info in short_symbol_count.items() if info['count'] >= 2}
        
        return {
            'long': resonance_long,
            'short': resonance_short
        }

# 工具函数
def validate_trade_date(date_str: str) -> bool:
    """验证交易日期格式"""
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def get_recent_trade_date(days_back: int = 1) -> str:
    """获取最近的交易日期"""
    date = datetime.now() - timedelta(days=days_back)
    return date.strftime('%Y%m%d')

if __name__ == "__main__":
    # 测试代码
    engine = FuturesAnalysisEngine()
    trade_date = get_recent_trade_date()
    
    def progress_callback(message, progress):
        print(f"[{progress*100:.1f}%] {message}")
    
    print(f"开始分析 {trade_date} 的数据...")
    results = engine.full_analysis(trade_date, progress_callback)
    
    if results:
        print("分析完成！")
        print(f"分析了 {results['summary']['statistics']['total_contracts']} 个合约")
        print(f"看多信号: {results['summary']['statistics']['total_long_signals']} 个")
        print(f"看空信号: {results['summary']['statistics']['total_short_signals']} 个")
    else:
        print("分析失败！") 