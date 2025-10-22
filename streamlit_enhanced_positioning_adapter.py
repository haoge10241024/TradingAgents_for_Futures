#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit增强版持仓分析适配器
将enhanced_positioning_analysis_system.py适配到Streamlit系统中
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入增强版持仓分析系统
from enhanced_positioning_analysis_system import (
    EnhancedPositioningAnalysisEngine,
    SYMBOL_NAMES
)

class StreamlitEnhancedPositioningAdapter:
    """Streamlit增强版持仓分析适配器"""
    
    def __init__(self):
        self.engine = EnhancedPositioningAnalysisEngine()
    
    def analyze_positioning_for_streamlit(self, symbol: str, analysis_date: str = None, 
                                        use_reasoner: bool = True) -> Dict[str, Any]:
        """
        为Streamlit系统提供持仓分析
        
        Args:
            symbol: 品种代码
            analysis_date: 分析日期
            use_reasoner: 是否使用reasoner模型
            
        Returns:
            Dict: 分析结果
        """
        try:
            # 运行异步分析 - 修复事件循环问题
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果已有事件循环，使用create_task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.engine.analyze_variety_comprehensive(
                            symbol=symbol,
                            analysis_date=analysis_date,
                            use_reasoner=use_reasoner
                        )
                    )
                    result = future.result()
            except RuntimeError:
                # 没有运行的事件循环，直接使用asyncio.run
                result = asyncio.run(
                    self.engine.analyze_variety_comprehensive(
                        symbol=symbol,
                        analysis_date=analysis_date,
                        use_reasoner=use_reasoner
                    )
                )
            
            # 处理结果格式化
            if result.get("success"):
                return self._format_for_streamlit(result)
            else:
                return {
                    "success": False,
                    "error": result.get("error", "分析失败"),
                    "symbol": symbol,
                    "symbol_name": SYMBOL_NAMES.get(symbol.upper(), symbol)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"持仓分析过程中发生错误: {str(e)}",
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol.upper(), symbol)
            }
    
    def _format_for_streamlit(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化结果以适配Streamlit显示"""
        
        formatted_result = {
            "success": True,
            "symbol": result.get("symbol", ""),
            "symbol_name": result.get("symbol_name", ""),
            "analysis_date": result.get("analysis_date", ""),
            "model_used": result.get("model_used", ""),
            "data_points": result.get("data_points", 0),
            "data_quality_score": result.get("data_quality_score", 0.0)
        }
        
        # 提取核心分析结果
        if "professional_analysis" in result:
            professional_content = result["professional_analysis"]
            formatted_result["ai_analysis"] = professional_content
            
            # 检查professional_analysis是否为JSON格式
            if isinstance(professional_content, str):
                # 如果是字符串且不为空，直接使用
                if len(professional_content.strip()) > 0:
                    formatted_result["analysis_content"] = professional_content
                else:
                    # 如果professional_analysis为空，尝试从structured_analysis生成
                    if "structured_analysis" in result:
                        analysis_content = self._generate_analysis_content_from_structured(result["structured_analysis"])
                        formatted_result["analysis_content"] = analysis_content
            else:
                # 如果不是字符串，尝试转换为字符串
                formatted_result["analysis_content"] = str(professional_content)
        else:
            # 如果没有professional_analysis字段，检查是否有结构化分析数据
            # 检查是否有直接的结构化分析字段（如spider_web_analysis等）
            structured_data = {}
            analysis_fields = ["spider_web_analysis", "smart_money_analysis", "seat_behavior_analysis", 
                             "concentration_analysis", "comprehensive_conclusion", "trading_recommendations"]
            
            for field in analysis_fields:
                if field in result:
                    structured_data[field] = result[field]
            
            if structured_data:
                # 有结构化数据，生成文本分析
                analysis_content = self._generate_analysis_content_from_structured(structured_data)
                formatted_result["ai_analysis"] = analysis_content
                formatted_result["analysis_content"] = analysis_content
                formatted_result["structured_analysis"] = structured_data
            elif "structured_analysis" in result:
                # 从structured_analysis生成文本分析
                analysis_content = self._generate_analysis_content_from_structured(result["structured_analysis"])
                formatted_result["ai_analysis"] = analysis_content
                formatted_result["analysis_content"] = analysis_content
        
        # 提取结构化分析结果（如果有JSON格式）
        analysis_sections = {}
        
        # 尝试解析结构化分析结果
        for key in ["spider_web_analysis", "smart_money_analysis", "seat_behavior_analysis", 
                   "concentration_analysis", "comprehensive_conclusion", "trading_recommendations"]:
            if key in result:
                analysis_sections[key] = result[key]
        
        if analysis_sections:
            formatted_result["structured_analysis"] = analysis_sections
        
        # 提取方法论解释
        if "methodology_explanation" in result:
            formatted_result["methodology"] = result["methodology_explanation"]
        
        # 提取支撑数据
        if "supporting_data" in result:
            formatted_result["supporting_data"] = result["supporting_data"]
        
        # 提取图表 - 转换为主界面期望的格式
        if "professional_charts" in result:
            charts_dict = result["professional_charts"]

            if charts_dict:
                if len(charts_dict) == 1:
                    # 单个图表，直接使用图表对象
                    chart_key = list(charts_dict.keys())[0]
                    formatted_result["charts_html"] = charts_dict[chart_key]
                    print(f"✅ 持仓分析图表数据已转换: 单个图表 '{chart_key}'")
                else:
                    # 多个图表，保持字典格式
                    formatted_result["charts_html"] = charts_dict
                    print(f"✅ 持仓分析图表数据已转换: {len(charts_dict)}个图表")
            else:
                formatted_result["charts_html"] = None
        
        # 提取外部引用
        if "external_citations" in result:
            formatted_result["citations"] = result["external_citations"]
        
        # 提取席位分类摘要
        if "seat_classification_summary" in result:
            formatted_result["seat_classification"] = result["seat_classification_summary"]
        
        # 提取历史分析
        if "historical_analysis" in result:
            formatted_result["historical_analysis"] = result["historical_analysis"]
        
        return formatted_result
    
    def _generate_analysis_content_from_structured(self, structured_analysis: Dict[str, Any]) -> str:
        """从结构化分析数据生成可读的文本分析内容"""
        
        content_parts = []
        
        # 1. 蜘蛛网分析
        if "spider_web_analysis" in structured_analysis:
            spider_data = structured_analysis["spider_web_analysis"]
            content_parts.append("🕸️ **蜘蛛网策略分析**")
            content_parts.append(f"信号方向: {spider_data.get('signal', '未知')}")
            content_parts.append(f"信号强度: {spider_data.get('strength', 0):.1f}")
            content_parts.append(f"分析信心: {spider_data.get('confidence', 0):.1f}")
            content_parts.append(f"核心逻辑: {spider_data.get('reasoning', '暂无')}")
            content_parts.append("")
        
        # 2. 聪明钱分析
        if "smart_money_analysis" in structured_analysis:
            smart_data = structured_analysis["smart_money_analysis"]
            content_parts.append("🧠 **聪明钱分析**")
            content_parts.append(f"信号方向: {smart_data.get('signal', '未知')}")
            content_parts.append(f"信号强度: {smart_data.get('strength', 0):.1f}")
            content_parts.append(f"分析信心: {smart_data.get('confidence', 0):.1f}")
            content_parts.append(f"核心逻辑: {smart_data.get('reasoning', '暂无')}")
            content_parts.append("")
        
        # 3. 席位行为分析
        if "seat_behavior_analysis" in structured_analysis:
            seat_data = structured_analysis["seat_behavior_analysis"]
            content_parts.append("💺 **席位行为分析**")
            content_parts.append(f"信号方向: {seat_data.get('signal', '未知')}")
            content_parts.append(f"信号强度: {seat_data.get('strength', 0):.1f}")
            content_parts.append(f"分析信心: {seat_data.get('confidence', 0):.1f}")
            content_parts.append(f"核心逻辑: {seat_data.get('reasoning', '暂无')}")
            content_parts.append("")
        
        # 4. 集中度分析
        if "concentration_analysis" in structured_analysis:
            conc_data = structured_analysis["concentration_analysis"]
            content_parts.append("📊 **持仓集中度分析**")
            content_parts.append(f"信号方向: {conc_data.get('signal', '未知')}")
            content_parts.append(f"信号强度: {conc_data.get('strength', 0):.1f}")
            content_parts.append(f"分析信心: {conc_data.get('confidence', 0):.1f}")
            content_parts.append(f"核心逻辑: {conc_data.get('reasoning', '暂无')}")
            content_parts.append("")
        
        # 5. 综合结论
        if "comprehensive_conclusion" in structured_analysis:
            conclusion_data = structured_analysis["comprehensive_conclusion"]
            content_parts.append("🎯 **综合结论**")
            
            # 处理不同的数据类型
            if isinstance(conclusion_data, dict):
                content_parts.append(f"总体信号: {conclusion_data.get('overall_signal', '未知')}")
                content_parts.append(f"分析信心: {conclusion_data.get('confidence', 0):.1f}")
                content_parts.append(f"时间周期: {conclusion_data.get('time_horizon', '未知')}")
                
                key_factors = conclusion_data.get('key_factors', [])
                if key_factors:
                    content_parts.append(f"关键因素: {', '.join(key_factors)}")
                
                supporting_evidence = conclusion_data.get('supporting_evidence', '')
                if supporting_evidence:
                    content_parts.append(f"支撑证据: {supporting_evidence}")
                
                risk_factors = conclusion_data.get('risk_factors', [])
                if risk_factors:
                    content_parts.append(f"风险因素: {', '.join(risk_factors)}")
            elif isinstance(conclusion_data, str):
                content_parts.append(f"结论: {conclusion_data}")
            else:
                content_parts.append(f"结论: {str(conclusion_data)}")
            
            content_parts.append("")
        
        # 6. 交易建议
        if "trading_recommendations" in structured_analysis:
            trade_data = structured_analysis["trading_recommendations"]
            content_parts.append("💼 **交易建议**")
            
            # 处理不同的数据类型
            if isinstance(trade_data, dict):
                content_parts.append(f"主要策略: {trade_data.get('primary_strategy', '暂无')}")
                content_parts.append(f"进场时机: {trade_data.get('entry_timing', '暂无')}")
                content_parts.append(f"仓位规模: {trade_data.get('position_sizing', '暂无')}")
                content_parts.append(f"止损设置: {trade_data.get('stop_loss', '暂无')}")
                content_parts.append(f"盈利目标: {trade_data.get('profit_target', '暂无')}")
                content_parts.append(f"风险管理: {trade_data.get('risk_management', '暂无')}")
            elif isinstance(trade_data, str):
                content_parts.append(f"建议: {trade_data}")
            else:
                content_parts.append(f"建议: {str(trade_data)}")
        
        return "\n".join(content_parts)

def analyze_positioning_for_streamlit(symbol: str, analysis_date: str = None, 
                                    use_reasoner: bool = True) -> Dict[str, Any]:
    """
    Streamlit系统调用的持仓分析接口
    
    Args:
        symbol: 品种代码
        analysis_date: 分析日期
        use_reasoner: 是否使用reasoner模型
        
    Returns:
        Dict: 格式化的分析结果
    """
    # 每次调用都创建新的适配器实例，避免状态污染
    adapter = StreamlitEnhancedPositioningAdapter()
    return adapter.analyze_positioning_for_streamlit(symbol, analysis_date, use_reasoner)

# 测试函数
if __name__ == "__main__":
    print("🧪 测试Streamlit增强版持仓分析适配器")
    
    # 测试分析
    test_symbol = "RB"
    print(f"📊 测试分析品种: {test_symbol}")
    
    result = analyze_positioning_for_streamlit(test_symbol, use_reasoner=False)
    
    if result.get("success"):
        print("✅ 测试成功!")
        print(f"📈 品种: {result['symbol_name']}({result['symbol']})")
        print(f"📅 分析日期: {result['analysis_date']}")
        print(f"🤖 使用模型: {result['model_used']}")
        print(f"📊 数据点数: {result['data_points']}")
        print(f"🎯 数据质量: {result['data_quality_score']:.1%}")
        
        if "ai_analysis" in result:
            print(f"🤖 AI分析长度: {len(result['ai_analysis'])} 字符")
        
        if "charts" in result:
            print(f"📊 图表数量: {len(result['charts'])} 个")
        
        if "citations" in result:
            print(f"🔗 外部引用: {len(result['citations'])} 条")
            
    else:
        print(f"❌ 测试失败: {result.get('error', '未知错误')}")
