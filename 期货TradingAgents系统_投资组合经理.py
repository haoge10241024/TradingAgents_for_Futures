#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 投资组合经理模块
负责最终的投资组合决策和资金配置管理

功能特点：
1. 综合所有Agent的建议做出最终决策
2. 投资组合优化和资金配置
3. 多品种协调和相关性管理
4. 动态仓位管理和再平衡
5. 最终执行指令生成

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
import numpy as np
import math
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
    OrderType
)
from 期货TradingAgents系统_风险管理团队 import (
    RiskDebateResult,
    RiskAction,
    RiskLevel
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    DataValidator,
    TimeUtils,
    log_execution_time,
    retry_on_failure
)

# ============================================================================
# 1. 投资组合管理核心数据结构
# ============================================================================

class PortfolioDecision(Enum):
    """投资组合决策"""
    EXECUTE = "execute"                    # 执行
    EXECUTE_MODIFIED = "execute_modified"  # 修改后执行
    DEFER = "defer"                       # 延期
    REJECT = "reject"                     # 拒绝

class AllocationMethod(Enum):
    """资金配置方法"""
    EQUAL_WEIGHT = "equal_weight"         # 等权重
    RISK_PARITY = "risk_parity"          # 风险平价
    MEAN_VARIANCE = "mean_variance"       # 均值-方差优化
    KELLY_OPTIMAL = "kelly_optimal"       # 凯利最优
    STRATEGIC = "strategic"               # 战略配置

class RebalanceFrequency(Enum):
    """再平衡频率"""
    DAILY = "daily"                       # 日度
    WEEKLY = "weekly"                     # 周度
    MONTHLY = "monthly"                   # 月度
    QUARTERLY = "quarterly"               # 季度
    EVENT_DRIVEN = "event_driven"         # 事件驱动

@dataclass
class PortfolioPosition:
    """投资组合头寸"""
    commodity: str
    direction: TradingDirection
    target_weight: float         # 目标权重 (0-1)
    current_weight: float        # 当前权重 (0-1)
    target_contracts: int        # 目标合约数
    current_contracts: int       # 当前合约数
    market_value: float          # 市场价值
    unrealized_pnl: float        # 未实现盈亏
    risk_contribution: float     # 风险贡献度
    correlation_impact: float    # 相关性影响

@dataclass
class PortfolioMetrics:
    """投资组合指标"""
    total_value: float                    # 总价值
    total_margin_used: float             # 已用保证金
    available_margin: float              # 可用保证金
    leverage_ratio: float                # 杠杆比率
    
    # 风险指标
    portfolio_var: float                 # 组合VaR
    portfolio_volatility: float          # 组合波动率
    max_drawdown: float                  # 最大回撤
    sharpe_ratio: float                  # 夏普比率
    
    # 多样化指标
    concentration_ratio: float           # 集中度比率
    correlation_risk: float              # 相关性风险
    diversification_ratio: float        # 分散化比率
    
    # 绩效指标
    total_return: float                  # 总回报率
    alpha: float                         # 超额回报
    beta: float                          # 市场贝塔
    information_ratio: float             # 信息比率

@dataclass
class ExecutionOrder:
    """执行订单"""
    commodity: str
    order_type: OrderType
    direction: TradingDirection
    quantity: int                        # 合约数量
    target_price: Optional[float]        # 目标价格
    price_limit: Optional[float]         # 价格限制
    time_in_force: str                   # 有效期 ("GTC", "IOC", "FOK")
    execution_strategy: str              # 执行策略
    priority: int                        # 优先级 (1-10)
    reasoning: str                       # 执行理由

