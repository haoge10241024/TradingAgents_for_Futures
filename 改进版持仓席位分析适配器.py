#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版持仓席位分析适配器
现在使用基于真实数据的分析系统
严肃专业，无emoji，基于本地数据库
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime
import traceback

# 添加项目根目录到路径
try:
    project_root = Path(__file__).parent
except NameError:
    project_root = Path.cwd()

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def analyze_improved_positioning_for_streamlit(symbol: str, analysis_date: str = None, 
                                                   use_reasoner: bool = True) -> Dict[str, Any]:
    """
    改进版持仓席位分析适配器 - 基于真实数据
    使用本地数据库的真实持仓席位数据进行分析
    严肃专业，无emoji，基于实际数据
    
    Args:
        symbol: 品种代码，如 'CU', 'RB', 'I' 等
        analysis_date: 分析日期，默认为None使用最新数据
        use_reasoner: 是否使用推理模式，默认True获得更深入分析
        
    Returns:
        Dict: 包含完整分析结果的字典
    """
    
    print(f"启动改进版持仓席位分析: {symbol}")
    print("使用基于真实数据的分析系统")
    
    try:
        # 优先使用真实数据分析系统
        try:
            from 持仓席位分析_真实数据适配器 import analyze_real_positioning_for_streamlit
            print("使用基于真实数据的持仓席位分析系统")
            result = analyze_real_positioning_for_streamlit(symbol)
            
            if result.get('success', False):
                print(f"基于真实数据的持仓席位分析完成")
                return result
            else:
                print(f"真实数据分析失败: {result.get('error', '未知错误')}")
                return result
                
        except ImportError as e:
            print(f"真实数据系统不可用: {e}")
            error_msg = "真实数据分析系统不可用，请检查系统配置"
            return {
                "success": False,
                "error": error_msg,
                "analysis_content": f"分析{symbol}持仓席位时系统不可用，请检查配置。",
                "ai_analysis": f"分析{symbol}持仓席位时系统不可用，请检查配置。",
                "charts": {},
                "professional_charts": {},
                "strategy_results": {}
            }
        except Exception as e:
            print(f"真实数据分析出错: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            error_msg = f"真实数据分析出错: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "analysis_content": f"分析{symbol}持仓席位时出现技术问题: {str(e)}",
                "ai_analysis": f"分析{symbol}持仓席位时出现技术问题，请稍后重试。",
                "charts": {},
                "professional_charts": {},
                "strategy_results": {}
            }
        
    except Exception as e:
        error_msg = f"持仓席位分析过程中出现错误: {str(e)}"
        print(f"错误: {error_msg}")
        print(f"错误详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": error_msg,
            "analysis_content": f"分析{symbol}持仓席位时出现技术问题，请稍后重试。",
            "ai_analysis": f"分析{symbol}持仓席位时出现技术问题，请稍后重试。",
            "charts": {},
            "professional_charts": {},
            "strategy_results": {}
        }

def _format_multi_force_strategies_for_streamlit(strategy_results: Dict) -> Dict:
    """格式化多空力量策略结果以便Streamlit显示"""
    formatted = {}
    
    for strategy_code, result in strategy_results.items():
        try:
            formatted[strategy_code] = {
                "strategy_name": result.get('strategy_name', strategy_code),
                "net_direction": result.get('net_direction', '中性'),
                "bullish_power": result.get('bullish_power', 0),
                "bearish_power": result.get('bearish_power', 0),
                "power_difference": result.get('power_difference', 0),
                "signal_strength": result.get('signal_strength', 0),
                "confidence_level": result.get('confidence_level', 50),
                "key_indicators": result.get('key_indicators', {}),
                "supporting_evidence": result.get('supporting_evidence', {}),
                "strategy_theory": result.get('strategy_theory', ''),
                "calculation_method": result.get('calculation_method', ''),
                "usage_guidance": result.get('usage_guidance', ''),
                "risk_warnings": result.get('risk_warnings', '')
            }
        except Exception as e:
            print(f"格式化策略 {strategy_code} 时出错: {e}")
            formatted[strategy_code] = {
                "strategy_name": strategy_code,
                "net_direction": "未知",
                "bullish_power": 0,
                "bearish_power": 0,
                "power_difference": 0,
                "signal_strength": 0,
                "confidence_level": 0
            }
    
    return formatted

# 测试函数
def test_improved_adapter():
    """测试改进版适配器"""
    
    print("测试改进版持仓席位分析适配器")
    print("=" * 60)
    
    # 测试AG
    result = analyze_improved_positioning_for_streamlit("AG")
    
    print(f"分析结果:")
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  品种: {result.get('symbol_name', 'N/A')}")
        print(f"  策略数量: {result.get('analysis_summary', {}).get('total_strategies', 0)}")
        print(f"  报告长度: {len(result.get('ai_analysis', ''))} 字符")
        print(f"  图表数量: {len([k for k, v in result.get('professional_charts', {}).items() if v is not None])}")
    else:
        print(f"  错误: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    test_improved_adapter()