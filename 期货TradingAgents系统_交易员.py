#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 交易员模块
基于研究共识制定具体的交易策略和执行方案

功能特点：
1. 基于研究共识制定交易策略
2. 计算具体的仓位大小和风险参数
3. 确定最佳的入场和出场时机
4. 生成详细的交易执行计划
5. 支持多种交易策略和风格

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
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
from 期货TradingAgents系统_研究经理 import (
    ResearchConsensus,
    DebateManagementResult
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    DataValidator,
    TimeUtils,
    log_execution_time,
    retry_on_failure
)

# ============================================================================
# 1. 交易员核心数据结构
# ============================================================================

class TradingDirection(Enum):
    """交易方向"""
    LONG = "long"      # 做多
    SHORT = "short"    # 做空
    NEUTRAL = "neutral" # 观望
    HEDGE = "hedge"    # 对冲

class PositionSizingMethod(Enum):
    """仓位计算方法"""
    FIXED_PERCENTAGE = "fixed_percentage"    # 固定百分比
    KELLY_CRITERION = "kelly_criterion"      # 凯利公式
    VOLATILITY_BASED = "volatility_based"    # 基于波动率
    RISK_PARITY = "risk_parity"             # 风险平价

class OrderType(Enum):
    """订单类型"""
    MARKET = "market"           # 市价单
    LIMIT = "limit"            # 限价单
    STOP = "stop"              # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单

@dataclass
class TradingSignal:
    """交易信号"""
    direction: TradingDirection
    strength: float  # 信号强度 (0-1)
    confidence: float  # 信心水平 (0-1)
    urgency: str  # 紧急程度 ("low", "medium", "high")
    reasoning: str  # 信号原因
    supporting_factors: List[str] = None
    risk_factors: List[str] = None

@dataclass
class PositionSizing:
    """仓位配置"""
    position_percentage: float  # 仓位百分比 (0-1)
    contract_quantity: int  # 合约数量
    margin_required: float  # 所需保证金
    max_loss_amount: float  # 最大损失金额
    sizing_method: PositionSizingMethod  # 计算方法
    reasoning: str  # 仓位决策原因

@dataclass
class RiskParameters:
    """风险参数"""
    stop_loss_price: float  # 止损价位
    stop_loss_percentage: float  # 止损百分比
    take_profit_price: float  # 止盈价位
    take_profit_percentage: float  # 止盈百分比
    max_drawdown: float  # 最大回撤
    risk_reward_ratio: float  # 风险回报比
    var_estimate: float  # VaR估计
    confidence_interval: float  # 置信区间

@dataclass
class TradingStrategy:
    """交易策略"""
    strategy_name: str
    entry_conditions: List[str]  # 入场条件
    exit_conditions: List[str]   # 出场条件
    time_horizon: str  # 持仓周期 ("intraday", "short_term", "medium_term", "long_term")
    strategy_type: str  # 策略类型 ("trend_following", "mean_reversion", "breakout", "arbitrage")
    expected_return: float  # 预期收益率
    expected_volatility: float  # 预期波动率
    win_rate: float  # 预期胜率
    avg_win_loss_ratio: float  # 平均盈亏比

@dataclass
class ExecutionPlan:
    """执行计划"""
    execution_timing: str  # 执行时机
    order_type: OrderType  # 订单类型
    entry_price_target: float  # 目标入场价
    price_tolerance: float  # 价格容忍度
    execution_method: str  # 执行方法 ("aggressive", "passive", "twap", "vwap")
    market_impact_estimate: float  # 市场冲击估计
    execution_cost_estimate: float  # 执行成本估计
    contingency_plans: List[str] = None  # 应急预案

@dataclass
class TradingDecision:
    """交易决策"""
    commodity: str
    analysis_date: str
    decision_timestamp: str
    
    # 核心决策
    trading_signal: TradingSignal
    position_sizing: PositionSizing
    risk_parameters: RiskParameters
    trading_strategy: TradingStrategy
    execution_plan: ExecutionPlan
    
    # 决策支撑
    research_consensus_summary: Dict
    market_conditions: Dict
    
    # 决策评估
    decision_confidence: float  # 决策信心 (0-1)
    expected_outcome: Dict  # 预期结果
    scenario_analysis: List[Dict] = None  # 情景分析
    
    # 监控和调整
    monitoring_indicators: List[str] = None  # 监控指标
    adjustment_triggers: List[str] = None   # 调整触发条件
    
    # 元数据
    trader_reasoning: str = ""  # 交易员推理过程

# ============================================================================
# 2. 交易员主类
# ============================================================================