@dataclass
class PortfolioDecisionResult:
    """投资组合决策结果"""
    commodity: str
    analysis_date: str
    decision_timestamp: str
    
    # 最终决策
    portfolio_decision: PortfolioDecision
    decision_confidence: float           # 决策信心 (0-1)
    
    # 资金配置
    allocated_capital: float             # 分配资金
    position_sizing: Dict[str, float]    # 仓位配置
    risk_budget: float                   # 风险预算
    
    # 执行指令
    execution_orders: List[ExecutionOrder] = None
    
    # 投资组合影响
    portfolio_impact: Dict = None
    correlation_adjustments: Dict = None
    
    # 监控和控制
    stop_conditions: List[str] = None    # 停止条件
    rebalance_triggers: List[str] = None # 再平衡触发器
    review_schedule: str = ""            # 复审计划
    
    # 决策依据
    decision_factors: List[str] = None
    risk_considerations: List[str] = None
    
    # 元数据
    portfolio_manager_reasoning: str = ""

# ============================================================================
# 2. 投资组合经理主类
# ============================================================================

class FuturesPortfolioManager:
    """期货投资组合经理 - 最终决策制定者"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.role = "portfolio_manager"
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 投资组合配置
        portfolio_config = config.get("portfolio_management", {})
        self.total_capital = portfolio_config.get("total_capital", 10000000)  # 1000万
        self.max_portfolio_risk = portfolio_config.get("max_portfolio_risk", 0.02)  # 2%
        self.max_single_position = portfolio_config.get("max_single_position", 0.15)  # 15%
        self.allocation_method = AllocationMethod(portfolio_config.get("allocation_method", "risk_parity"))
        self.rebalance_threshold = portfolio_config.get("rebalance_threshold", 0.05)  # 5%
        
        # 当前投资组合状态（简化实现）
        self.current_portfolio = {}
        self.portfolio_metrics = None
        
        # 相关性矩阵（简化版）
        self.correlation_matrix = self._initialize_correlation_matrix()
        
        # 日志
        self.logger = logging.getLogger("FuturesPortfolioManager")
        
        # 期货品种信息
        self.commodity_info = {
            "RB": {"sector": "steel", "volatility": 0.25, "liquidity": "high"},
            "CU": {"sector": "metals", "volatility": 0.20, "liquidity": "high"},
            "AU": {"sector": "precious", "volatility": 0.15, "liquidity": "high"},
            "AG": {"sector": "precious", "volatility": 0.22, "liquidity": "medium"},
            "I": {"sector": "steel", "volatility": 0.30, "liquidity": "high"},
            "J": {"sector": "steel", "volatility": 0.28, "liquidity": "medium"},
            "M": {"sector": "agriculture", "volatility": 0.18, "liquidity": "high"},
            "Y": {"sector": "agriculture", "volatility": 0.16, "liquidity": "high"}
        }
        
    def _initialize_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """初始化相关性矩阵（简化版）"""
        
        # 简化的相关性矩阵
        correlations = {
            "RB": {"RB": 1.0, "I": 0.8, "J": 0.7, "HC": 0.9, "CU": 0.3, "AU": -0.1, "M": 0.1, "Y": 0.1},
            "CU": {"RB": 0.3, "I": 0.2, "J": 0.2, "HC": 0.2, "CU": 1.0, "AU": 0.4, "M": 0.1, "Y": 0.1},
            "AU": {"RB": -0.1, "I": -0.1, "J": -0.1, "HC": -0.1, "CU": 0.4, "AU": 1.0, "M": 0.0, "Y": 0.0},
            "I": {"RB": 0.8, "I": 1.0, "J": 0.6, "HC": 0.7, "CU": 0.2, "AU": -0.1, "M": 0.1, "Y": 0.1},
            "J": {"RB": 0.7, "I": 0.6, "J": 1.0, "HC": 0.6, "CU": 0.2, "AU": -0.1, "M": 0.1, "Y": 0.1},
            "M": {"RB": 0.1, "I": 0.1, "J": 0.1, "HC": 0.1, "CU": 0.1, "AU": 0.0, "M": 1.0, "Y": 0.7},
            "Y": {"RB": 0.1, "I": 0.1, "J": 0.1, "HC": 0.1, "CU": 0.1, "AU": 0.0, "M": 0.7, "Y": 1.0}
        }
        
        return correlations
    
    @log_execution_time()
    async def make_portfolio_decision(self, 
                                    trading_decision: TradingDecision,
                                    risk_assessment: RiskDebateResult,
                                    analysis_state: FuturesAnalysisState) -> PortfolioDecisionResult:
        """制定最终投资组合决策"""
        
        self.logger.info(f"开始投资组合决策: {trading_decision.commodity}")
        
        # 1. 综合评估所有输入
        comprehensive_assessment = await self._conduct_comprehensive_assessment(
            trading_decision, risk_assessment, analysis_state
        )
        
        # 2. 制定投资组合决策
        portfolio_decision = self._make_final_decision(comprehensive_assessment)
        
        # 3. 计算资金配置
        allocation_result = await self._calculate_capital_allocation(
            trading_decision, risk_assessment, portfolio_decision
        )
        
        # 4. 评估投资组合影响
        portfolio_impact = await self._assess_portfolio_impact(
            trading_decision, allocation_result
        )
        
        # 5. 生成执行指令
        execution_orders = await self._generate_execution_orders(
            trading_decision, allocation_result, portfolio_decision
        )
        
        # 6. 设定监控和控制机制
        control_mechanisms = self._establish_control_mechanisms(
            trading_decision, risk_assessment, allocation_result
        )
        
        # 7. 生成最终推理
        reasoning = await self._generate_portfolio_reasoning(
            trading_decision, risk_assessment, comprehensive_assessment, portfolio_decision
        )
        
        # 构建决策结果
        decision_result = PortfolioDecisionResult(
            commodity=trading_decision.commodity,
            analysis_date=trading_decision.analysis_date,
            decision_timestamp=datetime.now().isoformat(),
            portfolio_decision=portfolio_decision,
            decision_confidence=comprehensive_assessment.get("confidence", 0.7),
            allocated_capital=allocation_result.get("allocated_capital", 0),
            position_sizing=allocation_result.get("position_sizing", {}),
            risk_budget=allocation_result.get("risk_budget", 0),
            execution_orders=execution_orders,
            portfolio_impact=portfolio_impact,
            correlation_adjustments=portfolio_impact.get("correlation_adjustments", {}),
            stop_conditions=control_mechanisms.get("stop_conditions", []),
            rebalance_triggers=control_mechanisms.get("rebalance_triggers", []),
            review_schedule=control_mechanisms.get("review_schedule", ""),
            decision_factors=comprehensive_assessment.get("decision_factors", []),
            risk_considerations=comprehensive_assessment.get("risk_considerations", []),
            portfolio_manager_reasoning=reasoning
        )
        
        self.logger.info(f"投资组合决策完成: {portfolio_decision.value}, 分配资金: {allocation_result.get('allocated_capital', 0):,.0f}")
        
        return decision_result
    
    async def _conduct_comprehensive_assessment(self, 
                                              trading_decision: TradingDecision,
                                              risk_assessment: RiskDebateResult,
                                              analysis_state: FuturesAnalysisState) -> Dict:
        """进行综合评估"""
        
        assessment = {}
        
        # 1. 交易信号评估
        signal_strength = trading_decision.trading_signal.strength
        signal_confidence = trading_decision.trading_signal.confidence
        assessment["signal_quality"] = (signal_strength + signal_confidence) / 2
        
        # 2. 风险评估整合
        risk_level = risk_assessment.final_risk_level
        risk_recommendation = risk_assessment.final_recommendation
        position_adjustment = risk_assessment.final_position_adjustment
        
        risk_score = self._convert_risk_level_to_score(risk_level)
        assessment["risk_score"] = risk_score
        assessment["risk_adjustment"] = position_adjustment
        
        # 3. 研究质量评估
        data_completeness = analysis_state.get_analysis_progress()
        assessment["research_quality"] = data_completeness
        
        # 4. 市场条件评估
        market_conditions = trading_decision.market_conditions
        assessment["market_favorability"] = self._assess_market_favorability(market_conditions)
        
        # 5. 投资组合适配性评估
        portfolio_fit = await self._assess_portfolio_fit(trading_decision)
        assessment["portfolio_fit"] = portfolio_fit
        
        # 6. 综合评分
        weights = {
            "signal_quality": 0.25,
            "risk_score": 0.30,
            "research_quality": 0.15,
            "market_favorability": 0.15,
            "portfolio_fit": 0.15
        }
        
        composite_score = sum(
            assessment[factor] * weight 
            for factor, weight in weights.items()
        )
        assessment["composite_score"] = composite_score
        assessment["confidence"] = min(0.95, max(0.3, composite_score))
        
        # 7. 决策因素总结
        assessment["decision_factors"] = [
            f"交易信号质量: {assessment['signal_quality']:.1%}",
            f"风险评估: {risk_level.value}",
            f"研究质量: {assessment['research_quality']:.1%}",
            f"市场适宜性: {assessment['market_favorability']:.1%}",
            f"组合适配性: {assessment['portfolio_fit']:.1%}"
        ]
        
        # 8. 风险考虑因素
        risk_factors_count = 0
        if (risk_assessment.aggressive_assessment and 
            risk_assessment.aggressive_assessment.identified_risks):
            risk_factors_count = len(risk_assessment.aggressive_assessment.identified_risks)
        
        assessment["risk_considerations"] = [
            f"风险管理建议: {risk_recommendation.value}",
            f"仓位调整建议: {position_adjustment:.1%}",
            f"主要风险因素: {risk_factors_count}个"
        ]
        
        return assessment
    
    def _convert_risk_level_to_score(self, risk_level: RiskLevel) -> float:
        """将风险等级转换为评分"""
        risk_scores = {
            RiskLevel.VERY_LOW: 0.9,
            RiskLevel.LOW: 0.8,
            RiskLevel.MEDIUM: 0.6,
            RiskLevel.HIGH: 0.4,
            RiskLevel.VERY_HIGH: 0.2
        }
        return risk_scores.get(risk_level, 0.6)
    
    def _assess_market_favorability(self, market_conditions: Dict) -> float:
        """评估市场有利程度"""
        
        favorability = 0.5  # 基础分数
        
        # 流动性条件
        liquidity = market_conditions.get("liquidity_conditions", "normal")
        if liquidity == "good":
            favorability += 0.2
        elif liquidity == "poor":
            favorability -= 0.2
        
        # 波动率制度
        volatility = market_conditions.get("volatility_regime", "normal")
        if volatility == "low":
            favorability += 0.1  # 低波动率有利于仓位建立
        elif volatility == "high":
            favorability -= 0.1  # 高波动率增加执行风险
        
        # 趋势强度
        trend_strength = market_conditions.get("trend_strength", "weak")
        if trend_strength == "strong":
            favorability += 0.2
        elif trend_strength == "weak":
            favorability -= 0.1
        
        return min(1.0, max(0.0, favorability))
    
    async def _assess_portfolio_fit(self, trading_decision: TradingDecision) -> float:
        """评估与投资组合的适配性"""
        
        commodity = trading_decision.commodity
        direction = trading_decision.trading_signal.direction
        
        fit_score = 0.7  # 基础分数
        
        # 1. 相关性影响
        correlation_impact = self._calculate_correlation_impact(commodity, direction)
        fit_score += correlation_impact * 0.2
        
        # 2. 集中度影响
        concentration_impact = self._calculate_concentration_impact(commodity)
        fit_score += concentration_impact * 0.2
        
        # 3. 风险贡献度
        risk_contribution_impact = self._calculate_risk_contribution_impact(commodity)
        fit_score += risk_contribution_impact * 0.1
        
        return min(1.0, max(0.0, fit_score))
    
    def _calculate_correlation_impact(self, commodity: str, direction: TradingDirection) -> float:
        """计算相关性影响"""
        
        # 简化实现：检查与现有持仓的相关性
        if not self.current_portfolio:
            return 0.1  # 空仓时相关性影响为正
        
        total_correlation = 0
        position_count = 0
        
        for existing_commodity, position_info in self.current_portfolio.items():
            if existing_commodity in self.correlation_matrix.get(commodity, {}):
                correlation = self.correlation_matrix[commodity][existing_commodity]
                
                # 如果方向相同且相关性高，影响为负
                if position_info.get("direction") == direction and correlation > 0.5:
                    total_correlation -= correlation * 0.5
                # 如果方向相反且相关性高，影响为正（对冲效果）
                elif position_info.get("direction") != direction and correlation > 0.5:
                    total_correlation += correlation * 0.3
                
                position_count += 1
        
        return total_correlation / max(1, position_count)
    
    def _calculate_concentration_impact(self, commodity: str) -> float:
        """计算集中度影响"""
        
        if not self.current_portfolio:
            return 0.1  # 空仓时集中度影响为正
        
        # 计算品种集中度
        commodity_info = self.commodity_info.get(commodity, {})
        sector = commodity_info.get("sector", "unknown")
        
        sector_exposure = 0
        for existing_commodity, position_info in self.current_portfolio.items():
            existing_info = self.commodity_info.get(existing_commodity, {})
            if existing_info.get("sector") == sector:
                sector_exposure += position_info.get("weight", 0)
        
        # 如果行业集中度过高，影响为负
        if sector_exposure > 0.4:  # 40%以上同行业暴露
            return -0.3
        elif sector_exposure > 0.2:  # 20-40%同行业暴露
            return -0.1
        else:
            return 0.1
    
    def _calculate_risk_contribution_impact(self, commodity: str) -> float:
        """计算风险贡献度影响"""
        
        commodity_info = self.commodity_info.get(commodity, {})
        volatility = commodity_info.get("volatility", 0.2)
        
        # 高波动率品种的风险贡献影响为负
        if volatility > 0.3:
            return -0.2
        elif volatility > 0.2:
            return -0.1
        else:
            return 0.1
    
    def _make_final_decision(self, assessment: Dict) -> PortfolioDecision:
        """制定最终决策"""
        
        composite_score = assessment["composite_score"]
        confidence = assessment["confidence"]
        
        # 基于综合评分和信心水平决定
        if composite_score >= 0.8 and confidence >= 0.8:
            return PortfolioDecision.EXECUTE
        elif composite_score >= 0.6 and confidence >= 0.6:
            return PortfolioDecision.EXECUTE_MODIFIED
        elif composite_score >= 0.4:
            return PortfolioDecision.DEFER
        else:
            return PortfolioDecision.REJECT
    
    async def _calculate_capital_allocation(self, 
                                          trading_decision: TradingDecision,
                                          risk_assessment: RiskDebateResult,
                                          portfolio_decision: PortfolioDecision) -> Dict:
        """计算资金配置"""
        
        if portfolio_decision == PortfolioDecision.REJECT:
            return {
                "allocated_capital": 0,
                "position_sizing": {},
                "risk_budget": 0
            }
        
        # 基础配置
        base_allocation = trading_decision.position_sizing.position_percentage * self.total_capital
        risk_adjustment = risk_assessment.final_position_adjustment
        
        # 应用风险调整
        adjusted_allocation = base_allocation * risk_adjustment
        
        # 应用投资组合约束
        max_allocation = self.total_capital * self.max_single_position
        final_allocation = min(adjusted_allocation, max_allocation)
        
        # 如果是修改执行，进一步调整
        if portfolio_decision == PortfolioDecision.EXECUTE_MODIFIED:
            final_allocation *= 0.8  # 减少20%
        
        # 计算风险预算
        risk_budget = final_allocation * 0.02  # 2%的风险预算
        
        # 仓位配置
        position_sizing = {
            trading_decision.commodity: final_allocation / self.total_capital
        }
        
        return {
            "allocated_capital": final_allocation,
            "position_sizing": position_sizing,
            "risk_budget": risk_budget,
            "base_allocation": base_allocation,
            "risk_adjustment_factor": risk_adjustment,
            "portfolio_constraint_applied": final_allocation < adjusted_allocation
        }
    
    async def _assess_portfolio_impact(self, 
                                     trading_decision: TradingDecision,
                                     allocation_result: Dict) -> Dict:
        """评估投资组合影响"""
        
        commodity = trading_decision.commodity
        allocated_capital = allocation_result["allocated_capital"]
        
        impact = {
            "capital_utilization": allocated_capital / self.total_capital,
            "risk_impact": allocation_result["risk_budget"] / (self.total_capital * self.max_portfolio_risk),
            "concentration_change": 0,  # 简化实现
            "correlation_adjustments": {}
        }
        
        # 评估相关性调整需求
        if self.current_portfolio:
            for existing_commodity in self.current_portfolio.keys():
                if commodity in self.correlation_matrix and existing_commodity in self.correlation_matrix[commodity]:
                    correlation = self.correlation_matrix[commodity][existing_commodity]
                    if abs(correlation) > 0.6:  # 高相关性
                        impact["correlation_adjustments"][existing_commodity] = {
                            "correlation": correlation,
                            "recommended_adjustment": -0.1 if correlation > 0 else 0.1
                        }
        
        return impact
    
    async def _generate_execution_orders(self, 
                                       trading_decision: TradingDecision,
                                       allocation_result: Dict,
                                       portfolio_decision: PortfolioDecision) -> List[ExecutionOrder]:
        """生成执行指令"""
        
        if portfolio_decision == PortfolioDecision.REJECT:
            return []
        
        orders = []
        
        # 主要执行订单
        commodity = trading_decision.commodity
        direction = trading_decision.trading_signal.direction
        
        if direction != TradingDirection.NEUTRAL:
            # 计算合约数量
            allocated_capital = allocation_result["allocated_capital"]
            estimated_price = 3500  # 简化处理
            contract_multiplier = 10   # 简化处理
            
            target_contracts = int(allocated_capital / (estimated_price * contract_multiplier))
            
            if target_contracts > 0:
                main_order = ExecutionOrder(
                    commodity=commodity,
                    order_type=trading_decision.execution_plan.order_type,
                    direction=direction,
                    quantity=target_contracts,
                    target_price=trading_decision.execution_plan.entry_price_target,
                    price_limit=trading_decision.execution_plan.entry_price_target * 1.002,
                    time_in_force="GTC",
                    execution_strategy=trading_decision.execution_plan.execution_method,
                    priority=8 if portfolio_decision == PortfolioDecision.EXECUTE else 6,
                    reasoning=f"基于投资组合决策{portfolio_decision.value}，分配资金{allocated_capital:,.0f}"
                )
                orders.append(main_order)
        
        # 相关性调整订单（如果需要）
        correlation_adjustments = allocation_result.get("correlation_adjustments", {})
        for commodity_to_adjust, adjustment_info in correlation_adjustments.items():
            if abs(adjustment_info["recommended_adjustment"]) > 0.05:  # 5%以上的调整
                # 这里简化处理，实际需要更复杂的逻辑
                pass
        
        return orders
    
    def _establish_control_mechanisms(self, 
                                    trading_decision: TradingDecision,
                                    risk_assessment: RiskDebateResult,
                                    allocation_result: Dict) -> Dict:
        """建立控制机制"""
        
        mechanisms = {}
        
        # 停止条件
        stop_conditions = [
            f"损失超过风险预算{allocation_result['risk_budget']:,.0f}",
            "市场流动性严重恶化",
            "基本面发生重大变化"
        ]
        
        # 根据风险等级添加额外停止条件
        if risk_assessment.final_risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            stop_conditions.extend([
                "市场波动率超过历史95分位数",
                "相关品种出现系统性风险"
            ])
        
        mechanisms["stop_conditions"] = stop_conditions
        
        # 再平衡触发器
        rebalance_triggers = [
            f"仓位偏离目标超过{self.rebalance_threshold:.1%}",
            "风险贡献度发生重大变化",
            "相关性结构发生显著变化"
        ]
        mechanisms["rebalance_triggers"] = rebalance_triggers
        
        # 复审计划
        if risk_assessment.final_risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            review_schedule = "每日复审"
        elif risk_assessment.final_risk_level == RiskLevel.MEDIUM:
            review_schedule = "每周复审"
        else:
            review_schedule = "每月复审"
        
        mechanisms["review_schedule"] = review_schedule
        
        return mechanisms
    
    async def _generate_portfolio_reasoning(self, 
                                          trading_decision: TradingDecision,
                                          risk_assessment: RiskDebateResult,
                                          assessment: Dict,
                                          portfolio_decision: PortfolioDecision) -> str:
        """生成投资组合推理"""
        
        reasoning_parts = []
        
        # 决策概述
        reasoning_parts.append(f"基于综合评估，投资组合决策: {portfolio_decision.value}")
        
        # 主要考虑因素
        composite_score = assessment["composite_score"]
        reasoning_parts.append(f"综合评分: {composite_score:.1%}")
        
        # 风险考量
        risk_level = risk_assessment.final_risk_level
        reasoning_parts.append(f"风险等级: {risk_level.value}")
        
        # 投资组合适配性
        portfolio_fit = assessment["portfolio_fit"]
        reasoning_parts.append(f"组合适配性: {portfolio_fit:.1%}")
        
        # 资金配置逻辑
        if portfolio_decision != PortfolioDecision.REJECT:
            reasoning_parts.append("资金配置考虑了风险调整和投资组合约束")
        
        # 控制机制
        reasoning_parts.append("已建立相应的风险控制和监控机制")
        
        return "; ".join(reasoning_parts)
    
    def get_portfolio_manager_info(self) -> Dict:
        """获取投资组合经理信息"""
        return {
            "name": "期货投资组合经理",
            "role": self.role,
            "total_capital": self.total_capital,
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_single_position": self.max_single_position,
            "allocation_method": self.allocation_method.value,
            "rebalance_threshold": self.rebalance_threshold,
            "supported_commodities": list(self.commodity_info.keys()),
            "version": "1.0.0"
        }

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_portfolio_manager():
    """测试投资组合经理"""
    
    print("💼 测试期货投资组合经理...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建投资组合经理
    portfolio_manager = FuturesPortfolioManager(config)
    
    print(f"投资组合经理信息: {portfolio_manager.get_portfolio_manager_info()}")
    
    # 创建模拟数据
    from 期货TradingAgents系统_交易员 import (
        TradingDecision, TradingSignal, PositionSizing, RiskParameters,
        TradingStrategy, ExecutionPlan, TradingDirection, PositionSizingMethod, OrderType
    )
    from 期货TradingAgents系统_风险管理团队 import (
        RiskDebateResult, RiskAssessment, RiskLevel, RiskAction
    )
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState
    
    # 模拟交易决策
    trading_signal = TradingSignal(
        direction=TradingDirection.LONG,
        strength=0.8,
        confidence=0.75,
        urgency="medium",
        reasoning="综合分析支持看涨"
    )
    
    position_sizing = PositionSizing(
        position_percentage=0.12,
        contract_quantity=2,
        margin_required=120000,
        max_loss_amount=40000,
        sizing_method=PositionSizingMethod.RISK_PARITY,
        reasoning="风险平价方法计算"
    )
    
    risk_parameters = RiskParameters(
        stop_loss_price=3350,
        stop_loss_percentage=0.05,
        take_profit_price=4000,
        take_profit_percentage=0.14,
        max_drawdown=40000,
        risk_reward_ratio=2.8,
        var_estimate=20000,
        confidence_interval=0.95
    )
    
    trading_strategy = TradingStrategy(
        strategy_name="趋势跟踪策略",
        entry_conditions=["趋势确认", "动量支持"],
        exit_conditions=["趋势反转", "目标达成"],
        time_horizon="medium_term",
        strategy_type="trend_following",
        expected_return=0.14,
        expected_volatility=0.18,
        win_rate=0.7,
        avg_win_loss_ratio=2.5
    )
    
    execution_plan = ExecutionPlan(
        execution_timing="适时执行",
        order_type=OrderType.LIMIT,
        entry_price_target=3520,
        price_tolerance=10,
        execution_method="passive",
        market_impact_estimate=0.001,
        execution_cost_estimate=0.0005
    )
    
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
        market_conditions={"volatility_regime": "normal", "liquidity_conditions": "good", "trend_strength": "moderate"},
        decision_confidence=0.78,
        expected_outcome={
            "expected_return": 0.14,
            "expected_volatility": 0.18,
            "win_probability": 0.7,
            "risk_reward_ratio": 2.8
        },
        scenario_analysis=[
            {"scenario": "基准", "probability": 0.6, "return": 0.14},
            {"scenario": "乐观", "probability": 0.25, "return": 0.25},
            {"scenario": "悲观", "probability": 0.15, "return": -0.05}
        ],
        monitoring_indicators=["价格趋势", "成交量", "技术指标", "基本面变化"],
        adjustment_triggers=["止损触发", "目标达成", "趋势反转"],
        trader_reasoning="基于趋势跟踪策略的中期多头布局"
    )
    
    # 模拟风险评估结果
    risk_assessment_mock = RiskAssessment(
        assessor_type="neutral",
        overall_risk_level=RiskLevel.MEDIUM,
        risk_score=45.0,
        recommendation=RiskAction.APPROVE_WITH_CONDITIONS,
        position_adjustment=0.9,
        reasoning="中等风险，建议适度控制"
    )
    
    risk_debate_result = RiskDebateResult(
        commodity="RB",
        analysis_date="2025-01-19",
        final_risk_level=RiskLevel.MEDIUM,
        final_recommendation=RiskAction.APPROVE_WITH_CONDITIONS,
        final_position_adjustment=0.9,
        consensus_reached=True,
        debate_quality=8.0
    )
    risk_debate_result.aggressive_assessment = risk_assessment_mock
    risk_debate_result.conservative_assessment = risk_assessment_mock
    risk_debate_result.neutral_assessment = risk_assessment_mock
    
    # 模拟分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-19"
    )
    
    try:
        print("\n💡 开始投资组合决策...")
        portfolio_decision_result = await portfolio_manager.make_portfolio_decision(
            trading_decision, risk_debate_result, analysis_state
        )
        
        print(f"✅ 投资组合决策完成")
        print(f"   最终决策: {portfolio_decision_result.portfolio_decision.value}")
        print(f"   决策信心: {portfolio_decision_result.decision_confidence:.1%}")
        print(f"   分配资金: {portfolio_decision_result.allocated_capital:,.0f}")
        print(f"   风险预算: {portfolio_decision_result.risk_budget:,.0f}")
        print(f"   执行订单数量: {len(portfolio_decision_result.execution_orders)}")
        print(f"   复审计划: {portfolio_decision_result.review_schedule}")
        
        # 显示执行订单详情
        if portfolio_decision_result.execution_orders:
            print(f"\n📋 执行订单:")
            for i, order in enumerate(portfolio_decision_result.execution_orders, 1):
                print(f"   {i}. {order.commodity} {order.direction.value} {order.quantity}手")
                print(f"      订单类型: {order.order_type.value}")
                print(f"      目标价格: {order.target_price}")
                print(f"      优先级: {order.priority}")
        
        # 保存结果
        result_file = Path("test_portfolio_decision_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(portfolio_decision_result), f, ensure_ascii=False, indent=2, default=str)
        
        print(f"   结果已保存到: {result_file}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 投资组合经理测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_portfolio_manager())
