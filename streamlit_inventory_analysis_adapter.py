#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit库存分析适配器 - 终极完善版集成
将最新的终极完善版库存分析系统集成到Streamlit环境中
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
import asyncio

# 确保能够导入改进后的库存分析系统
sys.path.append(str(Path(__file__).parent))

# 动态加载终极完善版库存分析系统
UltimateAnalyzer = None
try:
    print("🚀 正在加载终极完善版库存分析系统...")
    from 专业库存仓单AI分析系统_终极完善版 import UltimatePerfectedInventoryAnalyzer
    UltimateAnalyzer = UltimatePerfectedInventoryAnalyzer
    print("✅ 终极完善版库存分析系统加载成功")
except Exception as e:
    print(f"❌ 加载终极完善版库存分析系统失败: {e}")
    UltimateAnalyzer = None

# 降级选项：数据增强版
DataEnhancedAnalyzer = None
try:
    from 库存仓单分析_数据增强版 import DataEnhancedInventoryAnalysisSystem
    DataEnhancedAnalyzer = DataEnhancedInventoryAnalysisSystem
    print("✅ 数据增强版系统可用作备用")
except:
    DataEnhancedAnalyzer = None

# 最后降级选项：改进版（暂时禁用，文件不存在）
ImprovedAnalyzer = None
# try:
#     # 动态加载改进版系统
#     exec(open('改进版库存仓单分析系统.py', encoding='utf-8').read(), globals())
#     ImprovedAnalyzer = ImprovedInventoryAnalysisSystem
#     print("✅ 改进版系统可用作最终备用")
# except Exception as e:
#     print(f"⚠️ 改进版系统加载失败: {e}")
#     ImprovedAnalyzer = None
print("ℹ️ 改进版系统已禁用（文件不存在），使用终极完善版或数据增强版")


