#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 第三阶段完整版
整合交易执行层，提供端到端的完整交易决策流程

功能特点：
1. 完整的Trading Agents工作流 (分析→研究→交易→风险→投资组合)
2. 交易员Agent专业交易决策
3. 风险管理团队多角度风险评估
4. 投资组合经理最终决策和资金配置
5. 完整的执行指令生成

作者: AI Assistant
版本: 2.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import sys

# 导入所有模块
from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState,
    FuturesAnalysisIntegrator,
    FuturesTradingAgentsConfig,
    AnalysisStatus
)
from 期货TradingAgents系统_看涨研究员 import (
    FuturesBullResearcher,
    BullishAnalysisResult
)
from 期货TradingAgents系统_看跌研究员 import (
    FuturesBearResearcher,
    BearishAnalysisResult
)
from 期货TradingAgents系统_研究经理 import (
    FuturesResearchManager,
    DebateManagementResult
)
from 期货TradingAgents系统_交易员 import (
    FuturesTrader,
    TradingDecision
)
from 期货TradingAgents系统_风险管理团队 import (
    FuturesRiskManager,
    RiskDebateResult
)
from 期货TradingAgents系统_投资组合经理 import (
    FuturesPortfolioManager,
    PortfolioDecisionResult
)
from 期货TradingAgents系统_工具模块 import (
    TimeUtils,
    FileManager,
    log_execution_time
)

# ============================================================================
# 1. 完整系统结果数据结构
# ============================================================================

@dataclass
class CompleteTradingExecutionResult:
    """完整交易执行结果"""
    # 基础信息
    commodity: str
    analysis_date: str
    system_version: str = "2.0.0"
    
    # 各阶段结果
    analysis_state: FuturesAnalysisState = None
    bull_analysis: BullishAnalysisResult = None
    bear_analysis: BearishAnalysisResult = None
    debate_management: DebateManagementResult = None
    trading_decision: TradingDecision = None
    risk_assessment: RiskDebateResult = None
    portfolio_decision: PortfolioDecisionResult = None
    
    # 最终执行指令
    final_execution_orders: List = None
    execution_summary: Dict = None
    
    # 执行统计
    total_execution_time: float = 0.0
    stage_timings: Dict[str, float] = None
    
    # 质量指标
    overall_confidence: float = 0.0
    decision_quality_score: float = 0.0
    risk_management_score: float = 0.0
    
    # 元数据
    completion_timestamp: str = ""

# ============================================================================
# 2. 完整交易执行系统
# ============================================================================

