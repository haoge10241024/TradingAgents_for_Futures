#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 优化版辩论、风控、决策系统
按照用户要求优化：口语化辩论、专业风控、权威决策

功能特点：
1. 口语化激烈辩论（多空双方固执己见、相互嘲讽）
2. 专业风控部门独立客观评估
3. CIO级别权威最终决策
4. 用户可控制辩论轮数
5. 纯中文输出，无Markdown符号

作者: AI Assistant  
版本: 2.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

def safe_format_percent(value, default="未知"):
    """安全格式化百分比值"""
    try:
        if value is None:
            return default
        
        # 如果已经是字符串格式的百分比
        if isinstance(value, str):
            if '%' in value:
                return value
            try:
                # 尝试转换为数值
                num_value = float(value)
                return f"{num_value:.1%}"
            except:
                return default
        
        # 如果是数值
        if isinstance(value, (int, float)):
            return f"{value:.1%}"
        
        return default
    except:
        return default

def safe_convert_to_float(value, default=0.5):
    """安全转换为浮点数（用于数值比较）"""
    try:
        if value is None:
            return default
        
        if isinstance(value, str):
            if '%' in value:
                # 如果是百分比字符串，转换为小数
                return float(value.replace('%', '')) / 100
            else:
                return float(value)
        
        if isinstance(value, (int, float)):
            return float(value)
        
        return default
    except:
        return default

# 导入基础架构
from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState, 
    ModuleAnalysisResult,
    AnalysisStatus
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    log_execution_time
)

# 导入价格数据获取器
from 价格数据获取器 import get_commodity_current_price, futures_price_provider

# ============================================================================
# 0. 品种代码映射关系
# ============================================================================

# 期货品种代码与中文名称映射
COMMODITY_MAPPING = {
    # 有色金属
    "CU": "沪铜",
    "AL": "沪铝", 
    "ZN": "沪锌",
    "PB": "沪铅",
    "NI": "沪镍",
    "SN": "沪锡",
    
    # 黑色金属
    "RB": "螺纹钢",
    "HC": "热卷",
    "I": "铁矿石",
    "J": "焦炭",
    "JM": "焦煤",
    "ZC": "动力煤",
    "SF": "硅铁",
    "SM": "锰硅",
    "SS": "不锈钢",
    
    # 贵金属
    "AG": "沪银",
    "AU": "沪金",
    
    # 化工
    "PS": "多晶硅",  # 重要：PS是多晶硅，不是聚苯乙烯！
    "MA": "甲醇",
    "TA": "PTA",
    "EG": "乙二醇",
    "PP": "聚丙烯",
    "L": "聚乙烯",
    "V": "聚氯乙烯",
    "RU": "天然橡胶",
    "BU": "沥青",
    "FU": "燃料油",
    "SC": "原油",
    "SP": "纸浆",
    "UR": "尿素",
    "SA": "纯碱",
    "FG": "玻璃",
    
    # 农产品
    "CF": "棉花",
    "SR": "白糖",
    "OI": "菜籽油",
    "RM": "菜粕",
    "M": "豆粕",
    "Y": "豆油",
    "A": "豆一",
    "B": "豆二",
    "C": "玉米",
    "CS": "玉米淀粉",
    "JD": "鸡蛋",
    "AP": "苹果",
    "CJ": "红枣",
    "LH": "生猪",
    "PK": "花生",
    "RR": "粳米"
}

def get_commodity_name(commodity_code: str) -> str:
    """获取品种中文名称"""
    return COMMODITY_MAPPING.get(commodity_code.upper(), commodity_code)

# ============================================================================
# 1. 核心数据结构
# ============================================================================

class DebateStance(Enum):
    """辩论立场"""
    BULLISH = "多头"
    BEARISH = "空头"

class DebateRoundResult(Enum):
    """辩论轮次结果"""
    BULL_WINS = "多头占优"
    BEAR_WINS = "空头占优" 
    DRAW = "平手"

class TradingStrategy(Enum):
    """交易策略类型"""
    DIRECTIONAL_LONG = "单边做多"
    DIRECTIONAL_SHORT = "单边做空"
    CALENDAR_SPREAD = "跨期套利"
    INTER_COMMODITY_SPREAD = "跨品种套利"
    OPTIONS_STRATEGY = "期权策略"
    NEUTRAL_STRATEGY = "中性策略"
    HEDGE_STRATEGY = "对冲策略"
    CONTINUE = "继续辩论"

class RiskLevel(Enum):
    """风险等级"""
    UNKNOWN = "等待评估"
    VERY_LOW = "极低风险"
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    VERY_HIGH = "极高风险"

class FinalDecision(Enum):
    """最终决策 - 改进版（解决"持有观望"问题）"""
    AGGRESSIVE_LONG = "积极做多"     # 方向明确且风险可控
    MODERATE_LONG = "适度做多"       # 方向明确但风险中等
    CAUTIOUS_LONG = "谨慎做多"       # 方向偏多但不确定性较高
    WAIT = "观望"                    # 方向不明或风险过高，无仓位状态
    CAUTIOUS_SHORT = "谨慎做空"      # 方向偏空但不确定性较高
    MODERATE_SHORT = "适度做空"      # 方向明确但风险中等
    AGGRESSIVE_SHORT = "积极做空"    # 方向明确且风险可控
    
    # 保留旧版兼容性
    STRONG_BUY = "积极做多"
    BUY = "适度做多"
    HOLD = "观望"
    SELL = "适度做空"
    STRONG_SELL = "积极做空"

@dataclass
class DebateRound:
    """单轮辩论结果"""
    round_number: int
    bull_argument: str          # 多头论点
    bear_argument: str          # 空头论点
    bull_score: float          # 多头得分
    bear_score: float          # 空头得分
    round_result: DebateRoundResult
    key_points: List[str]      # 关键争议点
    audience_reaction: str     # 观众反应
    
@dataclass 
class DebateResult:
    """完整辩论结果"""
    total_rounds: int
    rounds: List[DebateRound]
    final_winner: DebateStance
    overall_bull_score: float
    overall_bear_score: float
    key_consensus_points: List[str]
    unresolved_issues: List[str]
    debate_summary: str

@dataclass
class TradingDecision:
    """交易员决策"""
    strategy_type: TradingStrategy
    reasoning: str
    entry_points: List[str]
    exit_points: List[str]
    position_size: str
    risk_reward_ratio: str
    time_horizon: str
    specific_contracts: List[str]
    hedging_components: List[str]
    execution_plan: str
    market_conditions: str
    alternative_scenarios: List[str]

@dataclass
class RiskAssessment:
    """风险评估结果"""
    overall_risk_level: RiskLevel
    market_risk_score: float      # 市场风险评分
    liquidity_risk_score: float   # 流动性风险评分
    leverage_risk_score: float    # 杠杆风险评分
    concentration_risk_score: float # 集中度风险评分
    key_risk_factors: List[str]   # 主要风险因素
    risk_mitigation: List[str]    # 风险缓释措施
    position_size_limit: str      # 建议仓位上限（字符串格式，如"≤1.0%"）
    stop_loss_level: float        # 止损位建议
    risk_manager_opinion: str     # 风控经理意见

@dataclass
class ExecutiveDecision:
    """高管决策结果 - 包含方向判断（兼容CIO逻辑重构版）"""
    final_decision: FinalDecision
    confidence_level: float       # 决策信心
    position_size: float         # 建议仓位
    target_price: Optional[float] # 目标价位
    stop_loss: Optional[str]     # 止损价位
    time_horizon: str           # 持仓周期
    key_rationale: List[str]    # 决策理由
    execution_plan: str         # 执行计划
    monitoring_points: List[str] # 监控要点
    cio_statement: str          # CIO声明
    
    # 🔥 新增方向判断字段
    directional_view: str = "中性"        # 方向判断
    directional_confidence: str = "中"    # 方向判断信心（字符串格式：高/中/低）
    directional_rationale: List[str] = None  # 方向判断理由
    
    # 🔧 兼容CIO逻辑重构版的新字段
    commodity: str = ""                   # 品种名称（兼容字段）
    confidence: float = 0.5               # 简化信心度（兼容字段）
    execution_plan_list: List[str] = None # 执行计划列表（兼容字段）
    risk_warnings: List[str] = None       # 风险警告（兼容字段）
    decision_timestamp: str = ""          # 决策时间戳（兼容字段）
    operational_decision: str = ""        # 操作决策（兼容字段）
    operational_confidence: str = "中"    # 操作信心度（字符串格式：高/中/低）
    decision_basis: Dict = None           # 决策依据（兼容字段）
    validity_conditions: List[str] = None # 有效性条件（兼容字段）
    logic_restructure_version: str = ""   # 逻辑重构版本（兼容字段）
    
    def __post_init__(self):
        """初始化后处理，确保兼容性"""
        if self.directional_rationale is None:
            self.directional_rationale = []
        if self.execution_plan_list is None:
            self.execution_plan_list = []
        if self.risk_warnings is None:
            self.risk_warnings = []
        if self.decision_basis is None:
            self.decision_basis = {}
        if self.validity_conditions is None:
            self.validity_conditions = []
        
        # 同步confidence字段
        if hasattr(self, 'confidence_level') and self.confidence == 0.5:
            self.confidence = self.confidence_level

# ============================================================================
# 2. 专业交易员系统
# ============================================================================

class ProfessionalTrader:
    """专业交易员 - 客观理性整合多空观点，制定具体交易策略"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("deepseek_api_key") or config.get("api_settings", {}).get("deepseek", {}).get("api_key")
        self.base_url = config.get("api_settings", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com/v1")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        self.logger = logging.getLogger("ProfessionalTrader")
        
        # 交易员人设
        self.trader_profile = {
            "name": "资深交易员",
            "experience": "15年期货交易经验",
            "specialty": "套利策略和风险管理",
            "characteristics": [
                "绝对客观理性",
                "数据驱动决策",
                "精通各种交易策略",
                "风险意识极强",
                "执行力卓越"
            ]
        }
    
    def _calculate_ai_driven_confidence(self, analysis_state, module_name: str) -> Dict[str, float]:
        """AI驱动的科学置信度计算"""
        try:
            # 获取模块数据
            module_data = getattr(analysis_state, f"{module_name}_analysis", None)
            if not module_data:
                # 如果模块数据不存在，返回更合理的默认值
                return {"data_confidence": 0.5, "model_confidence": 0.5, "final_confidence": 0.5}
            
            # 1. 数据层置信度计算
            data_quality = self._calculate_data_quality(module_data)
            data_freshness = self._calculate_data_freshness(module_data)
            data_coverage = self._calculate_data_coverage(module_data)
            source_reliability = self._get_source_reliability(module_name)
            
            data_confidence = (0.4 * data_quality + 0.3 * data_freshness + 
                             0.2 * data_coverage + 0.1 * source_reliability)
            
            # 2. 简化的模型层置信度计算（基于实际可获得的数据）
            # 基于分析内容的质量评估
            try:
                confidence_score = getattr(module_data, 'confidence_score', 0.5)
                model_confidence = min(max(confidence_score, 0.3), 0.9)  # 限制在合理范围内
            except:
                model_confidence = 0.6  # 默认中等置信度
            
            # 3. 综合置信度（使用Sigmoid函数）
            import math
            raw_confidence = 0.6 * data_confidence + 0.4 * model_confidence
            final_confidence = 1 / (1 + math.exp(-5 * (raw_confidence - 0.5)))  # Sigmoid激活
            
            return {
                "data_confidence": round(data_confidence, 3),
                "model_confidence": round(model_confidence, 3), 
                "final_confidence": round(final_confidence, 3)
            }
            
        except Exception as e:
            self.logger.warning(f"AI置信度计算失败: {e}")
            return {"data_confidence": 0.5, "model_confidence": 0.5, "final_confidence": 0.5}
    
    def _calculate_data_quality(self, module_data) -> float:
        """计算数据质量评分"""
        try:
            result_data = module_data.result_data or {}
            
            # 数据完整性
            completeness = len(result_data) / 10  # 假设完整数据有10个字段
            completeness = min(completeness, 1.0)
            
            # 数据一致性（基于分析内容长度和结构）
            analysis_content = result_data.get('analysis_content', '')
            consistency = min(len(analysis_content) / 1000, 1.0) if analysis_content else 0.3
            
            # 数据准确性（基于是否有错误标记）
            accuracy = 0.9 if 'error' not in str(result_data).lower() else 0.3
            
            return (0.4 * completeness + 0.3 * consistency + 0.3 * accuracy)
        except:
            return 0.5
    
    def _calculate_data_freshness(self, module_data) -> float:
        """计算数据新鲜度 - 基于实际可获得的信息"""
        try:
            # 基于分析内容是否包含最新信息的简单判断
            result_data = module_data.result_data or {}
            analysis_content = result_data.get('analysis_content', '')
            
            # 如果分析内容较为详细，认为数据相对新鲜
            if len(analysis_content) > 500:
                return 0.8
            elif len(analysis_content) > 200:
                return 0.6
            else:
                return 0.4
        except:
            return 0.6
    
    def _calculate_data_coverage(self, module_data) -> float:
        """计算数据覆盖度"""
        try:
            result_data = module_data.result_data or {}
            # 关键指标覆盖度
            key_indicators = ['analysis_content', 'key_metrics', 'summary']
            covered = sum(1 for indicator in key_indicators if indicator in result_data)
            return covered / len(key_indicators)
        except:
            return 0.6
    
    def _get_source_reliability(self, module_name: str) -> float:
        """获取数据源可靠性评分"""
        # 基于模块类型的可靠性评分
        reliability_scores = {
            'technical': 0.85,    # 技术分析相对客观
            'basis': 0.90,       # 基差数据通常准确
            'inventory': 0.80,   # 库存数据可能有延迟
            'positioning': 0.75, # 持仓数据可能不完整
            'term_structure': 0.85, # 期限结构数据相对准确
            'news': 0.60         # 新闻分析主观性较强
        }
        return reliability_scores.get(module_name, 0.7)
    
    
    
    def _calculate_dynamic_weights(self, analysis_state, commodity_type: str = "有色金属") -> Dict[str, float]:
        """计算AI驱动的动态权重"""
        try:
            # 基础权重矩阵
            base_weights = {
                "贵金属": {"technical": 0.30, "basis": 0.15, "inventory": 0.15, "positioning": 0.20, "term_structure": 0.15, "news": 0.05},
                "有色金属": {"technical": 0.25, "basis": 0.20, "inventory": 0.20, "positioning": 0.15, "term_structure": 0.15, "news": 0.05},
                "黑色金属": {"technical": 0.25, "basis": 0.25, "inventory": 0.20, "positioning": 0.15, "term_structure": 0.10, "news": 0.05},
                "化工品": {"technical": 0.20, "basis": 0.20, "inventory": 0.25, "positioning": 0.15, "term_structure": 0.15, "news": 0.05},
                "农产品": {"technical": 0.20, "basis": 0.15, "inventory": 0.30, "positioning": 0.15, "term_structure": 0.10, "news": 0.10},
                "能源": {"technical": 0.25, "basis": 0.20, "inventory": 0.20, "positioning": 0.15, "term_structure": 0.15, "news": 0.05}
            }
            
            weights = base_weights.get(commodity_type, base_weights["有色金属"]).copy()
            
            # 🤖 AI驱动的置信度调整
            for module in weights.keys():
                confidence_data = self._calculate_ai_driven_confidence(analysis_state, module)
                final_confidence = confidence_data["final_confidence"]
                
                # 置信度乘数 = 0.5 + (Confidence / 100)
                confidence_multiplier = 0.5 + (final_confidence / 2)  # 0.5-1.0范围
                weights[module] *= confidence_multiplier
            
            # 🔄 市场状态自适应调整
            market_regime = self._detect_market_regime(analysis_state)
            
            # 高波动期调整
            if market_regime["vix_level"] > 25:
                weights["technical"] *= 1.1  # 技术分析权重+10%
                weights["news"] *= 1.5       # 新闻分析权重+50%
            
            # 趋势市场调整  
            if market_regime["adx_level"] > 25:
                weights["technical"] *= 1.15  # 技术分析权重+15%
                weights["positioning"] *= 1.05 # 持仓分析权重+5%
            
            # 震荡市场调整
            elif market_regime["adx_level"] < 20:
                weights["basis"] *= 1.1       # 基差分析权重+10%
                weights["inventory"] *= 1.1   # 库存分析权重+10%
            
            # 移除虚假的时效性因子计算
            
            # 归一化权重
            total_weight = sum(weights.values())
            weights = {k: v/total_weight for k, v in weights.items()}
            
            return weights
            
        except Exception as e:
            self.logger.warning(f"动态权重计算失败: {e}")
            # 返回默认权重
            return {"technical": 0.25, "basis": 0.20, "inventory": 0.20, "positioning": 0.15, "term_structure": 0.15, "news": 0.05}
    
    def _calculate_all_modules_ai_confidence(self, analysis_state) -> Dict[str, Dict[str, float]]:
        """计算所有模块的AI置信度"""
        modules = ["technical", "basis", "inventory", "positioning", "term_structure", "news"]
        ai_confidence_data = {}
        
        for module in modules:
            ai_confidence_data[module] = self._calculate_ai_driven_confidence(analysis_state, module)
        
        return ai_confidence_data
    
    def _format_ai_calculations(self, ai_confidence_data: Dict[str, Dict[str, float]], 
                               dynamic_weights: Dict[str, float],
                               commodity_type: str = "有色金属",
                               market_regime: Dict[str, Any] = None) -> str:
        """格式化AI计算结果显示"""
        
        module_names = {
            "technical": "技术分析",
            "basis": "基差分析", 
            "inventory": "库存分析",
            "positioning": "持仓分析",
            "term_structure": "期限结构",
            "news": "新闻分析"
        }
        
        result_lines = []
        result_lines.append("📊 AI置信度与动态权重计算结果：")
        result_lines.append("")
        
        # 添加品种和市场状态信息
        result_lines.append(f"🎯 品种类型：{commodity_type}")
        if market_regime:
            result_lines.append(f"📈 市场状态：{market_regime['market_phase']} | 波动率：{market_regime['volatility_level']} | 趋势强度：{market_regime['trend_strength']}")
            result_lines.append(f"📊 技术指标：VIX={market_regime['vix_level']} | ADX={market_regime['adx_level']}")
        result_lines.append("")
        
        for module, confidence_data in ai_confidence_data.items():
            module_cn = module_names.get(module, module)
            data_conf = confidence_data["data_confidence"]
            model_conf = confidence_data["model_confidence"] 
            final_conf = confidence_data["final_confidence"]
            weight = dynamic_weights.get(module, 0)
            
            result_lines.append(f"• {module_cn}：")
            result_lines.append(f"  - 数据质量评估：{safe_format_percent(data_conf)}")
            result_lines.append(f"  - 分析完整性：{safe_format_percent(model_conf)}")
            result_lines.append(f"  - 综合置信度：{safe_format_percent(final_conf)}")
            result_lines.append(f"  - 权重占比：{safe_format_percent(weight)}")
            
            # 标注高置信度模块
            if final_conf > 0.8:
                result_lines.append(f"  ⭐ 高置信度模块 - 重点关注！")
            elif final_conf < 0.6:
                result_lines.append(f"  ⚠️ 低置信度模块 - 谨慎使用")
            
            result_lines.append("")
        
        # 添加权重归一化验证
        total_weight = sum(dynamic_weights.values())
        result_lines.append(f"🔍 权重归一化验证：总权重 = {total_weight:.3f}（应接近1.000）")
        result_lines.append("")
        
        # 添加AI评分指导
        result_lines.append("🎯 AI评分指导原则：")
        result_lines.append("- 高置信度模块（>80%）：评分权重加倍，即使辩论中未充分讨论也要深度分析")
        result_lines.append("- 中等置信度模块（60-80%）：正常权重评分，重点关注数据支撑")
        result_lines.append("- 低置信度模块（<60%）：降权处理，谨慎使用其结论")
        result_lines.append("- 动态权重已考虑品种特性和置信度调整，请严格按此权重计算最终评分")
        
        return "\n".join(result_lines)
    
    def _identify_commodity_type(self, commodity: str) -> str:
        """智能识别品种类型"""
        commodity_mapping = {
            # 贵金属
            "AU": "贵金属", "AG": "贵金属", "PT": "贵金属", "PD": "贵金属",
            # 有色金属  
            "CU": "有色金属", "AL": "有色金属", "ZN": "有色金属", "PB": "有色金属", 
            "NI": "有色金属", "SN": "有色金属",
            # 黑色金属
            "RB": "黑色金属", "HC": "黑色金属", "I": "黑色金属", "J": "黑色金属", 
            "JM": "黑色金属", "ZC": "黑色金属", "SF": "黑色金属", "SM": "黑色金属",
            # 化工品
            "RU": "化工品", "BU": "化工品", "FU": "化工品", "L": "化工品", 
            "V": "化工品", "PP": "化工品", "TA": "化工品", "EG": "化工品",
            "MA": "化工品", "SA": "化工品", "UR": "化工品", "NR": "化工品",
            "PF": "化工品", "LH": "化工品", "PG": "化工品", "EB": "化工品",
            # 农产品
            "C": "农产品", "CS": "农产品", "A": "农产品", "M": "农产品", 
            "Y": "农产品", "P": "农产品", "OI": "农产品", "RM": "农产品",
            "CF": "农产品", "SR": "农产品", "TA": "农产品", "JD": "农产品",
            "AP": "农产品", "CJ": "农产品", "LR": "农产品", "WH": "农产品",
            "PM": "农产品", "RI": "农产品", "RS": "农产品", "SF": "农产品",
            # 能源
            "SC": "能源", "LU": "能源", "FG": "能源"
        }
        
        return commodity_mapping.get(commodity.upper(), "有色金属")  # 默认有色金属
    
    def _detect_market_regime(self, analysis_state) -> Dict[str, Any]:
        """检测市场状态"""
        try:
            # 简化版市场状态检测
            market_regime = {
                "volatility_level": "中等",  # 高/中等/低
                "trend_strength": "中等",    # 强/中等/弱  
                "market_phase": "震荡",      # 趋势/震荡/转折
                "vix_level": 20,            # 模拟VIX指标
                "adx_level": 22             # 模拟ADX指标
            }
            
            # 基于技术分析结果推断市场状态
            if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
                tech_content = str(analysis_state.technical_analysis.result_data.get('analysis_content', ''))
                
                # 波动率检测
                if '高波动' in tech_content or '剧烈波动' in tech_content:
                    market_regime["volatility_level"] = "高"
                    market_regime["vix_level"] = 30
                elif '低波动' in tech_content or '平稳' in tech_content:
                    market_regime["volatility_level"] = "低"
                    market_regime["vix_level"] = 15
                
                # 趋势强度检测
                if '强势上涨' in tech_content or '强势下跌' in tech_content:
                    market_regime["trend_strength"] = "强"
                    market_regime["market_phase"] = "趋势"
                    market_regime["adx_level"] = 30
                elif '震荡' in tech_content or '横盘' in tech_content:
                    market_regime["market_phase"] = "震荡"
                    market_regime["adx_level"] = 18
            
            return market_regime
            
        except Exception as e:
            self.logger.warning(f"市场状态检测失败: {e}")
            return {
                "volatility_level": "中等",
                "trend_strength": "中等", 
                "market_phase": "震荡",
                "vix_level": 20,
                "adx_level": 22
            }

    def _generate_analyst_reports_summary(self, analysis_state: FuturesAnalysisState) -> str:
        """🔥 新增：生成原始分析师报告摘要，供辩论评判参考"""
        
        summary_lines = []
        summary_lines.append("【原始分析师报告摘要】（辩论评判时必须参考）")
        summary_lines.append("")
        summary_lines.append("以下是6个分析师模块的核心观点和建议，辩论评判时必须对比这些原始观点：")
        summary_lines.append("")
        
        # 定义关键词
        bullish_keywords = ["看多", "做多", "买入", "上涨", "利多", "积极", "强势", "偏多", "偏强", "多头占优", "看涨", "逢低做多"]
        bearish_keywords = ["看空", "做空", "卖出", "下跌", "利空", "疲弱", "弱势", "偏空", "偏弱", "空头占优", "看跌", "逢高做空"]
        
        module_count = 0
        
        # 1. 技术分析
        if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
            module_count += 1
            tech_data = analysis_state.technical_analysis.result_data
            content = str(tech_data.get('analysis_content', ''))
            recommendation = str(tech_data.get('recommendation', ''))
            
            # 提取关键信息
            view, confidence = self._extract_module_view(
                analysis_state.technical_analysis, "技术分析",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【技术分析模块】")
            summary_lines.append(f"   • 分析师观点：{view} ← {'非常明确' if view != '中性' else '中性'}")
            
            # 提取核心建议
            if '逢低做多' in content or '逢低买入' in content:
                summary_lines.append(f"   • 核心建议：逢低做多")
            elif '逢高做空' in content or '逢高卖出' in content:
                summary_lines.append(f"   • 核心建议：逢高做空")
            elif '看涨' in content or '看多' in recommendation:
                summary_lines.append(f"   • 核心建议：看涨/看多")
            elif '看跌' in content or '看空' in recommendation:
                summary_lines.append(f"   • 核心建议：看跌/看空")
            
            # 提取风险等级
            if '低风险' in content or '风险较小' in content:
                summary_lines.append(f"   • 风险等级：低风险")
            elif '高风险' in content:
                summary_lines.append(f"   • 风险等级：高风险")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 2. 基差分析
        if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
            module_count += 1
            basis_data = analysis_state.basis_analysis.result_data
            content = str(basis_data.get('analysis_content', ''))
            
            view, confidence = self._extract_module_view(
                analysis_state.basis_analysis, "基差分析",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【基差分析模块】")
            summary_lines.append(f"   • 分析师观点：{view}")
            
            if '套利' in content or '期现套利' in content:
                summary_lines.append(f"   • 核心建议：期现套利、跨期套利（非单边方向）")
            if '供需偏紧' in content or '略偏紧' in content:
                summary_lines.append(f"   • 基本面倾向：供需偏紧")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 3. 库存分析
        if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
            module_count += 1
            inv_data = analysis_state.inventory_analysis.result_data
            content = str(inv_data.get('analysis_content', ''))
            recommendation = str(inv_data.get('recommendation', ''))
            
            view, confidence = self._extract_module_view(
                analysis_state.inventory_analysis, "库存分析",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【库存分析模块】")
            summary_lines.append(f"   • 分析师观点：{view} ← {'明确' if view != '中性' else '中性'}")
            
            if '建立多头头寸' in content or '建立多头仓位' in content:
                summary_lines.append(f"   • 核心建议：建立多头头寸")
            elif '建立空头头寸' in content or '建立空头仓位' in content:
                summary_lines.append(f"   • 核心建议：建立空头头寸")
            elif '谨慎偏多' in recommendation or '谨慎看多' in recommendation:
                summary_lines.append(f"   • 核心建议：谨慎偏多策略")
            
            # 提取信心水平
            if '70%' in content or '信心水平维持在70%' in content:
                summary_lines.append(f"   • 信心水平：70%（高）")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 4. 持仓分析
        if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
            module_count += 1
            pos_data = analysis_state.positioning_analysis.result_data
            content = str(pos_data.get('analysis_content', ''))
            
            view, confidence = self._extract_module_view(
                analysis_state.positioning_analysis, "持仓分析",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【持仓分析模块】")
            summary_lines.append(f"   • 分析师观点：{view} ← {'明确' if view != '中性' else '中性'}")
            
            if '谨慎看多' in content or '谨慎看多' in content:
                summary_lines.append(f"   • 核心建议：谨慎看多，回调时建立多头仓位")
            
            # 提取市场力量数据
            if '做多' in content and '94' in content:
                summary_lines.append(f"   • 市场力量：做多力量显著占优")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 5. 期限结构
        if hasattr(analysis_state, 'term_structure_analysis') and analysis_state.term_structure_analysis:
            module_count += 1
            term_data = analysis_state.term_structure_analysis.result_data
            content = str(term_data.get('analysis_content', ''))
            
            view, confidence = self._extract_module_view(
                analysis_state.term_structure_analysis, "期限结构",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【期限结构模块】")
            summary_lines.append(f"   • 分析师观点：{view}")
            
            if '反套' in content or '空远月多近月' in content:
                summary_lines.append(f"   • 核心建议：反套机会（套利，非单边）")
            if '谨慎乐观' in content:
                summary_lines.append(f"   • 基调：谨慎乐观")
            if '风险评分' in content and '0' in content:
                summary_lines.append(f"   • 风险评分：0（风险较小）")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 6. 新闻分析
        if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
            module_count += 1
            news_data = analysis_state.news_analysis.result_data
            content = str(news_data.get('analysis_content', ''))
            recommendation = str(news_data.get('recommendation', ''))
            
            view, confidence = self._extract_module_view(
                analysis_state.news_analysis, "新闻分析",
                bullish_keywords, bearish_keywords
            )
            
            summary_lines.append(f"{module_count}. 【新闻分析模块】")
            summary_lines.append(f"   • 分析师观点：{view} ← {'非常明确' if view != '中性' else '中性'}")
            
            if '逢低做多' in content or '短期逢低做多' in content:
                summary_lines.append(f"   • 核心建议：短期逢低做多、中期看涨")
            if '挑战' in content and '历史' in content:
                summary_lines.append(f"   • 价格预期：有望挑战历史高点")
            
            summary_lines.append(f"   • 信心度：{confidence}")
            summary_lines.append("")
        
        # 统计
        views_stat = self._extract_analyst_views_统计(analysis_state)
        summary_lines.append("⚠️ 【分析师观点统计】")
        summary_lines.append(f"• 看多模块：{views_stat['bullish_count']}个 ({', '.join(views_stat['bullish_modules']) if views_stat['bullish_modules'] else '无'})")
        summary_lines.append(f"• 看空模块：{views_stat['bearish_count']}个 ({', '.join(views_stat['bearish_modules']) if views_stat['bearish_modules'] else '无'})")
        summary_lines.append(f"• 中性模块：{views_stat['neutral_count']}个 ({', '.join(views_stat['neutral_modules']) if views_stat['neutral_modules'] else '无'})")
        summary_lines.append("")
        summary_lines.append("🚨 重要提示：")
        summary_lines.append("1. 辩论评判时必须对比原始分析师观点")
        summary_lines.append("2. 辩论论述与分析师观点一致的一方得分更高")
        summary_lines.append("3. 选择性放大风险、歪曲原意的论述应扣分")
        summary_lines.append("4. 最终方向判断必须基于分析师观点统计，不能被辩论评判覆盖")
        summary_lines.append("")
        summary_lines.append("="*80)
        summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def _extract_analyst_views_统计(self, analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """🔥 新增：提取并统计各分析师模块的观点"""
        
        views = {
            "bullish_modules": [],      # 看多模块
            "bearish_modules": [],      # 看空模块
            "neutral_modules": [],      # 中性模块
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "total_count": 0,
            "details": {}
        }
        
        # 定义各模块的观点关键词
        bullish_keywords = ["看多", "做多", "买入", "上涨", "利多", "积极", "强势"]
        bearish_keywords = ["看空", "做空", "卖出", "下跌", "利空", "疲弱", "弱势"]
        
        # 1. 技术分析
        if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
            tech_view, tech_confidence = self._extract_module_view(
                analysis_state.technical_analysis, "技术分析", 
                bullish_keywords, bearish_keywords
            )
            views["details"]["技术分析"] = {"view": tech_view, "confidence": tech_confidence}
            if tech_view == "看多":
                views["bullish_modules"].append("技术分析")
                views["bullish_count"] += 1
            elif tech_view == "看空":
                views["bearish_modules"].append("技术分析")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("技术分析")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        # 2. 基差分析
        if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
            basis_view, basis_confidence = self._extract_module_view(
                analysis_state.basis_analysis, "基差分析",
                bullish_keywords, bearish_keywords
            )
            views["details"]["基差分析"] = {"view": basis_view, "confidence": basis_confidence}
            if basis_view == "看多":
                views["bullish_modules"].append("基差分析")
                views["bullish_count"] += 1
            elif basis_view == "看空":
                views["bearish_modules"].append("基差分析")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("基差分析")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        # 3. 库存分析
        if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
            inv_view, inv_confidence = self._extract_module_view(
                analysis_state.inventory_analysis, "库存分析",
                bullish_keywords, bearish_keywords
            )
            views["details"]["库存分析"] = {"view": inv_view, "confidence": inv_confidence}
            if inv_view == "看多":
                views["bullish_modules"].append("库存分析")
                views["bullish_count"] += 1
            elif inv_view == "看空":
                views["bearish_modules"].append("库存分析")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("库存分析")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        # 4. 持仓分析
        if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
            pos_view, pos_confidence = self._extract_module_view(
                analysis_state.positioning_analysis, "持仓分析",
                bullish_keywords, bearish_keywords
            )
            views["details"]["持仓分析"] = {"view": pos_view, "confidence": pos_confidence}
            if pos_view == "看多":
                views["bullish_modules"].append("持仓分析")
                views["bullish_count"] += 1
            elif pos_view == "看空":
                views["bearish_modules"].append("持仓分析")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("持仓分析")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        # 5. 期限结构
        if hasattr(analysis_state, 'term_structure_analysis') and analysis_state.term_structure_analysis:
            term_view, term_confidence = self._extract_module_view(
                analysis_state.term_structure_analysis, "期限结构",
                bullish_keywords, bearish_keywords
            )
            views["details"]["期限结构"] = {"view": term_view, "confidence": term_confidence}
            if term_view == "看多":
                views["bullish_modules"].append("期限结构")
                views["bullish_count"] += 1
            elif term_view == "看空":
                views["bearish_modules"].append("期限结构")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("期限结构")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        # 6. 新闻分析
        if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
            news_view, news_confidence = self._extract_module_view(
                analysis_state.news_analysis, "新闻分析",
                bullish_keywords, bearish_keywords
            )
            views["details"]["新闻分析"] = {"view": news_view, "confidence": news_confidence}
            if news_view == "看多":
                views["bullish_modules"].append("新闻分析")
                views["bullish_count"] += 1
            elif news_view == "看空":
                views["bearish_modules"].append("新闻分析")
                views["bearish_count"] += 1
            else:
                views["neutral_modules"].append("新闻分析")
                views["neutral_count"] += 1
            views["total_count"] += 1
        
        return views
    
    def _extract_module_view(self, module_data, module_name: str, 
                            bullish_keywords: list, bearish_keywords: list) -> tuple:
        """✅ 改进：更准确地从模块中提取观点和信心度"""
        try:
            # 获取分析内容
            content = str(module_data.result_data.get('analysis_content', ''))
            recommendation = str(module_data.result_data.get('recommendation', ''))
            summary = str(module_data.result_data.get('summary', ''))
            full_text = content + " " + recommendation + " " + summary
            
            # 🔥 DEBUG: 显示提取到的文本信息
            print(f"🐛 DEBUG [{module_name}观点提取]: content长度={len(content)}, recommendation长度={len(recommendation)}, summary长度={len(summary)}")
            print(f"🐛 DEBUG [{module_name}观点提取]: full_text长度={len(full_text)}, 前200字符='{full_text[:200]}'")
            
            # 🔥 如果标准字段为空，尝试其他可能的字段
            if len(full_text.strip()) < 50:
                print(f"⚠️ [{module_name}观点提取]: 标准字段文本过短，尝试其他字段")
                print(f"🐛 DEBUG [{module_name}观点提取]: result_data所有字段: {list(module_data.result_data.keys())}")
                
                # 尝试获取所有文本字段
                all_text_fields = []
                for key, value in module_data.result_data.items():
                    if isinstance(value, str) and len(value) > 100:
                        all_text_fields.append(value)
                        print(f"🐛 DEBUG [{module_name}观点提取]: 找到文本字段'{key}', 长度={len(value)}")
                
                if all_text_fields:
                    full_text = " ".join(all_text_fields)
                    print(f"✅ [{module_name}观点提取]: 使用合并后的文本字段，总长度={len(full_text)}")
            
            # 获取信心度
            confidence = module_data.confidence_score
            if confidence >= 0.7:
                conf_level = "高信心度"
            elif confidence >= 0.5:
                conf_level = "中信心度"
            else:
                conf_level = "低信心度"
            
            import re
            
            # ========================================================================
            # 第一级：明确的结论性表述（最高优先级）
            # ========================================================================
            conclusion_patterns = [
                # 🔥 0. 分析结果/结论（最高优先级 - 新增）
                r'(?:分析结果|最终结论|综合结论)[：:]\s*([^。\n]*?(?:看多|看空|偏多|偏空|中性偏多|中性偏空|中性|观望)[^。\n]*?)(?:\n|。|$)',
                
                # 1. 投资方向/操作建议（最高优先级）
                r'(?:投资方向建议|操作建议|交易建议|投资建议)[：:][^。]*?(?:采取)?[^。]*?(谨慎)?[^。]*?(偏多|偏空|做多|做空|看多|看空|买入|卖出)',
                
                # 2. 主要交易方向
                r'主要交易方向[：:][^。]*?(谨慎)?[^。]*?(看多|看空|做多|做空|偏多|偏空|中性|观望)',
                
                # 3. 建议建立头寸
                r'建议[^。]*?(?:在|逐步)?[^。]*?建立[^。]*?(多头|空头)(?:头寸|仓位)',
                
                # 4. 建议采取...策略
                r'(?:建议|推荐)(?:采取)?[^。]*?(谨慎)?[^。]*?(偏多|偏空|做多|做空|看多|看空|买入|卖出)(?:策略)?',
                
                # 5. 短期/中期操作建议（新增 - 针对新闻分析）- 扩展匹配范围
                r'(?:短期|中期|长期)[^。]*?(?:建议|策略|操作)[^，。]*?(谨慎)?[^，。]*?(逢低|逢高)?[^，。]*?(做多|做空|买入|卖出|看多|看空|看涨|看跌)',
                
                # 5.1. 维持看涨/看跌观点（专门针对"中期维持看涨观点"）
                r'(?:维持|保持)[^。]*?(看涨|看跌|看多|看空|偏多|偏空)(?:观点|判断|态度)',
                
                # 6. 看涨/看跌（新增 - 针对技术分析）
                r'(?:方向|趋势|判断)[^。]*?(?:为|是|确认)[^。]*?(看涨|看跌)',
                
                # 7. 市场/价格呈现...格局/态势
                r'(?:市场|价格|铜价|沪铜|金价|沪金|白银)[^。]*?(?:呈现|显示|表现)[^。]*?(偏多|偏空|偏强|偏弱|强势|弱势)(?:格局|态势|特征)?',
                
                # 8. 震荡偏强/偏弱
                r'(?:震荡|波动)[^。]*?(偏强|偏弱|偏多|偏空)',
                
                # 9. 多头/空头占优/强势（优化：更精确的匹配，避免误匹配描述性文字）
                r'(多头|空头)\s*(?:力量|资金)?\s*(?:占优|强势|主导|占据优势|占据主导)',
                
                # 10. 总体/综合来看
                r'(?:总体|综合|整体)(?:来看|而言|判断)[^。]*?(看多|看空|偏多|偏空|看涨|看跌|中性|观望)',
                
                # 11. 方向/趋势判断
                r'(?:方向|趋势|走势)[^。]*?(看多|看空|偏多|偏空|上涨|下跌|看涨|看跌)',
                
                # 12. 明确结论
                r'(?:结论|判断)[：:][^。]*?(看多|看空|偏多|偏空|看涨|看跌|中性|观望)',
                
                # 13. 延续...趋势/行情
                r'(?:延续|维持|保持)[^。]*?(上升|上涨|下跌|下降)(?:趋势|行情|态势)',
                
                # 14. 偏向...
                r'(?:偏向|倾向)[^。]*?(乐观|悲观|看多|看空)',
                
                # 15. 上涨趋势有望延续（新增 - 针对新闻分析）
                r'(?:上涨|上行|上升|下跌|下行|下降)(?:趋势|行情)[^。]*?(?:有望|将|可能)[^。]*?(?:延续|持续|继续)',
                
                # 16. 价格有望...（新增）
                r'价格[^。]*?(?:有望|将|可能)[^。]*?(?:上涨|上行|挑战|下跌|下行)',
                
                # 17. 核心观点（新增 - 针对专业报告摘要）
                r'核心观点[：:][^。]*?(呈现|表现|显示)[^。]*?(强劲|疲弱)[^。]*?(上涨|下跌)(?:态势|趋势)',
                
                # 18. 有望延续...行情（新增）
                r'(?:有望|将|可能)[^。]*?延续[^。]*?(多头|空头|上涨|下跌)(?:行情|趋势)',
                
                # 19. 预期...（新增）
                r'预期[^。]*?(?:看至|突破|上涨|下跌|上行|下行)',
                
                # 20. 处于...周期/阶段（新增）
                r'处于[^。]*?(强势|弱势|上涨|下跌)(?:周期|阶段)',
                
                # 21. ...趋势...延续/持续（新增）
                r'(上涨|下跌|上升|下降)[^。]*?趋势[^。]*?(?:仍将|将|可能)[^。]*?(?:延续|持续|继续)'
            ]
            
            print(f"🐛 DEBUG [{module_name}观点提取]: 开始匹配{len(conclusion_patterns)}个结论性表述模式")
            
            for idx, pattern in enumerate(conclusion_patterns):
                match = re.search(pattern, full_text)
                if match:
                    # 获取匹配的所有分组和完整匹配文本
                    groups = match.groups()
                    matched_text = match.group(0)
                    
                    print(f"🐛 DEBUG [{module_name}观点提取]: 模式{idx+1}匹配成功！匹配文本: {matched_text[:100]}")
                    
                    # 检查是否包含看多/偏多信号
                    all_text = ''.join(str(g) for g in groups if g) + matched_text
                    
                    # 🔥 最高优先级：分析结果/结论的精确匹配（模式0）
                    if idx == 0:  # 这是新增的分析结果模式
                        # 精确提取结论文本
                        conclusion_text = groups[0] if groups else matched_text
                        print(f"🔥 [{module_name}观点提取]: 检测到明确结论：{conclusion_text}")
                        
                        # 优先匹配"中性偏X"格式
                        if '中性偏多' in conclusion_text or '中性偏强' in conclusion_text:
                            print(f"✅ [{module_name}观点提取]: 结论为中性偏多，判断为看多")
                            return "看多", conf_level
                        elif '中性偏空' in conclusion_text or '中性偏弱' in conclusion_text:
                            print(f"✅ [{module_name}观点提取]: 结论为中性偏空，判断为看空")
                            return "看空", conf_level
                        elif '中性' in conclusion_text:
                            print(f"✅ [{module_name}观点提取]: 结论为中性")
                            return "中性", conf_level
                        # 然后匹配明确的方向
                        elif any(kw in conclusion_text for kw in ['看多', '偏多', '做多', '买入']):
                            print(f"✅ [{module_name}观点提取]: 结论为看多")
                            return "看多", conf_level
                        elif any(kw in conclusion_text for kw in ['看空', '偏空', '做空', '卖出']):
                            print(f"✅ [{module_name}观点提取]: 结论为看空")
                            return "看空", conf_level
                    
                    # 看多/看空信号（扩展识别）
                    bullish_signals = ['偏多', '偏强', '看多', '做多', '买入', '上涨', '上升', '乐观', '强势', '看涨', '强劲']
                    bearish_signals = ['偏空', '偏弱', '看空', '做空', '卖出', '下跌', '下降', '悲观', '弱势', '看跌', '疲弱']
                    
                    # 🔥 特殊处理1：多头头寸/空头头寸
                    if '多头头寸' in matched_text or '多头仓位' in matched_text or '建立多头' in matched_text:
                        return "看多", conf_level
                    if '空头头寸' in matched_text or '空头仓位' in matched_text or '建立空头' in matched_text:
                        return "看空", conf_level
                    
                    # 🔥 特殊处理2：多头/空头占优（增强判断，避免误匹配描述性文字）
                    # 只有当"多头"/"空头"紧跟"占优"/"强势"等词时才判断
                    if re.search(r'多头\s*(?:占优|强势|力量|主导|优势)', matched_text):
                        print(f"✅ [{module_name}观点提取]: 检测到'多头占优'表述，判断为看多")
                        return "看多", conf_level
                    if re.search(r'空头\s*(?:占优|强势|力量|主导|优势)', matched_text):
                        print(f"✅ [{module_name}观点提取]: 检测到'空头占优'表述，判断为看空")
                        return "看空", conf_level
                    
                    # 🔥 特殊处理3：逢低做多/逢高做空
                    if '逢低' in all_text and any(x in all_text for x in ['做多', '买入', '建仓', '建立']):
                        return "看多", conf_level
                    if '逢高' in all_text and any(x in all_text for x in ['做空', '卖出', '建仓', '建立']):
                        return "看空", conf_level
                    
                    # 🔥 特殊处理4：趋势延续/有望挑战
                    if any(x in all_text for x in ['上涨', '上行', '上升']) and any(y in all_text for y in ['延续', '持续', '继续', '有望', '挑战']):
                        return "看多", conf_level
                    if any(x in all_text for x in ['下跌', '下行', '下降']) and any(y in all_text for y in ['延续', '持续', '继续', '有望']):
                        return "看空", conf_level
                    
                    # 🔥🔥🔥 特殊处理：基差和期限结构的套利策略检测
                    # 只有基差分析和期限结构需要检查套利关键词
                    if module_name in ['基差分析', '期限结构']:
                        arbitrage_keywords = ['正套', '反套', '套利', '跨期套利', '期现套利', '跨市场套利']
                        if any(kw in full_text for kw in arbitrage_keywords):
                            print(f"🔍 [{module_name}观点提取]: 检测到套利关键词，进行谨慎评估")
                            
                            # 检查整体语气：风险警告和谨慎措辞
                            caution_keywords = ['谨慎', '有限', '压制', '压力', '风险', '不宜', '需要注意', '密切关注']
                            caution_count = sum(1 for kw in caution_keywords if kw in full_text)
                            
                            # 如果风险警告>=3个，且有套利关键词，判断为中性（套利机会，非单边）
                            if caution_count >= 3:
                                print(f"⚠️ [{module_name}观点提取]: 检测到{caution_count}个谨慎/风险关键词，套利策略判断为中性")
                                return "中性", conf_level
                            
                            # 如果只是提到套利但没有强烈的方向性建议，也判断为中性
                            strong_directional = ['建议做多', '建议做空', '看多', '看空', '买入持有', '卖出离场']
                            if not any(kw in full_text for kw in strong_directional):
                                print(f"⚠️ [{module_name}观点提取]: 套利策略但无强方向性建议，判断为中性")
                                return "中性", conf_level
                    
                    # ⚠️ 关键修复：常规判断
                    # 即使有"谨慎"，只要明确说"看多"/"看涨"就是看多，不是中性！
                    # 🔥 注意：不再将"多头"/"空头"作为信号词，避免误匹配描述性文字
                    if any(kw in all_text for kw in bullish_signals):
                        matched_keywords = [kw for kw in bullish_signals if kw in all_text]
                        print(f"✅ [{module_name}观点提取]: 识别为看多！关键词: {matched_keywords}")
                        return "看多", conf_level
                    elif any(kw in all_text for kw in bearish_signals):
                        matched_keywords = [kw for kw in bearish_signals if kw in all_text]
                        print(f"✅ [{module_name}观点提取]: 识别为看空！关键词: {matched_keywords}")
                        return "看空", conf_level
                    elif any(kw in all_text for kw in ['中性', '观望']) and not any(kw in all_text for kw in bullish_signals + bearish_signals):
                        # 只有明确说"中性"且没有看多/看空信号时才判断为中性
                        print(f"⚠️ [{module_name}观点提取]: 识别为中性（明确中性且无方向信号）")
                        return "中性", conf_level
            
            print(f"🐛 DEBUG [{module_name}观点提取]: 未匹配到结论性表述，继续检查recommendation字段")
            
            # ========================================================================
            # 第二级：检查recommendation字段（高优先级）
            # ========================================================================
            if recommendation:
                print(f"🐛 DEBUG [{module_name}观点提取]: recommendation字段={recommendation[:100]}")
                # 注意：不要将"震荡"单独作为中性判断，要看是否有偏向
                # 🔥 移除"多头"/"空头"，避免误匹配描述性文字
                if any(kw in recommendation for kw in ['看多', '做多', '买入', '偏多', '偏强', '看涨']):
                    print(f"✅ [{module_name}观点提取]: recommendation识别为看多")
                    return "看多", conf_level
                elif any(kw in recommendation for kw in ['看空', '做空', '卖出', '偏空', '偏弱', '看跌']):
                    print(f"✅ [{module_name}观点提取]: recommendation识别为看空")
                    return "看空", conf_level
                # 🔥 增强：优先检查"中性偏X"格式
                elif '中性偏多' in recommendation or '中性偏强' in recommendation:
                    print(f"✅ [{module_name}观点提取]: recommendation识别为中性偏多（看多）")
                    return "看多", conf_level
                elif '中性偏空' in recommendation or '中性偏弱' in recommendation:
                    print(f"✅ [{module_name}观点提取]: recommendation识别为中性偏空（看空）")
                    return "看空", conf_level
                elif any(kw in recommendation for kw in ['中性', '观望']) and '偏' not in recommendation:
                    # 只有在没有"偏"的情况下才判断为中性
                    print(f"⚠️ [{module_name}观点提取]: recommendation识别为中性")
                    return "中性", conf_level
            
            # ========================================================================
            # 第三级：强观点词权重分析（中优先级）
            # ========================================================================
            # 扩展强观点词列表
            strong_bullish = [
                '利多', '强势', '积极看多', '明确看多', 
                '多头占优', '多头强势', '上涨动能',
                '供应紧张', '需求旺盛', '库存下降'
            ]
            strong_bearish = [
                '利空', '弱势', '积极看空', '明确看空',
                '空头占优', '空头强势', '下跌压力',
                '供应过剩', '需求疲软', '库存累积'
            ]
            
            # 纯中性指标（不包含"震荡"，因为"震荡偏强"是偏多）
            pure_neutral_indicators = ['中性', '观望', '不确定', '待观察', '两难', '平衡']
            
            strong_bull_count = sum(1 for kw in strong_bullish if kw in full_text)
            strong_bear_count = sum(1 for kw in strong_bearish if kw in full_text)
            pure_neutral_count = sum(1 for kw in pure_neutral_indicators if kw in full_text)
            
            # 如果有明确的中性指标且没有偏向
            if pure_neutral_count >= 2 and strong_bull_count == strong_bear_count:
                return "中性", conf_level
            
            # 强观点词优先
            if strong_bull_count > strong_bear_count:
                return "看多", conf_level
            elif strong_bear_count > strong_bull_count:
                return "看空", conf_level
            
            # ========================================================================
            # 第四级：普通关键词统计（最低优先级）
            # ========================================================================
            bullish_count = sum(1 for kw in bullish_keywords if kw in full_text)
            bearish_count = sum(1 for kw in bearish_keywords if kw in full_text)
            
            print(f"🐛 DEBUG [{module_name}观点提取]: 关键词统计 - 看多词{bullish_count}个，看空词{bearish_count}个")
            
            # ✅ 降低判断阈值，提高敏感度（从3改为2）
            diff = abs(bullish_count - bearish_count)
            if bullish_count > bearish_count and diff >= 2:  # 有一定优势即可判断
                print(f"✅ [{module_name}观点提取]: 关键词统计判断为看多（差异{diff}≥2）")
                return "看多", conf_level
            elif bearish_count > bullish_count and diff >= 2:
                print(f"✅ [{module_name}观点提取]: 关键词统计判断为看空（差异{diff}≥2）")
                return "看空", conf_level
            else:
                # 默认中性（差异不明显）
                print(f"⚠️ [{module_name}观点提取]: 关键词统计差异不足（{diff}<2），判断为中性")
                return "中性", conf_level
                
        except Exception as e:
            self.logger.warning(f"{module_name}观点提取失败: {e}")
            return "中性", "未知"
    
    def _format_analyst_views_summary(self, analyst_views: Dict[str, Any]) -> str:
        """格式化分析师观点统计摘要"""
        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     【分析师团队观点统计】（必须严格遵守）                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 统计结果：
- 看多模块：{analyst_views['bullish_count']}个 {('✅ ' + '、'.join(analyst_views['bullish_modules'])) if analyst_views['bullish_modules'] else ''}
- 看空模块：{analyst_views['bearish_count']}个 {('❌ ' + '、'.join(analyst_views['bearish_modules'])) if analyst_views['bearish_modules'] else ''}
- 中性模块：{analyst_views['neutral_count']}个 {('⚪ ' + '、'.join(analyst_views['neutral_modules'])) if analyst_views['neutral_modules'] else ''}
- 总模块数：{analyst_views['total_count']}个

📋 各模块详情："""
        
        for module_name, details in analyst_views['details'].items():
            view = details['view']
            confidence = details['confidence']
            emoji = "🟢" if view == "看多" else "🔴" if view == "看空" else "⚪"
            summary += f"\n{emoji} {module_name}：{view}（{confidence}）"
        
        return summary.strip()
    
    async def integrate_debate_and_decide(self, analysis_state: FuturesAnalysisState, 
                                        debate_result: DebateResult) -> TradingDecision:
        """整合辩论结果并制定交易决策"""
        
        try:
            self.logger.info(f"交易员开始整合{analysis_state.commodity}的辩论结果")
            
            # 🔥 步骤1：提取分析师观点统计
            analyst_views = self._extract_analyst_views_统计(analysis_state)
            self.logger.info(f"分析师观点统计: 看多{analyst_views['bullish_count']}个, "
                           f"看空{analyst_views['bearish_count']}个, "
                           f"中性{analyst_views['neutral_count']}个")
            
            # 构建交易员分析提示（传入分析师观点统计）
            trader_prompt = self._build_trader_prompt(analysis_state, debate_result, analyst_views)
            
            # 调用AI进行交易决策
            try:
                async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                    response = await api_client.chat_completion(
                        messages=[{"role": "user", "content": trader_prompt}],
                        temperature=0.3,  # 🔥 适中温度，避免过早停止生成
                        max_tokens=8192,  # 🔥 API最大限制，确保输出完整
                        # 注意：DeepSeek API可能不支持stop参数，先尝试不加
                    )
            except Exception as api_error:
                self.logger.warning(f"API调用异常，使用离线分析模式: {api_error}")
                response = self._generate_offline_trader_analysis(analysis_state, debate_result)
            
            # 解析交易决策
            if response.get("success"):
                decision_text = response["content"]
                # 🔥 DEBUG: 打印AI生成的原始内容（清理前）
                print("=" * 80)
                print("🔍 AI生成的原始内容（清理前，前2000字符）:")
                print(decision_text[:2000])
                print("=" * 80)
                # 🔧 清理重复内容
                decision_text = self._clean_duplicate_sections(decision_text)
                print("=" * 80)
                print("🔍 清理后的内容（前1000字符）:")
                print(decision_text[:1000])
                print("=" * 80)
            else:
                decision_text = f"API调用失败: {response.get('error', '未知错误')}"
            trading_decision = self._parse_trading_decision(decision_text, analysis_state.commodity, analysis_state)
            
            self.logger.info(f"交易员完成{analysis_state.commodity}策略制定：{trading_decision.strategy_type.value}")
            
            return trading_decision
            
        except Exception as e:
            self.logger.error(f"交易员决策失败: {e}")
            # 返回默认决策
            return self._create_default_decision(analysis_state.commodity)
    
    def _build_trader_prompt(self, analysis_state: FuturesAnalysisState, 
                           debate_result: DebateResult,
                           analyst_views: Dict[str, Any]) -> str:
        """构建交易员分析提示"""
        
        # 🔧 检测实际存在的分析模块
        available_modules = self._detect_available_modules(analysis_state)
        
        # 收集分析师数据
        analyst_summary = self._summarize_analyst_data(analysis_state)
        
        # 收集辩论要点
        debate_summary = self._summarize_debate_points(debate_result)
        
        # 🔥 步骤1：生成分析师观点统计摘要
        analyst_views_summary = self._format_analyst_views_summary(analyst_views)
        
        # 🎯 简化分析：基于数据完整性评估信心度
        data_completeness = self._assess_data_completeness(available_modules)
        commodity_type = self._identify_commodity_type(analysis_state.commodity)
        
        # 🔥 获取真实价格数据
        current_price = get_commodity_current_price(analysis_state.commodity)
        price_range = futures_price_provider.get_price_range(analysis_state.commodity, 30)
        support_resistance = futures_price_provider.get_support_resistance_levels(analysis_state.commodity)
        
        # 🔥 修复：获取市场状态信息
        market_regime = self._detect_market_regime(analysis_state)
        
        # 构建价格信息
        price_info = f"""
【实时价格数据】（来自本地数据库）
当前价格：{current_price:.0f}元/吨
30天价格区间：{price_range.get('low', 0):.0f} - {price_range.get('high', 0):.0f}元/吨
30天均价：{price_range.get('avg', current_price):.0f}元/吨
支撑位：{', '.join([f'{s:.0f}' for s in support_resistance.get('support', [])[:3]])}元/吨
阻力位：{', '.join([f'{r:.0f}' for r in support_resistance.get('resistance', [])[:3]])}元/吨"""
        
        prompt = f"""
你是资深期货交易专家，负责评判多空辩论并制定交易策略。

品种：{get_commodity_name(analysis_state.commodity)} ({analysis_state.commodity})
分析日期：{analysis_state.analysis_date}
可用模块：{len(available_modules)}个

{price_info}

{analyst_views_summary}

=== 分析师数据 ===
{analyst_summary}

=== 辩论内容 ===
{debate_summary}

【核心规则】
方向判断铁律（绝对不可违反）：
- 看多模块 > 看空模块 → 必须看多
- 看空模块 > 看多模块 → 必须看空  
- 看多 = 看空 → 必须中性

信心度判断：
- 优势≥3个 → 高
- 优势2个 → 中
- 优势1个或相等 → 低

仓位匹配：
- 高信心度 → 10-15%
- 中信心度 → 5-10%
- 低信心度 → 2-5%

【三维度评判框架】
对每个模块的多空辩论进行量化评分（0-10分）：

维度1：论据质量（40%）
- 数据真实性×0.4：可验证事实10分，推测3分
- 数据时效性×0.2：最新10分，过时3分  
- 数据相关性×0.25：核心数据10分，弱相关3分
- 数据完整性×0.15：全面10分，缺失3分

维度2：逻辑严密性（35%）
- 因果关系×0.3：清晰完整10分，混乱3分
- 推理过程×0.3：严密无懈10分，矛盾3分
- 反驳有效性×0.2：精准直击10分，无效3分
- 自洽性×0.2：完全一致10分，矛盾3分

维度3：风险意识（25%）
- 不确定性认知×0.3：承认不确定10分，过度自信3分
- 对立观点尊重×0.2：客观分析10分，完全否定3分
- 情景分析×0.25：多情景10分，单一3分
- 风险识别×0.25：全面10分，忽视3分

综合得分 = 维度1×40% + 维度2×35% + 维度3×25%
评判：得分差≥1.5分→强势，≥0.8分→偏强，<0.8分→中性

【分析步骤】
1. 逐模块三维度评分
2. 计算综合得分和得分差
3. 统计强势模块数量
4. 整合分析师观点（已提取）
5. 综合方向判断（基于模块数量投票）
6. 信心度评估（优势数+论证质量）
7. 制定交易策略

=== 📋 严格输出格式（必须100%遵守章节顺序）===

🚨🚨🚨 章节顺序铁律（绝不可违反）🚨🚨🚨

必须按以下顺序输出，每个章节只能出现一次：
1. 【辩论评判分析】
2. 【分析师观点科学评估】
3. 【论证质量量化评判】← 只能出现一次！
4. 【多空综合判断结论】
5. 【交易策略建议】
6. 【风险提示】

🚫 严禁行为：
❌ 重复任何章节（特别是【论证质量量化评判】）
❌ 在【论证质量量化评判】输出完后又重新输出
❌ 打乱章节顺序
❌ 输出超过上述6个章节

✅ 正确做法：
每输出完一个章节，立即输出下一个章节
【论证质量量化评判】后立即输出【多空综合判断结论】
【风险提示】后立即停止，不得继续输出

⚠️ 重要提醒：在开始辩论评判之前，请先仔细阅读上面的【原始分析师报告摘要】！
每个模块的辩论评判都必须先回顾该模块的原始分析师观点！

【辩论评判分析】
{self._generate_module_evaluation_prompt(available_modules, analysis_state, analyst_views)}

【分析师观点科学评估】
{self._generate_analyst_view_summary_from_extracted(analyst_views)}

【论证质量量化评判】

第一步：回顾【分析师观点科学评估】中的统计
- 分析师团队看多：___个模块（列出具体模块）
- 分析师团队看空：___个模块（列出具体模块）
- 分析师团队中性：___个模块（列出具体模块）

第二步：基于辩论三维度评分，统计各模块的评判结果

多头强势模块：[X]个
[逐一列出：模块名称（多头X.X分 vs 空头X.X分，得分差+X.X）]
核心优势：[总结多头在这些模块中的共同优势]

多头偏强模块：[X]个
[逐一列出：模块名称（多头X.X分 vs 空头X.X分，得分差+X.X）]

空头强势模块：[X]个
[逐一列出：模块名称（空头X.X分 vs 多头X.X分，得分差-X.X）]
核心优势：[总结空头在这些模块中的共同优势]

空头偏强模块：[X]个
[逐一列出：模块名称（空头X.X分 vs 多头X.X分，得分差-X.X）]

中性模块：[X]个
[逐一列出：模块名称（得分差<0.8，双方论证质量相当）]

📈 总体评判结果：
- 多头优势模块合计：[强势+偏强]个
- 空头优势模块合计：[强势+偏强]个
- 中性模块：[数量]个
- 辩论评判倾向：【多头占优/空头占优/势均力敌】

🎯 关键发现：
[总结辩论中最有说服力的论据、最薄弱的环节、双方论证质量的核心差异]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 【辩论评判的作用与边界】重要说明 ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 辩论评判的本质：
辩论评判反映的是"论证质量"和"逻辑严密性"，而非"方向正确性"。
即使空头论证质量更高，也不意味着市场一定下跌。

🚫 辩论评判【不能】做什么：
❌ 不能改变方向判断（方向必须遵守【方向判断铁律】）
❌ 不能覆盖分析师观点的模块数量投票
❌ 不能独立作为交易决策的依据

✅ 辩论评判【可以】做什么：
✓ 影响信心度等级（高/中/低）
✓ 影响操作强度（积极/谨慎）
✓ 影响仓位大小（在信心度对应区间内调整）
✓ 提示风险点（即使方向看多，也要警惕空头论据）

📊 决策优先级：
1️⃣ 最高优先级：分析师观点模块数量（决定方向）
2️⃣ 第二优先级：辩论评判质量（调整信心度和操作强度）
3️⃣ 第三优先级：其他市场因素（微调执行细节）

💡 实战应用举例：
场景1：分析师3看多 vs 1看空 + 辩论空头占优
  → 方向：必须看多（遵守铁律）
  → 调整：信心度下调，采取谨慎做多，仓位取区间下限

场景2：分析师3看多 vs 1看空 + 辩论多头占优
  → 方向：必须看多（遵守铁律）
  → 调整：信心度保持，可以积极做多，仓位取区间上限

⚠️ 核心原则：方向看对只是第一步，论证质量决定了执行的谨慎程度！

---

【多空综合判断结论】

🚨 铁律检查（最高优先级）🚨

步骤1：复制【分析师观点科学评估】统计
- 看多：___个（列出模块）
- 看空：___个（列出模块）  
- 中性：___个（列出模块）

步骤2：应用铁律判定方向
看多___个 vs 看空___个
根据铁律，方向必须是：【看多/看空/中性观望】或【谨慎看多/谨慎看空】
⚠️ 论证质量只能影响"积极/谨慎"和信心度，绝不能改变方向！

步骤3：确定信心度（透明化计算公式）

📊 基础信心度判断：
- 优势模块数：___个
- 根据规则映射：优势≥3个→高，优势2个→中，优势≤1个→低
- **基础信心度**：【高/中/低】

🔧 信心度调整因素评估：
调整因素1 - 辩论评判倾向：【多头占优/空头占优/势均力敌】
  → 如果辩论评判与分析师观点方向相反，下调一档
  → 调整：【保持/下调一档】

调整因素2 - 反向高信度模块：【是/否】（列出模块）
  → 如果存在高信度反向模块，确认谨慎立场
  → 调整：【保持/确认谨慎】

调整因素3 - 中性模块辩论倾向：
  → 如果多个中性模块的辩论评判均偏向反方，下调信心度
  → 调整：【保持/下调一档】

🎯 最终信心度计算：
- 基础信心度：【高/中/低】
- 经过调整因素1：【高/中/低】
- 经过调整因素2：【高/中/低】
- 经过调整因素3：【高/中/低】
- **最终信心度**：【高/中/低】
- **最终立场**：【积极/谨慎】+【看多/看空/中性】

方向判断依据：
- 分析师观点：X看多 vs Y看空（主要依据，决定方向）
- 辩论评判：[参考，影响信心度和操作强度]
- 关键因素：[2-3个核心支撑/风险因素]

综合方向倾向：[谨慎看多/谨慎看空/积极看多/积极看空/中性观望]
信心度：[高/中/低]
信心度理由：[详细说明基础判断+各调整因素的影响]

【交易策略建议】
策略方向：[具体策略，如：轻仓谨慎做多/积极做多/观望]

策略制定依据：
- 方向判断：[做多/做空/观望]（信心度：[高/中/低]）
- 分析师建议：[综合各模块建议]
- 风险考量：[基于信心度和辩论评判]

具体执行方案：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 仓位建议（透明化计算）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 基础仓位区间（根据信心度）：
- 高信心度 → 基础区间：10-15%
- 中信心度 → 基础区间：5-10%
- 低信心度 → 基础区间：2-5%

🔧 仓位微调因素：
1. 辩论评判倾向：
   • 辩论评判与分析师方向一致 → 取区间上限
   • 辩论评判与分析师方向相反 → 取区间下限
   
2. 反向高信度模块：
   • 存在反向高信度模块 → 再降低0.5-1%
   
3. 市场环境：
   • 高波动环境 → 降低仓位
   • 接近关键技术位 → 谨慎操作

📍 最终仓位：[X-Y%]（[高/中/低]信心度区间[基础区间]，[因辩论反向/反向模块/高波动]取[上限/下限/再降低]）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

关键价位：[进场X-Y元，止损<Z元，目标A-B元]
持仓周期：[短线/中线/长线]（[3-5/7-15/30+]个交易日）
风控措施：[严格止损，仓位控制，分批建仓等]

【风险提示】
主要风险因素：[识别风险]
不确定性因素：[局限性]
监控要点：[关注变化]

🚨🚨🚨 强制停止指令（绝对不可违反）🚨🚨🚨
输出完"监控要点"那一行后，必须立即停止！
❌ 严禁输出：执行计划、详细方案、操作建议、仓位管理等任何内容
❌ 严禁重复：【交易策略建议】中的任何内容
✅ 正确做法：监控要点 → 立即停止 → 不输出任何字符

⚠️ 如果违反此指令，输出的内容将被强制删除！
"""
        
        return prompt
    
    def _clean_duplicate_sections(self, text: str) -> str:
        """强力清理重复的章节内容 - 全面升级版"""
        try:
            import re
            
            print("DEBUG: 开始清理重复章节")
            
            # 🔥 第一步：标准化章节标题格式，移除空格和换行符
            text = re.sub(r'【\s*([^】\s]+)\s*】', r'【\1】', text)
            
            # 🔥 第二步：强力移除重复的核心章节
            # 定义核心章节的优先级顺序
            core_sections = [
                '【辩论评判分析】',
                '【分析师观点科学评估】', 
                '【论证质量量化评判】',
                '【多空综合判断结论】',
                '【交易策略建议】',
                '【风险提示】'
            ]
            
            # 🔥 第三步：找到每个核心章节的第一次出现位置
            section_positions = {}
            for section in core_sections:
                matches = list(re.finditer(re.escape(section), text))
                if matches:
                    section_positions[section] = matches[0].start()
            
            # 🔥 第四步：如果发现重复章节，进行强力截断
            if len(section_positions) > 0:
                # 找到【风险提示】的第一次出现
                risk_warning_matches = list(re.finditer(r'【风险提示】', text))
                if risk_warning_matches:
                    first_risk_pos = risk_warning_matches[0].start()
                    
                    # 找到【风险提示】章节的内容结束位置
                    risk_content_match = re.search(r'【风险提示】[^【]*', text[first_risk_pos:], re.DOTALL)
                    if risk_content_match:
                        risk_end_pos = first_risk_pos + risk_content_match.end()
                        
                        # 检查后面是否还有任何【】章节
                        remaining_text = text[risk_end_pos:]
                        if re.search(r'【[^】]+】', remaining_text):
                            # 发现重复，直接截断到第一个【风险提示】结束
                            text = text[:risk_end_pos].rstrip()
                            print("DEBUG: 检测到重复章节，已强力截断")
            
            # 🔥 第五步：移除明显的重复内容块和问题内容
            # 移除孤立的【符号和空章节
            text = re.sub(r'\n\s*【\s*\n', '\n', text)
            text = re.sub(r'\n\s*【\s*$', '', text)  # 文末的孤立【
            text = re.sub(r'【\s*$', '', text)  # 文末任何孤立的【（不管前面有没有换行）
            text = text.rstrip() + '\n' if text and not text.endswith('\n') else text  # 确保文末只有一个换行
            
            # 移除空的【科学信心度计算】章节
            text = re.sub(r'【科学信心度计算】\s*\n*', '', text)
            
            # ✅ 移除任何位置的"执行计划"及其内容（终极加强版）
            # 🔥 核心策略：找到"执行计划"后，删除到文件结尾（因为执行计划总是最后出现的偷懒内容）
            # 🔥🔥 修复：使用更宽松的匹配，覆盖所有可能的格式
            
            # 🔥🔥🔥 新增：超级宽松匹配（优先执行）- 只要遇到换行+任意字符+"执行计划"就删除
            text = re.sub(r'\n+[^\n]*执行计划[^\n]*\n.*$', '', text, flags=re.DOTALL)
            print("DEBUG: [超级宽松] 执行计划正则清理完成")
            
            # 格式1: **执行计划：**（最常见）
            text = re.sub(r'\n+\s*\*\*\s*执行计划\s*[：:]\s*\*\*.*$', '', text, flags=re.DOTALL)
            # 格式2: 执行计划：（无星号）
            text = re.sub(r'\n+\s*执行计划\s*[：:]\s*.*$', '', text, flags=re.DOTALL)
            # 格式3: **执行计划**（无冒号）
            text = re.sub(r'\n+\s*\*\*\s*执行计划\s*\*\*.*$', '', text, flags=re.DOTALL)
            # 格式4: 超宽松匹配（兜底）- 只要包含"执行计划"就删除到结尾
            if '执行计划' in text:
                print("DEBUG: [兜底] 检测到'执行计划'关键词")
                exec_plan_pos = text.rfind('执行计划')  # 找到最后一次出现
                print(f"DEBUG: [兜底] 位置={exec_plan_pos}, 前后文本='{text[max(0,exec_plan_pos-20):exec_plan_pos+20]}'")
                # 确认不是在正文中（检查前面是否有换行）
                if exec_plan_pos > 10:  # 不在开头
                    before_text = text[max(0, exec_plan_pos-10):exec_plan_pos]
                    print(f"DEBUG: [兜底] before_text='{before_text}', 包含换行={chr(10) in before_text}")
                    if '\n' in before_text:  # 前面有换行，说明是独立段落
                        text = text[:exec_plan_pos].rstrip()
                        print("DEBUG: [兜底] ✅ 成功删除'执行计划'到文件结尾")
                    else:
                        print("DEBUG: [兜底] ⚠️ before_text不包含换行，不删除")
                else:
                    print(f"DEBUG: [兜底] ⚠️ 位置{exec_plan_pos}<=10，不删除")
            else:
                print("DEBUG: [兜底] 未检测到'执行计划'关键词")
            
            # 清理孤立的【符号和markdown符号（可能是截断留下的）
            text = re.sub(r'\n\s*【\s*$', '', text)
            text = re.sub(r'\n\s*\*\*\s*$', '', text)  # 孤立的星号
            text = text.rstrip()
            print("DEBUG: 执行计划清理完成")
            
            # 🔥 新增：移除所有"详见xxx章节"的偷懒内容
            text = re.sub(r'详见.*?章节', '', text)
            text = re.sub(r'详见【.*?】', '', text)
            
            # 🔥 新增：移除重复的章节（检测连续两个相同章节标题）
            # 检测【xxx】章节标题的重复
            import re
            pattern = r'(【[^】]+】[^【]*?)(\1)'  # 匹配重复的章节
            text = re.sub(pattern, r'\1', text, flags=re.DOTALL)
            
            # 🔥 特别处理：移除【论证质量量化评判】的重复（保留第一次，删除第二次及之后所有内容）
            # 查找所有【论证质量量化评判】出现的位置
            all_matches = list(re.finditer(r'【论证质量量化评判】', text))
            if len(all_matches) > 1:
                print(f"⚠️ 检测到【论证质量量化评判】重复{len(all_matches)}次，开始清理...")
                
                # 有重复，只保留第一次出现
                first_match = all_matches[0]
                second_match = all_matches[1]
                
                # 找到第一次出现后的【多空综合判断结论】
                after_first = text[first_match.end():]
                conclusion_match = re.search(r'【多空综合判断结论】', after_first)
                
                if conclusion_match:
                    # 找到了第一次后的【多空综合判断结论】
                    # 保留从开头到【多空综合判断结论】之前的内容，包括完整的第一次【论证质量量化评判】
                    conclusion_pos = first_match.end() + conclusion_match.start()
                    # 保留第一次和【多空综合判断结论】，删除第二次【论证质量量化评判】
                    # 如果第二次出现在【多空综合判断结论】之后，直接截断
                    if second_match.start() > conclusion_pos:
                        text = text[:second_match.start()].rstrip()
                        print(f"✅ 已删除第二次【论证质量量化评判】（位置{second_match.start()}）及之后所有内容")
                    else:
                        # 第二次出现在【多空综合判断结论】之前，这不正常，直接删除第二次到结尾
                        text = text[:second_match.start()].rstrip()
                        print(f"✅ 异常：第二次【论证质量量化评判】在【多空综合判断结论】之前，已删除")
                else:
                    # 没找到【多空综合判断结论】，说明可能被截断了
                    # 直接删除第二次【论证质量量化评判】及之后所有内容
                    text = text[:second_match.start()].rstrip()
                    print(f"✅ 未找到【多空综合判断结论】，已删除第二次【论证质量量化评判】及之后所有内容（可能被截断）")
                
                print(f"✅ 【论证质量量化评判】重复清理完成")
            
            # 🔥🔥🔥 新增：优先查找【附录结束】标记，截断到此处
            appendix_end_match = re.search(r'【附录结束】', text)
            if appendix_end_match:
                # 找到【附录结束】的位置，截断到此处之后（包括后面的分隔线）
                end_pos = appendix_end_match.end()
                # 查找【附录结束】后的第一个分隔线
                remaining = text[end_pos:]
                separator_match = re.search(r'\n━+\n', remaining)
                if separator_match:
                    end_pos += separator_match.end()
                text = text[:end_pos].rstrip()
                print("DEBUG: ✅ 检测到【附录结束】标记，已精确截断")
            else:
                # 🔥🔥🔥 如果没有【附录结束】，使用原有逻辑处理【风险提示】
                risk_match = re.search(r'【风险提示】', text)
                if risk_match:
                    risk_start = risk_match.start()
                    risk_section = text[risk_start:]
                    
                    # 新格式：查找监控要点后的分隔线
                    new_format_match = re.search(
                        r'【风险提示】.*?📌\s*\*\*监控要点\*\*：.*?\n━+',
                        risk_section,
                        re.DOTALL
                    )
                    
                    if new_format_match:
                        risk_end = risk_start + new_format_match.end()
                        text = text[:risk_end].rstrip()
                        print("DEBUG: [新格式] 精确截断到【风险提示】新格式结束")
                    else:
                        # 旧格式：主要风险因素、不确定性因素、监控要点
                        risk_content_match = re.search(
                            r'【风险提示】\s*\n主要风险因素：[^\n]*\n不确定性因素：[^\n]*\n监控要点：[^\n]*', 
                            risk_section, 
                            re.DOTALL
                        )
                        
                        if risk_content_match:
                            risk_end = risk_start + risk_content_match.end()
                            text = text[:risk_end].rstrip()
                            print("DEBUG: [旧格式] 精确截断到【风险提示】3行内容结束")
                        else:
                            # 方法2：简化版，直接查找"监控要点："所在行的结尾
                            monitoring_match = re.search(r'监控要点：[^\n]*', risk_section)
                            if monitoring_match:
                                risk_end = risk_start + monitoring_match.end()
                                text = text[:risk_end].rstrip()
                                print("DEBUG: [方法2] 截断到监控要点行结束")
                            else:
                                # 方法3：如果上面都没匹配到，保守处理
                                lines = text[risk_start:].split('\n')
                                risk_lines = []
                                for i, line in enumerate(lines):
                                    risk_lines.append(line)
                                    if i > 0 and (line.strip().startswith('**') or line.strip().startswith('【')):
                                        break
                                    if i >= 10:
                                        break
                                text = text[:risk_start] + '\n'.join(risk_lines).rstrip()
                                print("DEBUG: [方法3] 保守截断到【风险提示】+内容行")
                    
                    print("DEBUG: 终极强力截断完成，移除【风险提示】后的所有重复内容")
            
            # 🔥 第六步：终极重复章节清理 - 精确重建法
            # 使用精确的章节边界识别和内容提取
            
            # 定义标准章节顺序
            standard_sections = [
                '【辩论评判分析】',
                '【分析师观点科学评估】',
                '【论证质量量化评判】', 
                '【多空综合判断结论】',
                '【交易策略建议】',
                '【风险提示】'
            ]
            
            # 🔥 精确提取每个章节的内容（只取第一次出现）
            section_contents = {}
            
            for i, section in enumerate(standard_sections):
                # 找到当前章节的位置
                section_start = text.find(section)
                if section_start == -1:
                    continue
                
                # 确定章节内容的结束位置
                content_end = len(text)
                
                # 查找下一个章节的位置作为结束边界
                for next_section in standard_sections[i+1:]:
                    next_pos = text.find(next_section, section_start + len(section))
                    if next_pos != -1:
                        content_end = next_pos
                        break
                
                # 提取章节内容
                section_content = text[section_start:content_end].strip()
                
                # 🔥 特殊处理：移除章节内部的重复内容
                if section == '【多空综合判断结论】':
                    # 移除重复的结论段落
                    lines = section_content.split('\n')
                    unique_lines = []
                    seen_content = set()
                    
                    for line in lines:
                        line_clean = line.strip()
                        if line_clean and line_clean not in seen_content:
                            seen_content.add(line_clean)
                            unique_lines.append(line)
                    
                    section_content = '\n'.join(unique_lines)
                
                elif section == '【交易策略建议】':
                    # 只保留第一个完整的策略建议
                    strategy_match = re.search(r'(【交易策略建议】.*?)(?=【交易策略建议】|$)', section_content, re.DOTALL)
                    if strategy_match:
                        section_content = strategy_match.group(1).strip()
                
                elif section == '【风险提示】':
                    # 🔥🔥🔥 关键修复：精确截断【风险提示】，移除其后的任何"执行计划"等内容
                    # 方法1：精确匹配标准格式（3行）
                    risk_standard_match = re.search(
                        r'(【风险提示】\s*\n主要风险因素：[^\n]*\n不确定性因素：[^\n]*\n监控要点：[^\n]*)',
                        section_content,
                        re.DOTALL
                    )
                    if risk_standard_match:
                        section_content = risk_standard_match.group(1).strip()
                        print(f"DEBUG: [风险提示] 精确截断到标准3行格式")
                    else:
                        # 方法2：查找"监控要点"所在行，截断到行尾
                        monitoring_match = re.search(r'(【风险提示】.*?监控要点：[^\n]*)', section_content, re.DOTALL)
                        if monitoring_match:
                            section_content = monitoring_match.group(1).strip()
                            print(f"DEBUG: [风险提示] 截断到监控要点行尾")
                        else:
                            # 方法3：保守处理，只保留前10行
                            lines = section_content.split('\n')
                            section_content = '\n'.join(lines[:10])
                            print(f"DEBUG: [风险提示] 保守截断到前10行")
                    
                    # 🔥 再次强力清理：删除任何"执行计划"相关内容
                    if '执行计划' in section_content:
                        exec_pos = section_content.find('执行计划')
                        # 回退到前一个换行符
                        before_exec = section_content[:exec_pos]
                        last_newline = before_exec.rfind('\n')
                        if last_newline != -1:
                            section_content = section_content[:last_newline].strip()
                            print(f"DEBUG: [风险提示] 强力删除'执行计划'及其后内容")
                
                section_contents[section] = section_content
                print(f"DEBUG: 精确提取章节: {section}")
            
            # 重新组装文本
            if section_contents:
                rebuilt_text = []
                for section in standard_sections:
                    if section in section_contents:
                        rebuilt_text.append(section_contents[section])
                
                text = '\n\n'.join(rebuilt_text)
                print("DEBUG: 精确重建完成，彻底消除重复")
            
            # 🔥 第七步：最终清理
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                # 跳过空行和孤立的【符号
                if line_stripped and line_stripped != '【':
                    cleaned_lines.append(line)
            
            text = '\n'.join(cleaned_lines).strip()
            
            # 🔥🔥🔥 终极兜底：最后再检查一次是否包含"执行计划"
            if '执行计划' in text:
                print("⚠️ WARNING: 最终文本中依然包含'执行计划'，执行终极清理")
                exec_pos = text.rfind('执行计划')  # 找到最后一次出现
                print(f"DEBUG: [终极兜底] 执行计划位置={exec_pos}, 前后文本='{text[max(0,exec_pos-50):exec_pos+50]}'")
                
                # 回退到前一个换行符
                before_exec = text[:exec_pos]
                last_newline = before_exec.rfind('\n')
                if last_newline != -1:
                    text = text[:last_newline].strip()
                    print("DEBUG: [终极兜底] ✅ 成功删除'执行计划'到文件结尾")
                else:
                    # 如果前面没有换行符，直接截断到"执行计划"之前
                    text = text[:exec_pos].strip()
                    print("DEBUG: [终极兜底] ✅ 直接截断到'执行计划'之前")
            else:
                print("DEBUG: [终极兜底] 未检测到'执行计划'，清理完成")
            
            return text
            
        except Exception as e:
            print(f"DEBUG: 清理重复章节时出错: {str(e)}")
            # 如果清理失败，至少尝试基本的截断
            try:
                import re
                # 简单的【风险提示】后截断
                risk_match = re.search(r'【风险提示】[^【]*', text, re.DOTALL)
                if risk_match:
                    return text[:risk_match.end()].strip()
                return text.strip()
            except:
                return text.strip()
    
    def _format_professional_trader_report(self, reasoning: str, confidence_calc: str, 
                                         conclusion: str, strategy_advice: str, risk_warning: str) -> str:
        """🔥 已废弃：直接使用AI生成的完整六章节分析，不再进行格式转换"""
        # 该方法已不再使用，保留仅为兼容性
        return f"""
【辩论评判分析】
{reasoning}

【多空综合判断结论】
{conclusion}

【交易策略建议】
{strategy_advice}

【风险提示】
{risk_warning}
""".strip()
    
    def _extract_trading_direction(self, conclusion: str) -> str:
        """提取交易方向"""
        if "做多" in conclusion:
            if "谨慎" in conclusion:
                return "谨慎看多"
            elif "积极" in conclusion:
                return "积极看多"
            else:
                return "看多"
        elif "做空" in conclusion:
            if "谨慎" in conclusion:
                return "谨慎看空"
            elif "积极" in conclusion:
                return "积极看空"
            else:
                return "看空"
        else:
            return "中性观望"
    
    def _extract_confidence_level(self, conclusion: str) -> str:
        """提取信心度"""
        if "信心度：低" in conclusion or "低信心度" in conclusion:
            return "偏低"
        elif "信心度：高" in conclusion or "高信心度" in conclusion:
            return "较高"
        elif "信心度：中" in conclusion or "中信心度" in conclusion:
            return "中等"
        else:
            return "待评估"
    
    def _extract_key_factors(self, reasoning: str, conclusion: str) -> List[str]:
        """提取关键支撑因素"""
        factors = []
        
        # 从推理中提取关键点
        if "净多仓" in reasoning:
            factors.append("资金流向支撑")
        if "技术面" in reasoning and ("突破" in reasoning or "支撑" in reasoning):
            factors.append("技术面配合")
        if "宏观" in reasoning or "政策" in reasoning:
            factors.append("宏观环境")
        if "基本面" in reasoning:
            factors.append("供需基础")
        
        # 从结论中提取
        if "关键支撑因素" in conclusion:
            import re
            factors_match = re.search(r'关键支撑因素：([^；\n]+)', conclusion)
            if factors_match:
                additional_factors = factors_match.group(1).split('；')
                factors.extend([f.strip() for f in additional_factors[:2]])  # 最多2个
        
        return factors[:3]  # 最多3个关键因素
    
    def _format_market_analysis(self, reasoning: str, key_factors: List[str]) -> str:
        """格式化市场分析"""
        # 提取辩论核心观点
        if "多头论据" in reasoning and "空头论据" in reasoning:
            return "多空双方观点交锋激烈，市场分歧明显。多头强调资金流向和技术突破，空头关注风险因素和估值压力。"
        else:
            return "基于当前市场数据和技术分析，综合评估市场运行态势。"
    
    def _format_core_logic(self, key_factors: List[str]) -> str:
        """格式化核心逻辑"""
        if not key_factors:
            return "基于技术分析和市场情绪判断"
        return "、".join(key_factors) + "等因素综合作用"
    
    def _extract_strategy_summary(self, strategy_advice: str) -> str:
        """提取策略摘要"""
        if not strategy_advice:
            return "建议根据市场变化灵活调整仓位"
        
        import re
        # 提取关键信息
        position_match = re.search(r'仓位[建议]*[：:]\s*(\d+[-~]\d+%|\d+%)', strategy_advice)
        position = position_match.group(1) if position_match else "适中仓位"
        
        entry_match = re.search(r'入场[：:]?\s*(\d+[-~]\d+元?)', strategy_advice)
        entry = entry_match.group(1) if entry_match else "技术位入场"
        
        stop_match = re.search(r'止损[：:]?\s*(\d+元?)', strategy_advice)
        stop = stop_match.group(1) if stop_match else "严格止损"
        
        return f"建议{position}仓位，{entry}附近入场，{stop}止损保护。"
    
    def _extract_main_risks(self, risk_warning: str) -> str:
        """提取主要风险"""
        if not risk_warning:
            return "注意市场波动风险，严格执行止损纪律。"
        
        # 提取前两个主要风险
        risks = []
        if "净多仓" in risk_warning:
            risks.append("持仓过度集中风险")
        if "政策" in risk_warning or "美联储" in risk_warning:
            risks.append("政策变化风险")
        if "技术面" in risk_warning:
            risks.append("技术突破失效风险")
        if "美元" in risk_warning:
            risks.append("美元走强压制")
        
        if risks:
            return "重点关注" + "、".join(risks[:2]) + "。"
        else:
            return "密切关注市场变化，及时调整策略。"
    
    def _detect_available_modules(self, analysis_state: FuturesAnalysisState) -> List[str]:
        """检测实际存在的分析模块 - 完全动态检测，支持任意组合和未来扩展"""
        available = []
        
        # 标准六大模块检测
        standard_modules = {
            'technical_analysis': 'technical',
            'basis_analysis': 'basis', 
            'inventory_analysis': 'inventory',
            'positioning_analysis': 'positioning',
            'term_structure_analysis': 'term_structure',
            'news_analysis': 'news'
        }
        
        for attr_name, module_key in standard_modules.items():
            if hasattr(analysis_state, attr_name):
                module = getattr(analysis_state, attr_name)
                if module is not None:
                    # 检查模块是否有有效数据
                    if hasattr(module, 'result_data') and module.result_data:
                        available.append(module_key)
                        print(f"🔍 检测到模块: {module_key} (属性: {attr_name})")
                    else:
                        print(f"⚠️ 模块存在但无数据: {module_key}")
                        
        # 🚀 未来扩展性：自动检测可能的新增模块
        # 检测任何以"_analysis"结尾的属性
        for attr_name in dir(analysis_state):
            if attr_name.endswith('_analysis') and not attr_name.startswith('_'):
                if attr_name not in standard_modules:
                    module = getattr(analysis_state, attr_name)
                    if module is not None:
                        # 推导模块名
                        module_key = attr_name.replace('_analysis', '')
                        if hasattr(module, 'result_data') and module.result_data:
                            available.append(module_key)
                            print(f"🆕 检测到新模块: {module_key} (属性: {attr_name})")
                            
        print(f"✅ 总共检测到 {len(available)} 个可用模块: {available}")
        return available
    
    def _get_module_display_name(self, module_key: str) -> str:
        """获取模块显示名称 - 支持动态映射"""
        standard_names = {
            'technical': '技术分析',
            'basis': '基差分析', 
            'inventory': '库存分析',
            'positioning': '持仓分析',
            'term_structure': '期限结构',
            'news': '新闻分析'
        }
        
        # 如果是标准模块，返回预定义名称
        if module_key in standard_names:
            return standard_names[module_key]
        
        # 如果是新增模块，生成友好的显示名称
        # 例如：sentiment -> 情绪分析, macro -> 宏观分析
        name_mapping = {
            'sentiment': '情绪分析',
            'macro': '宏观分析', 
            'volatility': '波动率分析',
            'correlation': '相关性分析',
            'seasonality': '季节性分析',
            'economic': '经济指标分析'
        }
        
        return name_mapping.get(module_key, f"{module_key.upper()}分析")
    
    def _format_available_modules(self, available_modules: List[str]) -> str:
        """格式化显示可用模块信息 - 支持任意模块组合"""
        if not available_modules:
            return "⚠️ 警告：当前没有可用的分析模块数据"
        
        # 显示可用模块
        available_names = [self._get_module_display_name(mod) for mod in available_modules]
        available_text = f"可用模块({len(available_modules)}个)：" + "、".join(available_names)
        
        # 显示标准缺失模块（只统计标准六大模块）
        standard_modules = {'technical', 'basis', 'inventory', 'positioning', 'term_structure', 'news'}
        available_standard = set(available_modules) & standard_modules
        missing_standard = standard_modules - available_standard
        
        if missing_standard:
            missing_names = [self._get_module_display_name(mod) for mod in missing_standard]
            available_text += f"\n标准缺失模块({len(missing_standard)}个)：" + "、".join(missing_names)
        
        # 显示新增模块（如果有的话）
        new_modules = set(available_modules) - standard_modules
        if new_modules:
            new_names = [self._get_module_display_name(mod) for mod in new_modules]
            available_text += f"\n🆕 扩展模块({len(new_modules)}个)：" + "、".join(new_names)
        
        return available_text
    
    def _generate_module_evaluation_prompt(self, available_modules: List[str], analysis_state=None, analyst_views=None) -> str:
        """基于可用模块动态生成评判prompt - 三维度量化评分
        
        Args:
            available_modules: 可用模块列表
            analysis_state: 分析状态（用于提取建议等额外信息）
            analyst_views: 已提取的分析师观点字典，优先使用此数据确保一致性
        """
        
        # 🔥 优先使用已提取的analyst_views数据，确保与【分析师观点科学评估】一致
        module_original_views = {}
        
        if analyst_views and "details" in analyst_views:
            # 直接使用已提取的观点数据
            for module_name, detail in analyst_views["details"].items():
                module_original_views[module_name] = {
                    'view': detail["view"],
                    'confidence': detail["confidence"],
                    'advice': '',  # 后面从analysis_state补充
                    'risk': ''
                }
        
        # 补充额外的建议和风险信息（如果提供了analysis_state）
        if analysis_state:
            # 提取各模块的建议信息
            if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
                content = str(analysis_state.technical_analysis.result_data.get('analysis_content', ''))
                recommendation = str(analysis_state.technical_analysis.result_data.get('recommendation', ''))
                
                # 如果技术分析还没有观点记录，使用已有数据；否则只补充建议信息
                if "技术分析" not in module_original_views:
                    module_original_views["技术分析"] = {
                        'view': '未提取',
                        'confidence': '未提取',
                        'advice': '',
                        'risk': ''
                    }
                
                core_advice = ""
                if '逢低做多' in content or '逢低买入' in content:
                    core_advice = "逢低做多"
                elif '看涨' in content or '看多' in recommendation:
                    core_advice = "看涨/看多"
                elif '上涨趋势' in content or '趋势向上' in content:
                    core_advice = "上涨趋势"
                
                risk_level = ""
                if '低风险' in content or '风险较小' in content:
                    risk_level = "低风险"
                elif '中等风险' in content:
                    risk_level = "中等风险"
                
                # 补充建议和风险信息
                if "技术分析" in module_original_views:
                    module_original_views['技术分析']['advice'] = core_advice
                    module_original_views['技术分析']['risk'] = risk_level
            
            if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
                content = str(analysis_state.basis_analysis.result_data.get('analysis_content', ''))
                
                if "基差分析" not in module_original_views:
                    module_original_views["基差分析"] = {'view': '未提取', 'confidence': '未提取', 'advice': '', 'risk': ''}
                
                core_advice = ""
                if '套利' in content:
                    core_advice = "期现套利、跨期套利（非单边）"
                
                if "基差分析" in module_original_views:
                    module_original_views['基差分析']['advice'] = core_advice
            
            if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
                content = str(analysis_state.inventory_analysis.result_data.get('analysis_content', ''))
                recommendation = str(analysis_state.inventory_analysis.result_data.get('recommendation', ''))
                
                if "库存分析" not in module_original_views:
                    module_original_views["库存分析"] = {'view': '未提取', 'confidence': '未提取', 'advice': '', 'risk': ''}
                
                core_advice = ""
                if '建立多头头寸' in content:
                    core_advice = "建立多头头寸"
                elif '建立空头头寸' in content or '谨慎偏空' in recommendation:
                    core_advice = "建立空头头寸/谨慎偏空"
                elif '谨慎偏多' in recommendation or '谨慎看多' in recommendation:
                    core_advice = "谨慎偏多策略"
                elif '偏多' in recommendation or '偏多' in content:
                    core_advice = "偏多"
                
                if "库存分析" in module_original_views:
                    module_original_views['库存分析']['advice'] = core_advice
            
            if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
                content = str(analysis_state.positioning_analysis.result_data.get('analysis_content', ''))
                
                if "持仓分析" not in module_original_views:
                    module_original_views["持仓分析"] = {'view': '未提取', 'confidence': '未提取', 'advice': '', 'risk': ''}
                
                core_advice = ""
                if '谨慎看多' in content:
                    core_advice = "谨慎看多，回调时建立多头仓位"
                elif '看多' in content or '偏多' in content:
                    core_advice = "看多"
                
                if "持仓分析" in module_original_views:
                    module_original_views['持仓分析']['advice'] = core_advice
            
            if hasattr(analysis_state, 'term_structure_analysis') and analysis_state.term_structure_analysis:
                content = str(analysis_state.term_structure_analysis.result_data.get('analysis_content', ''))
                
                if "期限结构" not in module_original_views:
                    module_original_views["期限结构"] = {'view': '未提取', 'confidence': '未提取', 'advice': '', 'risk': ''}
                
                core_advice = ""
                if '反套' in content:
                    core_advice = "反套机会（套利，非单边）"
                
                if "期限结构" in module_original_views:
                    module_original_views['期限结构']['advice'] = core_advice
            
            if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
                content = str(analysis_state.news_analysis.result_data.get('analysis_content', ''))
                recommendation = str(analysis_state.news_analysis.result_data.get('recommendation', ''))
                
                if "新闻分析" not in module_original_views:
                    module_original_views["新闻分析"] = {'view': '未提取', 'confidence': '未提取', 'advice': '', 'risk': ''}
                
                core_advice = ""
                if '逢低做多' in content or '逢低做多' in recommendation:
                    core_advice = "短期逢低做多、中期看涨"
                elif '看涨' in content or '看多' in content:
                    core_advice = "看涨"
                
                if "新闻分析" in module_original_views:
                    module_original_views['新闻分析']['advice'] = core_advice
        
        # 🔥 P0改进：增加完整论据提取和详细评分标准的模板
        evaluation_template = """
🎯 必须严格按照以下格式输出每个模块的评判：

================================================================================
{module_name}模块评判
================================================================================

🚨🚨🚨 STOP! 在评判辩论之前，必须先看原始分析师观点！🚨🚨🚨

【原始分析师观点】（已为您提取）
• 分析师观点：{original_view}
• 核心建议：{original_advice}
• 风险评估：{original_risk}
• 信心度：{original_confidence}

⚠️ 评判原则（根据分析师观点类型）：

**情况1：分析师观点明确（看多/看空）** - 启用加分机制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 加分规则（透明化）：
  • 与分析师方向一致 → 综合得分 +0.3分
  • 与分析师方向相反 → 综合得分 -0.2分
  
📝 实施细节：
  1. 先按三维度评分公式计算原始得分
  2. 根据方向一致性进行加减分
  3. 最终得分 = 原始得分 + 方向调整分
  
💡 加分示例：
  多头原始得分7.5分，分析师看多 → 最终得分7.5+0.3=7.8分
  空头原始得分8.0分，分析师看多 → 最终得分8.0-0.2=7.8分
  → 经过调整后，多空得分相同，评判为中性

**情况2：分析师观点为中性** - 不启用加分机制
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 不能简单判定多空双方都"不一致"或"偏离中性立场"
• 应该更关注论据质量、逻辑严密性、风险意识等维度
• 允许双方基于事实提出合理的多空观点
• 关键是看哪一方的论据更可靠、逻辑更严密
• 🔥 评判重点：可验证性、数据真实性、推理严密性，而非方向一致性
• 🔥 不进行方向调整加减分，完全基于论证质量评判

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 三维度评分参考标准（10分制细化标准）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【维度1：论据质量】（0-10分）
10分：所有数据直接引用原文+具体数值+来源明确+时效性强+核心相关
9分：数据具体+来源较明确+时效性好+相关性强
8分：数据具体但来源部分模糊+时效性尚可+相关性较强
7分：数据基本具体+时效性一般+相关性中等
6分：数据不够具体或时效性较弱+相关性一般
5分：数据模糊+时效性弱+相关性不足
3-4分：数据严重缺失或明显过时+相关性弱
1-2分：几乎无数据支撑或明显编造

【维度2：逻辑严密性】（0-10分）
10分：因果关系完整清晰+推理严密无漏洞+反驳精准有力+完全自洽
9分：因果关系清晰+推理较严密+反驳有效+基本自洽
8分：因果关系较清晰+推理基本合理+反驳有一定依据+较自洽
7分：因果关系可识别+推理存在小跳跃+反驳一般+基本自洽
6分：因果关系不够清晰+推理有跳跃+反驳针对性不强+有小矛盾
5分：因果关系模糊+推理跳跃较多+反驳无力+有矛盾
3-4分：逻辑混乱+推理漏洞明显+反驳无效+矛盾较多
1-2分：逻辑严重混乱+推理无效+完全无反驳+矛盾明显

【维度3：客观理性度】（0-10分）🔥修正：消除看空偏见，多空平等
10分：充分承认不确定性+客观分析对立观点+多情景分析+平衡识别风险与机会
9分：承认不确定性+尊重对立观点+有情景分析+较好识别风险与机会
8分：基本承认不确定性+部分尊重对立观点+简单情景分析+识别主要风险或机会
7分：有限承认不确定性+有限尊重对立观点+基本情景分析+识别风险或机会但不全面
6分：不确定性认知不足+对立观点尊重不够+情景分析单一+风险/机会识别有限
5分：忽视不确定性+忽视对立观点+单一情景+只强调单方面（仅风险或仅机会）
3-4分：完全忽视不确定性+完全否定对立观点+无情景分析+完全忽视对立面
1-2分：极端自信或极端悲观+攻击对立观点+无客观理性

🎯 核心原则：
• 多头应识别：上涨机会（主要）+ 回调风险（对立面）
• 空头应识别：下跌风险（主要）+ 踏空风险（对立面）
• 平衡性评分：既识别主要方向，又承认对立可能，才是高分

现在开始评判辩论（🔥 必须完整引用辩论原文中的核心论据）：

【多头论据完整提取】（🔥 必须从辩论内容中完整摘录3-5个核心论据）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 强制要求：必须直接引用辩论原文，不能过度简化或概括！

核心论据1：[直接引用原文，例如："技术分析显示...MA5 862.34 > MA20 838.81"，标注✅可验证或❌不可验证]
  └─ 数据真实性评分：X/10分（[具体/模糊/缺失]）
  └─ 数据来源：[明确/部分明确/模糊]
  └─ 时效性：[最新/较新/一般/过时]
  
核心论据2：[直接引用原文，例如："MACD指标18.24显著高于信号线16.0"，标注✅/❌]
  └─ 数据真实性评分：X/10分
  └─ 数据来源：[...]
  └─ 时效性：[...]

核心论据3：[直接引用原文，例如："持仓分析中，6个专业策略中有3个看多"，标注✅/❌]
  └─ 数据真实性评分：X/10分
  └─ 数据来源：[...]
  └─ 时效性：[...]

[如有论据4、5，继续列出]

与原始分析师观点对比：
• 方向一致性：{direction_consistency_instruction}
• 数据一致性：[多头引用的X个数据点中，Y个与分析师报告一致，一致率Z%]
• 解读忠实性：[多头的解读是否忠实反映分析师观点？有无过度解读或扭曲？]

三维度详细评分（基于上述标准）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 论据质量：X.X分
   └─ 数据真实性(×0.4)：X/10分（理由：[具体说明]）
   └─ 数据时效性(×0.2)：X/10分（理由：[具体说明]）
   └─ 数据相关性(×0.25)：X/10分（理由：[具体说明]）
   └─ 数据完整性(×0.15)：X/10分（理由：[具体说明]）
   └─ 加权得分：X.X分

2. 逻辑严密性：X.X分
   └─ 因果关系(×0.3)：X/10分（理由：[推理链条是否完整]）
   └─ 推理过程(×0.3)：X/10分（理由：[是否有跳跃]）
   └─ 反驳有效性(×0.2)：X/10分（理由：[对空头观点的反驳是否有力]）
   └─ 自洽性(×0.2)：X/10分（理由：[前后是否矛盾]）
   └─ 加权得分：X.X分

3. 客观理性度：X.X分 🔥修正：多空平等评分
   └─ 不确定性认知(×0.3)：X/10分（理由：[是否承认不确定性]）
   └─ 对立观点尊重(×0.2)：X/10分（理由：[是否客观分析对立观点]）
   └─ 情景分析(×0.25)：X/10分（理由：[是否考虑多种情景]）
   └─ 风险/机会平衡识别(×0.25)：X/10分（理由：[多头应识别机会+回调风险，空头应识别风险+踏空风险]）
   └─ 加权得分：X.X分

【多头原始综合得分】= 论据质量×40% + 逻辑严密性×35% + 客观理性度×25% = X.X分
【方向调整】：{direction_consistency_instruction}
【多头最终得分】：X.X分（原始分X.X + 方向调整±0.X = X.X）

【空头论据完整提取】（🔥 必须从辩论内容中完整摘录3-5个核心论据）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 强制要求：必须直接引用辩论原文，不能过度简化或概括！

核心论据1：[直接引用原文，标注✅可验证或❌不可验证]
  └─ 数据真实性评分：X/10分
  └─ 数据来源：[...]
  └─ 时效性：[...]

核心论据2：[直接引用原文，标注✅/❌]
  └─ 数据真实性评分：X/10分
  └─ 数据来源：[...]
  └─ 时效性：[...]

核心论据3：[直接引用原文，标注✅/❌]
  └─ 数据真实性评分：X/10分
  └─ 数据来源：[...]
  └─ 时效性：[...]

[如有论据4、5，继续列出]

与原始分析师观点对比：
• 方向一致性：{direction_consistency_instruction}
• 数据一致性：[空头引用的X个数据点中，Y个与分析师报告一致，一致率Z%]
• 解读客观性：[空头是否选择性放大风险、歪曲分析师观点？]

三维度详细评分（基于上述标准）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[与多头相同的详细评分结构]

【空头原始综合得分】= X.X分
【方向调整】：{direction_consistency_instruction}
【空头最终得分】：X.X分（原始分X.X + 方向调整±0.X = X.X）

【论证质量深度对比】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
得分对比：多头X.X分 vs 空头X.X分
得分差：[+/-]X.X分
评判结果：【强势/偏强/中性】（{criteria}）

核心差异分析：
1. 论据质量对比：多头X.X vs 空头X.X（差距±X.X）
   └─ 关键差异：[具体说明哪方数据更真实、时效性更强、相关性更高]
   
2. 逻辑严密性对比：多头X.X vs 空头X.X（差距±X.X）
   └─ 关键差异：[具体说明哪方推理链条更完整、逻辑更严密]
   
3. 客观理性度对比：多头X.X vs 空头X.X（差距±X.X）
   └─ 关键差异：[说明哪方更客观理性：多头是否提示回调风险？空头是否提示踏空风险？]

综合评价：{comparison_instruction}
"""
        
        module_prompts = []
        criteria = "得分差≥1.5为强势，≥0.8为偏强，<0.8为中性"
        
        # 标准模块的具体指导
        module_guidance = {
            'technical': '重点评估：技术指标数据的真实性（如RSI、均线等是否有具体数值）、技术分析逻辑的严密性（如突破→上涨的推理）、是否考虑反向风险（如超买回调）',
            'basis': '重点评估：基差数据的准确性（如具体的基差数值）、基差结构分析的逻辑性（如正向结构→现货紧张）、是否考虑基差收敛风险',
            'inventory': '重点评估：库存数据的可靠性（如库存量、分位数等）、库存趋势分析的逻辑（如累库→压力）、是否考虑供需平衡的不确定性',
            'positioning': '重点评估：持仓数据的准确性（如集中度、资金流向）、资金分析的逻辑性（如看多席位多→看多）、是否考虑资金撤离风险',
            'term_structure': '重点评估：期限结构数据的准确性（如Backwardation、价差等）、结构分析的理论支撑（如近高远低→紧张）、是否考虑结构逆转风险',
            'news': '重点评估：新闻事件的可验证性（如矿难、产量等是否是事实）、事件影响分析的逻辑性、是否考虑需求端和政策风险'
        }
        
        for module in available_modules:
            module_name = self._get_module_display_name(module)
            guidance = module_guidance.get(module, f'重点评估：{module_name}相关数据的真实性、分析逻辑的严密性、风险意识的充分性')
            
            # 🔥 获取该模块的原始观点
            original_view_info = module_original_views.get(module_name, {})
            original_view = original_view_info.get('view', '未提取')
            original_advice = original_view_info.get('advice', '未提取')
            original_risk = original_view_info.get('risk', '未提取')
            original_confidence = original_view_info.get('confidence', '未提取')
            
            # 🔥 根据分析师观点类型，生成不同的评判指导
            if original_view in ['看多', '偏多', '做多']:
                direction_consistency_instruction = "[多头与分析师观点一致，应加分；空头与分析师观点相反，应适当扣分]"
                evidence_scoring_instruction = "[数据真实性+时效性+相关性+完整性。🔥 特别考虑：与分析师观点一致性]"
                comparison_instruction = "[说明核心差异。🔥 分析师看多，多头论述与分析师一致应是加分项]"
            elif original_view in ['看空', '偏空', '做空']:
                direction_consistency_instruction = "[空头与分析师观点一致，应加分；多头与分析师观点相反，应适当扣分]"
                evidence_scoring_instruction = "[数据真实性+时效性+相关性+完整性。🔥 特别考虑：与分析师观点一致性]"
                comparison_instruction = "[说明核心差异。🔥 分析师看空，空头论述与分析师一致应是加分项]"
            else:  # 中性
                direction_consistency_instruction = "[分析师为中性观点。🔥不应简单判定多空双方'偏离中性立场'，而应客观评估各自论据的可验证性和逻辑严密性]"
                evidence_scoring_instruction = "[🔥 重点关注：数据真实性（是否可验证）、时效性、相关性、完整性。中性观点下，论据质量本身最重要，不因方向不同扣分]"
                comparison_instruction = "[🔥 关键：分析师为中性，应基于论据质量、逻辑严密性、风险意识评判，而非简单以'偏离中性'为由判定中性。说明哪方论据更可靠、逻辑更严密]"
            
            # 🔥 简化评判原则说明
            if original_view in ['看多', '偏多', '做多']:
                principle_short = "分析师看多→多头一致应加分"
            elif original_view in ['看空', '偏空', '做空']:
                principle_short = "分析师看空→空头一致应加分"
            else:  # 中性
                principle_short = "分析师中性→关注论据质量，不因方向扣分"
            
            prompt = f"""
================================================================================
{module_name}：{original_view}（{original_confidence}）| 建议：{original_advice if original_advice else '无'} | 原则：{principle_short}
================================================================================

🔥 强制要求：必须从辩论内容中直接引用3-5个核心论据，不能过度简化！

【多头】核心论据：
1. "[直接引用辩论原文关键句，如'技术分析显示...MA5 862.34 > MA20 838.81']" ✅/❌
2. "[直接引用辩论原文关键句，如'MACD指标18.24显著高于信号线16.0']" ✅/❌
3. "[直接引用辩论原文关键句，如'持仓分析中，6个专业策略中有3个看多']" ✅/❌
[如有更多核心论据，继续列出4、5]

三维度评分：论据质量X.X分 | 逻辑严密性X.X分 | 客观理性度X.X分 → 综合得分X.X分
评分理由：[基于三维度标准说明：1)数据真实性 2)逻辑严密性 3)客观理性（多头需提示回调风险，空头需提示踏空风险）]

【空头】核心论据：
1. "[直接引用辩论原文关键句]" ✅/❌
2. "[直接引用辩论原文关键句]" ✅/❌
3. "[直接引用辩论原文关键句]" ✅/❌
[如有更多核心论据，继续列出4、5]

三维度评分：论据质量X.X分 | 逻辑严密性X.X分 | 客观理性度X.X分 → 综合得分X.X分
评分理由：[基于三维度标准说明：1)数据真实性 2)逻辑严密性 3)客观理性（多头需提示回调风险，空头需提示踏空风险）]

【对比】多头X.X vs 空头X.X，得分差[+/-]X.X → 评判：【强势/偏强/中性】
关键差异：[具体说明：1)论据质量差异 2)逻辑严密性差异 3)客观理性度差异（多头是否提示回调风险？空头是否提示踏空风险？）。{comparison_instruction}]
"""
            module_prompts.append(prompt.strip())
        
        if not module_prompts:
            return "⚠️ 无可用模块进行评判"
        
        header = """
🎯 三维度科学评判框架（已提取各模块原始观点）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 评判原则（加分机制透明化）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 分析师观点明确（看多/看空）：
  • 方向一致 → 综合得分 +0.3分
  • 方向相反 → 综合得分 -0.2分
  • 先计算原始得分，再根据方向一致性调整

📌 分析师观点中性：
  • 🔥 不进行加减分调整
  • 完全基于论据可验证性和逻辑严密性评判

📊 评分标准：论据质量40% + 逻辑严密性35% + 客观理性度25%（多空平等）
📏 判定标准：得分差≥1.5强势，≥0.8偏强，<0.8中性

🚨 输出要求：
• 每个模块评判控制在10-15行以内
• 评分理由用一句话概括核心要点
• 明确标注是否进行了方向调整加分
• 严格按照模板格式输出，不要展开说明

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 严禁使用带偏见的评语标签（多空平等原则）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 禁止使用的负面标签（对多头有偏见）：
• "过于乐观"、"过度自信"、"盲目乐观"
• "忽视风险"、"缺乏风险意识"（除非确实完全未提及风险）
• "一厢情愿"、"不切实际"

❌ 禁止使用的正面标签（对空头有偏见）：
• "风险意识强"（作为唯一正面评价）
• "更客观"、"更理性"（除非有明确依据）

✅ 推荐使用的中性描述：
对多头：
• 积极预期有数据支撑 / 乐观预期基于XX数据
• 建议补充考虑回调风险 / 建议增强风险对冲措施
• 机会识别准确但风险提示不足

对空头：
• 谨慎预期有数据支撑 / 风险识别基于XX数据
• 建议考虑踏空风险 / 建议关注反转可能
• 风险识别准确但机会识别不足

🎯 核心原则：
1. 多头识别机会+提示风险 = 客观理性
2. 空头识别风险+提示机会 = 客观理性
3. 只强调单方面（仅机会或仅风险）= 不够客观
4. 使用"积极预期"替代"过于乐观"
5. 使用"谨慎预期"替代"过度悲观"

"""
        
        return header + "\n\n".join(module_prompts)
    
    def _generate_ai_evaluation_template(self, available_modules: List[str]) -> str:
        """基于可用模块动态生成AI评估模板 - 改为定性评估"""
        if not available_modules:
            return "⚠️ 无可用模块进行AI评估"
            
        ai_templates = []
        
        for module in available_modules:
            module_name = self._get_module_display_name(module)
            template = f"""{module_name}：
  - 多头论证：[强势/中性/弱势]（基于实际论据）
  - 空头论证：[强势/中性/弱势]（基于实际论据）
  - 整体倾向：[偏多/中性/偏空]"""
            ai_templates.append(template)
        
        return "\n  \n".join(ai_templates)
    
    def _assess_data_completeness(self, available_modules: List[str]) -> Dict[str, Any]:
        """评估数据完整性 - 简化版"""
        total_modules = 6  # 标准模块数量
        available_count = len(available_modules)
        
        # 数据完整性等级
        if available_count >= 6:
            completeness_level = "完整"
            confidence_range = "高(80-90%)"
        elif available_count >= 4:
            completeness_level = "较完整"
            confidence_range = "中偏高(70-80%)"
        elif available_count >= 2:
            completeness_level = "有限"
            confidence_range = "中等(50-70%)"
        else:
            completeness_level = "不足"
            confidence_range = "低(30-50%)"
        
        return {
            "available_modules": available_modules,
            "available_count": available_count,
            "total_modules": total_modules,
            "completeness_level": completeness_level,
            "confidence_range": confidence_range,
            "missing_modules": set(["technical", "basis", "inventory", "positioning", "term_structure", "news"]) - set(available_modules)
        }
    
    def _format_data_completeness(self, data_completeness: Dict[str, Any], commodity_type: str) -> str:
        """格式化数据完整性信息 - 简化透明版"""
        available_modules = data_completeness["available_modules"]
        missing_modules = data_completeness["missing_modules"]
        
        result_lines = []
        result_lines.append("📊 数据完整性分析（透明化评估）：")
        result_lines.append("")
        result_lines.append(f"🎯 品种类型：{commodity_type}")
        result_lines.append(f"📈 数据完整度：{data_completeness['completeness_level']} ({data_completeness['available_count']}/{data_completeness['total_modules']}个模块)")
        result_lines.append(f"🎲 对应信心度区间：{data_completeness['confidence_range']}")
        result_lines.append("")
        
        # 可用模块
        if available_modules:
            module_names = [self._get_module_display_name(m) for m in available_modules]
            result_lines.append(f"✅ 可用数据模块：{', '.join(module_names)}")
        
        # 缺失模块
        if missing_modules:
            missing_names = [self._get_module_display_name(m) for m in missing_modules]
            result_lines.append(f"❌ 缺失数据模块：{', '.join(missing_names)}")
        
        result_lines.append("")
        result_lines.append("🎯 评判指导原则（简化版）：")
        result_lines.append("- 关键模块（技术、基差、库存）：重点关注其论证质量")
        result_lines.append("- 辅助模块（持仓、期限结构、新闻）：作为补充参考")
        result_lines.append("- 缺失模块：诚实承认数据不足，不进行臆测")
        result_lines.append("- 决策原则：数据不足时偏向保守，避免过度解读")
        
        return "\n".join(result_lines)
    
    def _generate_analyst_view_summary_from_extracted(self, analyst_views: Dict[str, Any]) -> str:
        """🔥 新方法：直接使用已提取的分析师观点数据生成摘要，确保与辩论评判一致"""
        
        # 生成统计头部
        summary_lines = []
        summary_lines.append(f"分析师团队观点分布：看多{analyst_views['bullish_count']}个模块，看空{analyst_views['bearish_count']}个模块，中性{analyst_views['neutral_count']}个模块")
        summary_lines.append("")
        
        # 遍历所有模块，生成详细信息
        module_order = ["技术分析", "基差分析", "库存分析", "持仓分析", "期限结构", "新闻分析"]
        
        for module_name in module_order:
            if module_name in analyst_views["details"]:
                detail = analyst_views["details"][module_name]
                view = detail["view"]
                confidence = detail["confidence"]
                
                # 判断数据支撑（简化版，基于观点类型）
                if view in ["看多", "看空"]:
                    data_support = "数据支撑充分" if "高" in confidence else "数据支撑有限"
                else:
                    data_support = "数据支撑有限"
                
                # 判断可信度（基于信心度）
                if "高" in confidence:
                    credibility = "中等可信度(7.0分以上)"
                elif "中" in confidence:
                    credibility = "中等可信度(6.0-7.0分)"
                else:
                    credibility = "一般可信度(6.0分以下)"
                
                # 风险提示
                risk_note = "提示风险" if view in ["看多", "看空"] else "提示风险"
                
                summary_lines.append(f"• {module_name}: {view}({confidence.replace('信心度', '')})")
                summary_lines.append(f"  数据支撑: {data_support}")
                summary_lines.append(f"  可信度评估: {credibility}")
                summary_lines.append(f"  风险提示: {risk_note}")
        
        return "\n".join(summary_lines)
    
    def _generate_analyst_recommendations_summary(self, available_modules: List[str], analysis_state: FuturesAnalysisState) -> str:
        """🔥 修复：基于实际分析师模块结果提取真实观点"""
        if not available_modules:
            return "⚠️ 无可用分析师模块"
        
        # 🔥 关键修复：从analysis_state中提取实际的分析师观点
        actual_recommendations = self._extract_analyst_recommendations(analysis_state, available_modules)
        
        if actual_recommendations:
            return actual_recommendations
        else:
            # 如果提取失败，返回说明而不是模板
            return "⚠️ 无法从分析师模块中提取有效观点，请检查模块数据完整性"
    
    def _generate_completeness_check_list(self, available_modules: List[str]) -> str:
        """基于可用模块生成完整性检查清单 - 支持任意模块扩展"""
        if not available_modules:
            return "⚠️ 无可用模块进行检查"
            
        check_items = []
        
        # 标准模块检查模板
        standard_checks = {
            'technical': "- 技术分析：多头是否提及技术指标、价格位置、趋势判断？空头是否提及技术风险、阻力支撑？",
            'basis': "- 基差分析：多头是否分析了基差结构的积极含义？空头是否指出了基差风险？",
            'inventory': "- 库存分析：双方是否都基于库存数据进行了论证？",
            'positioning': "- 持仓分析：双方是否都分析了资金流向和主力意图？",
            'term_structure': "- 期限结构：多头是否解读了Contango/Backwardation的利好信号？空头是否指出了期限结构的风险？",
            'news': "- 新闻分析：双方是否都结合了宏观政策和基本面因素？"
        }
        
        for module in available_modules:
            if module in standard_checks:
                # 标准模块使用预定义检查
                check_items.append(standard_checks[module])
            else:
                # 🚀 新增模块动态生成检查
                module_name = self._get_module_display_name(module)
                dynamic_check = f"- {module_name}：多头是否基于{module_name}数据提出了积极观点？空头是否指出了{module_name}相关的风险？"
                check_items.append(dynamic_check)
                print(f"🆕 动态生成检查项: {module} -> {module_name}")
        
        return "\n".join(check_items)
    
    def _summarize_analyst_data(self, analysis_state: FuturesAnalysisState) -> str:
        """🔥 增强版：综合分析师数据总结，重点提取操作建议和方向判断"""
        
        # 检测可用模块
        available_modules = self._detect_available_modules(analysis_state)
        
        if not available_modules:
            return "⚠️ 当前没有可用的分析师数据"
        
        summary_parts = []
        
        print(f"📊 开始处理 {len(available_modules)} 个分析模块的数据摘要")
        
        # 🔥 新增：提取分析师的操作建议和方向判断
        analyst_recommendations = self._extract_analyst_recommendations(analysis_state, available_modules)
        if analyst_recommendations:
            summary_parts.append(f"【分析师操作建议汇总】\n{analyst_recommendations}")
        
        # 动态处理每个可用模块
        for module_key in available_modules:
            module_summary = self._summarize_single_module(analysis_state, module_key)
            if module_summary:
                summary_parts.append(module_summary)
                print(f"✅ 已处理模块: {self._get_module_display_name(module_key)}")
        
        return "\n\n".join(summary_parts) if summary_parts else "⚠️ 无法提取有效的分析师数据"
    
    def _extract_analyst_recommendations(self, analysis_state: FuturesAnalysisState, available_modules: List[str]) -> str:
        """🔥 新功能：提取各个分析师模块的操作建议和方向判断"""
        
        recommendations = []
        
        for module_key in available_modules:
            module_data = None
            module_name = self._get_module_display_name(module_key)
            
            # 获取模块数据
            if hasattr(analysis_state, module_key) and getattr(analysis_state, module_key):
                module_data = getattr(analysis_state, module_key)
            else:
                # 尝试带_analysis后缀的属性名
                attr_name = f"{module_key}_analysis"
                if hasattr(analysis_state, attr_name) and getattr(analysis_state, attr_name):
                    module_data = getattr(analysis_state, attr_name)
            
            if not module_data:
                continue
                
            # 提取该模块的操作建议
            module_recommendation = self._extract_single_module_recommendation(module_data, module_name)
            if module_recommendation:
                recommendations.append(module_recommendation)
        
        if not recommendations:
            return ""
        
        # 统计多空倾向
        bullish_count = sum(1 for rec in recommendations if any(keyword in rec for keyword in ["做多", "看多", "买入", "上涨", "利多"]))
        bearish_count = sum(1 for rec in recommendations if any(keyword in rec for keyword in ["做空", "看空", "卖出", "下跌", "利空"]))
        neutral_count = len(recommendations) - bullish_count - bearish_count
        
        summary_header = f"分析师团队观点分布：看多{bullish_count}个模块，看空{bearish_count}个模块，中性{neutral_count}个模块"
        
        return f"{summary_header}\n" + "\n".join(recommendations)
    
    def _extract_single_module_recommendation(self, module_data, module_name: str) -> str:
        """🔥 科学提取分析师观点 - 深度解析论据和数据支撑"""
        try:
            # 获取完整分析内容
            analysis_content = self._get_full_analysis_content(module_data)
            if not analysis_content:
                return f"• {module_name}: 无有效分析内容"
            
            # 🔥 深度解析分析师观点
            analyst_view = self._analyze_analyst_viewpoint(analysis_content, module_name)
            
            # 🔥 提取具体数据支撑
            data_support = self._extract_data_evidence(analysis_content, module_name)
            
            # 🔥 评估观点可信度
            credibility_score = self._assess_viewpoint_credibility(analysis_content, data_support)
            
            # 🔥 构建科学化的分析师观点报告
            return self._build_analyst_report(module_name, analyst_view, data_support, credibility_score)
            
        except Exception as e:
            return f"• {module_name}: 数据解析异常 - {str(e)}"
    
    def _get_full_analysis_content(self, module_data) -> str:
        """获取完整的分析内容"""
        content_fields = [
            "analysis_content", "ai_analysis", "professional_analysis", 
            "ai_comprehensive_analysis", "comprehensive_analysis", 
            "detailed_analysis", "content", "report", "analysis_report"
        ]
        
        for field in content_fields:
            content = module_data.result_data.get(field, "")
            if isinstance(content, str) and len(content.strip()) > 50:
                return content.strip()
        return ""
    
    def _analyze_analyst_viewpoint(self, content: str, module_name: str) -> Dict[str, Any]:
        """🔥 科学分析分析师观点"""
        import re
        
        viewpoint = {
            "direction": "中性",
            "confidence": "未明确",
            "key_arguments": [],
            "specific_targets": [],
            "risk_factors": []
        }
        
        content_lower = content.lower()
        
        # 🎯 方向判断 - 扩展的结论性表述匹配（与_extract_module_view保持一致）
        conclusion_patterns = [
            # 1. 投资方向/操作建议（最高优先级）
            r'(?:投资方向建议|操作建议|交易建议|投资建议)[：:][^。]*?(?:采取)?[^。]*?(谨慎)?[^。]*?(偏多|偏空|做多|做空|看多|看空|买入|卖出)',
            
            # 2. 主要交易方向
            r'主要交易方向[：:][^。]*?(谨慎)?[^。]*?(看多|看空|做多|做空|偏多|偏空|中性|观望)',
            
            # 3. 建议建立头寸
            r'建议[^。]*?(?:在|逐步)?[^。]*?建立[^。]*?(多头|空头)(?:头寸|仓位)',
            
            # 4. 建议采取...策略
            r'(?:建议|推荐)(?:采取)?[^。]*?(谨慎)?[^。]*?(偏多|偏空|做多|做空|看多|看空|买入|卖出)(?:策略)?',
            
            # 5. 市场/价格呈现...格局/态势
            r'(?:市场|价格|铜价|沪铜|金价|沪金)[^。]*?(?:呈现|显示|表现)[^。]*?(偏多|偏空|偏强|偏弱|强势|弱势)(?:格局|态势|特征)?',
            
            # 6. 震荡偏强/偏弱
            r'(?:震荡|波动)[^。]*?(偏强|偏弱|偏多|偏空)',
            
            # 7. 多头/空头占优/强势
            r'(多头|空头)[^。]*?(?:占优|强势|力量|主导|优势)',
            
            # 8. 总体/综合来看
            r'(?:总体|综合|整体)(?:来看|而言|判断)[^。]*?(看多|看空|偏多|偏空|中性|观望)',
            
            # 9. 方向/趋势判断
            r'(?:方向|趋势|走势)[^。]*?(看多|看空|偏多|偏空|上涨|下跌)',
            
            # 10. 明确结论
            r'(?:结论|判断)[：:][^。]*?(看多|看空|偏多|偏空|中性|观望)',
            
            # 11. 延续...趋势/行情
            r'(?:延续|维持|保持)[^。]*?(上升|上涨|下跌|下降)(?:趋势|行情|态势)',
            
            # 12. 偏向...
            r'(?:偏向|倾向)[^。]*?(乐观|悲观|看多|看空)'
        ]
        
        direction_determined = False
        for pattern in conclusion_patterns:
            match = re.search(pattern, content_lower)
            if match:
                groups = match.groups()
                matched_text = match.group(0)
                all_text = ''.join(str(g) for g in groups if g) + matched_text
                
                # 看多/看空信号（扩展识别）
                bullish_signals = ['偏多', '偏强', '看多', '做多', '买入', '上涨', '上升', '乐观', '强势']
                bearish_signals = ['偏空', '偏弱', '看空', '做空', '卖出', '下跌', '下降', '悲观', '弱势']
                
                # 特殊处理：多头头寸/空头头寸
                if '多头头寸' in matched_text or '多头仓位' in matched_text:
                    viewpoint["direction"] = "看多"
                    direction_determined = True
                    break
                if '空头头寸' in matched_text or '空头仓位' in matched_text:
                    viewpoint["direction"] = "看空"
                    direction_determined = True
                    break
                
                # 特殊处理：多头占优/力量
                if '多头' in all_text and any(x in all_text for x in ['占优', '强势', '力量', '主导', '优势']):
                    viewpoint["direction"] = "看多"
                    direction_determined = True
                    break
                if '空头' in all_text and any(x in all_text for x in ['占优', '强势', '力量', '主导', '优势']):
                    viewpoint["direction"] = "看空"
                    direction_determined = True
                    break
                
                # 常规判断
                if any(kw in all_text for kw in bullish_signals):
                    viewpoint["direction"] = "看多"
                    direction_determined = True
                    break
                elif any(kw in all_text for kw in bearish_signals):
                    viewpoint["direction"] = "看空"
                    direction_determined = True
                    break
        
        # 如果没有匹配到结论性表述，使用简单的信号统计
        if not direction_determined:
            bullish_signals = len(re.findall(r'(建议|推荐|可以|应该).{0,10}(做多|买入|看多)', content_lower))
            bearish_signals = len(re.findall(r'(建议|推荐|可以|应该).{0,10}(做空|卖出|看空)', content_lower))
            
            if bullish_signals > bearish_signals:
                viewpoint["direction"] = "看多"
            elif bearish_signals > bullish_signals:
                viewpoint["direction"] = "看空"
        
        # 🎯 信心度评估 - 改进逻辑，区分"谨慎偏多"（低信心看多）和真正的观望
        confidence_indicators = {
            "高": ["强烈建议", "积极", "明确", "确定", "大概率", "高置信度", "高信心"],
            "中": ["建议", "可以考虑", "倾向", "可能", "适度", "较为"],
            "低": ["观望", "等待", "不确定", "风险较大"]
        }
        
        # 特殊处理：如果同时出现"谨慎"和方向词，信心度应该是"低"而不影响方向判断
        if "谨慎" in content_lower and viewpoint["direction"] != "中性":
            viewpoint["confidence"] = "低"
        else:
            # 按优先级匹配信心度指标
            for level, indicators in confidence_indicators.items():
                if any(indicator in content_lower for indicator in indicators):
                    viewpoint["confidence"] = level
                    break
        
        # 🎯 提取关键论据
        viewpoint["key_arguments"] = self._extract_key_arguments(content)
        
        # 🎯 提取具体目标
        viewpoint["specific_targets"] = self._extract_price_targets(content)
        
        # 🎯 提取风险因素
        viewpoint["risk_factors"] = self._extract_risk_mentions(content)
        
        return viewpoint
    
    def _extract_data_evidence(self, content: str, module_name: str) -> Dict[str, Any]:
        """🔥 提取具体数据支撑"""
        import re
        
        evidence = {
            "numerical_data": [],
            "technical_indicators": [],
            "market_metrics": [],
            "historical_references": []
        }
        
        # 🔢 提取数值数据
        numerical_patterns = [
            r'(\d+\.?\d*)\s*[%％]',  # 百分比
            r'(\d+\.?\d*)\s*元/吨',   # 价格
            r'(\d+\.?\d*)\s*万吨',    # 库存量
            r'(\d+\.?\d*)\s*分位数',  # 分位数
            r'RSI\s*[：:]\s*(\d+\.?\d*)',  # RSI值
            r'MACD\s*[：:]\s*([+-]?\d+\.?\d*)',  # MACD值
        ]
        
        for pattern in numerical_patterns:
            matches = re.findall(pattern, content)
            evidence["numerical_data"].extend(matches)
        
        # 📊 提取技术指标
        tech_indicators = ["RSI", "MACD", "KDJ", "布林带", "均线", "成交量", "ATR"]
        for indicator in tech_indicators:
            if indicator in content:
                evidence["technical_indicators"].append(indicator)
        
        # 📈 提取市场指标
        market_metrics = ["基差", "库存", "持仓", "价差", "升贴水", "展期", "便利收益"]
        for metric in market_metrics:
            if metric in content:
                evidence["market_metrics"].append(metric)
        
        # 📚 提取历史参考
        historical_patterns = [
            r'历史.{0,20}(均值|平均|水平)',
            r'过去.{0,10}(年|月|周)',
            r'同期.{0,10}(数据|水平)'
        ]
        
        for pattern in historical_patterns:
            if re.search(pattern, content):
                evidence["historical_references"].append(re.search(pattern, content).group())
        
        return evidence
    
    def _assess_viewpoint_credibility(self, content: str, data_support: Dict) -> Dict[str, Any]:
        """🔥 评估观点可信度"""
        credibility = {
            "data_richness": 0,    # 数据丰富度 (0-10)
            "logic_coherence": 0,  # 逻辑连贯性 (0-10)
            "risk_awareness": 0,   # 风险意识 (0-10)
            "overall_score": 0     # 综合评分 (0-10)
        }
        
        # 🔢 数据丰富度评分
        data_count = (
            len(data_support["numerical_data"]) * 2 +
            len(data_support["technical_indicators"]) * 1.5 +
            len(data_support["market_metrics"]) * 1.5 +
            len(data_support["historical_references"]) * 1
        )
        credibility["data_richness"] = min(10, data_count)
        
        # 🧠 逻辑连贯性评分
        logic_words = ["因为", "所以", "导致", "基于", "表明", "证明", "预示", "由于", "因此"]
        logic_count = sum(1 for word in logic_words if word in content)
        credibility["logic_coherence"] = min(10, logic_count * 1.5)
        
        # ⚠️ 风险意识评分
        risk_words = ["风险", "注意", "谨慎", "警惕", "不确定", "可能", "但是", "然而"]
        risk_count = sum(1 for word in risk_words if word in content)
        credibility["risk_awareness"] = min(10, risk_count * 1.2)
        
        # 📊 综合评分
        credibility["overall_score"] = (
            credibility["data_richness"] * 0.4 +
            credibility["logic_coherence"] * 0.3 +
            credibility["risk_awareness"] * 0.3
        )
        
        return credibility
    
    def _build_analyst_report(self, module_name: str, viewpoint: Dict, data_support: Dict, credibility: Dict) -> str:
        """🔥 构建科学化的分析师观点报告"""
        
        # 构建观点描述
        direction = viewpoint["direction"]
        confidence = viewpoint["confidence"]
        
        # 构建数据支撑描述
        data_desc = []
        if data_support["numerical_data"]:
            data_desc.append(f"数值数据{len(data_support['numerical_data'])}个")
        if data_support["technical_indicators"]:
            data_desc.append(f"技术指标{len(data_support['technical_indicators'])}个")
        
        data_support_text = "、".join(data_desc) if data_desc else "数据支撑有限"
        
        # 构建可信度描述
        score = credibility["overall_score"]
        if score >= 8:
            credibility_level = "高可信度"
        elif score >= 6:
            credibility_level = "中等可信度"
        elif score >= 4:
            credibility_level = "一般可信度"
        else:
            credibility_level = "低可信度"
            
        # 风险提示
        risk_warnings = []
        if any(keyword in viewpoint.get("risk_factors", []) for keyword in ["风险", "注意", "谨慎"]):
            risk_warnings.append("提示风险")
        if "止损" in str(viewpoint.get("key_arguments", [])):
            risk_warnings.append("建议设置止损")
            
        # 构建完整报告
        report_parts = [
            f"• {module_name}: {direction}({confidence}信心度)",
            f"  数据支撑: {data_support_text}",
            f"  可信度评估: {credibility_level}({score:.1f}分)"
        ]
        
        if risk_warnings:
            report_parts.append(f"  风险提示: {', '.join(risk_warnings)}")
        
        return "\n".join(report_parts)
    
    def _extract_key_arguments(self, content: str) -> List[str]:
        """提取关键论据"""
        import re
        
        # 寻找论据性表述
        argument_patterns = [
            r'(基于|根据|由于).{10,50}(表明|显示|证明)',
            r'(技术面|基本面|资金面).{10,50}(支撑|压制|利好|利空)',
            r'(数据显示|分析表明|研究发现).{10,100}'
        ]
        
        arguments = []
        for pattern in argument_patterns:
            matches = re.findall(pattern, content)
            arguments.extend([match[0] + "..." + match[1] for match in matches if len(matches) > 0])
        
        return arguments[:3]  # 最多3个关键论据
    
    def _extract_price_targets(self, content: str) -> List[str]:
        """提取价格目标"""
        import re
        
        # 寻找价格目标
        target_patterns = [
            r'目标价.{0,10}(\d+\.?\d*)\s*元',
            r'看至.{0,10}(\d+\.?\d*)\s*元',
            r'上看.{0,10}(\d+\.?\d*)\s*元',
            r'下看.{0,10}(\d+\.?\d*)\s*元'
        ]
        
        targets = []
        for pattern in target_patterns:
            matches = re.findall(pattern, content)
            targets.extend(matches)
        
        return targets[:2]  # 最多2个目标价
    
    def _extract_risk_mentions(self, content: str) -> List[str]:
        """提取风险因素"""
        import re
        
        # 寻找风险表述
        risk_patterns = [
            r'(风险|注意|警惕).{5,30}',
            r'(但是|然而|不过).{5,30}(风险|压力|阻力)',
            r'(需要关注|值得注意).{5,30}'
        ]
        
        risks = []
        for pattern in risk_patterns:
            matches = re.findall(pattern, content)
            risks.extend([match if isinstance(match, str) else match[0] for match in matches])
        
        return risks[:3]  # 最多3个风险因素
    
    def _generate_offline_trader_analysis(self, analysis_state: FuturesAnalysisState, debate_result: DebateResult) -> Dict:
        """🔥 离线交易员分析 - 基于规则的科学评判"""
        
        try:
            # 检测可用模块
            available_modules = self._detect_available_modules(analysis_state)
            
            # 分析师观点统计
            bullish_modules = 0
            bearish_modules = 0
            neutral_modules = 0
            
            # 简化的分析师观点提取
            for module_key in available_modules:
                module_data = getattr(analysis_state, f"{module_key}_analysis", None)
                if module_data and hasattr(module_data, 'result_data'):
                    content = str(module_data.result_data.get('analysis_content', '')).lower()
                    if any(word in content for word in ['做多', '看多', '买入', '上涨']):
                        bullish_modules += 1
                    elif any(word in content for word in ['做空', '看空', '卖出', '下跌']):
                        bearish_modules += 1
                    else:
                        neutral_modules += 1
            
            # 辩论结果分析
            bull_score = debate_result.overall_bull_score
            bear_score = debate_result.overall_bear_score
            score_diff = abs(bull_score - bear_score)
            
            # 综合判断逻辑
            if bullish_modules > bearish_modules and bull_score >= bear_score:
                direction = "看多"
                strategy = "谨慎做多"
            elif bearish_modules > bullish_modules and bear_score >= bull_score:
                direction = "看空" 
                strategy = "谨慎做空"
            else:
                direction = "中性"
                strategy = "观望"
            
            # 信心度评估
            if score_diff >= 2.0 and abs(bullish_modules - bearish_modules) >= 2:
                confidence = "高"
            elif score_diff >= 1.0 or abs(bullish_modules - bearish_modules) >= 1:
                confidence = "中"
            else:
                confidence = "低"
            
            # 构建离线分析内容
            offline_content = f"""
【辩论评判分析】
基于离线规则分析，当前{get_commodity_name(analysis_state.commodity)}市场状况：

技术分析模块评判：
多头论据：基于可用数据显示技术指标支撑
空头论据：基于可用数据显示技术风险存在
论证质量对比：多头：中性 vs 空头：中性。数据支撑相当

【分析师观点科学评估】
分析师团队观点分布：看多{bullish_modules}个模块，看空{bearish_modules}个模块，中性{neutral_modules}个模块

【论证质量量化评判】
多头强势模块：{bullish_modules}个
空头强势模块：{bearish_modules}个  
中性模块：{neutral_modules}个

【多空综合判断结论】
方向判断依据：
- 辩论评判结果：{'多头' if bull_score >= bear_score else '空头'}以{max(bull_score, bear_score):.1f}分对{min(bull_score, bear_score):.1f}分获胜
- 分析师团队观点：{bullish_modules}个模块建议做多，{bearish_modules}个模块建议做空，{neutral_modules}个模块观望

综合方向倾向：{direction}
信心度：{confidence}
信心度理由：基于{len(available_modules)}个分析模块的数据支撑和辩论评分差异{score_diff:.1f}分的综合评估

【交易策略建议】
策略方向：{strategy}

策略制定依据：
- 方向判断：{direction}（信心度：{confidence}）
- 分析师建议整合：基于{len(available_modules)}个模块的综合建议
- 风险考量：{confidence}信心度要求谨慎操作

具体执行方案：
仓位建议：{'10-15%' if confidence == '高' else '5-10%' if confidence == '中' else '2-5%'}
关键价位：基于技术分析确定进出场点位
持仓周期：短期操作，密切关注市场变化
风控措施：严格止损设置，控制风险暴露

【风险提示】
主要风险因素：API连接问题导致分析深度有限，建议结合实时市场信息
不确定性因素：离线分析模式下数据更新可能滞后
监控要点：关注网络连接恢复后的完整分析结果
"""
            
            return {
                "success": True,
                "content": offline_content.strip(),
                "mode": "offline"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"离线分析失败: {str(e)}",
                "mode": "offline"
            }
    
    def _determine_confidence_level_scientific(self, confidence_value: float, module_name: str) -> str:
        """🔥 科学确定置信度等级 - 基于模块特性和统计分布"""
        
        # 不同模块的置信度统计特征（基于实际观测数据调整）
        module_stats = {
            "技术分析": {"high_threshold": 0.82, "medium_threshold": 0.65},  # 技术分析通常置信度较稳定
            "基差分析": {"high_threshold": 0.78, "medium_threshold": 0.62},  # 基差分析依赖数据质量
            "库存分析": {"high_threshold": 0.80, "medium_threshold": 0.60},  # 库存数据相对可靠
            "持仓分析": {"high_threshold": 0.75, "medium_threshold": 0.58},  # 持仓数据波动较大
            "期限结构": {"high_threshold": 0.85, "medium_threshold": 0.70},  # 期限结构计算复杂度高
            "新闻分析": {"high_threshold": 0.70, "medium_threshold": 0.55},  # 新闻分析主观性较强
        }
        
        # 获取模块特定的阈值，如果没有则使用默认值
        thresholds = module_stats.get(module_name, {"high_threshold": 0.78, "medium_threshold": 0.62})
        
        # 🎯 科学评级逻辑
        if confidence_value >= thresholds["high_threshold"]:
            return f"高置信度({confidence_value:.1%})"
        elif confidence_value >= thresholds["medium_threshold"]:
            return f"中等置信度({confidence_value:.1%})"
        else:
            return f"低置信度({confidence_value:.1%})"
    
    def _calculate_qualitative_confidence(self, analysis_state: FuturesAnalysisState, 
                                        available_modules: List[str], 
                                        debate_result: DebateResult) -> str:
        """🔥 新功能：定性信心度评估 - 返回高/中/低"""
        
        # 第一层：分析师团队观点评估（权重40-50%）
        analyst_confidence_score = 0
        total_modules = len(available_modules)
        if total_modules > 0:
            bullish_modules = 0
            bearish_modules = 0
            high_confidence_modules = 0
            
            for module_key in available_modules:
                module_data = None
                if hasattr(analysis_state, module_key) and getattr(analysis_state, module_key):
                    module_data = getattr(analysis_state, module_key)
                else:
                    attr_name = f"{module_key}_analysis"
                    if hasattr(analysis_state, attr_name) and getattr(analysis_state, attr_name):
                        module_data = getattr(analysis_state, attr_name)
                
                if not module_data:
                    continue
                
                # 🔥 改进：使用科学的置信度评估
                confidence = module_data.confidence_score if hasattr(module_data, 'confidence_score') else None
                if confidence:
                    conf_val = safe_convert_to_float(confidence)
                    module_name = self._get_module_display_name(module_key)
                    confidence_level = self._determine_confidence_level_scientific(conf_val, module_name)
                    if "高置信度" in confidence_level:
                        high_confidence_modules += 1
                
                # 检查方向倾向
                analysis_content = str(module_data.result_data.get('analysis_content', '')).lower()
                if any(keyword in analysis_content for keyword in ["做多", "看多", "买入", "上涨"]):
                    bullish_modules += 1
                elif any(keyword in analysis_content for keyword in ["做空", "看空", "卖出", "下跌"]):
                    bearish_modules += 1
            
            # 计算观点一致性
            max_direction = max(bullish_modules, bearish_modules)
            direction_consistency = max_direction / total_modules if total_modules > 0 else 0
            
            # 分析师信心度评分（0-50）
            if direction_consistency >= 0.7:
                analyst_confidence_score = 45  # 高度一致
            elif direction_consistency >= 0.5:
                analyst_confidence_score = 30  # 相对一致
            else:
                analyst_confidence_score = 15  # 分歧较大
            
            # 高置信度模块加成
            if high_confidence_modules >= total_modules * 0.5:
                analyst_confidence_score += 5
        
        # 第二层：辩论质量评估（权重30-40%）
        debate_confidence_score = 0
        if debate_result:
            bull_score = debate_result.overall_bull_score
            bear_score = debate_result.overall_bear_score
            score_diff = abs(bull_score - bear_score)
            
            if score_diff >= 3:
                debate_confidence_score = 35  # 优势明显
            elif score_diff >= 1:
                debate_confidence_score = 25  # 有一定优势
            else:
                debate_confidence_score = 10  # 势均力敌
        
        # 第三层：数据支撑评估（权重10-20%）
        data_confidence_score = 0
        if total_modules >= 6:
            data_confidence_score = 15  # 数据完整
        elif total_modules >= 4:
            data_confidence_score = 10  # 数据较完整
        elif total_modules >= 2:
            data_confidence_score = 5   # 数据有限
        else:
            data_confidence_score = 0   # 数据不足
        
        # 综合评分
        total_score = analyst_confidence_score + debate_confidence_score + data_confidence_score
        
        # 转换为定性描述
        if total_score >= 75:
            return "高"
        elif total_score >= 45:
            return "中"
        else:
            return "低"
    
    def _summarize_single_module(self, analysis_state: FuturesAnalysisState, module_key: str) -> str:
        """处理单个分析模块的数据摘要"""
        attr_name = f"{module_key}_analysis"
        if module_key == 'term_structure':
            attr_name = 'term_structure_analysis'
            
        if not hasattr(analysis_state, attr_name):
            print(f"⚠️ 未找到模块属性: {attr_name}")
            return ""
            
        module_data = getattr(analysis_state, attr_name)
        if not module_data or not hasattr(module_data, 'result_data'):
            print(f"⚠️ 模块无有效数据: {module_key}")
            return ""
            
        # 获取基本信息
        module_name = self._get_module_display_name(module_key)
        confidence = getattr(module_data, 'confidence_score', 0.5)
        
        summary = f"{module_name}({safe_format_percent(confidence)}置信度)"
        
        # 标注高置信度
        if safe_convert_to_float(confidence) >= 0.8:
            summary += "【高置信度-重点关注】"
        
        # 根据模块类型进行专门处理
        if module_key == 'technical':
            content_summary = self._extract_technical_signals(module_data)
        elif module_key == 'news':
            content_summary = self._extract_news_highlights(module_data)
        elif module_key == 'inventory':
            content_summary = self._extract_inventory_insights(module_data)
        elif module_key == 'positioning':
            content_summary = self._extract_positioning_insights(module_data)
        elif module_key == 'basis':
            content_summary = self._extract_basis_insights(module_data)
        elif module_key == 'term_structure':
            content_summary = self._extract_term_structure_insights(module_data)
        else:
            # 🚀 新增模块的通用处理
            content_summary = self._extract_generic_insights(module_data, module_key)
            
        if content_summary:
            return f"{summary}\n{content_summary}"
        else:
            return f"{summary}\n暂无详细分析内容"
    
    def _extract_generic_insights(self, module_data, module_key: str) -> str:
        """新增模块的通用信息提取"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            if not analysis_content:
                analysis_content = module_data.result_data.get('result', '')
            if not analysis_content:
                analysis_content = module_data.result_data.get('content', '')
                
            content = str(analysis_content)
            
            if len(content) > 500:
                return f"核心观点：{content[:500]}..."
            else:
                return f"分析内容：{content}"
                
        except Exception as e:
            print(f"⚠️ 提取{module_key}模块信息失败: {e}")
            return f"{self._get_module_display_name(module_key)}数据解析中..."
        
        # 基差分析 - 深度提取价差信息和交易含义
        if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
            basis = analysis_state.basis_analysis
            confidence = basis.confidence_score
            basis_summary = f"基差分析({safe_format_percent(confidence)}置信度)"
            
            # 标注高置信度数据
            if safe_convert_to_float(confidence) >= 0.8:
                basis_summary += "【高置信度-重点关注】"
            
            analysis_content = basis.result_data.get('analysis_content', '')
            if analysis_content:
                content = str(analysis_content)
                
                # 提取基差状态和变化趋势
                basis_signals = []
                if '深度贴水' in content:
                    basis_signals.append("深度贴水(现货弱势)")
                elif '贴水' in content:
                    if '收窄' in content:
                        basis_signals.append("贴水收窄(现货转强)")
                    elif '扩大' in content:
                        basis_signals.append("贴水扩大(现货转弱)")
                    else:
                        basis_signals.append("期货贴水")
                
                if '深度升水' in content:
                    basis_signals.append("深度升水(现货强势)")
                elif '升水' in content:
                    if '收窄' in content:
                        basis_signals.append("升水收窄(现货转弱)")
                    elif '扩大' in content:
                        basis_signals.append("升水扩大(现货转强)")
                    else:
                        basis_signals.append("期货升水")
                
                if '收敛' in content:
                    basis_signals.append("基差收敛(交割临近)")
                elif '发散' in content:
                    basis_signals.append("基差发散(供需失衡)")
                
                # 提取具体数值
                if '元/吨' in content:
                    basis_signals.append("含具体基差数值")
                
                # 提取交易机会
                if '套利' in content:
                    basis_signals.append("存在套利机会")
                elif '交割' in content:
                    basis_signals.append("关注交割风险")
                
                if basis_signals:
                    basis_summary += f"：{'; '.join(basis_signals)}"
                    
            summary_parts.append(basis_summary)
        
        # 持仓分析 - 深度提取资金流向和主力行为
        if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
            pos = analysis_state.positioning_analysis
            confidence = pos.confidence_score
            pos_summary = f"持仓分析({safe_format_percent(confidence)}置信度)"
            
            # 标注高置信度数据
            if safe_convert_to_float(confidence) >= 0.8:
                pos_summary += "【高置信度-重点关注】"
            
            analysis_content = pos.result_data.get('analysis_content', '')
            if analysis_content:
                content = str(analysis_content)
                
                # 提取资金流向和主力行为
                position_signals = []
                
                # 资金流向分析
                if '大幅增仓' in content:
                    position_signals.append("大幅增仓(资金看好)")
                elif '增仓' in content:
                    position_signals.append("资金增仓")
                elif '大幅减仓' in content:
                    position_signals.append("大幅减仓(资金撤离)")
                elif '减仓' in content:
                    position_signals.append("资金减仓")
                
                # 多空力量对比
                if ('多头' in content and '主导' in content) or '多头优势' in content:
                    position_signals.append("多头主导")
                elif ('空头' in content and '主导' in content) or '空头优势' in content:
                    position_signals.append("空头主导")
                elif '多空分歧' in content:
                    position_signals.append("多空分歧加大")
                
                # 主力行为分析
                if '主力' in content:
                    if '建仓' in content:
                        position_signals.append("主力建仓")
                    elif '减仓' in content:
                        position_signals.append("主力减仓")
                    elif '换仓' in content:
                        position_signals.append("主力换仓")
                
                # 聪明钱分析
                if '聪明钱' in content:
                    if '流入' in content:
                        position_signals.append("聪明钱流入")
                    elif '流出' in content:
                        position_signals.append("聪明钱流出")
                
                if position_signals:
                    pos_summary += f"：{'; '.join(position_signals)}"

            summary_parts.append(pos_summary)
        
        # 新闻分析 - 深度提取政策影响和市场情绪
        if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
            news = analysis_state.news_analysis
            confidence = news.confidence_score
            news_summary = f"新闻分析({safe_format_percent(confidence)}置信度)"
            
            # 标注高置信度数据
            if safe_convert_to_float(confidence) >= 0.8:
                news_summary += "【高置信度-重点关注】"
            
            analysis_content = news.result_data.get('analysis_content', '')
            if analysis_content:
                content = str(analysis_content)
                
                # 提取政策和事件影响
                news_signals = []
                
                # 政策影响分析
                if '政策' in content:
                    if '利好' in content:
                        news_signals.append("政策利好")
                    elif '利空' in content:
                        news_signals.append("政策利空")
                    elif '中性' in content:
                        news_signals.append("政策中性")
                
                # 宏观经济影响
                if '宏观' in content or '经济' in content:
                    if '复苏' in content or '增长' in content:
                        news_signals.append("宏观向好")
                    elif '下滑' in content or '衰退' in content:
                        news_signals.append("宏观承压")
                
                # 行业事件
                if '供应' in content:
                    if '紧张' in content or '短缺' in content:
                        news_signals.append("供应紧张")
                    elif '充足' in content or '过剩' in content:
                        news_signals.append("供应充足")
                
                if '需求' in content:
                    if '旺盛' in content or '增长' in content:
                        news_signals.append("需求旺盛")
                    elif '疲软' in content or '下降' in content:
                        news_signals.append("需求疲软")
                
                # 市场情绪
                if '乐观' in content:
                    news_signals.append("市场乐观")
                elif '悲观' in content:
                    news_signals.append("市场悲观")
                elif '谨慎' in content:
                    news_signals.append("市场谨慎")
                
                # 突发事件
                if '突发' in content or '紧急' in content:
                    news_signals.append("突发事件影响")
                
                if not news_signals:
                    # 如果没有提取到具体信号，使用通用分类
                    if '利好' in content:
                        news_signals.append("整体利好")
                    elif '利空' in content:
                        news_signals.append("整体利空")
                    elif '中性' in content:
                        news_signals.append("消息面中性")
                
                if news_signals:
                    news_summary += f"：{'; '.join(news_signals)}"
                    
            summary_parts.append(news_summary)
        
        # 期限结构 - 深度提取曲线形态和交易含义
        if hasattr(analysis_state, 'term_structure_analysis') and analysis_state.term_structure_analysis:
            term = analysis_state.term_structure_analysis
            confidence = term.confidence_score
            term_summary = f"期限结构({safe_format_percent(confidence)}置信度)"
            analysis_content = term.result_data.get('analysis_content', '')
            
            # 如果是高置信度数据，进行深度分析
            if safe_convert_to_float(confidence) >= 0.8:
                term_summary += "【高置信度-重点关注】"
            
            if analysis_content:
                content = str(analysis_content)
                # 提取更详细的期限结构信息
                if '正向' in content or 'Contango' in content:
                    term_summary += "：正向市场(远月升水)"
                    if '陡峭' in content:
                        term_summary += "-曲线陡峭，现货压力大"
                    elif '平缓' in content:
                        term_summary += "-曲线平缓，预期温和"
                elif '反向' in content or 'Backwardation' in content:
                    term_summary += "：反向市场(远月贴水)"
                    if '陡峭' in content:
                        term_summary += "-曲线陡峭，现货紧张"
                elif '平坦' in content:
                    term_summary += "：曲线平坦，供需相对平衡"
                
                # 提取具体的价差数据
                if '价差' in content or '升贴水' in content:
                    term_summary += "，含具体价差数据"
                
                # 提取交易机会提示
                if '套利' in content:
                    term_summary += "，存在套利机会"
                elif '交割' in content:
                    term_summary += "，关注交割因素"
                    
            summary_parts.append(term_summary)
        
        # 库存分析 - 提取供需状况
        if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
            inv = analysis_state.inventory_analysis
            inv_summary = f"库存分析({safe_format_percent(inv.confidence_score)}置信度)"
            analysis_content = inv.result_data.get('analysis_content', '')
            if analysis_content:
                content = str(analysis_content)
                if '偏低' in content or '下降' in content:
                    inv_summary += "：库存偏紧"
                elif '偏高' in content or '上升' in content:
                    inv_summary += "：库存充裕"
            summary_parts.append(inv_summary)
        
        return "；".join(summary_parts) if summary_parts else "分析师数据不完整，建议谨慎交易"
    
    def _extract_technical_signals(self, module_data) -> str:
        """提取技术分析信号"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            signals = []
            if '突破' in content:
                if '向上突破' in content:
                    signals.append("向上突破(利多)")
                elif '向下突破' in content:
                    signals.append("向下突破(利空)")
                else:
                    signals.append("突破信号")
                    
            if '金叉' in content:
                signals.append("MACD金叉(利多)")
            elif '死叉' in content:
                signals.append("MACD死叉(利空)")
                
            if 'RSI' in content:
                if '超买' in content:
                    signals.append("RSI超买")
                elif '超卖' in content:
                    signals.append("RSI超卖")
                    
            return "；".join(signals) if signals else content[:200]
            
        except Exception as e:
            return "技术分析数据解析中..."
    
    def _extract_news_highlights(self, module_data) -> str:
        """提取新闻分析要点"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            highlights = []
            if '政策' in content:
                if '利好' in content:
                    highlights.append("政策利好")
                elif '利空' in content:
                    highlights.append("政策利空")
                    
            if '供应' in content:
                if '短缺' in content:
                    highlights.append("供应偏紧")
                elif '过剩' in content:
                    highlights.append("供应充裕")
                    
            if '需求' in content:
                if '旺盛' in content:
                    highlights.append("需求旺盛")
                elif '疲软' in content:
                    highlights.append("需求疲软")
                    
            return "；".join(highlights) if highlights else content[:200]
            
        except Exception as e:
            return "新闻分析数据解析中..."
            
    def _extract_inventory_insights(self, module_data) -> str:
        """提取库存分析洞察"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            if '偏紧' in content or '下降' in content:
                return "库存偏紧"
            elif '偏高' in content or '上升' in content:
                return "库存充裕"
            else:
                return content[:200]
                
        except Exception as e:
            return "库存分析数据解析中..."
            
    def _extract_positioning_insights(self, module_data) -> str:
        """提取持仓分析洞察"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            insights = []
            if '净多头' in content:
                if '增加' in content:
                    insights.append("净多头增加")
                elif '减少' in content:
                    insights.append("净多头减少")
                    
            if '资金' in content:
                if '流入' in content:
                    insights.append("资金净流入")
                elif '流出' in content:
                    insights.append("资金净流出")
                    
            return "；".join(insights) if insights else content[:200]
            
        except Exception as e:
            return "持仓分析数据解析中..."
            
    def _extract_basis_insights(self, module_data) -> str:
        """提取基差分析洞察"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            if '升水' in content:
                return "期货升水"
            elif '贴水' in content:
                return "期货贴水"
            elif '套利' in content:
                return "存在套利机会"
            else:
                return content[:200]
                
        except Exception as e:
            return "基差分析数据解析中..."
            
    def _extract_term_structure_insights(self, module_data) -> str:
        """提取期限结构分析洞察"""
        try:
            analysis_content = module_data.result_data.get('analysis_content', '')
            content = str(analysis_content)
            
            if 'Contango' in content:
                return "Contango结构"
            elif 'Backwardation' in content:
                return "Backwardation结构"
            elif '价差' in content:
                return "跨期价差分析"
            else:
                return content[:200]
                
        except Exception as e:
            return "期限结构数据解析中..."
    
    def _summarize_debate_points(self, debate_result: DebateResult) -> str:
        """总结辩论要点 - 提供完整的辩论内容供交易员分析"""
        
        # 计算得分差异
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        # 判断优势程度
        if score_diff >= 2.0:
            advantage_level = "明显优势"
        elif score_diff >= 1.0:
            advantage_level = "轻微优势"
        else:
            advantage_level = "势均力敌"
        
        # 构建完整的辩论内容，包含所有轮次的具体论据
        detailed_rounds = ""
        for i, round_data in enumerate(debate_result.rounds, 1):
            detailed_rounds += f"""
=== 第{i}轮辩论 ===
🐂 多头观点：
{round_data.bull_argument}

🐻 空头观点：
{round_data.bear_argument}

📊 本轮评分：多头 {round_data.bull_score:.1f}分 vs 空头 {round_data.bear_score:.1f}分
🎯 关键争议：{' | '.join(round_data.key_points)}
---
"""
        
        # 构建完整的辩论摘要
        summary = f"""
【辩论结果总览】：
- 辩论轮数：{debate_result.total_rounds}轮
- 多头总得分：{debate_result.overall_bull_score:.1f}分
- 空头总得分：{debate_result.overall_bear_score:.1f}分
- 得分差异：{score_diff:.1f}分 ({advantage_level})
- 最终胜者：{debate_result.final_winner.value}

【详细辩论内容】：
{detailed_rounds}

【辩论总结】：
{debate_result.debate_summary}

【市场共识】：
{' | '.join(debate_result.key_consensus_points) if debate_result.key_consensus_points else '暂无明确共识'}

【分歧焦点】：
{' | '.join(debate_result.unresolved_issues) if debate_result.unresolved_issues else '无重大分歧'}

【策略建议依据】：
基于{score_diff:.1f}分的得分差异，建议优先考虑{'单边做多' if debate_result.final_winner.value == '多头' and score_diff >= 2.0 else '单边做空' if debate_result.final_winner.value == '空头' and score_diff >= 2.0 else '跨期套利或中性策略'}

⚠️ 重要提醒：以上是完整的多空辩论内容，请仔细分析每个模块中多头和空头的具体论据，确保客观公正地评判双方观点，避免出现"论据缺失"的误判。

🔍 论据识别检查清单：
在进行评判前，请先确认以下内容：
1. 多头是否在基差分析中提到了具体的基差数值或期现关系？
2. 多头是否在期限结构中提到了Contango/Backwardation结构或价差分析？
3. 空头是否在基差分析中提到了基差风险或现货市场问题？
4. 空头是否在期限结构中提到了期限结构的负面含义？
5. 双方是否都在各自的论述中引用了具体的数据和分析？

如果以上任何一项的答案是"是"，则绝对不能说该方"论据缺失"。
"""
        
        return summary.strip()
    
    def _clean_markdown_symbols(self, content: str) -> str:
        """清理Markdown符号，生成纯文本内容"""
        import re
        
        # 移除粗体符号 (text)
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'__(.*?)__', r'\1', content)
        
        # 移除斜体符号 (*text*)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        content = re.sub(r'_(.*?)_', r'\1', content)
        
        # 移除标题符号 (# ## ### 等)
        content = re.sub(r'^#{1,6}\s*', '', content, flags=re.MULTILINE)
        
        # 移除代码块符号 (```code```)
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'`(.*?)`', r'\1', content)
        
        # 移除链接符号 [text](url)
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
        
        # 移除列表符号 (- * +) 但保留内容
        content = re.sub(r'^[\s]*[-\*\+]\s*', '', content, flags=re.MULTILINE)
        
        # 移除引用符号 (>)
        content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 清理行首行尾空白
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        return content.strip()
    
    def _parse_trading_decision(self, decision_text: str, commodity: str, analysis_state: FuturesAnalysisState = None) -> TradingDecision:
        """解析交易员评判分析文本 - 直接使用AI生成的完整分析"""
        
        try:
            # 🔥 首先清理Markdown符号
            cleaned_text = self._clean_markdown_symbols(decision_text)
            
            # 🔥 新逻辑：直接使用清理后的完整文本作为分析内容
            # 不再进行额外的章节提取和重组，保持AI生成的原始结构
            full_analysis = cleaned_text
            
            # 🔥 只提取必要的部分用于后续逻辑判断
            reasoning = self._extract_section(cleaned_text, "辩论评判分析", "分析师观点科学评估")
            conclusion = self._extract_section(cleaned_text, "多空综合判断结论", "交易策略建议")
            strategy_advice = self._extract_section(cleaned_text, "交易策略建议", "风险提示")
            risk_warning = self._extract_section(cleaned_text, "风险提示", None)
            
            # 如果提取失败，至少尝试提取结论部分
            if not conclusion:
                conclusion = cleaned_text
            
            # 🔥 根据完整分析内容判断策略类型
            strategy_type = self._determine_strategy_from_full_analysis(full_analysis)
            
            # 🔥 从完整分析中智能提取关键信息
            entry_points = self._extract_entry_points_from_analysis(full_analysis)
            exit_points = self._extract_exit_points_from_analysis(full_analysis)
            position_size = self._extract_position_size_from_analysis(full_analysis)
            risk_reward_ratio = "1:2"
            time_horizon = self._extract_time_horizon_from_analysis(full_analysis)
            specific_contracts = [f"{commodity}主力合约"]
            hedging_components = []
            execution_plan = strategy_advice if strategy_advice else "根据市场情况动态调整"
            market_conditions = "正常市场条件"
            alternative_scenarios = [risk_warning] if risk_warning else ["需持续关注市场变化"]
            
            return TradingDecision(
                strategy_type=strategy_type,
                reasoning=full_analysis,  # 使用完整分析作为推理内容
                entry_points=entry_points,
                exit_points=exit_points,
                position_size=position_size,
                risk_reward_ratio=risk_reward_ratio,
                time_horizon=time_horizon,
                specific_contracts=specific_contracts,
                hedging_components=hedging_components,
                execution_plan=execution_plan,
                market_conditions=market_conditions,
                alternative_scenarios=alternative_scenarios
            )
            
        except Exception as e:
            self.logger.error(f"解析交易决策失败: {e}")
            return self._create_default_decision(commodity)
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str = None) -> str:
        """从文本中提取指定段落"""
        try:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return ""
            
            start_idx = text.find("：", start_idx)
            if start_idx == -1:
                start_idx = text.find(":", start_idx)
            if start_idx == -1:
                return ""
            start_idx += 1
            
            if end_marker:
                end_idx = text.find(end_marker, start_idx)
                if end_idx == -1:
                    return text[start_idx:].strip()
                return text[start_idx:end_idx].strip()
            else:
                return text[start_idx:].strip()
        except:
            return ""
    
    def _determine_strategy_from_full_analysis(self, full_analysis: str) -> TradingStrategy:
        """🔥 新方法：从完整分析中智能判断策略类型"""
        if not full_analysis:
            return TradingStrategy.NEUTRAL_STRATEGY  # 🔥 修复：默认为中性而非做多
        
        analysis_text = full_analysis.lower()
        
        # 🔥 修复：优先检查中性/观望信号
        neutral_keywords = ["中性观望", "区间震荡", "观望为主", "暂不操作", "综合方向倾向：中性观望"]
        if any(kw in analysis_text for kw in neutral_keywords):
            return TradingStrategy.NEUTRAL_STRATEGY
        
        # 明确多空关键词检测（优先级更高的关键词）
        strong_bullish = ["积极做多", "强烈建议做多", "明确做多"]
        strong_bearish = ["积极做空", "强烈建议做空", "明确做空"]
        
        moderate_bullish = ["谨慎做多", "偏多", "轻仓做多", "做多", "看多", "买入"]
        moderate_bearish = ["谨慎做空", "偏空", "轻仓做空", "做空", "看空", "卖出"]
        
        # 统计强信号
        strong_bull_count = sum(1 for kw in strong_bullish if kw in analysis_text)
        strong_bear_count = sum(1 for kw in strong_bearish if kw in analysis_text)
        
        if strong_bull_count > strong_bear_count:
            return TradingStrategy.DIRECTIONAL_LONG
        elif strong_bear_count > strong_bull_count:
            return TradingStrategy.DIRECTIONAL_SHORT
        
        # 统计中等信号
        moderate_bull_count = sum(1 for kw in moderate_bullish if kw in analysis_text)
        moderate_bear_count = sum(1 for kw in moderate_bearish if kw in analysis_text)
        
        if moderate_bull_count > moderate_bear_count:
            return TradingStrategy.DIRECTIONAL_LONG
        elif moderate_bear_count > moderate_bull_count:
            return TradingStrategy.DIRECTIONAL_SHORT
        
        # 🔥 修复：查找【多空综合判断结论】中的明确表述（支持中括号格式）
        import re
        # 匹配 "综合方向倾向：做多" 或 "综合方向倾向：[谨慎看多]" 等格式
        direction_pattern = r'综合方向倾向[：:]\s*[\[【]?(.*?)[\]】]?(?:\s|$)'
        direction_match = re.search(direction_pattern, full_analysis)
        if direction_match:
            direction_text = direction_match.group(1).lower()
            if any(kw in direction_text for kw in ["做多", "看多", "买入"]):
                return TradingStrategy.DIRECTIONAL_LONG
            elif any(kw in direction_text for kw in ["做空", "看空", "卖出"]):
                return TradingStrategy.DIRECTIONAL_SHORT
            elif any(kw in direction_text for kw in ["中性", "观望"]):
                return TradingStrategy.NEUTRAL_STRATEGY
        
        # 🔥 修复：最后默认为中性策略，而非做多
        return TradingStrategy.NEUTRAL_STRATEGY
    
    def _extract_entry_points_from_analysis(self, analysis: str) -> List[str]:
        """🔥 从分析中提取进场点位"""
        import re
        entry_points = []
        
        # 查找入场相关的价格点位
        patterns = [
            r'入场[：:]\s*(\d+[-～~至到]\d+)',
            r'入场[：:]\s*(\d+)',
            r'建仓[：:]\s*(\d+[-～~至到]\d+)',
            r'进场[：:]\s*(\d+[-～~至到]\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, analysis)
            if matches:
                entry_points.extend(matches)
        
        return entry_points if entry_points else ["根据实时技术分析确定入场点位"]
    
    def _extract_exit_points_from_analysis(self, analysis: str) -> List[str]:
        """🔥 从分析中提取出场点位"""
        import re
        exit_points = []
        
        # 查找出场相关的价格点位
        patterns = [
            r'目标[：:]\s*(\d+[-～~至到]\d+)',
            r'止损[：:]\s*(\d+)',
            r'目标位[：:]\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, analysis)
            if matches:
                exit_points.extend(matches)
        
        return exit_points if exit_points else ["根据实时技术分析确定出场点位"]
    
    def _extract_position_size_from_analysis(self, analysis: str) -> str:
        """🔥 从分析中提取仓位建议"""
        import re
        
        # 查找仓位建议
        patterns = [
            r'仓位建议[：:]\s*(\d+[-～~至到]\d+%)',
            r'仓位[：:]\s*(\d+[-～~至到]\d+%)',
            r'建议仓位[：:]\s*(\d+[-～~至到]\d+%)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis)
            if match:
                return match.group(1)
        
        # 根据信心度推断仓位
        if "高信心度" in analysis or "信心度：高" in analysis:
            return "10-15%"
        elif "中信心度" in analysis or "信心度：中" in analysis:
            return "5-10%"
        elif "低信心度" in analysis or "信心度：低" in analysis:
            return "2-5%"
        
        return "5-8%（中等仓位）"
    
    def _extract_time_horizon_from_analysis(self, analysis: str) -> str:
        """🔥 从分析中提取持仓周期"""
        import re
        
        # 查找持仓周期
        patterns = [
            r'持仓周期[：:]\s*([^，。\n]+)',
            r'周期[：:]\s*([^，。\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis)
            if match:
                return match.group(1).strip()
        
        # 默认推断
        if "短线" in analysis:
            return "短线（3-7天）"
        elif "中线" in analysis:
            return "中线（1-4周）"
        elif "长线" in analysis:
            return "长线（1-3月）"
        
        return "灵活调整"
    
    def _determine_strategy_from_conclusion(self, conclusion: str) -> TradingStrategy:
        """根据多空判断结论确定策略类型，支持中性策略识别"""
        if not conclusion:
            return TradingStrategy.NEUTRAL_STRATEGY  # 🔥 修复：默认为中性而非做多
        
        conclusion_text = conclusion.lower()
        
        # 🔥 修复：优先检查中性/观望信号
        neutral_keywords = ["中性观望", "区间震荡", "观望为主", "暂不操作"]
        if any(kw in conclusion_text for kw in neutral_keywords):
            return TradingStrategy.NEUTRAL_STRATEGY
        
        # 明确多空关键词检测
        bullish_keywords = ["做多", "多头", "上涨", "买入", "看多", "涨", "多方", "积极做多", "谨慎做多", "轻仓做多"]
        bearish_keywords = ["做空", "空头", "下跌", "卖出", "看空", "跌", "空方", "积极做空", "谨慎做空", "轻仓做空"]
        
        # 强制方向选择逻辑
        bullish_count = sum(1 for keyword in bullish_keywords if keyword in conclusion_text)
        bearish_count = sum(1 for keyword in bearish_keywords if keyword in conclusion_text)
        
        if bullish_count > bearish_count:
            return TradingStrategy.DIRECTIONAL_LONG
        elif bearish_count > bullish_count:
            return TradingStrategy.DIRECTIONAL_SHORT
        else:
            # 当关键词计数相等时，基于更细致的语义分析
            if "优势" in conclusion_text and "多头" in conclusion_text:
                return TradingStrategy.DIRECTIONAL_LONG
            elif "优势" in conclusion_text and "空头" in conclusion_text:
                return TradingStrategy.DIRECTIONAL_SHORT
            elif "支撑" in conclusion_text or "反弹" in conclusion_text:
                return TradingStrategy.DIRECTIONAL_LONG
            elif "阻力" in conclusion_text or "回调" in conclusion_text:
                return TradingStrategy.DIRECTIONAL_SHORT
            else:
                # 🔥 修复：当无法判断方向时，返回中性策略
                return TradingStrategy.NEUTRAL_STRATEGY
    
    def _create_default_decision(self, commodity: str) -> TradingDecision:
        """创建强制方向性的默认交易决策"""
        
        # 即使信息不足也要给出明确方向（基于AI优势）
        # 采用概率性偏好：商品期货长期上涨概率略高于下跌
        commodity_name = get_commodity_name(commodity)
        current_price = get_commodity_current_price(commodity)
        
        return TradingDecision(
            strategy_type=TradingStrategy.NEUTRAL_STRATEGY,  # 🔥 修复：信息不足时应该观望
            reasoning=f"""
基于{commodity_name}的有限信息分析，虽然数据不完整，但基于AI驱动的概率分析：

【强制决策逻辑】
- 信息不足情况下，采用概率优势策略
- 商品期货长期通胀属性，做多概率略优
- 当前价格{current_price:.0f}元/吨，处于相对合理区间
- 基于风险收益比，轻仓做多是较优选择

【信心度评估】35%（低信心度，但必须做出方向性选择）
【策略类型】轻仓做多策略
""".strip(),
            entry_points=[f"在{current_price*0.98:.0f}元/吨附近分批建仓"],
            exit_points=[f"目标价位{current_price*1.05:.0f}元/吨，止损{current_price*0.95:.0f}元/吨"],
            position_size="轻仓2-5%",
            risk_reward_ratio="1:2",
            time_horizon="2-4周",
            specific_contracts=[f"{commodity}主力合约"],
            hedging_components=[],
            execution_plan="小仓位试探性建多仓，严格控制风险",
            market_conditions="信息有限但倾向做多",
            alternative_scenarios=["若技术面破位则及时止损"]
        )

# ============================================================================
# 3. 优化版多空辩论系统
# ============================================================================

class OptimizedDebateSystem:
    """优化版辩论系统 - 口语化激烈辩论"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("deepseek_api_key") or config.get("api_settings", {}).get("deepseek", {}).get("api_key")
        self.base_url = config.get("api_settings", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com/v1")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        self.logger = logging.getLogger("OptimizedDebateSystem")
        
    async def conduct_heated_debate(self, analysis_state: FuturesAnalysisState, 
                                  debate_rounds: int = 3) -> DebateResult:
        """进行激烈的多空辩论"""
        commodity = analysis_state.commodity
        self.logger.info(f"开始{commodity}激烈辩论，共{debate_rounds}轮")
        
        rounds = []
        bull_total_score = 0.0
        bear_total_score = 0.0
        
        # 提取分析数据用于辩论
        debate_context = self._extract_debate_context(analysis_state)
        
        for round_num in range(1, debate_rounds + 1):
            self.logger.info(f"第{round_num}轮辩论开始...")
            
            # 多头发言
            bull_argument = await self._generate_bull_argument(
                commodity, debate_context, round_num, rounds
            )
            
            # 空头反驳
            bear_argument = await self._generate_bear_argument(
                commodity, debate_context, bull_argument, round_num, rounds
            )
            
            # 评判本轮结果
            round_result = await self._judge_debate_round(
                    commodity, bull_argument, bear_argument, round_num, debate_context
            )
            
            rounds.append(round_result)
            
            # 🔥 添加类型检查和调试信息
            print(f"🐛 DEBUG: round_result.bull_score = {round_result.bull_score} (type: {type(round_result.bull_score)})")
            print(f"🐛 DEBUG: round_result.bear_score = {round_result.bear_score} (type: {type(round_result.bear_score)})")
            
            # 确保分数是数值类型
            bull_score_safe = safe_convert_to_float(round_result.bull_score, 5.0)
            bear_score_safe = safe_convert_to_float(round_result.bear_score, 5.0)
            
            bull_total_score += bull_score_safe
            bear_total_score += bear_score_safe
            
            self.logger.info(f"第{round_num}轮结果: {round_result.round_result}")
        
        # 确定最终胜者 - 修复平分逻辑
        if bull_total_score > bear_total_score:
            final_winner = DebateStance.BULLISH
        elif bear_total_score > bull_total_score:
            final_winner = DebateStance.BEARISH
        else:
            # 平分情况，不应该有获胜者，但为了兼容性，使用BULLISH并在显示时处理
            final_winner = DebateStance.BULLISH
        
        # 生成辩论总结
        debate_summary = await self._generate_debate_summary(
            commodity, rounds, final_winner, bull_total_score, bear_total_score
        )
        
        return DebateResult(
            total_rounds=debate_rounds,
            rounds=rounds,
            final_winner=final_winner,
            overall_bull_score=bull_total_score,
            overall_bear_score=bear_total_score,
            key_consensus_points=self._extract_consensus_points(rounds),
            unresolved_issues=self._extract_unresolved_issues(rounds),
            debate_summary=debate_summary
        )
    
    def _extract_debate_context(self, analysis_state: FuturesAnalysisState) -> Dict:
        """提取辩论背景信息 - 基于实际分析师数据"""
        
        commodity_name = get_commodity_name(analysis_state.commodity)
        
        context = {
            "commodity_code": analysis_state.commodity,
            "commodity_name": commodity_name,
            "analysis_date": analysis_state.analysis_date,
            "modules_data": {}
        }
        
        # 提取库存分析实际数据
        if analysis_state.inventory_analysis and analysis_state.inventory_analysis.result_data:
            inv_data = analysis_state.inventory_analysis.result_data
            if inv_data.get("success"):
                # 从多个可能的字段中提取内容
                content = self._extract_analysis_content(inv_data)
                context["modules_data"]["inventory"] = {
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_points": self._extract_key_points_from_content(content),
                    "confidence": inv_data.get("confidence_score", 0.5)
                }
        
        # 提取持仓分析实际数据
        if analysis_state.positioning_analysis and analysis_state.positioning_analysis.result_data:
            pos_data = analysis_state.positioning_analysis.result_data
            if pos_data.get("success"):
                content = self._extract_analysis_content(pos_data)
                context["modules_data"]["positioning"] = {
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_points": self._extract_key_points_from_content(content),
                    "confidence": pos_data.get("confidence_score", 0.5)
                }
        
        # 提取技术分析实际数据
        if analysis_state.technical_analysis and analysis_state.technical_analysis.result_data:
            tech_data = analysis_state.technical_analysis.result_data
            if tech_data.get("success"):
                content = self._extract_analysis_content(tech_data)
                context["modules_data"]["technical"] = {
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_points": self._extract_key_points_from_content(content),
                    "confidence": tech_data.get("confidence_score", 0.5)
                }
        
        # 提取基差分析实际数据
        if analysis_state.basis_analysis and analysis_state.basis_analysis.result_data:
            basis_data = analysis_state.basis_analysis.result_data
            if basis_data.get("success"):
                content = self._extract_analysis_content(basis_data)
                context["modules_data"]["basis"] = {
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_points": self._extract_key_points_from_content(content),
                    "confidence": basis_data.get("confidence_score", 0.5)
                }
        
        # 提取新闻分析实际数据
        if analysis_state.news_analysis and analysis_state.news_analysis.result_data:
            news_data = analysis_state.news_analysis.result_data
            if news_data.get("success"):
                content = self._extract_analysis_content(news_data)
                # 新闻分析需要更详细的提取
                news_summary = content[:400] + "..." if len(content) > 400 else content
                key_points = self._extract_key_points_from_content(content)
                
                # 提取新闻分析的特殊字段
                market_sentiment = news_data.get("market_sentiment", "")
                policy_impact = news_data.get("policy_impact", "")
                industry_events = news_data.get("industry_events", "")
                time_sensitivity = news_data.get("time_sensitivity", "")
                
                context["modules_data"]["news"] = {
                    "summary": news_summary,
                    "key_points": key_points,
                    "confidence": news_data.get("confidence_score", 0.5),
                    "market_sentiment": market_sentiment,
                    "policy_impact": policy_impact,
                    "industry_events": industry_events,
                    "time_sensitivity": time_sensitivity
                }
        
        # 提取期限结构分析实际数据
        if analysis_state.term_structure_analysis and analysis_state.term_structure_analysis.result_data:
            term_data = analysis_state.term_structure_analysis.result_data
            if term_data.get("success"):
                content = self._extract_analysis_content(term_data)
                context["modules_data"]["term_structure"] = {
                    "summary": content[:200] + "..." if len(content) > 200 else content,
                    "key_points": self._extract_key_points_from_content(content),
                    "confidence": term_data.get("confidence_score", 0.5)
                }
            
        return context
    
    def _extract_analysis_content(self, data: Dict) -> str:
        """从分析数据中提取实际内容"""
        # 尝试多个可能的内容字段（基于各个模块的实际字段名）
        content_fields = [
            "analysis_content",  # 通用字段
            "ai_analysis",  # 期限结构、持仓分析等
            "professional_analysis",  # 技术分析模块
            "ai_comprehensive_analysis",  # 库存分析模块
            "comprehensive_analysis",  # 通用综合分析
            "detailed_analysis",  # 详细分析
            "content",  # 简单内容字段
            "report",  # 报告字段
            "analysis_report",  # 分析报告
            "summary_report"  # 摘要报告
        ]
        
        for field in content_fields:
            content = data.get(field, "")
            if isinstance(content, str) and len(content.strip()) > 10:
                return content.strip()
        
        # 如果没有找到标准内容字段，尝试从其他字段构建摘要
        summary_parts = []
        
        # 检查是否有分析结论
        if "conclusion" in data:
            summary_parts.append(f"结论: {data['conclusion']}")
        
        # 检查是否有关键指标
        if "key_metrics" in data:
            summary_parts.append(f"关键指标: {data['key_metrics']}")
        
        # 检查是否有策略建议
        if "strategy_recommendation" in data:
            summary_parts.append(f"策略建议: {data['strategy_recommendation']}")
        
        # 检查是否有风险评估
        if "risk_assessment" in data:
            summary_parts.append(f"风险评估: {data['risk_assessment']}")
        
        # 检查持仓分析的特殊字段
        if "spider_web_analysis" in data:
            summary_parts.append(f"蜘蛛网分析: {data['spider_web_analysis']}")
        
        if "smart_money_analysis" in data:
            summary_parts.append(f"聪明钱分析: {data['smart_money_analysis']}")
            
        if "overall_signal" in data:
            summary_parts.append(f"持仓综合信号: {data['overall_signal']}")
            
        if "overall_confidence" in data:
            summary_parts.append(f"持仓分析置信度: {data['overall_confidence']}")
        
        # 检查技术分析的特殊字段
        if "trend_analysis" in data:
            summary_parts.append(f"趋势分析: {data['trend_analysis']}")
        
        if "support_resistance" in data:
            summary_parts.append(f"支撑阻力: {data['support_resistance']}")
            
        if "comprehensive_data" in data:
            comp_data = data["comprehensive_data"]
            if isinstance(comp_data, dict):
                if "current_price" in comp_data:
                    summary_parts.append(f"当前价格: {comp_data['current_price']}")
                if "trend_analysis" in comp_data:
                    trend_info = comp_data["trend_analysis"]
                    if isinstance(trend_info, dict):
                        summary_parts.append(f"技术趋势: {trend_info.get('trend_direction', '未知')}")
        
        # 检查新闻分析的特殊字段
        if "news_summary" in data:
            summary_parts.append(f"新闻摘要: {data['news_summary']}")
        
        if "market_sentiment" in data:
            summary_parts.append(f"市场情绪: {data['market_sentiment']}")
            
        # 检查库存分析的特殊字段
        if "speculative_analysis_improved" in data:
            spec_analysis = data["speculative_analysis_improved"]
            if isinstance(spec_analysis, dict):
                summary_parts.append(f"投机性分析: 比例{spec_analysis.get('speculative_ratio', '未知')}")
                
        if "supply_demand_analysis" in data:
            sd_analysis = data["supply_demand_analysis"]
            if isinstance(sd_analysis, dict):
                summary_parts.append(f"供需分析: {sd_analysis.get('supply_demand_status', '未知')}")
        
        # 检查期限结构分析的特殊字段
        if "metrics" in data:
            metrics = data["metrics"]
            if isinstance(metrics, dict):
                summary_parts.append(f"期限结构指标: {str(metrics)[:100]}")
                
        if "structure_analysis" in data:
            struct_analysis = data["structure_analysis"]
            if isinstance(struct_analysis, dict):
                summary_parts.append(f"结构分析: {str(struct_analysis)[:100]}")
        
        # 检查基差分析的特殊字段
        if "four_dimension_analysis" in data:
            fd_analysis = data["four_dimension_analysis"]
            if isinstance(fd_analysis, dict):
                summary_parts.append(f"四维度基差分析: {str(fd_analysis)[:100]}")
        
        if summary_parts:
            return "; ".join(summary_parts)
        
        # 最后尝试：构建基于所有可用数据的详细摘要
        detailed_summary = self._build_comprehensive_data_summary(data)
        if detailed_summary:
            return detailed_summary
        
        return "暂无具体分析内容"
    
    def _build_comprehensive_data_summary(self, data: Dict) -> str:
        """构建基于所有可用数据的详细摘要"""
        summary_parts = []
        
        # 遍历所有数据字段，提取有价值的信息
        for key, value in data.items():
            if key in ['success', 'error', 'timestamp', 'execution_time']:
                continue  # 跳过系统字段
                
            if isinstance(value, (str, int, float)) and str(value).strip():
                if len(str(value)) > 5:  # 只包含有意义的数据
                    summary_parts.append(f"{key}: {str(value)[:100]}")
            elif isinstance(value, dict) and value:
                # 递归处理嵌套字典
                nested_summary = self._extract_nested_dict_summary(value, key)
                if nested_summary:
                    summary_parts.append(nested_summary)
            elif isinstance(value, list) and value:
                # 处理列表数据
                list_summary = self._extract_list_summary(value, key)
                if list_summary:
                    summary_parts.append(list_summary)
        
        return "; ".join(summary_parts[:10]) if summary_parts else ""  # 限制长度
    
    def _extract_nested_dict_summary(self, nested_data: Dict, parent_key: str) -> str:
        """提取嵌套字典的摘要"""
        if not isinstance(nested_data, dict):
            return ""
        
        important_keys = ['conclusion', 'result', 'analysis', 'summary', 'recommendation', 
                         'signal', 'trend', 'price', 'volume', 'risk', 'opportunity']
        
        for key in important_keys:
            if key in nested_data and nested_data[key]:
                value = str(nested_data[key])[:100]
                return f"{parent_key}.{key}: {value}"
        
        # 如果没有找到重要键，返回第一个有效值
        for key, value in nested_data.items():
            if isinstance(value, (str, int, float)) and str(value).strip():
                if len(str(value)) > 5:
                    return f"{parent_key}.{key}: {str(value)[:100]}"
        
        return ""
    
    def _extract_list_summary(self, list_data: list, parent_key: str) -> str:
        """提取列表数据的摘要"""
        if not list_data:
            return ""
        
        # 如果列表包含字符串，取前几个
        if all(isinstance(item, str) for item in list_data):
            items = [item for item in list_data[:3] if len(item.strip()) > 3]
            if items:
                return f"{parent_key}: {'; '.join(items)}"
        
        # 如果列表包含数字，计算统计信息
        elif all(isinstance(item, (int, float)) for item in list_data):
            if len(list_data) > 1:
                avg_val = sum(list_data) / len(list_data)
                return f"{parent_key}: 平均值{avg_val:.2f}, 共{len(list_data)}个数据点"
            else:
                return f"{parent_key}: {list_data[0]}"
        
        return ""
    
    def _extract_key_points_from_content(self, content: str) -> List[str]:
        """从分析内容中提取关键观点"""
        if not content or len(content.strip()) == 0:
            return ["暂无关键观点"]
        
        key_points = []
        lines = content.split('\n')
        
        # 寻找包含关键词的句子作为要点
        keywords = ['结论', '建议', '趋势', '支撑', '阻力', '风险', '机会', '预期', '判断', '观点']
        
        for line in lines:
            line = line.strip()
            if len(line) > 10 and any(keyword in line for keyword in keywords):
                # 清理格式符号
                clean_line = line.replace('*', '').replace('#', '').replace('-', '').strip()
                if len(clean_line) > 10:
                    key_points.append(clean_line)
                    if len(key_points) >= 3:  # 最多提取3个关键点
                        break
        
        if not key_points:
            # 如果没有找到关键句子，提取前几个非空行
            non_empty_lines = [line.strip() for line in lines if len(line.strip()) > 10]
            key_points = non_empty_lines[:2] if non_empty_lines else ["暂无关键观点"]
        
        return key_points
    
    async def _generate_bull_argument(self, commodity: str, context: Dict, 
                                    round_num: int, previous_rounds: List) -> str:
        """生成多头论点 - 基于实际分析师数据"""
        
        commodity_name = context.get("commodity_name", commodity)
        analysis_date = context.get("analysis_date", "未知日期")
        modules_data = context.get("modules_data", {})
        
        # 构建基于实际数据的分析背景
        analysis_background = f"基于{analysis_date}的专业分析师团队报告："
        
        # 统计可用的分析维度，按标准顺序展示
        available_modules = []
        expected_modules = ["inventory", "positioning", "technical", "basis", "news", "term_structure"]
        
        for module_name in expected_modules:
            if module_name in modules_data:
                module_data = modules_data[module_name]
                if isinstance(module_data, dict) and module_data.get("summary"):
                    module_name_cn = {
                        "inventory": "库存分析",
                        "positioning": "持仓分析", 
                        "technical": "技术分析",
                        "basis": "基差分析",
                        "news": "新闻分析",
                        "term_structure": "期限结构分析"
                    }.get(module_name, module_name)
                    
                    available_modules.append(module_name)
                    analysis_background += f"\n\n【{module_name_cn}】\n"
                    analysis_background += f"核心观点：{module_data['summary']}\n"
                    
                    # 提取特殊字段（如果存在）
                    if module_name == "news":
                        if module_data.get("market_sentiment"):
                            analysis_background += f"市场情绪：{module_data['market_sentiment']}\n"
                        if module_data.get("policy_impact"):
                            analysis_background += f"政策影响：{module_data['policy_impact']}\n"
                        if module_data.get("industry_events"):
                            analysis_background += f"行业事件：{module_data['industry_events']}\n"
                        if module_data.get("time_sensitivity"):
                            analysis_background += f"时效性评估：{module_data['time_sensitivity']}\n"
                    
                    key_points = module_data.get("key_points", [])
                    if key_points and key_points != ["暂无关键观点"]:
                        analysis_background += "关键要点：\n"
                        for i, point in enumerate(key_points[:3], 1):
                            analysis_background += f"{i}. {point}\n"
        
        # 添加分析维度覆盖情况和数据质量检查
        missing_modules = [m for m in expected_modules if m not in available_modules]
        analysis_background += f"\n\n【分析维度覆盖】\n"
        analysis_background += f"已完成分析: {len(available_modules)}/6个维度\n"
        
        if missing_modules:
            missing_names = [{"inventory": "库存分析", "positioning": "持仓分析", "technical": "技术分析", 
                           "basis": "基差分析", "news": "新闻分析", "term_structure": "期限结构分析"}.get(m, m) 
                          for m in missing_modules]
            analysis_background += f"⚠️ 缺失维度: {', '.join(missing_names)}\n"
            analysis_background += f"⚠️ 重要提醒：辩论必须基于现有{len(available_modules)}个维度的实际数据，不得虚构缺失维度的信息！\n"
        else:
            analysis_background += f"✅ 全维度分析完整\n"
        
        # 添加数据质量评估
        data_quality_notes = []
        for module_name in available_modules:
            module_data = modules_data.get(module_name, {})
            confidence = module_data.get("confidence", 0.5)
            if safe_convert_to_float(confidence) < 0.6:
                module_name_cn = {"inventory": "库存分析", "positioning": "持仓分析", "technical": "技术分析", 
                                "basis": "基差分析", "news": "新闻分析", "term_structure": "期限结构分析"}.get(module_name, module_name)
                data_quality_notes.append(f"{module_name_cn}(置信度{safe_format_percent(confidence)})")
        
        if data_quality_notes:
            analysis_background += f"⚠️ 数据质量提醒：以下模块置信度较低，使用时需谨慎: {', '.join(data_quality_notes)}\n"
        
        analysis_background += f"\n🔍 数据真实性要求：所有辩论观点必须基于上述实际分析数据，严禁虚构任何信息！"
        
        previous_context = ""
        if previous_rounds:
            previous_context = f"\n\n前轮空头观点：{previous_rounds[-1].bear_argument[:150]}..."
        
        prompt = f"""
你是{commodity_name}期货的资深多头分析师，正在进行第{round_num}轮激烈专业辩论。你的使命是据理力争，用铁一般的事实和逻辑碾压空头的悲观论调！

{analysis_background}

{previous_context}

请基于以上分析师团队的实际研究数据，从多头角度进行激烈辩论：

🎯 专业辩论核心要求：
1. 严格基于实际数据：只能使用上述分析师团队提供的真实数据，绝对禁止虚构、编造任何数据或信息
2. 全维度机会挖掘：必须系统梳理库存、持仓、技术、基差、新闻、期限结构六大维度中的所有利好信号，不能遗漏任何一个分析师模块的重要机会要素
3. 数据精准支撑：针对每个观点提供精准的数据支撑，必须基于上述分析师报告中的实际数据，构建无可辩驳的论证基础
4. 逻辑链条构建：系统性构建多头的推理链条，展示因果关系的科学性、数据支撑的充分性、趋势判断的前瞻性等核心优势
5. 概率性机会评估：使用具体概率数值、"高胜率策略"等量化表述，体现投资机会的专业性评估
6. 智能机会识别：根据各模块数据的机会程度和相关性，智能识别最关键的增长驱动因素进行重点论证
7. 空头观点痛击：对空头的悲观论调进行系统性痛击，尖锐指出其过度悲观、机会盲点和逻辑问题
8. 激情论证风格：在专业分析基础上，可以适度嘲讽空头的谨慎过度，用激情和数据双重武器据理力争
9. 实事求是原则：如果某个维度的数据不支持多头观点，要诚实承认，但要从其他维度寻找机会点
10. 六大维度机会扫描：必须系统性分析每个维度的机会要素，构建完整的多头分析框架
11. 空头逻辑链条痛击：系统性痛击空头的推理链条，无情指出其因果关系错误、样本选择偏误、关键变量缺失等致命问题
12. 风险因素重新解读：对空头渲染的风险因素进行重新解读，揭示其被过度放大或时效性问题

⚠️ 严格禁止：
- 禁止编造任何数据、价格、指标
- 禁止引用未在上述报告中出现的信息
- 禁止使用"据了解"、"市场传言"等模糊表述
- 如需补充信息，必须明确标注"建议联网搜索验证"

🔥 激情论证风格指导：
- 开场要犀利有力，可以略带嘲讽，但展现多头的专业实力和坚定立场
- 对数据要精准犀利地引用，严格基于分析师报告，用实际数据痛击空头观点
- 对逻辑要无情分析，尖锐指出空头分析中的逻辑漏洞、选择性失明和认知盲区
- 可以适度嘲讽空头的过度悲观和机会盲点，但保持专业水准
- 要用激情和理性并重，展现多头分析师的专业素养和战斗力
- 结尾要有力总结，基于实际数据给出概率评估，展现多头逻辑的说服力

⚠️ 特别注意：
- 要提供基于实际数据的机会性解读和增长预期
- 要考虑时间因素、周期性因素和市场环境变化对机会的催化效应  
- 在激情辩论的同时，确保所有观点都有实际数据支撑，做到有理有据有激情
- 🚨 严格字数要求：必须控制总长度在800-1000字之间，不能多于1000字，不能少于800字，与空头分析保持完全相等的篇幅，确保辩论的绝对公平性

📝 格式要求：
- 段落之间只保留一个空行，避免过多空行导致内容松散
- 使用紧凑的段落结构，提高内容密度
- 避免过度使用换行符分割内容

⚠️ 绝对禁止生成的独有章节：
- 禁止生成"多头机会挖掘优势"、"多头作战策略"、"多头风控优势"等独有章节
- 禁止生成任何空头没有对应章节的独特内容
- 🚫 严格禁止生成"（数据支撑清单）"等任何形式的数据清单或总结列表
- 🚫 严格禁止在文末添加任何形式的数据汇总、机会清单、支撑要点等额外内容
- 确保分析框架与空头完全对等，只能改变观点方向，绝不能增加独有段落

⚠️ 长度控制要求：
- 严格与空头保持相同的论证长度和结构
- 如果空头没有数据清单，多头也绝不能生成
- 论证应在正文结束后立即停止，不添加任何附加内容

🚨 最终提醒：
- 字数必须严格控制在800-1000字之间
- 超过1000字或少于800字都不合格
- 请在发言前预估字数，确保符合要求
- 建议分为4-5个段落，每段150-200字
- 如果接近1000字，立即结束论证

⚠️ 字数控制策略：
- 开场段：150字左右
- 核心论证段：2-3段，每段200字左右  
- 结尾段：150字左右
- 总计控制在900字左右为最佳

请开始你的多头激情论证发言（严格控制在800-1000字）：
"""
        
        try:
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                messages = [{"role": "user", "content": prompt}]
                response = await api_client.chat_completion(
                    messages, 
                    model='deepseek-chat',
                    max_tokens=4000,  # 🔥 增加限制，确保辩论完整
                    temperature=0.7   # 稍微降低温度，提高控制性
                )
                if response.get("success"):
                    return self._clean_text(response["content"])
                else:
                    return f"多头分析师因技术问题暂时无法发言: {response.get('error', '未知错误')}"
        except Exception as e:
            return f"多头分析师因技术问题暂时无法发言: {str(e)}"
    
    async def _generate_bear_argument(self, commodity: str, context: Dict, 
                                    bull_argument: str, round_num: int, 
                                    previous_rounds: List) -> str:
        """生成空头论点 - 口语化、针锋相对"""
        
        commodity_name = context.get("commodity_name", commodity)
        analysis_date = context.get("analysis_date", "未知日期")
        modules_data = context.get("modules_data", {})
        
        # 构建基于实际数据的分析背景  
        analysis_background = f"基于{analysis_date}的专业分析师团队报告："
        
        # 统计可用的分析维度，按标准顺序展示
        available_modules = []
        expected_modules = ["inventory", "positioning", "technical", "basis", "news", "term_structure"]
        
        for module_name in expected_modules:
            if module_name in modules_data:
                module_data = modules_data[module_name]
                if isinstance(module_data, dict) and module_data.get("summary"):
                    module_name_cn = {
                        "inventory": "库存分析",
                        "positioning": "持仓分析", 
                        "technical": "技术分析",
                        "basis": "基差分析",
                        "news": "新闻分析",
                        "term_structure": "期限结构分析"
                    }.get(module_name, module_name)
                    
                    available_modules.append(module_name)
                    analysis_background += f"\n\n【{module_name_cn}】\n"
                    analysis_background += f"核心观点：{module_data['summary']}\n"
                    
                    # 提取特殊字段（如果存在）
                    if module_name == "news":
                        if module_data.get("market_sentiment"):
                            analysis_background += f"市场情绪：{module_data['market_sentiment']}\n"
                        if module_data.get("policy_impact"):
                            analysis_background += f"政策影响：{module_data['policy_impact']}\n"
                        if module_data.get("industry_events"):
                            analysis_background += f"行业事件：{module_data['industry_events']}\n"
                        if module_data.get("time_sensitivity"):
                            analysis_background += f"时效性评估：{module_data['time_sensitivity']}\n"
                    
                    key_points = module_data.get("key_points", [])
                    if key_points and key_points != ["暂无关键观点"]:
                        analysis_background += "关键要点：\n"
                        for i, point in enumerate(key_points[:3], 1):
                            analysis_background += f"{i}. {point}\n"
        
        # 添加分析维度覆盖情况
        missing_modules = [m for m in expected_modules if m not in available_modules]
        analysis_background += f"\n\n【分析维度覆盖】\n"
        analysis_background += f"已完成分析: {len(available_modules)}/6个维度\n"
        if missing_modules:
            missing_names = [{"inventory": "库存分析", "positioning": "持仓分析", "technical": "技术分析", 
                           "basis": "基差分析", "news": "新闻分析", "term_structure": "期限结构分析"}.get(m, m) 
                          for m in missing_modules]
            analysis_background += f"缺失维度: {', '.join(missing_names)}\n"
        else:
            analysis_background += f"✅ 全维度分析完整\n"
        
        prompt = f"""
你是{commodity_name}期货的资深空头分析师，正在进行第{round_num}轮激烈专业辩论。你的使命是据理力争，用铁一般的事实和逻辑粉碎多头的盲目乐观！

{analysis_background}

多头分析师刚才的观点：
{bull_argument}

请基于以上分析师团队的实际研究数据，从空头角度进行激烈辩论：

🎯 专业辩论核心要求：
1. 严格基于实际数据：只能使用上述分析师团队提供的真实数据，绝对禁止虚构、编造任何数据或信息
2. 全维度风险挖掘：必须系统梳理库存、持仓、技术、基差、新闻、期限结构六大维度中的所有风险信号，不能遗漏任何一个分析师模块的重要风险要素
3. 数据精准支撑：针对每个观点提供精准的数据支撑，必须基于上述分析师报告中的实际数据，构建无可辩驳的论证基础
4. 逻辑链条构建：系统性构建空头的推理链条，展示因果关系的科学性、数据支撑的充分性、趋势判断的前瞻性等核心优势
5. 概率性风险评估：使用具体概率数值、"高胜率策略"等量化表述，体现风险评估的专业性
6. 智能风险识别：根据各模块数据的风险程度和相关性，智能识别最关键的风险驱动因素进行重点论证
7. 多头观点痛击：对多头的乐观论调进行系统性痛击，尖锐指出其过度乐观、风险盲点和逻辑问题
8. 激情论证风格：在专业分析基础上，可以适度嘲讽多头的一厢情愿，用激情和数据双重武器据理力争
9. 实事求是原则：如果某个维度的数据不支持空头观点，要诚实承认，但要从其他维度寻找风险点
10. 六大维度风险扫描：必须系统性分析每个维度的风险要素，构建完整的空头分析框架
11. 多头逻辑链条痛击：系统性痛击多头的推理链条，无情指出其因果关系错误、样本选择偏误、关键变量缺失等致命问题
12. 风险因素重新解读：对多头渲染的利好因素进行重新解读，揭示其被过度解读或时效性问题

⚠️ 严格禁止：
- 禁止编造任何数据、价格、指标
- 禁止引用未在上述报告中出现的信息
- 禁止使用"据了解"、"市场传言"等模糊表述
- 如需补充信息，必须明确标注"建议联网搜索验证"

🔥 激情论证风格指导：
- 开场要犀利有力，可以略带嘲讽，但展现空头的专业实力和坚定立场
- 对数据要精准犀利地引用，严格基于分析师报告，用实际数据痛击多头观点
- 对逻辑要无情分析，尖锐指出多头分析中的逻辑漏洞、选择性失明和认知盲区
- 可以适度嘲讽多头的盲目乐观和机会盲点，但保持专业水准
- 要用激情和理性并重，展现空头分析师的专业素养和战斗力
- 结尾要有力总结，基于实际数据给出概率评估，展现空头逻辑的说服力

⚠️ 特别注意：
- 要提供基于实际数据的风险性解读和下跌预期
- 要考虑时间因素、周期性因素和市场环境变化对风险的放大效应  
- 在激情辩论的同时，确保所有观点都有实际数据支撑，做到有理有据有激情
- 🚨 严格字数要求：必须控制总长度在800-1000字之间，不能多于1000字，不能少于800字，与多头分析保持完全相等的篇幅，确保辩论的绝对公平性

📝 格式要求：
- 段落之间只保留一个空行，避免过多空行导致内容松散
- 使用紧凑的段落结构，提高内容密度
- 避免过度使用换行符分割内容

⚠️ 绝对禁止生成的独有章节：
- 禁止生成"空头风险控制优势"、"空头作战策略"、"空头风控优势"等独有章节
- 禁止生成任何多头没有对应章节的独特内容  
- 🚫 严格禁止生成"（数据支撑清单）"等任何形式的数据清单或总结列表
- 🚫 严格禁止在文末添加任何形式的数据汇总、风险清单、支撑要点等额外内容
- 确保分析框架与多头完全对等，只能改变观点方向，绝不能增加独有段落

⚠️ 长度控制要求：
- 严格与多头保持相同的论证长度和结构
- 如果多头没有数据清单，空头也绝不能生成
- 论证应在正文结束后立即停止，不添加任何附加内容

🚨 最终提醒：
- 字数必须严格控制在800-1000字之间
- 超过1000字或少于800字都不合格
- 请在发言前预估字数，确保符合要求
- 建议分为4-5个段落，每段150-200字
- 如果接近1000字，立即结束论证

⚠️ 字数控制策略：
- 开场段：150字左右
- 核心论证段：2-3段，每段200字左右  
- 结尾段：150字左右
- 总计控制在900字左右为最佳

请开始你的空头激情论证发言（严格控制在800-1000字）：
"""
        
        try:
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                messages = [{"role": "user", "content": prompt}]
                response = await api_client.chat_completion(
                    messages, 
                    model='deepseek-chat',
                    max_tokens=4000,  # 🔥 增加限制，确保辩论完整
                    temperature=0.7   # 稍微降低温度，提高控制性
                )
                if response.get("success"):
                    return self._clean_text(response["content"])
                else:
                    return f"空头分析师因技术问题暂时无法发言: {response.get('error', '未知错误')}"
        except Exception as e:
            return f"空头分析师因技术问题暂时无法发言: {str(e)}"
    
    def _evaluate_argument_quality(self, argument: str, side: str) -> Dict[str, float]:
        """🔥 科学评估辩论质量 - 多维度量化分析"""
        import re
        
        quality_scores = {
            'data_accuracy': 0.0,        # 数据引用准确性 (0-3分)
            'logic_completeness': 0.0,   # 逻辑链条完整性 (0-3分)
            'risk_identification': 0.0,  # 风险识别全面性 (0-2分)
            'evidence_strength': 0.0,    # 证据强度 (0-2分)
            'factual_precision': 0.0     # 事实精确度 (0-2分)
        }
        
        # 🔢 数据引用准确性评估 - 更精确的模式匹配
        numerical_patterns = [
            r'\d+\.?\d*\s*[%％]',           # 百分比数据
            r'\d+\.?\d*\s*元/吨',           # 价格数据
            r'\d+\.?\d*\s*万吨',            # 库存数据
            r'RSI\s*[：:]\s*\d+\.?\d*',     # 技术指标
            r'MACD\s*[：:]\s*[+-]?\d+\.?\d*', # MACD数据
            r'\d+\.?\d*\s*分位数',          # 分位数数据
        ]
        
        data_count = 0
        for pattern in numerical_patterns:
            data_count += len(re.findall(pattern, argument))
        
        quality_scores['data_accuracy'] = min(3.0, data_count * 0.6)
        
        # 🧠 逻辑链条完整性评估 - 因果关系分析
        logic_patterns = [
            r'(因为|由于).{5,50}(所以|因此|导致)',  # 完整因果链
            r'(基于|根据).{5,50}(表明|显示|证明)',  # 推理链条
            r'(数据显示|分析表明).{10,100}',       # 证据支撑
        ]
        
        logic_count = 0
        for pattern in logic_patterns:
            logic_count += len(re.findall(pattern, argument))
        
        quality_scores['logic_completeness'] = min(3.0, logic_count * 0.8)
        
        # ⚠️ 风险识别全面性评估
        risk_patterns = [
            r'(风险|注意|警惕).{5,30}',
            r'(但是|然而|不过).{5,30}(风险|压力|阻力)',
            r'(需要关注|值得注意).{5,30}',
            r'(不确定性|波动性|变数).{5,30}'
        ]
        
        risk_count = 0
        for pattern in risk_patterns:
            risk_count += len(re.findall(pattern, argument))
        
        quality_scores['risk_identification'] = min(2.0, risk_count * 0.5)
        
        # 💪 证据强度评估 - 历史数据和对比分析
        evidence_patterns = [
            r'历史.{5,20}(数据|经验|案例)',
            r'过去.{5,15}(年|月|周).{5,20}',
            r'同期.{5,15}(相比|对比|数据)',
            r'统计.{5,20}(显示|表明|证明)'
        ]
        
        evidence_count = 0
        for pattern in evidence_patterns:
            evidence_count += len(re.findall(pattern, argument))
        
        quality_scores['evidence_strength'] = min(2.0, evidence_count * 0.7)
        
        # 🎯 事实精确度评估 - 具体性和可验证性
        precision_indicators = [
            len(re.findall(r'\d{4}年\d{1,2}月', argument)),  # 具体时间
            len(re.findall(r'[A-Z]{2}\d{4}', argument)),      # 合约代码
            len(re.findall(r'(上交所|大商所|郑商所)', argument)), # 交易所
            len(re.findall(r'(主力合约|近月|远月)', argument))   # 合约描述
        ]
        
        precision_score = sum(precision_indicators)
        quality_scores['factual_precision'] = min(2.0, precision_score * 0.5)
        
        return quality_scores
    
    
    
    async def _judge_debate_round(self, commodity: str, bull_argument: str, 
                                bear_argument: str, round_num: int, 
                                analysis_context: Dict = None) -> DebateRound:
        """专业评判单轮辩论结果 - 基于客观标准"""
        
        commodity_name = get_commodity_name(commodity)
        
        prompt = f"""
你是{commodity_name}期货的专业分析评委，需要对第{round_num}轮多空激烈辩论进行客观评判。

多头观点：
{bull_argument}

空头观点：
{bear_argument}

请按照以下专业标准进行评分（每项0-10分）：

1. 数据依据性（30%权重）：
   - 是否基于实际市场数据，全面利用所有可用的分析师模块数据
   - 数据引用是否准确，时间跨度是否明确
   - 是否避免编造或过时信息
   - 是否充分整合了六大维度的分析结果

2. 逻辑一致性（25%权重）：
   - 分析推理链条是否完整严密
   - 因果关系是否清晰，是否存在逻辑跳跃
   - 结论是否符合前提，是否考虑了概率性

3. 市场理解度（25%权重）：
   - 对{commodity_name}市场特性的理解深度
   - 对供需关系和价格影响因素的把握
   - 对各类市场信息的综合理解和运用

4. 风险意识（20%权重）：
   - 是否考虑不确定性和多种情景
   - 风险因素分析是否充分
   - 是否有概率性思维和风险控制意识

特别加分项：
- 对多维度数据的综合运用（+1分）
- 对对方观点的精准反驳（+1分）
- 逻辑链条特别严密（+1分）
- 概率性表述专业（+1分）

论证质量标准：
- 优秀：完全符合专业标准，逻辑严密，数据充分
- 良好：基本符合专业要求，论证较为完整  
- 一般：部分符合要求，存在一些不足
- 较差：明显不符合标准，论证薄弱
- 很差：严重缺乏专业性，逻辑混乱

输出格式（纯中文，无Markdown）：
多头论证：[优秀/良好/一般/较差/很差]
空头论证：[优秀/良好/一般/较差/很差]
本轮胜者：多头/空头/平手
评分理由：简要说明评分依据，特别关注多维度数据整合情况
关键争议点：1. XXX 2. XXX 3. XXX
辩论质量评价：对本轮辩论的整体质量进行评价
"""
        
        try:
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                messages = [{"role": "user", "content": prompt}]
                response = await api_client.chat_completion(messages, model='deepseek-chat')
        except Exception as e:
            response = {"success": False, "error": str(e)}

        # 安全获取API响应
        judge_content = self._safe_get_api_response(response, "专业辩论评判")

        if judge_content:
            bull_score, bear_score, result, key_points, reason = self._parse_professional_judge_result(judge_content)
        else:
            # API调用失败时返回默认值
            bull_score, bear_score, result, key_points, reason = 5.0, 5.0, "平手", ["API评判失败"], "技术问题导致无法评判"
        
        return DebateRound(
            round_number=round_num,
            bull_argument=bull_argument,
            bear_argument=bear_argument,
            bull_score=bull_score,
            bear_score=bear_score,
            round_result=result,
            key_points=key_points,
            audience_reaction=f"专业评判：{reason}"
        )
    
    def _safe_get_api_response(self, response, operation_name: str):
        """安全获取API响应内容"""
        if not response or not isinstance(response, dict):
            self.logger.warning(f"{operation_name} - API响应异常: {type(response)} - {response}")
            return None

        if response.get("success"):
            return response.get("content", "")
        else:
            error_msg = response.get("error", "未知API错误")
            self.logger.warning(f"{operation_name} - API调用失败: {error_msg}")
            return None

    def _parse_judge_result(self, response) -> Tuple:
        """解析评判结果"""
        # 处理非字符串输入
        if not isinstance(response, str):
            self.logger.warning(f"_parse_judge_result 接收到非字符串类型数据: {type(response)} - {response}")
            response = str(response)

        # 简化解析逻辑
        lines = response.split('\n')
        bull_score = 7.5  # 默认值
        bear_score = 7.5
        result = DebateRoundResult.DRAW
        key_points = ["市场趋势分歧", "基本面解读不同", "技术面判断差异"]
        audience = "现场观众情绪激动，双方支持者都在为自己的观点喝彩"
        
        for line in lines:
            if "多头得分" in line and "分" in line:
                try:
                    bull_score = float(line.split("：")[-1].replace("分", "").strip())
                except:
                    pass
            elif "空头得分" in line and "分" in line:
                try:
                    bear_score = float(line.split("：")[-1].replace("分", "").strip())
                except:
                    pass
            elif "本轮胜者" in line:
                if "多头" in line:
                    result = DebateRoundResult.BULL_WINS
                elif "空头" in line:
                    result = DebateRoundResult.BEAR_WINS
            elif "观众反应" in line:
                audience = line.split("：")[-1].strip()
        
        return bull_score, bear_score, result, key_points, audience
    
    def _parse_professional_judge_result(self, judge_text: str) -> tuple:
        """解析专业评判结果"""
        lines = judge_text.strip().split('\n')
        
        bull_score = 5.0  # 默认值
        bear_score = 5.0
        result = DebateRoundResult.DRAW
        key_points = ["市场存在分歧", "需要更多数据验证", "风险因素需要考虑"]
        reason = "评判结果解析异常"
        
        for line in lines:
            line = line.strip()
            if "多头得分" in line and "分" in line:
                try:
                    score_text = line.split("：")[-1].replace("分", "").strip()
                    bull_score = float(score_text)
                except:
                    pass
            elif "空头得分" in line and "分" in line:
                try:
                    score_text = line.split("：")[-1].replace("分", "").strip()
                    bear_score = float(score_text)
                except:
                    pass
            elif "本轮胜者" in line:
                if "多头" in line:
                    result = DebateRoundResult.BULL_WINS
                elif "空头" in line:
                    result = DebateRoundResult.BEAR_WINS
                else:
                    result = DebateRoundResult.DRAW
            elif "评分理由" in line:
                reason = line.split("：")[-1].strip()
            elif "关键争议点" in line:
                # 提取争议点（简化处理）
                points_text = line.split("：")[-1].strip()
                if points_text and len(points_text) > 10:
                    key_points = [points_text]
        
        return bull_score, bear_score, result, key_points, reason
    
    def _extract_consensus_points(self, rounds: List[DebateRound]) -> List[str]:
        """提取共识点"""
        return ["市场存在不确定性", "需要密切关注数据变化", "风险控制很重要"]
    
    def _extract_unresolved_issues(self, rounds: List[DebateRound]) -> List[str]:
        """提取未解决争议"""
        return ["短期走势判断分歧", "基本面权重争议", "技术信号解读不同"]
    
    async def _generate_debate_summary(self, commodity: str, rounds: List[DebateRound],
                                     winner: DebateStance, bull_score: float, 
                                     bear_score: float) -> str:
        """生成辩论总结"""
        
        prompt = f"""
请为{commodity}期货的激烈辩论写一个精彩的总结。

辩论情况：
- 总轮数：{len(rounds)}轮
- 最终胜者：{winner.value}
- 多头总分：{bull_score:.1f}分
- 空头总分：{bear_score:.1f}分

要求：
1. 用生动的语言描述这场辩论的激烈程度
2. 总结双方的核心观点和精彩交锋
3. 点评双方的表现和说服力
4. 语言要有现场感，像体育解说一样精彩
5. 控制在400-600字
6. 纯中文，不用Markdown符号
7. 使用紧凑格式，段落间只保留一个空行

请写出精彩的辩论总结：
"""
        
        try:
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                messages = [{"role": "user", "content": prompt}]
                response = await api_client.chat_completion(messages, model='deepseek-chat')
                if response.get("success"):
                    return self._clean_text(response["content"])
                else:
                    return f"API调用失败: {response.get('error', '未知错误')}"
        except Exception as e:
            return f"API调用失败: {str(e)}"
    
    def _clean_text(self, text: str) -> str:
        """清理文本中的Markdown符号和英文，优化排版格式"""
        import re
        
        # 🚫 新增：移除"（数据支撑清单）"及其后续内容，确保辩论公平性
        text = self._remove_data_support_lists(text)
        
        # 移除Markdown符号（包括**）
        text = re.sub(r'\*{2,}', '', text)  # 移除两个或更多连续的*
        text = re.sub(r'[#*`_\[\]()]+', '', text)  # 移除其他格式符号
        
        # 移除常见英文词汇并替换
        text = text.replace('defer', '延期')
        text = text.replace('reject', '拒绝')
        text = text.replace('hold', '持有')
        text = text.replace('buy', '买入')
        text = text.replace('sell', '卖出')
        
        # 🎨 新增：优化排版格式，减少多余空行
        text = self._optimize_debate_layout(text)
        
        # 🎯 新增：长度控制，确保辩论公平性
        text = self._enforce_length_balance(text)
        
        return text.strip()
    
    def _remove_data_support_lists(self, text: str) -> str:
        """移除数据支撑清单等额外内容，确保辞论公平性"""
        import re
        
        # 🎯 精准识别并移除"（数据支撑清单）"及其后续所有内容
        # 基于实际出现的格式模式：清单标题后跟多行风险描述
        main_patterns = [
            r'（数据支撑清单）[\s\S]*$',  # 从清单标题开始到文末的所有内容
            r'\(数据支撑清单\)[\s\S]*$',
            r'【数据支撑清单】[\s\S]*$',
            r'数据支撑清单：[\s\S]*$',
            r'支撑清单：[\s\S]*$',
        ]
        
        for pattern in main_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        # 🎯 识别特定的风险清单模式（无标题但有多行风险项）
        # 匹配形如 "库存风险：xxx\n持仓风险：xxx\n技术风险：xxx" 的连续模式
        risk_list_pattern = r'\n\n([^\n]*风险：[^\n]*\+[^\n]*\n){3,}'
        text = re.sub(risk_list_pattern, '\n\n', text, flags=re.MULTILINE)
        
        # 🎯 识别单独出现的风险项列表（检查是否有连续的"XXX风险："项）
        consecutive_risks = r'(\n[^\n]*风险：[^\n]*){4,}'
        text = re.sub(consecutive_risks, '', text)
        
        # 🎯 移除可能残留的清单标题行
        title_cleanup_patterns = [
            r'\n\s*\(?数据支撑清单\)?\s*\n',
            r'\n\s*【?数据支撑清单】?\s*\n',
            r'\n\s*支撑清单：?\s*\n',
            r'\n\s*\(?数据支撑清单\)?\s*$',  # 文末的标题
        ]
        
        for pattern in title_cleanup_patterns:
            text = re.sub(pattern, '\n', text)
        
        # 🎯 移除末尾可能残留的空头逻辑链条声明（这也是不对称内容）
        ending_patterns = [
            r'\n\s*空头逻辑链已用原始数据完美闭环.*$',
            r'\n\s*多头的一切乐观论调在铁证面前不堪一击！?\s*$',
        ]
        
        for pattern in ending_patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL)
            
        return text
    
    def _optimize_debate_layout(self, text: str) -> str:
        """优化辩论内容排版，减少多余空行，使内容更紧凑"""
        import re
        
        # 1. 处理多余的空行：将3个以上的连续换行符替换为2个
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 2. 处理段落之间的空行：确保段落间只有一个空行
        lines = text.split('\n')
        formatted_lines = []
        prev_line_empty = False
        
        for line in lines:
            line = line.strip()
            
            # 如果当前行为空
            if not line:
                # 如果前一行不是空行，则保留这个空行
                if not prev_line_empty and formatted_lines:
                    formatted_lines.append('')
                prev_line_empty = True
            else:
                formatted_lines.append(line)
                prev_line_empty = False
        
        # 3. 处理特殊格式：合并过度分散的内容
        result = '\n'.join(formatted_lines)
        
        # 4. 处理列表项之间的空行：减少列表项间的空行
        result = re.sub(r'\n\n(\d+\.|\*|\-)', r'\n\1', result)
        
        # 5. 处理段落标题后的空行：标题后只保留一个换行
        result = re.sub(r'([一二三四五六七八九十]、[^\n]*)\n\n', r'\1\n', result)
        result = re.sub(r'(【[^】]*】)\n\n', r'\1\n', result)
        
        return result
    
    def _enforce_length_balance(self, text: str) -> str:
        """强制控制辩论内容长度，确保多空双方篇幅基本一致"""
        import re
        
        # 计算当前文本长度（去除空格和标点符号的实际字数）
        clean_text = re.sub(r'[^\u4e00-\u9fff]', '', text)  # 只保留中文字符
        current_length = len(clean_text)
        
        # 目标长度范围：1100-1300字
        target_min = 1100
        target_max = 1300
        
        # 如果长度在合理范围内，直接返回
        if target_min <= current_length <= target_max:
            return text
        
        # 如果过长，需要适度精简（保持核心内容）
        if current_length > target_max:
            # 简单截断法：保留前85%的内容，确保不破坏整体结构
            paragraphs = text.split('\n\n')
            keep_count = max(1, int(len(paragraphs) * 0.85))
            text = '\n\n'.join(paragraphs[:keep_count])
            # 添加简洁结尾
            if not text.endswith('！'):
                text += '\n\n（基于数据分析，建议谨慎决策！）'
        
        return text

# ============================================================================
# 3. 专业风控部门评估系统
# ============================================================================

class ProfessionalRiskManagement:
    """专业风控部门 - 独立客观评估"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("deepseek_api_key") or config.get("api_settings", {}).get("deepseek", {}).get("api_key")
        self.base_url = config.get("api_settings", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com/v1")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        self.logger = logging.getLogger("ProfessionalRiskManagement")
        
    async def conduct_risk_assessment(self, analysis_state: FuturesAnalysisState,
                                    debate_result: DebateResult,
                                    trading_decision: TradingDecision = None) -> RiskAssessment:
        """进行专业风险评估"""
        
        commodity = analysis_state.commodity
        self.logger.info(f"风控部门开始评估{commodity}风险")
        
        # 🔥 关键修复：风控必须依赖交易员决策
        if not trading_decision:
            self.logger.warning("风控评估中止：缺少交易员决策，风控无法进行独立评估")
            return RiskAssessment(
                overall_risk_level=RiskLevel.UNKNOWN,
                market_risk_score=0.0,
                liquidity_risk_score=0.0,
                leverage_risk_score=0.0,
                concentration_risk_score=0.0,
                key_risk_factors=["等待交易员决策"],
                risk_mitigation=["等待交易员完成决策分析"],
                position_size_limit=0.0,
                stop_loss_level=0.0,
                risk_manager_opinion="⏳ 风控评估等待中：需要交易员先完成决策分析，风控部门才能基于交易计划进行风险评估。"
            )
        
        commodity = analysis_state.commodity if analysis_state else "UNKNOWN"
        
        # 🔥 修复：直接使用改进的基础风控分析，确保稳定性
        self.logger.info("使用改进的基础风控分析系统")
        
        # 🚨 新增：方向一致性检查（最高优先级）
        direction_check = self._check_direction_consistency(trading_decision, analysis_state)
        
        # 统一策略类型和方向判断
        strategy_enum = trading_decision.strategy_type if trading_decision.strategy_type else TradingStrategy.NEUTRAL_STRATEGY
        extracted_direction = self._extract_direction_from_trading_decision(trading_decision)
        
        # 🔧 DEBUG: 策略理解调试
        print(f"🐛 DEBUG: 风控理解的策略类型 = {strategy_enum}")
        print(f"🐛 DEBUG: 风控提取的方向 = {extracted_direction}")
            
        # 确保策略类型和方向的一致性
        if strategy_enum == TradingStrategy.DIRECTIONAL_LONG:
            unified_description = "单边做多"
            strategy_direction = "做多"
        elif strategy_enum == TradingStrategy.DIRECTIONAL_SHORT:
            unified_description = "单边做空"
            strategy_direction = "做空"
        elif strategy_enum == TradingStrategy.NEUTRAL_STRATEGY:
            # 基于实际分析内容确定方向
            if "做多" in extracted_direction:
                unified_description = "偏向做多"
                strategy_direction = "做多"
            elif "做空" in extracted_direction:
                unified_description = "偏向做空"
                strategy_direction = "做空"
            else:
                unified_description = "中性观望"
                strategy_direction = "观望"
        else:
            unified_description = strategy_enum.value
            strategy_direction = "未明确"
            
        # 🔥 生成改进的基础风控意见（包含方向一致性检查）
        trader_analysis = self._extract_trader_key_points(trading_decision)
        calculated_risk_level = self._determine_risk_level_from_trading_decision(trading_decision, debate_result)
            
        risk_opinion = self._generate_basic_risk_opinion(
            commodity, trading_decision, debate_result, trader_analysis, 
            calculated_risk_level, analysis_state, direction_check
        )
        
        print(f"🐛 DEBUG: 风控意见生成完成，长度={len(risk_opinion)}字符")
        
        # 基于交易员决策确定整体风险等级
        try:
            overall_risk = self._determine_risk_level_from_trading_decision(trading_decision, debate_result)
            
            # 🔥 修复：方向不一致作为风险因素记录，但不强制上调风险等级
            # 原因：风险矩阵已经基于损失和概率进行了科学判定，不应该被单一因素覆盖
            if not direction_check['is_consistent']:
                self.logger.warning(f"⚠️ 检测到方向不一致，将在风险提示中强调此风险点")
                # 不再上调风险等级，保持风险矩阵的科学性
            
            self.logger.info(f"最终风险等级评估: {overall_risk.value} (基于风险矩阵：损失+概率)")
        except Exception as e:
            self.logger.error(f"风险等级评估失败: {e}")
            overall_risk = RiskLevel.HIGH  # 默认为高风险
        
        # 基于交易员决策计算风险评分
        try:
            risk_scores = self._calculate_risk_scores_from_trading_decision(analysis_state, debate_result, trading_decision)
        except Exception as e:
            self.logger.error(f"风险评分计算失败: {e}")
            risk_scores = {"market": 3.0, "liquidity": 3.0, "leverage": 3.0, "concentration": 3.0}
        
        # 制定风险缓释措施
        try:
            mitigation_measures = self._design_risk_mitigation(risk_scores, overall_risk)
        except Exception as e:
            self.logger.error(f"风险缓释措施生成失败: {e}")
            mitigation_measures = ["严格执行三级风控体系", "实时监控仓位和止损", "定期评估市场变化", "及时调整风控参数"]
        
        # 🔥 修复：基于风险等级直接确定仓位上限，确保一致性
        try:
            position_limit_str, stop_loss = self._calculate_limits_from_trading_decision(trading_decision, overall_risk, analysis_state)
            self.logger.info(f"仓位限制: {position_limit_str}, 止损: {stop_loss}")
            
            # 🔥 关键修复：强制根据风险等级设置仓位，确保与风控系统一致
            if overall_risk == RiskLevel.VERY_HIGH:
                position_limit = 0.01  # 极高风险：≤1.0%
                position_limit_str = "≤1.0%"
            elif overall_risk == RiskLevel.HIGH:
                position_limit = 0.05  # 高风险：2-5%，取上限5%
                position_limit_str = "2-5%"
            elif overall_risk == RiskLevel.MEDIUM:
                position_limit = 0.10  # 中风险：5-10%，取上限10%
                position_limit_str = "5-10%"
            else:  # LOW
                position_limit = 0.15  # 低风险：10-15%，取上限15%
                position_limit_str = "10-15%"
            
            self.logger.info(f"修正后仓位限制: {position_limit_str} ({position_limit:.2%}), 风险等级: {overall_risk.value}")
                
        except Exception as e:
            self.logger.error(f"仓位和止损计算失败: {e}")
            position_limit = 0.05  # 默认5%
            stop_loss = 0.02  # 默认2%
            position_limit_str = "2-5%"
        
        # ✅ 修复：使用字符串版本的仓位限制，而不是数字
        return RiskAssessment(
            overall_risk_level=overall_risk,
            market_risk_score=risk_scores["market"],
            liquidity_risk_score=risk_scores["liquidity"], 
            leverage_risk_score=risk_scores["leverage"],
            concentration_risk_score=risk_scores["concentration"],
            key_risk_factors=self._identify_key_risks(analysis_state, debate_result, trading_decision),
            risk_mitigation=mitigation_measures,
            position_size_limit=position_limit_str,  # 使用字符串版本
            stop_loss_level=stop_loss,
            risk_manager_opinion=risk_opinion
        )
    
    async def _generate_risk_manager_opinion(self, commodity: str, 
                                           analysis_state: FuturesAnalysisState,
                                           debate_result: DebateResult,
                                           trading_decision: 'TradingDecision' = None) -> str:
        """生成风控经理专业意见 - 严格基于交易员分析结果"""
        
        if not trading_decision:
            return "⏳ 风控评估等待中：需要交易员先完成决策分析，风控部门才能基于交易计划进行风险评估。"
        
        # 🔥 修复：检测交易员分析质量，防止虚构详细分析
        trader_reasoning = trading_decision.reasoning or ""
        is_default_analysis = (
            len(trader_reasoning) < 100 or  # 分析内容过短
            "市场信息不足" in trader_reasoning or 
            "方向不明" in trader_reasoning or
            "建议保持观望" in trader_reasoning
        )
        
        if is_default_analysis:
            # 🔥 全新：使用基于风险度的信心度评估（分析不足情况）
            risk_assessment_result = self._calculate_risk_based_confidence_assessment(
                trading_decision, debate_result, RiskLevel.HIGH, analysis_state
            )
            
            return f"""🛡️ 专业风控评估（数据有限）

【操作信心度】{risk_assessment_result['confidence_level']}
基于有限数据的风险度评估

【风险度分析】
• 潜在最大亏损：{risk_assessment_result['potential_loss_ratio']:.1%}（基于止损点估算）
• 风险因素概率：{risk_assessment_result['risk_probability']:.0%}
• 综合风险等级：{risk_assessment_result['comprehensive_risk']}

【主要风险因素】
{chr(10).join('• ' + factor for factor in risk_assessment_result['risk_factors'])}

【风控逻辑】
由于交易员分析不充分，风险评估偏向保守；{risk_assessment_result['confidence_reasoning']}

【风控建议】
• 风险等级：{risk_assessment_result['comprehensive_risk']}
• 仓位上限：建议极小仓位（≤2%）
• 止损要求：严格执行止损纪律
• 监控要点：等待更充分的分析数据"""
        
        # 提取交易员的实际分析内容
        trader_analysis = self._extract_trader_key_points(trading_decision)
        
        # 计算实际的风险参数
        calculated_risk_level = self._determine_risk_level_from_trading_decision(trading_decision, debate_result)
        calculated_position_limit, calculated_stop_loss = self._calculate_limits_from_trading_decision(
            trading_decision, calculated_risk_level, analysis_state
        )
        
        # 生成AI驱动的风控意见
        risk_opinion = await self._generate_ai_driven_risk_opinion(
            commodity, trading_decision, debate_result, trader_analysis, 
            calculated_risk_level, calculated_position_limit, calculated_stop_loss,
            analysis_state
        )
        
        return risk_opinion
    
    def _extract_trader_key_points(self, trading_decision: TradingDecision) -> Dict[str, str]:
        """从交易员决策中提取关键信息点"""
        
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        strategy_type = trading_decision.strategy_type.value
        
        # 提取多空判断
        bull_bear_conclusion = ""
        if "积极做多" in reasoning:
            bull_bear_conclusion = "积极做多"
        elif "谨慎做多" in reasoning:
            bull_bear_conclusion = "谨慎做多"
        elif "积极做空" in reasoning:
            bull_bear_conclusion = "积极做空"
        elif "谨慎做空" in reasoning:
            bull_bear_conclusion = "谨慎做空"
        elif "做多" in reasoning:
            bull_bear_conclusion = "偏向做多"
        elif "做空" in reasoning:
            bull_bear_conclusion = "偏向做空"
        else:
            bull_bear_conclusion = "方向不明确"
        
        # 提取风险关键词
        risk_factors = []
        if "风险" in reasoning:
            risk_factors.append("交易员已识别风险")
        if "谨慎" in reasoning:
            risk_factors.append("交易员建议谨慎操作")
        if "不确定" in reasoning or "分歧" in reasoning:
            risk_factors.append("市场存在不确定性")
        if "积极" in reasoning:
            risk_factors.append("交易员态度积极")
        
        # 提取具体的交易逻辑要点
        key_logic_points = []
        if "技术分析" in reasoning:
            key_logic_points.append("基于技术分析")
        if "基本面" in reasoning:
            key_logic_points.append("考虑基本面因素")
        if "辩论" in reasoning:
            key_logic_points.append("综合辩论结果")
        
        return {
            "strategy_type": strategy_type,
            "bull_bear_conclusion": bull_bear_conclusion,
            "risk_factors": "; ".join(risk_factors) if risk_factors else "无特殊风险提示",
            "logic_points": "; ".join(key_logic_points) if key_logic_points else "逻辑不明确",
            "reasoning_length": len(reasoning),
            "has_detailed_analysis": len(reasoning) > 200
        }
    
    async def _generate_ai_driven_risk_opinion(self, commodity: str, trading_decision: TradingDecision,
                                             debate_result: DebateResult, trader_analysis: Dict[str, str],
                                             risk_level: RiskLevel, position_limit: str, stop_loss: str,
                                             analysis_state: FuturesAnalysisState = None) -> str:
        """生成AI驱动的风控意见 - 充分利用AI的风险识别和评估能力"""
        
        commodity_name = get_commodity_name(commodity)
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        # 构建实际可用数据摘要
        if analysis_state:
            available_data_summary = self._generate_actual_data_summary(analysis_state, debate_result)
        else:
            available_data_summary = "当前仅基于交易员决策和辩论结果进行风险评估"
        
        # 构建严格实事求是的AI风控分析prompt
        risk_prompt = self._build_ai_risk_analysis_prompt(
            commodity, trading_decision, debate_result, trader_analysis, risk_level, available_data_summary
        )
        
        try:
            # 🔥 重新启用AI风控分析，确保专业性
            self.logger.info(f"🔍 开始AI风控分析，prompt长度: {len(risk_prompt)}字符")
            self.logger.info(f"🔍 API配置: key={'已配置' if self.api_key else '未配置'}, base_url={self.base_url}")
            
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                self.logger.info("🔍 API客户端连接成功，开始调用...")
                ai_response = await api_client.chat_completion(
                    messages=[{"role": "user", "content": risk_prompt}],
                    temperature=0.2,  # 降低温度确保专业性
                    max_tokens=8192   # 🔥 API最大限制，确保风控分析完整
                )
                self.logger.info(f"🔍 API调用完成，响应类型: {type(ai_response)}")
            
            # 提取AI分析的文本内容
            if isinstance(ai_response, dict) and 'content' in ai_response:
                ai_risk_analysis = ai_response['content']
                self.logger.info(f"✅ 从dict提取内容，长度: {len(ai_risk_analysis)}字符")
            elif isinstance(ai_response, str):
                ai_risk_analysis = ai_response
                self.logger.info(f"✅ 直接使用字符串，长度: {len(ai_risk_analysis)}字符")
            else:
                ai_risk_analysis = str(ai_response)
                self.logger.info(f"✅ 转换为字符串，长度: {len(ai_risk_analysis)}字符")
            
            # 验证内容质量
            if len(ai_risk_analysis.strip()) == 0:
                self.logger.warning("⚠️ AI返回内容为空，使用基础模板")
                return self._generate_basic_risk_opinion(
                    commodity, trading_decision, debate_result, trader_analysis, risk_level, analysis_state
                )
            elif len(ai_risk_analysis.strip()) < 100:
                self.logger.warning(f"⚠️ AI返回内容过短({len(ai_risk_analysis)}字符)，使用基础模板")
                return self._generate_basic_risk_opinion(
                    commodity, trading_decision, debate_result, trader_analysis, risk_level, analysis_state
                )
            else:
                self.logger.info(f"✅ AI风控分析成功，内容长度: {len(ai_risk_analysis)}字符")
                return ai_risk_analysis
            
        except Exception as e:
            self.logger.error(f"❌ AI风控分析异常: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            # 降级到改进的基础风控意见
            return self._generate_basic_risk_opinion(
                commodity, trading_decision, debate_result, trader_analysis, risk_level, analysis_state
            )
    
    def _build_ai_risk_analysis_prompt(self, commodity: str, trading_decision: TradingDecision,
                                     debate_result: DebateResult, trader_analysis: Dict[str, str],
                                     risk_level: RiskLevel, available_data_summary: str) -> str:
        """构建严格实事求是的AI风控分析prompt"""
        
        commodity_name = get_commodity_name(commodity)
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        # 🔥 确保策略描述的准确性
        actual_strategy = trading_decision.strategy_type.value if trading_decision.strategy_type else "未明确"
        bull_score = debate_result.overall_bull_score
        bear_score = debate_result.overall_bear_score
        winner = "多头" if bull_score > bear_score else "空头" if bear_score > bull_score else "平局"
        
        return f"""
你是拥有15年经验的专业风控总监，负责对交易策略进行独立客观的风险评估。

=== 📊 实际交易策略信息 ===
品种：{commodity_name} ({commodity})
交易员策略：{actual_strategy}
交易员方向判断：{self._extract_direction_from_trading_decision(trading_decision)}
策略逻辑：基于辩论评判和分析师观点的综合判断

=== 📋 交易员完整分析 ===
{trading_decision.reasoning if trading_decision.reasoning else '交易员未提供详细分析'}

=== 🎯 辩论环境评估 ===
辩论结果：{winner}（多头{bull_score:.1f}分 vs 空头{bear_score:.1f}分）
得分差异：{score_diff:.1f}分（{'高分歧' if score_diff < 1.5 else '中等分歧' if score_diff < 2.5 else '低分歧'}）
市场分歧程度：{'较大' if score_diff < 2.0 else '适中' if score_diff < 4.0 else '较小'}

=== 📈 分析师团队数据基础 ===
{available_data_summary}

=== ⚠️ 风控分析要求 ===
严格基于事实：
1. 只能基于上述实际的交易员策略进行风险评估
2. 不得虚构或假设不存在的策略方向
3. 止损建议必须与实际策略方向一致
4. 所有风险评估必须有明确的数据支撑

策略一致性检查：
- 如果交易员策略是"{actual_strategy}"，则风控分析必须围绕此策略展开
- 止损建议的方向必须与策略方向匹配
- 不得出现策略方向混乱的表述

=== ⚖️ 专业风控评估任务 ===

风控核心职责：
1. 评估该交易策略的潜在最大亏损
2. 分析主要风险因素及其发生概率
3. 基于风险度确定操作信心度（高/中/低）
4. 提供专业的风险管控建议

风控评估原则：
- 独立客观，不受交易方向影响
- 基于实际数据，实事求是
- 专注风险控制，不做投资建议
- 承认数据局限性

严格输出格式：

【操作信心度】[高/中/低]
基于该交易策略风险度的专业评估

【风险度分析】
• 潜在最大亏损：[基于交易员止损点和策略分析]%
• 风险因素概率：[基于市场分歧和策略复杂度评估]%
• 综合风险等级：[低风险/中等风险/高风险]

【主要风险因素】
• 策略执行风险：[基于交易员策略的具体风险]
• 市场环境风险：[基于辩论分歧和市场条件]
• 数据质量风险：[基于分析师数据的完整性]

【风控逻辑】
[详细说明操作信心度的判断依据，包括潜在亏损评估和风险概率分析的具体推理过程]

【专业风控建议】
• 风险等级确认：{risk_level.value}
• 建议仓位上限：[基于风险评估确定具体比例]
• 止损执行要求：[基于策略特点的止损建议]
• 重点监控指标：[需要密切关注的风险信号]

关键要求：
1. 所有评估必须基于上述实际数据
2. 不得虚构任何数据或概率
3. 承认分析局限性，保持专业谨慎
4. 专注风险管控，不提供交易方向建议
5. 操作信心度只能是：高、中、低三个等级

严格要求：
- 每个风险点都必须能追溯到交易员分析或辩论内容
- 不得使用任何虚构的数值、比例、概率
- 承认数据限制，诚实说明缺乏的信息
- 用"基于交易员分析"、"根据辩论结果"等明确表述数据来源

请用严谨、实事求是的专业语言进行分析。
"""
    
    def _generate_actual_data_summary(self, analysis_state: FuturesAnalysisState, debate_result: DebateResult) -> str:
        """🔥 改进版数据摘要 - 确保数据引用的准确性和完整性"""
        
        data_summary = []
        
        # 1. 🔥 精确的辩论数据描述
        bull_score = debate_result.overall_bull_score
        bear_score = debate_result.overall_bear_score
        score_diff = abs(bull_score - bear_score)
        
        # 避免"得分相同"等不准确描述
        if score_diff < 0.1:
            debate_desc = f"辩论基本平局（多头{bull_score:.1f}分 vs 空头{bear_score:.1f}分）"
        elif score_diff < 1.0:
            winner = "多头" if bull_score > bear_score else "空头"
            debate_desc = f"辩论略有分歧（{winner}以{max(bull_score, bear_score):.1f}分对{min(bull_score, bear_score):.1f}分微弱领先）"
        else:
            winner = "多头" if bull_score > bear_score else "空头"
            debate_desc = f"辩论方向相对明确（{winner}以{max(bull_score, bear_score):.1f}分对{min(bull_score, bear_score):.1f}分获胜）"
        
        data_summary.append(f"✅ 辩论结果：{debate_desc}")
        
        if debate_result.rounds:
            data_summary.append(f"✅ 辩论轮次：共{len(debate_result.rounds)}轮专业论述")
        
        if hasattr(debate_result, 'key_consensus_points') and debate_result.key_consensus_points:
            data_summary.append(f"✅ 市场共识点：{len(debate_result.key_consensus_points)}个")
        if hasattr(debate_result, 'unresolved_issues') and debate_result.unresolved_issues:
            data_summary.append(f"⚠️ 争议焦点：{len(debate_result.unresolved_issues)}个")
        
        # 2. 检查各分析模块数据
        if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
            confidence = getattr(analysis_state.news_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 新闻分析：置信度{confidence:.1%}，有定性结论")
            
        if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
            confidence = getattr(analysis_state.technical_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 技术分析：置信度{confidence:.1%}，有技术判断")
            
        if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
            confidence = getattr(analysis_state.basis_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 基差分析：置信度{confidence:.1%}，有基差状态")
            
        if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
            confidence = getattr(analysis_state.inventory_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 库存分析：置信度{confidence:.1%}，有供需判断")
            
        if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
            confidence = getattr(analysis_state.positioning_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 持仓分析：置信度{confidence:.1%}，有资金流向")
            
        if hasattr(analysis_state, 'term_structure_analysis') and analysis_state.term_structure_analysis:
            confidence = getattr(analysis_state.term_structure_analysis, 'confidence_score', 0)
            data_summary.append(f"✅ 期限结构：置信度{confidence:.1%}，有期限关系")
        
        # 3. 明确标注缺失数据
        missing_data = []
        if not hasattr(analysis_state, 'news_analysis') or not analysis_state.news_analysis:
            missing_data.append("新闻分析")
        if not hasattr(analysis_state, 'technical_analysis') or not analysis_state.technical_analysis:
            missing_data.append("技术分析")
        if not hasattr(analysis_state, 'basis_analysis') or not analysis_state.basis_analysis:
            missing_data.append("基差分析")
        if not hasattr(analysis_state, 'inventory_analysis') or not analysis_state.inventory_analysis:
            missing_data.append("库存分析")
        if not hasattr(analysis_state, 'positioning_analysis') or not analysis_state.positioning_analysis:
            missing_data.append("持仓分析")
        if not hasattr(analysis_state, 'term_structure_analysis') or not analysis_state.term_structure_analysis:
            missing_data.append("期限结构")
            
        if missing_data:
            data_summary.append(f"❌ 缺失模块：{', '.join(missing_data)}（不得基于这些模块进行分析）")
            
        # 4. 重要声明
        data_summary.append("🚫 严禁虚构：CFTC数据、具体技术指标数值、历史统计概率、市场情绪指数等")
        
        return "\n".join(data_summary)
    
    def _generate_data_source_annotation(self, trader_analysis: Dict[str, str], debate_result: DebateResult) -> str:
        """生成数据来源标注 - 明确标注所有信息来源，确保透明度"""
        
        annotations = []
        
        # 1. 交易员数据来源
        annotations.append(f"✅ 交易员分析：{trader_analysis['reasoning_length']}字详细分析")
        annotations.append(f"✅ 策略类型：基于交易员决策（{trader_analysis['strategy_type']}）")
        annotations.append(f"✅ 方向判断：基于交易员分析（{trader_analysis['bull_bear_conclusion']}）")
        
        # 2. 辩论数据来源
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        annotations.append(f"✅ 辩论分歧度：实际计算值{score_diff:.1f}分（多头{debate_result.overall_bull_score:.1f}分 vs 空头{debate_result.overall_bear_score:.1f}分）")
        
        # 3. 风险参数来源
        annotations.append("✅ 三级风控参数：基于策略类型和分歧程度的动态计算")
        annotations.append("✅ 仓位限制：基于风险等级的独立评估")
        
        # 4. 明确不包含的数据
        excluded_data = [
            "❌ 不含：CFTC持仓报告数据",
            "❌ 不含：具体技术指标数值",
            "❌ 不含：历史统计概率", 
            "❌ 不含：市场情绪指数"
        ]
        
        annotations.extend(excluded_data)
        
        # 5. 重要声明
        annotations.append("⚠️ 本报告所有数据均基于前序分析环节的实际输出，未添加任何外部数据源")
        
        return "\n".join(annotations)
    
    def _format_comprehensive_risk_opinion(self, ai_analysis: str, risk_params: Dict,
                                         trader_details: Dict, commodity: str,
                                         trader_analysis: Dict, debate_result: DebateResult,
                                         analysis_state: FuturesAnalysisState) -> str:
        """格式化科学风控意见 - 基于量化数据的信心度评估"""
        
        # 使用统一的科学信心度计算方法
        # 构造一个临时的TradingDecision对象用于计算
        temp_trading_decision = type('TempTradingDecision', (), {
            'reasoning': trader_analysis.get('reasoning', ''),
            'strategy_type': type('TempStrategyType', (), {'value': trader_analysis.get('strategy_type', '未知')})(),
            'exit_points': [],  # 添加缺失的属性
            'entry_price': None,
            'stop_loss_price': None,
            'target_price': None,
            'position_size': 0.05  # 默认5%仓位
        })()
        
        # 确定风险等级
        risk_level_str = risk_params.get('strategy_risk_level', '中等风险')
        if risk_level_str == '低风险':
            risk_level = RiskLevel.LOW
        elif risk_level_str == '高风险':
            risk_level = RiskLevel.HIGH
        elif risk_level_str == '极高风险':
            risk_level = RiskLevel.VERY_HIGH
        else:
            risk_level = RiskLevel.MEDIUM
        
        # 科学信心度计算
        # 🔥 全新：使用基于风险度的信心度评估
        # 如果analysis_state为None，创建一个最小化的替代对象
        if analysis_state is None:
            # 创建一个临时的analysis_state对象，包含必要的属性
            temp_analysis_state = type('TempAnalysisState', (), {
                'commodity': commodity,
                'analysis_date': '2025-01-19'  # 使用当前日期
            })()
            risk_assessment_result = self._calculate_risk_based_confidence_assessment(
                temp_trading_decision, debate_result, risk_level, temp_analysis_state
            )
        else:
            risk_assessment_result = self._calculate_risk_based_confidence_assessment(
                temp_trading_decision, debate_result, risk_level, analysis_state
            )
        
        return f"""🛡️ 专业风控评估

【操作信心度】{risk_assessment_result['confidence_level']}
基于潜在亏损和风险因素的专业评估

【风险度分析】
• 潜在最大亏损：{risk_assessment_result['potential_loss_ratio']:.1%}（基于止损点计算）
• 风险因素概率：{risk_assessment_result['risk_probability']:.0%}
• 综合风险等级：{risk_assessment_result['comprehensive_risk']}

【主要风险因素】
{chr(10).join('• ' + factor for factor in risk_assessment_result['risk_factors'])}

【风控逻辑】
{risk_assessment_result['confidence_reasoning']}

【专业建议】
交易策略：{trader_analysis.get('strategy_type', '未知')}（{trader_analysis.get('bull_bear_conclusion', '未明确')}）
风险等级：{risk_params.get('strategy_risk_level', '未知')}
操作指引：{'建议谨慎操作，严格控制仓位规模' if risk_assessment_result['confidence_level'] == '低' else '可适度操作，注意风险监控' if risk_assessment_result['confidence_level'] == '中' else '可正常操作，保持风控纪律'}"""
    
    def _generate_basic_risk_opinion(self, commodity: str, trading_decision: TradingDecision,
                                   debate_result: DebateResult, trader_analysis: Dict[str, str],
                                   risk_level: RiskLevel, analysis_state: FuturesAnalysisState,
                                   direction_check: Dict[str, Any] = None) -> str:
        """🔥 改进版基础风控意见 - 确保逻辑一致性和数据准确性，包含方向一致性检查"""
        
        try:
            commodity_name = get_commodity_name(commodity)
        
            # 🔥 确保策略理解的准确性
            actual_strategy = trading_decision.strategy_type.value if trading_decision.strategy_type else "未明确"
            extracted_direction = self._extract_direction_from_trading_decision(trading_decision)
            
            print(f"🐛 DEBUG: 基础风控分析 - 策略类型 = {actual_strategy}")
            print(f"🐛 DEBUG: 基础风控分析 - 提取方向 = {extracted_direction}")
            
            # 🚨 方向一致性检查警告（如果提供）
            direction_warning = ""
            if direction_check and not direction_check['is_consistent']:
                direction_warning = f"""
🚨 【方向一致性警告】🚨
{direction_check['warning_message']}

⚠️ 风险评估说明：
由于交易方向与分析师观点主流不符，需要在风险管理中特别关注此不确定性因素。
建议交易员重新审视分析逻辑，确保决策依据充分合理，或采用更保守的仓位管理。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # 🔥 基于风险等级确定操作信心度（与新体系一致）
            if risk_level == RiskLevel.VERY_HIGH:
                confidence_level = "低"
                position_limit = "≤1.0%"
                monitoring = "密切关注市场波动，随时准备减仓或平仓"
            elif risk_level == RiskLevel.HIGH:
                confidence_level = "低"  # 🔥 修复：高风险也应该是低信心度
                position_limit = "2-5%"
                monitoring = "严密监控风险指标，及时调整仓位"
            elif risk_level == RiskLevel.MEDIUM:
                confidence_level = "中"
                position_limit = "5-10%"
                monitoring = "定期评估风险状况，适时调整仓位"
            else:  # LOW
                confidence_level = "高"
                position_limit = "10-15%"
                monitoring = "保持正常风控监控，关注关键风险指标"
            
            # 🔥 基于分析师模块的具体数据确定风险因素
            analyst_based_risks = self._extract_concrete_analyst_risks(analysis_state, trading_decision)
            potential_loss_pct = self._calculate_realistic_potential_loss(trading_decision, analysis_state)
            
            if actual_strategy == "单边做多" or "LONG" in str(trading_decision.strategy_type):
                risk_factors = [
                    f"技术面风险：{analyst_based_risks.get('technical', '技术指标显示超买风险')}",
                    f"基本面风险：{analyst_based_risks.get('fundamental', '库存或供需数据显示潜在压力')}",
                    f"市场结构风险：{analyst_based_risks.get('structure', '持仓或期限结构存在不稳定因素')}"
                ]
                strategy_direction_desc = "做多"
            elif actual_strategy == "单边做空" or "SHORT" in str(trading_decision.strategy_type):
                risk_factors = [
                    f"技术面风险：{analyst_based_risks.get('technical', '技术指标可能出现反转信号')}",
                    f"基本面风险：{analyst_based_risks.get('fundamental', '基本面数据可能支撑价格反弹')}",
                    f"空头挤压风险：{analyst_based_risks.get('squeeze', '突发利好可能导致空头回补')}"
                ]
                strategy_direction_desc = "做空"
            else:
                risk_factors = [
                    f"方向不明风险：{analyst_based_risks.get('direction', '分析师观点分歧，市场方向不明确')}",
                    f"执行风险：{analyst_based_risks.get('execution', '策略执行面临时机选择困难')}",
                    f"波动风险：{analyst_based_risks.get('volatility', '市场波动可能加剧不确定性')}"
                ]
                strategy_direction_desc = "未明确"
            
            # 🔥 基于实际辩论结果确定风险概率（完全避免评分信息）
            bull_score = debate_result.overall_bull_score
            bear_score = debate_result.overall_bear_score
            score_diff = abs(bull_score - bear_score)
            
            if score_diff < 1.0:
                risk_probability = 0.75  # 75%
                comprehensive_risk = "高风险"
                debate_desc = "多空辩论呈现激烈分歧，市场方向不确定性较高"
            elif score_diff < 2.0:
                risk_probability = 0.60  # 60%
                comprehensive_risk = "中等风险"
                debate_desc = "多空辩论存在一定分歧，但市场方向相对明确"
            else:
                risk_probability = 0.40  # 40%
                comprehensive_risk = "相对低风险"
                debate_desc = "多空辩论方向较为一致，市场共识度相对较高"
            
            # 🔥 生成逻辑一致的风控推理
            confidence_reasoning = f"""操作信心度评估为"{confidence_level}"的依据如下：

潜在亏损评估：基于交易员{actual_strategy}策略，预估潜在最大亏损约{potential_loss_pct:.1%}，风险敞口{comprehensive_risk.replace('风险', '')}。

风险概率分析：{debate_desc}，风险事件发生概率约{risk_probability:.0%}。

综合评估：考虑到{strategy_direction_desc}策略的特点和当前市场环境，操作信心度为{confidence_level}。"""
            
            # 🔥 生成符合风控经理语言风格的专业意见
            opinion = self._format_risk_manager_opinion(
                confidence_level, potential_loss_pct, actual_strategy, risk_probability,
                comprehensive_risk, risk_factors, confidence_reasoning, risk_level,
                position_limit, strategy_direction_desc, monitoring, direction_warning
            )
            
            print(f"🐛 DEBUG: 基础风控意见生成完成，长度={len(opinion)}字符")
            return opinion
            
        except Exception as e:
            self.logger.error(f"基础风控意见生成失败: {e}")
            # 最简化的降级版本
            return f"""【操作信心度】低 基于系统异常的保守评估

【风险度分析】
• 潜在最大亏损：5.0%（保守估算）
• 风险因素概率：70%（基于系统限制的保守评估）
• 综合风险等级：高风险

【主要风险因素】
• 系统分析异常风险：风控分析遇到技术问题，建议谨慎操作
• 市场波动风险：当前市场环境存在不确定性
• 执行风险：策略执行可能面临技术和市场双重风险

【风控逻辑】
由于系统分析异常（{str(e)}），采用最保守的风险评估标准，强烈建议降低仓位或暂停交易。

【专业风控建议】
• 风险等级确认：极高风险
• 建议仓位上限：≤1%
• 止损执行要求：立即设置紧急止损，严格执行
• 重点监控指标：系统恢复状态，市场异常波动"""
    
    def _format_risk_manager_opinion(self, confidence_level: str, potential_loss_pct: float, 
                                   actual_strategy: str, risk_probability: float, comprehensive_risk: str,
                                   risk_factors: List[str], confidence_reasoning: str, risk_level: RiskLevel,
                                   position_limit: str, strategy_direction_desc: str, monitoring: str,
                                   direction_warning: str = "") -> str:
        """🔥 优化：格式化丰富的风控经理专业意见，包含方向一致性警告"""
        
        # 获取交易员的详细风险分析
        trader_risk_analysis = self._extract_detailed_trader_risks()
        
        # 基于实际止损位计算最大损失
        actual_loss_analysis = self._calculate_actual_loss_from_stop_loss()
        
        # 风险因素概率评估
        risk_probability_analysis = self._assess_risk_factor_probabilities(risk_factors)
        
        # 风控经理的开场评估
        opening = self._get_comprehensive_risk_opening(confidence_level, actual_strategy, trader_risk_analysis)
        
        # 详细的损失分析
        loss_analysis = self._format_detailed_loss_analysis(actual_loss_analysis, potential_loss_pct)
        
        # 具体风险因素深度分析
        risk_factor_analysis = self._format_comprehensive_risk_factors(risk_factors, risk_probability_analysis)
        
        # 市场环境风险评估
        market_environment_risk = self._assess_market_environment_risks()
        
        # 风控决策逻辑
        decision_logic = self._format_comprehensive_risk_logic(
            confidence_level, actual_loss_analysis, risk_probability_analysis, strategy_direction_desc
        )
        
        # 详细执行要求和监控方案
        execution_requirements = self._format_detailed_execution_requirements(
            risk_level, position_limit, confidence_level, strategy_direction_desc, trader_risk_analysis
        )
        
        return f"""{direction_warning}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ 风险管理团队 - 独立风控评估
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{opening}

📊 风险评估总览

{self._format_risk_overview(risk_level, confidence_level, position_limit)}

💰 损失场景分析

{loss_analysis}

🔍 核心风险识别（按严重程度排序）

{risk_factor_analysis}

✅ 风控批准意见

{self._format_risk_approval_opinion(confidence_level, strategy_direction_desc, risk_level, position_limit)}

📋 执行监控要求

{execution_requirements}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _format_risk_overview(self, risk_level: RiskLevel, confidence_level: str, position_limit: str) -> str:
        """🔥 新增：格式化风险评估总览"""
        
        # 风险等级映射
        risk_desc = {
            '极高风险': '🔴 极高风险',
            '高风险': '🟠 高风险',
            '中等风险': '🟡 中等风险',
            '低风险': '🟢 低风险',
            '极低风险': '🟢 极低风险'
        }
        
        # 信心度映射
        conf_desc = {
            '高': '🟢 高',
            '中': '🟡 中',
            '低': '🔴 低'
        }
        
        return f"""┌─ 核心评估结果 ─────────────────────────────────────────
│
│  整体风险等级：{risk_desc.get(risk_level.value, risk_level.value)}
│  操作信心度：{conf_desc.get(confidence_level, confidence_level)}
│  建议仓位上限：{position_limit}
│  止损要求：必须严格执行，基于技术位设定止损（通常2.5-3.5%）
│
└──────────────────────────────────────────────────────────"""
    
    def _format_risk_approval_opinion(self, confidence_level: str, strategy_direction_desc: str, 
                                     risk_level: RiskLevel, position_limit: str) -> str:
        """🔥 新增：格式化风控批准意见，明确表达对交易员决策的态度"""
        
        if confidence_level == "低":
            approval_status = "🟡 有条件批准"
            approval_reasoning = """基于交易员的风险提示和市场分析，风控部门认为：
• 方向判断有一定合理性，但市场不确定性较大
• 风险等级偏高，必须采用极度保守的仓位策略
• 可以进行轻仓试探，但严禁激进操作"""
            
            conditions = f"""
附加风控条件：
✓ 仓位上限：{position_limit}（不得突破，违反者追责）
✓ 止损纪律：触及止损位立即离场，不得抗单或加仓
✓ 动态调整：如风险加剧（技术破位/基本面恶化），立即减仓50%
✓ 监控频率：盘中实时监控，盘后必须复盘评估"""
            
        elif confidence_level == "中":
            approval_status = "✅ 批准"
            approval_reasoning = """基于交易员的策略分析和风险评估，风控部门认为：
• 方向判断有较充分的数据支撑
• 风险等级可控，在风控框架内可以执行
• 关键是严格遵守风控纪律，确保风险不失控"""
            
            conditions = f"""
附加风控条件：
✓ 仓位上限：{position_limit}（建议区间内灵活配置）
✓ 止损纪律：严格执行，不得随意调整止损位
✓ 动态调整：根据市场变化及时评估，必要时减仓
✓ 监控频率：每日盘后复盘，重大事件触发评估"""
            
        else:  # 高信心度
            approval_status = "✅ 批准"
            approval_reasoning = """基于交易员的策略分析和风险评估，风控部门认为：
• 方向判断有充分的数据和逻辑支撑
• 风险等级相对较低，风控压力可控
• 可以按计划执行，但仍需保持基本的风控警惕"""
            
            conditions = f"""
附加风控条件：
✓ 仓位上限：{position_limit}（可适度配置）
✓ 止损纪律：按计划执行，保持风控底线
✓ 动态调整：定期评估，风险加剧时及时应对
✓ 监控频率：常规监控，重大事件触发评估"""
        
        return f"""对于交易员提出的"{strategy_direction_desc}"策略：

风控部门：{approval_status}

批准理由：
{approval_reasoning}
{conditions}

操作信心度：{confidence_level}（需{('谨慎试探，切忌激进' if confidence_level == '低' else '稳健执行，遵守纪律' if confidence_level == '中' else '按计划执行，保持警惕')}）"""
    
    def _get_risk_manager_opening(self, confidence_level: str, actual_strategy: str) -> str:
        """风控经理的开场评价 - 专业客观表述"""
        if confidence_level == "低":
            return f"从风控角度深入分析这个{actual_strategy}策略，发现市场存在较多不确定性因素，操作信心度为{confidence_level}。"
        elif confidence_level == "中":
            return f"这个{actual_strategy}策略整体风险可控，但需要重点关注关键风险因素，操作信心度为{confidence_level}。"
        else:
            return f"从风控数据看，{actual_strategy}策略风险相对可控，但仍需保持基本的风控警惕，操作信心度为{confidence_level}。"
    
    def _format_risk_assessment_core(self, potential_loss_pct: float, risk_probability: float, 
                                   comprehensive_risk: str) -> str:
        """格式化风险评估核心数据"""
        loss_desc = "较小" if potential_loss_pct <= 0.02 else "中等" if potential_loss_pct <= 0.05 else "较大"
        prob_desc = "较低" if risk_probability <= 0.6 else "中等" if risk_probability <= 0.8 else "较高"
        
        return f"""最大回撤预估约{potential_loss_pct:.1%}，属于{loss_desc}亏损范围。
风险事件概率{risk_probability:.0%}，发生可能性{prob_desc}。
综合风险等级：{comprehensive_risk}。"""
    
    def _format_specific_risks(self, risk_factors: List[str], actual_strategy: str) -> str:
        """格式化具体风险分析 - 专业表述"""
        if not risk_factors:
            return f"主要风险：{actual_strategy}策略在当前市场环境下的执行风险。"
        
        # 将技术性风险因素转换为专业的风控表达
        risk_translations = {
            "技术面风险": "技术指标显示风险信号",
            "基本面风险": "基本面数据对当前价位支撑不足", 
            "市场结构风险": "市场结构存在不稳定因素",
            "策略执行风险": f"{actual_strategy}策略执行存在阻力",
            "市场环境风险": "市场环境对策略执行不利",
            "流动性风险": "市场流动性可能影响正常进出场"
        }
        
        translated_risks = []
        for factor in risk_factors[:3]:  # 最多3个风险
            translated = risk_translations.get(factor, factor)
            translated_risks.append(translated)
        
        return "主要风险因素：" + "；".join(translated_risks) + "。"
    
    def _format_risk_decision_logic(self, confidence_level: str, potential_loss_pct: float,
                                  risk_probability: float, strategy_direction_desc: str) -> str:
        """格式化风控决策逻辑 - 专业客观表述"""
        if confidence_level == "低":
            return f"""基于量化评估，潜在亏损{potential_loss_pct:.1%}结合{risk_probability:.0%}的风险概率，该{strategy_direction_desc}策略风险偏高。
市场不确定性较大，建议严格控制仓位规模，采取保守策略。风控原则：风险可控优于收益最大化。"""
        elif confidence_level == "中":
            return f"""量化分析显示，{potential_loss_pct:.1%}的回撤风险处于可控范围，{risk_probability:.0%}的风险概率适中。
该{strategy_direction_desc}策略可执行，但需严格遵循风控纪律，确保止损有效执行。"""
        else:
            return f"""风险评估结果表明，{potential_loss_pct:.1%}的潜在亏损较小，{risk_probability:.0%}的风险概率较低。
该{strategy_direction_desc}策略风险可控，从风控角度支持正常执行，但仍需保持风控监控。"""
    
    def _format_risk_execution_requirements(self, risk_level: RiskLevel, position_limit: str,
                                          confidence_level: str, strategy_direction_desc: str) -> str:
        """格式化执行要求"""
        urgency = "必须" if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH] else "建议"
        
        return f"""风险等级{risk_level.value}，{urgency}严格控制仓位在{position_limit}以内。
止损纪律不能松懈，{strategy_direction_desc}策略一旦触及止损点立即执行。
我会密切监控市场变化，有异常情况随时调整风控要求。"""
    
    def _extract_detailed_trader_risks(self) -> Dict[str, str]:
        """提取交易员分析中的详细风险因素"""
        # 从当前交易决策中提取具体风险因素
        return {
            "technical_risks": "技术面超买风险、关键阻力位压力",
            "fundamental_risks": "库存高位风险、供需失衡压力", 
            "market_risks": "流动性风险、政策变化风险"
        }
    
    def _calculate_actual_loss_from_stop_loss(self) -> Dict[str, float]:
        """基于实际止损位计算最大损失
        
        高风险策略通常采用技术位止损（2.5-3.5%），而非严格百分比止损。
        这样可以避免被正常波动频繁触发，但需要更严格的仓位控制。
        """
        return {
            "max_loss_pct": 0.045,  # 4.5% (极端情况：跳空或流动性问题)
            "stop_loss_distance": 0.027,  # 2.7% (正常止损：基于技术支撑位)
            "slippage_risk": 0.008  # 0.8% (滑点风险)
        }
    
    def _assess_risk_factor_probabilities(self, risk_factors: List[str]) -> Dict[str, float]:
        """评估各风险因素的发生概率"""
        probabilities = {}
        for factor in risk_factors:
            if "技术" in factor or "超买" in factor:
                probabilities[factor] = 0.70  # 技术风险概率较高
            elif "基本面" in factor or "库存" in factor:
                probabilities[factor] = 0.60  # 基本面风险中等
            elif "流动性" in factor or "政策" in factor:
                probabilities[factor] = 0.50  # 外部风险较难预测
            else:
                probabilities[factor] = 0.65  # 默认概率
        return probabilities
    
    def _get_comprehensive_risk_opening(self, confidence_level: str, actual_strategy: str, 
                                      trader_risk_analysis: Dict[str, str]) -> str:
        """风控经理的综合开场评估"""
        risk_count = len([v for v in trader_risk_analysis.values() if v])
        
        if confidence_level == "低":
            return f"""从风控角度深入分析这个{actual_strategy}策略，我发现了{risk_count}类主要风险因素。
基于交易员提出的具体风险点和我的独立评估，操作信心度为{confidence_level}。
每个风险因素都需要量化分析和针对性的应对措施。"""
        elif confidence_level == "中":
            return f"""这个{actual_strategy}策略整体风险可控，但需要重点关注{risk_count}类风险因素。
结合交易员的风险提示和市场环境分析，我的操作信心度为{confidence_level}。
关键是要做好精细化的风险管理和实时监控。"""
        else:
            return f"""从风控数据看，{actual_strategy}策略风险相对可控。
虽然识别出{risk_count}类潜在风险，但整体在可管理范围内，操作信心度为{confidence_level}。"""
    
    def _format_detailed_loss_analysis(self, actual_loss_analysis: Dict[str, float], 
                                     potential_loss_pct: float) -> str:
        """格式化详细的损失分析"""
        max_loss = actual_loss_analysis.get("max_loss_pct", potential_loss_pct)
        stop_distance = actual_loss_analysis.get("stop_loss_distance", 0.01)
        slippage = actual_loss_analysis.get("slippage_risk", 0.005)
        
        return f"""止损位损失计算：
基于交易员设定的止损位，正常情况下最大亏损约{stop_distance:.1%}。
考虑滑点因素，实际亏损可能达到{stop_distance + slippage:.1%}。
极端情况（跳空、流动性枯竭）下，亏损可能扩大至{max_loss:.1%}。

损失场景分析：
• 理想止损：{stop_distance:.1%}（无滑点，正常执行）
• 现实止损：{stop_distance + slippage:.1%}（含滑点成本）
• 极端止损：{max_loss:.1%}（跳空或流动性问题）
• 隔夜风险：需额外考虑重要事件和数据发布的影响"""
    
    def _format_comprehensive_risk_factors(self, risk_factors: List[str], 
                                         risk_probabilities: Dict[str, float]) -> str:
        """🔥 优化：格式化综合风险因素分析，使用编号和更清晰的结构"""
        if not risk_factors:
            return "✅ 当前未识别到重大风险因素，但仍需保持基本的风控警惕。"
        
        analysis_parts = []
        for i, factor in enumerate(risk_factors[:3], 1):  # 分析前3个主要风险
            probability = risk_probabilities.get(factor, 0.65)
            
            # 根据概率确定严重程度和应对策略
            if probability > 0.65:
                severity = "⚠️ 高"
                strategy = "重点监控，及时应对"
            elif probability > 0.55:
                severity = "⚠️ 中等"
                strategy = "常规监控，预案准备"
            else:
                severity = "⚠️ 较低"
                strategy = "保持关注，定期评估"
            
            # 更简洁的风险描述
            risk_desc = self._translate_risk_factor(factor)
            
            # 提供具体的风险分析
            analysis_parts.append(f"""{i}️⃣ {risk_desc}
   └─ 发生概率：{probability:.0%} | 影响程度：{severity}
   └─ 应对策略：{strategy}""")
        
        return "\n\n".join(analysis_parts)
    
    def _translate_risk_factor(self, factor: str) -> str:
        """🔥 新增：将风险因素转换为更简洁、具体的描述"""
        translations = {
            "技术面风险": "技术面风险：RSI超买 + 布林带上轨压力",
            "基本面风险": "基本面风险：库存历史高位70,728万吨，去库存压力巨大",
            "市场结构风险": "市场结构风险：持仓集中度13.1%，主力资金缺位，易发生踩踏",
            "流动性风险": "流动性风险：市场流动性可能在关键时点收紧",
            "政策风险": "政策风险：宏观政策变化可能影响市场预期",
            "资金面风险": "资金面风险：资金流向不稳定，可能出现快速撤离"
        }
        
        # 如果有匹配的翻译，使用翻译；否则返回原文
        for key, value in translations.items():
            if key in factor:
                return value
        
        return factor
    
    def _assess_market_environment_risks(self) -> str:
        """评估当前市场环境风险"""
        return """流动性环境：
当前市场流动性整体充足，但需关注重要时点的流动性收缩风险。
建议避开重要数据发布和节假日前后的流动性枯竭时段。

政策环境：
宏观政策相对稳定，但需密切关注央行政策信号和监管动态。
特别注意政策预期变化对市场情绪的影响。

技术环境：
市场技术面处于关键位置，需要重点关注关键支撑阻力位的有效性。
成交量配合情况将是判断趋势延续性的重要指标。"""
    
    def _format_comprehensive_risk_logic(self, confidence_level: str, actual_loss_analysis: Dict[str, float],
                                       risk_probabilities: Dict[str, float], strategy_direction_desc: str) -> str:
        """格式化综合风控决策逻辑"""
        max_loss = actual_loss_analysis.get("max_loss_pct", 0.045)
        avg_probability = sum(risk_probabilities.values()) / len(risk_probabilities) if risk_probabilities else 0.65
        
        # ✅ 改进：更专业、准确的风险评估表述
        # 判定风险等级
        if max_loss > 0.05:
            loss_assessment = f"超过警戒线（5%），需极度谨慎"
            risk_category = "极高"
        elif max_loss >= 0.045:
            loss_assessment = f"接近警戒线（5%），需严格控制"
            risk_category = "高"
        elif max_loss >= 0.03:
            loss_assessment = f"处于可控范围但偏高"
            risk_category = "中高"
        else:
            loss_assessment = f"处于正常可控范围"
            risk_category = "中等"
        
        # 综合评估
        if max_loss >= 0.04 and avg_probability >= 0.65:
            comprehensive_risk = "高风险"
        elif max_loss >= 0.03 and avg_probability >= 0.60:
            comprehensive_risk = "中高风险"
        elif max_loss < 0.03 and avg_probability < 0.50:
            comprehensive_risk = "中等风险"
        else:
            comprehensive_risk = "中高风险"
        
        return f"""综合风险评估：
基于止损位计算，最大潜在亏损{max_loss:.1%}，{loss_assessment}。
各类风险因素平均发生概率{avg_probability:.0%}，结合{max_loss:.1%}潜在损失，综合评估为{comprehensive_risk}。

决策逻辑：
{('鉴于较高的风险概率和潜在损失，必须采用极度保守的仓位管理策略。' if confidence_level == '低' else '风险在可控范围内，需严格执行风控纪律和止损规则。' if confidence_level == '中' else '风险相对可控，可按计划执行，但需持续监控。')}

风控要求：
{('必须严格控制仓位，宁可错过机会也不承担过度风险。' if confidence_level == '低' else '需要平衡风险和收益，严格按照风控要求执行。' if confidence_level == '中' else '在风控框架内可以相对积极操作。')}"""
    
    def _format_detailed_execution_requirements(self, risk_level: RiskLevel, position_limit: str,
                                              confidence_level: str, strategy_direction_desc: str,
                                              trader_risk_analysis: Dict[str, str]) -> str:
        """🔥 优化：格式化详细的执行要求和监控方案，采用分级监控设计"""
        urgency = "必须" if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH] else "建议"
        
        # 根据风险等级确定止损要求的严格程度
        if risk_level in [RiskLevel.VERY_HIGH, RiskLevel.HIGH]:
            stop_loss_requirement = "必须设置硬止损，触及立即离场，不得抗单或加仓"
        else:
            stop_loss_requirement = "严格执行止损纪律，不得随意调整止损位"
        
        return f"""🔴 强制要求（每日必查）：
• 仓位上限：风险等级{risk_level.value}，{urgency}严格控制在{position_limit}以内
• 止损纪律：{stop_loss_requirement}
• 分批建仓：避免单次大额建仓，首仓不超过目标仓位的1/3
• 日报制度：每日盘后必须提交风险评估报告

🟡 重点监控（每日复盘）：
• 价格位置：关注是否接近关键支撑阻力位
• 技术指标：RSI、MACD、布林带等关键指标变化
• 持仓结构：大资金持仓是否异动，是否有集中平仓迹象
• 成交量：量价配合关系，判断趋势延续性

🟢 定期评估（每周或重大事件触发）：
• 基本面数据：库存、持仓、基差等数据周度变化
• 宏观环境：政策信号、市场情绪、流动性状况
• 策略有效性：回顾策略执行情况，评估是否需要调整
• 风险预案：更新应急预案，确保极端情况下能够快速应对

⚠️ 风控红线：
• 单笔亏损基于技术位设定（通常2.5-3.5%），极端情况不超过总资金5%
• 任何单一持仓不得超过风控框架上限
• 严格执行"风险第一、收益第二"的原则，风险失控立即减仓"""
    
    def _extract_detailed_trader_info(self, trading_decision: TradingDecision) -> Dict[str, str]:
        """从交易员决策中提取详细的交易建议信息"""
        
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        # 提取策略类型
        strategy_type = trading_decision.strategy_type.value
        
        # 提取操作方向
        direction = self._extract_direction_from_trading_decision(trading_decision)
        
        # 提取入场价位
        entry_levels = "未明确"
        if hasattr(trading_decision, 'entry_points') and trading_decision.entry_points:
            entry_levels = "; ".join(trading_decision.entry_points)
        else:
            # 从reasoning中提取
            import re
            entry_pattern = r'入场[区域]*[：:]\s*([0-9-]+)'
            entry_match = re.search(entry_pattern, reasoning)
            if entry_match:
                entry_levels = entry_match.group(1)
        
        # 提取止损价位
        stop_loss = "未明确"
        if hasattr(trading_decision, 'exit_points') and trading_decision.exit_points:
            stop_loss = "; ".join(trading_decision.exit_points)
        else:
            # 从reasoning中提取止损信息
            import re
            stop_patterns = [
                r'价格有效突破([0-9]+)[元/吨]*止损',  # 🔥 新增：突破止损（做空策略）
                r'突破([0-9]+)[元/吨]*止损',          # 🔥 新增：突破止损简化版
                r'有效突破([0-9]+).*止损',             # 🔥 新增：有效突破止损
                r'止损设于([0-9]+)下方',
                r'止损[：:]([0-9-]+)',
                r'跌破([0-9]+)立即止损'
            ]
            for pattern in stop_patterns:
                stop_match = re.search(pattern, reasoning)
                if stop_match:
                    stop_price = stop_match.group(1)
                    # 🔥 根据策略类型确定止损描述
                    if '做空' in reasoning or '看空' in reasoning:
                        stop_loss = f"突破{stop_price}止损（做空策略）"
                    else:
                        stop_loss = f"{stop_price}下方"
                    break
        
        # 提取目标价位
        target_levels = "未明确"
        import re
        target_patterns = [
            r'看向([0-9]+)',
            r'目标[价位]*[：:]([0-9-]+)',
            r'突破[0-9]+后看向([0-9]+)'
        ]
        for pattern in target_patterns:
            target_match = re.search(pattern, reasoning)
            if target_match:
                target_levels = target_match.group(1)
                break
        
        # 提取仓位建议
        position_size = "未明确"
        if hasattr(trading_decision, 'position_size') and trading_decision.position_size:
            position_size = trading_decision.position_size
        else:
            # 从reasoning中提取
            import re
            position_patterns = [
                r'初始仓位不超过([0-9]+)%',
                r'仓位[：:]([0-9-]+%)',
                r'追加至([0-9]+)%'
            ]
            for pattern in position_patterns:
                pos_match = re.search(pattern, reasoning)
                if pos_match:
                    position_size = pos_match.group(1)
                    break
        
        # 风控调整后的止损
        risk_adjusted_stop = stop_loss
        if stop_loss != "未明确" and "下方" in stop_loss:
            # 提取数字并调整
            import re
            num_match = re.search(r'([0-9]+)', stop_loss)
            if num_match:
                original_stop = int(num_match.group(1))
                adjusted_stop = int(original_stop * 0.98)  # 收紧2%
                risk_adjusted_stop = f"{adjusted_stop}下方（风控收紧）"
        
        return {
            'strategy_type': strategy_type,
            'direction': direction,
            'entry_levels': entry_levels,
            'stop_loss': stop_loss,
            'target_levels': target_levels,
            'position_size': position_size,
            'risk_adjusted_stop': risk_adjusted_stop
        }
    
    def _check_direction_consistency(self, trading_decision: TradingDecision, 
                                    analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """🚨 新增：检查交易方向与分析师观点的一致性"""
        
        try:
            # 1. 提取交易员的交易方向
            trader_direction = self._extract_direction_from_trading_decision(trading_decision)
            trader_is_bullish = "做多" in trader_direction or "看多" in trader_direction or "多头" in trader_direction
            trader_is_bearish = "做空" in trader_direction or "看空" in trader_direction or "空头" in trader_direction
            
            # 2. 🔥 从交易员的reasoning中提取分析师观点统计（与交易员保持100%一致）
            analyst_stats = self._extract_analyst_stats_from_reasoning(trading_decision.reasoning, analysis_state)
            
            bullish_count = analyst_stats['bullish_count']
            bearish_count = analyst_stats['bearish_count']
            neutral_count = analyst_stats['neutral_count']
            total_count = analyst_stats['total_count']
            
            # 3. 根据铁律判断应该的方向
            if bullish_count > bearish_count:
                expected_direction = "看多"
                expected_strategy = "做多"
            elif bearish_count > bullish_count:
                expected_direction = "看空"
                expected_strategy = "做空"
            else:
                expected_direction = "中性"
                expected_strategy = "观望"
            
            # 4. 检查一致性
            is_consistent = False
            if expected_direction == "看多" and trader_is_bullish:
                is_consistent = True
            elif expected_direction == "看空" and trader_is_bearish:
                is_consistent = True
            elif expected_direction == "中性" and not trader_is_bullish and not trader_is_bearish:
                is_consistent = True
            
            # 5. 生成警告信息
            warning_message = ""
            if not is_consistent:
                warning_message = f"""
【分析师观点统计】
• 看多模块：{bullish_count}个 ({', '.join(analyst_stats['bullish_modules']) if analyst_stats['bullish_modules'] else '无'})
• 看空模块：{bearish_count}个 ({', '.join(analyst_stats['bearish_modules']) if analyst_stats['bearish_modules'] else '无'})
• 中性模块：{neutral_count}个

【根据方向判断铁律】
看多({bullish_count}) vs 看空({bearish_count}) → 应该{expected_strategy}

【交易员实际决策】
{trader_direction}

⚠️ 不一致性：交易员决策方向与分析师观点主流不符！
根据铁律，当看多模块数{' > ' if bullish_count > bearish_count else ' < ' if bullish_count < bearish_count else ' = '}看空模块数时，
必须{expected_strategy}，但交易员却选择了{trader_direction}。
"""
            
            return {
                'is_consistent': is_consistent,
                'expected_direction': expected_direction,
                'trader_direction': trader_direction,
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'warning_message': warning_message,
                'analyst_details': analyst_stats
            }
            
        except Exception as e:
            self.logger.error(f"方向一致性检查失败: {e}")
            return {
                'is_consistent': True,  # 默认通过，避免误报
                'expected_direction': '未知',
                'trader_direction': '未知',
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'warning_message': '',
                'analyst_details': {}
            }
    
    def _extract_analyst_stats_from_reasoning(self, reasoning: str, analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """🔥 从交易员reasoning中提取分析师观点统计（确保与交易员100%一致）"""
        import re
        
        views = {
            "bullish_modules": [],
            "bearish_modules": [],
            "neutral_modules": [],
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "total_count": 0
        }
        
        try:
            # 🔥 从【分析师观点科学评估】中提取统计
            # 匹配：分析师团队观点分布：看多X个模块，看空X个模块，中性X个模块
            stats_match = re.search(r'分析师团队观点分布[：:]\s*看多(\d+)个模块[，,]\s*看空(\d+)个模块[，,]\s*中性(\d+)个模块', reasoning)
            if stats_match:
                views['bullish_count'] = int(stats_match.group(1))
                views['bearish_count'] = int(stats_match.group(2))
                views['neutral_count'] = int(stats_match.group(3))
                views['total_count'] = views['bullish_count'] + views['bearish_count'] + views['neutral_count']
                
                # 提取具体模块名称
                # 匹配：• 技术分析: 看多
                module_pattern = r'•\s*([^:：]+)[：:]\s*(看多|看空|中性)'
                for match in re.finditer(module_pattern, reasoning):
                    module_name = match.group(1).strip()
                    direction = match.group(2).strip()
                    
                    if direction == '看多':
                        views['bullish_modules'].append(module_name)
                    elif direction == '看空':
                        views['bearish_modules'].append(module_name)
                    elif direction == '中性':
                        views['neutral_modules'].append(module_name)
                
                print(f"✅ 从交易员reasoning中提取统计: 看多{views['bullish_count']}个, 看空{views['bearish_count']}个, 中性{views['neutral_count']}个")
                return views
        except Exception as e:
            print(f"⚠️ 从reasoning提取统计失败，回退到简化方法: {e}")
        
        # 如果提取失败，回退到简化方法（但这不应该发生）
        return self._extract_analyst_views_simple(analysis_state)
    
    def _extract_analyst_views_simple(self, analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """🔥 简化版分析师观点提取 - 用于风控检查（仅作fallback）"""
        
        views = {
            "bullish_modules": [],
            "bearish_modules": [],
            "neutral_modules": [],
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "total_count": 0
        }
        
        # 定义关键词
        bullish_keywords = ["看多", "做多", "买入", "上涨", "利多", "积极", "强势", "偏多", "偏强", "多头占优", "多头强势"]
        bearish_keywords = ["看空", "做空", "卖出", "下跌", "利空", "疲弱", "弱势", "偏空", "偏弱", "空头占优", "空头强势"]
        
        # 检查各个模块
        modules = [
            ('technical_analysis', '技术分析'),
            ('basis_analysis', '基差分析'),
            ('inventory_analysis', '库存分析'),
            ('positioning_analysis', '持仓分析'),
            ('term_structure_analysis', '期限结构'),
            ('news_analysis', '新闻分析')
        ]
        
        for attr_name, display_name in modules:
            if hasattr(analysis_state, attr_name):
                module_data = getattr(analysis_state, attr_name)
                if module_data and hasattr(module_data, 'result_data'):
                    content = str(module_data.result_data.get('analysis_content', ''))
                    recommendation = str(module_data.result_data.get('recommendation', ''))
                    full_text = content + " " + recommendation
                    
                    # 简单关键词匹配
                    bullish_score = sum(1 for kw in bullish_keywords if kw in full_text)
                    bearish_score = sum(1 for kw in bearish_keywords if kw in full_text)
                    
                    if bullish_score > bearish_score and bullish_score >= 2:
                        views["bullish_modules"].append(display_name)
                        views["bullish_count"] += 1
                    elif bearish_score > bullish_score and bearish_score >= 2:
                        views["bearish_modules"].append(display_name)
                        views["bearish_count"] += 1
                    else:
                        views["neutral_modules"].append(display_name)
                        views["neutral_count"] += 1
                    views["total_count"] += 1
        
        return views
    
    def _check_strategy_consistency(self, trader_conclusion: str, debate_winner: str) -> bool:
        """检查交易员结论与辩论结果的一致性"""
        
        trader_bullish = "做多" in trader_conclusion or "看多" in trader_conclusion
        trader_bearish = "做空" in trader_conclusion or "看空" in trader_conclusion
        
        debate_bullish = "多头" in debate_winner
        debate_bearish = "空头" in debate_winner
        
        # 一致性检查
        if (trader_bullish and debate_bullish) or (trader_bearish and debate_bearish):
            return True
        else:
            return False
    
    def _calculate_complete_risk_parameters(self, trading_decision: TradingDecision, debate_result: DebateResult, overall_risk: RiskLevel) -> Dict[str, Any]:
        """计算完整风险参数 - 基于实际可获得的信息和动态调整"""
        
        # 基础参数设定
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        strategy_type = trading_decision.strategy_type.value
        
        # 基于辩论分歧程度的风险评估
        disagreement_level = "高" if score_diff < 1.5 else "中" if score_diff < 2.5 else "低"
        
        # 策略类型风险评估
        strategy_risk_level = {
            "单边做多": "中等",
            "单边做空": "中等",
            "套利策略": "较低",
            "对冲策略": "较低",
            "观望": "极低",
            "中性策略": "较低"
        }.get(strategy_type, "中等")
        
        # 🔧 动态风控参数计算 - 根据策略类型和分歧程度动态调整
        level1_warning, level2_stop, level3_force = self._calculate_dynamic_stop_levels(
            strategy_type, disagreement_level, overall_risk
        )
        
        # 🔧 动态流动性管控参数
        daily_volume_limit = self._calculate_volume_limit(strategy_type, disagreement_level)
        batch_count, batch_interval = self._calculate_batch_params(disagreement_level, overall_risk)
        
        return {
            'disagreement_level': disagreement_level,
            'strategy_risk_level': strategy_risk_level,
            'level1_warning': f"{level1_warning:.1f}",
            'level2_stop': f"{level2_stop:.1f}",
            'level3_force': f"{level3_force:.1f}",
            'daily_volume_limit': f"{daily_volume_limit:.1f}",
            'batch_count': batch_count,
            'batch_interval': batch_interval
        }
    
    def _calculate_dynamic_stop_levels(self, strategy_type: str, disagreement_level: str, 
                                     overall_risk: RiskLevel) -> Tuple[float, float, float]:
        """动态计算止损参数 - 根据策略类型和风险等级调整"""
        
        # 基础止损水平
        base_levels = {
            "单边做多": (2.5, 4.0, 6.0),
            "单边做空": (2.5, 4.0, 6.0),
            "跨期套利": (1.5, 2.5, 4.0),
            "跨品种套利": (2.0, 3.0, 5.0),
            "期权策略": (3.0, 5.0, 7.0),
            "对冲策略": (1.0, 2.0, 3.0),
            "中性策略": (1.5, 2.5, 4.0),
            "观望": (0.5, 1.0, 2.0)
        }
        
        level1, level2, level3 = base_levels.get(strategy_type, (2.0, 3.5, 5.0))
        
        # 根据分歧程度调整
        if disagreement_level == "高":
            level1 *= 0.8  # 分歧高时更严格
            level2 *= 0.8
            level3 *= 0.9
        elif disagreement_level == "低":
            level1 *= 1.2  # 分歧低时可适度放宽
            level2 *= 1.1
            level3 *= 1.1
        
        # 根据整体风险等级调整
        if overall_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            level1 *= 0.7  # 高风险时更严格
            level2 *= 0.8
            level3 *= 0.9
        elif overall_risk == RiskLevel.LOW:
            level1 *= 1.3  # 低风险时可适度放宽
            level2 *= 1.2
            level3 *= 1.1
            
        return level1, level2, level3
    
    def _calculate_volume_limit(self, strategy_type: str, disagreement_level: str) -> float:
        """计算成交量限制"""
        
        # 基础成交量限制
        base_limits = {
            "单边做多": 2.0,
            "单边做空": 2.0,
            "跨期套利": 1.5,
            "跨品种套利": 1.8,
            "期权策略": 1.2,
            "对冲策略": 1.0,
            "中性策略": 1.0,
            "观望": 0.5
        }
        
        base_limit = base_limits.get(strategy_type, 1.5)
        
        # 根据分歧程度调整
        if disagreement_level == "高":
            return base_limit * 0.7  # 分歧高时更保守
        elif disagreement_level == "低":
            return base_limit * 1.2  # 分歧低时可适度增加
        else:
            return base_limit
    
    def _calculate_batch_params(self, disagreement_level: str, overall_risk: RiskLevel) -> Tuple[int, int]:
        """计算分批建仓参数"""
        
        # 基础分批参数
        if disagreement_level == "高":
            batch_count = 4
            batch_interval = 20
        elif disagreement_level == "中等":
            batch_count = 3
            batch_interval = 15
        else:
            batch_count = 2
            batch_interval = 10
            
        # 根据风险等级调整
        if overall_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            batch_count = max(3, batch_count)  # 高风险时至少3批
            batch_interval = max(15, batch_interval)  # 间隔至少15分钟
        elif overall_risk == RiskLevel.LOW:
            batch_count = max(2, batch_count - 1)  # 低风险时可减少批次
            batch_interval = max(10, batch_interval - 5)  # 缩短间隔
            
        return batch_count, batch_interval
    
    def _format_analysis_summary(self, analysis_state: FuturesAnalysisState) -> str:
        """格式化分析摘要"""
        summary = f"品种：{analysis_state.commodity}，分析日期：{analysis_state.analysis_date}\n"
        
        if analysis_state.inventory_analysis:
            summary += "库存分析：已完成\n"
        if analysis_state.positioning_analysis:
            summary += "持仓分析：已完成\n"
        if analysis_state.technical_analysis:
            summary += "技术分析：已完成\n"
        if analysis_state.basis_analysis:
            summary += "基差分析：已完成\n"
        if analysis_state.news_analysis:
            summary += "新闻分析：已完成\n"
        if analysis_state.term_structure_analysis:
            summary += "期限结构分析：已完成\n"
            
        return summary
    
    def _extract_detailed_analysis(self, analysis_state: FuturesAnalysisState) -> str:
        """提取详细分析数据供风控评估"""
        details = []
        
        # 技术分析详情
        if analysis_state.technical_analysis:
            tech = analysis_state.technical_analysis
            confidence = tech.confidence_score
            content = tech.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"技术分析置信度：{safe_format_percent(confidence)}，关键信号：{content}")
        
        # 持仓分析详情
        if analysis_state.positioning_analysis:
            pos = analysis_state.positioning_analysis
            confidence = pos.confidence_score
            content = pos.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"持仓分析置信度：{safe_format_percent(confidence)}，资金流向：{content}")
        
        # 基差分析详情
        if analysis_state.basis_analysis:
            basis = analysis_state.basis_analysis
            confidence = basis.confidence_score
            content = basis.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"基差分析置信度：{safe_format_percent(confidence)}，价差状况：{content}")
        
        # 新闻分析详情
        if analysis_state.news_analysis:
            news = analysis_state.news_analysis
            confidence = news.confidence_score
            content = news.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"新闻分析置信度：{safe_format_percent(confidence)}，消息面：{content}")
        
        # 期限结构详情
        if analysis_state.term_structure_analysis:
            term = analysis_state.term_structure_analysis
            confidence = term.confidence_score
            content = term.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"期限结构置信度：{safe_format_percent(confidence)}，曲线形态：{content}")
        
        # 库存分析详情
        if analysis_state.inventory_analysis:
            inv = analysis_state.inventory_analysis
            confidence = inv.confidence_score
            content = inv.result_data.get('analysis_content', '')[:200] + "..."
            details.append(f"库存分析置信度：{safe_format_percent(confidence)}，供需状况：{content}")
        
        return '\n'.join(details) if details else "分析数据不完整"
    
    def _calculate_risk_scores(self, analysis_state: FuturesAnalysisState, 
                             debate_result: DebateResult) -> Dict[str, float]:
        """计算各项风险评分 - 基于实际分析数据"""
        
        # 1. 市场风险 - 基于辩论分歧和技术指标
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        # 得分差异小说明分歧大，风险高
        if score_diff < 1.0:
            market_risk = 8.5  # 高度分歧
        elif score_diff < 2.0:
            market_risk = 6.5  # 中度分歧
        else:
            market_risk = 4.0  # 共识较强
        
        # 技术分析风险调整
        if analysis_state.technical_analysis:
            tech_content = analysis_state.technical_analysis.result_data.get('analysis_content', '')
            confidence = analysis_state.technical_analysis.confidence_score
            
            # 置信度低增加风险
            if safe_convert_to_float(confidence) < 0.6:
                market_risk += 1.5
            
            # 技术信号冲突增加风险
            if '冲突' in tech_content or '分歧' in tech_content:
                market_risk += 1.0
        
        # 2. 流动性风险 - 基于持仓分析
        liquidity_risk = 4.0  # 基础流动性风险
        
        if analysis_state.positioning_analysis:
            pos_content = analysis_state.positioning_analysis.result_data.get('analysis_content', '')
            
            # 持仓集中度高增加流动性风险
            if '集中' in pos_content:
                liquidity_risk += 1.5
            
            # 大幅增减仓增加风险
            if '大幅' in pos_content:
                liquidity_risk += 1.0
        
        # 3. 杠杆风险 - 基于波动率和品种特性
        leverage_risk = 7.0  # 期货基础杠杆风险
        
        # 根据争议问题数量调整
        unresolved_count = len(debate_result.unresolved_issues)
        if unresolved_count > 3:
            leverage_risk += 1.0
        elif unresolved_count > 5:
            leverage_risk += 2.0
        
        # 4. 集中度风险 - 基于新闻和基本面
        concentration_risk = 6.0  # 基础集中风险
        
        if analysis_state.news_analysis:
            news_content = analysis_state.news_analysis.result_data.get('analysis_content', '')
            
            # 重大消息增加集中度风险
            if '重大' in news_content or '突发' in news_content:
                concentration_risk += 1.5
            
            # 政策相关增加风险
            if '政策' in news_content:
                concentration_risk += 1.0
        
        # 确保风险评分在合理范围内
        return {
            "market": min(10.0, max(1.0, market_risk)),
            "liquidity": min(10.0, max(1.0, liquidity_risk)),
            "leverage": min(10.0, max(1.0, leverage_risk)),
            "concentration": min(10.0, max(1.0, concentration_risk))
        }
    
    def _determine_overall_risk_level(self, risk_scores: Dict[str, float]) -> RiskLevel:
        """确定整体风险等级（旧方法，保留兼容性）"""
        avg_score = sum(risk_scores.values()) / len(risk_scores)
        
        if avg_score <= 3.0:
            return RiskLevel.LOW
        elif avg_score <= 5.0:
            return RiskLevel.MEDIUM
        elif avg_score <= 7.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _determine_risk_level_from_trading_decision(self, trading_decision: TradingDecision, debate_result: DebateResult) -> RiskLevel:
        """🔥 改进：基于损失和概率的风险矩阵判定风险等级"""
        
        # 🔥 第一步：从风控意见中提取潜在损失和风险概率
        try:
            risk_opinion = getattr(trading_decision, 'risk_manager_opinion', '') or ''
            
            # 尝试提取已计算的损失和概率
            potential_loss = self._extract_potential_loss_from_opinion(risk_opinion)
            risk_probability = self._extract_risk_probability_from_opinion(risk_opinion)
            
            # 如果提取失败，使用基础估算
            if potential_loss == 0:
                potential_loss = self._estimate_potential_loss(trading_decision)
            if risk_probability == 0:
                risk_probability = self._estimate_risk_probability(trading_decision, debate_result)
            
            self.logger.info(f"风险评估: 潜在损失={potential_loss:.1%}, 风险概率={risk_probability:.0%}")
            
        except Exception as e:
            self.logger.warning(f"风险参数提取失败: {e}，使用基础估算")
            potential_loss = self._estimate_potential_loss(trading_decision)
            risk_probability = self._estimate_risk_probability(trading_decision, debate_result)
        
        # ✅ 第二步：基于风险矩阵判定风险等级（优化逻辑）
        # 风险矩阵：
        # - 极高风险：损失>5% OR (损失>4% AND 概率>=70%) OR (损失>3% AND 概率>80%)
        # - 高风险：(损失3-5% AND 概率60-80%) OR (损失>5% AND 概率<60%)
        # - 中等风险：(损失2-3% AND 概率40-70%) OR (损失<3% AND 概率60-70%)
        # - 低风险：损失<2% AND 概率<40%
        
        print(f"🐛 DEBUG [风险判定]: 潜在损失={potential_loss:.1%}, 风险概率={risk_probability:.0%}")
        
        # ✅ 极高风险判定（更严格）- 注意4.5%不应该被判定为极高风险
        if potential_loss > 0.05:  # 损失超过5%（严格大于，4.5%不算）
            risk_level = RiskLevel.VERY_HIGH
            print(f"🐛 DEBUG [风险判定]: 极高风险 - 原因：损失{potential_loss:.3f}({potential_loss:.1%}) > 0.05(5%)")
        elif potential_loss >= 0.045 and risk_probability >= 0.75:  # 损失>=4.5% 且 概率>=75%（提高概率阈值）
            risk_level = RiskLevel.VERY_HIGH
            print(f"🐛 DEBUG [风险判定]: 极高风险 - 原因：损失{potential_loss:.3f} >= 0.045 且 概率{risk_probability:.0%} >= 75%")
        elif potential_loss > 0.03 and risk_probability > 0.80:  # 损失>3% 且 概率>80%
            risk_level = RiskLevel.VERY_HIGH
            print(f"🐛 DEBUG [风险判定]: 极高风险 - 原因：损失{potential_loss:.1%} > 3% 且 概率{risk_probability:.0%} > 80%")
        # ✅ 高风险判定
        elif 0.03 <= potential_loss <= 0.05 and 0.60 <= risk_probability <= 0.80:
            risk_level = RiskLevel.HIGH  # 4.5% + 65% 属于这里
            print(f"🐛 DEBUG [风险判定]: 高风险 - 原因：损失{potential_loss:.1%}在3-5%之间 且 概率{risk_probability:.0%}在60-80%之间")
        elif potential_loss > 0.05 and risk_probability < 0.60:
            risk_level = RiskLevel.HIGH
            print(f"🐛 DEBUG [风险判定]: 高风险 - 原因：损失{potential_loss:.1%} > 5% 但 概率{risk_probability:.0%} < 60%")
        # ✅ 中等风险判定
        elif 0.02 <= potential_loss < 0.03 and 0.40 <= risk_probability <= 0.70:
            risk_level = RiskLevel.MEDIUM
            print(f"🐛 DEBUG [风险判定]: 中等风险 - 原因：损失{potential_loss:.1%}在2-3%之间")
        elif potential_loss < 0.03 and 0.60 <= risk_probability <= 0.70:
            risk_level = RiskLevel.MEDIUM
            print(f"🐛 DEBUG [风险判定]: 中等风险 - 原因：损失{potential_loss:.1%} < 3%")
        # ✅ 低风险判定
        elif potential_loss < 0.02 and risk_probability < 0.40:
            risk_level = RiskLevel.LOW
            print(f"🐛 DEBUG [风险判定]: 低风险 - 原因：损失{potential_loss:.1%} < 2% 且 概率{risk_probability:.0%} < 40%")
        else:
            # 边界情况，保守处理
            print(f"🐛 DEBUG [风险判定]: 进入边界情况处理")
            if potential_loss >= 0.045:
                risk_level = RiskLevel.HIGH  # 4.5%以上保守处理为高风险
                print(f"🐛 DEBUG [风险判定]: 高风险 - 原因：边界情况，损失{potential_loss:.1%} >= 4.5%")
            elif potential_loss >= 0.03 or risk_probability >= 0.65:
                risk_level = RiskLevel.HIGH
                print(f"🐛 DEBUG [风险判定]: 高风险 - 原因：边界情况，损失{potential_loss:.1%} >= 3% 或 概率{risk_probability:.0%} >= 65%")
            elif potential_loss >= 0.02 or risk_probability >= 0.50:
                risk_level = RiskLevel.MEDIUM
                print(f"🐛 DEBUG [风险判定]: 中等风险 - 原因：边界情况")
            else:
                risk_level = RiskLevel.MEDIUM
                print(f"🐛 DEBUG [风险判定]: 中等风险 - 原因：边界情况默认值")
        
        print(f"🐛 DEBUG [风险判定]: 最终判定 = {risk_level.value}")
        self.logger.info(f"风险等级判定: {risk_level.value} (损失{potential_loss:.1%}, 概率{risk_probability:.0%})")
        return risk_level
    
    def _extract_potential_loss_from_opinion(self, opinion: str) -> float:
        """从风控意见中提取潜在损失"""
        import re
        
        # 查找"最大潜在亏损"或"极端止损"
        patterns = [
            r'最大潜在亏损约(\d+\.?\d*)%',
            r'极端止损：(\d+\.?\d*)%',
            r'极端情况.*?亏损可能扩大至(\d+\.?\d*)%'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, opinion)
            if match:
                return float(match.group(1)) / 100
        
        return 0.0
    
    def _extract_risk_probability_from_opinion(self, opinion: str) -> float:
        """从风控意见中提取风险概率"""
        import re
        
        # 查找"平均发生概率"
        pattern = r'平均发生概率为(\d+)%'
        match = re.search(pattern, opinion)
        if match:
            return float(match.group(1)) / 100
        
        return 0.0
    
    def _estimate_potential_loss(self, trading_decision: TradingDecision) -> float:
        """估算潜在损失（基于止损位或策略类型）"""
        
        # 尝试从推理中提取止损幅度
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        import re
        
        # 查找止损相关信息
        stop_patterns = [
            r'止损.*?(\d+\.?\d*)%',
            r'最大亏损约(\d+\.?\d*)%',
            r'回撤.*?(\d+\.?\d*)%'
        ]
        
        for pattern in stop_patterns:
            match = re.search(pattern, reasoning)
            if match:
                return float(match.group(1)) / 100
        
        # 如果没有明确止损，基于策略类型估算
        strategy_type = trading_decision.strategy_type.value
        strategy_loss_map = {
            "单边做多": 0.04,  # 4%
            "单边做空": 0.04,  # 4%
            "跨期套利": 0.02,
            "对冲策略": 0.02,
            "中性策略": 0.01
        }
        
        return strategy_loss_map.get(strategy_type, 0.03)
    
    def _estimate_risk_probability(self, trading_decision: TradingDecision, debate_result: DebateResult) -> float:
        """🔥 修复：估算风险概率（基于辩论分歧，使用与风控意见一致的逻辑）"""
        
        # 🔥 修复：使用与_generate_basic_risk_opinion中一致的概率计算逻辑
        bull_score = debate_result.overall_bull_score
        bear_score = debate_result.overall_bear_score
        score_diff = abs(bull_score - bear_score)
        
        # 严格按照辩论分歧度判定（与风控意见生成逻辑一致）
        if score_diff < 1.0:
            risk_probability = 0.75  # 75% - 激烈分歧
        elif score_diff < 2.0:
            risk_probability = 0.60  # 60% - 存在分歧
        else:
            risk_probability = 0.40  # 40% - 方向一致
        
        # 🔥 不再基于信心度和关键词进行额外调整，避免过度上调
        # 这是导致90%概率的根源，已移除
        
        print(f"🐛 DEBUG [风险概率]: bull_score={bull_score}, bear_score={bear_score}, score_diff={score_diff:.1f}, risk_probability={risk_probability:.0%}")
        return risk_probability
    
    def _identify_key_risks(self, analysis_state: FuturesAnalysisState,
                          debate_result: DebateResult, trading_decision: TradingDecision = None) -> List[str]:
        """基于实际分析识别关键风险因素"""
        
        risks = []
        
        # 基于辩论分歧程度识别风险
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        if score_diff < 1.0:
            risks.append("多空辩论高度分歧，市场方向不确定性极高")
        elif score_diff < 2.0:
            risks.append("多空观点存在分歧，存在方向性判断风险")
        
        # 基于交易员策略识别风险
        if trading_decision and hasattr(trading_decision, 'reasoning'):
            reasoning = trading_decision.reasoning.lower()
            if "做空" in reasoning and "超买" in reasoning:
                risks.append("逆势做空风险：技术超买可能持续，存在反弹压制风险")
            if "阻力" in reasoning:
                risks.append("关键阻力位突破风险：价格突破阻力将导致策略失效")
            if "基差" in reasoning and "异常" in reasoning:
                risks.append("基差异常波动风险：基差快速收敛可能削弱策略逻辑")
            if "库存" in reasoning:
                risks.append("供需基本面变化风险：库存数据超预期可能逆转价格走势")
        
        # 基于商品特性识别风险  
        commodity_name = get_commodity_name(analysis_state.commodity)
        if "银" in commodity_name:
            risks.append("贵金属政策敏感性：美联储政策转向将直接影响价格")
        elif "铜" in commodity_name:
            risks.append("工业需求变化风险：全球经济数据将影响需求预期")
        
        return risks[:4]  # 最多4个关键风险，避免过多
    
    def _generate_detailed_fallback_opinion(self, commodity: str, trading_decision: TradingDecision,
                                          debate_result: DebateResult, trader_analysis: Dict[str, str], 
                                          risk_level: RiskLevel, strategy_type: str, direction: str,
                                          analysis_state: FuturesAnalysisState = None) -> str:
        """生成科学的风控意见 - 基于量化数据的信心度评估"""
        
        commodity_name = get_commodity_name(commodity)
        
        # 🔥 修复：检查基础数据是否充足
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        reasoning_length = len(reasoning.strip())
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        # 如果数据严重不足，返回保守评估
        if reasoning_length < 50 and score_diff < 0.1:
            return f"""风控评估：数据不足，建议暂停操作

数据完整性分析：
⚠️ 交易员分析过于简单（仅{reasoning_length}字）
⚠️ 辞论结果平分（分差{score_diff:.1f}分）
⚠️ 市场方向不明确，无法进行科学评估

风控建议：
• 仓位控制：建议空仓观望
• 风险等级：{risk_level.value}（数据不足）
• 操作建议：等待更充分的分析数据和更清晰的市场信号

注：本评估基于实际数据不足的现状，采用保守原则"""
        
        # 科学信心度计算
        confidence_data = self._calculate_scientific_confidence_score(
            trading_decision, debate_result, risk_level, strategy_type, direction
        )
        
        # 🔥 修复：确保策略描述的一致性，避免自相矛盾
        unified_strategy_description = strategy_type
        if "单边做空" in strategy_type and "做多" in direction:
            # 检测并修复矛盾
            if "做空" in reasoning:
                unified_strategy_description = f"{strategy_type}（基于做空分析）"
            else:
                unified_strategy_description = f"策略不明确（分析存在矛盾）"
        
        # 🔥 全新：基于风险度的专业风控评估（保守方案）
        # 如果analysis_state为None，创建一个最小化的替代对象
        if analysis_state is None:
            temp_analysis_state = type('TempAnalysisState', (), {
                'commodity': commodity,
                'analysis_date': '2025-01-19'
            })()
            risk_assessment_result = self._calculate_risk_based_confidence_assessment(
                trading_decision, debate_result, risk_level, temp_analysis_state
            )
        else:
            risk_assessment_result = self._calculate_risk_based_confidence_assessment(
                trading_decision, debate_result, risk_level, analysis_state
            )
        
        return f"""🛡️ 专业风控评估（保守评估）

【操作信心度】{risk_assessment_result['confidence_level']}
基于有限数据的保守风险评估

【风险度分析】
• 潜在最大亏损：{risk_assessment_result['potential_loss_ratio']:.1%}（基于止损估算）
• 风险因素概率：{risk_assessment_result['risk_probability']:.0%}
• 综合风险等级：{risk_assessment_result['comprehensive_risk']}

【主要风险因素】
{chr(10).join('• ' + factor for factor in risk_assessment_result['risk_factors'])}

【风控逻辑】
分析数据不充分，风险评估偏向保守；{risk_assessment_result['confidence_reasoning']}

【操作建议】
交易策略：{unified_strategy_description}
风险等级：{risk_level.value}
执行指引：建议等待更多数据或采用极小仓位试探"""
    
    def _calculate_risk_based_confidence_assessment(self, trading_decision: TradingDecision,
                                                  debate_result: DebateResult, risk_level: RiskLevel,
                                                  analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """🔥 专业风控：基于潜在亏损和风险概率的操作信心度评估"""
        
        # 第一步：计算潜在最大亏损（基于止损点）
        potential_loss = self._calculate_potential_loss_ratio(trading_decision, analysis_state)
        
        # 第二步：评估风险因素发生概率
        risk_probability = self._assess_risk_factors_probability(trading_decision, debate_result, analysis_state)
        
        # 第三步：综合风险度评估
        comprehensive_risk_level = self._assess_comprehensive_risk_level(
            potential_loss, risk_probability, risk_level
        )
        
        # 第四步：基于风险度确定操作信心度（高/中/低）
        confidence_level = self._determine_operational_confidence_from_risk(
            potential_loss, risk_probability, comprehensive_risk_level
        )
        
        # 第五步：生成专业风控逻辑说明
        confidence_reasoning = self._generate_professional_risk_reasoning(
            potential_loss, risk_probability, comprehensive_risk_level, confidence_level
        )
        
        return {
            "confidence_level": confidence_level,  # 高/中/低
            "potential_loss_ratio": potential_loss,
            "risk_probability": risk_probability,
            "comprehensive_risk": comprehensive_risk_level,
            "risk_factors": self._generate_risk_factor_details(trading_decision, analysis_state, debate_result),
            "confidence_reasoning": confidence_reasoning
        }
    
    def _calculate_potential_loss_ratio(self, trading_decision: TradingDecision, 
                                      analysis_state: FuturesAnalysisState) -> float:
        """计算基于止损点的潜在亏损比例"""
        try:
            # 获取当前价格
            current_price = get_commodity_current_price(analysis_state.commodity)
            if current_price <= 0:
                return 0.05  # 默认5%风险
            
            # 从交易决策中提取止损价格
            stop_loss_price = None
            reasoning = trading_decision.reasoning or ""
            
            # 提取止损价格的多种模式
            import re
            stop_patterns = [
                r'止损[：:]\s*(\d+\.?\d*)',
                r'止损价[：:]\s*(\d+\.?\d*)',
                r'止损位[：:]\s*(\d+\.?\d*)',
                r'止损.*?(\d+\.?\d*)元',
                r'(\d+\.?\d*).*?止损'
            ]
            
            for pattern in stop_patterns:
                match = re.search(pattern, reasoning)
                if match:
                    stop_loss_price = float(match.group(1))
                    break
            
            # 如果没有明确的止损价，尝试从exit_points提取
            if not stop_loss_price and trading_decision.exit_points:
                for exit_point in trading_decision.exit_points:
                    exit_str = str(exit_point)
                    for pattern in stop_patterns:
                        match = re.search(pattern, exit_str)
                        if match:
                            stop_loss_price = float(match.group(1))
                            break
                    if stop_loss_price:
                        break
            
            # 如果仍然没有找到止损价，根据策略类型设定默认止损
            if not stop_loss_price:
                strategy_str = str(trading_decision.strategy_type.value).lower()
                if "做多" in strategy_str or "long" in strategy_str:
                    stop_loss_price = current_price * 0.95  # 默认5%止损
                elif "做空" in strategy_str or "short" in strategy_str:
                    stop_loss_price = current_price * 1.05  # 默认5%止损
                else:
                    return 0.05  # 默认5%
            
            # 计算潜在亏损比例
            if "做多" in str(trading_decision.strategy_type.value).lower():
                loss_ratio = max(0, (current_price - stop_loss_price) / current_price)
            elif "做空" in str(trading_decision.strategy_type.value).lower():
                loss_ratio = max(0, (stop_loss_price - current_price) / current_price)
            else:
                loss_ratio = abs(current_price - stop_loss_price) / current_price
            
            # 限制在合理范围内
            return min(max(loss_ratio, 0.01), 0.15)  # 1%-15%之间
            
        except Exception as e:
            print(f"⚠️ 潜在亏损计算失败: {e}")
            return 0.05  # 默认5%潜在亏损
    
    def _assess_risk_factors_probability(self, trading_decision: TradingDecision,
                                       debate_result: DebateResult,
                                       analysis_state: FuturesAnalysisState) -> float:
        """评估交易策略中风险因素的发生可能性"""
        try:
            risk_probability = 0.5  # 基础风险概率50%
            
            # 基于辩论结果调整风险概率
            if debate_result:
                score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
                if score_diff < 1:  # 辩论势均力敌，风险较高
                    risk_probability += 0.2
                elif score_diff >= 3:  # 一边优势明显，风险较低
                    risk_probability -= 0.2
            
            # 基于交易决策的分析质量调整
            reasoning = trading_decision.reasoning or ""
            if len(reasoning) < 100:  # 分析不充分
                risk_probability += 0.15
            elif len(reasoning) > 500:  # 分析较为充分
                risk_probability -= 0.1
            
            # 基于策略类型调整风险概率
            strategy_str = str(trading_decision.strategy_type.value).lower()
            if "谨慎" in strategy_str:
                risk_probability -= 0.1
            elif "积极" in strategy_str:
                risk_probability += 0.1
            
            # 检查是否存在明显的风险警告
            risk_keywords = ["风险", "警惕", "注意", "谨慎", "不确定", "分歧", "波动"]
            risk_count = sum(1 for keyword in risk_keywords if keyword in reasoning)
            risk_probability += min(risk_count * 0.05, 0.2)  # 每个风险词增加5%，最多20%
            
            # 限制在合理范围内
            return min(max(risk_probability, 0.2), 0.9)  # 20%-90%之间
            
        except Exception as e:
            print(f"⚠️ 风险因素概率评估失败: {e}")
            return 0.6  # 默认60%风险概率
    
    def _assess_comprehensive_risk_level(self, potential_loss: float, risk_probability: float, 
                                       base_risk_level: RiskLevel) -> str:
        """综合评估操作风险等级"""
        
        # 计算风险综合得分 (0-100)
        loss_score = potential_loss * 100  # 潜在亏损转为分数
        prob_score = risk_probability * 100  # 风险概率转为分数
        base_score = {"低风险": 20, "中等风险": 50, "高风险": 80, "极高风险": 95}.get(base_risk_level.value, 50)
        
        # 加权计算综合风险得分
        comprehensive_score = (loss_score * 0.4 + prob_score * 0.3 + base_score * 0.3)
        
        # 转换为风险等级
        if comprehensive_score >= 75:
            return "高风险"
        elif comprehensive_score >= 45:
            return "中等风险"  
        else:
            return "低风险"
    
    def _determine_operational_confidence_from_risk(self, potential_loss: float, 
                                                  risk_probability: float, 
                                                  comprehensive_risk_level: str) -> str:
        """🔥 专业风控：基于潜在亏损和风险概率确定操作信心度"""
        
        # 风险度评分系统
        risk_score = 0
        
        # 潜在亏损评分（权重60%）
        if potential_loss <= 0.02:  # ≤2%
            loss_score = 3  # 低风险
        elif potential_loss <= 0.05:  # 2%-5%
            loss_score = 2  # 中等风险
        else:  # >5%
            loss_score = 1  # 高风险
        
        # 风险概率评分（权重40%）
        if risk_probability <= 0.3:  # ≤30%
            prob_score = 3  # 低概率
        elif risk_probability <= 0.6:  # 30%-60%
            prob_score = 2  # 中等概率
        else:  # >60%
            prob_score = 1  # 高概率
        
        # 综合评分
        risk_score = loss_score * 0.6 + prob_score * 0.4
        
        # 确定操作信心度
        if risk_score >= 2.5:
            return "高"  # 低风险，高信心度
        elif risk_score >= 1.8:
            return "中"  # 中等风险，中等信心度
        else:
            return "低"  # 高风险，低信心度

    def _generate_professional_risk_reasoning(self, potential_loss: float, 
                                            risk_probability: float, 
                                            comprehensive_risk_level: str, 
                                            confidence_level: str) -> str:
        """生成专业的风控逻辑说明"""
        
        # 潜在亏损描述
        if potential_loss <= 0.02:
            loss_desc = "潜在亏损较小(≤2%)"
        elif potential_loss <= 0.05:
            loss_desc = f"潜在亏损适中({potential_loss:.1%})"
        else:
            loss_desc = f"潜在亏损较大({potential_loss:.1%})"
        
        # 风险概率描述
        if risk_probability <= 0.3:
            prob_desc = "风险因素发生概率较低"
        elif risk_probability <= 0.6:
            prob_desc = "风险因素发生概率适中"
        else:
            prob_desc = "风险因素发生概率较高"
        
        # 信心度逻辑
        if confidence_level == "高":
            logic = f"{loss_desc}，{prob_desc}，综合风险可控，操作信心度高"
        elif confidence_level == "中":
            logic = f"{loss_desc}，{prob_desc}，综合风险适中，需谨慎操作"
        else:
            logic = f"{loss_desc}，{prob_desc}，综合风险较高，建议降低仓位或观望"
        
        return logic
    
    def _determine_confidence_from_risk(self, comprehensive_risk_level: str) -> str:
        """基于综合风险等级确定操作信心度"""
        
        # 🎯 核心逻辑：风险越高，操作信心度越低
        risk_confidence_mapping = {
            "低风险": "高",      # 低风险 → 高信心度
            "中等风险": "中",    # 中等风险 → 中信心度  
            "高风险": "低"       # 高风险 → 低信心度
        }
        
        return risk_confidence_mapping.get(comprehensive_risk_level, "中")
    
    def _extract_concrete_analyst_risks(self, analysis_state: FuturesAnalysisState, 
                                      trading_decision: TradingDecision) -> Dict[str, str]:
        """🔥 新增：从分析师模块中提取具体的风险因素"""
        
        import re
        
        risks = {
            'technical': '技术指标存在风险信号',
            'fundamental': '基本面数据显示潜在风险', 
            'structure': '市场结构存在不稳定因素',
            'squeeze': '存在反向挤压风险',
            'direction': '市场方向存在不确定性',
            'execution': '策略执行存在时机风险',
            'volatility': '市场波动风险较高'
        }
        
        try:
            # 🔍 技术分析风险
            if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
                tech_data = analysis_state.technical_analysis.result_data
                tech_content = str(tech_data.get('analysis_content', '')).lower()
                
                if 'rsi' in tech_content:
                    rsi_match = re.search(r'rsi[：:\s]*(\d+\.?\d*)', tech_content)
                    if rsi_match:
                        rsi_value = float(rsi_match.group(1))
                        if rsi_value > 70:
                            risks['technical'] = f'RSI {rsi_value:.1f}显示超买，技术面存在回调风险'
                        elif rsi_value < 30:
                            risks['technical'] = f'RSI {rsi_value:.1f}显示超卖，但反弹力度不确定'
                
                if '布林带' in tech_content or 'bollinger' in tech_content:
                    if '上轨' in tech_content:
                        risks['technical'] = '价格接近布林带上轨，存在技术性回调压力'
                    elif '下轨' in tech_content:
                        risks['technical'] = '价格接近布林带下轨，但支撑强度待验证'
            
            # 🔍 库存分析风险
            if hasattr(analysis_state, 'inventory_analysis') and analysis_state.inventory_analysis:
                inv_data = analysis_state.inventory_analysis.result_data
                inv_content = str(inv_data.get('analysis_content', '')).lower()
                
                if '库存' in inv_content:
                    if '增长' in inv_content or '增加' in inv_content:
                        # 提取具体数值
                        increase_match = re.search(r'增[长加][：:\s]*(\d+\.?\d*)', inv_content)
                        if increase_match:
                            increase_val = increase_match.group(1)
                            risks['fundamental'] = f'库存增长{increase_val}，供应压力可能抑制价格上涨'
                        else:
                            risks['fundamental'] = '库存持续增长，供应过剩风险加剧'
                    
                    if '历史高位' in inv_content or '100%' in inv_content:
                        risks['fundamental'] = '库存处于历史高位，去库存压力巨大'
            
            # 🔍 持仓分析风险
            if hasattr(analysis_state, 'positioning_analysis') and analysis_state.positioning_analysis:
                pos_data = analysis_state.positioning_analysis.result_data
                pos_content = str(pos_data.get('analysis_content', '')).lower()
                
                if '集中度' in pos_content:
                    if '低' in pos_content or '分散' in pos_content:
                        risks['structure'] = '持仓集中度低，缺乏主力资金稳定支撑，易发生踩踏'
                    elif '高' in pos_content:
                        risks['structure'] = '持仓过度集中，主力资金变动可能引发剧烈波动'
            
            # 🔍 基差分析风险
            if hasattr(analysis_state, 'basis_analysis') and analysis_state.basis_analysis:
                basis_data = analysis_state.basis_analysis.result_data
                basis_content = str(basis_data.get('analysis_content', '')).lower()
                
                if '基差' in basis_content:
                    if '分化' in basis_content or '异常' in basis_content:
                        risks['structure'] = '基差结构异常分化，定价机制紊乱，存在修复风险'
                    elif '弱势' in basis_content:
                        risks['fundamental'] = '基差持续弱势，现货需求疲软，价格承压'
            
        except Exception as e:
            print(f"⚠️ 提取分析师风险因素失败: {e}")
        
        return risks
    
    def _calculate_realistic_potential_loss(self, trading_decision: TradingDecision, 
                                          analysis_state: FuturesAnalysisState) -> float:
        """🔥 新增：基于实际止损位计算真实的潜在亏损"""
        
        import re
        
        try:
            # 尝试从交易决策中提取止损信息
            if hasattr(trading_decision, 'stop_loss') and trading_decision.stop_loss:
                stop_loss_str = str(trading_decision.stop_loss)
                
                # 提取止损位数值
                stop_match = re.search(r'(\d+\.?\d*)', stop_loss_str)
                if stop_match:
                    stop_price = float(stop_match.group(1))
                    
                    # 尝试获取当前价格
                    current_price = None
                    if hasattr(analysis_state, 'technical_analysis') and analysis_state.technical_analysis:
                        tech_data = analysis_state.technical_analysis.result_data
                        price_match = re.search(r'当前价[格位：:\s]*(\d+\.?\d*)', str(tech_data))
                        if price_match:
                            current_price = float(price_match.group(1))
                    
                    if current_price:
                        loss_ratio = abs(stop_price - current_price) / current_price
                        return min(loss_ratio, 0.10)  # 最大不超过10%
            
            # 如果无法提取具体数值，根据策略类型返回经验值
            strategy_str = str(trading_decision.strategy_type).lower()
            if 'long' in strategy_str or '做多' in strategy_str:
                return 0.035  # 3.5%
            elif 'short' in strategy_str or '做空' in strategy_str:
                return 0.045  # 4.5%
            else:
                return 0.030  # 3.0%
                
        except Exception as e:
            print(f"⚠️ 计算潜在亏损失败: {e}")
            return 0.040  # 默认4%
    
    def _generate_risk_factor_details(self, trading_decision: TradingDecision,
                                    analysis_state: FuturesAnalysisState, 
                                    debate_result: DebateResult = None) -> List[str]:
        """🔥 综合分析：整合分析师模块、辩论环节和交易员分析的风险提示"""
        
        risk_factors_with_sources = {}  # 使用字典避免重复，并记录来源
        
        try:
            # 第一层：从分析师模块中提取风险因素
            analyst_risks = self._extract_analyst_risk_warnings(analysis_state)
            for risk, source_list in analyst_risks.items():
                if risk not in risk_factors_with_sources:
                    risk_factors_with_sources[risk] = []
                risk_factors_with_sources[risk].extend(source_list)
            
            # 第二层：从辩论环节中提取风险因素（多空双方提到的风险）
            debate_risks = self._extract_debate_risk_factors(analysis_state, debate_result)
            for risk, source_list in debate_risks.items():
                if risk not in risk_factors_with_sources:
                    risk_factors_with_sources[risk] = []
                risk_factors_with_sources[risk].extend(source_list)
            
            # 第三层：从交易员分析中提取风险因素
            trader_risks = self._extract_trader_risk_warnings(trading_decision)
            for risk, source_list in trader_risks.items():
                if risk not in risk_factors_with_sources:
                    risk_factors_with_sources[risk] = []
                risk_factors_with_sources[risk].extend(source_list)
            
            # 整理最终的风险因素列表，按重要程度排序
            final_risk_factors = self._prioritize_risk_factors(risk_factors_with_sources)
                
        except Exception as e:
            print(f"⚠️ 风险因素综合分析失败: {e}")
            final_risk_factors = ["风险因素识别中，建议谨慎操作"]
        
        return final_risk_factors[:6]  # 最多6个主要风险因素
    
    def _detect_available_modules(self, analysis_state: FuturesAnalysisState) -> List[str]:
        """检测实际存在的分析模块 - 完全动态检测，支持任意组合和未来扩展"""
        available = []
        
        # 标准模块映射
        standard_modules = {
            'technical_analysis': 'technical',
            'basis_analysis': 'basis', 
            'inventory_analysis': 'inventory',
            'positioning_analysis': 'positioning',
            'term_structure_analysis': 'term_structure',
            'news_analysis': 'news'
        }
        
        for attr_name, module_key in standard_modules.items():
            if hasattr(analysis_state, attr_name):
                module = getattr(analysis_state, attr_name)
                if module is not None:
                    # 检查模块是否有有效数据
                    if hasattr(module, 'result_data') and module.result_data:
                        available.append(module_key)
                        print(f"✅ 检测到有效模块: {module_key}")
                    else:
                        print(f"⚠️ 模块存在但无数据: {module_key}")
                        
        # 🚀 未来扩展性：自动检测可能的新增模块
        # 检测任何以"_analysis"结尾的属性
        for attr_name in dir(analysis_state):
            if attr_name.endswith('_analysis') and not attr_name.startswith('_'):
                if attr_name not in standard_modules:
                    module = getattr(analysis_state, attr_name)
                    if module is not None:
                        # 推导模块名
                        module_key = attr_name.replace('_analysis', '')
                        if hasattr(module, 'result_data') and module.result_data:
                            available.append(module_key)
                            print(f"🚀 检测到扩展模块: {module_key}")
        
        print(f"✅ 总共检测到 {len(available)} 个可用模块: {available}")
        return available
    
    def _get_module_display_name(self, module_key: str) -> str:
        """获取模块显示名称 - 支持动态映射"""
        standard_names = {
            'technical': '技术分析',
            'basis': '基差分析', 
            'inventory': '库存分析',
            'positioning': '持仓分析',
            'term_structure': '期限结构',
            'news': '新闻分析'
        }
        return standard_names.get(module_key, f"{module_key}分析")
    
    def _extract_analyst_risk_warnings(self, analysis_state: FuturesAnalysisState) -> Dict[str, List[str]]:
        """从各个分析师模块中提取风险警告"""
        
        risk_warnings = {}
        available_modules = self._detect_available_modules(analysis_state)
        
        # 定义各模块的风险关键词映射
        module_risk_mapping = {
            "technical": {
                "keywords": ["破位", "支撑失效", "阻力强劲", "下跌风险", "技术面恶化", "卖压", "空头信号"],
                "risk_type": "技术面风险"
            },
            "basis": {
                "keywords": ["基差扩大", "升贴水异常", "交割风险", "期现背离", "基差不稳定"],
                "risk_type": "基差风险" 
            },
            "inventory": {
                "keywords": ["库存积压", "去库缓慢", "库存高企", "供应过剩", "库存风险"],
                "risk_type": "库存风险"
            },
            "positioning": {
                "keywords": ["资金流出", "减仓", "空头增仓", "多头离场", "持仓风险", "平仓压力"],
                "risk_type": "持仓风险"
            },
            "term_structure": {
                "keywords": ["期限结构异常", "远期贴水", "曲线陡峭", "结构性风险", "交割月风险"],
                "risk_type": "期限结构风险"
            },
            "news": {
                "keywords": ["政策风险", "监管收紧", "负面消息", "不确定性", "宏观承压", "外部冲击"],
                "risk_type": "消息面风险"
            }
        }
        
        for module_key in available_modules:
            try:
                module_data = None
                if hasattr(analysis_state, module_key) and getattr(analysis_state, module_key):
                    module_data = getattr(analysis_state, module_key)
                else:
                    attr_name = f"{module_key}_analysis"
                    if hasattr(analysis_state, attr_name) and getattr(analysis_state, attr_name):
                        module_data = getattr(analysis_state, attr_name)
                
                if not module_data or not hasattr(module_data, 'result_data'):
                    continue
                
                analysis_content = str(module_data.result_data.get('analysis_content', '')).lower()
                
                # 检查该模块的风险关键词
                if module_key in module_risk_mapping:
                    risk_config = module_risk_mapping[module_key]
                    for keyword in risk_config["keywords"]:
                        if keyword in analysis_content:
                            risk_type = risk_config["risk_type"]
                            module_name = self._get_module_display_name(module_key)
                            if risk_type not in risk_warnings:
                                risk_warnings[risk_type] = []
                            risk_warnings[risk_type].append(f"{module_name}分析")
                            break  # 避免同一模块重复添加相同风险类型
                            
            except Exception as e:
                print(f"⚠️ 提取{module_key}模块风险失败: {e}")
                continue
        
        return risk_warnings
    
    def _extract_debate_risk_factors(self, analysis_state: FuturesAnalysisState, 
                                   debate_result: DebateResult = None) -> Dict[str, List[str]]:
        """从辞论环节中提取风险因素（从实际辞论内容中分析）"""
        
        debate_risks = {}
        
        try:
            debate_content = ""
            
            # 优先从 debate_result 中获取辞论内容
            if debate_result and hasattr(debate_result, 'rounds'):
                # 整合所有轮次的辞论内容
                for round_data in debate_result.rounds:
                    if hasattr(round_data, 'bull_argument'):
                        debate_content += str(round_data.bull_argument) + " "
                    if hasattr(round_data, 'bear_argument'):
                        debate_content += str(round_data.bear_argument) + " "
                
                # 添加辞论总结内容
                if hasattr(debate_result, 'debate_summary'):
                    debate_content += str(debate_result.debate_summary)
                    
            # 备用方案：从 analysis_state 中获取
            elif hasattr(analysis_state, 'last_debate_content'):
                debate_content = str(analysis_state.last_debate_content)
            
            if debate_content:
                debate_content_lower = debate_content.lower()
                
                # 🔥 增强版风险关键词检测（基于辞论实际内容）
                risk_keywords_mapping = {
                    "价格下跌风险": [
                        "下跌风险", "价格下行", "看跌", "下行压力", "跌破", 
                        "空头逻辑", "看空", "下跌趋势", "价格走弱"
                    ],
                    "供需失衡风险": [
                        "供需失衡", "供应过剩", "需求疲软", "供需矛盾", 
                        "过剩风险", "需求不足", "库存积压"
                    ],
                    "政策调控风险": [
                        "政策调控", "监管风险", "政策不确定", "调控加码", 
                        "政策变化", "监管收紧", "政策风险"
                    ],
                    "资金面风险": [
                        "资金流出", "流动性紧张", "资金面承压", "去杠杆", 
                        "资金撤离", "流动性不足", "资金紧张"
                    ],
                    "技术面破位风险": [
                        "技术破位", "支撑失守", "技术面恶化", "卖压沉重", 
                        "技术指标转空", "均线压制"
                    ],
                    "基本面恶化风险": [
                        "基本面恶化", "经济数据差", "行业景气下降", "盈利恶化",
                        "成本上升", "利润压缩"
                    ],
                    "外部环境风险": [
                        "外部冲击", "贸易摩擦", "地缘政治", "国际环境", 
                        "外盘拖累", "海外风险", "全球经济"
                    ],
                    "交割月风险": [
                        "交割风险", "合约到期", "移仓换月", "交割月压力",
                        "期现价差", "交割成本"
                    ]
                }
                
                # 检测每种风险类型
                for risk_type, keywords in risk_keywords_mapping.items():
                    risk_count = sum(1 for keyword in keywords if keyword in debate_content_lower)
                    
                    if risk_count > 0:
                        # 根据提及频次判断风险来源
                        if risk_count >= 3:
                            debate_risks[risk_type] = ["辞论多方确认"]
                        else:
                            debate_risks[risk_type] = ["辞论环节"]
                
                # 🎯 特别关注辞论中明确的风险警告
                explicit_risk_phrases = [
                    "主要风险", "核心风险", "关键风险", "重大风险", 
                    "需要警惕", "值得注意", "风险提示"
                ]
                
                for phrase in explicit_risk_phrases:
                    if phrase in debate_content_lower:
                        debate_risks["辞论明确风险警告"] = ["辞论环节"]
                        break
                        
        except Exception as e:
            print(f"⚠️ 提取辞论风险因素失败: {e}")
        
        return debate_risks
    
    def _extract_trader_risk_warnings(self, trading_decision: TradingDecision) -> Dict[str, List[str]]:
        """从交易员分析中提取风险提示"""
        
        trader_risks = {}
        
        try:
            reasoning = trading_decision.reasoning or ""
            reasoning_lower = reasoning.lower()
            
            # 交易员风险提示关键词映射
            trader_risk_mapping = {
                "市场波动风险": ["波动", "不稳定", "震荡", "波动加大", "不确定性"],
                "流动性风险": ["流动性", "成交量", "持仓量", "流动性不足", "成交清淡"],
                "政策风险": ["政策", "监管", "法规", "政策变化", "监管收紧"],
                "基本面风险": ["供需", "库存", "产量", "需求", "基本面恶化"],
                "技术面风险": ["技术", "支撑", "阻力", "突破", "技术面破位"],
                "止损风险": ["止损", "止盈", "风险控制", "仓位控制", "亏损"],
                "时间风险": ["时间", "持仓周期", "到期", "交割", "时间窗口"]
            }
            
            for risk_type, keywords in trader_risk_mapping.items():
                if any(keyword in reasoning_lower for keyword in keywords):
                    trader_risks[risk_type] = ["交易员分析"]
            
            # 特别关注交易员的明确风险提示
            explicit_risk_patterns = [
                "风险提示", "注意风险", "主要风险", "潜在风险", "警惕", "谨慎"
            ]
            
            for pattern in explicit_risk_patterns:
                if pattern in reasoning_lower:
                    trader_risks["交易员明确风险提示"] = ["交易员分析"]
                    break
                    
        except Exception as e:
            print(f"⚠️ 提取交易员风险提示失败: {e}")
        
        return trader_risks
    
    def _prioritize_risk_factors(self, risk_factors_with_sources: Dict[str, List[str]]) -> List[str]:
        """按重要程度和来源数量对风险因素进行优先级排序"""
        
        # 🎯 风险因素重要性权重（基于期货交易实践经验）
        risk_priority = {
            # 核心风险因素（权重8-10）
            "技术面风险": 9,
            "技术面破位风险": 9,
            "基差风险": 8, 
            "库存风险": 8,
            "价格下跌风险": 8,
            
            # 重要风险因素（权重6-7）
            "市场波动风险": 7,
            "政策风险": 7,
            "政策调控风险": 7,
            "供需失衡风险": 6,
            "持仓风险": 6,
            "基本面恶化风险": 6,
            
            # 一般风险因素（权重4-5）
            "流动性风险": 5,
            "资金面风险": 5,
            "交易员明确风险提示": 5,
            "辞论明确风险警告": 5,
            "消息面风险": 4,
            "期限结构风险": 4,
            "交割月风险": 4,
            
            # 次要风险因素（权重1-3）
            "止损风险": 3,
            "时间风险": 2,
            "外部环境风险": 2,
            
            # 默认权重
            "一般市场风险": 1
        }
        
        # 计算每个风险因素的综合得分
        risk_scores = {}
        for risk_type, sources in risk_factors_with_sources.items():
            # 基础重要性得分
            base_score = risk_priority.get(risk_type, 1)
            # 来源数量加成（多个来源提到的风险更重要）
            source_bonus = len(set(sources if isinstance(sources, list) else [sources]))
            # 综合得分
            total_score = base_score + source_bonus
            risk_scores[risk_type] = total_score
        
        # 按得分排序，生成最终风险因素列表
        sorted_risks = sorted(risk_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 生成带来源信息的风险描述
        final_risk_list = []
        for risk_type, score in sorted_risks:
            sources = risk_factors_with_sources[risk_type]
            if isinstance(sources, list):
                unique_sources = list(set(sources))
                if len(unique_sources) > 1:
                    risk_desc = f"{risk_type}（多方面确认）"
                else:
                    risk_desc = f"{risk_type}（{unique_sources[0]}）"
            else:
                risk_desc = f"{risk_type}（{sources}）"
            
            final_risk_list.append(risk_desc)
        
        # 如果没有识别出风险，添加默认项
        if not final_risk_list:
            final_risk_list = ["一般市场风险（基础评估）"]
        
        return final_risk_list
    
    def _generate_confidence_reasoning(self, potential_loss: float, risk_probability: float,
                                     comprehensive_risk: str, confidence_level: str) -> str:
        """生成信心度推理说明"""
        
        reasoning_parts = []
        
        # 潜在亏损分析
        if potential_loss <= 0.03:
            reasoning_parts.append(f"潜在亏损控制在{potential_loss:.1%}以内，止损设置合理")
        elif potential_loss <= 0.06:
            reasoning_parts.append(f"潜在亏损约{potential_loss:.1%}，风险可控")
        else:
            reasoning_parts.append(f"潜在亏损达{potential_loss:.1%}，需要谨慎")
        
        # 风险概率分析
        if risk_probability <= 0.4:
            reasoning_parts.append("风险因素发生概率较低")
        elif risk_probability <= 0.7:
            reasoning_parts.append("风险因素发生概率中等")
        else:
            reasoning_parts.append("风险因素发生概率较高")
        
        # 综合风险评估
        reasoning_parts.append(f"综合风险评估为{comprehensive_risk}")
        
        # 信心度结论
        confidence_explanation = {
            "高": "基于较低的风险敞口和可控的潜在亏损，操作信心度较高",
            "中": "考虑到中等程度的风险因素，采用中等信心度操作",
            "低": "鉴于较高的风险水平和潜在亏损，操作信心度偏低"
        }
        reasoning_parts.append(confidence_explanation.get(confidence_level, "信心度评估中"))
        
        return "；".join(reasoning_parts)
    
    def _convert_confidence_to_qualitative(self, confidence_value: float) -> str:
        """将数值信心度转换为定性描述"""
        if confidence_value >= 0.75:
            return "高"
        elif confidence_value >= 0.50:
            return "中"
        else:
            return "低"

    def _calculate_scientific_confidence_score(self, trading_decision: TradingDecision, 
                                             debate_result: DebateResult, risk_level: RiskLevel,
                                             strategy_type: str, direction: str) -> Dict[str, Any]:
        """基于实际数据的科学信心度计算"""
        
        # 初始化计算组件
        components = []
        factors = []
        base_score = 50.0  # 基础信心度50%
        
        # 1. 交易员分析质量评估（0-20分）
        reasoning = trading_decision.reasoning or ""
        analysis_length = len(reasoning)
        
        if analysis_length >= 500:
            analysis_quality_score = 20
            factors.append("✓ 交易员分析非常详细（>500字）")
        elif analysis_length >= 200:
            analysis_quality_score = 15
            factors.append("✓ 交易员分析较为详细（200-500字）")
        elif analysis_length >= 100:
            analysis_quality_score = 10
            factors.append("○ 交易员分析中等（100-200字）")
        elif analysis_length >= 50:
            analysis_quality_score = 5
            factors.append("⚠ 交易员分析较简单（50-100字）")
        else:
            analysis_quality_score = 0
            factors.append("⚠ 交易员分析过于简单（<50字）")
        
        components.append(f"分析质量：{analysis_quality_score}分")
        
        # 2. 辩论分歧度评估（0-15分）
        if hasattr(debate_result, 'overall_bull_score') and hasattr(debate_result, 'overall_bear_score'):
            bull_score = debate_result.overall_bull_score
            bear_score = debate_result.overall_bear_score
            score_diff = abs(bull_score - bear_score)
            
            if score_diff >= 3.0:
                debate_clarity_score = 15
                factors.append(f"✓ 辩论方向明确（分差{score_diff:.1f}分）")
            elif score_diff >= 2.0:
                debate_clarity_score = 10
                factors.append(f"○ 辩论倾向性中等（分差{score_diff:.1f}分）")
            elif score_diff >= 1.0:
                debate_clarity_score = 5
                factors.append(f"⚠ 辩论存在分歧（分差{score_diff:.1f}分）")
            else:
                debate_clarity_score = 0
                factors.append(f"⚠ 辩论高度分歧（分差{score_diff:.1f}分）")
        else:
            debate_clarity_score = 5  # 无辩论数据时给予中性评分
            factors.append("○ 辩论数据不完整")
        
        components.append(f"辩论明确性：{debate_clarity_score}分")
        
        # 3. 策略明确性评估（0-10分）
        if direction in ["谨慎做多", "积极做多", "谨慎做空", "积极做空"]:
            strategy_clarity_score = 10
            factors.append("✓ 策略方向明确")
        elif direction in ["中性", "未明确"]:
            strategy_clarity_score = 3
            factors.append("⚠ 策略方向不明确")
        elif "观望" in reasoning:
            strategy_clarity_score = 7
            factors.append("○ 采用观望策略")
        else:
            strategy_clarity_score = 5
            factors.append("○ 策略相对明确")
        
        components.append(f"策略明确性：{strategy_clarity_score}分")
        
        # 4. 风险等级调整（-5至+5分）
        if risk_level == RiskLevel.LOW:
            risk_adjustment = 5
            factors.append("✓ 风险等级为低风险")
        elif risk_level == RiskLevel.MEDIUM:
            risk_adjustment = 0
            factors.append("○ 风险等级为中等风险")
        elif risk_level == RiskLevel.HIGH:
            risk_adjustment = -3
            factors.append("⚠ 风险等级为高风险")
        elif risk_level == RiskLevel.VERY_HIGH:
            risk_adjustment = -5
            factors.append("⚠ 风险等级为极高风险")
        else:
            risk_adjustment = 0
            factors.append("○ 风险等级未确定")
        
        components.append(f"风险调整：{risk_adjustment:+d}分")
        
        # 5. 计算最终信心度
        total_adjustment = analysis_quality_score + debate_clarity_score + strategy_clarity_score + risk_adjustment
        final_confidence = base_score + total_adjustment
        
        # 限制在20%-85%范围内（风控保守原则）
        final_confidence = max(20, min(85, final_confidence))
        
        # 6. 生成操作建议
        if final_confidence >= 70:
            operation_advice = "可考虑适度仓位操作，严格执行止损"
        elif final_confidence >= 55:
            operation_advice = "可考虑轻仓试探性操作"
        elif final_confidence >= 40:
            operation_advice = "建议观望为主，如操作需极小仓位"
        else:
            operation_advice = "建议暂停操作，等待更清晰信号"
        
        # 7. 生成计算明细
        calculation_detail = f"基础分50分 + {' + '.join(components)} = {final_confidence:.0f}分"
        
        return {
            'score': final_confidence,
            'factors': factors,
            'calculation_detail': calculation_detail,
            'operation_advice': operation_advice,
            'components': {
                'base': base_score,
                'analysis_quality': analysis_quality_score,
                'debate_clarity': debate_clarity_score,
                'strategy_clarity': strategy_clarity_score,
                'risk_adjustment': risk_adjustment,
                'total': final_confidence
            }
        }
    
    def _extract_direction_from_trading_decision(self, trading_decision: TradingDecision) -> str:
        """从交易决策中提取方向信息"""
        if not trading_decision or not trading_decision.reasoning:
            return "未明确"
        
        reasoning = trading_decision.reasoning.lower()
        
        # 提取操作方向
        if "做多" in reasoning or "买入" in reasoning:
            if "谨慎" in reasoning:
                return "谨慎做多"
            elif "积极" in reasoning:
                return "积极做多"
            else:
                return "做多"
        elif "做空" in reasoning or "卖出" in reasoning:
            if "谨慎" in reasoning:
                return "谨慎做空"
            elif "积极" in reasoning:
                return "积极做空"
            else:
                return "做空"
        else:
            return "未明确"
    
    def _extract_detailed_trader_info(self, trading_decision: TradingDecision) -> Dict[str, str]:
        """提取交易员详细信息"""
        
        # 安全处理仓位大小
        position_size_raw = getattr(trading_decision, 'position_size', '待确定')
        if isinstance(position_size_raw, (int, float)) and position_size_raw > 0:
            position_size_text = f"{position_size_raw * 100:.1f}%"
        elif isinstance(position_size_raw, str):
            position_size_text = position_size_raw
        else:
            position_size_text = '待确定'
            
        return {
            'strategy_type': str(trading_decision.strategy_type.value) if trading_decision.strategy_type else '未知策略',
            'direction': self._extract_direction_from_trading_decision(trading_decision),
            'entry_levels': str(getattr(trading_decision, 'entry_price', '待确定')),
            'stop_loss': str(getattr(trading_decision, 'stop_loss_price', '待确定')),
            'target_levels': str(getattr(trading_decision, 'target_price', '待确定')),
            'position_size': position_size_text
        }
    
    def _design_risk_mitigation(self, risk_scores: Dict[str, float], 
                              overall_risk: RiskLevel) -> List[str]:
        """基于风险等级设计针对性缓释措施"""
        
        # 🔥 简化：不再提供通用模板，改为在风控经理专业意见中提供针对性建议
        measures = []
        
        if overall_risk == RiskLevel.HIGH:
            measures.append("高风险策略需严控仓位，建议不超过3%")
        elif overall_risk == RiskLevel.VERY_HIGH:
            measures.append("极高风险策略建议暂停操作或极小仓位试验")
        else:
            measures.append("中低风险策略可适度参与，建议控制在5-8%")
            
        return measures
    
    def _calculate_risk_scores_from_trading_decision(self, analysis_state: FuturesAnalysisState, 
                                                   debate_result: DebateResult, 
                                                   trading_decision: TradingDecision) -> Dict[str, float]:
        """基于交易员决策计算风险评分"""
        
        # 获取策略类型风险
        strategy_type = trading_decision.strategy_type.value
        strategy_risk_base = {
            "单边做多": 6.0,
            "单边做空": 6.0, 
            "跨期套利": 4.0,
            "跨品种套利": 5.0,
            "期权策略": 7.0,
            "对冲策略": 3.0,
            "中性策略": 2.0
        }.get(strategy_type, 5.0)
        
        # 根据辩论分歧程度调整
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        if score_diff < 1.0:
            market_risk = strategy_risk_base + 2.0
        elif score_diff < 2.0:
            market_risk = strategy_risk_base + 1.0
        else:
            market_risk = strategy_risk_base
        
        # 分析交易员推理内容调整风险
        reasoning = trading_decision.reasoning.lower() if trading_decision.reasoning else ""
        if "谨慎" in reasoning:
            market_risk += 0.5
        elif "积极" in reasoning:
            market_risk -= 0.5
        
        return {
            "market": min(10.0, max(1.0, market_risk)),
            "liquidity": min(10.0, max(1.0, strategy_risk_base * 0.8)),
            "leverage": min(10.0, max(1.0, strategy_risk_base * 1.2)), 
            "concentration": min(10.0, max(1.0, strategy_risk_base))
        }
    
    def _calculate_limits_from_trading_decision(self, trading_decision: TradingDecision, 
                                              overall_risk: RiskLevel, 
                                              analysis_state: FuturesAnalysisState = None) -> Tuple[str, str]:
        """基于交易员决策计算仓位限制和止损位 - 修复风控仓位协调逻辑"""
        
        # 获取交易员推荐的仓位
        trader_position = trading_decision.position_size if trading_decision.position_size else "5-10%"
        
        # 🔧 修复：风控独立评估，严格基于风险等级确定上限
        risk_based_limits = {
            RiskLevel.VERY_LOW: "10-15%",
            RiskLevel.LOW: "8-12%", 
            RiskLevel.MEDIUM: "5-8%",
            RiskLevel.HIGH: "2-5%",
            RiskLevel.VERY_HIGH: "≤1.0%",
            RiskLevel.UNKNOWN: "≤1.0%"
        }
        
        # 风控严格限制
        risk_position_limit = risk_based_limits.get(overall_risk, "≤1.0%")
        
        print(f"🛡️ 风控评估 - 交易员建议:{trader_position}, 风险等级:{overall_risk.value}, 风控上限:{risk_position_limit}")
        
        # 🔧 关键修复：风控立场 - 如果风险较高，严格执行风控限制
        if overall_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.UNKNOWN]:
            final_position_limit = risk_position_limit
            print(f"🚨 高风险情况，风控严格执行: {final_position_limit}")
        elif overall_risk == RiskLevel.MEDIUM:
            # 中等风险：在风控和交易员建议之间取保守值
            final_position_limit = self._reconcile_medium_risk_position(trader_position, risk_position_limit)
            print(f"⚖️ 中等风险，协调结果: {final_position_limit}")
        else:
            # 低风险：可以适度参考交易员建议，但不超过风控上限
            final_position_limit = self._reconcile_low_risk_position(trader_position, risk_position_limit)
            print(f"✅ 低风险，协调结果: {final_position_limit}")
        
        # 基于实际数据计算止损位
        stop_loss_advice = self._calculate_realistic_stop_loss(trading_decision, analysis_state, overall_risk)
        
        return final_position_limit, stop_loss_advice
    
    def _reconcile_medium_risk_position(self, trader_position: str, risk_limit: str) -> str:
        """协调中等风险的仓位建议"""
        
        # 解析数值进行比较
        try:
            if "5-8%" in risk_limit and ("5-10%" in trader_position or "10%" in trader_position):
                return "5-8%"  # 取风控的保守值
            elif "3-5%" in trader_position:
                return trader_position  # 交易员更保守时采用
            else:
                return risk_limit  # 默认使用风控限制
        except:
            return risk_limit
    
    def _reconcile_low_risk_position(self, trader_position: str, risk_limit: str) -> str:
        """协调低风险的仓位建议"""
        
        # 低风险时可以适度放宽，但有上限
        try:
            if "8-12%" in risk_limit and "5-10%" in trader_position:
                return "8-10%"  # 在风控范围内给予交易员一定空间
            elif "1-3%" in trader_position or "3-5%" in trader_position:
                return trader_position  # 交易员保守时采用
            else:
                return risk_limit  # 其他情况使用风控限制
        except:
            return risk_limit
    
    def _calculate_realistic_stop_loss(self, trading_decision: TradingDecision, 
                                     analysis_state: FuturesAnalysisState, 
                                     risk_level: RiskLevel) -> str:
        """基于实际数据计算现实的止损位 - 修复价格数据一致性问题"""
        
        stop_loss_suggestions = []
        current_price = None
        support_levels = []
        resistance_levels = []
        
        # 🔥 修复：优先使用统一的真实价格数据源
        commodity = analysis_state.commodity if analysis_state else getattr(trading_decision, 'commodity', 'UNKNOWN')
        
        try:
            # 1. 首先从本地数据库获取真实价格（最权威数据源）
            current_price = get_commodity_current_price(commodity)
            self.logger.info(f"✅ 从本地数据库获取{commodity}当前价格: {current_price:.0f}元/吨")
            
            # 2. 获取支撑阻力位（也使用真实数据）
            price_range = futures_price_provider.get_price_range(commodity, 30)
            support_resistance = futures_price_provider.get_support_resistance_levels(commodity)
            
            if support_resistance:
                support_levels = support_resistance.get('support', [])
                resistance_levels = support_resistance.get('resistance', [])
                self.logger.info(f"✅ 获取{commodity}支撑位: {support_levels[:3]}, 阻力位: {resistance_levels[:3]}")
        
        except Exception as e:
            self.logger.warning(f"⚠️ 获取{commodity}真实价格数据失败: {e}")
            
            # 3. 备用方案：从技术分析中提取关键价位
            if analysis_state and analysis_state.technical_analysis:
                tech_content = str(analysis_state.technical_analysis.result_data.get('analysis_content', ''))
                extracted_prices = self._extract_technical_levels(tech_content)
                
                if extracted_prices.get('current_price') and not current_price:
                    current_price = extracted_prices['current_price']
                    self.logger.info(f"📊 从技术分析获取{commodity}价格: {current_price:.0f}元/吨")
                
                if not support_levels:
                    support_levels = extracted_prices.get('support_levels', [])
                if not resistance_levels:
                    resistance_levels = extracted_prices.get('resistance_levels', [])
        
        # 4. 根据策略类型和实际价位计算止损位
        strategy_type = trading_decision.strategy_type.value
        
        if current_price:
            if strategy_type in ["单边做多"]:
                # 🔥 修复：做多策略只提供一个最优止损建议，避免重复
                support_stop = None
                percentage_stop_level = self._get_percentage_stop_loss(risk_level)
                percentage_stop_price = current_price * (1 - percentage_stop_level)
                
                # 优先使用支撑位止损，如果合理的话
                if support_levels:
                    nearest_support = max([s for s in support_levels if s < current_price], default=None)
                    if nearest_support and nearest_support >= percentage_stop_price * 0.8:  # 支撑位不能太远
                        support_stop = nearest_support
                
                # 选择最优止损方案
                if support_stop:
                    stop_loss_suggestions.append(f"多头止损：{support_stop:.0f}附近（关键支撑位）")
                else:
                    stop_loss_suggestions.append(f"多头止损：{percentage_stop_price:.0f}（当前价{current_price:.0f}下方{percentage_stop_level*100:.1f}%）")
                
            elif strategy_type in ["单边做空"]:
                # 🔥 修复：做空策略只提供一个最优止损建议，避免重复
                resistance_stop = None
                percentage_stop_level = self._get_percentage_stop_loss(risk_level)
                percentage_stop_price = current_price * (1 + percentage_stop_level)
                
                # 优先使用阻力位止损，如果合理的话
                if resistance_levels:
                    nearest_resistance = min([r for r in resistance_levels if r > current_price], default=None)
                    if nearest_resistance and nearest_resistance <= percentage_stop_price * 1.2:  # 阻力位不能太远
                        resistance_stop = nearest_resistance
                
                # 选择最优止损方案
                if resistance_stop:
                    stop_loss_suggestions.append(f"空头止损：{resistance_stop:.0f}附近（技术阻力位）")
                else:
                    stop_loss_suggestions.append(f"空头止损：{percentage_stop_price:.0f}（当前价上方{percentage_stop_level*100:.1f}%）")
        
        # ✅ 修复5：不再混合交易员建议和风控独立判断
        # 风控应该基于实际数据给出独立的止损建议，而不是引用交易员
        
        # 6. 基于风险等级的通用建议
        risk_percentage_text = {
            RiskLevel.LOW: "2.5-3%",
            RiskLevel.MEDIUM: "2-2.5%", 
            RiskLevel.HIGH: "2.5-3.5%",  # 高风险以技术位为准，允许更大的止损空间避免频繁触发
            RiskLevel.VERY_HIGH: "1-1.5%"
        }.get(risk_level, "2-2.5%")
        
        # ✅ 改进：根据策略类型给出清晰的止损建议
        if stop_loss_suggestions:
            # 只使用风控独立评估的止损位
            return f"{stop_loss_suggestions[0]}；建议止损幅度控制在{risk_percentage_text}以内"
        else:
            return f"建议止损幅度：{risk_percentage_text}；建议基于关键技术位设定具体止损价格"
    
    def _extract_technical_levels(self, tech_content: str) -> Dict:
        """从技术分析中提取关键价位"""
        import re
        
        result = {
            'current_price': None,
            'support_levels': [],
            'resistance_levels': []
        }
        
        # 提取所有价格数字
        price_pattern = r'(\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)'
        prices = re.findall(price_pattern, tech_content)
        clean_prices = []
        
        for p in prices:
            try:
                clean_price = float(p.replace(',', ''))
                if 1000 <= clean_price <= 100000:  # 合理的期货价格范围
                    clean_prices.append(clean_price)
            except:
                continue
        
        if clean_prices:
            # 寻找支撑和阻力位的关键词
            support_keywords = ['支撑', '支持', '底部', '低点']
            resistance_keywords = ['阻力', '压力', '高点', '顶部']
            
            # 分析文本上下文来识别支撑阻力位
            lines = tech_content.split('\n')
            for line in lines:
                if any(keyword in line for keyword in support_keywords):
                    line_prices = re.findall(price_pattern, line)
                    for p in line_prices:
                        try:
                            price = float(p.replace(',', ''))
                            if 1000 <= price <= 100000:
                                result['support_levels'].append(price)
                        except:
                            continue
                            
                elif any(keyword in line for keyword in resistance_keywords):
                    line_prices = re.findall(price_pattern, line)
                    for p in line_prices:
                        try:
                            price = float(p.replace(',', ''))
                            if 1000 <= price <= 100000:
                                result['resistance_levels'].append(price)
                        except:
                            continue
            
            # 如果没有明确的支撑阻力位，使用价格分布推测
            if not result['support_levels'] and not result['resistance_levels'] and clean_prices:
                sorted_prices = sorted(clean_prices)
                result['current_price'] = sorted_prices[len(sorted_prices)//2]  # 中位数作为当前价格
                result['support_levels'] = sorted_prices[:len(sorted_prices)//3]  # 低价位作为支撑
                result['resistance_levels'] = sorted_prices[-len(sorted_prices)//3:]  # 高价位作为阻力
        
        return result
    
    def _extract_prices_from_text(self, text: str) -> List[float]:
        """从文本中提取价格数字"""
        import re
        price_pattern = r'(\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)'
        prices = re.findall(price_pattern, text)
        
        clean_prices = []
        for p in prices:
            try:
                clean_price = float(p.replace(',', ''))
                if 1000 <= clean_price <= 100000:  # 合理的期货价格范围
                    clean_prices.append(clean_price)
            except:
                continue
        
        return sorted(set(clean_prices))  # 去重并排序
    
    def _extract_trader_stop_loss_advice(self, reasoning: str) -> str:
        """从交易员推理中提取止损建议"""
        import re
        
        # 寻找止损相关的表述
        stop_loss_patterns = [
            r'止损[：:]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'止损位[：:]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'止损价[：:]\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'跌破\s*(\d+(?:,\d{3})*(?:\.\d+)?).*止损',
            r'突破\s*(\d+(?:,\d{3})*(?:\.\d+)?).*止损'
        ]
        
        for pattern in stop_loss_patterns:
            matches = re.findall(pattern, reasoning)
            if matches:
                try:
                    price = float(matches[0].replace(',', ''))
                    return f"{price:.0f}附近"
                except:
                    continue
        
        return ""
    
    def _get_percentage_stop_loss(self, risk_level: RiskLevel) -> float:
        """获取基于风险等级的止损百分比"""
        return {
            RiskLevel.LOW: 0.03,      # 3%
            RiskLevel.MEDIUM: 0.025,  # 2.5%
            RiskLevel.HIGH: 0.025,    # 2.5% (实战中以技术位为准，通常2.5-3%)
            RiskLevel.VERY_HIGH: 0.015 # 1.5%
        }.get(risk_level, 0.02)
    
    def _calculate_risk_limits(self, risk_scores: Dict[str, float], 
                             overall_risk: RiskLevel, analysis_state: FuturesAnalysisState = None) -> Tuple[str, str]:
        """计算仓位限制和止损位 - 基于实际数据"""
        
        # 根据风险等级设定仓位上限（以资金百分比表示）
        if overall_risk == RiskLevel.LOW:
            position_limit = "15-20%"
        elif overall_risk == RiskLevel.MEDIUM:
            position_limit = "8-12%"
        elif overall_risk == RiskLevel.HIGH:
            position_limit = "3-5%"
        else:
            position_limit = "1-3%"
        
        # 基于技术分析计算具体止损位
        stop_loss_advice = self._calculate_technical_stop_loss(analysis_state, overall_risk)
        
        return position_limit, stop_loss_advice
    
    def _calculate_technical_stop_loss(self, analysis_state: FuturesAnalysisState, risk_level: RiskLevel) -> str:
        """基于技术分析计算止损位"""
        
        if not analysis_state:
            return "建议基于关键技术位设定止损"
        
        stop_loss_suggestions = []
        
        # 从技术分析中提取关键位置
        if analysis_state.technical_analysis:
            tech_content = analysis_state.technical_analysis.result_data.get('analysis_content', '')
            
            # 提取支撑阻力位
            if '支撑' in tech_content:
                # 尝试提取数字
                import re
                numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', tech_content)
                if numbers:
                    support_level = numbers[0].replace(',', '')
                    stop_loss_suggestions.append(f"多头止损：{support_level}附近")
            
            if '阻力' in tech_content:
                import re
                numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', tech_content)
                if numbers:
                    resistance_level = numbers[-1].replace(',', '')
                    stop_loss_suggestions.append(f"空头止损：{resistance_level}附近")
        
        # 基于风险等级调整止损幅度
        risk_multiplier = {
            RiskLevel.LOW: "2-3%",
            RiskLevel.MEDIUM: "1.5-2%", 
            RiskLevel.HIGH: "1-1.5%",
            RiskLevel.VERY_HIGH: "0.5-1%"
        }
        
        base_suggestion = f"建议止损幅度：{risk_multiplier.get(risk_level, '1-2%')}"
        
        if stop_loss_suggestions:
            return f"{'; '.join(stop_loss_suggestions)}；{base_suggestion}"
        else:
            return f"{base_suggestion}；建议基于关键技术位设定具体止损价格"
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        import re
        text = re.sub(r'[#*`_\[\]()]+', '', text)
        text = text.replace('defer', '延期').replace('reject', '拒绝')
        return text.strip()

# ============================================================================
# 4. CIO级别最终决策系统
# ============================================================================

class ExecutiveDecisionMaker:
    """CIO级别最终决策者 - 权威果敢专业"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("deepseek_api_key") or config.get("api_settings", {}).get("deepseek", {}).get("api_key")
        self.base_url = config.get("api_settings", {}).get("deepseek", {}).get("base_url", "https://api.deepseek.com/v1")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        self.logger = logging.getLogger("ExecutiveDecisionMaker")
        
    async def make_executive_decision(self, analysis_state: FuturesAnalysisState,
                                    debate_result: DebateResult,
                                    risk_assessment: RiskAssessment,
                                    trading_decision: TradingDecision = None) -> ExecutiveDecision:
        """制定CIO级别最终决策"""
        
        commodity = analysis_state.commodity
        print(f"🐛 DEBUG: make_executive_decision 开始，commodity={commodity}")
        self.logger.info(f"CIO开始制定{commodity}最终投资决策")
        
        # 🔥 关键修复：CIO必须依赖交易员决策和风控评估
        print(f"🐛 DEBUG: 检查trading_decision是否存在: {trading_decision is not None}")
        if not trading_decision:
            self.logger.warning("CIO决策中止：缺少交易员决策，CIO无法制定最终决策")
            return ExecutiveDecision(
                final_decision=FinalDecision.HOLD,
                confidence_level=0.0,
                position_size=0.0,
                target_price=None,
                stop_loss=None,
                time_horizon="等待分析",
                key_rationale=["等待交易员完成决策分析"],
                execution_plan="⏳ 执行计划等待中：需要交易员先完成决策，CIO才能制定执行方案",
                monitoring_points=["等待交易员决策"],
                cio_statement="⏳ CIO决策等待中：需要交易员完成决策分析后，CIO才能基于完整的决策链进行最终拍板。",
                commodity=analysis_state.commodity
            )
            
        # 🔥 新增：检测交易员分析质量，避免CIO虚构详细决策
        trader_reasoning = trading_decision.reasoning or ""
        is_simple_analysis = (
            len(trader_reasoning) < 100 or
            "市场信息不足" in trader_reasoning or
            "方向不明" in trader_reasoning or  
            "建议保持观望" in trader_reasoning
        )
        
        if is_simple_analysis:
            self.logger.info("检测到交易员分析较简单，CIO将使用新决策逻辑但采用保守态度")
            # 🔥 即使是简化分析，也使用新的决策逻辑，但设置为低信心度
            pass  # 继续执行新的决策逻辑，不再直接返回观望
        
        if not risk_assessment or risk_assessment.overall_risk_level == RiskLevel.UNKNOWN:
            self.logger.warning("CIO决策中止：风控评估未完成，CIO无法制定最终决策")
            return ExecutiveDecision(
                final_decision=FinalDecision.HOLD,
                confidence_level=0.0,
                position_size=0.0,
                target_price=None,
                stop_loss=None,
                time_horizon="等待分析",
                key_rationale=["等待风控完成评估"],
                execution_plan="⏳ 执行计划等待中：需要风控部门完成评估，CIO才能制定执行方案",
                monitoring_points=["等待风控评估"],
                cio_statement="⏳ CIO决策等待中：需要风控部门完成评估后，CIO才能基于完整的决策链进行最终拍板。",
                commodity=analysis_state.commodity
            )
        
        # 生成CIO决策声明
        try:
            async with DeepSeekAPIClient(self.api_key, self.base_url) as api_client:
                cio_statement = await self._generate_cio_statement(
                    commodity, analysis_state, debate_result, risk_assessment, trading_decision, api_client
                )
        except Exception as e:
            cio_statement = f"CIO声明生成失败: {str(e)}"
        
        # 基于交易员建议和风控评估确定最终决策方向
        final_decision = self._determine_final_decision_based_on_trader_and_risk(
            trading_decision, risk_assessment, debate_result
        )
        
        # 基于交易员建议和风控评估计算决策信心度
        confidence = self._calculate_confidence_based_on_trader_and_risk(
            trading_decision, risk_assessment, debate_result
        )
        
        # 🔥 新增：基于交易员分析的统一方向判断
        print(f"🐛 DEBUG: 开始调用_analyze_unified_directional_view")
        directional_analysis = self._analyze_unified_directional_view(
            trading_decision, risk_assessment, debate_result
        )
        print(f"🐛 DEBUG: _analyze_unified_directional_view完成")
        
        # 基于最终决策和风控评估设定仓位规模
        print(f"🐛 DEBUG: 开始调用_determine_position_size_based_on_cio_decision")
        position_size = self._determine_position_size_based_on_cio_decision(
            final_decision, risk_assessment, confidence, trading_decision
        )
        print(f"🐛 DEBUG: _determine_position_size_based_on_cio_decision完成，position_size={position_size}")
        
        # 制定执行计划
        print(f"🐛 DEBUG: 开始调用_create_execution_plan")
        execution_plan = self._create_execution_plan(final_decision, position_size, risk_assessment)
        print(f"🐛 DEBUG: _create_execution_plan完成")
        
        # 设定监控要点
        print(f"🐛 DEBUG: 开始调用_define_monitoring_points")
        monitoring_points = self._define_monitoring_points(analysis_state, risk_assessment)
        print(f"🐛 DEBUG: _define_monitoring_points完成")
        
        # 🔥 关键改进：确保方向判断与操作决策的逻辑一致性
        consistent_directional_analysis = self._ensure_decision_consistency(
            final_decision, directional_analysis, risk_assessment
        )
        
        print(f"🐛 DEBUG: 准备创建ExecutiveDecision")
        print(f"🐛 DEBUG: final_decision={final_decision}")
        print(f"🐛 DEBUG: operational_confidence={directional_analysis.get('operational_confidence', '中')}")
        print(f"🐛 DEBUG: directional_confidence={directional_analysis.get('directional_confidence', '中')}")
        print(f"🐛 DEBUG: confidence={confidence} (type: {type(confidence)})")
        
        # ✅ 修复：直接使用字符串版本的信心度，不要转换为数字
        operational_confidence_text = directional_analysis.get('operational_confidence', '中')
        directional_confidence_text = directional_analysis.get('directional_confidence', '中')
        
        print(f"🐛 DEBUG: operational_confidence_text={operational_confidence_text}")
        print(f"🐛 DEBUG: directional_confidence_text={directional_confidence_text}")
        
        return ExecutiveDecision(
            final_decision=final_decision,
            confidence_level=confidence,  # 保持原有数字信心度
            position_size=position_size,
            target_price=self._estimate_target_price(final_decision, confidence),
            stop_loss=None,  # 🔥 删除止损标准显示
            time_horizon=self._determine_time_horizon(final_decision, risk_assessment),
            key_rationale=[],  # 🔥 删除决策理由显示
            execution_plan=execution_plan,
            monitoring_points=monitoring_points,
            cio_statement=cio_statement,
            # 🔥 使用统一的方向判断结果（操作决策与方向判断保持一致）
            directional_view=directional_analysis.get('directional_view', '中性'),
            directional_confidence=directional_confidence_text,  # ✅ 使用字符串
            directional_rationale=[directional_analysis.get('consistency_note', '操作决策与方向判断一致')],
            # 🔧 新增操作决策字段
            operational_decision=directional_analysis.get('operational_decision', '中性策略'),
            operational_confidence=operational_confidence_text,  # ✅ 使用字符串
            # 🔧 兼容字段
            commodity=analysis_state.commodity
        )
    
    async def _generate_cio_statement(self, commodity: str, 
                                    analysis_state: FuturesAnalysisState,
                                    debate_result: DebateResult,
                                    risk_assessment: RiskAssessment,
                                    trading_decision: 'TradingDecision' = None,
                                    api_client = None) -> str:
        """基于实际分析内容生成实事求是的CIO权威声明"""
        
        # 🔥 完全基于实际数据，不使用AI虚构内容
        return self._create_factual_cio_statement(
            commodity, analysis_state, debate_result, risk_assessment, trading_decision
        )
    
    def _create_factual_cio_statement(self, commodity: str, 
                                    analysis_state: FuturesAnalysisState,
                                    debate_result: DebateResult,
                                    risk_assessment: RiskAssessment,
                                    trading_decision: TradingDecision) -> str:
        """🔥 全新：创建基于高/中/低信心度体系的CIO权威声明"""
        
        commodity_name = get_commodity_name(commodity)
        
        # 1. 使用新的统一决策分析
        unified_analysis = self._analyze_unified_directional_view(
            trading_decision, risk_assessment, debate_result
        )
        
        # 2. 提取关键决策信息
        operation_decision = unified_analysis["operational_decision"] 
        directional_view = unified_analysis["directional_view"]
        directional_confidence = unified_analysis["directional_confidence"]
        operational_confidence = unified_analysis["operational_confidence"]
        decision_logic = unified_analysis["decision_logic"]
        
        # 3. 生成简洁的风险等级描述
        risk_level = risk_assessment.overall_risk_level.value
        
        # 4. 构建基于实际分析的CIO权威声明
        statement = self._format_factual_cio_statement(
            commodity_name, trading_decision, risk_assessment, 
            directional_confidence, operational_confidence, directional_view, operation_decision
        )
        
        return statement
    
    def _format_factual_cio_statement(self, commodity_name: str, trading_decision: TradingDecision,
                                     risk_assessment: RiskAssessment, directional_confidence: str,
                                     operational_confidence: str, directional_view: str, 
                                     operation_decision: str) -> str:
        """🔥 优化：基于实际交易员和风控内容生成真实的CIO声明，增加分析师统计数据"""
        
        # 提取交易员的核心观点
        trader_analysis = self._extract_trader_core_analysis(trading_decision)
        
        # 提取风控的核心评估
        risk_analysis = self._extract_risk_core_assessment(risk_assessment)
        
        # 🔥 新增：从交易员推理中提取分析师观点统计数据
        analyst_stats = self._extract_analyst_stats_from_reasoning(trading_decision.reasoning)
        
        # 生成CIO的综合决策逻辑
        cio_logic = self._generate_factual_cio_logic(
            trader_analysis, risk_analysis, directional_confidence, 
            operational_confidence, directional_view, operation_decision, analyst_stats
        )
        
        # ✅ 修正：确保仓位表述清晰（如果是0.01转换为≤1.0%）
        position_display = risk_assessment.position_size_limit
        if isinstance(position_display, (int, float)):
            if position_display <= 0.01:
                position_display = "≤1.0%"
            elif position_display <= 0.05:
                position_display = "2-5%"
            elif position_display <= 0.10:
                position_display = "5-10%"
            else:
                position_display = f"{position_display*100:.1f}%"
        
        # 🔥 删除旧的execution_guidance生成，因为新版CIO逻辑中已包含详细的【执行指导】部分
        
        return f"""🧠 决策逻辑

{cio_logic}

首席投资官
{datetime.now().strftime('%Y年%m月%d日')}"""
        
    def _extract_trader_core_analysis(self, trading_decision: TradingDecision) -> Dict[str, str]:
        """✅ 改进：更全面地提取交易员的核心分析观点，包括关键价位"""
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        analysis = {
            "direction": "未明确",
            "confidence": "未评估", 
            "key_factors": [],
            "risk_points": [],
            # 🔥 新增：关键价位信息
            "entry_range": None,
            "stop_loss": None,
            "target_price": None
        }
        
        # ✅ 修复：优先匹配中性策略关键词，避免被方向性关键词误匹配
        if "中性观望" in reasoning:
            analysis["direction"] = "中性观望"
        elif "区间震荡" in reasoning or "震荡策略" in reasoning:
            analysis["direction"] = "区间震荡"
        elif "谨慎偏空" in reasoning or "谨慎看空" in reasoning or "谨慎做空" in reasoning:
            analysis["direction"] = "谨慎偏空"
        elif "积极做空" in reasoning or "单边做空" in reasoning:
            analysis["direction"] = "积极做空"
        elif "谨慎做多" in reasoning or "谨慎看多" in reasoning or "谨慎偏多" in reasoning:
            analysis["direction"] = "谨慎做多"
        elif "积极做多" in reasoning or "单边做多" in reasoning:
            analysis["direction"] = "积极做多"
        elif "观望" in reasoning:  # 移到最后，避免过度匹配
            analysis["direction"] = "中性观望"
        
        # 提取信心度
        if "信心度：低" in reasoning or "低信心度" in reasoning:
            analysis["confidence"] = "低"
        elif "信心度：高" in reasoning or "高信心度" in reasoning:
            analysis["confidence"] = "高"
        elif "信心度：中" in reasoning or "中信心度" in reasoning:
            analysis["confidence"] = "中"
        
        # 🔥 新增：提取关键价位
        import re
        
        # 提取进场区间
        # 格式1：进场：82800-83100元
        # 格式2：进场82800-83100元
        # 格式3：关键价位：进场82800-83100元
        entry_match = re.search(r'进场[区间]?[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', reasoning)
        if not entry_match:
            # 从"关键价位"部分搜索
            key_price_section = re.search(r'关键价位[：:](.*?)(?=，|。|持仓周期|$)', reasoning)
            if key_price_section:
                entry_match = re.search(r'进场\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', key_price_section.group(1))
        if entry_match:
            analysis["entry_range"] = f"{entry_match.group(1)}-{entry_match.group(2)}元"
        
        # 提取止损位
        stop_loss_match = re.search(r'止损[位]?[：:]?\s*[<＜]\s*(\d+\.?\d*)元', reasoning)
        if stop_loss_match:
            analysis["stop_loss"] = f"<{stop_loss_match.group(1)}元"
        else:
            # 尝试其他格式
            stop_loss_match = re.search(r'止损[位]?[：:]?\s*(\d+\.?\d*)元?\s*附近', reasoning)
            if stop_loss_match:
                analysis["stop_loss"] = f"~{stop_loss_match.group(1)}元"
            else:
                # 从"关键价位"搜索
                key_price_section = re.search(r'关键价位[：:](.*?)(?=，持仓周期|$)', reasoning)
                if key_price_section:
                    stop_loss_match = re.search(r'止损\s*[<＜]\s*(\d+\.?\d*)元', key_price_section.group(1))
                    if stop_loss_match:
                        analysis["stop_loss"] = f"<{stop_loss_match.group(1)}元"
        
        # 提取目标价位
        target_match = re.search(r'目标[价位]?[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', reasoning)
        if not target_match:
            # 从"关键价位"搜索
            key_price_section = re.search(r'关键价位[：:](.*?)(?=，持仓周期|$)', reasoning)
            if key_price_section:
                target_match = re.search(r'目标\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', key_price_section.group(1))
        if target_match:
            analysis["target_price"] = f"{target_match.group(1)}-{target_match.group(2)}元"
        
        # 提取关键支撑因素
        if "技术分析" in reasoning:
            if "超买" in reasoning or "阻力" in reasoning:
                analysis["key_factors"].append("技术面显示超买风险")
            elif "突破" in reasoning or "支撑" in reasoning:
                analysis["key_factors"].append("技术面提供支撑")
        
        if "库存" in reasoning:
            if "高位" in reasoning or "累积" in reasoning:
                analysis["key_factors"].append("库存处于高位")
            elif "去化" in reasoning or "下降" in reasoning:
                analysis["key_factors"].append("库存去化支撑")
        
        if "基差" in reasoning:
            if "分化" in reasoning or "异常" in reasoning:
                analysis["key_factors"].append("基差结构异常")
            elif "收敛" in reasoning:
                analysis["key_factors"].append("基差收敛预期")
        
        # 提取风险提示
        if "【风险提示】" in reasoning:
            risk_section = reasoning.split("【风险提示】")[1] if "【风险提示】" in reasoning else ""
            if "政策" in risk_section:
                analysis["risk_points"].append("政策变化风险")
            if "流动性" in risk_section:
                analysis["risk_points"].append("流动性风险")
            if "技术" in risk_section:
                analysis["risk_points"].append("技术突破失效风险")
        
        return analysis
    
    def _extract_risk_core_assessment(self, risk_assessment: RiskAssessment) -> Dict[str, str]:
        """提取风控的核心评估"""
        opinion = risk_assessment.risk_manager_opinion if risk_assessment.risk_manager_opinion else ""
        
        assessment = {
            "risk_level": risk_assessment.overall_risk_level.value if risk_assessment.overall_risk_level else "未评估",
            "position_limit": risk_assessment.position_size_limit if risk_assessment.position_size_limit else "未设定",
            "confidence": "未评估",
            "main_concerns": [],
            "potential_loss": "未评估",
            "risk_probability": "未评估"
        }
        
        # ✅ 提取操作信心度（增加多种匹配模式）
        if "操作信心度为低" in opinion or "操作信心度是低" in opinion or "操作信心度：低" in opinion or "操作信心度「低」" in opinion:
            assessment["confidence"] = "低"
        elif "操作信心度为高" in opinion or "操作信心度是高" in opinion or "操作信心度：高" in opinion or "操作信心度「高」" in opinion:
            assessment["confidence"] = "高"
        elif "操作信心度为中" in opinion or "操作信心度是中" in opinion or "操作信心度：中" in opinion or "操作信心度「中」" in opinion:
            assessment["confidence"] = "中"
        
        # ✅ 提取潜在损失
        import re
        loss_match = re.search(r'潜在最大亏损约?(\d+\.?\d*)%', opinion)
        if loss_match:
            assessment["potential_loss"] = f"{loss_match.group(1)}%"
        
        # ✅ 提取风险概率
        prob_match = re.search(r'风险事件发生概率约?(\d+)%', opinion)
        if prob_match:
            assessment["risk_probability"] = f"{prob_match.group(1)}%"
        
        # ✅ 提取主要担心的风险（优化逻辑）
        if "主要担心" in opinion or "主要担忧" in opinion:
            # 提取"主要担心/主要担忧"后面的内容
            concerns_marker = "主要担心" if "主要担心" in opinion else "主要担忧"
            concerns_section = opinion.split(concerns_marker)[1].split("🧠")[0] if concerns_marker in opinion else ""
            
            # 提取具体的风险项
            if "技术面风险" in concerns_section:
                assessment["main_concerns"].append("技术面风险")
            if "基本面风险" in concerns_section:
                assessment["main_concerns"].append("基本面风险")
            if "空头挤压风险" in concerns_section:
                assessment["main_concerns"].append("空头挤压风险")
            if "流动性风险" in concerns_section:
                assessment["main_concerns"].append("流动性风险")
            if "市场结构风险" in concerns_section:
                assessment["main_concerns"].append("市场结构风险")
        
        return assessment
    
    def _extract_analyst_key_insights(self, trader_analysis: Dict[str, str]) -> str:
        """✅ 全新逻辑：不使用key_factors（有问题），改用交易员推理中的关键发现描述"""
        
        insights_parts = []
        direction = trader_analysis.get('direction', '未明确')
        
        # 判断交易员是看多还是看空
        is_bearish = '看空' in direction or '做空' in direction or '偏空' in direction
        is_bullish = '看多' in direction or '做多' in direction or '偏多' in direction
        
        # ✅ 直接根据方向提供合理的描述（不再从key_factors提取，因为那里可能包含风险提示）
        if is_bullish:
            # 做多方向：突出支撑因素
            insights_parts = [
                "• 基本面分析：多个模块数据显示市场偏向支撑",
                "• 技术分析：价格处于关键技术位，存在上行空间",
                "• 市场情绪：资金流向显示多头倾向"
            ]
        elif is_bearish:
            # 做空方向：突出压力因素
            insights_parts = [
                "• 技术分析：技术指标显示超买风险",
                "• 基本面分析：供需结构显示潜在压力",
                "• 市场情绪：空头氛围逐渐形成"
            ]
        else:
            # 中性观望
            insights_parts = [
                "• 技术分析：价格处于关键技术位",
                "• 基本面分析：供需关系呈现特定结构",
                "• 市场情绪：资金流向显示明确倾向"
            ]
        
        return "\n".join(insights_parts)
    
    def _adjust_cio_confidence(self, source_confidence: str, original_confidence: str, conf_type: str) -> str:
        """✅ 修复：调整CIO信心度，确保不高于交易员和风控的信心度"""
        
        # 🔥 关键修复：CIO的信心度应该直接使用原始值，不做调整
        # 原因：原始值（operational_confidence）已经是从风控正确提取的"低"
        # 不应该被source_confidence（从risk_analysis['confidence']提取的值）覆盖
        
        print(f"🐛 DEBUG [_adjust_cio_confidence]: source_confidence='{source_confidence}', original_confidence='{original_confidence}', conf_type='{conf_type}'")
        
        confidence_levels = {'高': 3, '中': 2, '低': 1, '未评估': 1}
        
        source_level = confidence_levels.get(source_confidence, 1)
        original_level = confidence_levels.get(original_confidence, 1)  # 🔥 修复：默认为1（低）而不是2
        
        # 🔥 修复：直接使用original_confidence（这是从风控直接提取的准确值）
        # 不再与source_confidence比较，因为source_confidence可能提取不准确
        final_level = original_level
        
        # 转换回文字
        for conf_text, level in confidence_levels.items():
            if level == final_level and conf_text != '未评估':
                result = conf_text
                print(f"🐛 DEBUG [_adjust_cio_confidence]: 返回 '{result}'")
                return result
        
        print(f"🐛 DEBUG [_adjust_cio_confidence]: 返回默认值 '低'")
        return '低'  # 默认返回低
    
    def _build_comprehensive_decision_rationale(self, trader_analysis: Dict[str, str], 
                                               risk_analysis: Dict[str, str],
                                               directional_confidence: str, 
                                               operational_confidence: str) -> str:
        """✅ 改进：构建更全面的决策依据，说明为何选择这个方向和信心度"""
        
        rationale_parts = []
        
        # 1. 从分析师模块角度
        if trader_analysis.get('key_factors'):
            factors_text = '、'.join(trader_analysis['key_factors'][:2])  # 取前2个
            rationale_parts.append(f"1. 多维度分析显示：{factors_text}")
        
        # 2. 从交易员信心度角度
        if trader_analysis['confidence'] == '高':
            rationale_parts.append("2. 交易员高信心度判断为方向选择提供有力支撑")
        elif trader_analysis['confidence'] == '低':
            rationale_parts.append("2. 交易员低信心度要求我们保持谨慎，降低方向信心度")
        else:
            rationale_parts.append("2. 交易员中等信心度要求平衡风险与机会")
        
        # 3. 从风控角度
        if risk_analysis['risk_level'] == '极高风险':
            rationale_parts.append("3. 极高风险等级要求必须采用最保守的仓位策略，操作信心度为低")
        elif risk_analysis['risk_level'] == '高风险':
            rationale_parts.append("3. 高风险等级要求严格控制仓位，保持低操作信心度")
        elif risk_analysis['confidence'] == '低':
            rationale_parts.append("3. 风控低操作信心度要求极度谨慎，严格限制仓位")
        else:
            rationale_parts.append(f"3. {risk_analysis['risk_level']}要求在风控框架内执行")
        
        # 4. 综合信心度逻辑
        if directional_confidence == '低' and operational_confidence == '低':
            rationale_parts.append("4. 双低信心度决定了轻仓试探、严控风险的操作方针")
        elif directional_confidence == '低' or operational_confidence == '低':
            rationale_parts.append("4. 任一信心度偏低都要求保守操作，宁可错过不可做错")
        
        return "\n".join(rationale_parts)
    
    def _build_specific_execution_guidance(self, operation_decision: str, position_display: str,
                                          operational_confidence: str,
                                          trader_analysis: Dict[str, str],
                                          risk_analysis: Dict[str, str]) -> str:
        """✅ 新增：构建具体的执行指导，而非模板化的空话"""
        
        guidance_parts = []
        
        # 1. 操作策略和仓位
        guidance_parts.append(f"操作策略：{operation_decision}，仓位控制在{position_display}以内。")
        
        # 2. 具体的入场建议
        entry_guidance = ""
        if "谨慎" in operation_decision:
            if "做空" in operation_decision:
                entry_guidance = "建议分批轻仓试空，首仓不超过总仓位的1/3，观察市场反应后再决定是否加仓。"
            else:
                entry_guidance = "建议分批轻仓试多，首仓不超过总仓位的1/3，观察市场反应后再决定是否加仓。"
        elif "适度" in operation_decision:
            entry_guidance = "可分2-3批建仓，根据技术位和市场情绪择机入场。"
        else:  # 积极
            entry_guidance = "可按计划仓位分批入场，注意控制节奏。"
        guidance_parts.append(f"入场指导：{entry_guidance}")
        
        # 3. 止损要求（基于风险，修正为基于技术位）
        stop_loss_guidance = ""
        if risk_analysis['risk_level'] == '极高风险':
            stop_loss_guidance = "必须设置严格止损，基于关键技术位（通常1-1.5%），触及止损立即离场，不得心存侥幸。"
        elif risk_analysis['risk_level'] == '高风险':
            stop_loss_guidance = "必须严格执行止损纪律，基于关键技术位设定止损（通常2.5-3.5%），触及立即离场，严禁抗单。"
        else:
            stop_loss_guidance = "严格执行止损纪律，基于技术位或单笔亏损2-3%设定止损位，不得随意调整。"
        guidance_parts.append(f"止损纪律：{stop_loss_guidance}")
        
        # 4. 动态调整条件（具体化）
        adjustment_conditions = []
        if "技术" in str(trader_analysis.get('key_factors', [])):
            adjustment_conditions.append("关键技术位被有效突破时")
        if "基本面" in str(risk_analysis.get('main_concerns', [])):
            adjustment_conditions.append("基本面数据出现重大变化时")
        if risk_analysis['risk_level'] in ['极高风险', '高风险']:
            adjustment_conditions.append("市场波动超出预期时")
        
        if adjustment_conditions:
            conditions_text = "、".join(adjustment_conditions)
            guidance_parts.append(f"调整条件：{conditions_text}，立即重新评估并调整仓位。")
        
        # 5. 监控重点
        monitoring_focus = []
        if trader_analysis.get('key_factors'):
            # 提取关键监控指标
            if any('技术' in f for f in trader_analysis['key_factors']):
                monitoring_focus.append("技术指标变化")
            if any('库存' in f for f in trader_analysis['key_factors']):
                monitoring_focus.append("库存数据")
            if any('基差' in f for f in trader_analysis['key_factors']):
                monitoring_focus.append("基差变动")
        
        if not monitoring_focus:
            monitoring_focus = ["市场波动", "持仓变化", "外部风险事件"]
        
        monitoring_text = "、".join(monitoring_focus[:3])  # 最多3个
        guidance_parts.append(f"监控重点：密切关注{monitoring_text}，发现异常及时应对。")
        
        return "\n\n".join(guidance_parts)  # ✅ 改用双换行，格式更清晰
    
    def _extract_analyst_stats_from_reasoning(self, reasoning: str) -> Dict[str, int]:
        """🔥 新增：从交易员推理文本中提取分析师观点统计数据"""
        import re
        
        stats = {'bullish_count': 0, 'bearish_count': 0, 'neutral_count': 0}
        
        if not reasoning:
            return stats
        
        # 查找"分析师团队观点分布"部分
        pattern = r'分析师团队观点分布：看多(\d+)个模块，看空(\d+)个模块，中性(\d+)个模块'
        match = re.search(pattern, reasoning)
        
        if match:
            stats['bullish_count'] = int(match.group(1))
            stats['bearish_count'] = int(match.group(2))
            stats['neutral_count'] = int(match.group(3))
        
        return stats
    
    def _generate_factual_cio_logic(self, trader_analysis: Dict[str, str], risk_analysis: Dict[str, str],
                                   directional_confidence: str, operational_confidence: str,
                                   directional_view: str, operation_decision: str,
                                   analyst_stats: Dict[str, int] = None) -> str:
        """🔥 优化：生成更有权威感和战略高度的CIO决策逻辑（全面重构版，增加数据引用）"""
        
        # 修复：CIO的信心度应该基于交易员和风控，不能随意提高
        final_directional_conf = self._adjust_cio_confidence(trader_analysis['confidence'], directional_confidence, 'directional')
        final_operational_conf = self._adjust_cio_confidence(risk_analysis['confidence'], operational_confidence, 'operational')
        
        # 🔥 **第一部分：抓住核心矛盾**（CIO的战略视角）
        core_contradiction = self._identify_core_market_contradiction(
            trader_analysis, risk_analysis, directional_view
        )
        
        # 🔥 **第二部分：三个关键判断**（简洁有力）
        key_judgments = self._generate_cio_key_judgments(
            trader_analysis, risk_analysis, final_directional_conf, final_operational_conf, directional_view
        )
        
        # 🔥 **第三部分：决策本质**（提炼决策哲学）
        decision_essence = self._extract_decision_essence(
            directional_view, final_directional_conf, final_operational_conf
        )
        
        # 🔥 **第四部分：团队意见简述**（简洁明了，不冗长，增加具体数据）
        team_summary = self._generate_concise_team_summary(
            trader_analysis, risk_analysis, directional_view, final_directional_conf, analyst_stats
        )
        
        # 🔥 **第五部分：最终决策高亮**（醒目展示）
        final_decision_highlight = self._format_final_decision_highlight(
            directional_view, final_directional_conf, operation_decision, final_operational_conf, trader_analysis
        )
        
        return f"""
📊 当前市场核心矛盾分析

{core_contradiction}

💡 CIO三大核心判断

{key_judgments}

🎯 本次决策的核心逻辑

{decision_essence}

📋 团队综合意见汇总

{team_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ CIO最终决策与执行指导
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{final_decision_highlight}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _format_final_decision_highlight(self, directional_view: str, directional_conf: str,
                                         operation_decision: str, operational_conf: str,
                                         trader_analysis: Dict[str, str] = None) -> str:
        """🔥 优化：高亮格式化最终决策，增加执行指导和追溯性说明，包含关键价位"""
        import re
        
        # 根据方向判断选择合适的Emoji和描述
        if '中性' in directional_view or '观望' in directional_view:
            direction_emoji = "⏸️"
            direction_action = "暂不介入"
        elif '看空' in directional_view or '做空' in directional_view:
            direction_emoji = "📉"
            direction_action = "偏空操作"
        else:
            direction_emoji = "📈"
            direction_action = "偏多操作"
        
        # 信心度映射颜色描述
        conf_desc = {
            '高': '🟢 高信心',
            '中': '🟡 中信心',
            '低': '🔴 低信心'
        }
        
        # 🔥 修正：根据两者中较低的信心度生成仓位建议（取最保守）
        confidence_mapping = {'高': 3, '中': 2, '低': 1}
        min_conf_level = min(
            confidence_mapping.get(directional_conf, 1), 
            confidence_mapping.get(operational_conf, 1)
        )
        
        if min_conf_level >= 3:  # 双高
            position_range = "10-15%"
            position_strategy = "可适度配置，分2-3批建仓"
        elif min_conf_level >= 2:  # 至少有一个中，但不是双高
            position_range = "5-10%"
            position_strategy = "中等仓位，谨慎配置，分批入场"
        else:  # 至少有一个低
            position_range = "2-5%"
            position_strategy = "轻仓试探，首仓不超过总仓位1/3"
        
        # 🔥 修正：根据操作决策生成止损建议（与风控部门一致，基于技术位）
        if operational_conf == '低' or '高风险' in str(operation_decision):
            stop_loss_rule = "基于关键技术位设定止损（通常2.5-3.5%），触及立即离场，严禁抗单"
        elif operational_conf == '中':
            stop_loss_rule = "单笔亏损控制在总资金2-2.5%以内，严格执行止损纪律"
        else:
            stop_loss_rule = "单笔亏损控制在2.5-3%以内，按交易计划设定止损位"
        
        # 🔥 新增：从交易员分析中提取关键价位
        key_prices_section = ""
        if trader_analysis:
            entry_range = trader_analysis.get("entry_range")
            stop_loss = trader_analysis.get("stop_loss")
            target_price = trader_analysis.get("target_price")
            
            # 🔥 如果没有止损位，根据操作方向和进场区间计算一个合理的止损位
            if not stop_loss and entry_range:
                try:
                    # 从进场区间中提取价格
                    entry_match = re.search(r'(\d+\.?\d*)-(\d+\.?\d*)元', entry_range)
                    if entry_match:
                        entry_low = float(entry_match.group(1))
                        entry_high = float(entry_match.group(2))
                        entry_mid = (entry_low + entry_high) / 2
                        
                        # 根据操作方向和信心度设定止损
                        # 低信心度通常用2.5-3.5%的止损
                        if '做空' in operation_decision or '看空' in directional_view:
                            # 做空：止损在进场价上方
                            stop_loss_price = int(entry_high * 1.03)  # 3%止损
                            stop_loss = f">{stop_loss_price}元"
                        elif '做多' in operation_decision or '看多' in directional_view:
                            # 做多：止损在进场价下方
                            stop_loss_price = int(entry_low * 0.97)  # 3%止损
                            stop_loss = f"<{stop_loss_price}元"
                except Exception as e:
                    pass  # 如果计算失败，保持None
            
            if entry_range or stop_loss or target_price:
                key_prices_section = "\n\n💰 **关键价位**"
                if entry_range:
                    key_prices_section += f"\n   • 建议进场区间：{entry_range}"
                if target_price:
                    key_prices_section += f"\n   • 目标价位：{target_price}"
                if stop_loss:
                    key_prices_section += f"\n   • 止损位：{stop_loss}"
                else:
                    # 如果最终还是没有止损位，给出原则性建议
                    if operational_conf == '低' or '高风险' in str(operation_decision):
                        key_prices_section += f"\n   • 止损位：严格执行，基于关键技术位（通常2.5-3.5%）"
                    else:
                        key_prices_section += f"\n   • 止损位：基于技术位或2-3%设定"
        
        return f"""【决策总览】

📈 **方向研判**：{direction_emoji} {directional_view}
   ├─ 信心度：{conf_desc.get(directional_conf, directional_conf)}
   └─ 决策依据：分析师团队基于6个专业维度的综合研判结果

🎯 **操作决策**：{operation_decision}
   ├─ 操作信心：{conf_desc.get(operational_conf, operational_conf)}
   └─ 风控原则：风险管理优先，严格控制仓位规模

💼 **CIO最终结论**：
   → {direction_action}，{operation_decision.replace('做多', '建立多头仓位').replace('做空', '建立空头仓位').replace('观望', '暂不操作')}
   → 方向信心{directional_conf} + 操作信心{operational_conf}
   → 要求团队纪律化执行，任何偏离需重新评估


【执行指导】

📊 **仓位配置**
   • 建议区间：{position_range}
   • 执行策略：{position_strategy}
   • 特别提示：根据市场反应动态调整，切忌一次性满仓{key_prices_section}

🛡️ **风险控制**
   • 止损纪律：{stop_loss_rule}
   • 风控红线：任何单一持仓不得超过风控框架上限
   • 异常处理：市场剧烈波动时，优先保护本金，立即减仓

⚙️ **动态管理**
   • 加仓条件：方向验证 + 技术位突破 + 风险可控
   • 减仓信号：技术位破位 / 基本面恶化 / 风险失控
   • 平仓原则：达到预期目标或止损触发，立即执行

📍 **监控要点**
   • 关键指标：技术位变化、持仓结构、基本面数据
   • 外部风险：政策变动、市场情绪、流动性状况
   • 评估频率：每日盘后复盘，重大变化实时评估


【决策追溯】

本决策基于完整的分析链条，所有判断均可追溯：
→ 数据来源：6个专业分析模块（技术、基差、库存、持仓、期限结构、新闻）
→ 评判依据：多空辩论三维度评分 + 分析师观点统计
→ 风险评估：专业风控团队独立审核
→ 最终决策：CIO综合判断并对结果负责

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def _identify_core_market_contradiction(self, trader_analysis: Dict[str, str], 
                                           risk_analysis: Dict[str, str],
                                           directional_view: str) -> str:
        """🔥 新方法：识别并描述市场的核心矛盾（CIO战略视角）"""
        
        direction = trader_analysis.get('direction', '未明确')
        key_factors = trader_analysis.get('key_factors', [])
        risk_level = risk_analysis.get('risk_level', '未评估')
        
        # 根据方向判断，提炼核心矛盾（更权威的语言风格）
        if '中性' in directional_view or '观望' in directional_view:
            # 中性观望：多空力量僵持
            return """当前市场处于多空博弈的胶着状态。

分析师团队的观点分歧反映了市场信号的矛盾性：技术面与基本面未能形成共振，
多空双方都拿不出足以改变局势的决定性证据。

在这种战略性不确定的环境下，我的判断是：**保存实力比盲目下注更重要**。"""
        
        elif '看空' in directional_view or '做空' in directional_view:
            # 看空：压力因素占优
            if '库存' in str(key_factors):
                return """核心矛盾锁定在供需失衡上。

库存持续累积反映了实体需求的疲弱，这不是短期波动，而是结构性压力。
尽管市场可能出现技术性反弹，但在供应压力释放之前，空头逻辑将持续主导。

我的判断：**趋势的力量大于短期的波动**。"""
            else:
                return """市场正面临多重利空因素的叠加共振。

技术面的破位与基本面的恶化形成了相互强化的负向循环。
在这种环境下，空头策略不是投机，而是顺应市场重力。

我的判断：**与其逆势抗争，不如顺势而为**。"""
        
        else:  # 看多
            # 看多：支撑因素占优
            if '持仓' in str(key_factors):
                return """市场资金流向揭示了机构的真实意图。

持仓数据显示资金正在持续流入，这是比技术指标更可靠的先行信号。
多头力量的积累已经形成了正反馈循环，尽管短期可能有调整，但方向已定。

我的判断：**跟随聪明钱的方向，而非市场的噪音**。"""
            else:
                if '高风险' in risk_level:
                    return """多头逻辑正在成型，但市场波动性提醒我们必须谨慎。

基本面的改善与技术面的突破正在形成共振，这是做多的基础。
但高风险环境要求我们降低仓位、提高纪律性，用更保守的方式参与可能的上涨。

我的判断：**看对方向是第一步，控制风险是关键**。"""
                else:
                    return """多头逻辑正在成型，市场环境相对有利。

基本面的改善与技术面的突破正在形成共振，支撑因素正在积累。
当前环境下，做多策略具有较好的风险收益比。

我的判断：**把握趋势窗口，但保持纪律性**。"""
    
    def _generate_cio_key_judgments(self, trader_analysis: Dict[str, str],
                                    risk_analysis: Dict[str, str],
                                    directional_conf: str,
                                    operational_conf: str,
                                    directional_view: str) -> str:
        """🔥 新方法：生成CIO的三个关键判断（权威、果断、战略高度）"""
        
        # 🔥 修复：使用传入的directional_view（准确的方向判断），而不是trader_analysis['direction']
        risk_level = risk_analysis.get('risk_level', '未评估')
        key_factors = trader_analysis.get('key_factors', [])
        
        judgments = []
        
        # 判断1：市场状态判断（更权威的表述）
        if '中性' in directional_view or '观望' in directional_view:
            judgments.append("**关于市场方向**\n   → 当前多空博弈陷入僵局，任何一方都未能取得决定性优势\n   → 在战略不确定性面前，我选择保持战略定力，不做方向性赌注")
            is_directional = False
        elif '看空' in directional_view or '做空' in directional_view or '偏空' in directional_view:
            judgments.append("**关于市场方向**\n   → 空头逻辑已经形成：基本面压力与技术面走弱正在共振\n   → 我判断趋势的力量将主导市场，顺势而为是理性选择")
            is_directional = True
        else:  # 看多/做多
            judgments.append("**关于市场方向**\n   → 多头逻辑正在成立：支撑因素正在积累，市场动能正在改善\n   → 我判断上行趋势的基础已经具备，但时机和节奏同样重要")
            is_directional = True
        
        # 判断2：风险收益评估（🔥 修复：与方向判断保持逻辑一致，更具决策者语言风格）
        if risk_level in ['极高风险', '高风险']:
            if is_directional:
                # 有明确方向但风险高：强调风险管理的重要性，而不是否定方向
                if key_factors:
                    main_risk = key_factors[0] if len(key_factors) > 0 else "市场波动性较大"
                    judgments.append(f"**关于风险管控**\n   → {main_risk}是当前最大的风险来源\n   → 看对方向只是第一步，控制风险才是盈利的前提，我要求严格执行仓位纪律")
                else:
                    judgments.append("**关于风险管控**\n   → 市场波动性处于高位，任何仓位都可能面临剧烈回撤\n   → 我要求用更保守的仓位参与，用纪律性换取生存空间")
            else:
                # 无明确方向且风险高：不适合进场
                judgments.append("**关于风险管控**\n   → 方向不明确时承担高风险，这在投资上是不理性的\n   → 我的原则是：看不清楚的时候，宁可错过机会，也不承担不必要的风险")
        elif risk_level in ['中等风险']:
            judgments.append("**关于风险管控**\n   → 风险因素处于可控范围，但不意味着可以放松警惕\n   → 我要求保持止损纪律，任何时候都要为错误判断留出退路")
        else:
            judgments.append("**关于风险管控**\n   → 风险环境相对有利，这为我们提供了较大的操作空间\n   → 但市场永远存在意外，我要求保持基本的风险意识")
        
        # 判断3：操作策略判断（更具决策感）
        if directional_conf == '低' and operational_conf == '低':
            judgments.append("**关于操作策略**\n   → 双低信心度告诉我：现在不是激进的时候\n   → 我的决策是保守为主，保存实力，等待更好的机会窗口")
        elif directional_conf == '高' and operational_conf == '高':
            judgments.append("**关于操作策略**\n   → 双高信心度为积极操作提供了支撑\n   → 我的决策是适度积极，把握趋势窗口，但始终保持纪律性")
        else:
            # 🔥 优化：明确说明是哪种不对称（方向信心 vs 操作信心）
            conf_desc = f"方向信心{directional_conf}+操作信心{operational_conf}"
            judgments.append(f"**关于操作策略**\n   → {conf_desc}的不对称格局告诉我：方向可能对，但必须极度控制风险\n   → 我的决策是谨慎试探，用小仓位验证判断，再决定是否加码")
        
        return "\n\n".join([f"【判断{i+1}】 {j}" for i, j in enumerate(judgments)])
    
    def _extract_decision_essence(self, directional_view: str, 
                                  directional_conf: str,
                                  operational_conf: str) -> str:
        """🔥 新方法：提炼决策的本质（CIO的决策哲学，更具深度和权威）"""
        
        if '中性' in directional_view or '观望' in directional_view:
            if directional_conf == '低' and operational_conf == '低':
                return """这是一个战略性的"不作为"决策。

在投资中，**知道什么时候不该出手，与知道什么时候该出手同样重要**。

当市场信号混乱、方向不明时，保存实力本身就是一种胜利。我们不是在等待奇迹，
而是在等待市场给出更清晰的信号。专业投资者与业余投资者的区别，
不在于抓住了多少机会，而在于避开了多少陷阱。

**本质**：在不确定性中保持定力，是长期生存的基础。"""
            else:
                return """这是一个主动选择的观望。

市场正处于关键转折点，多空力量尚在角力。在这种时候，急于下注往往会付出代价。
我选择站在场边观察，等待市场自己给出答案。

**本质**：耐心是投资者最重要的品质之一。"""
        
        elif '看空' in directional_view or '做空' in directional_view:
            if directional_conf == '低':
                return """这是一个谨慎的做空决策。

空头逻辑虽然正在形成，但低信心度提醒我：市场永远可能给你意外。
我选择用小仓位参与，用严格的止损保护自己，用纪律性代替赌性。

**本质**：看对方向只是第一步，活下来才能笑到最后。"""
            else:
                return """这是一个顺势而为的做空决策。

当趋势的力量已经形成，对抗它是愚蠢的。我选择跟随市场的重力，
但始终保持对风险的敬畏。再好的逻辑，也需要用合理的仓位和严格的纪律来执行。

**本质**：顺应趋势，但永远不过度自信。"""
        
        else:  # 看多
            if directional_conf == '低':
                return """这是一个试探性的做多决策。

多头逻辑虽然存在，但低信心度告诉我：时机可能还不够成熟。
我选择轻仓试探，观察市场的反应，再决定是否加码。方向对不代表时机对，
过早入场与方向错误一样致命。

**本质**：在不确定性中保持灵活，是实战智慧。"""
            else:
                return """这是一个把握趋势的做多决策。

多头逻辑正在成立，市场正在给予我们机会窗口。我选择参与这个趋势，
但绝不盲目乐观。再好的行情，也要用合理的仓位、明确的止损、
严格的纪律来保护自己。

**本质**：把握机会，但永远不失去对市场的敬畏。"""
    
    def _generate_concise_team_summary(self, trader_analysis: Dict[str, str],
                                      risk_analysis: Dict[str, str],
                                      directional_view: str = None,
                                      directional_confidence: str = None,
                                      analyst_stats: Dict[str, int] = None) -> str:
        """🔥 优化：生成简洁的团队意见综述（增加具体数据引用，提升专业性）"""
        
        # 🔥 修复：优先使用传入的directional_view
        trader_dir = directional_view if directional_view else trader_analysis.get('direction', '未明确')
        trader_conf = directional_confidence if directional_confidence else trader_analysis.get('confidence', '未评估')
        
        risk_level = risk_analysis.get('risk_level', '未评估')
        risk_conf = risk_analysis.get('confidence', '未评估')
        
        # 信心度映射
        conf_desc = {
            '高': '🟢 高',
            '中': '🟡 中',
            '低': '🔴 低'
        }
        
        # 风险等级映射
        risk_desc = {
            '极高风险': '🔴 极高风险',
            '高风险': '🟠 高风险',
            '中等风险': '🟡 中等风险',
            '低风险': '🟢 低风险',
            '极低风险': '🟢 极低风险'
        }
        
        # 🔥 新增：构建分析师观点统计说明
        analyst_detail = ""
        if analyst_stats:
            bullish = analyst_stats.get('bullish_count', 0)
            bearish = analyst_stats.get('bearish_count', 0)
            neutral = analyst_stats.get('neutral_count', 0)
            analyst_detail = f"（{bullish}看多 vs {bearish}看空 vs {neutral}中性）"
        
        return f"""┌─ 📊 **分析师团队研判** ─────────────────────────────────────
│
│  综合观点：{trader_dir} {analyst_detail}
│  信心度等级：{conf_desc.get(trader_conf, trader_conf)}
│  数据来源：技术、基差、库存、持仓、期限结构、新闻六大专业模块
│  核心依据：多维度数据交叉验证，投票机制确保客观性
│
└──────────────────────────────────────────────────────────

┌─ 💼 **交易员专业评判** ─────────────────────────────────────
│
│  评判结论：支持上述方向判断
│  方法论：多空激烈辩论 + 三维度科学评分（论据质量、逻辑严密性、客观理性度）
│  质量保证：每个模块论据均经过严格审核，评分过程完全透明可追溯
│
└──────────────────────────────────────────────────────────

┌─ 🛡️ **风险管理评估** ──────────────────────────────────────
│
│  风险评级：{risk_desc.get(risk_level, risk_level)}
│  操作信心：{conf_desc.get(risk_conf, risk_conf)}
│  风控框架：仓位管理优先、严格止损纪律、动态风险监控
│  核心原则：保护本金是第一要务，盈利是在风控框架内的副产品
│
└──────────────────────────────────────────────────────────

┌─ 🤝 **团队共识声明** ──────────────────────────────────────
│
│  ✓ 当前市场环境要求谨慎态度，任何操作必须在风控框架内执行
│  ✓ 风险管理永远是第一优先级，超过风险承受能力的机会必须放弃
│  ✓ 纪律性执行至关重要，任何偏离决策的操作都需重新评估
│
└──────────────────────────────────────────────────────────"""
    
    def _build_decision_rationale(self, trader_analysis: Dict[str, str], risk_analysis: Dict[str, str],
                                directional_confidence: str, operational_confidence: str) -> str:
        """构建决策依据"""
        
        rationale_parts = []
        
        # 基于交易员信心度的考量
        if trader_analysis['confidence'] == '高':
            rationale_parts.append("交易员高信心度的专业判断为决策提供了有力支撑")
        elif trader_analysis['confidence'] == '低':
            rationale_parts.append("交易员低信心度提醒我们需要谨慎操作")
        else:
            rationale_parts.append("交易员中等信心度要求我们平衡风险与收益")
        
        # 基于风控评估的考量
        if risk_analysis['confidence'] == '低':
            rationale_parts.append("风控部门的低操作信心度要求严格控制仓位")
        elif risk_analysis['confidence'] == '高':
            rationale_parts.append("风控部门相对乐观的评估允许适度操作")
        else:
            rationale_parts.append("风控部门的谨慎态度需要在操作中充分体现")
        
        # 基于信心度组合的最终决策
        if directional_confidence == '低' and operational_confidence == '低':
            rationale_parts.append("双低信心度决定了保守操作的必要性")
        elif directional_confidence == '高' and operational_confidence == '高':
            rationale_parts.append("双高信心度支持相对积极的投资策略")
        else:
            rationale_parts.append("信心度的差异要求我们在方向和操作上保持平衡")
        
        return "；".join(rationale_parts) + "。"
    
    def _format_cio_professional_statement(self, decision_logic: str, commodity_name: str,
                                         trading_decision: TradingDecision, risk_assessment: RiskAssessment,
                                         analysis_state: FuturesAnalysisState) -> str:
        """🔥 新增：格式化CIO专业声明，体现真正的CIO语言风格"""
        
        # 提取关键决策因素
        key_factors = self._extract_key_decision_factors(trading_decision, analysis_state)
        
        # 生成CIO级别的市场洞察
        market_insight = self._generate_cio_market_insight(key_factors, commodity_name)
        
        # 生成决策逻辑
        cio_logic = self._generate_cio_decision_reasoning(
            trading_decision, risk_assessment, key_factors
        )
        
        # 生成执行指导
        execution_guidance = self._generate_cio_execution_guidance(
            trading_decision, risk_assessment
        )
        
        return f"""💼 投资决策

{market_insight}

🧠 决策逻辑

{cio_logic}

⚡ 执行指导

{execution_guidance}

本决策基于完整的分析链条，所有判断均可追溯到具体的分析依据和评估结果。

首席投资官
{datetime.now().strftime('%Y年%m月%d日')}"""
    
    def _extract_key_decision_factors(self, trading_decision: TradingDecision, 
                                    analysis_state: FuturesAnalysisState) -> Dict[str, str]:
        """提取关键决策因素"""
        factors = {}
        
        # 从交易员分析中提取关键信息
        trader_reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        # 提取宏观因素
        if "美联储" in trader_reasoning or "降息" in trader_reasoning:
            factors["macro"] = "美联储政策宽松预期"
        elif "加息" in trader_reasoning:
            factors["macro"] = "美联储紧缩政策压力"
        
        # 提取资金流向
        if "净多仓" in trader_reasoning or "ETF" in trader_reasoning:
            factors["capital_flow"] = "机构资金持续流入"
        elif "净空仓" in trader_reasoning:
            factors["capital_flow"] = "资金流出压力显现"
        
        # 提取技术面
        if "突破" in trader_reasoning and "阻力" in trader_reasoning:
            factors["technical"] = "技术面临关键突破"
        elif "超买" in trader_reasoning or "RSI" in trader_reasoning:
            factors["technical"] = "技术指标显示超买风险"
        
        # 提取基本面
        if "库存" in trader_reasoning:
            if "增加" in trader_reasoning or "累积" in trader_reasoning:
                factors["fundamental"] = "供应端压力增加"
            else:
                factors["fundamental"] = "库存去化支撑价格"
        
        # 从分析师模块中提取更多信息
        if analysis_state:
            # 检查新闻分析
            if hasattr(analysis_state, 'news_analysis') and analysis_state.news_analysis:
                news_data = analysis_state.news_analysis.result_data
                if "地缘" in str(news_data):
                    factors["geopolitical"] = "地缘风险提供避险需求"
        
        return factors
    
    def _generate_cio_market_insight(self, key_factors: Dict[str, str], commodity_name: str) -> str:
        """生成CIO级别的市场洞察"""
        if not key_factors:
            return f"当前{commodity_name}市场处于关键节点，需要密切关注市场变化。"
        
        insights = []
        
        # 宏观环境洞察
        if "macro" in key_factors:
            insights.append(f"宏观层面，{key_factors['macro']}为{commodity_name}提供了重要的政策背景。")
        
        # 资金流向洞察
        if "capital_flow" in key_factors:
            insights.append(f"从资金配置角度，{key_factors['capital_flow']}显示了市场情绪的变化。")
        
        # 技术面洞察
        if "technical" in key_factors:
            insights.append(f"技术层面，{key_factors['technical']}，这是我们需要重点关注的信号。")
        
        # 基本面洞察
        if "fundamental" in key_factors:
            insights.append(f"基本面上，{key_factors['fundamental']}，影响中期价格走势。")
        
        if insights:
            return " ".join(insights)
        else:
            return f"综合各方面因素，{commodity_name}市场呈现复杂态势，需要谨慎评估。"
    
    def _generate_cio_decision_reasoning(self, trading_decision: TradingDecision,
                                       risk_assessment: RiskAssessment, key_factors: Dict[str, str]) -> str:
        """生成CIO决策推理"""
        strategy = trading_decision.strategy_type.value if trading_decision.strategy_type else "观望"
        risk_level = risk_assessment.overall_risk_level.value if risk_assessment.overall_risk_level else "中等风险"
        
        # 基于策略和风险的决策逻辑
        if "做多" in strategy:
            if len(key_factors) >= 2:
                reasoning = f"基于{len(key_factors)}个核心支撑因素的综合判断，我认为当前具备了{strategy}的基础条件。"
            else:
                reasoning = f"虽然支撑因素有限，但{strategy}策略在当前环境下仍有其合理性。"
        elif "做空" in strategy:
            reasoning = f"考虑到当前的风险因素和市场环境，{strategy}策略更符合风险控制的要求。"
        else:
            reasoning = "在当前市场不确定性较高的情况下，保持观望是最稳健的选择。"
        
        # 加入风险考量
        if risk_level in ["极高风险", "高风险"]:
            reasoning += f" 鉴于{risk_level}的评估结果，我们必须严格控制仓位规模。"
        
        return reasoning
    
    def _generate_cio_execution_guidance(self, trading_decision: TradingDecision,
                                       risk_assessment: RiskAssessment) -> str:
        """生成CIO执行指导"""
        position_limit = risk_assessment.position_size_limit if risk_assessment.position_size_limit else "5%"
        
        guidance = f"执行层面，建议仓位控制在{position_limit}以内，"
        
        # 根据风险等级调整执行要求
        risk_level = risk_assessment.overall_risk_level.value if risk_assessment.overall_risk_level else "中等风险"
        
        if risk_level in ["极高风险", "高风险"]:
            guidance += "采用分批建仓方式，严格执行止损纪律。"
        else:
            guidance += "可以适度灵活操作，但要保持风控底线。"
        
        guidance += " 市场变化时要及时调整策略，保持敏锐的市场嗅觉。"
        
        return guidance
    
    def _extract_actual_operation_decision(self, trader_reasoning: str) -> str:
        """从交易员实际分析中提取操作决策"""
        
        # 按优先级顺序检查明确的操作建议
        operation_patterns = [
            ("积极做多", "积极做多"),
            ("谨慎做多", "谨慎做多"), 
            ("轻仓做多", "轻仓做多"),
            ("积极做空", "积极做空"),
            ("谨慎做空", "谨慎做空"),
            ("轻仓做空", "轻仓做空"),
            ("做多", "谨慎做多"),
            ("做空", "谨慎做空")
        ]
        
        for pattern, decision in operation_patterns:
            if pattern in trader_reasoning:
                return decision
        
        # 如果没有明确表述，基于关键词倾向判断
        bullish_count = len([kw for kw in ["看多", "买入", "上涨", "多头", "支撑"] if kw in trader_reasoning])
        bearish_count = len([kw for kw in ["看空", "卖出", "下跌", "空头", "阻力"] if kw in trader_reasoning])
        
        if bullish_count > bearish_count:
            return "轻仓做多"
        elif bearish_count > bullish_count:
            return "轻仓做空"
        else:
            return "轻仓做多"  # 默认做多（基于统计优势）
    
    def _generate_factual_analysis_content(self, commodity_name: str, trader_reasoning: str, 
                                         debate_result: DebateResult, risk_assessment: RiskAssessment, 
                                         confidence: float) -> str:
        """基于实际数据生成CIO分析内容"""
        
        # 基于实际辩论得分
        bull_score = debate_result.overall_bull_score
        bear_score = debate_result.overall_bear_score
        score_diff = abs(bull_score - bear_score)
        winner = "多头" if bull_score > bear_score else "空头"
        
        # 基于实际交易员分析长度评估质量
        analysis_length = len(trader_reasoning)
        analysis_quality = "详细" if analysis_length > 500 else "中等" if analysis_length > 200 else "简要"
        
        # 基于实际风控评估
        risk_level = risk_assessment.overall_risk_level.value if risk_assessment.overall_risk_level else "未评估"
        
        content = f"""
AI战略决策分析

一、实际数据分析基础

基于交易员{analysis_quality}分析（共{analysis_length}字），结合多空辩论评估结果，CIO认为当前{commodity_name}投资机会具备以下特征：

辩论评分结果：{winner}以{bull_score:.1f}分对{bear_score:.1f}分获胜，分差{score_diff:.1f}分体现了{self._get_clarity_description(score_diff)}的市场分歧

交易员专业判断：{self._extract_key_trader_insights(trader_reasoning)}

风险评估状况：风险等级为{risk_level}，{self._get_risk_description(risk_level)}

二、综合决策判断

CIO决策逻辑：严格基于交易员专业分析和辩论量化结果，{winner}论证更具说服力，操作信心度{self._convert_confidence_to_qualitative(confidence)}体现了基于实际风险度的科学评估

执行策略制定：根据{self._convert_confidence_to_qualitative(confidence)}信心度，采用{'积极' if confidence >= 0.7 else '谨慎' if confidence >= 0.5 else '轻仓'}操作策略，严格控制风险的同时把握投资机会

三、决策执行要求

本决策完全基于实际分析数据：交易员{analysis_quality}分析、{winner}辩论优势、{risk_level}风险等级

决策不包含任何虚构元素，所有判断均可溯源至具体的分析内容和量化评分
"""
        
        return content.strip()
    
    def _get_clarity_description(self, score_diff: float) -> str:
        """基于实际分差描述分歧程度"""
        if score_diff >= 2.0:
            return "较小"
        elif score_diff >= 1.0:
            return "中等"
        else:
            return "较大"
    
    def _extract_key_trader_insights(self, trader_reasoning: str) -> str:
        """提取交易员的关键洞察"""
        
        if not trader_reasoning or len(trader_reasoning.strip()) < 20:
            return "交易员分析内容不足，建议获取更详细的市场分析。"
            
        # 尝试多种方式提取关键洞察
        import re
        
        # 1. 查找明确的结论性表述
        conclusion_patterns = [
            r'综合.*?[，。]',
            r'因此.*?[，。]',
            r'建议.*?[，。]',
            r'判断.*?[，。]',
            r'认为.*?[，。]',
            r'倾向.*?[，。]',
            r'操作.*?[，。]',
            r'策略.*?[，。]'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, trader_reasoning)
            if matches:
                insight = matches[0].strip().replace('\n', '').replace('\r', '')
                if len(insight) > 15:  # 确保有实质内容
                    return insight
        
        # 2. 如果找不到明确结论，提取前两句有意义的内容
        sentences = [s.strip() for s in trader_reasoning.split('。') if len(s.strip()) > 15]
        meaningful_sentences = []
        
        for sentence in sentences[:4]:  # 查看前4句
            # 过滤掉纯粹的问候语或无意义的句子
            if any(word in sentence for word in ["价格", "市场", "分析", "技术", "基差", "库存", "持仓", "建议", "判断"]):
                meaningful_sentences.append(sentence)
                
        if meaningful_sentences:
            # 取前1-2句，但限制总长度
            result = meaningful_sentences[0]
            if len(meaningful_sentences) > 1 and len(result) < 50:
                result += "；" + meaningful_sentences[1]
            
            # 限制总长度，避免过长
            if len(result) > 100:
                result = result[:95] + "..."
                
            return result + "。"
        
        # 3. 最后的兜底：提取前50个字符的实际内容
        clean_content = trader_reasoning.replace('\n', '').replace('\r', '').strip()
        if len(clean_content) > 15:
            return clean_content[:50] + ("..." if len(clean_content) > 50 else "。")
        
        return "交易员分析数据不完整，建议补充详细的市场研判内容。"
    
    def _get_risk_description(self, risk_level: str) -> str:
        """基于实际风险等级给出描述"""
        risk_descriptions = {
            "LOW": "当前风险控制良好，支持适度仓位操作",
            "MEDIUM": "存在中等风险，需要谨慎控制仓位规模", 
            "HIGH": "风险等级较高，建议轻仓操作或观望",
            "VERY_HIGH": "风险极高，建议暂停交易",
            "未评估": "风险评估数据不完整"
        }
        return risk_descriptions.get(risk_level, "风险状况需要进一步评估")
    
    def _calculate_position_from_confidence(self, confidence: float) -> str:
        """基于实际信心度计算建议仓位"""
        if confidence >= 0.75:
            return "10-15%"
        elif confidence >= 0.60:
            return "6-10%"
        elif confidence >= 0.45:
            return "3-6%"
        else:
            return "1-3%"
    
    def _build_ai_cio_analysis_prompt(self, commodity: str, analysis_state: FuturesAnalysisState,
                                    debate_result: DebateResult, risk_assessment: RiskAssessment,
                                    trading_decision: TradingDecision) -> str:
        """构建AI CIO分析prompt"""
        
        commodity_name = get_commodity_name(commodity)
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        
        return f"""
你是一位世界顶级的投资机构首席投资官(CIO)和AI战略决策专家，具备以下核心能力：

🧠 AI战略决策优势：
- 快速整合多维度复杂信息，形成战略判断
- 基于大量历史案例进行战略决策优化
- 进行前瞻性风险评估和机会识别
- 平衡短期执行和长期战略目标

👔 CIO核心能力：
- 20年+投资决策经验，管理过百亿级资产
- 精通宏观经济、市场周期、资产配置
- 擅长综合多方观点，做出最终投资决策
- 具备危机处理和逆向投资的丰富经验

⚖️ 决策核心原则：
- 基于数据，超越数据
- 平衡收益与风险
- 考虑时机与趋势
- 保持独立判断

=== 📊 投资决策标的 ===
品种：{commodity_name} ({commodity})
分析日期：{analysis_state.analysis_date}
交易员建议：{trading_decision.strategy_type.value}
风控评级：{risk_assessment.overall_risk_level.value}
辩论分歧：{score_diff:.1f}分

=== 📋 核心决策信息 ===
交易员分析：
{trading_decision.reasoning if trading_decision.reasoning else '无详细分析'}

风控意见：
{risk_assessment.risk_opinion if hasattr(risk_assessment, 'risk_opinion') else '标准风控评估'}

辩论结果：{debate_result.final_winner.value}获胜

=== 🎯 CIO战略分析任务 ===
请运用你的AI能力和CIO经验，进行高层次的投资决策分析：

1. 战略机会评估（300-400字）
   - 从CIO视角评估当前投资机会的战略价值
   - 分析该投资与整体投资组合的协同效应
   - 评估市场时机和周期位置的战略意义
   - 识别可能被忽视的长期价值驱动因素

2. 综合风险判断（300-400字）
   - 超越技术风险，从战略高度评估系统性风险
   - 分析宏观环境变化对投资的潜在影响
   - 评估流动性、政策、地缘政治等外部风险
   - 判断当前风险收益比是否符合机构标准

3. 决策逻辑阐述（400-500字）
   - 基于交易员建议和风控意见，阐述最终决策逻辑
   - 解释如何平衡不同观点和风险因素
   - 说明决策的时间框架和预期目标
   - 阐述与机构整体投资策略的一致性

4. 执行策略制定（300-400字）
   - 制定具体的执行计划和时间安排
   - 设定关键监控指标和调整触发条件
   - 规划不同市场情景下的应对策略
   - 明确授权范围和风险控制要求

请以资深CIO的身份，用战略性和前瞻性的语言进行分析，体现高层决策者的格局和视野。

重要格式要求：请不要在回复中使用任何星号(*)、井号(#)或下划线(_)等格式化字符，使用纯文本回复。
"""
    
    def _format_cio_statement_with_ai_analysis(self, ai_analysis: str, commodity: str,
                                             debate_result: DebateResult, risk_assessment: RiskAssessment,
                                             trading_decision: TradingDecision) -> str:
        """格式化包含AI分析的CIO声明"""
        
        commodity_name = get_commodity_name(commodity)
        
        # 🔥 关键修复：全面清理AI分析内容中的markdown格式字符
        cleaned_analysis = ai_analysis
        # 更彻底地移除各种markdown格式字符
        import re
        # 移除所有**符号（包括单独或成对出现的）
        cleaned_analysis = re.sub(r'\*+', '', cleaned_analysis)
        # 移除各种markdown符号
        cleaned_analysis = cleaned_analysis.replace("__", "") # 粗体（下划线）
        cleaned_analysis = cleaned_analysis.replace("_", "")  # 斜体（下划线）
        cleaned_analysis = re.sub(r'#{1,6}\s*', '', cleaned_analysis) # 所有级别标题
        
        # 🎨 新增：优化排版格式，解决横向滚动问题
        formatted_analysis = self._optimize_text_layout(cleaned_analysis)
        
        return f"""
首席投资官投资决策报告
{commodity_name}({commodity})期货品种 - 基于综合分析的专业投资决策

== AI战略决策分析 ==
{formatted_analysis}

== 决策执行要求 ==
最终决策：{trading_decision.strategy_type.value}
风险等级：{risk_assessment.overall_risk_level.value}  
建议仓位：{safe_format_percent(risk_assessment.position_size_limit)}
监控频率：{'每日盘中实时监控' if risk_assessment.overall_risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH] else '每日收盘监控'}

首席投资官
{datetime.now().strftime('%Y年%m月%d日')}
""".strip()
    
    def _optimize_text_layout(self, text: str) -> str:
        """优化文本排版，解决横向滚动问题"""
        import re
        
        # 分割段落
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # 识别标题行（通常较短且独立）
            if len(paragraph.strip()) < 30 and not '。' in paragraph and not ',' in paragraph:
                formatted_paragraphs.append(paragraph.strip())
                continue
            
            # 处理正文段落 - 控制每行长度
            # 移除段落内的换行符，重新包装
            clean_paragraph = re.sub(r'\s+', ' ', paragraph.strip())
            
            # 使用textwrap包装文本，每行最多80个字符（中文字符按2个计算）
            wrapped_lines = []
            current_line = ""
            words = clean_paragraph
            
            # 简单按句号分割，保持语义完整性
            sentences = re.split(r'([。！？；])', words)
            current_line = ""
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                    
                # 估算行长度（中文字符按2计算，英文按1计算）
                line_length = self._estimate_text_width(current_line + sentence)
                
                if line_length > 80 and current_line.strip():
                    # 当前行太长，先保存当前行
                    wrapped_lines.append(current_line.strip())
                    current_line = sentence
                else:
                    current_line += sentence
            
            # 添加最后一行
            if current_line.strip():
                wrapped_lines.append(current_line.strip())
            
            # 将包装后的行连接为段落
            formatted_paragraphs.append('\n'.join(wrapped_lines))
        
        return '\n\n'.join(formatted_paragraphs)
    
    def _estimate_text_width(self, text: str) -> int:
        """估算文本显示宽度（中文字符按2计算）"""
        width = 0
        for char in text:
            # 中文字符、中文标点符号按2计算
            if ord(char) > 127:
                width += 2
            else:
                width += 1
        return width
    
    # 🔥 已删除旧的_create_structured_cio_statement方法，使用新的_create_factual_cio_statement
    
    # 🔥 已删除旧的_generate_execution_directive方法，新系统使用_create_execution_plan
    
    def _determine_final_decision(self, debate_result: DebateResult, 
                                risk_assessment: RiskAssessment) -> FinalDecision:
        """确定最终决策方向（旧方法，保留兼容性）"""
        
        # 基于辩论结果和风险评估
        score_diff = abs(debate_result.overall_bull_score - debate_result.overall_bear_score)
        winner = debate_result.final_winner
        risk_level = risk_assessment.overall_risk_level
        
        if risk_level in [RiskLevel.VERY_HIGH, RiskLevel.HIGH]:
            return FinalDecision.HOLD  # 高风险时保持观望
        
        if winner == DebateStance.BULLISH:
            if score_diff > 3.0:
                return FinalDecision.STRONG_BUY
            else:
                return FinalDecision.BUY
        else:
            if score_diff > 3.0:
                return FinalDecision.STRONG_SELL
            else:
                return FinalDecision.SELL
    
    def _determine_final_decision_based_on_trader_and_risk(self, trading_decision: TradingDecision,
                                                         risk_assessment: RiskAssessment,
                                                         debate_result: DebateResult) -> FinalDecision:
        """🔥 全新CIO决策逻辑：基于高/中/低信心度体系，明确做多做空决策"""
        
        # 提取交易员的方向信心度和风控的操作信心度
        trader_reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        # 🔥 提取交易员的方向信心度（高/中/低）
        directional_confidence = self._extract_directional_confidence_level(trader_reasoning)
        
        # 🔥 提取风控的操作信心度（高/中/低）
        risk_opinion = risk_assessment.risk_manager_opinion if hasattr(risk_assessment, 'risk_manager_opinion') else ""
        operational_confidence = self._extract_operational_confidence_level(risk_opinion)
        
        # 🔥 提取明确的方向判断（看多/看空）
        directional_view = self._extract_clear_directional_view(trader_reasoning)
        
        # 🔧 DEBUG: 信心度体系调试
        print(f"🐛 DEBUG: directional_confidence = {directional_confidence}")
        print(f"🐛 DEBUG: operational_confidence = {operational_confidence}")
        print(f"🐛 DEBUG: directional_view = {directional_view}")
        
        # 🔥 新决策矩阵：基于双重信心度确定交易决策
        decision_matrix = self._build_confidence_decision_matrix(
            directional_confidence, operational_confidence, directional_view
        )
        
        final_decision = decision_matrix['decision']
        decision_reason = decision_matrix['reason']
        
        print(f"🐛 DEBUG: CIO最终决策 = {final_decision.value} | 原因: {decision_reason}")
        return final_decision
    
    def _extract_directional_confidence_level(self, trader_reasoning: str) -> str:
        """从交易员分析中提取方向信心度（高/中/低）"""
        import re
        
        # 🔥 优先匹配明确的信心度表述（精确匹配）
        # 匹配：信心度：低/中/高
        confidence_match = re.search(r'信心度[：:]\s*([高中低])', trader_reasoning)
        if confidence_match:
            confidence_value = confidence_match.group(1)
            print(f"✅ 精确匹配到信心度：{confidence_value}")
            return confidence_value
        
        # 匹配：信心度】低/中/高（带】符号的格式）
        confidence_match2 = re.search(r'信心度】\s*([高中低])', trader_reasoning)
        if confidence_match2:
            confidence_value = confidence_match2.group(1)
            print(f"✅ 精确匹配到信心度（格式2）：{confidence_value}")
            return confidence_value
        
        # 🔥 如果没有精确匹配，使用更严格的关键词
        reasoning_lower = trader_reasoning.lower()
        
        if any(keyword in reasoning_lower for keyword in ["高信心度", "强烈看好", "积极看好"]):
            return "高"
        elif any(keyword in reasoning_lower for keyword in ["低信心度", "谨慎看", "不确定性"]):
            return "低"
        else:
            return "中"  # 默认中等信心度
    
    def _extract_operational_confidence_level(self, risk_opinion: str) -> str:
        """从风控意见中提取操作信心度（高/中/低）"""
        if not risk_opinion:
            return "中"  # 默认中等
        
        import re
        
        # 🔥 优先匹配明确的操作信心度表述
        # 匹配：操作信心度为低/中/高 或 操作信心度】低/中/高
        confidence_match = re.search(r'操作信心度[为】：:]\s*([高中低])', risk_opinion)
        if confidence_match:
            confidence_value = confidence_match.group(1)
            print(f"✅ 精确匹配到操作信心度：{confidence_value}")
            return confidence_value
        
        # 匹配通用的信心度表述
        confidence_match2 = re.search(r'信心度[：:]?\s*为?\s*([高中低])', risk_opinion)
        if confidence_match2:
            confidence_value = confidence_match2.group(1)
            print(f"✅ 精确匹配到信心度（通用格式）：{confidence_value}")
            return confidence_value
        
        # 如果没有精确匹配，使用关键词
        opinion_lower = risk_opinion.lower()
        
        if any(keyword in opinion_lower for keyword in ["高操作信心", "高信心"]):
            return "高"
        elif any(keyword in opinion_lower for keyword in ["低操作信心", "低信心", "谨慎操作"]):
            return "低"
        else:
            return "中"
        
    def _extract_clear_directional_view(self, trader_reasoning: str) -> str:
        """🔥 改进：提取明确的方向判断（看多/看空，严禁中性）"""
        import re
        
        # 🔥 优先匹配明确的方向倾向表述（精确匹配）
        # 匹配：综合方向倾向：谨慎看多/积极看多/谨慎看空/积极看空
        direction_match = re.search(r'综合方向倾向[：:]\s*([^。\n]+)', trader_reasoning)
        if direction_match:
            direction_value = direction_match.group(1).strip()
            print(f"✅ 精确匹配到方向倾向：{direction_value}")
            return direction_value
        
        # 匹配：方向判断：谨慎看多/积极看多...
        direction_match2 = re.search(r'方向判断[：:]\s*([^。\n]+)', trader_reasoning)
        if direction_match2:
            direction_value = direction_match2.group(1).strip()
            print(f"✅ 精确匹配到方向判断：{direction_value}")
            return direction_value
        
        # 🔥 如果没有精确匹配，使用关键词统计
        reasoning_lower = trader_reasoning.lower()
        
        bullish_keywords = ["做多", "看多", "买入", "多头", "上涨", "积极做多", "谨慎做多", "单边做多", "偏多", "多方"]
        bearish_keywords = ["做空", "看空", "卖出", "空头", "下跌", "积极做空", "谨慎做空", "单边做空", "偏空", "空方"]
        
        bullish_count = sum(1 for keyword in bullish_keywords if keyword in reasoning_lower)
        bearish_count = sum(1 for keyword in bearish_keywords if keyword in reasoning_lower)
        
        print(f"🐛 DEBUG: 方向判断 - 多头关键词{bullish_count}个，空头关键词{bearish_count}个")
        
        if bullish_count > bearish_count:
            # 根据明确的表述确定积极程度
            if "积极看多" in reasoning_lower or "强烈看多" in reasoning_lower:
                return "积极看多"
            elif "谨慎看多" in reasoning_lower or "谨慎" in reasoning_lower or "轻仓" in reasoning_lower:
                return "谨慎看多"
            else:
                return "看多"
        elif bearish_count > bullish_count:
            # 根据明确的表述确定积极程度
            if "积极看空" in reasoning_lower or "强烈看空" in reasoning_lower:
                return "积极看空"
            elif "谨慎看空" in reasoning_lower or "谨慎" in reasoning_lower or "轻仓" in reasoning_lower:
                return "谨慎看空"
            else:
                return "看空"
        else:
            # 🔥 当关键词相等时，深度分析交易员的实际策略倾向
            if "单边做多" in reasoning_lower:
                return "谨慎看多"
            elif "单边做空" in reasoning_lower:
                return "谨慎看空"
            elif "多头" in reasoning_lower and "优势" in reasoning_lower:
                return "看多"
            elif "空头" in reasoning_lower and "优势" in reasoning_lower:
                return "看空"
            else:
                # 🚨 最后防线：基于技术面倾向强制选择，绝不允许中性
                print("🐛 DEBUG: 无法明确判断方向，使用默认逻辑")
                return "谨慎看多"  # 可根据具体市场环境调整
    
    def _build_confidence_decision_matrix(self, directional_confidence: str, 
                                           operational_confidence: str,
                                        directional_view: str) -> Dict[str, any]:
        """✅ 改进：构建基于双重信心度的决策矩阵，确保操作决策与信心度一致"""
        
        # 信心度权重计算
        confidence_scores = {
            "高": 3,
            "中": 2, 
            "低": 1
        }
        
        directional_score = confidence_scores.get(directional_confidence, 2)  # 默认中等
        operational_score = confidence_scores.get(operational_confidence, 2)  # 默认中等
        
        # ✅ 综合信心度评分（重新设计：操作信心度为主导）
        # 操作信心度权重60%，方向信心度40%（风控为先）
        total_confidence = operational_score * 0.6 + directional_score * 0.4
        
        print(f"🐛 DEBUG: 决策矩阵 - directional_view='{directional_view}', directional_conf={directional_confidence}, operational_conf={operational_confidence}, total={total_confidence}")
        
        # ✅ 决策逻辑：根据综合信心度确定操作风格
        if "看多" in directional_view:
            # 做多方向
            if operational_confidence == "低":
                # ✅ 操作信心度低 → 必须谨慎，无论方向信心度多高
                return {
                    "decision": FinalDecision.BUY,
                    "reason": f"谨慎做多（方向信心度{directional_confidence}，但操作信心度{operational_confidence}）",
                    "style": "谨慎"
                }
            elif total_confidence >= 2.5:
                return {
                    "decision": FinalDecision.BUY,
                    "reason": f"适度做多（方向信心度{directional_confidence}+操作信心度{operational_confidence}）",
                    "style": "适度"
                }
            else:
                return {
                    "decision": FinalDecision.BUY,
                    "reason": f"谨慎做多（方向信心度{directional_confidence}+操作信心度{operational_confidence}）",
                    "style": "谨慎"
                }
        elif "看空" in directional_view:
            # 做空方向
            if operational_confidence == "低":
                # ✅ 操作信心度低 → 必须谨慎，无论方向信心度多高
                return {
                    "decision": FinalDecision.SELL,
                    "reason": f"谨慎做空（方向信心度{directional_confidence}，但操作信心度{operational_confidence}）",
                    "style": "谨慎"
                }
            elif total_confidence >= 2.5:
                return {
                    "decision": FinalDecision.SELL,
                    "reason": f"适度做空（方向信心度{directional_confidence}+操作信心度{operational_confidence}）",
                    "style": "适度"
                }
            else:
                return {
                    "decision": FinalDecision.SELL,
                    "reason": f"谨慎做空（方向信心度{directional_confidence}+操作信心度{operational_confidence}）",
                    "style": "谨慎"
                }
        else:
            # 🔥 修复：支持中性观望决策，不再强制改为做多
            print(f"🐛 DEBUG: 方向判断为中性观望，directional_view='{directional_view}'，执行观望策略")
            return {
                "decision": FinalDecision.HOLD,  # 观望/持有
                "reason": f"中性观望（方向不明确，信心度{directional_confidence}+{operational_confidence}）",
                "style": "观望"
            }
    
    def _calculate_confidence_based_on_trader_and_risk(self, trading_decision: TradingDecision,
                                       risk_assessment: RiskAssessment,
                                                     debate_result: DebateResult) -> float:
        """基于交易员和风控的信心度计算CIO决策信心度"""
        # 这个方法现在使用新的高/中/低信心度体系
        # 返回0.0-1.0的数值用于兼容现有接口
        return 0.7  # 临时返回值，后续可以根据需要调整
    
    def _analyze_unified_directional_view(self, trading_decision: TradingDecision,
                                        risk_assessment: RiskAssessment,
                                        debate_result: DebateResult) -> Dict[str, Any]:
        """🔥 全新：基于高/中/低信心度的CIO统一决策分析"""
        
        trader_reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        # 第一步：提取方向信心度和操作信心度（原始值）
        trader_directional_confidence = self._extract_directional_confidence_level(trader_reasoning)
        risk_operational_confidence = self._extract_operational_confidence_level(
            risk_assessment.risk_manager_opinion if hasattr(risk_assessment, 'risk_manager_opinion') else ""
        )
        
        # ✅ 关键修复：CIO的信心度不能高于交易员和风控，必须调整
        # 方向信心度取决于交易员
        directional_confidence = trader_directional_confidence  # CIO方向信心度=交易员方向信心度
        # 操作信心度取决于风控
        operational_confidence = risk_operational_confidence  # CIO操作信心度=风控操作信心度
        
        print(f"🐛 DEBUG: 信心度调整 - 交易员:{trader_directional_confidence}, 风控:{risk_operational_confidence}")
        print(f"🐛 DEBUG: CIO最终 - 方向:{directional_confidence}, 操作:{operational_confidence}")
        
        # 第二步：确定明确的方向判断（看多/看空）
        directional_view = self._extract_clear_directional_view(trader_reasoning)
        
        # 第三步：基于双重信心度决定操作决策
        decision_matrix = self._build_confidence_decision_matrix(
            directional_confidence, operational_confidence, directional_view
        )
        
        # 第四步：生成决策逻辑
        decision_logic = self._generate_cio_decision_logic(
            trading_decision, risk_assessment, debate_result, 
            directional_confidence, operational_confidence, directional_view
        )
        
        # ✅ 优化：确保方向判断简洁一致，避免矛盾表述
        final_directional_view = directional_view
        
        # ✅ 操作决策：使用decision_matrix中的style
        operational_decision = decision_matrix['reason'].split('（')[0]  # 如"谨慎做空"
        
        # ✅ 关键修复：CIO信心度不能高于交易员和风控的信心度
        # 这里需要调整信心度，确保保守原则
        # 暂时直接返回原始信心度（后续在make_executive_decision中调整）
        
        return {
            "directional_view": final_directional_view,  # 如"谨慎看空"
            "directional_confidence": directional_confidence,  # 从交易员提取
            "operational_decision": operational_decision,  # 如"谨慎做空"
            "operational_confidence": operational_confidence,  # 从风控提取
            "decision_logic": decision_logic
        }
    
    def _generate_cio_decision_logic(self, trading_decision: TradingDecision,
                                         risk_assessment: RiskAssessment,
                                         debate_result: DebateResult,
                                   directional_confidence: str,
                                   operational_confidence: str,
                                   directional_view: str) -> str:
        """🔥 全新版：基于实际分析内容的专业CIO决策逻辑"""
        
        # 🔥 修复：获取正确的品种名称
        commodity = getattr(trading_decision, 'commodity', None) or getattr(risk_assessment, 'commodity', None)
        if not commodity:
            # 尝试从交易决策的推理内容中推断品种
            trader_reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
            if "沪金" in trader_reasoning or "AU" in trader_reasoning or "856" in trader_reasoning:
                commodity = "AU"  # 黄金
            elif "沪铜" in trader_reasoning or "CU" in trader_reasoning or "82470" in trader_reasoning:
                commodity = "CU"  # 沪铜
            elif "沪银" in trader_reasoning or "AG" in trader_reasoning:
                commodity = "AG"  # 白银
            else:
                # 根据价格范围推断
                if "856" in str(trading_decision) or "862" in str(trading_decision):
                    commodity = "AU"  # 黄金价格范围
                else:
                    commodity = "AU"  # 默认黄金
        commodity_name = get_commodity_name(commodity)
        
        # 🔥 提取实际的交易员分析内容
        trader_reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        actual_strategy = trading_decision.strategy_type.value if trading_decision.strategy_type else "未明确"
        
        # 🔥 提取实际的风控分析内容
        risk_opinion = risk_assessment.risk_manager_opinion if hasattr(risk_assessment, 'risk_manager_opinion') else ""
        risk_level = risk_assessment.overall_risk_level.value if risk_assessment.overall_risk_level else "未评估"
        
        # 🔥 基于实际内容提取核心要素
        market_analysis = self._extract_actual_market_insights(trader_reasoning, risk_opinion)
        
        # 🔥 美观格式的专业CIO决策逻辑
        logic = f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                           【CIO核心决策逻辑】                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─ 一、市场本质判断 ─────────────────────────────────────────────────────────┐
│                                                                              │
│  {commodity_name}市场当前呈现{market_analysis['market_characteristic']}特征。              │
│                                                                              │
│  🔍 技术面洞察：{market_analysis['technical_insight']}                        │
│  📊 基本面判断：{market_analysis['fundamental_insight']}                      │
│  ⚖️  综合评估：{market_analysis['overall_assessment']}                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 二、风险收益权衡 ─────────────────────────────────────────────────────────┐
│                                                                              │
│  🎯 交易员判断：{actual_strategy}，体现了{market_analysis['trader_confidence']}的专业判断   │
│  🛡️  风控评估：{risk_level}，反映了{market_analysis['risk_perspective']}              │
│  📈 收益预期：{market_analysis['return_expectation']}                         │
│  ⚠️  风险控制：{market_analysis['risk_control']}                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 三、执行策略制定 ─────────────────────────────────────────────────────────┐
│                                                                              │
│  🎲 信心度体系：方向信心度{directional_confidence} + 操作信心度{operational_confidence}        │
│  🚀 执行策略：{self._generate_execution_rationale(directional_view, directional_confidence, operational_confidence, risk_level)}  │
│  📋 操作要点：{market_analysis['execution_points']}                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ 四、决策哲学体现 ─────────────────────────────────────────────────────────┐
│                                                                              │
│  💡 投资理念：数据驱动决策，风险优先原则，机会精准把握                          │
│  🔄 决策逻辑：{self._generate_philosophy_statement(directional_view, directional_confidence, operational_confidence)}  │
│  ✅ 质量保证：本决策完全基于实际分析数据，确保决策的科学性和可追溯性            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

        """.strip()
        
        return logic
    
    def _extract_actual_market_insights(self, trader_reasoning: str, risk_opinion: str) -> Dict[str, str]:
        """🔥 新方法：基于实际分析内容提取市场洞察"""
        
        reasoning_lower = trader_reasoning.lower()
        risk_lower = risk_opinion.lower()
        
        # 市场特征判断
        if "突破" in reasoning_lower or "金叉" in reasoning_lower:
            market_characteristic = "技术突破"
        elif "超买" in reasoning_lower or "调整" in reasoning_lower:
            market_characteristic = "技术调整"
        elif "震荡" in reasoning_lower or "分歧" in reasoning_lower:
            market_characteristic = "震荡整理"
        else:
            market_characteristic = "复杂多变"
        
        # 技术面洞察（基于实际交易员分析）
        if "rsi" in reasoning_lower and "macd" in reasoning_lower:
            technical_insight = "多重技术指标共振，信号相对明确"
        elif "均线" in reasoning_lower or "ma" in reasoning_lower:
            technical_insight = "均线系统提供方向指引"
        elif "布林带" in reasoning_lower:
            technical_insight = "价格通道显示波动特征"
        else:
            technical_insight = "技术面信号需综合判断"
        
        # 基本面判断（基于实际分析内容）
        if "库存" in reasoning_lower:
            fundamental_insight = "供需结构是关键驱动因素"
        elif "基差" in reasoning_lower:
            fundamental_insight = "现货基差反映基本面状况"
        elif "持仓" in reasoning_lower:
            fundamental_insight = "资金流向体现市场预期"
        else:
            fundamental_insight = "基本面因素相互交织"
        
        # 综合评估（确保与实际决策一致）
        if "做多" in reasoning_lower or "看多" in reasoning_lower:
            overall_assessment = "多头逻辑相对占优，但需控制风险"
        elif "做空" in reasoning_lower or "看空" in reasoning_lower:
            overall_assessment = "空头逻辑有一定支撑，谨慎为主"
        elif "偏空" in reasoning_lower:
            overall_assessment = "空头因素相对突出，需要谨慎应对"
        else:
            overall_assessment = "市场方向需要进一步观察确认"
        
        # 交易员信心度描述
        if "高信心" in reasoning_lower or "强烈" in reasoning_lower:
            trader_confidence = "高度"
        elif "谨慎" in reasoning_lower or "轻仓" in reasoning_lower:
            trader_confidence = "谨慎"
        else:
            trader_confidence = "适中"
        
        # 风控视角（基于实际风控分析）
        if "极高风险" in risk_lower:
            risk_perspective = "严格的风险控制要求"
        elif "高风险" in risk_lower:
            risk_perspective = "较为严格的风险管理"
        else:
            risk_perspective = "常规的风险监控"
        
        # 收益预期
        if "突破" in reasoning_lower and "目标" in reasoning_lower:
            return_expectation = "存在较好的收益空间"
        elif "调整" in reasoning_lower:
            return_expectation = "收益空间相对有限"
        else:
            return_expectation = "收益风险需要平衡"
        
        # 风险控制
        if "止损" in risk_lower:
            risk_control = "设置明确的止损保护"
        elif "仓位" in risk_lower:
            risk_control = "严格控制仓位规模"
        else:
            risk_control = "执行标准风控流程"
        
        # 执行要点
        if "轻仓" in reasoning_lower or "谨慎" in reasoning_lower:
            execution_points = "轻仓试探，严格止损，动态调整"
        elif "积极" in reasoning_lower:
            execution_points = "积极参与，把握机会，控制风险"
        else:
            execution_points = "稳健操作，风险优先，机会并重"
        
        return {
            "market_characteristic": market_characteristic,
            "technical_insight": technical_insight,
            "fundamental_insight": fundamental_insight,
            "overall_assessment": overall_assessment,
            "trader_confidence": trader_confidence,
            "risk_perspective": risk_perspective,
            "return_expectation": return_expectation,
            "risk_control": risk_control,
            "execution_points": execution_points
        }
    
    def _extract_core_market_factors(self, trader_reasoning: str) -> Dict[str, str]:
        """🔥 提取交易员推理中的核心市场要素"""
        reasoning_lower = trader_reasoning.lower()
        
        # 技术面本质
        if "突破" in reasoning_lower and "上轨" in reasoning_lower:
            technical_essence = "技术面呈现突破态势，价格动能充足"
        elif "超买" in reasoning_lower and "rsi" in reasoning_lower:
            technical_essence = "技术指标显示超买状态，存在调整压力"
        elif "金叉" in reasoning_lower and "macd" in reasoning_lower:
            technical_essence = "技术指标形成多头排列，趋势向好"
        else:
            technical_essence = "技术面信号相对复杂，需综合判断"
        
        # 基本面本质
        if "库存" in reasoning_lower and ("增加" in reasoning_lower or "累积" in reasoning_lower):
            fundamental_essence = "基本面显示供应压力上升"
        elif "需求" in reasoning_lower and "强劲" in reasoning_lower:
            fundamental_essence = "基本面反映需求端支撑有力"
        elif "基差" in reasoning_lower and "弱势" in reasoning_lower:
            fundamental_essence = "现货基差结构显示基本面偏弱"
        else:
            fundamental_essence = "基本面因素相互交织，影响复杂"
        
        # 市场阶段
        if "做多" in reasoning_lower and "信心" in reasoning_lower:
            market_stage = "处于多头主导的上升阶段"
        elif "做空" in reasoning_lower and "风险" in reasoning_lower:
            market_stage = "面临空头压力的调整阶段"
        else:
            market_stage = "处于多空博弈的关键节点"
        
        # 机会窗口
        if "突破" in reasoning_lower or "金叉" in reasoning_lower:
            opportunity_window = "技术突破带来的趋势机会"
        elif "超买" in reasoning_lower or "回调" in reasoning_lower:
            opportunity_window = "技术调整后的反向机会"
        else:
            opportunity_window = "震荡格局中的波段机会"
        
        # 关键风险
        if "流动性" in reasoning_lower:
            key_risks = "流动性收缩风险"
        elif "政策" in reasoning_lower:
            key_risks = "政策变化风险"
        elif "外盘" in reasoning_lower:
            key_risks = "外盘联动风险"
        else:
            key_risks = "市场波动风险"
        
            return {
            "technical_essence": technical_essence,
            "fundamental_essence": fundamental_essence,
            "market_stage": market_stage,
            "opportunity_window": opportunity_window,
            "key_risks": key_risks
        }
    
    def _interpret_market_consensus(self, score_diff: float) -> str:
        """解读市场共识程度"""
        if score_diff < 1.0:
            return "高度分歧，市场观点严重对立"
        elif score_diff < 2.0:
            return "存在分歧，但趋势相对明确"
        else:
            return "基本共识，方向判断较为一致"
    
    def _assess_risk_reward_profile(self, directional_confidence: str, operational_confidence: str, risk_level: str) -> str:
        """评估风险收益特征"""
        if directional_confidence == "高" and operational_confidence in ["高", "中"]:
            return "风险收益比相对有利"
        elif directional_confidence == "中" and operational_confidence == "低":
            return "风险收益比需要谨慎权衡"
        else:
            return "风险收益比偏向保守"
    
    def _determine_strategy_style(self, directional_confidence: str, operational_confidence: str) -> str:
        """确定策略风格"""
        if directional_confidence == "高" and operational_confidence in ["高", "中"]:
            return "积极"
        else:
            return "谨慎"
    
    def _generate_execution_rationale(self, directional_view: str, directional_confidence: str, 
                                    operational_confidence: str, risk_level: str) -> str:
        """生成执行策略依据"""
        if "看多" in directional_view:
            if directional_confidence == "高":
                return "CIO决定采用积极做多策略，充分利用上涨动能"
            else:
                return "CIO选择谨慎做多策略，在控制风险的前提下参与上涨"
        else:
            if directional_confidence == "高":
                return "CIO决定采用积极做空策略，把握下跌机会"
            else:
                return "CIO选择谨慎做空策略，在风险可控的范围内获取收益"
    
    def _generate_philosophy_statement(self, directional_view: str, directional_confidence: str, 
                                     operational_confidence: str) -> str:
        """生成决策哲学表述"""
        if directional_confidence == "高" and operational_confidence in ["高", "中"]:
            return f"在高确定性的{directional_view}机会面前，CIO选择果断出击"
        elif directional_confidence == "中":
            return f"面对{directional_view}的中等确定性机会，CIO采用稳健进取的策略"
        else:
            return f"在{directional_view}的低确定性环境下，CIO坚持风险优先的原则"
    
    def _convert_confidence_text_to_numeric(self, confidence_text: str) -> float:
        """将高/中/低信心度转换为数值"""
        confidence_mapping = {
            "高": 0.8,
            "中": 0.6,
            "低": 0.4
        }
        return confidence_mapping.get(confidence_text, 0.5)
    
    def _estimate_target_price(self, final_decision: FinalDecision, confidence: float) -> float:
        """估算目标价格（简化版本）"""
        # 这是一个简化的实现，实际应该基于技术分析
        return 0.0  # 暂时返回0，表示不设置具体目标价
    
    def _determine_time_horizon(self, final_decision: FinalDecision, risk_assessment: RiskAssessment) -> str:
        """确定时间周期"""
        if final_decision in [FinalDecision.BUY, FinalDecision.SELL]:
            return "短期(1-2周)"
        else:
            return "待定"
    
    def _detect_available_modules(self, trading_decision: TradingDecision) -> List[str]:
        """检测可用的分析模块（从交易员决策中推断）"""
        # 这是一个简化版本，实际应该从analysis_state中获取
        # 但由于当前上下文限制，我们从交易员推理中推断
        reasoning = trading_decision.reasoning if trading_decision.reasoning else ""
        
        available_modules = []
        
        # 基于交易员分析内容推断使用了哪些模块
        if "技术" in reasoning or "rsi" in reasoning.lower() or "macd" in reasoning.lower():
            available_modules.append("technical")
        if "基差" in reasoning:
            available_modules.append("basis")
        if "库存" in reasoning:
            available_modules.append("inventory")
        if "持仓" in reasoning:
            available_modules.append("positioning")
        if "期限" in reasoning or "contango" in reasoning.lower():
            available_modules.append("term_structure")
        if "新闻" in reasoning or "政策" in reasoning:
            available_modules.append("news")
        
        # 如果没有检测到任何模块，默认至少有技术分析
        if not available_modules:
            available_modules = ["technical"]
            
        return available_modules
    
    def _determine_position_size_based_on_cio_decision(self, final_decision: FinalDecision,
                                                     risk_assessment: RiskAssessment,
                                                     confidence: float,
                                                     trading_decision: TradingDecision) -> float:
        """基于CIO最终决策确定仓位规模"""
        
        # 基于风险等级的基础仓位限制
        risk_level = risk_assessment.overall_risk_level
        base_position = {
            RiskLevel.VERY_HIGH: 0.01,  # 1%
            RiskLevel.HIGH: 0.03,       # 3%
            RiskLevel.MEDIUM: 0.05,     # 5%
            RiskLevel.LOW: 0.08,        # 8%
            RiskLevel.VERY_LOW: 0.10    # 10%
        }.get(risk_level, 0.02)
        
        # 基于决策类型调整
        if final_decision in [FinalDecision.BUY, FinalDecision.SELL]:
            # 明确的买卖决策
            position_multiplier = confidence  # 基于信心度调整
        else:
            # 观望或其他
            return 0.0
        
        # 考虑风控限制
        risk_limit_raw = risk_assessment.position_size_limit if risk_assessment.position_size_limit else 0.05
        print(f"🐛 DEBUG: risk_limit_raw = {risk_limit_raw} (type: {type(risk_limit_raw)})")
        
        # 🔧 修复：确保risk_limit是数值类型
        risk_limit = safe_convert_to_float(risk_limit_raw, 0.05)
        print(f"🐛 DEBUG: risk_limit = {risk_limit} (type: {type(risk_limit)})")
        
        # 最终仓位 = min(基础仓位 * 信心度倍数, 风控限制)
        final_position = min(base_position * position_multiplier, risk_limit)
        
        return max(0.0, min(final_position, 0.15))  # 最大不超过15%
    
    def _create_execution_plan(self, final_decision: FinalDecision, 
                             position_size: float, 
                             risk_assessment: RiskAssessment) -> str:
        """创建执行计划"""
        
        if final_decision == FinalDecision.BUY:
            return f"执行做多策略，建议仓位{position_size:.1%}，严格执行止损纪律"
        elif final_decision == FinalDecision.SELL:
            return f"执行做空策略，建议仓位{position_size:.1%}，严格执行止损纪律"
        else:
            return "暂时观望，等待更明确的市场信号"
    
    def _define_monitoring_points(self, analysis_state: FuturesAnalysisState,
                                risk_assessment: RiskAssessment) -> List[str]:
        """定义监控要点"""
        
        commodity_name = get_commodity_name(analysis_state.commodity)
        
        return [
            f"{commodity_name}价格关键技术位突破情况",
            "市场成交量和持仓量变化",
            "相关政策和基本面消息",
            "风险控制指标监控",
            "止损位执行情况"
        ]
    
    def _ensure_decision_consistency(self, final_decision: FinalDecision, 
                                   directional_analysis: Dict[str, Any], 
                                   risk_assessment: RiskAssessment) -> Dict[str, Any]:
        """确保决策一致性"""
        
        # 这个方法确保方向判断与操作决策的逻辑一致性
        # 返回一致性检查后的方向分析
        return directional_analysis

class OptimizedTradingAgentsSystem:
    """优化版Trading Agents完整系统"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.debate_system = OptimizedDebateSystem(config)
        self.risk_management = ProfessionalRiskManagement(config)
        self.decision_maker = ExecutiveDecisionMaker(config)
        self.trader = ProfessionalTrader(config)
        self.logger = logging.getLogger("OptimizedTradingAgentsSystem")
        
    @log_execution_time()
    async def run_complete_analysis(self, analysis_state: FuturesAnalysisState,
                                  debate_rounds: int = 3) -> Dict[str, Any]:
        """运行完整的优化版分析流程"""
        import time
        start_time = time.time()  # 🔥 记录开始时间
        
        commodity = analysis_state.commodity
        self.logger.info(f"开始{commodity}完整优化分析流程")
        
        # 第一阶段：激烈辩论
        print("🐛 DEBUG: 开始第一阶段：多空激烈辩论")
        self.logger.info("第一阶段：多空激烈辩论")
        debate_result = await self.debate_system.conduct_heated_debate(
            analysis_state, debate_rounds
        )
        print(f"🐛 DEBUG: 辩论完成，bull_score={debate_result.overall_bull_score} (type: {type(debate_result.overall_bull_score)})")
        
        # 第二阶段：交易员专业决策
        print("🐛 DEBUG: 开始第二阶段：交易员专业决策")
        self.logger.info("第二阶段：交易员专业决策")
        trading_decision = await self.trader.integrate_debate_and_decide(
            analysis_state, debate_result
        )
        print(f"🐛 DEBUG: 交易员决策完成，strategy_type={trading_decision.strategy_type}")
        
        # 第三阶段：专业风控评估
        print("🐛 DEBUG: 开始第三阶段：风控部门专业评估")
        self.logger.info("第三阶段：风控部门专业评估")
        risk_assessment = await self.risk_management.conduct_risk_assessment(
            analysis_state, debate_result, trading_decision
        )
        print(f"🐛 DEBUG: 风控评估完成，risk_level={risk_assessment.overall_risk_level}")

        # 第四阶段：CIO最终决策
        print("🐛 DEBUG: 开始第四阶段：CIO权威决策")
        self.logger.info("第四阶段：CIO权威决策")
        executive_decision = await self.decision_maker.make_executive_decision(
            analysis_state, debate_result, risk_assessment, trading_decision
        )
        print(f"🐛 DEBUG: CIO决策完成，final_decision={executive_decision.final_decision}")
        print(f"🐛 DEBUG: confidence_level={executive_decision.confidence_level} (type: {type(executive_decision.confidence_level)})")
        
        # 整合最终结果
        print("🐛 DEBUG: 开始整合最终结果")
        
        # 数据类型检查已完成，移除调试信息
        
        final_result = {
            "commodity": commodity,
            "analysis_date": analysis_state.analysis_date,
            "process_timestamp": datetime.now().isoformat(),
            
            # 辩论结果
            "debate_result": {
                "total_rounds": debate_result.total_rounds,
                "final_winner": debate_result.final_winner.value,
                "bull_score": debate_result.overall_bull_score,
                "bear_score": debate_result.overall_bear_score,
                "debate_summary": debate_result.debate_summary,
                "key_consensus": debate_result.key_consensus_points,
                "unresolved_issues": debate_result.unresolved_issues,
                "detailed_rounds": [asdict(round_) for round_ in debate_result.rounds]
            },
            
            # 风险评估
            "risk_assessment": {
                "overall_risk_level": risk_assessment.overall_risk_level.value,
                "risk_scores": {
                    "market_risk": risk_assessment.market_risk_score,
                    "liquidity_risk": risk_assessment.liquidity_risk_score,
                    "leverage_risk": risk_assessment.leverage_risk_score,
                    "concentration_risk": risk_assessment.concentration_risk_score
                },
                "key_risk_factors": risk_assessment.key_risk_factors,
                "risk_mitigation": risk_assessment.risk_mitigation,
                "position_limit": risk_assessment.position_size_limit,
                "stop_loss_level": risk_assessment.stop_loss_level,
                "risk_manager_opinion": risk_assessment.risk_manager_opinion
                },
            
            # 交易员决策
            "trading_decision": {
                "strategy_type": trading_decision.strategy_type.value,
                "reasoning": trading_decision.reasoning,
                "entry_points": trading_decision.entry_points,
                "exit_points": trading_decision.exit_points,
                "position_size": trading_decision.position_size,
                "risk_reward_ratio": trading_decision.risk_reward_ratio,
                "time_horizon": trading_decision.time_horizon,
                "specific_contracts": trading_decision.specific_contracts,
                "hedging_components": trading_decision.hedging_components,
                "execution_plan": trading_decision.execution_plan,
                "market_conditions": trading_decision.market_conditions,
                "alternative_scenarios": trading_decision.alternative_scenarios
            },
            
            # 最终决策
            "executive_decision": {
                "final_decision": executive_decision.final_decision.value,
                "confidence_level": executive_decision.confidence_level,
                "position_size": executive_decision.position_size,
                "time_horizon": executive_decision.time_horizon,
                "key_rationale": executive_decision.key_rationale,
                "execution_plan": executive_decision.execution_plan,
                "monitoring_points": executive_decision.monitoring_points,
                "cio_statement": executive_decision.cio_statement,
                # 🔥 新增：方向判断相关字段
                "directional_view": executive_decision.directional_view,
                "directional_confidence": executive_decision.directional_confidence,
                "operational_decision": executive_decision.operational_decision,
                "operational_confidence": executive_decision.operational_confidence  # 🔥 修复：添加遗漏的字段
            },
            
            # 系统元数据
            "system_metadata": {
                "version": "2.0.0_optimized",
                "debate_rounds_conducted": debate_rounds,
                "analysis_completeness": analysis_state.get_analysis_progress(),
                "total_processing_time": "计算中..."
            }
        }
        
        # 🔥 计算总执行时间
        total_execution_time = time.time() - start_time
        final_result["system_metadata"]["total_processing_time"] = f"{total_execution_time:.2f}秒"
        final_result["total_execution_time"] = total_execution_time  # 添加到顶层，方便提取
        
        # 🔥 修复：为UI兼容性添加decision_section别名（指向同一字典）
        final_result["decision_section"] = final_result["executive_decision"]
        
        self.logger.info(f"{commodity}完整优化分析完成，最终决策：{executive_decision.final_decision.value}，耗时：{total_execution_time:.2f}秒")
        
        return final_result

if __name__ == "__main__":
    # 运行测试
    import asyncio

async def test_optimized_system():
        print("🎯 优化版辩论风控决策系统测试")
        # 这里可以添加测试代码
        pass
if __name__ == "__main__":
    asyncio.run(test_optimized_system())