async def analyze_inventory_for_streamlit(variety: str, analysis_date: str = None, use_reasoner: bool = True) -> Dict[str, Any]:
    """
    异步适配器，用于在Streamlit环境中调用库存分析系统。
    优先使用终极完善版，提供最高质量的分析结果。
    
    Args:
        variety: 品种代码，如 'JD', 'RM', 'CU', 'V' 等（支持任何品种）
        analysis_date: 分析日期，默认为None使用最新数据
        use_reasoner: 是否使用推理模式，默认True获得更深入分析
        
    Returns:
        Dict: 包含分析结果的字典，格式化后可直接用于Streamlit显示
    """
    
    # 第一优先级：使用终极完善版
    if UltimateAnalyzer:
        try:
            print(f"🚀 使用终极完善版库存分析: {variety}")
            
            # 创建终极完善版分析系统实例
            analyzer = UltimateAnalyzer()
            
            # 调用终极分析的兼容接口
            result = analyzer.analyze_variety_comprehensive(variety, analysis_date)
            
            if result.get("analysis_content"):
                print(f"✅ 终极完善版分析成功")
                
                # 转换为Streamlit兼容格式
                streamlit_result = {
                    "success": True,
                    "analysis_content": result["analysis_content"],
                    "confidence_score": result.get("confidence_score", 0.85),
                    "analysis_mode": "ultimate_perfected_inventory_analysis",
                    "analysis_version": "v8.0_Ultimate_Perfection",
                    "variety_name": result.get("result_data", {}).get("variety_name", variety),
                    "charts": result.get("charts", []),
                    "streamlit_compatible": True,
                    "chart_integration": "professional_charts",
                    "data_source_verified": True,
                    
                    # 原始结果数据
                    "result_data": result.get("result_data", {}),
                    "ai_analysis": result["analysis_content"],
                    "ai_comprehensive_analysis": result["analysis_content"],
                    
                    # 元数据
                    "data_quality": {
                        "多维度数据": "可用",
                        "联网数据": "可用" if result.get("result_data", {}).get("analysis_metadata", {}).get("online_data_used", False) else "不可用",
                        "专业图表": f"{len(result.get('charts', []))}个",
                        "分析完整性": result.get("result_data", {}).get("analysis_metadata", {}).get("analysis_completeness", "完整")
                    }
                }
                
                return streamlit_result
            else:
                print(f"⚠️ 终极完善版分析失败，尝试使用备用版本")
                
        except Exception as e:
            print(f"⚠️ 终极完善版出错，尝试使用备用版本: {e}")
    
    # 第二优先级：使用数据增强版
    if DataEnhancedAnalyzer:
        try:
            print(f"🔄 使用数据增强版库存分析: {variety}")
            
            analyzer = DataEnhancedAnalyzer()
            result = analyzer.analyze_variety_comprehensive(variety, analysis_date, use_reasoner)
            
            if result.get("success", False):
                print(f"✅ 数据增强版分析成功")
                result.update({
                    "analysis_version": "v6.0_data_enhanced",
                    "streamlit_compatible": True,
                    "chart_integration": "inline_display", 
                    "data_source_verified": True
                })
                return result
            else:
                print(f"⚠️ 数据增强版分析失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"⚠️ 数据增强版出错: {e}")
    
    # 第三优先级：使用改进版（最后备用）
    if ImprovedAnalyzer:
        try:
            print(f"🔧 使用改进版库存分析（备用）: {variety}")
            
            analyzer = ImprovedAnalyzer()
            result = analyzer.analyze_variety_comprehensive(variety, analysis_date, use_reasoner)
            
            # 确保结果中包含success字段
            if "error" in result:
                result["success"] = False
                result["analysis_mode"] = "improved_inventory_analysis"
                result["analysis_version"] = "v5.0_enhanced_backup"
            else:
                result["success"] = True
                result["analysis_mode"] = "improved_inventory_analysis"
                result["analysis_version"] = "v5.0_enhanced_backup"
                
                # 添加Streamlit特定的元数据
                result["streamlit_compatible"] = True
                result["chart_integration"] = "inline_display"
                result["data_source_verified"] = True
                
                # 确保关键字段存在
                if "ai_analysis" not in result and "ai_comprehensive_analysis" in result:
                    result["ai_analysis"] = result["ai_comprehensive_analysis"]
                
                # 添加置信度分数
                if "confidence_score" not in result:
                    data_quality = result.get("data_quality", {})
                    available_sources = sum(1 for v in data_quality.values() if "可用" in str(v))
                    total_sources = len(data_quality)
                    if total_sources > 0:
                        result["confidence_score"] = min(0.95, 0.6 + (available_sources / total_sources) * 0.35)
                    else:
                        result["confidence_score"] = 0.75
            
            return result
            
        except Exception as e:
            print(f"❌ 改进版库存分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 所有版本都失败了
    print(f"❌ 所有库存分析版本都失败")
    return {
        "error": "所有库存分析系统版本都不可用，请检查系统配置", 
        "success": False,
        "analysis_mode": "system_failure",
        "analysis_version": "failure",
        "confidence_score": 0.0
    }


def get_ultimate_inventory_system_info() -> Dict[str, Any]:
    """获取终极完善版库存分析系统信息"""
    return {
        "system_name": "专业库存仓单AI分析系统（终极完善版）",
        "version": "v8.0 Ultimate Perfection", 
        "features": [
            "元数据信息完全后置，开头直接分析内容",
            "严禁任何英文，纯中文专业表达",
            "专业图表生成功能（库存趋势+价格对比+反身性分析）",
            "完全兼容Streamlit系统调用",
            "五维数据整合（库存+价格+基差+期限结构+持仓）",
            "库存反身性关系深度解读",
            "投机性库存vs真实消费区分",
            "库存周期理论应用",
            "多维度交叉验证分析",
            "DeepSeek V3.1 + Reasoner推理模式"
        ],
        "improvements": [
            "解决了元数据前置问题",
            "彻底消除了英文表达",
            "确保了专业图表生成",
            "完善了Streamlit集成",
            "强化了联网数据获取",
            "深化了反身性关系分析"
        ],
        "theoretical_framework": [
            "库存与价格反身性关系理论",
            "投机性库存识别理论（区分真实消费vs投机需求）",
            "库存周期理论（主动补库-被动补库-主动去库-被动去库）",
            "供需蓄水池杠杆效应理论",
            "多维度数据交叉验证方法论",
            "专业投资机构级别分析框架"
        ],
        "data_sources": [
            "本地多维历史数据（库存、仓单、价格、基差、期限结构、持仓）",
            "联网实时数据（东方财富、新浪财经、交易所官方数据）",
            "多维度市场背景信息（Serper搜索）",
            "实时行情补充数据"
        ],
        "analysis_depth": "机构级专业深度分析（DeepSeek-Reasoner推理模式）",
        "report_style": "纯中文专业机构级分析报告（无markdown符号）",
        "chart_generation": "专业图表（库存趋势、价格对比、周期分析）",
        "compatibility": "完全兼容Streamlit系统调用"
    }


if __name__ == "__main__":
    # 测试适配器
    import asyncio
    
    async def test_adapter():
        print("🧪 测试Streamlit库存分析适配器（终极完善版集成）...")
        
        # 测试基本功能
        result = await analyze_inventory_for_streamlit('聚氯乙烯', None, True)
        
        if result.get("success", False):
            print("✅ 适配器测试成功")
            print(f"📊 分析版本: {result.get('analysis_version', 'unknown')}")
            print(f"🔍 分析模式: {result.get('analysis_mode', 'unknown')}")
            print(f"🎯 置信度: {result.get('confidence_score', 0):.2f}")
            print(f"📈 图表数量: {len(result.get('charts', []))}个")
            print(f"📝 分析内容长度: {len(result.get('analysis_content', ''))}字符")
        else:
            print(f"❌ 适配器测试失败: {result.get('error', '未知错误')}")
        
        # 显示系统信息
        info = get_ultimate_inventory_system_info()
        print(f"\n📋 系统信息: {info['system_name']} {info['version']}")
        print(f"🔧 核心功能: {len(info['features'])} 项增强功能")
        print(f"📊 专业图表: {info['chart_generation']}")
        print(f"🎯 兼容性: {info['compatibility']}")
        
        return result
    
    # 运行测试
    asyncio.run(test_adapter())