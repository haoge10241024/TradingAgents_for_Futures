#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持仓席位分析 - 真实数据适配器
将基于真实数据的持仓席位分析系统适配到Streamlit界面
严肃专业，无emoji，基于本地数据库
"""

from 持仓席位分析_真实数据完整版 import RealDataPositioningSystem, _get_symbol_name
import traceback
from typing import Dict, Any

def analyze_real_positioning_for_streamlit(symbol: str) -> Dict[str, Any]:
    """
    基于真实数据的持仓席位分析 - Streamlit适配版本
    
    Args:
        symbol: 品种代码 (如 'AG', 'CU', 'RB' 等)
    
    Returns:
        包含分析结果的字典
    """
    
    print(f"基于真实数据的持仓席位分析系统启动: {symbol}")
    print("使用本地数据库真实持仓席位数据进行分析")
    
    try:
        # 初始化真实数据分析系统
        system = RealDataPositioningSystem()
        
        # 执行综合分析
        strategy_results = system.analyze_comprehensive_positioning(symbol)
        
        if not strategy_results:
            return {
                'success': False,
                'error': f'未能获取品种 {symbol} 的持仓席位数据',
                'ai_analysis': '暂无分析数据',
                'charts_html': {},
                'professional_charts': {},
                'strategy_results': {}
            }
        
        print(f"成功分析 {len(strategy_results)} 个策略")
        
        # 生成专业分析报告
        ai_analysis = system.generate_serious_analysis_report(strategy_results, symbol)
        
        # 生成图表
        charts = {}
        professional_charts = {}
        
        # 价格走势图
        try:
            price_chart = system.create_price_chart(symbol)
            charts['price_trend'] = price_chart
            professional_charts['price_trend'] = price_chart
            print(f"成功生成价格走势图")
        except Exception as e:
            print(f"生成价格图表失败: {e}")
            charts['price_trend'] = None
            professional_charts['price_trend'] = None
        
        # 策略分析图表
        for result in strategy_results:
            try:
                strategy_chart = system.create_strategy_chart(result, symbol)
                chart_key = result.strategy_code
                charts[chart_key] = strategy_chart
                professional_charts[chart_key] = strategy_chart
                print(f"成功生成 {result.strategy_name} 图表")
            except Exception as e:
                print(f"生成 {result.strategy_name} 图表失败: {e}")
                charts[chart_key] = None
                professional_charts[chart_key] = None
        
        # 格式化策略结果
        strategy_results_dict = {}
        for result in strategy_results:
            strategy_results_dict[result.strategy_code] = {
                'strategy_name': result.strategy_name,
                'net_direction': result.net_direction.value,
                'bullish_power': result.bullish_power,
                'bearish_power': result.bearish_power,
                'power_difference': result.power_difference,
                'signal_strength': result.signal_strength,
                'confidence_level': result.confidence_level,
                'key_indicators': result.key_indicators,
                'supporting_evidence': result.supporting_evidence,
                'strategy_theory': result.strategy_theory,
                'calculation_method': result.calculation_method,
                'usage_guidance': result.usage_guidance,
                'risk_warnings': result.risk_warnings
            }
        
        # 构建返回结果
        result_dict = {
            'success': True,
            'symbol': symbol,
            'symbol_name': _get_symbol_name(symbol),
            'analysis_time': '基于真实持仓席位数据',
            'ai_analysis': ai_analysis,
            'analysis_content': ai_analysis,  # 兼容性字段
            'comprehensive_analysis': ai_analysis,  # 兼容性字段
            'charts_html': {},  # Streamlit使用plotly对象，不需要HTML
            'professional_charts': professional_charts,
            'charts': charts,  # 兼容性字段
            'price_and_strategy_charts': professional_charts,  # 兼容性字段
            'strategy_results': strategy_results_dict,
            'analysis_summary': {
                'total_strategies': len(strategy_results),
                'bullish_signals': len([r for r in strategy_results if r.power_difference > 0.1]),
                'bearish_signals': len([r for r in strategy_results if r.power_difference < -0.1]),
                'neutral_signals': len([r for r in strategy_results if abs(r.power_difference) <= 0.1]),
                'avg_confidence': sum([r.confidence_level for r in strategy_results]) / len(strategy_results) if strategy_results else 0
            }
        }
        
        print(f"真实数据持仓席位分析完成: {symbol}")
        return result_dict
        
    except FileNotFoundError as e:
        error_msg = f"数据文件未找到: {str(e)}"
        print(f"错误: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'ai_analysis': f'无法获取{_get_symbol_name(symbol)}的持仓席位数据，请检查数据文件是否存在。',
            'charts_html': {},
            'professional_charts': {},
            'strategy_results': {}
        }
        
    except Exception as e:
        error_msg = f"分析过程中出现错误: {str(e)}"
        print(f"错误: {error_msg}")
        print(f"错误详情: {traceback.format_exc()}")
        return {
            'success': False,
            'error': error_msg,
            'ai_analysis': f'分析{_get_symbol_name(symbol)}持仓席位时出现技术问题，请稍后重试。',
            'charts_html': {},
            'professional_charts': {},
            'strategy_results': {}
        }

def get_available_symbols() -> list:
    """获取可用的品种列表"""
    import os
    
    positioning_path = "qihuo/database/positioning"
    
    if not os.path.exists(positioning_path):
        return []
    
    symbols = []
    for item in os.listdir(positioning_path):
        item_path = os.path.join(positioning_path, item)
        if os.path.isdir(item_path):
            # 检查是否有必要的数据文件
            required_files = ['positioning_summary.json', 'long_position_ranking.csv', 'short_position_ranking.csv']
            if all(os.path.exists(os.path.join(item_path, f)) for f in required_files):
                symbols.append(item)
    
    return sorted(symbols)

# 测试函数
def test_real_data_adapter():
    """测试真实数据适配器"""
    
    print("测试真实数据持仓席位分析适配器")
    print("=" * 60)
    
    # 获取可用品种
    symbols = get_available_symbols()
    print(f"可用品种: {symbols[:5]}...")  # 只显示前5个
    
    if symbols:
        # 测试第一个品种
        test_symbol = symbols[0]
        print(f"\n测试品种: {test_symbol}")
        
        result = analyze_real_positioning_for_streamlit(test_symbol)
        
        print(f"分析结果:")
        print(f"  成功: {result['success']}")
        if result['success']:
            print(f"  品种: {result['symbol_name']}")
            print(f"  策略数量: {result['analysis_summary']['total_strategies']}")
            print(f"  看多信号: {result['analysis_summary']['bullish_signals']}")
            print(f"  看空信号: {result['analysis_summary']['bearish_signals']}")
            print(f"  平均置信度: {result['analysis_summary']['avg_confidence']:.1f}%")
            print(f"  报告长度: {len(result['ai_analysis'])} 字符")
            print(f"  图表数量: {len([k for k, v in result['professional_charts'].items() if v is not None])}")
        else:
            print(f"  错误: {result.get('error', '未知错误')}")
    else:
        print("未找到可用的品种数据")

if __name__ == "__main__":
    test_real_data_adapter()
