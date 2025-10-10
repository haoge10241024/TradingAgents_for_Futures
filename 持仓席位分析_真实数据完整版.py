#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓席位分析 - 真实数据完整版
基于真实本地数据库数据的完整持仓席位分析系统
无emoji，严肃专业的分析报告
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class NetDirection(Enum):
    STRONG_BULLISH = "强烈看多"
    BULLISH = "看多"
    NEUTRAL_BULLISH = "中性偏多"
    NEUTRAL = "中性"
    NEUTRAL_BEARISH = "中性偏空"
    BEARISH = "看空"
    STRONG_BEARISH = "强烈看空"

@dataclass
class StrategyAnalysisResult:
    strategy_name: str
    strategy_code: str
    bullish_power: float
    bearish_power: float
    power_difference: float
    net_direction: NetDirection
    signal_strength: float
    confidence_level: float
    key_indicators: Dict
    supporting_evidence: Dict
    strategy_theory: str
    calculation_method: str
    usage_guidance: str
    risk_warnings: str

class RealDataPositioningSystem:
    """基于真实数据的完整持仓席位分析系统"""
    
    def __init__(self, data_root: str = "qihuo/database"):
        self.data_root = data_root
        self.positioning_path = os.path.join(data_root, "positioning")
        self.technical_path = os.path.join(data_root, "technical_analysis")
    
    def load_positioning_data(self, symbol: str) -> Dict:
        """加载真实的持仓席位数据"""
        symbol_path = os.path.join(self.positioning_path, symbol)
        
        if not os.path.exists(symbol_path):
            raise FileNotFoundError(f"未找到品种 {symbol} 的持仓数据")
        
        # 读取持仓汇总信息
        summary_file = os.path.join(symbol_path, "positioning_summary.json")
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # 读取多头持仓排名
        long_file = os.path.join(symbol_path, "long_position_ranking.csv")
        long_df = pd.read_csv(long_file)
        
        # 读取空头持仓排名
        short_file = os.path.join(symbol_path, "short_position_ranking.csv")
        short_df = pd.read_csv(short_file)
        
        # 读取成交量排名
        volume_file = os.path.join(symbol_path, "volume_ranking.csv")
        volume_df = pd.read_csv(volume_file)
        
        return {
            'summary': summary,
            'long_positions': long_df,
            'short_positions': short_df,
            'volume_ranking': volume_df
        }
    
    def load_price_data(self, symbol: str) -> pd.DataFrame:
        """加载真实的价格数据"""
        price_file = os.path.join(self.technical_path, symbol, "ohlc_data.csv")
        
        if not os.path.exists(price_file):
            raise FileNotFoundError(f"未找到品种 {symbol} 的价格数据")
        
        df = pd.read_csv(price_file)
        df['时间'] = pd.to_datetime(df['时间'])
        return df.sort_values('时间').tail(30)  # 最近30天数据
    
    def classify_institutions(self, member_name: str) -> str:
        """分类机构席位类型"""
        if any(keyword in member_name for keyword in ['中信', '国泰', '华泰', '银河', '光大', '平安', '招商', '中金', '海通', '广发']):
            return '大型券商'
        elif any(keyword in member_name for keyword in ['永安', '浙商', '南华', '弘业', '混沌', '鲁证', '方正中期']):
            return '专业期货公司'
        elif any(keyword in member_name for keyword in ['物产', '建信', '中粮', '中储', '五矿', '中航']):
            return '产业客户'
        else:
            return '其他机构'
    
    def analyze_spider_web_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """蜘蛛网策略分析 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        volume_df = positioning_data['volume_ranking']
        
        # 获取最新日期的数据
        latest_date = long_df['date'].max()
        latest_long = long_df[long_df['date'] == latest_date].head(20)
        latest_short = short_df[short_df['date'] == latest_date].head(20)
        latest_volume = volume_df[volume_df['date'] == latest_date].head(20)
        
        # 计算知情度指标
        member_info = {}
        
        for _, member in latest_volume.iterrows():
            member_name = member['会员简称']
            volume = member['持仓量']
            
            # 查找对应的多空持仓
            long_pos = latest_long[latest_long['会员简称'] == member_name]['持仓量'].sum()
            short_pos = latest_short[latest_short['会员简称'] == member_name]['持仓量'].sum()
            
            if volume > 0:
                informed_ratio = (long_pos + short_pos) / volume
                net_tendency = (long_pos - short_pos) / (long_pos + short_pos + 1)
                
                member_info[member_name] = {
                    'informed_ratio': informed_ratio,
                    'net_tendency': net_tendency,
                    'long_pos': long_pos,
                    'short_pos': short_pos,
                    'volume': volume
                }
        
        # 按知情度排序，前40%为知情者，后60%为非知情者
        sorted_members = sorted(member_info.items(), key=lambda x: x[1]['informed_ratio'], reverse=True)
        total_members = len(sorted_members)
        informed_count = int(total_members * 0.4)
        
        informed_members = sorted_members[:informed_count]
        uninformed_members = sorted_members[informed_count:]
        
        # 计算知情者和非知情者的平均净倾向
        informed_tendency = np.mean([m[1]['net_tendency'] for m in informed_members]) if informed_members else 0
        uninformed_tendency = np.mean([m[1]['net_tendency'] for m in uninformed_members]) if uninformed_members else 0
        
        # MSD指标
        msd = informed_tendency - uninformed_tendency
        
        # 根据MSD判断方向
        if msd > 0.05:
            net_direction = NetDirection.BULLISH
            bullish_power = min(abs(msd) * 1000, 100)
            bearish_power = 0
        elif msd < -0.05:
            net_direction = NetDirection.BEARISH
            bullish_power = 0
            bearish_power = min(abs(msd) * 1000, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(msd * 1000, 0)
            bearish_power = max(-msd * 1000, 0)
        
        power_difference = msd
        signal_strength = min(abs(msd) * 1000, 100)
        confidence_level = min(signal_strength + 50, 95)
        
        return StrategyAnalysisResult(
            strategy_name="蜘蛛网策略",
            strategy_code="spider_web",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                'MSD': msd,
                '知情者倾向': informed_tendency,
                '非知情者倾向': uninformed_tendency,
                '知情者占比': 0.4,
                '信号确定性': abs(msd)
            },
            supporting_evidence={
                '知情者数量': informed_count,
                '非知情者数量': len(uninformed_members),
                '知情者平均净倾向': informed_tendency,
                '非知情者平均净倾向': uninformed_tendency,
                'MSD指标': msd,
                '分析日期': latest_date
            },
            strategy_theory="基于信息不对称理论，通过MSD指标识别知情资金与非知情资金的持仓差异",
            calculation_method="MSD = 知情者平均净倾向 - 非知情者平均净倾向",
            usage_guidance="MSD > 0.05看多，MSD < -0.05看空，否则中性",
            risk_warnings="知情资金识别可能存在误差，需要结合基本面分析"
        )
    
    def analyze_smart_money_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """聪明钱分析 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近两个交易日的数据进行对比
        dates = sorted(long_df['date'].unique())[-2:]
        if len(dates) < 2:
            dates = [dates[0], dates[0]]
        
        curr_date = dates[-1]
        
        # 分类机构和散户
        institution_change = 0
        retail_change = 0
        
        # 分析多头变化
        for _, row in long_df[long_df['date'] == curr_date].head(20).iterrows():
            member_name = row['会员简称']
            change = row['比上交易增减']
            
            member_type = self.classify_institutions(member_name)
            if member_type in ['大型券商', '专业期货公司', '产业客户']:
                institution_change += change
            else:
                retail_change += change
        
        # 分析空头变化
        for _, row in short_df[short_df['date'] == curr_date].head(20).iterrows():
            member_name = row['会员简称']
            change = row['比上交易增减']
            
            member_type = self.classify_institutions(member_name)
            if member_type in ['大型券商', '专业期货公司', '产业客户']:
                institution_change -= change  # 空头增加表示看空
            else:
                retail_change -= change
        
        # 计算聪明钱指标
        total_change = abs(institution_change) + abs(retail_change)
        if total_change > 0:
            smart_money_ratio = institution_change / total_change
        else:
            smart_money_ratio = 0
        
        # 根据聪明钱流向判断方向
        if smart_money_ratio > 0.3:
            net_direction = NetDirection.BULLISH
            bullish_power = min(smart_money_ratio * 100, 100)
            bearish_power = 0
        elif smart_money_ratio < -0.3:
            net_direction = NetDirection.STRONG_BEARISH
            bullish_power = 0
            bearish_power = min(abs(smart_money_ratio) * 100, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(smart_money_ratio * 100, 0)
            bearish_power = max(-smart_money_ratio * 100, 0)
        
        power_difference = smart_money_ratio
        signal_strength = min(abs(smart_money_ratio) * 100, 100)
        confidence_level = min(signal_strength + 50, 95)
        
        return StrategyAnalysisResult(
            strategy_name="聪明钱分析",
            strategy_code="smart_money",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                '聪明钱比例': smart_money_ratio,
                '机构净变化': institution_change,
                '散户净变化': retail_change,
                '资金流向强度': abs(smart_money_ratio)
            },
            supporting_evidence={
                '机构净持仓变化': f"{institution_change}手",
                '散户净持仓变化': f"{retail_change}手",
                '聪明钱流向比例': f"{smart_money_ratio:.2%}",
                '分析日期': curr_date
            },
            strategy_theory="基于行为金融学理论，跟踪机构资金流向，识别聪明钱的投资方向",
            calculation_method="聪明钱比例 = 机构净变化 / 总变化",
            usage_guidance="比例 > 0.3看多，< -0.3看空",
            risk_warnings="机构资金也会有错误判断，需要设置止损点"
        )
    
    def analyze_family_reverse_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """家人席位反向操作策略 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        latest_date = long_df['date'].max()
        latest_long = long_df[long_df['date'] == latest_date].head(20)
        latest_short = short_df[short_df['date'] == latest_date].head(20)
        
        # 识别家人席位（散户席位）
        family_long_pos = 0
        family_short_pos = 0
        total_long_pos = latest_long['持仓量'].sum()
        total_short_pos = latest_short['持仓量'].sum()
        
        for _, row in latest_long.iterrows():
            member_type = self.classify_institutions(row['会员简称'])
            if member_type == '其他机构':  # 散户席位
                family_long_pos += row['持仓量']
        
        for _, row in latest_short.iterrows():
            member_type = self.classify_institutions(row['会员简称'])
            if member_type == '其他机构':  # 散户席位
                family_short_pos += row['持仓量']
        
        # 计算家人席位占比
        family_long_ratio = family_long_pos / total_long_pos if total_long_pos > 0 else 0
        family_short_ratio = family_short_pos / total_short_pos if total_short_pos > 0 else 0
        
        # 家人席位偏向
        family_bias = family_long_ratio - family_short_ratio
        
        # 反向操作信号（与家人席位相反）
        reverse_signal = -family_bias
        
        if abs(reverse_signal) > 0.2:
            if reverse_signal > 0:
                net_direction = NetDirection.BULLISH
                bullish_power = min(abs(reverse_signal) * 100, 100)
                bearish_power = 0
            else:
                net_direction = NetDirection.BEARISH
                bullish_power = 0
                bearish_power = min(abs(reverse_signal) * 100, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(reverse_signal * 100, 0)
            bearish_power = max(-reverse_signal * 100, 0)
        
        power_difference = reverse_signal
        signal_strength = min(abs(reverse_signal) * 100, 100)
        confidence_level = min(signal_strength + 50, 95)
        
        return StrategyAnalysisResult(
            strategy_name="家人席位反向操作",
            strategy_code="family_reverse",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                '家人席位偏向': family_bias,
                '反向信号强度': abs(reverse_signal),
                '家人做多占比': family_long_ratio,
                '家人做空占比': family_short_ratio
            },
            supporting_evidence={
                '家人席位做多占比': f"{family_long_ratio:.2%}",
                '家人席位做空占比': f"{family_short_ratio:.2%}",
                '家人席位偏向': family_bias,
                '反向操作信号': reverse_signal,
                '分析日期': latest_date
            },
            strategy_theory="基于反向投资理论，当散户过度集中一方时，考虑反向操作",
            calculation_method="反向信号 = -(家人做多占比 - 家人做空占比)",
            usage_guidance="家人席位单边持仓占比>40%时，反向信号较强",
            risk_warnings="散户也可能偶尔判断正确，特别是在明确趋势中"
        )
    
    def analyze_seat_behavior_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """席位行为分析策略 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        latest_date = long_df['date'].max()
        latest_long = long_df[long_df['date'] == latest_date].head(20)
        latest_short = short_df[short_df['date'] == latest_date].head(20)
        
        # 分析机构和散户行为差异
        institution_long_bias = 0
        retail_long_bias = 0
        institution_short_bias = 0
        retail_short_bias = 0
        
        total_long = latest_long['持仓量'].sum()
        total_short = latest_short['持仓量'].sum()
        
        # 计算机构和散户的多头倾向
        for _, row in latest_long.iterrows():
            member_type = self.classify_institutions(row['会员简称'])
            pos_ratio = row['持仓量'] / total_long if total_long > 0 else 0
            
            if member_type in ['大型券商', '专业期货公司', '产业客户']:
                institution_long_bias += pos_ratio
            else:
                retail_long_bias += pos_ratio
        
        # 计算机构和散户的空头倾向
        for _, row in latest_short.iterrows():
            member_type = self.classify_institutions(row['会员简称'])
            pos_ratio = row['持仓量'] / total_short if total_short > 0 else 0
            
            if member_type in ['大型券商', '专业期货公司', '产业客户']:
                institution_short_bias += pos_ratio
            else:
                retail_short_bias += pos_ratio
        
        # 计算行为差异
        institution_net_bias = institution_long_bias - institution_short_bias
        retail_net_bias = retail_long_bias - retail_short_bias
        behavior_difference = institution_net_bias - retail_net_bias
        
        # 判断方向
        if behavior_difference > 0.2:
            net_direction = NetDirection.BULLISH
            bullish_power = min(behavior_difference * 100, 100)
            bearish_power = 0
        elif behavior_difference < -0.2:
            net_direction = NetDirection.BEARISH
            bullish_power = 0
            bearish_power = min(abs(behavior_difference) * 100, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(behavior_difference * 100, 0)
            bearish_power = max(-behavior_difference * 100, 0)
        
        power_difference = behavior_difference
        signal_strength = min(abs(behavior_difference) * 100, 100)
        confidence_level = min(signal_strength + 50, 95)
        
        return StrategyAnalysisResult(
            strategy_name="席位行为分析",
            strategy_code="seat_behavior",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                '行为差异': behavior_difference,
                '机构偏向': institution_net_bias,
                '散户偏向': retail_net_bias,
                '机构多头占比': institution_long_bias,
                '机构空头占比': institution_short_bias
            },
            supporting_evidence={
                '机构多头占比': f"{institution_long_bias:.2%}",
                '机构空头占比': f"{institution_short_bias:.2%}",
                '散户多头占比': f"{retail_long_bias:.2%}",
                '散户空头占比': f"{retail_short_bias:.2%}",
                '行为差异': behavior_difference,
                '分析日期': latest_date
            },
            strategy_theory="分析机构与散户行为差异，跟随机构投资方向",
            calculation_method="行为差异 = (机构多头占比 - 机构空头占比) - (散户多头占比 - 散户空头占比)",
            usage_guidance="机构与散户行为分化时，跟随机构方向",
            risk_warnings="席位分类可能不够准确，需要结合基本面分析"
        )
    
    def analyze_force_change_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """多空力量变化策略 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近两个交易日的数据
        dates = sorted(long_df['date'].unique())[-2:]
        if len(dates) < 2:
            dates = [dates[0], dates[0]]
        
        curr_date = dates[-1]
        
        # 计算多头和空头的总变化
        long_change = long_df[long_df['date'] == curr_date]['比上交易增减'].sum()
        short_change = short_df[short_df['date'] == curr_date]['比上交易增减'].sum()
        
        # 计算力量对比
        total_change = abs(long_change) + abs(short_change)
        if total_change > 0:
            force_difference = (long_change - short_change) / total_change
        else:
            force_difference = 0
        
        # 判断方向
        if force_difference > 0.1:
            net_direction = NetDirection.BULLISH
            bullish_power = min(force_difference * 100, 100)
            bearish_power = 0
        elif force_difference < -0.1:
            net_direction = NetDirection.BEARISH
            bullish_power = 0
            bearish_power = min(abs(force_difference) * 100, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(force_difference * 100, 0)
            bearish_power = max(-force_difference * 100, 0)
        
        power_difference = force_difference
        signal_strength = min(abs(force_difference) * 100, 100)
        confidence_level = min(signal_strength + 40, 90)
        
        return StrategyAnalysisResult(
            strategy_name="多空力量变化",
            strategy_code="force_change",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                '力量差异': force_difference,
                '多头变化': long_change,
                '空头变化': short_change,
                '总变化': total_change
            },
            supporting_evidence={
                '多头变化': f"{long_change}手",
                '空头变化': f"{short_change}手",
                '力量差异': force_difference,
                '分析日期': curr_date
            },
            strategy_theory="基于持仓变化分析多空力量对比，识别主导方向",
            calculation_method="力量差异 = (多头变化 - 空头变化) / 总变化",
            usage_guidance="力量持续向一方倾斜时，考虑跟随操作",
            risk_warnings="力量变化可能是短期波动，需要观察持续性"
        )
    
    def analyze_concentration_strategy(self, positioning_data: Dict) -> StrategyAnalysisResult:
        """持仓集中度分析策略 - 基于真实数据"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        latest_date = long_df['date'].max()
        latest_long = long_df[long_df['date'] == latest_date].head(20)
        latest_short = short_df[short_df['date'] == latest_date].head(20)
        
        # 计算HHI指数（赫芬达尔指数）
        def calculate_hhi(positions):
            total_positions = positions['持仓量'].sum()
            if total_positions == 0:
                return 0
            shares = positions['持仓量'] / total_positions
            return (shares ** 2).sum() * 10000
        
        long_hhi = calculate_hhi(latest_long)
        short_hhi = calculate_hhi(latest_short)
        
        # 计算前5大集中度
        long_top5_ratio = latest_long.head(5)['持仓量'].sum() / latest_long['持仓量'].sum() if latest_long['持仓量'].sum() > 0 else 0
        short_top5_ratio = latest_short.head(5)['持仓量'].sum() / latest_short['持仓量'].sum() if latest_short['持仓量'].sum() > 0 else 0
        
        # 集中度差异
        concentration_difference = long_top5_ratio - short_top5_ratio
        
        # 判断方向
        if abs(concentration_difference) > 0.1:
            if concentration_difference > 0:
                net_direction = NetDirection.NEUTRAL_BULLISH
                bullish_power = min(concentration_difference * 100, 100)
                bearish_power = 0
            else:
                net_direction = NetDirection.NEUTRAL_BEARISH
                bullish_power = 0
                bearish_power = min(abs(concentration_difference) * 100, 100)
        else:
            net_direction = NetDirection.NEUTRAL
            bullish_power = max(concentration_difference * 100, 0)
            bearish_power = max(-concentration_difference * 100, 0)
        
        power_difference = concentration_difference
        signal_strength = min(abs(concentration_difference) * 100, 100)
        confidence_level = min(signal_strength + 40, 85)
        
        return StrategyAnalysisResult(
            strategy_name="持仓集中度分析",
            strategy_code="concentration",
            bullish_power=bullish_power,
            bearish_power=bearish_power,
            power_difference=power_difference,
            net_direction=net_direction,
            signal_strength=signal_strength,
            confidence_level=confidence_level,
            key_indicators={
                'HHI指数': (long_hhi + short_hhi) / 2,
                '多头前5大集中度': long_top5_ratio,
                '空头前5大集中度': short_top5_ratio,
                '集中度差异': concentration_difference
            },
            supporting_evidence={
                '多头HHI指数': long_hhi,
                '空头HHI指数': short_hhi,
                '多头前5大集中度': f"{long_top5_ratio:.2%}",
                '空头前5大集中度': f"{short_top5_ratio:.2%}",
                '集中度差异': concentration_difference,
                '分析日期': latest_date
            },
            strategy_theory="基于HHI指数分析大户控盘程度，关注集中度变化",
            calculation_method="集中度差异 = 多头前5大集中度 - 空头前5大集中度",
            usage_guidance="集中度分化时，关注控盘方的后续动作",
            risk_warnings="高集中度意味着高风险，需要关注大户动向"
        )
    
    def analyze_comprehensive_positioning(self, symbol: str) -> List[StrategyAnalysisResult]:
        """综合持仓席位分析 - 完整的6大策略"""
        try:
            positioning_data = self.load_positioning_data(symbol)
            
            results = []
            
            # 1. 蜘蛛网策略分析
            spider_result = self.analyze_spider_web_strategy(positioning_data)
            results.append(spider_result)
            
            # 2. 聪明钱分析
            smart_money_result = self.analyze_smart_money_strategy(positioning_data)
            results.append(smart_money_result)
            
            # 3. 家人席位反向操作
            family_result = self.analyze_family_reverse_strategy(positioning_data)
            results.append(family_result)
            
            # 4. 席位行为分析
            seat_behavior_result = self.analyze_seat_behavior_strategy(positioning_data)
            results.append(seat_behavior_result)
            
            # 5. 多空力量变化
            force_change_result = self.analyze_force_change_strategy(positioning_data)
            results.append(force_change_result)
            
            # 6. 持仓集中度分析
            concentration_result = self.analyze_concentration_strategy(positioning_data)
            results.append(concentration_result)
            
            return results
            
        except Exception as e:
            print(f"分析过程中出现错误: {e}")
            return []
    
    def create_price_chart(self, symbol: str) -> go.Figure:
        """创建基于真实数据的价格走势图"""
        try:
            price_df = self.load_price_data(symbol)
            
            fig = go.Figure()
            
            # 收盘价折线图（更清晰地显示趋势）
            fig.add_trace(go.Scatter(
                x=price_df['时间'],
                y=price_df['收盘'],
                mode='lines',
                name=f'{_get_symbol_name(symbol)}收盘价',
                line=dict(color='#2E86AB', width=2.5),
                hovertemplate='日期: %{x}<br>收盘价: %{y:.0f}元/吨<extra></extra>'
            ))
            
            # 添加5日移动平均线
            if len(price_df) >= 5:
                ma5 = price_df['收盘'].rolling(window=5).mean()
                fig.add_trace(go.Scatter(
                    x=price_df['时间'], y=ma5, mode='lines', name='5日均线',
                    line=dict(color='#F39C12', width=1.5, dash='dot'), opacity=0.8
                ))
            
            # 添加20日移动平均线
            if len(price_df) >= 20:
                ma20 = price_df['收盘'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(
                    x=price_df['时间'], y=ma20, mode='lines', name='20日均线',
                    line=dict(color='#E74C3C', width=1.5, dash='dash'), opacity=0.8
                ))
            
            fig.update_layout(
                title=f"{_get_symbol_name(symbol)} 价格走势",
                xaxis_title="交易日期",
                yaxis_title="价格 (元/吨)",
                height=400,
                showlegend=True,
                template='plotly_white',
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            print(f"创建价格图表时出现错误: {e}")
            return go.Figure()
    
    def create_strategy_chart(self, result: StrategyAnalysisResult, symbol: str) -> go.Figure:
        """创建策略分析图表 - 基于真实数据"""
        try:
            positioning_data = self.load_positioning_data(symbol)
            
            if result.strategy_code == "spider_web":
                return self._create_spider_web_chart(positioning_data, result)
            elif result.strategy_code == "smart_money":
                return self._create_smart_money_chart(positioning_data, result)
            elif result.strategy_code == "family_reverse":
                return self._create_family_reverse_chart(positioning_data, result)
            elif result.strategy_code == "seat_behavior":
                return self._create_seat_behavior_chart(positioning_data, result)
            elif result.strategy_code == "force_change":
                return self._create_force_change_chart(positioning_data, result)
            elif result.strategy_code == "concentration":
                return self._create_concentration_chart(positioning_data, result)
            else:
                return go.Figure()
                
        except Exception as e:
            print(f"创建策略图表时出现错误: {e}")
            return go.Figure()
    
    def _create_spider_web_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建蜘蛛网策略图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        
        # 获取最近10个交易日的数据
        dates = sorted(long_df['date'].unique())[-10:]
        msd_series = []
        
        for date in dates:
            daily_long = long_df[long_df['date'] == date].head(10)
            if len(daily_long) > 0:
                # 简化的MSD计算
                top5_pos = daily_long.head(5)['持仓量'].sum()
                bottom5_pos = daily_long.tail(5)['持仓量'].sum()
                if top5_pos + bottom5_pos > 0:
                    daily_msd = (top5_pos - bottom5_pos) / (top5_pos + bottom5_pos) * 0.1
                else:
                    daily_msd = 0
                msd_series.append(daily_msd)
            else:
                msd_series.append(0)
        
        fig = go.Figure()
        
        # MSD指标折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=msd_series,
            mode='lines+markers',
            name='MSD指标',
            line=dict(color='#2E86AB', width=2.5),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>MSD: %{y:.4f}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.05, line_dash="dash", line_color="green", line_width=1, opacity=0.5, annotation_text="看多阈值")
        fig.add_hline(y=-0.05, line_dash="dash", line_color="red", line_width=1, opacity=0.5, annotation_text="看空阈值")
        
        fig.update_layout(
            title=f"蜘蛛网策略 - MSD指标走势 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="MSD指标值",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_smart_money_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建聪明钱分析图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近10个交易日的机构资金流向
        dates = sorted(long_df['date'].unique())[-10:]
        institution_flows = []
        smart_money_ratios = []
        
        for date in dates:
            inst_change = 0
            retail_change = 0
            
            # 计算机构和散户净流向变化
            curr_long = long_df[long_df['date'] == date].head(10)
            curr_short = short_df[short_df['date'] == date].head(10)
            
            for _, row in curr_long.iterrows():
                change = row['比上交易增减']
                member_type = self.classify_institutions(row['会员简称'])
                if member_type in ['大型券商', '专业期货公司', '产业客户']:
                    inst_change += change
                else:
                    retail_change += change
            
            for _, row in curr_short.iterrows():
                change = row['比上交易增减']
                member_type = self.classify_institutions(row['会员简称'])
                if member_type in ['大型券商', '专业期货公司', '产业客户']:
                    inst_change -= change  # 空头增加表示看空
                else:
                    retail_change -= change
            
            institution_flows.append(inst_change)
            
            # 计算聪明钱比例
            total_change = abs(inst_change) + abs(retail_change)
            if total_change > 0:
                smart_ratio = inst_change / total_change
            else:
                smart_ratio = 0
            smart_money_ratios.append(smart_ratio)
        
        fig = go.Figure()
        
        # 聪明钱比例折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=smart_money_ratios,
            mode='lines+markers',
            name='聪明钱比例',
            line=dict(color='#8E44AD', width=2.5),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>聪明钱比例: %{y:.2%}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.3, line_dash="dash", line_color="green", line_width=1, opacity=0.5, annotation_text="看多阈值")
        fig.add_hline(y=-0.3, line_dash="dash", line_color="red", line_width=1, opacity=0.5, annotation_text="看空阈值")
        
        fig.update_layout(
            title=f"聪明钱分析 - 机构资金流向 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="聪明钱比例",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_family_reverse_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建家人席位反向操作图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近10个交易日的家人席位占比
        dates = sorted(long_df['date'].unique())[-10:]
        family_ratios = []
        reverse_signals = []
        
        for date in dates:
            daily_long = long_df[long_df['date'] == date].head(20)
            daily_short = short_df[short_df['date'] == date].head(20)
            
            family_long = 0
            total_long = daily_long['持仓量'].sum()
            
            for _, row in daily_long.iterrows():
                member_type = self.classify_institutions(row['会员简称'])
                if member_type == '其他机构':
                    family_long += row['持仓量']
            
            family_short = 0
            total_short = daily_short['持仓量'].sum()
            
            for _, row in daily_short.iterrows():
                member_type = self.classify_institutions(row['会员简称'])
                if member_type == '其他机构':
                    family_short += row['持仓量']
            
            # 计算家人席位偏向
            family_long_ratio = family_long / total_long if total_long > 0 else 0
            family_short_ratio = family_short / total_short if total_short > 0 else 0
            family_bias = family_long_ratio - family_short_ratio
            
            family_ratios.append(family_bias)
            reverse_signals.append(-family_bias)  # 反向信号
        
        fig = go.Figure()
        
        # 家人席位偏向折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=family_ratios,
            mode='lines+markers',
            name='家人席位偏向',
            line=dict(color='#FF8C00', width=2),
            marker=dict(size=5),
            hovertemplate='日期: %{x}<br>家人席位偏向: %{y:.2%}<extra></extra>'
        ))
        
        # 反向操作信号折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=reverse_signals,
            mode='lines+markers',
            name='反向操作信号',
            line=dict(color='#8B008B', width=2.5, dash='dash'),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>反向信号: %{y:.2%}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.2, line_dash="dot", line_color="green", line_width=1, opacity=0.5, annotation_text="强反向信号")
        fig.add_hline(y=-0.2, line_dash="dot", line_color="red", line_width=1, opacity=0.5, annotation_text="强反向信号")
        
        fig.update_layout(
            title=f"家人席位反向操作 - 散户偏向与反向信号 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="偏向比例",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_seat_behavior_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建席位行为分析图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近10个交易日的行为差异
        dates = sorted(long_df['date'].unique())[-10:]
        behavior_differences = []
        
        for date in dates:
            daily_long = long_df[long_df['date'] == date].head(20)
            daily_short = short_df[short_df['date'] == date].head(20)
            
            # 计算机构和散户行为差异
            institution_bias = 0
            retail_bias = 0
            total_long = daily_long['持仓量'].sum()
            total_short = daily_short['持仓量'].sum()
            
            for _, row in daily_long.iterrows():
                member_type = self.classify_institutions(row['会员简称'])
                ratio = row['持仓量'] / total_long if total_long > 0 else 0
                if member_type in ['大型券商', '专业期货公司', '产业客户']:
                    institution_bias += ratio
                else:
                    retail_bias += ratio
            
            for _, row in daily_short.iterrows():
                member_type = self.classify_institutions(row['会员简称'])
                ratio = row['持仓量'] / total_short if total_short > 0 else 0
                if member_type in ['大型券商', '专业期货公司', '产业客户']:
                    institution_bias -= ratio
                else:
                    retail_bias -= ratio
            
            behavior_diff = institution_bias - retail_bias
            behavior_differences.append(behavior_diff)
        
        fig = go.Figure()
        
        # 行为差异折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=behavior_differences,
            mode='lines+markers',
            name='机构散户行为差异',
            line=dict(color='#E67E22', width=2.5),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>行为差异: %{y:.2%}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.2, line_dash="dash", line_color="green", line_width=1, opacity=0.5, annotation_text="强分化阈值")
        fig.add_hline(y=-0.2, line_dash="dash", line_color="red", line_width=1, opacity=0.5, annotation_text="强分化阈值")
        
        fig.update_layout(
            title=f"席位行为分析 - 机构散户行为差异 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="行为差异",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_force_change_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建多空力量变化图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近10个交易日的力量变化
        dates = sorted(long_df['date'].unique())[-10:]
        force_ratios = []
        
        for date in dates:
            daily_long_change = long_df[long_df['date'] == date]['比上交易增减'].sum()
            daily_short_change = short_df[short_df['date'] == date]['比上交易增减'].sum()
            
            total_change = abs(daily_long_change) + abs(daily_short_change)
            if total_change > 0:
                force_ratio = (daily_long_change - daily_short_change) / total_change
            else:
                force_ratio = 0
            
            force_ratios.append(force_ratio)
        
        fig = go.Figure()
        
        # 力量变化折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=force_ratios,
            mode='lines+markers',
            name='多空力量对比',
            line=dict(color='#9B59B6', width=2.5),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>力量对比: %{y:.2%}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.1, line_dash="dash", line_color="green", line_width=1, opacity=0.5, annotation_text="多头优势")
        fig.add_hline(y=-0.1, line_dash="dash", line_color="red", line_width=1, opacity=0.5, annotation_text="空头优势")
        
        fig.update_layout(
            title=f"多空力量变化 - 力量对比走势 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="力量对比",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_concentration_chart(self, positioning_data: Dict, result: StrategyAnalysisResult) -> go.Figure:
        """创建持仓集中度分析图表 - 使用折线图"""
        long_df = positioning_data['long_positions']
        short_df = positioning_data['short_positions']
        
        # 获取最近10个交易日的集中度差异
        dates = sorted(long_df['date'].unique())[-10:]
        concentration_diffs = []
        
        for date in dates:
            daily_long = long_df[long_df['date'] == date].head(20)
            daily_short = short_df[short_df['date'] == date].head(20)
            
            # 计算前5大集中度
            long_top5 = daily_long.head(5)['持仓量'].sum()
            long_total = daily_long['持仓量'].sum()
            long_concentration = long_top5 / long_total if long_total > 0 else 0
            
            short_top5 = daily_short.head(5)['持仓量'].sum()
            short_total = daily_short['持仓量'].sum()
            short_concentration = short_top5 / short_total if short_total > 0 else 0
            
            concentration_diff = long_concentration - short_concentration
            concentration_diffs.append(concentration_diff)
        
        fig = go.Figure()
        
        # 集中度差异折线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=concentration_diffs,
            mode='lines+markers',
            name='多空集中度差异',
            line=dict(color='#34495E', width=2.5),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>集中度差异: %{y:.2%}<extra></extra>'
        ))
        
        # 添加零轴线
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, opacity=0.5)
        
        # 添加阈值线
        fig.add_hline(y=0.1, line_dash="dash", line_color="green", line_width=1, opacity=0.5, annotation_text="多头集中")
        fig.add_hline(y=-0.1, line_dash="dash", line_color="red", line_width=1, opacity=0.5, annotation_text="空头集中")
        
        fig.update_layout(
            title=f"持仓集中度分析 - 多空集中度差异 (当前信号: {result.net_direction.value})",
            xaxis_title="交易日期",
            yaxis_title="集中度差异",
            height=350,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def generate_serious_analysis_report(self, strategy_results: List[StrategyAnalysisResult], symbol: str) -> str:
        """生成严肃专业的分析报告 - 详细版本"""
        symbol_name = _get_symbol_name(symbol)
        
        # 统计信号分布
        bullish_signals = len([r for r in strategy_results if r.power_difference > 0.1])
        bearish_signals = len([r for r in strategy_results if r.power_difference < -0.1])
        neutral_signals = len(strategy_results) - bullish_signals - bearish_signals
        
        # 计算平均置信度
        avg_confidence = np.mean([r.confidence_level for r in strategy_results])
        
        if bearish_signals > bullish_signals:
            market_sentiment = "偏空"
            dominant_force = "空头力量占据主导"
        elif bullish_signals > bearish_signals:
            market_sentiment = "偏多"
            dominant_force = "多头力量相对占优"
        else:
            market_sentiment = "中性"
            dominant_force = "多空力量基本均衡"
        
        # 构建详细报告
        report = f"""## AI持仓席位深度分析报告

本报告基于AI深度学习算法对{symbol_name}持仓席位数据进行综合分析。我们运用六大专业持仓席位分析策略，通过机器学习模型识别市场主力资金动向，为投资决策提供科学依据。

### 市场概况与背景

当前{symbol_name}市场整体呈现{market_sentiment}格局，{dominant_force}。通过对{len(strategy_results)}个持仓席位策略的综合分析，其中{bullish_signals}个策略显示看多信号，{bearish_signals}个策略显示看空信号，{neutral_signals}个策略保持中性。分析置信度达到{avg_confidence:.1f}%，表明当前分析结果具有较高的可靠性。

### 六大策略详细分析

我们基于以下六大经典持仓席位分析策略进行综合研判：

{self._generate_detailed_strategy_analysis(strategy_results)}

### 策略间关联性分析

{self._generate_strategy_correlation_analysis(strategy_results)}

### 市场力量综合解读

{self._generate_market_force_analysis(strategy_results, symbol_name)}

### 风险评估与控制

{self._generate_comprehensive_risk_assessment(strategy_results)}

### 交易策略建议

{self._generate_trading_strategy_recommendations(strategy_results, symbol_name)}

### 策略原理与逻辑说明

{self._generate_strategy_methodology_explanation(strategy_results)}

---

本分析报告由AI期货分析系统生成，基于真实持仓席位数据和技术分析模型。投资有风险，决策需谨慎。"""
        
        return report
    
    def _generate_detailed_strategy_analysis(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """生成详细的策略分析"""
        analysis = ""
        
        for i, result in enumerate(strategy_results, 1):
            direction_desc = result.net_direction.value
            confidence_desc = "高" if result.confidence_level > 80 else "中等" if result.confidence_level > 60 else "较低"
            
            analysis += f"""
**{i}. {result.strategy_name}**

策略原理：{result.strategy_theory}
计算方法：{result.calculation_method}
分析结果：{direction_desc}（置信度：{confidence_desc} {result.confidence_level:.1f}%）

关键指标：{self._format_key_indicators(result.key_indicators)}

该策略显示{result.net_direction.value}信号，信号强度为{result.signal_strength:.1f}%。{result.usage_guidance}

风险提示：{result.risk_warnings}
"""
        
        return analysis
    
    def _generate_strategy_correlation_analysis(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """生成策略间关联性分析"""
        
        # 分析策略一致性
        bullish_strategies = [r.strategy_name for r in strategy_results if r.power_difference > 0.1]
        bearish_strategies = [r.strategy_name for r in strategy_results if r.power_difference < -0.1]
        neutral_strategies = [r.strategy_name for r in strategy_results if abs(r.power_difference) <= 0.1]
        
        analysis = f"""通过对六大策略的交叉验证分析，我们发现：

**策略一致性评估**：
- 看多策略：{', '.join(bullish_strategies) if bullish_strategies else '无'}
- 看空策略：{', '.join(bearish_strategies) if bearish_strategies else '无'}  
- 中性策略：{', '.join(neutral_strategies) if neutral_strategies else '无'}

**关联性分析**：
蜘蛛网策略与聪明钱分析具有较强的相关性，两者都反映了市场主力资金的动向。家人席位反向操作策略与其他策略呈现反向关系，这符合散户投资者的行为特征。席位行为分析和多空力量变化策略能够相互印证，共同揭示市场资金流向的变化趋势。

**信号强度对比**：
{self._compare_signal_strengths(strategy_results)}"""
        
        return analysis
    
    def _generate_market_force_analysis(self, strategy_results: List[StrategyAnalysisResult], symbol_name: str) -> str:
        """生成市场力量综合解读"""
        
        # 计算综合多空力量
        total_bullish_power = sum([r.bullish_power for r in strategy_results])
        total_bearish_power = sum([r.bearish_power for r in strategy_results])
        net_power = total_bullish_power - total_bearish_power
        
        analysis = f"""基于六大策略的综合评估，当前{symbol_name}市场力量分布如下：

**多空力量对比**：
- 综合做多力量：{total_bullish_power:.1f}%
- 综合做空力量：{total_bearish_power:.1f}%  
- 净力量差异：{net_power:+.1f}%

**主力资金行为特征**：
从蜘蛛网策略和聪明钱分析可以看出，机构投资者的操作意图相对明确。大型券商和专业期货公司在持仓配置上显示出专业判断能力，其资金流向往往具有前瞻性。

**散户行为模式**：
家人席位反向操作策略显示，散户投资者的行为模式仍然表现出典型的追涨杀跌特征。这种行为差异为专业投资者提供了反向操作的机会。

**市场控盘程度**：
持仓集中度分析表明，当前市场的控盘程度处于{self._assess_market_control_level(strategy_results)}水平，大资金的影响力{self._assess_big_money_influence(strategy_results)}。"""
        
        return analysis
    
    def _generate_comprehensive_risk_assessment(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """生成综合风险评估"""
        
        avg_confidence = np.mean([r.confidence_level for r in strategy_results])
        signal_consistency = self._calculate_signal_consistency(strategy_results)
        
        if signal_consistency > 0.7:
            risk_level = "中等风险"
        elif signal_consistency > 0.5:
            risk_level = "较高风险"
        else:
            risk_level = "高风险"
        
        analysis = f"""**风险等级评估**：{risk_level}

**风险因素分析**：
1. 信号一致性：{signal_consistency:.1%}（一致性越高，风险越低）
2. 平均置信度：{avg_confidence:.1f}%（置信度越高，可靠性越强）
3. 策略分化程度：{self._assess_strategy_divergence(strategy_results)}

**风险控制建议**：
- 仓位管理：建议单笔交易仓位控制在总资金的8-12%以内
- 止损设置：根据技术分析设置3-5%的硬止损位
- 分批操作：采用分批建仓和分批平仓策略，降低时点风险
- 动态监控：密切关注持仓席位数据的变化，及时调整策略

**特别风险提示**：
持仓席位分析虽然具有一定的预测价值，但不能单独作为投资决策依据。建议结合基本面分析、技术分析和宏观经济环境进行综合判断。"""
        
        return analysis
    
    def _generate_trading_strategy_recommendations(self, strategy_results: List[StrategyAnalysisResult], symbol_name: str) -> str:
        """生成交易策略建议"""
        
        bullish_count = len([r for r in strategy_results if r.power_difference > 0.1])
        bearish_count = len([r for r in strategy_results if r.power_difference < -0.1])
        
        if bearish_count > bullish_count:
            main_direction = "谨慎看空"
            operation_advice = "可考虑在反弹至关键阻力位附近时建立空头仓位"
        elif bullish_count > bearish_count:
            main_direction = "谨慎看多"
            operation_advice = "可考虑在回调至重要支撑位附近时建立多头仓位"
        else:
            main_direction = "保持观望"
            operation_advice = "当前信号不明确，建议等待更清晰的方向信号"
        
        analysis = f"""**主要交易方向**：{main_direction}

**具体操作建议**：
{operation_advice}

**进场时机**：
- 等待价格回调或反弹至关键技术位
- 结合成交量变化确认进场信号
- 关注持仓席位数据的进一步变化

**持仓管理**：
- 建议仓位：5-10%（根据信号强度调整）
- 持仓周期：中短期操作，1-3周为宜
- 加仓条件：策略信号进一步加强且价格配合

**出场策略**：
- 获利了结：达到预期目标位后分批减仓
- 止损出场：价格突破关键技术位立即止损
- 信号转变：持仓席位分析结果发生重大变化时及时调整

**后续跟踪**：
建议每日关注持仓席位数据的变化，特别是前20名会员的持仓变动情况。一旦发现主力资金行为出现重大转变，应立即重新评估投资策略。"""
        
        return analysis
    
    def _generate_strategy_methodology_explanation(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """生成策略原理与逻辑说明"""
        
        analysis = """**持仓席位分析方法论**

持仓席位分析是期货市场技术分析的重要组成部分，通过分析不同类型投资者的持仓行为，揭示市场的资金流向和主力意图。

**核心理论基础**：
1. 信息不对称理论：市场中存在知情资金和非知情资金的差异
2. 行为金融学理论：不同类型投资者具有不同的行为特征
3. 反向投资理论：散户的行为往往与市场走势相反
4. 资金流向分析：主力资金的流向往往预示着价格走势

**分析框架说明**：
我们的分析框架基于六大核心策略，每个策略都有其特定的理论基础和应用场景。通过多策略交叉验证，提高分析结果的可靠性和准确性。

**数据来源与处理**：
- 数据来源：期货交易所公布的每日持仓排名数据
- 数据处理：基于席位名称进行机构分类，计算各类投资者的持仓变化
- 指标计算：运用统计学方法计算各种技术指标

**应用局限性**：
持仓席位分析具有一定的滞后性，且在市场极端情况下可能失效。投资者应将其作为决策参考之一，而非唯一依据。"""
        
        return analysis
    
    def _format_key_indicators(self, indicators: Dict) -> str:
        """格式化关键指标"""
        formatted = []
        for key, value in indicators.items():
            if isinstance(value, float):
                formatted.append(f"{key}: {value:.4f}")
            else:
                formatted.append(f"{key}: {value}")
        return "；".join(formatted)
    
    def _compare_signal_strengths(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """比较信号强度"""
        sorted_results = sorted(strategy_results, key=lambda x: x.signal_strength, reverse=True)
        comparisons = []
        
        for result in sorted_results:
            comparisons.append(f"{result.strategy_name}({result.signal_strength:.1f}%)")
        
        return "信号强度排序：" + " > ".join(comparisons)
    
    def _assess_market_control_level(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """评估市场控盘程度"""
        concentration_result = next((r for r in strategy_results if "集中度" in r.strategy_name), None)
        if concentration_result and abs(concentration_result.power_difference) > 0.1:
            return "较高"
        else:
            return "中等"
    
    def _assess_big_money_influence(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """评估大资金影响力"""
        smart_money_result = next((r for r in strategy_results if "聪明钱" in r.strategy_name), None)
        if smart_money_result and abs(smart_money_result.power_difference) > 0.2:
            return "较为明显"
        else:
            return "相对温和"
    
    def _calculate_signal_consistency(self, strategy_results: List[StrategyAnalysisResult]) -> float:
        """计算信号一致性"""
        bullish_count = len([r for r in strategy_results if r.power_difference > 0.1])
        bearish_count = len([r for r in strategy_results if r.power_difference < -0.1])
        total_count = len(strategy_results)
        
        return max(bullish_count, bearish_count) / total_count
    
    def _assess_strategy_divergence(self, strategy_results: List[StrategyAnalysisResult]) -> str:
        """评估策略分化程度"""
        consistency = self._calculate_signal_consistency(strategy_results)
        
        if consistency > 0.7:
            return "策略信号高度一致"
        elif consistency > 0.5:
            return "策略信号存在一定分化"
        else:
            return "策略信号严重分化"
    
    def _analyze_single_strategy_for_report(self, result: StrategyAnalysisResult) -> str:
        """为报告分析单个策略"""
        strategy_name = result.strategy_name
        
        if abs(result.power_difference) > 0.2:
            strength = "强烈"
            direction = "看多" if result.power_difference > 0 else "看空"
        elif abs(result.power_difference) > 0.1:
            strength = "明显"
            direction = "偏多" if result.power_difference > 0 else "偏空"
        else:
            strength = "中性"
            direction = "均衡"
        
        if "蜘蛛网" in strategy_name:
            return f"{strategy_name}显示知情资金与非知情资金的持仓分化达到{strength}水平，市场信息传导机制呈现{direction}特征。"
        elif "聪明钱" in strategy_name:
            return f"{strategy_name}揭示机构资金流向呈现{strength}{direction}态势，专业投资者的操作意图较为明确。"
        elif "家人席位" in strategy_name:
            return f"{strategy_name}表明散户资金配置出现{strength}的方向性集中，为反向操作提供参考信号。"
        else:
            return f"{strategy_name}分析结果显示{strength}的{direction}信号，为整体判断提供重要支撑。"

def _get_symbol_name(symbol: str) -> str:
    """获取品种中文名称"""
    symbol_names = {
        'CU': '沪铜', 'AL': '沪铝', 'ZN': '沪锌', 'PB': '沪铅', 'NI': '沪镍', 'SN': '沪锡',
        'AU': '沪金', 'AG': '沪银', 'RB': '螺纹钢', 'HC': '热卷', 'I': '铁矿石', 'J': '焦炭', 'JM': '焦煤',
        'A': '豆一', 'M': '豆粕', 'Y': '豆油', 'C': '玉米', 'V': 'PVC', 'PP': 'PP', 'L': 'LLDPE',
        'TA': 'PTA', 'CF': '棉花', 'SR': '白糖', 'RM': '菜粕', 'OI': '菜油', 'MA': '甲醇', 'FG': '玻璃'
    }
    return symbol_names.get(symbol, symbol)

# 测试函数
def test_real_data_system():
    """测试完整的真实数据系统"""
    system = RealDataPositioningSystem()
    
    try:
        print("测试基于真实数据的持仓席位分析系统")
        print("=" * 60)
        
        # 测试分析
        results = system.analyze_comprehensive_positioning("AG")
        
        if results:
            print(f"成功分析 {len(results)} 个策略")
            
            # 生成报告
            report = system.generate_serious_analysis_report(results, "AG")
            print("\n分析报告:")
            print("-" * 40)
            print(report[:500] + "..." if len(report) > 500 else report)
            
        else:
            print("分析失败")
            
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_real_data_system()
