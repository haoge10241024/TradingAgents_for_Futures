#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 风险管理团队模块
包含激进、保守、中性三种风险评估Agent和风险经理

功能特点：
1. 多角度风险评估和管理
2. 激进、保守、中性三种风险偏好
3. 风险经理协调和最终决策
4. 完整的风险控制体系
5. 期货市场专用风险模型

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# 导入基础模块
from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState,
    AnalysisStatus
)
from 期货TradingAgents系统_交易员 import (
    TradingDecision,
    TradingDirection,
    RiskParameters
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    DataValidator,
    TimeUtils,
    log_execution_time,
    retry_on_failure
)

# ============================================================================
# 1. 风险管理核心数据结构
# ============================================================================

class RiskLevel(Enum):
    """风险等级"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class RiskType(Enum):
    """风险类型"""
    MARKET_RISK = "market_risk"        # 市场风险
    LIQUIDITY_RISK = "liquidity_risk"  # 流动性风险
    CREDIT_RISK = "credit_risk"        # 信用风险
    OPERATIONAL_RISK = "operational_risk" # 操作风险
    LEVERAGE_RISK = "leverage_risk"    # 杠杆风险
    CONCENTRATION_RISK = "concentration_risk" # 集中度风险

class RiskAction(Enum):
    """风险行动"""
    APPROVE = "approve"           # 批准
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"  # 有条件批准
    MODIFY = "modify"            # 修改建议
    REJECT = "reject"            # 拒绝
    DEFER = "defer"              # 延期

@dataclass
class RiskFactor:
    """风险因素"""
    risk_type: RiskType
    description: str
    probability: float  # 发生概率 (0-1)
    impact: float      # 影响程度 (0-1)
    severity: RiskLevel
    mitigation: str    # 缓解措施
    monitoring: str    # 监控方法

@dataclass
class RiskAssessment:
    """风险评估"""
    assessor_type: str  # "aggressive", "conservative", "neutral"
    overall_risk_level: RiskLevel
    risk_score: float  # 风险评分 (0-100)
    
    # 风险因素
    identified_risks: List[RiskFactor] = None
    
    # 风险指标
    var_estimate: float = 0.0           # VaR估计
    expected_shortfall: float = 0.0     # 期望损失
    max_drawdown_estimate: float = 0.0  # 最大回撤估计
    sharpe_ratio_estimate: float = 0.0  # 夏普比率估计
    
    # 建议
    recommendation: RiskAction = RiskAction.DEFER
    position_adjustment: float = 1.0    # 仓位调整倍数 (0-2)
    additional_conditions: List[str] = None
    
    # 推理过程
    reasoning: str = ""
    
    # 时间信息
    assessment_timestamp: str = ""

@dataclass
class RiskDebateResult:
    """风险辩论结果"""
    commodity: str
    analysis_date: str
    
    # 三方评估
    aggressive_assessment: RiskAssessment = None
    conservative_assessment: RiskAssessment = None
    neutral_assessment: RiskAssessment = None
    
    # 辩论过程
    debate_rounds: int = 0
    consensus_reached: bool = False
    key_disagreements: List[str] = None
    
    # 最终结果
    final_risk_level: RiskLevel = RiskLevel.MEDIUM
    final_recommendation: RiskAction = RiskAction.DEFER
    final_position_adjustment: float = 1.0
    
    # 风险经理决策
    risk_manager_decision: Dict = None
    
    # 元数据
    debate_timestamp: str = ""
    debate_quality: float = 0.0

# ============================================================================
# 2. 风险评估Agent基类
# ============================================================================

class BaseRiskAgent:
    """风险评估Agent基类"""
    
    def __init__(self, config: Dict, risk_stance: str):
        self.config = config
        self.risk_stance = risk_stance  # "aggressive", "conservative", "neutral"
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 风险配置
        risk_config = config.get("risk_management", {}).get("risk_agents", {}).get(f"{risk_stance}_risk", {})
        self.risk_appetite = risk_config.get("risk_appetite", "medium")
        self.max_position_size = risk_config.get("max_position_size", 0.2)
        
        # 日志
        self.logger = logging.getLogger(f"RiskAgent_{risk_stance.title()}")
        
    async def assess_trading_decision(self, trading_decision: TradingDecision,
                                    analysis_state: FuturesAnalysisState) -> RiskAssessment:
        """评估交易决策的风险"""
        
        self.logger.info(f"开始{self.risk_stance}风险评估: {trading_decision.commodity}")
        
        # 1. 识别风险因素
        risk_factors = await self._identify_risk_factors(trading_decision, analysis_state)
        
        # 2. 计算风险指标
        risk_metrics = await self._calculate_risk_metrics(trading_decision, analysis_state)
        
        # 3. 评估整体风险水平
        overall_risk_level = self._assess_overall_risk_level(risk_factors, risk_metrics)
        
        # 4. 计算风险评分
        risk_score = self._calculate_risk_score(risk_factors, risk_metrics)
        
        # 5. 生成建议
        recommendation, position_adjustment, conditions = await self._generate_recommendation(
            trading_decision, overall_risk_level, risk_score
        )
        
        # 6. 生成推理过程
        reasoning = await self._generate_reasoning(
            trading_decision, risk_factors, overall_risk_level, recommendation
        )
        
        assessment = RiskAssessment(
            assessor_type=self.risk_stance,
            overall_risk_level=overall_risk_level,
            risk_score=risk_score,
            identified_risks=risk_factors,
            var_estimate=risk_metrics.get("var", 0.0),
            expected_shortfall=risk_metrics.get("es", 0.0),
            max_drawdown_estimate=risk_metrics.get("max_dd", 0.0),
            sharpe_ratio_estimate=risk_metrics.get("sharpe", 0.0),
            recommendation=recommendation,
            position_adjustment=position_adjustment,
            additional_conditions=conditions,
            reasoning=reasoning,
            assessment_timestamp=datetime.now().isoformat()
        )
        
        self.logger.info(f"{self.risk_stance}风险评估完成: {overall_risk_level.value}, 建议: {recommendation.value}")
        
        return assessment
    
    async def _identify_risk_factors(self, trading_decision: TradingDecision,
                                   analysis_state: FuturesAnalysisState) -> List[RiskFactor]:
        """识别风险因素"""
        
        risk_factors = []
        
        # 市场风险
        market_risk = self._assess_market_risk(trading_decision, analysis_state)
        if market_risk:
            risk_factors.append(market_risk)
        
        # 流动性风险
        liquidity_risk = self._assess_liquidity_risk(trading_decision, analysis_state)
        if liquidity_risk:
            risk_factors.append(liquidity_risk)
        
        # 杠杆风险
        leverage_risk = self._assess_leverage_risk(trading_decision)
        if leverage_risk:
            risk_factors.append(leverage_risk)
        
        # 集中度风险
        concentration_risk = self._assess_concentration_risk(trading_decision)
        if concentration_risk:
            risk_factors.append(concentration_risk)
        
        return risk_factors
    
    def _assess_market_risk(self, trading_decision: TradingDecision,
                          analysis_state: FuturesAnalysisState) -> Optional[RiskFactor]:
        """评估市场风险"""
        
        # 基于交易策略的预期波动率评估市场风险
        expected_volatility = trading_decision.trading_strategy.expected_volatility
        
        if expected_volatility > 0.3:  # 高波动率
            severity = RiskLevel.HIGH
            probability = 0.7
            description = f"市场波动率预期达到{expected_volatility:.1%}，存在较高市场风险"
        elif expected_volatility > 0.2:  # 中等波动率
            severity = RiskLevel.MEDIUM
            probability = 0.5
            description = f"市场波动率预期{expected_volatility:.1%}，存在中等市场风险"
        else:  # 低波动率
            severity = RiskLevel.LOW
            probability = 0.3
            description = f"市场波动率预期{expected_volatility:.1%}，市场风险相对较低"
        
        # 根据风险立场调整评估
        risk_level_order = [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        current_index = risk_level_order.index(severity)
        
        if self.risk_stance == "conservative":
            new_index = min(4, current_index + 1)
            severity = risk_level_order[new_index]
            probability = min(1.0, probability + 0.2)
        elif self.risk_stance == "aggressive":
            new_index = max(0, current_index - 1)
            severity = risk_level_order[new_index]
            probability = max(0.1, probability - 0.2)
        
        return RiskFactor(
            risk_type=RiskType.MARKET_RISK,
            description=description,
            probability=probability,
            impact=expected_volatility,
            severity=severity,
            mitigation="设置合理止损，控制仓位大小，分散投资",
            monitoring="监控价格波动率、技术指标、市场情绪变化"
        )
    
    def _assess_liquidity_risk(self, trading_decision: TradingDecision,
                             analysis_state: FuturesAnalysisState) -> Optional[RiskFactor]:
        """评估流动性风险"""
        
        # 简化的流动性风险评估
        position_size = trading_decision.position_sizing.position_percentage
        
        if position_size > 0.3:  # 大仓位
            severity = RiskLevel.HIGH
            probability = 0.6
            description = f"仓位比例{position_size:.1%}较大，可能面临流动性风险"
        elif position_size > 0.2:  # 中等仓位
            severity = RiskLevel.MEDIUM
            probability = 0.4
            description = f"仓位比例{position_size:.1%}中等，需关注流动性风险"
        else:
            return None  # 小仓位流动性风险较低
        
        # 风险立场调整
        risk_level_order = [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        current_index = risk_level_order.index(severity)
        
        if self.risk_stance == "conservative":
            new_index = min(4, current_index + 1)
            severity = risk_level_order[new_index]
        elif self.risk_stance == "aggressive":
            new_index = max(0, current_index - 1)
            severity = risk_level_order[new_index]
        
        return RiskFactor(
            risk_type=RiskType.LIQUIDITY_RISK,
            description=description,
            probability=probability,
            impact=position_size,
            severity=severity,
            mitigation="分批建仓，避免集中交易，选择活跃合约",
            monitoring="监控成交量、持仓量、买卖价差变化"
        )
    
    def _assess_leverage_risk(self, trading_decision: TradingDecision) -> Optional[RiskFactor]:
        """评估杠杆风险"""
        
        # 基于保证金比例评估杠杆风险
        margin_ratio = trading_decision.position_sizing.margin_required / (
            trading_decision.position_sizing.contract_quantity * 3500 * 10  # 简化计算
        ) if trading_decision.position_sizing.contract_quantity > 0 else 0.1
        
        leverage = 1 / margin_ratio if margin_ratio > 0 else 10
        
        if leverage > 15:  # 高杠杆
            severity = RiskLevel.VERY_HIGH
            probability = 0.8
            description = f"杠杆倍数约{leverage:.1f}倍，杠杆风险极高"
        elif leverage > 10:  # 中等杠杆
            severity = RiskLevel.HIGH
            probability = 0.6
            description = f"杠杆倍数约{leverage:.1f}倍，杠杆风险较高"
        elif leverage > 5:  # 低杠杆
            severity = RiskLevel.MEDIUM
            probability = 0.4
            description = f"杠杆倍数约{leverage:.1f}倍，杠杆风险中等"
        else:
            return None  # 极低杠杆风险
        
        # 风险立场调整
        risk_level_order = [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        current_index = risk_level_order.index(severity)
        
        if self.risk_stance == "conservative":
            new_index = min(4, current_index + 1)
            severity = risk_level_order[new_index]
        elif self.risk_stance == "aggressive":
            new_index = max(0, current_index - 1)
            severity = risk_level_order[new_index]
        
        return RiskFactor(
            risk_type=RiskType.LEVERAGE_RISK,
            description=description,
            probability=probability,
            impact=leverage / 20,  # 标准化影响程度
            severity=severity,
            mitigation="降低仓位，增加保证金，设置严格止损",
            monitoring="监控保证金使用率、账户权益变化、强制平仓风险"
        )
    
    def _assess_concentration_risk(self, trading_decision: TradingDecision) -> Optional[RiskFactor]:
        """评估集中度风险"""
        
        position_pct = trading_decision.position_sizing.position_percentage
        
        if position_pct > 0.4:  # 高集中度
            severity = RiskLevel.HIGH
            probability = 0.7
            description = f"单一品种仓位占比{position_pct:.1%}，集中度风险较高"
        elif position_pct > 0.25:  # 中等集中度
            severity = RiskLevel.MEDIUM
            probability = 0.5
            description = f"单一品种仓位占比{position_pct:.1%}，存在集中度风险"
        else:
            return None  # 低集中度风险
        
        # 风险立场调整
        risk_level_order = [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        current_index = risk_level_order.index(severity)
        
        if self.risk_stance == "conservative":
            new_index = min(4, current_index + 1)
            severity = risk_level_order[new_index]
        elif self.risk_stance == "aggressive":
            new_index = max(0, current_index - 1)
            severity = risk_level_order[new_index]
        
        return RiskFactor(
            risk_type=RiskType.CONCENTRATION_RISK,
            description=description,
            probability=probability,
            impact=position_pct,
            severity=severity,
            mitigation="分散投资，降低单一品种仓位，增加品种多样性",
            monitoring="监控投资组合集中度、相关性、分散化程度"
        )
    
    async def _calculate_risk_metrics(self, trading_decision: TradingDecision,
                                    analysis_state: FuturesAnalysisState) -> Dict[str, float]:
        """计算风险指标"""
        
        # 简化的风险指标计算
        expected_return = trading_decision.trading_strategy.expected_return
        expected_volatility = trading_decision.trading_strategy.expected_volatility
        position_size = trading_decision.position_sizing.position_percentage
        
        # VaR估计 (95%置信水平，1日)
        var_95 = 1.645 * expected_volatility * position_size
        
        # 期望损失 (Expected Shortfall)
        expected_shortfall = var_95 * 1.3  # 简化估算
        
        # 最大回撤估计
        max_drawdown = expected_volatility * 2 * position_size
        
        # 夏普比率估计
        risk_free_rate = 0.03  # 假设无风险利率3%
        sharpe_ratio = (expected_return - risk_free_rate) / expected_volatility if expected_volatility > 0 else 0
        
        return {
            "var": var_95,
            "es": expected_shortfall,
            "max_dd": max_drawdown,
            "sharpe": sharpe_ratio
        }
    
    def _assess_overall_risk_level(self, risk_factors: List[RiskFactor], 
                                 risk_metrics: Dict[str, float]) -> RiskLevel:
        """评估整体风险水平"""
        
        if not risk_factors:
            return RiskLevel.LOW
        
        # 计算风险因素的加权平均严重程度
        severity_scores = []
        for factor in risk_factors:
            severity_value = {
                RiskLevel.VERY_LOW: 1,
                RiskLevel.LOW: 2,
                RiskLevel.MEDIUM: 3,
                RiskLevel.HIGH: 4,
                RiskLevel.VERY_HIGH: 5
            }[factor.severity]
            
            # 按概率和影响加权
            weighted_score = severity_value * factor.probability * factor.impact
            severity_scores.append(weighted_score)
        
        avg_severity = sum(severity_scores) / len(severity_scores)
        
        # VaR调整
        var_adjustment = 0
        if risk_metrics.get("var", 0) > 0.1:  # 10%以上的VaR
            var_adjustment = 1
        elif risk_metrics.get("var", 0) > 0.05:  # 5-10%的VaR
            var_adjustment = 0.5
        
        final_score = avg_severity + var_adjustment
        
        # 根据风险立场调整
        if self.risk_stance == "conservative":
            final_score += 0.5
        elif self.risk_stance == "aggressive":
            final_score -= 0.5
        
        # 映射到风险等级
        if final_score >= 4.5:
            return RiskLevel.VERY_HIGH
        elif final_score >= 3.5:
            return RiskLevel.HIGH
        elif final_score >= 2.5:
            return RiskLevel.MEDIUM
        elif final_score >= 1.5:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _calculate_risk_score(self, risk_factors: List[RiskFactor], 
                            risk_metrics: Dict[str, float]) -> float:
        """计算风险评分 (0-100)"""
        
        base_score = 50  # 基础分数
        
        # 风险因素评分
        for factor in risk_factors:
            severity_impact = {
                RiskLevel.VERY_LOW: 5,
                RiskLevel.LOW: 10,
                RiskLevel.MEDIUM: 20,
                RiskLevel.HIGH: 35,
                RiskLevel.VERY_HIGH: 50
            }[factor.severity]
            
            base_score += severity_impact * factor.probability
        
        # VaR调整
        var_score = risk_metrics.get("var", 0) * 100
        base_score += var_score
        
        # 风险立场调整
        if self.risk_stance == "conservative":
            base_score *= 1.2
        elif self.risk_stance == "aggressive":
            base_score *= 0.8
        
        return min(100, max(0, base_score))
    
    async def _generate_recommendation(self, trading_decision: TradingDecision,
                                     risk_level: RiskLevel, 
                                     risk_score: float) -> Tuple[RiskAction, float, List[str]]:
        """生成风险建议"""
        
        conditions = []
        
        # 基于风险水平和立场生成建议
        if self.risk_stance == "aggressive":
            if risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]:
                recommendation = RiskAction.APPROVE
                position_adjustment = 1.2  # 可以适度增加仓位
            elif risk_level == RiskLevel.MEDIUM:
                recommendation = RiskAction.APPROVE
                position_adjustment = 1.0
            elif risk_level == RiskLevel.HIGH:
                recommendation = RiskAction.APPROVE_WITH_CONDITIONS
                position_adjustment = 0.8
                conditions = ["设置更严格的止损", "密切监控市场变化"]
            else:  # VERY_HIGH
                recommendation = RiskAction.MODIFY
                position_adjustment = 0.5
                conditions = ["大幅降低仓位", "增加对冲措施", "提高监控频率"]
                
        elif self.risk_stance == "conservative":
            if risk_level == RiskLevel.VERY_LOW:
                recommendation = RiskAction.APPROVE
                position_adjustment = 1.0
            elif risk_level == RiskLevel.LOW:
                recommendation = RiskAction.APPROVE_WITH_CONDITIONS
                position_adjustment = 0.9
                conditions = ["保持谨慎", "准备应急预案"]
            elif risk_level == RiskLevel.MEDIUM:
                recommendation = RiskAction.MODIFY
                position_adjustment = 0.7
                conditions = ["降低仓位", "增强风险监控", "设置保守止损"]
            elif risk_level == RiskLevel.HIGH:
                recommendation = RiskAction.REJECT
                position_adjustment = 0.3
                conditions = ["风险过高，不建议执行", "等待更好机会"]
            else:  # VERY_HIGH
                recommendation = RiskAction.REJECT
                position_adjustment = 0.0
                conditions = ["风险极高，强烈不建议", "暂停交易"]
                
        else:  # neutral
            if risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]:
                recommendation = RiskAction.APPROVE
                position_adjustment = 1.0
            elif risk_level == RiskLevel.MEDIUM:
                recommendation = RiskAction.APPROVE_WITH_CONDITIONS
                position_adjustment = 0.9
                conditions = ["适度控制风险", "保持监控"]
            elif risk_level == RiskLevel.HIGH:
                recommendation = RiskAction.MODIFY
                position_adjustment = 0.6
                conditions = ["降低仓位", "加强风险管理"]
            else:  # VERY_HIGH
                recommendation = RiskAction.REJECT
                position_adjustment = 0.4
                conditions = ["风险过高", "建议重新评估"]
        
        return recommendation, position_adjustment, conditions
    
    async def _generate_reasoning(self, trading_decision: TradingDecision,
                                risk_factors: List[RiskFactor],
                                risk_level: RiskLevel,
                                recommendation: RiskAction) -> str:
        """生成风险推理过程"""
        
        reasoning_parts = []
        
        # 风险立场声明
        stance_desc = {"aggressive": "激进", "conservative": "保守", "neutral": "中性"}
        reasoning_parts.append(f"基于{stance_desc[self.risk_stance]}风险评估立场")
        
        # 主要风险因素
        if risk_factors:
            main_risks = [f.risk_type.value for f in risk_factors[:2]]
            reasoning_parts.append(f"识别主要风险: {', '.join(main_risks)}")
        
        # 风险水平
        reasoning_parts.append(f"整体风险水平: {risk_level.value}")
        
        # 建议理由
        recommendation_reasons = {
            RiskAction.APPROVE: "风险可控，建议执行",
            RiskAction.APPROVE_WITH_CONDITIONS: "风险适中，有条件批准",
            RiskAction.MODIFY: "风险较高，建议修改",
            RiskAction.REJECT: "风险过高，不建议执行",
            RiskAction.DEFER: "需要更多信息"
        }
        reasoning_parts.append(recommendation_reasons[recommendation])
        
        return "; ".join(reasoning_parts)

# ============================================================================
# 3. 具体风险评估Agent
# ============================================================================

class AggressiveRiskAgent(BaseRiskAgent):
    """激进风险评估Agent"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "aggressive")
        self.logger.info("激进风险评估Agent初始化完成")

