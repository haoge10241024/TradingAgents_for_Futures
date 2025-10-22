#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit改进版持仓分析适配器
将独立持仓分析系统_Jupyter版.py集成到Streamlit系统中
支持四个完整策略：蜘蛛网、聪明钱、家人席位反向操作、持仓集中度
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
import concurrent.futures
from datetime import datetime

# 添加项目根目录到路径
try:
    project_root = Path(__file__).parent
except NameError:
    project_root = Path.cwd()

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入改进版持仓分析系统
try:
    from 独立持仓分析系统_Jupyter版 import JupyterPositioningAnalyzer, SYMBOL_NAMES
except ImportError as e:
    print(f"导入错误: {e}")
    # 备用导入
    class JupyterPositioningAnalyzer:
        def __init__(self):
            pass
        def analyze_symbol_sync(self, symbol, use_reasoner=False, days_back=14):
            return {"success": False, "error": "导入失败"}
    SYMBOL_NAMES = {}

class StreamlitImprovedPositioningAdapter:
    """Streamlit改进版持仓分析适配器"""
    
    def __init__(self):
        """初始化适配器"""
        try:
            self.analyzer = JupyterPositioningAnalyzer()
            self.initialized = True
            print("✅ 改进版持仓分析适配器初始化成功")
        except Exception as e:
            print(f"❌ 适配器初始化失败: {e}")
            self.analyzer = None
            self.initialized = False
    
    def analyze_positioning_for_streamlit(self, symbol: str, analysis_date: str = None, 
                                        use_reasoner: bool = False, days_back: int = 14) -> Dict[str, Any]:
        """
        为Streamlit系统提供改进版持仓分析
        
        Args:
            symbol: 品种代码
            analysis_date: 分析日期（暂时不使用，系统自动选择最新数据）
            use_reasoner: 是否使用reasoner模型
            days_back: 分析天数
            
        Returns:
            Dict: 分析结果，兼容Streamlit显示格式
        """
        if not self.initialized or self.analyzer is None:
            return {
                "success": False,
                "error": "持仓分析系统未正确初始化",
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol.upper(), symbol)
            }
        
        try:
            print(f"🔍 开始分析 {symbol}...")
            
            # 使用同步方法进行分析（避免Streamlit中的asyncio冲突）
            result = self.analyzer.analyze_symbol_sync(
                symbol=symbol.upper(),
                use_reasoner=use_reasoner,
                days_back=days_back
            )
            
            if result.get("success"):
                print(f"✅ {symbol} 分析成功")
                return self._format_for_streamlit(result)
            else:
                print(f"❌ {symbol} 分析失败: {result.get('error', '未知错误')}")
                return {
                    "success": False,
                    "error": result.get("error", "分析失败"),
                    "symbol": symbol,
                    "symbol_name": SYMBOL_NAMES.get(symbol.upper(), symbol)
                }
                
        except Exception as e:
            print(f"❌ 持仓分析异常: {e}")
            return {
                "success": False,
                "error": f"持仓分析过程中发生错误: {str(e)}",
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol.upper(), symbol)
            }
    
    def _format_for_streamlit(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化结果以适配Streamlit显示"""
        
        # 基础信息
        formatted_result = {
            "success": True,
            "symbol": result.get("symbol", ""),
            "symbol_name": result.get("symbol_name", ""),
            "analysis_date": result.get("analysis_date", ""),
            "model_used": result.get("model_used", ""),
            "data_points": result.get("data_points", 0),
            "data_quality_score": result.get("data_quality_score", 0.0)
        }
        
        # AI分析结果
        if "ai_analysis" in result:
            formatted_result["ai_analysis"] = result["ai_analysis"]
        
        # 四个策略的详细数据
        supporting_data = {}
        
        # 1. 蜘蛛网策略数据
        if "spider_web_data" in result:
            spider_data = result["spider_web_data"]
            supporting_data["spider_web_analysis"] = {
                "strategy_name": "蜘蛛网策略",
                "dB": spider_data.get("dB", 0),
                "dS": spider_data.get("dS", 0),
                "signal_strength": spider_data.get("signal_strength", 0),
                "long_total": spider_data.get("long_total_latest", 0),
                "short_total": spider_data.get("short_total_latest", 0),
                "description": "基于前20名多空持仓变化分析聪明资金流向"
            }
        
        # 2. 聪明钱分析数据
        if "smart_money_data" in result:
            smart_data = result["smart_money_data"]
            supporting_data["smart_money_analysis"] = {
                "strategy_name": "聪明钱分析",
                "oi_volume_ratio": smart_data.get("oi_volume_ratio", 0),
                "position_efficiency": smart_data.get("position_efficiency", 0),
                "smart_money_score": smart_data.get("smart_money_score", 0),
                "normalized_score": smart_data.get("normalized_score", 0),
                "description": "通过持仓成交比和持仓效率识别知情资金"
            }
        
        # 3. 家人席位反向操作策略数据
        if "seat_behavior_data" in result:
            seat_data = result["seat_behavior_data"]
            supporting_data["retail_reverse_analysis"] = {
                "strategy_name": "家人席位反向操作策略",
                "retail_long_change": seat_data.get("retail_long_change", 0),
                "retail_short_change": seat_data.get("retail_short_change", 0),
                "retail_long_position": seat_data.get("retail_long_position", 0),
                "retail_short_position": seat_data.get("retail_short_position", 0),
                "retail_long_ratio": seat_data.get("retail_long_ratio", 0),
                "retail_short_ratio": seat_data.get("retail_short_ratio", 0),
                "reverse_signal": seat_data.get("reverse_signal", "未知"),
                "reverse_direction": seat_data.get("reverse_direction", "中性"),
                "signal_strength": seat_data.get("signal_strength", 0),
                "retail_seats_found": seat_data.get("retail_seats_found", 0),
                "retail_seat_details": seat_data.get("retail_seat_details", []),
                "description": "分析家人席位（东财、徽商、平安）行为，提供反向操作建议"
            }
        
        # 4. 持仓集中度分析数据
        if "concentration_data" in result:
            conc_data = result["concentration_data"]
            supporting_data["concentration_analysis"] = {
                "strategy_name": "持仓集中度分析",
                "long_concentration_hhi": conc_data.get("long_concentration_hhi", 0),
                "short_concentration_hhi": conc_data.get("short_concentration_hhi", 0),
                "top5_long_ratio": conc_data.get("top5_long_ratio", 0),
                "top5_short_ratio": conc_data.get("top5_short_ratio", 0),
                "top10_long_ratio": conc_data.get("top10_long_ratio", 0),
                "top10_short_ratio": conc_data.get("top10_short_ratio", 0),
                "concentration_risk": conc_data.get("concentration_risk", "未知"),
                "control_assessment": conc_data.get("control_assessment", "未知"),
                "avg_concentration": conc_data.get("avg_concentration", 0),
                "description": "使用HHI指数评估大户控盘程度和市场操纵风险"
            }
        
        # 5. 持仓统计数据
        if "position_data" in result:
            pos_data = result["position_data"]
            supporting_data["position_statistics"] = {
                "long_top20_total": pos_data.get("long_top20_total", 0),
                "short_top20_total": pos_data.get("short_top20_total", 0),
                "net_position": pos_data.get("net_position", 0),
                "long_short_ratio": pos_data.get("long_short_ratio", 0)
            }
        
        formatted_result["supporting_data"] = supporting_data
        
        # 市场情报
        if "market_intelligence" in result:
            formatted_result["citations"] = [
                {
                    "index": i+1,
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "snippet": item.get("snippet", "")
                }
                for i, item in enumerate(result["market_intelligence"])
            ]
        
        # 原始数据（用于调试）
        if "raw_data" in result:
            formatted_result["raw_analysis_data"] = result["raw_data"]
        
        # 生成结构化分析摘要
        formatted_result["structured_analysis"] = self._generate_structured_summary(supporting_data)
        
        return formatted_result
    
    def _generate_structured_summary(self, supporting_data: Dict) -> Dict:
        """生成结构化分析摘要"""
        summary = {}
        
        # 蜘蛛网策略摘要
        if "spider_web_analysis" in supporting_data:
            spider = supporting_data["spider_web_analysis"]
            dB = spider.get("dB", 0)
            dS = spider.get("dS", 0)
            
            if dB > 0 and dS < 0:
                spider_signal = "看多"
            elif dB < 0 and dS > 0:
                spider_signal = "看空"
            else:
                spider_signal = "中性"
            
            summary["spider_web_summary"] = {
                "signal": spider_signal,
                "strength": abs(dB) + abs(dS),
                "confidence": min(abs(dB + dS) / 10000, 1.0)
            }
        
        # 聪明钱分析摘要
        if "smart_money_analysis" in supporting_data:
            smart = supporting_data["smart_money_analysis"]
            score = smart.get("normalized_score", 0)
            
            if score > 70:
                smart_signal = "强烈看好"
            elif score > 50:
                smart_signal = "温和看好"
            else:
                smart_signal = "中性"
            
            summary["smart_money_summary"] = {
                "signal": smart_signal,
                "score": score,
                "confidence": score / 100.0
            }
        
        # 家人席位反向操作摘要
        if "retail_reverse_analysis" in supporting_data:
            retail = supporting_data["retail_reverse_analysis"]
            direction = retail.get("reverse_direction", "中性")
            strength = retail.get("signal_strength", 0)
            
            summary["retail_reverse_summary"] = {
                "signal": direction,
                "strength": strength,
                "confidence": min(strength / 5000, 1.0),
                "seats_found": retail.get("retail_seats_found", 0)
            }
        
        # 持仓集中度摘要
        if "concentration_analysis" in supporting_data:
            conc = supporting_data["concentration_analysis"]
            risk = conc.get("concentration_risk", "未知")
            control = conc.get("control_assessment", "未知")
            
            summary["concentration_summary"] = {
                "risk_level": risk,
                "control_level": control,
                "avg_hhi": conc.get("avg_concentration", 0)
            }
        
        return summary

# 创建全局适配器实例
_improved_adapter = None

def get_improved_positioning_adapter():
    """获取改进版持仓分析适配器实例"""
    global _improved_adapter
    if _improved_adapter is None:
        _improved_adapter = StreamlitImprovedPositioningAdapter()
    return _improved_adapter

def analyze_improved_positioning_for_streamlit(symbol: str, analysis_date: str = None, 
                                             use_reasoner: bool = False, days_back: int = 14) -> Dict[str, Any]:
    """
    Streamlit系统调用的改进版持仓分析接口
    
    Args:
        symbol: 品种代码
        analysis_date: 分析日期
        use_reasoner: 是否使用reasoner模型
        days_back: 分析天数
        
    Returns:
        Dict: 格式化的分析结果
    """
    adapter = get_improved_positioning_adapter()
    return adapter.analyze_positioning_for_streamlit(symbol, analysis_date, use_reasoner, days_back)

# 测试函数
if __name__ == "__main__":
    print("🧪 测试Streamlit改进版持仓分析适配器")
    print("=" * 60)
    
    # 测试分析
    test_symbol = "RB"
    print(f"📊 测试分析品种: {test_symbol}")
    
    result = analyze_improved_positioning_for_streamlit(test_symbol, use_reasoner=False, days_back=14)
    
    if result.get("success"):
        print("✅ 测试成功!")
        print(f"📈 品种: {result['symbol_name']}({result['symbol']})")
        print(f"📅 分析日期: {result['analysis_date']}")
        print(f"🤖 使用模型: {result['model_used']}")
        print(f"📊 数据点数: {result['data_points']}")
        print(f"🎯 数据质量: {result['data_quality_score']:.1%}")
        
        # 检查四个策略数据
        supporting_data = result.get("supporting_data", {})
        print(f"\n📊 四个策略数据检查:")
        
        strategies = [
            ("spider_web_analysis", "🕸️ 蜘蛛网策略"),
            ("smart_money_analysis", "🧠 聪明钱分析"),
            ("retail_reverse_analysis", "🏛️ 家人席位反向操作"),
            ("concentration_analysis", "📊 持仓集中度分析")
        ]
        
        for key, name in strategies:
            if key in supporting_data:
                print(f"✅ {name}: 数据完整")
                if key == "retail_reverse_analysis":
                    retail_data = supporting_data[key]
                    print(f"   反向信号: {retail_data.get('reverse_direction', '未知')}")
                    print(f"   发现席位: {retail_data.get('retail_seats_found', 0)}个")
            else:
                print(f"❌ {name}: 数据缺失")
        
        if "ai_analysis" in result:
            ai_length = len(result['ai_analysis'])
            print(f"\n🤖 AI分析: {ai_length} 字符")
            if ai_length > 0:
                print("✅ AI分析包含具体席位数据")
        
        if "citations" in result:
            print(f"🔗 外部引用: {len(result['citations'])} 条")
            
    else:
        print(f"❌ 测试失败: {result.get('error', '未知错误')}")
    
    print("\n🎉 测试完成!")
