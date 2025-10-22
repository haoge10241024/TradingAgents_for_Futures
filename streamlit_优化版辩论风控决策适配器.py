#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit优化版辩论风控决策系统适配器
将优化版的辩论、风控、决策系统集成到Streamlit界面

功能特点：
1. 用户可控制辩论轮数
2. 口语化激烈辩论展示
3. 专业风控评估展示
4. CIO权威决策展示
5. 完整流程可视化

作者: AI Assistant
版本: 2.0.0
创建时间: 2025-01-19
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 导入优化版系统
from 完整版辩论风控决策系统_含交易员 import (
    CompleteOptimizedTradingSystem,
    DebateResult,
    RiskAssessment, 
    ExecutiveDecision,
    TradingDecision
)

from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState,
    ModuleAnalysisResult,
    AnalysisStatus
)

class StreamlitOptimizedTradingAdapter:
    """Streamlit优化版交易系统适配器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.system = CompleteOptimizedTradingSystem(config)
        self.logger = logging.getLogger("StreamlitOptimizedTradingAdapter")
        
    def run_optimized_analysis_for_streamlit(self, analysis_state: FuturesAnalysisState,
                                           debate_rounds: int = 3) -> Dict[str, Any]:
        """为Streamlit运行优化版分析"""
        
        try:
            # 使用线程池执行异步分析，避免事件循环冲突
            import concurrent.futures
            
            def run_async_in_thread():
                """在新线程中运行异步协程"""
                # 在新线程中创建事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.system.run_complete_analysis(analysis_state, debate_rounds)
                    )
                finally:
                    loop.close()
            
            # 使用线程执行
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                result = future.result()
            
            # 格式化为Streamlit友好的格式
            return self._format_for_streamlit(result)
            
        except Exception as e:
            self.logger.error(f"优化版分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "commodity": analysis_state.commodity
            }
    
    def _format_for_streamlit(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化结果供Streamlit显示"""
        
        # 检查分析是否成功
        if not result.get("success", False):
            # 分析失败时返回简化的错误结果
            return {
                "success": False,
                "commodity": result.get("commodity", "未知"),
                "analysis_date": result.get("analysis_date", "未知"),
                "process_timestamp": result.get("process_timestamp", "未知"),
                "error": result.get("error", "未知错误"),
                "metadata": {
                    "version": "2.1.0_with_trader",
                    "stages_completed": 0,
                    "analysis_failed": True
                }
            }
        
        # 分析成功时返回完整格式化结果
        formatted_result = {
            "success": True,
            "commodity": result["commodity"],
            "analysis_date": result["analysis_date"],
            "process_timestamp": result["process_timestamp"],
            
            # 直接使用已经格式化好的结果
            "debate_section": result["debate_section"],
            "trading_section": result["trading_section"],  # 新增交易员部分
            "risk_section": result["risk_section"],
            "decision_section": result["decision_section"],
            
            # 系统元数据
            "metadata": result["metadata"],
            
            # 用于显示的完整报告
            "full_report": self._generate_full_report(result)
        }
        
        return formatted_result
    
    def _format_debate_section(self, debate_data: Dict) -> Dict[str, Any]:
        """格式化辩论部分"""
        
        section = {
            "title": f"🥊 激烈辩论环节（共{debate_data['total_rounds']}轮）",
            "winner": debate_data["final_winner"],
            "scores": {
                "bull": debate_data["bull_score"],
                "bear": debate_data["bear_score"]
            },
            "summary": debate_data["debate_summary"],
            "consensus_points": debate_data["key_consensus"],
            "unresolved_issues": debate_data["unresolved_issues"],
            "detailed_rounds": []
        }
        
        # 格式化每轮辩论详情
        for i, round_data in enumerate(debate_data["detailed_rounds"], 1):
            round_formatted = {
                "round_number": i,
                "bull_argument": round_data["bull_argument"],
                "bear_argument": round_data["bear_argument"],
                "bull_score": round_data["bull_score"],
                "bear_score": round_data["bear_score"],
                "result": round_data["round_result"],
                "key_points": round_data["key_points"],
                "audience_reaction": round_data["audience_reaction"]
            }
            section["detailed_rounds"].append(round_formatted)
        
        return section
    
    def _format_risk_section(self, risk_data: Dict) -> Dict[str, Any]:
        """格式化风险评估部分"""
        
        section = {
            "title": "🛡️ 专业风控部门评估",
            "overall_risk": risk_data["overall_risk_level"],
            "risk_scores": risk_data["risk_scores"],
            "key_factors": risk_data["key_risk_factors"],
            "mitigation_measures": risk_data["risk_mitigation"],
            "position_limit": f"{risk_data['position_limit']:.1%}",
            "stop_loss": f"{risk_data['stop_loss_level']:.1%}",
            "manager_opinion": risk_data["risk_manager_opinion"]
        }
        
        return section
    
    def _format_decision_section(self, decision_data: Dict) -> Dict[str, Any]:
        """格式化决策部分"""
        
        section = {
            "title": "👔 CIO最终权威决策",
            "final_decision": decision_data["final_decision"],
            "confidence": f"{decision_data['confidence_level']:.1%}",
            "position_size": f"{decision_data['position_size']:.1%}",
            "time_horizon": decision_data["time_horizon"],
            "rationale": decision_data["key_rationale"],
            "execution_plan": decision_data["execution_plan"],
            "monitoring_points": decision_data["monitoring_points"],
            "cio_statement": decision_data["cio_statement"]
        }
        
        return section
    
    def _generate_full_report(self, result: Dict[str, Any]) -> str:
        """生成完整报告文本"""
        
        commodity = result["commodity"]
        date = result["analysis_date"]
        
        report_lines = [
            f"期货Trading Agents系统 - 优化版完整分析报告",
            "",
            f"品种：{commodity}",
            f"分析日期：{date}",
            f"报告生成时间：{result['process_timestamp']}",
            "",
            "=" * 80,
            ""
        ]
        
        # 第一阶段：激烈辩论环节
        if "debate_section" in result:
            debate = result["debate_section"]
            report_lines.extend([
                f"第一阶段：{debate.get('title', '激烈辩论环节')}",
                "-" * 60,
                f"辩论胜者：{debate.get('winner', '未知')}",
                f"最终得分：多头 {debate.get('scores', {}).get('bull', 0):.1f}分 vs 空头 {debate.get('scores', {}).get('bear', 0):.1f}分",
                "",
                "辩论总结：",
                debate.get("summary", "暂无总结"),
                ""
            ])
            
            # 详细辩论轮次（如果有）
            if "detailed_rounds" in debate and debate["detailed_rounds"]:
                for i, round_data in enumerate(debate["detailed_rounds"], 1):
                    report_lines.extend([
                        f"第{i}轮辩论：",
                        "",
                        f"多头发言（{round_data.get('bull_score', 0):.1f}分）：",
                        str(round_data.get("bull_argument", ""))[:300] + ("..." if len(str(round_data.get("bull_argument", ""))) > 300 else ""),
                        "",
                        f"空头反驳（{round_data.get('bear_score', 0):.1f}分）：", 
                        str(round_data.get("bear_argument", ""))[:300] + ("..." if len(str(round_data.get("bear_argument", ""))) > 300 else ""),
                        "",
                        f"本轮结果：{round_data.get('round_result', '未知')}",
                        f"观众反应：{round_data.get('audience_reaction', '暂无')}",
                        "",
                        "-" * 40,
                        ""
                    ])
        
        # 第二阶段：专业交易员决策
        if "trading_section" in result:
            trading = result["trading_section"]
            report_lines.extend([
                f"第二阶段：{trading.get('title', '专业交易员决策')}",
                "-" * 60,
                f"策略类型：{trading.get('strategy_type', '未知')}",
                f"仓位管理：{trading.get('position_size', '未知')}",
                f"风险收益比：{trading.get('risk_reward_ratio', '未知')}",
                f"持仓周期：{trading.get('time_horizon', '未知')}",
                "",
                "交易逻辑：",
                trading.get("reasoning", "暂无逻辑"),
                "",
                "入场点位：",
                str(trading.get("entry_points", [])),
                "",
                "出场点位：",
                str(trading.get("exit_points", [])),
                "",
                "执行计划：",
                trading.get("execution_plan", "暂无计划"),
                "",
                "市场条件：",
                trading.get("market_conditions", "暂无条件"),
                "",
                "=" * 60,
                ""
            ])
        
        # 第三阶段：专业风控评估
        if "risk_section" in result:
            risk = result["risk_section"]
            report_lines.extend([
                f"第三阶段：{risk.get('title', '专业风控评估')}",
                "-" * 60,
                f"整体风险等级：{risk.get('overall_risk', '未知')}",
                f"建议仓位上限：{risk.get('position_limit', '未知')}",
                f"建议止损位：{risk.get('stop_loss', '未知')}",
                "",
                "风控经理专业意见：",
                risk.get("manager_opinion", "暂无意见"),
                "",
                "=" * 60,
                ""
            ])
        
        # 第四阶段：CIO最终权威决策
        if "decision_section" in result:
            decision = result["decision_section"]
            report_lines.extend([
                f"第四阶段：{decision.get('title', 'CIO最终权威决策')}",
                "-" * 60,
                f"最终决策：{decision.get('final_decision', '未知')}",
                f"决策信心度：{decision.get('confidence', '未知')}",
                f"建议仓位：{decision.get('position_size', '未知')}",
                f"持仓周期：{decision.get('time_horizon', '未知')}",
                "",
                "CIO权威声明：",
                decision.get("cio_statement", "暂无声明"),
                "",
                "=" * 60,
                ""
            ])
        
        # 系统元数据
        if "metadata" in result:
            metadata = result["metadata"]
            report_lines.extend([
                "系统信息：",
                "-" * 30,
                f"系统版本：{metadata.get('version', '未知')}",
                f"完成阶段：{metadata.get('stages_completed', 0)}/5",
                f"分析轮数：{metadata.get('debate_rounds_conducted', 0)}轮",
                "",
            ])
        
        report_lines.extend([
            "=" * 80,
            "",
            f"报告完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "本报告由期货Trading Agents系统优化版生成",
            "包含完整的5阶段专业分析流程：分析师→辩论→交易员→风控→CIO决策"
        ])
        
        return "\n".join(report_lines)

    async def run_optimized_debate_risk_decision_for_streamlit(
        self,
        commodity: str,
        analyses: Dict[str, Any],
        debate_rounds: int = 3
    ) -> Dict[str, Any]:
        """
        为Streamlit执行优化版辩论风控决策分析
        
        Args:
            commodity: 品种代码
            analyses: 分析师团队的分析结果
            debate_rounds: 辩论轮数，默认3轮
            
        Returns:
            Dict[str, Any]: 格式化后的分析结果
        """
        try:
            # 创建FuturesAnalysisState对象
            from 期货TradingAgents系统_基础架构 import FuturesAnalysisState, ModuleAnalysisResult
            
            # 创建模块分析结果
            def create_module_result(module_data):
                if module_data and module_data.get("success", False):
                    return ModuleAnalysisResult(
                        status="completed",
                        result_data=module_data,
                        confidence_score=module_data.get("confidence", 0.8),
                        execution_time=module_data.get("execution_time", 0.0),
                        error_message=None
                    )
                else:
                    return ModuleAnalysisResult(
                        status="failed",
                        result_data=module_data or {},
                        confidence_score=0.0,
                        execution_time=0.0,
                        error_message=module_data.get("error", "分析失败") if module_data else "无数据"
                    )
            
            analysis_state = FuturesAnalysisState(
                commodity=commodity,
                analysis_date=datetime.now().strftime('%Y-%m-%d'),
                inventory_analysis=create_module_result(analyses.get("inventory")),
                positioning_analysis=create_module_result(analyses.get("positioning")),
                term_structure_analysis=create_module_result(analyses.get("term_structure")),
                technical_analysis=create_module_result(analyses.get("technical")),
                basis_analysis=create_module_result(analyses.get("basis")),
                news_analysis=create_module_result(analyses.get("news"))
            )
            
            # 调用核心分析方法
            result = await self.system.run_complete_analysis(
                analysis_state=analysis_state,
                debate_rounds=debate_rounds
            )
            
            # 格式化结果用于Streamlit显示
            formatted_result = self._format_for_streamlit(result)
            
            return formatted_result
            
        except Exception as e:
            print(f"❌ 辩论风控决策分析异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回错误结果
            return {
                "success": False,
                "error": str(e),
                "commodity": commodity,
                "analysis_date": "未知",
                "process_timestamp": "未知",
                "analysis_version": "v2.1.0_with_trader",
                
                # 简化的错误段落
                "debate_section": {"title": "辩论分析失败", "summary": f"分析异常: {str(e)}"},
                "trading_section": {"title": "交易员决策失败", "reasoning": f"分析异常: {str(e)}"},
                "risk_section": {"title": "风控评估失败", "manager_opinion": f"分析异常: {str(e)}"},
                "decision_section": {"title": "最终决策失败", "final_decision": f"分析异常: {str(e)}"},
                
                "metadata": {
                    "version": "v2.1.0_with_trader",
                    "stages_completed": 0,
                    "debate_rounds_conducted": 0
                },
                
                "full_report": f"分析失败: {str(e)}"
            }

# ============================================================================
# 便捷调用函数
# ============================================================================

def analyze_optimized_trading_for_streamlit(commodity: str, analysis_date: str,
                                          debate_rounds: int = 3,
                                          config: Dict = None) -> Dict[str, Any]:
    """便捷函数：为Streamlit运行优化版交易分析"""
    
    if not config:
        config = {
            "api_settings": {
                "deepseek": {
                    "api_key": "your_api_key_here",
                    "base_url": "https://api.deepseek.com/v1"
                }
            }
        }
    
    # 创建分析状态（简化版，实际应该从现有系统获取）
    analysis_state = FuturesAnalysisState(
        commodity=commodity,
        analysis_date=analysis_date
    )
    
    # 添加一些模拟的分析结果
    analysis_state.inventory_analysis = ModuleAnalysisResult(
        module_name="inventory",
        commodity=commodity,
        analysis_date=analysis_date,
        status=AnalysisStatus.COMPLETED
    )
    
    analysis_state.positioning_analysis = ModuleAnalysisResult(
        module_name="positioning", 
        commodity=commodity,
        analysis_date=analysis_date,
        status=AnalysisStatus.COMPLETED
    )
    
    # 创建适配器并运行分析
    adapter = StreamlitOptimizedTradingAdapter(config)
    
    return adapter.run_optimized_analysis_for_streamlit(
        analysis_state, debate_rounds
    )

# ============================================================================
# 测试代码
# ============================================================================

def test_streamlit_adapter():
    """测试Streamlit适配器"""
    
    print("🧪 测试Streamlit优化版交易适配器")
    print("=" * 50)
    
    # 运行测试分析
    result = analyze_optimized_trading_for_streamlit(
        commodity="螺纹钢",
        analysis_date="2025-01-19", 
        debate_rounds=2  # 测试用2轮
    )
    
    if result["success"]:
        print("✅ 适配器测试成功！")
        print(f"品种：{result['commodity']}")
        print(f"辩论轮数：{result['debate_section']['title']}")
        print(f"风险等级：{result['risk_section']['overall_risk']}")
        print(f"最终决策：{result['decision_section']['final_decision']}")
    else:
        print(f"❌ 适配器测试失败：{result['error']}")

if __name__ == "__main__":
    test_streamlit_adapter()