class FuturesTrader:
    """期货交易员 - 基于研究共识制定交易决策"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.role = "trader"
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 交易配置
        self.trading_config = config.get("trading_execution", {}).get("trader_agent", {})
        self.risk_tolerance = self.trading_config.get("risk_tolerance", "moderate")
        self.position_sizing_method = self.trading_config.get("position_sizing_method", "kelly_criterion")
        self.default_stop_loss = self.trading_config.get("stop_loss_percentage", 0.05)
        self.default_take_profit = self.trading_config.get("take_profit_percentage", 0.15)
        
        # 使用推理模式
        self.use_reasoning_mode = config.get("debate_settings", {}).get("enable_reasoning_mode", True)
        
        # 日志
        self.logger = logging.getLogger("FuturesTrader")
        
        # 期货合约规格（简化版，实际应该从配置文件读取）
        self.contract_specs = {
            "RB": {"multiplier": 10, "tick_size": 1, "margin_rate": 0.08, "unit": "吨"},
            "CU": {"multiplier": 5, "tick_size": 10, "margin_rate": 0.07, "unit": "吨"},
            "AU": {"multiplier": 1000, "tick_size": 0.02, "margin_rate": 0.06, "unit": "克"},
            "AG": {"multiplier": 15, "tick_size": 1, "margin_rate": 0.08, "unit": "千克"},
            "I": {"multiplier": 100, "tick_size": 0.5, "margin_rate": 0.08, "unit": "吨"},
            "J": {"multiplier": 100, "tick_size": 0.5, "margin_rate": 0.08, "unit": "吨"},
            "M": {"multiplier": 10, "tick_size": 1, "margin_rate": 0.06, "unit": "吨"},
            "Y": {"multiplier": 10, "tick_size": 2, "margin_rate": 0.06, "unit": "吨"}
        }
        
        # 期货品种名称映射
        self.commodity_names = {
            "RB": "螺纹钢", "HC": "热卷", "I": "铁矿石", "J": "焦炭", "JM": "焦煤",
            "CU": "沪铜", "AL": "沪铝", "ZN": "沪锌", "NI": "沪镍", "AU": "黄金", "AG": "白银",
            "RU": "橡胶", "BU": "沥青", "FU": "燃油", "MA": "甲醇", "TA": "PTA",
            "SR": "白糖", "CF": "棉花", "M": "豆粕", "Y": "豆油", "P": "棕榈油"
        }
    
    @log_execution_time()
    @retry_on_failure(max_retries=2)
    async def make_trading_decision(self, analysis_state: FuturesAnalysisState,
                                  research_consensus: ResearchConsensus,
                                  debate_result: DebateManagementResult,
                                  account_info: Dict = None) -> TradingDecision:
        """制定交易决策"""
        
        self.logger.info(f"开始制定交易决策: {analysis_state.commodity} ({analysis_state.analysis_date})")
        
        # 1. 分析市场条件
        market_conditions = await self._analyze_market_conditions(analysis_state, research_consensus)
        
        # 2. 生成交易信号
        trading_signal = await self._generate_trading_signal(research_consensus, debate_result, market_conditions)
        
        # 3. 制定交易策略
        trading_strategy = await self._develop_trading_strategy(trading_signal, research_consensus, market_conditions)
        
        # 4. 计算仓位大小
        position_sizing = await self._calculate_position_sizing(
            trading_signal, trading_strategy, market_conditions, account_info
        )
        
        # 5. 设定风险参数
        risk_parameters = await self._set_risk_parameters(
            trading_signal, position_sizing, market_conditions
        )
        
        # 6. 制定执行计划
        execution_plan = await self._create_execution_plan(
            trading_signal, trading_strategy, market_conditions
        )
        
        # 7. 进行情景分析
        scenario_analysis = await self._conduct_scenario_analysis(
            trading_signal, trading_strategy, risk_parameters
        )
        
        # 8. 构建完整交易决策
        trading_decision = TradingDecision(
            commodity=analysis_state.commodity,
            analysis_date=analysis_state.analysis_date,
            decision_timestamp=datetime.now().isoformat(),
            trading_signal=trading_signal,
            position_sizing=position_sizing,
            risk_parameters=risk_parameters,
            trading_strategy=trading_strategy,
            execution_plan=execution_plan,
            research_consensus_summary=self._summarize_research_consensus(research_consensus),
            market_conditions=market_conditions,
            decision_confidence=self._calculate_decision_confidence(trading_signal, research_consensus),
            expected_outcome=self._calculate_expected_outcome(trading_strategy, risk_parameters),
            scenario_analysis=scenario_analysis,
            monitoring_indicators=self._define_monitoring_indicators(trading_strategy),
            adjustment_triggers=self._define_adjustment_triggers(trading_signal, risk_parameters),
            trader_reasoning=await self._generate_trader_reasoning(research_consensus, trading_signal, trading_strategy)
        )
        
        self.logger.info(f"交易决策完成: {trading_signal.direction.value}, 信心: {trading_decision.decision_confidence:.1%}")
        
        return trading_decision
    
    async def _analyze_market_conditions(self, state: FuturesAnalysisState, 
                                       consensus: ResearchConsensus) -> Dict:
        """分析市场条件"""
        
        # 从分析状态中提取市场信息
        market_conditions = {
            "volatility_regime": self._assess_volatility_regime(state),
            "liquidity_conditions": self._assess_liquidity_conditions(state),
            "trend_strength": self._assess_trend_strength(state),
            "market_sentiment": consensus.consensus_type,
            "confidence_level": consensus.confidence_level,
            "data_quality": state.get_analysis_progress(),
            "cross_module_consistency": len([r for r in state.cross_relationships if r.logical_consistency]) / max(1, len(state.cross_relationships))
        }
        
        # 评估市场制度
        if market_conditions["volatility_regime"] == "high":
            market_conditions["recommended_approach"] = "defensive"
        elif market_conditions["trend_strength"] == "strong":
            market_conditions["recommended_approach"] = "trend_following"
        else:
            market_conditions["recommended_approach"] = "balanced"
        
        return market_conditions
    
    def _assess_volatility_regime(self, state: FuturesAnalysisState) -> str:
        """评估波动率制度"""
        # 简化实现，实际应该基于历史波动率数据
        if state.technical_analysis and state.technical_analysis.status == AnalysisStatus.COMPLETED:
            technical_data = state.technical_analysis.result_data
            if "波动率" in str(technical_data):
                return "high" if "高波动" in str(technical_data) else "normal"
        return "normal"
    
    def _assess_liquidity_conditions(self, state: FuturesAnalysisState) -> str:
        """评估流动性条件"""
        # 简化实现，实际应该基于成交量和持仓量数据
        if state.positioning_analysis and state.positioning_analysis.status == AnalysisStatus.COMPLETED:
            positioning_data = state.positioning_analysis.result_data
            if "流动性" in str(positioning_data):
                return "poor" if "流动性不足" in str(positioning_data) else "good"
        return "normal"
    
    def _assess_trend_strength(self, state: FuturesAnalysisState) -> str:
        """评估趋势强度"""
        if state.technical_analysis and state.technical_analysis.status == AnalysisStatus.COMPLETED:
            technical_data = state.technical_analysis.result_data
            trend_direction = technical_data.get("趋势方向", "")
            if trend_direction in ["强势上涨", "强势下跌"]:
                return "strong"
            elif trend_direction in ["上涨", "下跌"]:
                return "moderate"
        return "weak"
    
    async def _generate_trading_signal(self, consensus: ResearchConsensus,
                                     debate_result: DebateManagementResult,
                                     market_conditions: Dict) -> TradingSignal:
        """生成交易信号"""
        
        # 基于研究共识确定方向
        if consensus.consensus_type == "bullish":
            direction = TradingDirection.LONG
        elif consensus.consensus_type == "bearish":
            direction = TradingDirection.SHORT
        elif consensus.consensus_type == "neutral":
            direction = TradingDirection.NEUTRAL
        else:
            direction = TradingDirection.NEUTRAL
        
        # 计算信号强度
        strength = self._calculate_signal_strength(consensus, debate_result, market_conditions)
        
        # 确定紧急程度
        urgency = self._determine_urgency(consensus, market_conditions)
        
        # 生成推理
        reasoning = self._generate_signal_reasoning(consensus, debate_result, market_conditions)
        
        # 提取支撑因素和风险因素
        supporting_factors = consensus.key_findings[:3] if consensus.key_findings else []
        risk_factors = consensus.unresolved_issues[:2] if consensus.unresolved_issues else []
        
        return TradingSignal(
            direction=direction,
            strength=strength,
            confidence=consensus.confidence_level,
            urgency=urgency,
            reasoning=reasoning,
            supporting_factors=supporting_factors,
            risk_factors=risk_factors
        )
    
    def _calculate_signal_strength(self, consensus: ResearchConsensus,
                                 debate_result: DebateManagementResult,
                                 market_conditions: Dict) -> float:
        """计算信号强度"""
        
        # 基础强度来自共识信心
        base_strength = consensus.confidence_level
        
        # 辩论质量加成
        debate_quality_bonus = (debate_result.overall_debate_quality - 5) / 10 * 0.2
        
        # 市场条件调整
        market_adjustment = 0
        if market_conditions.get("trend_strength") == "strong":
            market_adjustment += 0.1
        if market_conditions.get("cross_module_consistency", 0) > 0.7:
            market_adjustment += 0.1
        
        # 风险容忍度调整
        risk_adjustment = 0
        if self.risk_tolerance == "aggressive":
            risk_adjustment = 0.1
        elif self.risk_tolerance == "conservative":
            risk_adjustment = -0.1
        
        final_strength = min(1.0, max(0.0, base_strength + debate_quality_bonus + market_adjustment + risk_adjustment))
        
        return final_strength
    
    def _determine_urgency(self, consensus: ResearchConsensus, market_conditions: Dict) -> str:
        """确定信号紧急程度"""
        
        if consensus.confidence_level >= 0.8 and market_conditions.get("trend_strength") == "strong":
            return "high"
        elif consensus.confidence_level >= 0.6:
            return "medium"
        else:
            return "low"
    
    def _generate_signal_reasoning(self, consensus: ResearchConsensus,
                                 debate_result: DebateManagementResult,
                                 market_conditions: Dict) -> str:
        """生成信号推理"""
        
        reasoning_parts = []
        
        # 共识基础
        reasoning_parts.append(f"基于研究共识({consensus.consensus_type})，信心水平{consensus.confidence_level:.1%}")
        
        # 辩论质量
        reasoning_parts.append(f"辩论质量评分{debate_result.overall_debate_quality:.1f}/10")
        
        # 市场条件
        if market_conditions.get("trend_strength") == "strong":
            reasoning_parts.append("市场趋势强劲")
        
        # 主要支撑因素
        if consensus.key_findings:
            reasoning_parts.append(f"主要支撑: {consensus.key_findings[0]}")
        
        return "; ".join(reasoning_parts)
    
    async def _develop_trading_strategy(self, signal: TradingSignal,
                                      consensus: ResearchConsensus,
                                      market_conditions: Dict) -> TradingStrategy:
        """制定交易策略"""
        
        # 基于信号和市场条件选择策略类型
        if signal.direction != TradingDirection.NEUTRAL:
            if market_conditions.get("trend_strength") == "strong":
                strategy_type = "trend_following"
                strategy_name = "趋势跟踪策略"
            elif signal.strength >= 0.7:
                strategy_type = "breakout"
                strategy_name = "突破策略"
            else:
                strategy_type = "mean_reversion"
                strategy_name = "均值回归策略"
        else:
            strategy_type = "neutral"
            strategy_name = "观望策略"
        
        # 确定时间周期
        if signal.urgency == "high":
            time_horizon = "short_term"
        elif consensus.confidence_level >= 0.7:
            time_horizon = "medium_term"
        else:
            time_horizon = "short_term"
        
        # 设定入场和出场条件
        entry_conditions = self._define_entry_conditions(signal, strategy_type)
        exit_conditions = self._define_exit_conditions(signal, strategy_type)
        
        # 估计策略参数
        expected_return = self._estimate_expected_return(signal, consensus)
        expected_volatility = self._estimate_expected_volatility(market_conditions)
        win_rate = self._estimate_win_rate(signal, strategy_type)
        avg_win_loss_ratio = self._estimate_win_loss_ratio(strategy_type)
        
        return TradingStrategy(
            strategy_name=strategy_name,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            time_horizon=time_horizon,
            strategy_type=strategy_type,
            expected_return=expected_return,
            expected_volatility=expected_volatility,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio
        )
    
    def _define_entry_conditions(self, signal: TradingSignal, strategy_type: str) -> List[str]:
        """定义入场条件"""
        
        conditions = []
        
        if signal.direction == TradingDirection.LONG:
            conditions.extend([
                "研究共识确认看涨",
                f"信号强度达到{signal.strength:.1%}以上",
                "技术指标支持上涨"
            ])
            
            if strategy_type == "breakout":
                conditions.append("价格有效突破关键阻力位")
            elif strategy_type == "trend_following":
                conditions.append("确认上涨趋势延续")
                
        elif signal.direction == TradingDirection.SHORT:
            conditions.extend([
                "研究共识确认看跌",
                f"信号强度达到{signal.strength:.1%}以上",
                "技术指标支持下跌"
            ])
            
            if strategy_type == "breakout":
                conditions.append("价格有效跌破关键支撑位")
            elif strategy_type == "trend_following":
                conditions.append("确认下跌趋势延续")
        
        return conditions
    
    def _define_exit_conditions(self, signal: TradingSignal, strategy_type: str) -> List[str]:
        """定义出场条件"""
        
        conditions = [
            "触发止损位",
            "达到止盈目标",
            "研究共识发生重大变化"
        ]
        
        if strategy_type == "trend_following":
            conditions.append("趋势反转信号确认")
        elif strategy_type == "mean_reversion":
            conditions.append("价格回归均值目标")
        
        return conditions
    
    def _estimate_expected_return(self, signal: TradingSignal, consensus: ResearchConsensus) -> float:
        """估计预期收益率"""
        
        base_return = signal.strength * signal.confidence * 0.1  # 基础预期收益
        
        # 根据共识类型调整
        if consensus.consensus_type in ["bullish", "bearish"]:
            direction_bonus = 0.02
        else:
            direction_bonus = 0
        
        return base_return + direction_bonus
    
    def _estimate_expected_volatility(self, market_conditions: Dict) -> float:
        """估计预期波动率"""
        
        if market_conditions.get("volatility_regime") == "high":
            return 0.25
        elif market_conditions.get("volatility_regime") == "low":
            return 0.10
        else:
            return 0.15
    
    def _estimate_win_rate(self, signal: TradingSignal, strategy_type: str) -> float:
        """估计胜率"""
        
        base_win_rate = 0.5 + signal.confidence * 0.2
        
        # 策略类型调整
        strategy_adjustments = {
            "trend_following": 0.05,
            "breakout": 0.02,
            "mean_reversion": -0.02
        }
        
        adjustment = strategy_adjustments.get(strategy_type, 0)
        
        return min(0.8, max(0.3, base_win_rate + adjustment))
    
    def _estimate_win_loss_ratio(self, strategy_type: str) -> float:
        """估计盈亏比"""
        
        strategy_ratios = {
            "trend_following": 2.0,
            "breakout": 1.5,
            "mean_reversion": 1.2,
            "neutral": 1.0
        }
        
        return strategy_ratios.get(strategy_type, 1.5)
    
    async def _calculate_position_sizing(self, signal: TradingSignal,
                                       strategy: TradingStrategy,
                                       market_conditions: Dict,
                                       account_info: Dict = None) -> PositionSizing:
        """计算仓位大小"""
        
        # 默认账户信息
        if account_info is None:
            account_info = {
                "total_capital": 1000000,  # 100万
                "available_margin": 800000,  # 80万可用保证金
                "risk_limit": 0.02  # 2%风险限制
            }
        
        # 根据方法计算仓位
        if self.position_sizing_method == "kelly_criterion":
            position_pct = self._kelly_criterion_sizing(signal, strategy, account_info)
        elif self.position_sizing_method == "volatility_based":
            position_pct = self._volatility_based_sizing(signal, strategy, market_conditions, account_info)
        elif self.position_sizing_method == "risk_parity":
            position_pct = self._risk_parity_sizing(signal, strategy, account_info)
        else:  # fixed_percentage
            position_pct = self._fixed_percentage_sizing(signal, account_info)
        
        # 获取合约规格
        commodity = signal.reasoning.split()[0] if signal.reasoning else "RB"  # 简化处理
        contract_spec = self.contract_specs.get(commodity, self.contract_specs["RB"])
        
        # 估算当前价格（简化处理，实际应该从市场数据获取）
        estimated_price = self._estimate_current_price(commodity)
        
        # 计算合约数量
        total_value = account_info["total_capital"] * position_pct
        contract_value = estimated_price * contract_spec["multiplier"]
        contract_quantity = int(total_value / contract_value)
        
        # 计算保证金需求
        margin_required = contract_quantity * contract_value * contract_spec["margin_rate"]
        
        # 计算最大损失
        max_loss_amount = account_info["total_capital"] * account_info.get("risk_limit", 0.02)
        
        # 仓位合理性检查
        if margin_required > account_info["available_margin"]:
            # 调整仓位以满足保证金要求
            max_contracts = int(account_info["available_margin"] / (contract_value * contract_spec["margin_rate"]))
            contract_quantity = min(contract_quantity, max_contracts)
            margin_required = contract_quantity * contract_value * contract_spec["margin_rate"]
            position_pct = (contract_quantity * contract_value) / account_info["total_capital"]
        
        reasoning = f"基于{self.position_sizing_method}方法，考虑信号强度{signal.strength:.1%}和账户风险承受能力"
        
        return PositionSizing(
            position_percentage=position_pct,
            contract_quantity=contract_quantity,
            margin_required=margin_required,
            max_loss_amount=max_loss_amount,
            sizing_method=PositionSizingMethod(self.position_sizing_method),
            reasoning=reasoning
        )
    
    def _kelly_criterion_sizing(self, signal: TradingSignal, strategy: TradingStrategy, account_info: Dict) -> float:
        """凯利公式仓位计算"""
        
        win_rate = strategy.win_rate
        win_loss_ratio = strategy.avg_win_loss_ratio
        
        # 凯利公式: f = (bp - q) / b
        # 其中 b = 盈亏比, p = 胜率, q = 败率
        kelly_fraction = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
        
        # 应用信号强度和信心调整
        adjusted_kelly = kelly_fraction * signal.strength * signal.confidence
        
        # 凯利公式通常过于激进，应用分数凯利
        fractional_kelly = adjusted_kelly * 0.25  # 使用1/4凯利
        
        # 限制最大仓位
        max_position = 0.3 if self.risk_tolerance == "aggressive" else 0.2
        
        return min(max_position, max(0.05, fractional_kelly))
    
    def _volatility_based_sizing(self, signal: TradingSignal, strategy: TradingStrategy,
                                market_conditions: Dict, account_info: Dict) -> float:
        """基于波动率的仓位计算"""
        
        target_volatility = 0.15  # 目标组合波动率
        expected_volatility = strategy.expected_volatility
        
        # 基础仓位 = 目标波动率 / 预期波动率
        base_position = target_volatility / expected_volatility
        
        # 信号调整
        signal_adjustment = signal.strength * signal.confidence
        adjusted_position = base_position * signal_adjustment
        
        # 风险容忍度调整
        risk_multiplier = {"conservative": 0.5, "moderate": 1.0, "aggressive": 1.5}[self.risk_tolerance]
        
        final_position = adjusted_position * risk_multiplier
        
        return min(0.4, max(0.05, final_position))
    
    def _risk_parity_sizing(self, signal: TradingSignal, strategy: TradingStrategy, account_info: Dict) -> float:
        """风险平价仓位计算"""
        
        # 简化的风险平价：目标风险贡献 / 预期波动率
        target_risk_contribution = 0.02  # 2%的风险贡献
        expected_volatility = strategy.expected_volatility
        
        base_position = target_risk_contribution / expected_volatility
        
        # 信号调整
        signal_adjustment = (signal.strength + signal.confidence) / 2
        
        return min(0.25, max(0.05, base_position * signal_adjustment))
    
    def _fixed_percentage_sizing(self, signal: TradingSignal, account_info: Dict) -> float:
        """固定百分比仓位计算"""
        
        base_percentages = {"conservative": 0.1, "moderate": 0.15, "aggressive": 0.25}
        base_position = base_percentages[self.risk_tolerance]
        
        # 信号强度调整
        signal_multiplier = (signal.strength + signal.confidence) / 2
        
        return base_position * signal_multiplier
    
    def _estimate_current_price(self, commodity: str) -> float:
        """估算当前价格（简化处理）"""
        
        # 这里使用简化的价格估算，实际应该从市场数据API获取
        price_estimates = {
            "RB": 3500, "CU": 70000, "AU": 450, "AG": 5000,
            "I": 800, "J": 2000, "M": 3000, "Y": 8000
        }
        
        return price_estimates.get(commodity, 3000)
    
    async def _set_risk_parameters(self, signal: TradingSignal,
                                 position_sizing: PositionSizing,
                                 market_conditions: Dict) -> RiskParameters:
        """设定风险参数"""
        
        # 估算当前价格
        estimated_price = 3500  # 简化处理
        
        # 计算止损价位
        if signal.direction == TradingDirection.LONG:
            stop_loss_price = estimated_price * (1 - self.default_stop_loss)
        elif signal.direction == TradingDirection.SHORT:
            stop_loss_price = estimated_price * (1 + self.default_stop_loss)
        else:
            stop_loss_price = estimated_price
        
        # 计算止盈价位
        if signal.direction == TradingDirection.LONG:
            take_profit_price = estimated_price * (1 + self.default_take_profit)
        elif signal.direction == TradingDirection.SHORT:
            take_profit_price = estimated_price * (1 - self.default_take_profit)
        else:
            take_profit_price = estimated_price
        
        # 计算风险回报比
        if signal.direction != TradingDirection.NEUTRAL:
            risk_amount = abs(estimated_price - stop_loss_price)
            reward_amount = abs(take_profit_price - estimated_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        else:
            risk_reward_ratio = 0
        
        # 估算VaR
        var_estimate = position_sizing.margin_required * 0.05  # 简化的VaR估算
        
        return RiskParameters(
            stop_loss_price=stop_loss_price,
            stop_loss_percentage=self.default_stop_loss,
            take_profit_price=take_profit_price,
            take_profit_percentage=self.default_take_profit,
            max_drawdown=position_sizing.max_loss_amount,
            risk_reward_ratio=risk_reward_ratio,
            var_estimate=var_estimate,
            confidence_interval=0.95
        )
    
    async def _create_execution_plan(self, signal: TradingSignal,
                                   strategy: TradingStrategy,
                                   market_conditions: Dict) -> ExecutionPlan:
        """制定执行计划"""
        
        # 确定执行时机
        if signal.urgency == "high":
            execution_timing = "立即执行"
            order_type = OrderType.MARKET
            execution_method = "aggressive"
        elif signal.urgency == "medium":
            execution_timing = "适时执行"
            order_type = OrderType.LIMIT
            execution_method = "passive"
        else:
            execution_timing = "等待机会"
            order_type = OrderType.LIMIT
            execution_method = "passive"
        
        # 估算目标价格
        estimated_price = 3500  # 简化处理
        if order_type == OrderType.LIMIT:
            if signal.direction == TradingDirection.LONG:
                entry_price_target = estimated_price * 0.998  # 略低于市价买入
            elif signal.direction == TradingDirection.SHORT:
                entry_price_target = estimated_price * 1.002  # 略高于市价卖出
            else:
                entry_price_target = estimated_price
        else:
            entry_price_target = estimated_price
        
        # 价格容忍度
        price_tolerance = estimated_price * 0.002  # 0.2%的价格容忍度
        
        # 估算市场冲击和执行成本
        market_impact_estimate = 0.001  # 0.1%的市场冲击
        execution_cost_estimate = 0.0005  # 0.05%的执行成本
        
        # 应急预案
        contingency_plans = [
            "如价格快速变动，调整为市价单执行",
            "如流动性不足，分批执行",
            "如市场条件恶化，取消订单"
        ]
        
        return ExecutionPlan(
            execution_timing=execution_timing,
            order_type=order_type,
            entry_price_target=entry_price_target,
            price_tolerance=price_tolerance,
            execution_method=execution_method,
            market_impact_estimate=market_impact_estimate,
            execution_cost_estimate=execution_cost_estimate,
            contingency_plans=contingency_plans
        )
    
    async def _conduct_scenario_analysis(self, signal: TradingSignal,
                                       strategy: TradingStrategy,
                                       risk_params: RiskParameters) -> List[Dict]:
        """进行情景分析"""
        
        scenarios = []
        
        # 基准情景
        scenarios.append({
            "scenario_name": "基准情景",
            "probability": 0.6,
            "description": "按预期发展",
            "expected_return": strategy.expected_return,
            "max_loss": risk_params.stop_loss_percentage,
            "outcome": "达到预期收益目标"
        })
        
        # 乐观情景
        scenarios.append({
            "scenario_name": "乐观情景",
            "probability": 0.2,
            "description": "超预期表现",
            "expected_return": strategy.expected_return * 1.5,
            "max_loss": risk_params.stop_loss_percentage * 0.5,
            "outcome": "大幅超越预期收益"
        })
        
        # 悲观情景
        scenarios.append({
            "scenario_name": "悲观情景",
            "probability": 0.2,
            "description": "不利发展",
            "expected_return": -risk_params.stop_loss_percentage,
            "max_loss": risk_params.stop_loss_percentage,
            "outcome": "触发止损出场"
        })
        
        return scenarios
    
    def _summarize_research_consensus(self, consensus: ResearchConsensus) -> Dict:
        """总结研究共识"""
        return {
            "consensus_type": consensus.consensus_type,
            "confidence_level": consensus.confidence_level,
            "key_findings": consensus.key_findings[:3] if consensus.key_findings else [],
            "bull_weight": consensus.bull_weight,
            "bear_weight": consensus.bear_weight,
            "investment_recommendation": consensus.investment_recommendation[:100] + "..." if len(consensus.investment_recommendation) > 100 else consensus.investment_recommendation
        }
    
    def _calculate_decision_confidence(self, signal: TradingSignal, consensus: ResearchConsensus) -> float:
        """计算决策信心"""
        
        # 基于信号强度和共识信心
        base_confidence = (signal.strength + signal.confidence + consensus.confidence_level) / 3
        
        # 风险调整
        if len(signal.risk_factors) > 2:
            risk_adjustment = -0.1
        else:
            risk_adjustment = 0
        
        return min(1.0, max(0.3, base_confidence + risk_adjustment))
    
    def _calculate_expected_outcome(self, strategy: TradingStrategy, risk_params: RiskParameters) -> Dict:
        """计算预期结果"""
        
        return {
            "expected_return": strategy.expected_return,
            "expected_volatility": strategy.expected_volatility,
            "win_probability": strategy.win_rate,
            "risk_reward_ratio": risk_params.risk_reward_ratio,
            "max_potential_loss": risk_params.stop_loss_percentage,
            "max_potential_gain": risk_params.take_profit_percentage
        }
    
    def _define_monitoring_indicators(self, strategy: TradingStrategy) -> List[str]:
        """定义监控指标"""
        
        base_indicators = [
            "价格变化",
            "成交量变化",
            "持仓量变化",
            "技术指标状态"
        ]
        
        if strategy.strategy_type == "trend_following":
            base_indicators.extend(["趋势强度", "动量指标"])
        elif strategy.strategy_type == "breakout":
            base_indicators.extend(["突破有效性", "回调幅度"])
        
        return base_indicators
    
    def _define_adjustment_triggers(self, signal: TradingSignal, risk_params: RiskParameters) -> List[str]:
        """定义调整触发条件"""
        
        return [
            f"价格触及止损位({risk_params.stop_loss_price})",
            f"价格达到止盈位({risk_params.take_profit_price})",
            "研究共识发生重大变化",
            "市场流动性急剧恶化",
            "基本面出现重大变化"
        ]
    
    async def _generate_trader_reasoning(self, consensus: ResearchConsensus,
                                       signal: TradingSignal,
                                       strategy: TradingStrategy) -> str:
        """生成交易员推理过程"""
        
        reasoning_prompt = f"""