class CompleteFuturesTradingExecution:
    """完整的期货Trading Agents交易执行系统"""
    
    def __init__(self, config_file: str = None, custom_config: Dict = None):
        # 加载配置
        self.config = FuturesTradingAgentsConfig(config_file, custom_config)
        
        # 初始化所有组件
        self.integrator = FuturesAnalysisIntegrator(
            data_root_dir=self.config.get("data_root_dir"),
            config=self.config.to_dict()
        )
        self.bull_researcher = FuturesBullResearcher(self.config.to_dict())
        self.bear_researcher = FuturesBearResearcher(self.config.to_dict())
        self.research_manager = FuturesResearchManager(self.config.to_dict())
        self.trader = FuturesTrader(self.config.to_dict())
        self.risk_manager = FuturesRiskManager(self.config.to_dict())
        self.portfolio_manager = FuturesPortfolioManager(self.config.to_dict())
        
        # 文件管理器
        self.file_manager = FileManager(self.config.get("results_dir"))
        
        # 日志
        self.logger = self._setup_logger()
        
        # 支持的品种
        self.supported_commodities = self.config.get("supported_commodities", [])
        
        self.logger.info("期货Trading Agents完整交易执行系统初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger("CompleteFuturesTradingExecution")
        
        # 设置日志级别
        log_level = self.config.get("logging", {}).get("level", "INFO")
        logger.setLevel(getattr(logging, log_level))
        
        # 如果还没有处理器，添加处理器
        if not logger.handlers:
            # 控制台处理器
            if self.config.get("logging", {}).get("console_logging", True):
                console_handler = logging.StreamHandler()
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_handler.setFormatter(console_formatter)
                logger.addHandler(console_handler)
            
            # 文件处理器
            if self.config.get("logging", {}).get("file_logging", True):
                log_file = Path(self.config.get("logs_dir", "logs")) / "trading_execution.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        return logger
    
    @log_execution_time()
    async def execute_complete_trading_flow(self, commodity: str, analysis_date: str = None, selected_modules: List[str] = None) -> CompleteTradingExecutionResult:
        """执行完整的交易流程"""
        
        if analysis_date is None:
            analysis_date = TimeUtils.get_recent_trading_day()
        
        self.logger.info(f"开始完整交易执行流程: {commodity} ({analysis_date})")
        
        start_time = datetime.now()
        stage_timings = {}
        
        try:
            # 验证输入
            self._validate_inputs(commodity, analysis_date)
            
            # 阶段1: 数据收集和整合
            self.logger.info("🔄 阶段1: 数据收集和整合...")
            stage_start = datetime.now()
            
            analysis_state = await self.integrator.collect_all_analyses(commodity, analysis_date, selected_modules)
            
            stage_timings["data_collection"] = (datetime.now() - stage_start).total_seconds()
            self.logger.info(f"数据收集完成，进度: {analysis_state.get_analysis_progress():.1%}")
            
            # 阶段2: 研究员分析和辩论
            self.logger.info("🐂🐻 阶段2: 研究员分析和辩论...")
            stage_start = datetime.now()
            
            # 并行执行看涨和看跌分析
            bull_task = self.bull_researcher.analyze_bullish_perspective(analysis_state)
            bear_task = self.bear_researcher.analyze_bearish_perspective(analysis_state)
            
            bull_result, bear_result = await asyncio.gather(bull_task, bear_task)
            
            # 研究经理主持辩论
            debate_result = await self.research_manager.manage_research_debate(
                analysis_state, bull_result, bear_result
            )
            
            stage_timings["research_debate"] = (datetime.now() - stage_start).total_seconds()
            self.logger.info(f"研究辩论完成 - 共识: {debate_result.final_consensus.consensus_type}")
            
            # 阶段3: 交易员决策
            self.logger.info("💼 阶段3: 交易员决策...")
            stage_start = datetime.now()
            
            trading_decision = await self.trader.make_trading_decision(
                analysis_state, debate_result.final_consensus, debate_result
            )
            
            stage_timings["trading_decision"] = (datetime.now() - stage_start).total_seconds()
            self.logger.info(f"交易决策完成 - 方向: {trading_decision.trading_signal.direction.value}")
            
            # 阶段4: 风险管理评估
            self.logger.info("⚠️ 阶段4: 风险管理评估...")
            stage_start = datetime.now()
            
            risk_assessment = await self.risk_manager.manage_risk_assessment(
                trading_decision, analysis_state
            )
            
            stage_timings["risk_assessment"] = (datetime.now() - stage_start).total_seconds()
            self.logger.info(f"风险评估完成 - 建议: {risk_assessment.final_recommendation.value}")
            
            # 阶段5: 投资组合决策
            self.logger.info("💰 阶段5: 投资组合决策...")
            stage_start = datetime.now()
            
            portfolio_decision = await self.portfolio_manager.make_portfolio_decision(
                trading_decision, risk_assessment, analysis_state
            )
            
            stage_timings["portfolio_decision"] = (datetime.now() - stage_start).total_seconds()
            self.logger.info(f"投资组合决策完成 - 决策: {portfolio_decision.portfolio_decision.value}")
            
            # 阶段6: 最终执行指令整合
            self.logger.info("📋 阶段6: 执行指令整合...")
            stage_start = datetime.now()
            
            final_execution_orders, execution_summary = await self._integrate_execution_orders(
                trading_decision, risk_assessment, portfolio_decision
            )
            
            stage_timings["execution_integration"] = (datetime.now() - stage_start).total_seconds()
            
            # 计算质量指标
            quality_metrics = self._calculate_quality_metrics(
                analysis_state, debate_result, trading_decision, risk_assessment, portfolio_decision
            )
            
            # 构建完整结果
            total_time = (datetime.now() - start_time).total_seconds()
            
            complete_result = CompleteTradingExecutionResult(
                commodity=commodity,
                analysis_date=analysis_date,
                analysis_state=analysis_state,
                bull_analysis=bull_result,
                bear_analysis=bear_result,
                debate_management=debate_result,
                trading_decision=trading_decision,
                risk_assessment=risk_assessment,
                portfolio_decision=portfolio_decision,
                final_execution_orders=final_execution_orders,
                execution_summary=execution_summary,
                total_execution_time=total_time,
                stage_timings=stage_timings,
                overall_confidence=quality_metrics["overall_confidence"],
                decision_quality_score=quality_metrics["decision_quality_score"],
                risk_management_score=quality_metrics["risk_management_score"],
                completion_timestamp=datetime.now().isoformat()
            )
            
            # 保存结果
            await self._save_execution_result(complete_result)
            
            self.logger.info(f"完整交易执行流程完成，总耗时: {total_time:.1f}秒")
            
            return complete_result
            
        except Exception as e:
            self.logger.error(f"交易执行流程失败: {e}")
            
            # 返回失败结果
            return CompleteTradingExecutionResult(
                commodity=commodity,
                analysis_date=analysis_date,
                execution_summary={
                    "status": "failed",
                    "error": str(e),
                    "recommendation": "执行失败，请检查配置和数据"
                },
                total_execution_time=(datetime.now() - start_time).total_seconds(),
                completion_timestamp=datetime.now().isoformat()
            )
    
    def _validate_inputs(self, commodity: str, analysis_date: str):
        """验证输入参数"""
        
        # 验证商品代码
        if commodity not in self.supported_commodities:
            raise ValueError(f"不支持的商品代码: {commodity}。支持的品种: {', '.join(self.supported_commodities[:10])}...")
        
        # 验证日期格式
        try:
            datetime.strptime(analysis_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"无效的日期格式: {analysis_date}，应为YYYY-MM-DD格式")
        
        # 检查API密钥
        if not self.config.get("api_settings", {}).get("deepseek", {}).get("api_key"):
            raise ValueError("未配置DeepSeek API密钥，请在配置文件中设置api_settings.deepseek.api_key")
    
    async def _integrate_execution_orders(self, 
                                        trading_decision: TradingDecision,
                                        risk_assessment: RiskDebateResult,
                                        portfolio_decision: PortfolioDecisionResult) -> tuple:
        """整合执行指令"""
        
        final_orders = []
        
        # 从投资组合决策中获取主要执行指令
        if portfolio_decision.execution_orders:
            final_orders.extend(portfolio_decision.execution_orders)
        
        # 执行摘要
        execution_summary = {
            "total_orders": len(final_orders),
            "total_allocated_capital": portfolio_decision.allocated_capital,
            "portfolio_decision": portfolio_decision.portfolio_decision.value,
            "risk_level": risk_assessment.final_risk_level.value,
            "execution_confidence": portfolio_decision.decision_confidence,
            "key_execution_points": []
        }
        
        # 添加关键执行要点
        if final_orders:
            for order in final_orders:
                execution_summary["key_execution_points"].append({
                    "commodity": order.commodity,
                    "direction": order.direction.value,
                    "quantity": order.quantity,
                    "priority": order.priority,
                    "reasoning": order.reasoning[:50] + "..." if len(order.reasoning) > 50 else order.reasoning
                })
        
        # 风险控制要点
        execution_summary["risk_controls"] = {
            "stop_conditions": portfolio_decision.stop_conditions[:3] if portfolio_decision.stop_conditions else [],
            "monitoring_requirements": risk_assessment.risk_manager_decision.get("monitoring_requirements", [])[:3] if risk_assessment.risk_manager_decision else [],
            "review_schedule": portfolio_decision.review_schedule
        }
        
        return final_orders, execution_summary
    
    def _calculate_quality_metrics(self, 
                                 analysis_state: FuturesAnalysisState,
                                 debate_result: DebateManagementResult,
                                 trading_decision: TradingDecision,
                                 risk_assessment: RiskDebateResult,
                                 portfolio_decision: PortfolioDecisionResult) -> Dict:
        """计算质量指标"""
        
        metrics = {}
        
        # 整体信心度
        confidence_components = [
            analysis_state.get_analysis_progress(),  # 数据完整性
            debate_result.final_consensus.confidence_level,  # 研究共识信心
            trading_decision.decision_confidence,  # 交易决策信心
            portfolio_decision.decision_confidence  # 投资组合决策信心
        ]
        
        overall_confidence = sum(confidence_components) / len(confidence_components)
        metrics["overall_confidence"] = overall_confidence
        
        # 决策质量评分
        decision_quality_factors = [
            debate_result.overall_debate_quality / 10,  # 辩论质量
            1.0 if risk_assessment.consensus_reached else 0.7,  # 风险共识
            trading_decision.trading_strategy.win_rate,  # 策略胜率
            min(1.0, trading_decision.risk_parameters.risk_reward_ratio / 3)  # 风险回报比
        ]
        
        decision_quality_score = sum(decision_quality_factors) / len(decision_quality_factors)
        metrics["decision_quality_score"] = decision_quality_score
        
        # 风险管理评分
        risk_management_factors = [
            risk_assessment.debate_quality / 10,  # 风险辩论质量
            1.0 - (len(risk_assessment.key_disagreements) / 10),  # 分歧程度（越少越好）
            portfolio_decision.decision_confidence,  # 最终决策信心
            1.0 if portfolio_decision.stop_conditions else 0.5  # 风控措施完整性
        ]
        
        risk_management_score = sum(risk_management_factors) / len(risk_management_factors)
        metrics["risk_management_score"] = risk_management_score
        
        return metrics
    
    async def _save_execution_result(self, result: CompleteTradingExecutionResult):
        """保存执行结果"""
        
        try:
            # 创建结果目录
            result_dir = Path(self.config.get("results_dir")) / "complete_execution" / result.commodity
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存完整结果
            result_file = result_dir / f"complete_execution_{result.analysis_date}.json"
            self.file_manager.save_json(asdict(result), result_file)
            
            # 保存执行摘要
            summary_file = result_dir / f"execution_summary_{result.analysis_date}.json"
            self.file_manager.save_json(result.execution_summary, summary_file)
            
            # 保存执行指令
            if result.final_execution_orders:
                orders_file = result_dir / f"execution_orders_{result.analysis_date}.json"
                orders_data = [asdict(order) for order in result.final_execution_orders]
                self.file_manager.save_json(orders_data, orders_file)
            
            self.logger.info(f"执行结果已保存: {result_file}")
            
        except Exception as e:
            self.logger.error(f"保存执行结果失败: {e}")
    
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            "name": "期货Trading Agents完整交易执行系统",
            "version": "2.0.0",
            "supported_commodities": len(self.supported_commodities),
            "config": {
                "max_debate_rounds": self.config.get("debate_settings", {}).get("max_debate_rounds", 2),
                "use_reasoning_mode": self.config.get("debate_settings", {}).get("enable_reasoning_mode", True),
                "data_root": self.config.get("data_root_dir"),
                "results_root": self.config.get("results_dir")
            },
            "execution_stages": [
                "数据收集和整合",
                "研究员分析和辩论", 
                "交易员决策",
                "风险管理评估",
                "投资组合决策",
                "执行指令整合"
            ],
            "components": {
                "data_integrator": "FuturesAnalysisIntegrator",
                "bull_researcher": "FuturesBullResearcher", 
                "bear_researcher": "FuturesBearResearcher",
                "research_manager": "FuturesResearchManager",
                "trader": "FuturesTrader",
                "risk_manager": "FuturesRiskManager",
                "portfolio_manager": "FuturesPortfolioManager"
            }
        }

