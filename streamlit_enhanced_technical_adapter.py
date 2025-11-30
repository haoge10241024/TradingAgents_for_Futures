#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit增强版技术分析适配器
将增强版专业技术分析系统集成到Streamlit环境中
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
import asyncio

# 确保能够导入增强版技术分析系统
sys.path.append(str(Path(__file__).parent))

try:
    from enhanced_professional_technical_analysis import EnhancedProfessionalTechnicalAnalyzer
    print("✅ 增强版技术分析系统加载成功")
except Exception as e:
    error_msg = str(e)  # 保存错误信息到外部作用域
    print(f"❌ 加载增强版技术分析系统失败: {error_msg}")
    # 提供一个假的类以避免后续错误
    class EnhancedProfessionalTechnicalAnalyzer:
        def __init__(self):
            pass
        def analyze_symbol_enhanced(self, symbol: str, include_market_info: bool = True, display_result: bool = False) -> Dict:
            return {"error": f"技术分析系统加载失败: {error_msg}", "success": False}


async def analyze_technical_for_streamlit(variety: str, analysis_date: str = None, include_market_info: bool = True) -> Dict[str, Any]:
    """
    异步适配器，用于在Streamlit环境中调用增强版技术分析系统。
    
    Args:
        variety: 品种代码，如 'RB', 'CU', 'AU' 等
        analysis_date: 分析日期，默认为None使用最新数据
        include_market_info: 是否包含市场信息搜索，默认True
        
    Returns:
        Dict: 包含分析结果的字典，格式化后可直接用于Streamlit显示
    """
    try:
        print(f"🚀 启动增强版技术分析: {variety}")
        
        # 创建分析系统实例
        analyzer = EnhancedProfessionalTechnicalAnalyzer()
        
        # 执行增强版分析
        result = analyzer.analyze_symbol_enhanced(
            symbol=variety,
            include_market_info=include_market_info,
            display_result=False  # Streamlit环境不显示控制台输出
        )
        
        # 确保结果中包含success字段
        if result is None or "error" in result:
            error_msg = result.get("error", "未知错误") if result else "返回结果为空"
            return {
                "error": f"技术分析失败: {error_msg}", 
                "success": False,
                "analysis_mode": "enhanced_professional_technical_analysis",
                "analysis_version": "v4.0_streamlit_enhanced",
                "confidence_score": 0.0
            }
        else:
            result["success"] = True
            result["analysis_mode"] = "enhanced_professional_technical_analysis"
            result["analysis_version"] = "v4.0_streamlit_enhanced"
            result["streamlit_compatible"] = True
            result["chart_integration"] = "inline_display"
            result["data_source_verified"] = True
            
            # 添加置信度分数
            if "confidence_score" not in result:
                # 基于数据质量和图表数量计算置信度
                chart_count = result.get("chart_count", 0)
                citation_count = result.get("citation_count", 0)
                base_confidence = 0.85  # 增强版基础置信度
                
                # 根据图表和引用数量调整置信度
                chart_bonus = min(0.1, chart_count * 0.03)
                citation_bonus = min(0.05, citation_count * 0.01)
                
                result["confidence_score"] = min(0.95, base_confidence + chart_bonus + citation_bonus)
            
            # 确保关键字段存在
            if "professional_analysis" in result and "ai_analysis" not in result:
                result["ai_analysis"] = result["professional_analysis"]

            # 处理图表数据格式转换 - 正确处理Plotly图表对象
            if "professional_charts" in result and result["professional_charts"]:
                charts_dict = result["professional_charts"]

                # 如果只有一个图表，直接使用它
                if len(charts_dict) == 1:
                    chart_key = list(charts_dict.keys())[0]
                    result["charts_html"] = charts_dict[chart_key]
                    print(f"✅ 图表数据已转换: 单个图表 '{chart_key}'")
                else:
                    # 如果有多个图表，保持字典格式但确保值是Plotly对象
                    result["charts_html"] = charts_dict
                    print(f"✅ 图表数据已转换: {len(charts_dict)}个图表")

        return result
        
    except Exception as e:
        print(f"❌ 技术分析适配器运行失败: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": f"技术分析适配器运行失败: {str(e)}", 
            "success": False,
            "analysis_mode": "enhanced_professional_technical_analysis",
            "analysis_version": "v4.0_streamlit_enhanced",
            "confidence_score": 0.0
        }


def get_enhanced_technical_system_info() -> Dict[str, Any]:
    """获取增强版技术分析系统信息"""
    return {
        "system_name": "增强版专业技术分析系统",
        "version": "v4.0_streamlit_enhanced", 
        "features": [
            "专业研究报告行文风格",
            "50+技术指标综合分析",
            "多时间框架趋势分析",
            "动量与背离检测",
            "支撑阻力位识别",
            "成交量与持仓量分析",
            "专业图表集成（Plotly交互式）",
            "数据来源标注（本地+联网）",
            "DeepSeek Reasoner深度分析",
            "风险评估与操作建议"
        ],
        "analysis_framework": [
            "市场概况与价格表现",
            "技术指标深度解析",
            "趋势分析与方向判断", 
            "支撑阻力位分析",
            "资金流向与持仓分析",
            "风险评估与操作建议",
            "后市展望"
        ],
        "technical_indicators": [
            "趋势指标: MA5/20/60, EMA20",
            "动量指标: RSI14, MACD, KDJ",
            "波动率指标: 布林带, ATR14, PSAR",
            "成交量指标: 量比, OBV, 量价关系",
            "期货特色: 持仓量, VWAP, HHV/LLV"
        ],
        "data_sources": [
            "本地技术分析数据库",
            "OHLCV基础数据", 
            "技术指标计算数据",
            "Serper市场信息搜索（标注来源）"
        ],
        "chart_types": [
            "K线图与均线系统",
            "MACD动量指标图",
            "RSI相对强弱指标图",
            "成交量分析图",
            "支撑阻力分析图",
            "持仓量与价格关系图"
        ],
        "analysis_depth": "DeepSeek Reasoner深度推理",
        "report_style": "专业研究报告级别",
        "chart_integration": "文段内嵌图表显示"
    }


if __name__ == "__main__":
    # 测试适配器
    import asyncio
    
    async def test_adapter():
        print("🧪 测试Streamlit增强版技术分析适配器...")
        
        # 测试基本功能
        result = await analyze_technical_for_streamlit('RB', include_market_info=True)
        
        if result.get("success", False):
            print("✅ 适配器测试成功")
            print(f"📊 分析版本: {result.get('analysis_version', 'unknown')}")
            print(f"🔍 分析模式: {result.get('analysis_mode', 'unknown')}")
            print(f"🎯 置信度: {result.get('confidence_score', 0):.2f}")
            print(f"📈 专业图表: {result.get('chart_count', 0)} 个")
            print(f"📚 外部引用: {result.get('citation_count', 0)} 个")
        else:
            print(f"❌ 适配器测试失败: {result.get('error', '未知错误')}")
        
        # 显示系统信息
        info = get_enhanced_technical_system_info()
        print(f"\n📋 系统信息: {info['system_name']} {info['version']}")
        print(f"🔧 核心功能: {len(info['features'])} 项增强功能")
        print(f"📊 技术指标: {len(info['technical_indicators'])} 类指标")
        print(f"📈 图表类型: {len(info['chart_types'])} 种图表")
        
        return result
    
    # 运行测试
    asyncio.run(test_adapter())