作为资深期货交易员，请总结以下交易决策的推理过程：

研究共识: {consensus.consensus_type} (信心: {consensus.confidence_level:.1%})
交易信号: {signal.direction.value} (强度: {signal.strength:.1%})
交易策略: {strategy.strategy_name} ({strategy.strategy_type})

请用简洁的语言总结交易逻辑和决策依据。
"""
        
        try:
            async with DeepSeekAPIClient(self.api_key) as client:
                response = await client.chat_completion(
                    messages=[
                        {"role": "system", "content": "你是一位专业的期货交易员，请提供简洁的交易推理。"},
                        {"role": "user", "content": reasoning_prompt}
                    ],
                    model=self.deepseek_config.get("model", "deepseek-chat"),
                    temperature=0.1,
                    max_tokens=500
                )
                
                if response.get("success"):
                    return response.get("content", "交易推理生成失败")
                else:
                    return "交易推理生成失败"
        except:
            return f"基于{consensus.consensus_type}共识，采用{strategy.strategy_name}，信号强度{signal.strength:.1%}"
    
    def get_trader_info(self) -> Dict:
        """获取交易员信息"""
        return {
            "name": "期货交易员",
            "role": self.role,
            "risk_tolerance": self.risk_tolerance,
            "position_sizing_method": self.position_sizing_method,
            "default_stop_loss": self.default_stop_loss,
            "default_take_profit": self.default_take_profit,
            "supported_contracts": list(self.contract_specs.keys()),
            "version": "1.0.0"
        }

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_futures_trader():
    """测试期货交易员"""
    
    print("💼 测试期货交易员...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建交易员
    trader = FuturesTrader(config)
    
    print(f"交易员信息: {trader.get_trader_info()}")
    
    # 创建模拟数据
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState, ModuleAnalysisResult
    from 期货TradingAgents系统_研究经理 import ResearchConsensus, DebateManagementResult
    
    # 模拟分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-19"
    )
    
    # 模拟研究共识
    research_consensus = ResearchConsensus(
        commodity="RB",
        analysis_date="2025-01-19",
        consensus_type="bullish",
        confidence_level=0.75,
        key_findings=["库存去化加速", "需求预期改善", "技术面突破确认"],
        investment_recommendation="建议适度做多，设置合理止损",
        bull_weight=0.6,
        bear_weight=0.4
    )
    
    # 模拟辩论结果
    debate_result = DebateManagementResult(
        commodity="RB",
        analysis_date="2025-01-19",
        total_rounds=2,
        overall_debate_quality=7.5
    )
    debate_result.final_consensus = research_consensus
    
    try:
        print("\n💡 开始制定交易决策...")
        trading_decision = await trader.make_trading_decision(
            analysis_state, research_consensus, debate_result
        )
        
        print(f"✅ 交易决策完成")
        print(f"   交易方向: {trading_decision.trading_signal.direction.value}")
        print(f"   信号强度: {trading_decision.trading_signal.strength:.1%}")
        print(f"   仓位比例: {trading_decision.position_sizing.position_percentage:.1%}")
        print(f"   合约数量: {trading_decision.position_sizing.contract_quantity}")
        print(f"   决策信心: {trading_decision.decision_confidence:.1%}")
        print(f"   策略类型: {trading_decision.trading_strategy.strategy_name}")
        
        # 保存结果
        result_file = Path("test_trading_decision_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(trading_decision), f, ensure_ascii=False, indent=2, default=str)
        
        print(f"   结果已保存到: {result_file}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 期货交易员测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_futures_trader())