# ============================================================================
# 2. 命令行接口
# ============================================================================

def create_cli_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="期货Trading Agents系统 - 第三阶段完整版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python 期货TradingAgents系统_第三阶段完整版.py --commodity RB
  python 期货TradingAgents系统_第三阶段完整版.py --commodity CU --date 2025-01-19
  python 期货TradingAgents系统_第三阶段完整版.py --list-commodities
  python 期货TradingAgents系统_第三阶段完整版.py --info
        """
    )
    
    parser.add_argument(
        "--commodity", "-c",
        type=str,
        help="期货品种代码 (如: RB, CU, AU)"
    )
    
    parser.add_argument(
        "--date", "-d",
        type=str,
        help="分析日期 (YYYY-MM-DD格式，默认为最近交易日)"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--list-commodities",
        action="store_true",
        help="列出支持的期货品种"
    )
    
    parser.add_argument(
        "--info",
        action="store_true", 
        help="显示系统信息"
    )
    
    return parser

async def main():
    """主函数"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    try:
        # 初始化系统
        system = CompleteFuturesTradingExecution(
            config_file=args.config or "期货TradingAgents系统_配置文件.json"
        )
        
        # 处理不同的命令
        if args.list_commodities:
            print("🎯 支持的期货品种:")
            commodities = system.supported_commodities
            categories = system.config.get("commodity_categories", {})
            
            for category, symbols in categories.items():
                print(f"\n【{category}】")
                for symbol in symbols:
                    if symbol in commodities:
                        print(f"  {symbol}")
            return
        
        if args.info:
            print("📊 系统信息:")
            info = system.get_system_info()
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return
        
        if not args.commodity:
            print("❌ 请指定要分析的期货品种，使用 --commodity 参数")
            print("使用 --list-commodities 查看支持的品种")
            return
        
        # 执行完整交易流程
        print(f"🚀 开始完整交易执行流程: {args.commodity}...")
        print("=" * 80)
        
        result = await system.execute_complete_trading_flow(args.commodity, args.date)
        
        # 显示结果摘要
        print("\n" + "=" * 80)
        print("📋 完整交易执行结果摘要")
        print("=" * 80)
        
        if result.execution_summary and result.execution_summary.get("status") != "failed":
            summary = result.execution_summary
            
            print(f"品种: {result.commodity}")
            print(f"日期: {result.analysis_date}")
            print(f"总耗时: {result.total_execution_time:.1f}秒")
            print(f"整体信心: {result.overall_confidence:.1%}")
            print(f"决策质量: {result.decision_quality_score:.1%}")
            print(f"风险管理: {result.risk_management_score:.1%}")
            
            print(f"\n💰 投资组合决策:")
            print(f"最终决策: {summary.get('portfolio_decision', 'N/A')}")
            print(f"分配资金: {summary.get('total_allocated_capital', 0):,.0f}")
            print(f"执行订单: {summary.get('total_orders', 0)}个")
            print(f"执行信心: {summary.get('execution_confidence', 0):.1%}")
            
            print(f"\n⚠️ 风险控制:")
            risk_controls = summary.get("risk_controls", {})
            print(f"风险等级: {summary.get('risk_level', 'N/A')}")
            print(f"复审计划: {risk_controls.get('review_schedule', 'N/A')}")
            
            if summary.get("key_execution_points"):
                print(f"\n📋 执行要点:")
                for i, point in enumerate(summary["key_execution_points"], 1):
                    print(f"  {i}. {point['commodity']} {point['direction']} {point['quantity']}手 (优先级: {point['priority']})")
            
            # 显示各阶段耗时
            if result.stage_timings:
                print(f"\n⏱️ 各阶段耗时:")
                for stage, duration in result.stage_timings.items():
                    print(f"   {stage}: {duration:.1f}秒")
        
        else:
            print(f"❌ 执行失败: {result.execution_summary.get('error', '未知错误')}")
        
        print(f"\n✅ 完整交易执行流程完成，详细结果已保存到结果目录")
        
    except Exception as e:
        print(f"❌ 系统运行失败: {e}")
        sys.exit(1)

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_complete_execution_system():
    """测试完整执行系统"""
    
    print("🚀 测试期货Trading Agents完整交易执行系统...")
    
    try:
        # 初始化系统
        system = CompleteFuturesTradingExecution(
            config_file="期货TradingAgents系统_配置文件.json"
        )
        
        print(f"系统信息: {system.get_system_info()}")
        
        # 检查API密钥配置
        if not system.config.get("api_settings", {}).get("deepseek", {}).get("api_key"):
            print("⚠️  未配置DeepSeek API密钥，将跳过实际执行")
            print("请在配置文件中设置api_settings.deepseek.api_key后重试")
            return
        
        # 执行完整流程
        print("\n🔍 开始完整交易执行流程...")
        result = await system.execute_complete_trading_flow("RB")  # 使用螺纹钢作为测试
        
        print(f"✅ 完整执行完成")
        print(f"   商品: {result.commodity}")
        print(f"   日期: {result.analysis_date}")
        print(f"   总耗时: {result.total_execution_time:.1f}秒")
        print(f"   整体信心: {result.overall_confidence:.1%}")
        print(f"   决策质量: {result.decision_quality_score:.1%}")
        print(f"   风险管理: {result.risk_management_score:.1%}")
        
        # 显示执行摘要
        if result.execution_summary:
            summary = result.execution_summary
            print(f"   投资组合决策: {summary.get('portfolio_decision', 'N/A')}")
            print(f"   分配资金: {summary.get('total_allocated_capital', 0):,.0f}")
            print(f"   执行订单数: {summary.get('total_orders', 0)}")
        
        # 显示各阶段耗时
        if result.stage_timings:
            print(f"\n⏱️ 各阶段耗时:")
            for stage, duration in result.stage_timings.items():
                print(f"   {stage}: {duration:.1f}秒")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✅ 完整执行系统测试完成")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 如果没有命令行参数，运行测试
        asyncio.run(test_complete_execution_system())
    else:
        # 如果有命令行参数，运行CLI
        asyncio.run(main())