class ConservativeRiskAgent(BaseRiskAgent):
    """保守风险评估Agent"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "conservative")
        self.logger.info("保守风险评估Agent初始化完成")

class NeutralRiskAgent(BaseRiskAgent):
    """中性风险评估Agent"""
    
    def __init__(self, config: Dict):
        super().__init__(config, "neutral")
        self.logger.info("中性风险评估Agent初始化完成")

# ============================================================================
# 4. 风险经理
# ============================================================================

class FuturesRiskManager:
    """期货风险经理 - 协调风险评估，做出最终风险决策"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.role = "risk_manager"
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 风险管理配置
        risk_manager_config = config.get("risk_management", {}).get("risk_manager", {})
        self.var_confidence_level = risk_manager_config.get("var_confidence_level", 0.95)
        self.max_portfolio_risk = risk_manager_config.get("max_portfolio_risk", 0.02)
        
        # 创建风险评估Agent
        self.aggressive_agent = AggressiveRiskAgent(config)
        self.conservative_agent = ConservativeRiskAgent(config)
        self.neutral_agent = NeutralRiskAgent(config)
        
        # 日志
        self.logger = logging.getLogger("FuturesRiskManager")
        
    @log_execution_time()
    async def manage_risk_assessment(self, trading_decision: TradingDecision,
                                   analysis_state: FuturesAnalysisState) -> RiskDebateResult:
        """管理风险评估流程"""
        
        self.logger.info(f"开始风险评估管理: {trading_decision.commodity}")
        
        # 1. 并行执行三方风险评估
        self.logger.info("执行三方风险评估...")
        
        aggressive_task = self.aggressive_agent.assess_trading_decision(trading_decision, analysis_state)
        conservative_task = self.conservative_agent.assess_trading_decision(trading_decision, analysis_state)
        neutral_task = self.neutral_agent.assess_trading_decision(trading_decision, analysis_state)
        
        aggressive_assessment, conservative_assessment, neutral_assessment = await asyncio.gather(
            aggressive_task, conservative_task, neutral_task
        )
        
        # 2. 分析评估分歧
        key_disagreements = self._analyze_disagreements(
            aggressive_assessment, conservative_assessment, neutral_assessment
        )
        
        # 3. 进行风险辩论（如果需要）
        debate_rounds = 1  # 简化实现，实际可以根据分歧程度决定
        consensus_reached = self._check_consensus(
            aggressive_assessment, conservative_assessment, neutral_assessment
        )
        
        # 4. 形成最终风险决策
        final_decision = await self._make_final_risk_decision(
            trading_decision, aggressive_assessment, conservative_assessment, neutral_assessment
        )
        
        # 5. 构建风险辩论结果
        risk_debate_result = RiskDebateResult(
            commodity=trading_decision.commodity,
            analysis_date=trading_decision.analysis_date,
            aggressive_assessment=aggressive_assessment,
            conservative_assessment=conservative_assessment,
            neutral_assessment=neutral_assessment,
            debate_rounds=debate_rounds,
            consensus_reached=consensus_reached,
            key_disagreements=key_disagreements,
            final_risk_level=final_decision["risk_level"],
            final_recommendation=final_decision["recommendation"],
            final_position_adjustment=final_decision["position_adjustment"],
            risk_manager_decision=final_decision,
            debate_timestamp=datetime.now().isoformat(),
            debate_quality=self._calculate_debate_quality(
                aggressive_assessment, conservative_assessment, neutral_assessment
            )
        )
        
        self.logger.info(f"风险评估管理完成: {final_decision['recommendation'].value}")
        
        return risk_debate_result
    
    def _analyze_disagreements(self, aggressive: RiskAssessment,
                             conservative: RiskAssessment,
                             neutral: RiskAssessment) -> List[str]:
        """分析评估分歧"""
        
        disagreements = []
        
        # 风险水平分歧
        risk_levels = [aggressive.overall_risk_level, conservative.overall_risk_level, neutral.overall_risk_level]
        if len(set(risk_levels)) > 1:
            disagreements.append(f"风险水平评估分歧: 激进={aggressive.overall_risk_level.value}, "
                               f"保守={conservative.overall_risk_level.value}, "
                               f"中性={neutral.overall_risk_level.value}")
        
        # 建议分歧
        recommendations = [aggressive.recommendation, conservative.recommendation, neutral.recommendation]
        if len(set(recommendations)) > 1:
            disagreements.append(f"建议分歧: 激进={aggressive.recommendation.value}, "
                               f"保守={conservative.recommendation.value}, "
                               f"中性={neutral.recommendation.value}")
        
        # 仓位调整分歧
        adjustments = [aggressive.position_adjustment, conservative.position_adjustment, neutral.position_adjustment]
        if max(adjustments) - min(adjustments) > 0.3:  # 调整差异超过30%
            disagreements.append(f"仓位调整分歧: 激进={aggressive.position_adjustment:.1%}, "
                               f"保守={conservative.position_adjustment:.1%}, "
                               f"中性={neutral.position_adjustment:.1%}")
        
        return disagreements
    
    def _check_consensus(self, aggressive: RiskAssessment,
                        conservative: RiskAssessment,
                        neutral: RiskAssessment) -> bool:
        """检查是否达成共识"""
        
        # 简化的共识检查：如果建议相同或相近，认为达成共识
        recommendations = [aggressive.recommendation, conservative.recommendation, neutral.recommendation]
        
        # 如果所有建议相同
        if len(set(recommendations)) == 1:
            return True
        
        # 如果建议相近（都是批准类或都是拒绝类）
        approve_types = {RiskAction.APPROVE, RiskAction.APPROVE_WITH_CONDITIONS}
        reject_types = {RiskAction.REJECT, RiskAction.MODIFY}
        
        if all(r in approve_types for r in recommendations) or all(r in reject_types for r in recommendations):
            return True
        
        return False
    
    async def _make_final_risk_decision(self, trading_decision: TradingDecision,
                                      aggressive: RiskAssessment,
                                      conservative: RiskAssessment,
                                      neutral: RiskAssessment) -> Dict:
        """制定最终风险决策"""
        
        # 计算加权风险评分
        risk_scores = [aggressive.risk_score, conservative.risk_score, neutral.risk_score]
        
        # 权重设置：保守评估权重稍高，体现风险管理的谨慎原则
        weights = [0.25, 0.45, 0.30]  # 激进、保守、中性
        weighted_risk_score = sum(score * weight for score, weight in zip(risk_scores, weights))
        
        # 确定最终风险水平
        if weighted_risk_score >= 80:
            final_risk_level = RiskLevel.VERY_HIGH
        elif weighted_risk_score >= 65:
            final_risk_level = RiskLevel.HIGH
        elif weighted_risk_score >= 45:
            final_risk_level = RiskLevel.MEDIUM
        elif weighted_risk_score >= 25:
            final_risk_level = RiskLevel.LOW
        else:
            final_risk_level = RiskLevel.VERY_LOW
        
        # 基于最终风险水平确定建议
        if final_risk_level == RiskLevel.VERY_LOW:
            final_recommendation = RiskAction.APPROVE
            position_adjustment = 1.0
        elif final_risk_level == RiskLevel.LOW:
            final_recommendation = RiskAction.APPROVE
            position_adjustment = 1.0
        elif final_risk_level == RiskLevel.MEDIUM:
            final_recommendation = RiskAction.APPROVE_WITH_CONDITIONS
            position_adjustment = 0.9
        elif final_risk_level == RiskLevel.HIGH:
            final_recommendation = RiskAction.MODIFY
            position_adjustment = 0.7
        else:  # VERY_HIGH
            final_recommendation = RiskAction.REJECT
            position_adjustment = 0.5
        
        # 考虑保守评估的强烈反对
        if conservative.recommendation == RiskAction.REJECT and conservative.risk_score > 75:
            final_recommendation = RiskAction.MODIFY
            position_adjustment = min(position_adjustment, 0.6)
        
        # 生成最终决策推理
        reasoning = await self._generate_final_reasoning(
            trading_decision, aggressive, conservative, neutral, 
            final_risk_level, final_recommendation
        )
        
        return {
            "risk_level": final_risk_level,
            "recommendation": final_recommendation,
            "position_adjustment": position_adjustment,
            "weighted_risk_score": weighted_risk_score,
            "reasoning": reasoning,
            "decision_confidence": self._calculate_decision_confidence(aggressive, conservative, neutral),
            "monitoring_requirements": self._define_monitoring_requirements(final_risk_level),
            "review_triggers": self._define_review_triggers(final_risk_level)
        }
    
    def _calculate_debate_quality(self, aggressive: RiskAssessment,
                                conservative: RiskAssessment,
                                neutral: RiskAssessment) -> float:
        """计算辩论质量"""
        
        # 基于评估的详细程度和一致性计算质量
        base_quality = 7.0
        
        # 风险因素识别的完整性
        total_risks = len(aggressive.identified_risks) + len(conservative.identified_risks) + len(neutral.identified_risks)
        if total_risks >= 6:
            base_quality += 1.0
        elif total_risks >= 3:
            base_quality += 0.5
        
        # 评估的差异性（适度差异说明从不同角度考虑）
        risk_score_std = np.std([aggressive.risk_score, conservative.risk_score, neutral.risk_score])
        if 10 <= risk_score_std <= 25:  # 适度差异
            base_quality += 0.5
        elif risk_score_std > 30:  # 差异过大
            base_quality -= 0.5
        
        return min(10.0, max(5.0, base_quality))
    
    async def _generate_final_reasoning(self, trading_decision: TradingDecision,
                                      aggressive: RiskAssessment,
                                      conservative: RiskAssessment,
                                      neutral: RiskAssessment,
                                      final_risk_level: RiskLevel,
                                      final_recommendation: RiskAction) -> str:
        """生成严格实事求是的最终决策推理 - 禁止虚构任何数据"""
        
        reasoning_parts = []
        
        # 📋 数据来源声明
        reasoning_parts.append("【数据来源声明】本评估严格基于三方风险评估结果和交易员决策内容，未添加任何外部数据源。")
        
        # 评估概况 - 基于实际计算结果
        risk_scores = [aggressive.risk_score, conservative.risk_score, neutral.risk_score]
        avg_score = sum(risk_scores) / len(risk_scores)
        reasoning_parts.append(f"综合三方风险评估（激进{aggressive.risk_score:.1f}分、保守{conservative.risk_score:.1f}分、中性{neutral.risk_score:.1f}分），加权平均{avg_score:.1f}分，最终风险等级: {final_risk_level.value}")
        
        # 主要风险因素 - 仅基于三方实际识别的风险
        all_risks = aggressive.identified_risks + conservative.identified_risks + neutral.identified_risks
        if all_risks:
            risk_types = list(set([r.risk_type.value for r in all_risks]))
            reasoning_parts.append(f"识别到的主要风险类型: {', '.join(risk_types[:3])}（基于{len(all_risks)}个风险因素）")
        else:
            reasoning_parts.append("未识别到明确的风险因素")
        
        # 决策依据 - 基于实际评估结果
        reasoning_parts.append(f"基于风险管理谨慎原则，采取{final_recommendation.value}建议")
        
        # 评估一致性分析
        consensus_reached = self._check_consensus(aggressive, conservative, neutral)
        if consensus_reached:
            reasoning_parts.append("三方评估基本达成共识，风险判断相对一致")
        else:
            disagreement_points = []
            if abs(aggressive.risk_score - conservative.risk_score) > 20:
                disagreement_points.append("激进与保守评估存在显著分歧")
            if len(set([a.recommendation for a in [aggressive, conservative, neutral]])) > 1:
                disagreement_points.append("推荐行动存在分歧")
            
            if disagreement_points:
                reasoning_parts.append(f"评估分歧: {', '.join(disagreement_points)}，因此采用保守原则")
        
        # 基于交易决策的风险考量
        if trading_decision.position_sizing.position_percentage > 0.2:
            reasoning_parts.append("交易员建议仓位较高，需要严格的风险控制措施")
        
        # 禁止虚构的数据说明
        reasoning_parts.append("【重要说明】本评估未使用任何CFTC持仓数据、技术指标具体数值、历史统计概率等外部量化指标，所有判断均基于前序分析环节的实际输出")
        
        return "\n\n".join(reasoning_parts)
    
    def _calculate_decision_confidence(self, aggressive: RiskAssessment,
                                     conservative: RiskAssessment,
                                     neutral: RiskAssessment) -> float:
        """计算决策信心"""
        
        # 基于评估一致性计算信心
        recommendations = [aggressive.recommendation, conservative.recommendation, neutral.recommendation]
        
        if len(set(recommendations)) == 1:  # 完全一致
            return 0.9
        elif len(set(recommendations)) == 2:  # 部分一致
            return 0.7
        else:  # 完全不一致
            return 0.5
    
    def _define_monitoring_requirements(self, risk_level: RiskLevel) -> List[str]:
        """定义监控要求"""
        
        base_monitoring = ["价格变化监控", "仓位状态检查", "保证金水平监控"]
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            base_monitoring.extend([
                "实时风险指标监控",
                "市场异常情况预警",
                "强制平仓风险监控"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            base_monitoring.extend([
                "日内风险检查",
                "技术指标监控"
            ])
        
        return base_monitoring
    
    def _define_review_triggers(self, risk_level: RiskLevel) -> List[str]:
        """定义复审触发条件"""
        
        base_triggers = ["重大市场事件", "基本面发生重大变化"]
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            base_triggers.extend([
                "损失超过预期50%",
                "市场波动率急剧上升",
                "流动性显著恶化"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            base_triggers.extend([
                "损失超过预期100%",
                "技术指标发生重大变化"
            ])
        
        return base_triggers
    
    def get_risk_manager_info(self) -> Dict:
        """获取风险经理信息"""
        return {
            "name": "期货风险经理",
            "role": self.role,
            "var_confidence_level": self.var_confidence_level,
            "max_portfolio_risk": self.max_portfolio_risk,
            "risk_agents": ["aggressive", "conservative", "neutral"],
            "version": "1.0.0"
        }

# ============================================================================
# 5. 测试和演示代码
# ============================================================================

async def test_risk_management_team():
    """测试风险管理团队"""
    
    print("⚠️ 测试期货风险管理团队...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建风险经理
    risk_manager = FuturesRiskManager(config)
    
    print(f"风险经理信息: {risk_manager.get_risk_manager_info()}")
    
    # 创建模拟交易决策
    from 期货TradingAgents系统_交易员 import (
        TradingDecision, TradingSignal, PositionSizing, RiskParameters,
        TradingStrategy, ExecutionPlan, TradingDirection, PositionSizingMethod, OrderType
    )
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState
    
    # 模拟交易信号
    trading_signal = TradingSignal(
        direction=TradingDirection.LONG,
        strength=0.75,
        confidence=0.8,
        urgency="medium",
        reasoning="技术面突破确认，基本面支持"
    )
    
    # 模拟仓位配置
    position_sizing = PositionSizing(
        position_percentage=0.15,
        contract_quantity=3,
        margin_required=150000,
        max_loss_amount=50000,
        sizing_method=PositionSizingMethod.KELLY_CRITERION,
        reasoning="基于凯利公式计算"
    )
    
    # 模拟风险参数
    risk_parameters = RiskParameters(
        stop_loss_price=3325,
        stop_loss_percentage=0.05,
        take_profit_price=4025,
        take_profit_percentage=0.15,
        max_drawdown=50000,
        risk_reward_ratio=3.0,
        var_estimate=25000,
        confidence_interval=0.95
    )
    
    # 模拟交易策略
    trading_strategy = TradingStrategy(
        strategy_name="突破策略",
        entry_conditions=["价格突破关键阻力", "成交量配合"],
        exit_conditions=["触发止损", "达到止盈"],
        time_horizon="medium_term",
        strategy_type="breakout",
        expected_return=0.12,
        expected_volatility=0.20,
        win_rate=0.65,
        avg_win_loss_ratio=2.5
    )
    
    # 模拟执行计划
    execution_plan = ExecutionPlan(
        execution_timing="适时执行",
        order_type=OrderType.LIMIT,
        entry_price_target=3500,
        price_tolerance=7,
        execution_method="passive",
        market_impact_estimate=0.001,
        execution_cost_estimate=0.0005
    )
    
    # 创建交易决策
    trading_decision = TradingDecision(
        commodity="RB",
        analysis_date="2025-01-19",
        decision_timestamp=datetime.now().isoformat(),
        trading_signal=trading_signal,
        position_sizing=position_sizing,
        risk_parameters=risk_parameters,
        trading_strategy=trading_strategy,
        execution_plan=execution_plan,
        research_consensus_summary={"consensus_type": "bullish", "confidence_level": 0.75},
        market_conditions={"volatility_regime": "normal", "liquidity_conditions": "good"},
        decision_confidence=0.8,
        expected_outcome={
            "expected_return": 0.12,
            "expected_volatility": 0.20,
            "win_probability": 0.65,
            "risk_reward_ratio": 3.0
        },
        scenario_analysis=[
            {"scenario": "基准", "probability": 0.6, "return": 0.12},
            {"scenario": "乐观", "probability": 0.2, "return": 0.20},
            {"scenario": "悲观", "probability": 0.2, "return": -0.05}
        ],
        monitoring_indicators=["价格变化", "成交量", "技术指标"],
        adjustment_triggers=["触发止损", "基本面变化"],
        trader_reasoning="基于技术突破和基本面支持的多头策略"
    )
    
    # 模拟分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-19"
    )
    
    try:
        print("\n🔍 开始风险评估管理...")
        risk_debate_result = await risk_manager.manage_risk_assessment(trading_decision, analysis_state)
        
        print(f"✅ 风险评估完成")
        print(f"   最终风险等级: {risk_debate_result.final_risk_level.value}")
        print(f"   最终建议: {risk_debate_result.final_recommendation.value}")
        print(f"   仓位调整: {risk_debate_result.final_position_adjustment:.1%}")
        print(f"   是否达成共识: {risk_debate_result.consensus_reached}")
        print(f"   分歧数量: {len(risk_debate_result.key_disagreements)}")
        print(f"   辩论质量: {risk_debate_result.debate_quality:.1f}")
        
        # 显示各方评估
        print(f"\n📊 各方风险评估:")
        print(f"   激进评估: {risk_debate_result.aggressive_assessment.overall_risk_level.value} "
              f"({risk_debate_result.aggressive_assessment.recommendation.value})")
        print(f"   保守评估: {risk_debate_result.conservative_assessment.overall_risk_level.value} "
              f"({risk_debate_result.conservative_assessment.recommendation.value})")
        print(f"   中性评估: {risk_debate_result.neutral_assessment.overall_risk_level.value} "
              f"({risk_debate_result.neutral_assessment.recommendation.value})")
        
        # 保存结果
        result_file = Path("test_risk_management_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(risk_debate_result), f, ensure_ascii=False, indent=2, default=str)
        
        print(f"   结果已保存到: {result_file}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 风险管理团队测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_risk_management_team())
