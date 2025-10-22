#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit基差分析适配器
将专业AI基差分析系统集成到Streamlit系统中
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from 专业AI基差分析系统_四维度框架 import ProfessionalBasisAnalysisSystem

class StreamlitBasisAnalysisAdapter:
    """Streamlit基差分析适配器"""
    
    def __init__(self):
        self.basis_system = ProfessionalBasisAnalysisSystem()
    
    async def analyze_variety_for_streamlit(self, variety: str, analysis_date: str = None, 
                                          use_reasoner: bool = False) -> Dict[str, Any]:
        """
        为Streamlit系统提供基差分析
        
        Args:
            variety: 品种代码
            analysis_date: 分析日期
            use_reasoner: 是否使用深度推理模式
            
        Returns:
            符合Streamlit系统格式的分析结果
        """
        
        try:
            # 调用专业基差分析系统
            result = self.basis_system.analyze_variety_comprehensive(
                variety=variety, 
                analysis_date=analysis_date, 
                use_reasoner=use_reasoner
            )
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"],
                    "analysis_mode": "basis_analysis",
                    "timestamp": datetime.now().isoformat()
                }
            
            # 转换为Streamlit系统兼容的格式
            streamlit_result = self._convert_to_streamlit_format(result)
            
            return streamlit_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"基差分析失败: {str(e)}",
                "analysis_mode": "basis_analysis",
                "timestamp": datetime.now().isoformat()
            }
    
    def _convert_to_streamlit_format(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """将专业基差分析结果转换为Streamlit系统格式"""
        
        # 提取关键信息
        variety = result.get("variety", "")
        variety_name = result.get("variety_name", "")
        analysis_date = result.get("analysis_date", "")
        ai_analysis = result.get("ai_comprehensive_analysis", "")
        
        # 提取核心指标
        continuous_analysis = result.get("continuous_basis_analysis", {})
        seasonal_analysis = result.get("seasonal_analysis", {})
        inventory_analysis = result.get("inventory_basis_analysis", {})
        
        # 构建Streamlit兼容的结果格式
        streamlit_result = {
            "success": True,
            "analysis_mode": "professional_four_dimension_basis",
            "analysis_version": "v2.0_professional",
            "model_used": result.get("analysis_mode", "deepseek-chat"),
            "search_enhanced": True,
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            
            # 基本信息
            "variety": variety,
            "variety_name": variety_name,
            "chinese_name": variety_name,
            "analysis_date": analysis_date,
            
            # AI分析内容
            "ai_analysis": ai_analysis,
            
            # 数据质量信息
            "data_quality": result.get("data_quality", {}),
            
            # 核心指标摘要
            "metrics": {
                "continuous_basis": continuous_analysis.get("current_continuous_basis"),
                "main_basis": continuous_analysis.get("current_main_basis"),
                "seasonal_deviation": seasonal_analysis.get("seasonal_deviation"),
                "inventory_level": inventory_analysis.get("inventory_level"),
                "region_classification": inventory_analysis.get("region_classification"),
                "data_quality_level": self._assess_overall_data_quality(result.get("data_quality", {}))
            },
            
            # 四维度分析结果
            "four_dimension_analysis": {
                "continuous_basis": continuous_analysis,
                "seasonal_analysis": seasonal_analysis,
                "inventory_analysis": inventory_analysis,
                "spatial_analysis": result.get("spatial_analysis", {}),
                "quality_analysis": result.get("quality_analysis", {})
            },

            # 专业图表 - 转换为主界面期望的格式
            "charts_html": None,  # 占位符，后续处理
            "professional_charts": result.get("professional_charts", {}),  # 保留原始字段以防需要

            # 外部引用
            "external_citations": result.get("external_citations", []),
            "reference_count": len(result.get("external_citations", [])),

            # 市场背景
            "market_context": result.get("market_context", {}),

            # 置信度评估
            "confidence_score": self._calculate_confidence_score(result)
        }

        # 在字典外部处理图表转换
        formatted_result = streamlit_result
        charts_dict = result.get("professional_charts", {})

        # 正确处理图表对象格式
        if charts_dict:
            if len(charts_dict) == 1:
                # 单个图表，直接使用图表对象
                chart_key = list(charts_dict.keys())[0]
                formatted_result["charts_html"] = charts_dict[chart_key]
                print(f"✅ 基差分析图表已转换: 单个图表 '{chart_key}'")
            else:
                # 多个图表，保持字典格式
                formatted_result["charts_html"] = charts_dict
                print(f"✅ 基差分析图表已转换: {len(charts_dict)}个图表")
        else:
            formatted_result["charts_html"] = None

        return streamlit_result
    
    def _assess_overall_data_quality(self, data_quality: Dict[str, str]) -> str:
        """评估整体数据质量"""
        if not data_quality:
            return "未知"
        
        available_count = sum(1 for status in data_quality.values() if status == "可用")
        total_count = len(data_quality)
        
        if total_count == 0:
            return "未知"
        
        quality_ratio = available_count / total_count
        
        if quality_ratio >= 0.8:
            return "优秀"
        elif quality_ratio >= 0.6:
            return "良好"
        elif quality_ratio >= 0.4:
            return "一般"
        else:
            return "较差"
    
    def _calculate_confidence_score(self, result: Dict[str, Any]) -> float:
        """计算分析置信度"""
        try:
            # 基于数据质量和分析完整性计算置信度
            data_quality = result.get("data_quality", {})
            available_count = sum(1 for status in data_quality.values() if status == "可用")
            total_count = len(data_quality) if data_quality else 1
            
            data_quality_score = available_count / total_count
            
            # 基于AI分析长度评估
            ai_analysis = result.get("ai_comprehensive_analysis", "")
            analysis_length_score = min(len(ai_analysis) / 3000, 1.0) if ai_analysis else 0.5
            
            # 基于外部引用数量评估
            citations_count = len(result.get("external_citations", []))
            citation_score = min(citations_count / 10, 1.0)
            
            # 综合评分
            confidence = (data_quality_score * 0.4 + 
                         analysis_length_score * 0.4 + 
                         citation_score * 0.2)
            
            return round(confidence, 2)
            
        except Exception:
            return 0.75  # 默认置信度

# 异步包装函数，供Streamlit系统调用
async def analyze_basis_for_streamlit(variety: str, analysis_date: str = None, 
                                    use_reasoner: bool = False) -> Dict[str, Any]:
    """
    异步基差分析函数，供Streamlit系统调用
    
    Args:
        variety: 品种代码
        analysis_date: 分析日期
        use_reasoner: 是否使用深度推理模式
        
    Returns:
        Streamlit系统兼容的分析结果
    """
    adapter = StreamlitBasisAnalysisAdapter()
    return await adapter.analyze_variety_for_streamlit(variety, analysis_date, use_reasoner)

# 同步版本（如果需要）
def analyze_basis_for_streamlit_sync(variety: str, analysis_date: str = None, 
                                   use_reasoner: bool = False) -> Dict[str, Any]:
    """
    同步基差分析函数
    """
    adapter = StreamlitBasisAnalysisAdapter()
    # 在同步环境中运行异步函数
    return asyncio.run(adapter.analyze_variety_for_streamlit(variety, analysis_date, use_reasoner))

if __name__ == "__main__":
    # 测试适配器
    print("🧪 测试Streamlit基差分析适配器...")
    
    # 测试同步版本
    result = analyze_basis_for_streamlit_sync("JD", use_reasoner=False)
    
    if result.get("success"):
        print("✅ 适配器测试成功")
        print(f"📊 品种: {result.get('variety_name')}")
        print(f"🎯 置信度: {result.get('confidence_score')}")
        print(f"📈 数据质量: {result.get('metrics', {}).get('data_quality_level')}")
    else:
        print(f"❌ 适配器测试失败: {result.get('error')}")
