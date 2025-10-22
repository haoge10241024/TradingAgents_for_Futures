#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit改进版新闻分析适配器
将改进版新闻分析系统集成到Streamlit系统中
支持专业分析报告，新闻链接标注，无Markdown符号
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
import concurrent.futures
from datetime import datetime
import os

# 添加项目根目录到路径
try:
    project_root = Path(__file__).parent
except NameError:
    project_root = Path.cwd()

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入专业报告版新闻分析系统
try:
    from 期货新闻AI分析系统_专业报告版 import ProfessionalFuturesNewsAnalyzer
    from 期货新闻AI分析系统_专业报告版 import install_and_import
except ImportError as e:
    print(f"导入错误: {e}")
    # 备用导入
    class ProfessionalFuturesNewsAnalyzer:
        def __init__(self, deepseek_api_key=None):
            pass
        def comprehensive_news_search(self, commodity, target_date, days_back):
            return []
        def analyze_comprehensive_news_professional(self, akshare_df, search_news, news_citations, commodity, target_date):
            return "导入失败", []
    def install_and_import():
        import pandas as pd
        return None, pd, None, None, None, None

class StreamlitImprovedNewsAdapter:
    """Streamlit改进版新闻分析适配器"""
    
    def __init__(self, deepseek_api_key: str = None):
        """初始化适配器"""
        try:
            # 使用默认API密钥如果未提供
            api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY', 'sk-default-key')
            self.analyzer = ProfessionalFuturesNewsAnalyzer(api_key)
            self.initialized = True
            print("✅ 专业报告版新闻分析适配器初始化成功")
        except Exception as e:
            print(f"❌ 适配器初始化失败: {e}")
            self.analyzer = None
            self.initialized = False
    
    def analyze_news_for_streamlit(self, commodity: str, analysis_date: str = None, 
                                 days_back: int = 7) -> Dict[str, Any]:
        """
        为Streamlit系统提供改进版新闻分析
        
        Args:
            commodity: 品种名称（中文）
            analysis_date: 分析日期
            days_back: 搜索天数
            
        Returns:
            Dict: 分析结果，兼容Streamlit显示格式
        """
        if not self.initialized or self.analyzer is None:
            return {
                "success": False,
                "error": "新闻分析系统未正确初始化",
                "commodity": commodity
            }
        
        try:
            print(f"🔍 开始分析{commodity}新闻...")
            
            # 导入必要库
            ak, pd, requests, BeautifulSoup, feedparser, date_parser = install_and_import()
            
            # 解析分析日期
            if analysis_date:
                try:
                    if isinstance(analysis_date, str):
                        if len(analysis_date) == 8 and analysis_date.isdigit():
                            target_date = datetime.strptime(analysis_date, "%Y%m%d").date()
                        else:
                            target_date = datetime.strptime(analysis_date, "%Y-%m-%d").date()
                    else:
                        target_date = analysis_date
                except:
                    target_date = datetime.now().date()
            else:
                target_date = datetime.now().date()
            
            # 1. 获取akshare数据
            akshare_news, akshare_total, akshare_citations = self.analyzer.get_akshare_news(
                commodity, target_date, days_back, ak
            )
            
            # 2. 综合搜索新闻
            search_news = self.analyzer.comprehensive_news_search(commodity, target_date, days_back)
            
            # 合并所有引用
            all_citations = akshare_citations.copy()
            for news in search_news:
                citation = {
                    'title': news['title'],
                    'source': news['source'],
                    'date': news['date'],
                    'url': news['url'],
                    'type': news.get('type', 'search')
                }
                all_citations.append(citation)
            
            total_news = len(akshare_news) + len(search_news) if not akshare_news.empty else len(search_news)
            
            if total_news == 0:
                return {
                    "success": False,
                    "error": f"未找到{commodity}相关新闻",
                    "commodity": commodity,
                    "news_count": 0
                }
            
            # 3. 生成专业分析
            analysis_result, final_citations = self.analyzer.analyze_comprehensive_news_professional(
                akshare_news, search_news, all_citations, commodity, target_date
            )
            
            if "❌" in analysis_result:
                print(f"❌ {commodity} 新闻分析失败: {analysis_result}")
                return {
                    "success": False,
                    "error": analysis_result,
                    "commodity": commodity
                }
            
            # 构建成功结果 - 支持中文名称和英文代码
            if commodity in self.analyzer.all_commodities:
                config = self.analyzer.all_commodities[commodity]
            else:
                # 尝试通过英文代码查找
                config = None
                for chinese_name, cfg in self.analyzer.all_commodities.items():
                    if cfg.get("symbol") == commodity:
                        config = cfg
                        break

                if not config:
                    return {
                        "success": False,
                        "error": f"未找到品种配置: {commodity}",
                        "commodity": commodity
                    }

            result = {
                "success": True,
                "commodity": commodity,
                "symbol": config['symbol'],
                "exchange": config['exchange'],
                "category": config['category'],
                "analysis_date": target_date.strftime('%Y-%m-%d'),
                "analysis_content": analysis_result,
                "news_sources": final_citations,
                "news_count": total_news,
                "akshare_count": len(akshare_news) if not akshare_news.empty else 0,
                "search_count": len(search_news),
                "data_quality_score": min(0.95, total_news / 20),  # 简单质量评分
                "analysis_version": "v4.0_professional"
            }
            
            print(f"✅ {commodity} 新闻分析成功")
            return self._format_for_streamlit(result)
                
        except Exception as e:
            print(f"❌ 新闻分析异常: {e}")
            return {
                "success": False,
                "error": f"新闻分析过程中发生错误: {str(e)}",
                "commodity": commodity
            }
    
    def _format_for_streamlit(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化结果以适配Streamlit显示"""
        
        # 基础信息
        formatted_result = {
            "success": True,
            "commodity": result.get("commodity", ""),
            "symbol": result.get("symbol", ""),
            "exchange": result.get("exchange", ""),
            "category": result.get("category", ""),
            "analysis_date": result.get("analysis_date", ""),
            "news_count": result.get("news_count", 0),
            "data_quality_score": result.get("data_quality_score", 0.0),
            "analysis_version": result.get("analysis_version", "v2.0_improved")
        }
        
        # AI分析内容（已清理Markdown符号）
        if "analysis_content" in result:
            formatted_result["ai_analysis"] = result["analysis_content"]
        
        # 新闻来源和引用
        if "news_sources" in result:
            formatted_result["citations"] = self._format_citations(result["news_sources"])
        
        # 添加akshare和搜索数据统计
        formatted_result["akshare_count"] = result.get("akshare_count", 0)
        formatted_result["search_count"] = result.get("search_count", 0)
        
        # 分析元数据
        formatted_result["metadata"] = {
            "analysis_timestamp": result.get("analysis_timestamp", ""),
            "data_source": "improved_news_analysis",
            "model_used": "deepseek-chat",
            "search_engines": self._extract_search_engines(result.get("news_sources", [])),
            "professional_sites_count": self._count_professional_sites(result.get("news_sources", []))
        }
        
        # 生成结构化分析摘要
        formatted_result["structured_analysis"] = self._generate_structured_summary(result)
        
        return formatted_result
    
    def _format_citations(self, news_sources: list) -> list:
        """格式化引用列表"""
        citations = []
        
        for i, source in enumerate(news_sources, 1):
            citation = {
                "index": i,
                "title": source.get("title", "未知标题"),
                "source": source.get("source", "未知来源"),
                "url": source.get("url", ""),
                "date": source.get("date", "未知日期"),
                "relevance_score": source.get("relevance", 0),  # 注意这里是relevance而不是relevance_score
                "search_engine": source.get("type", "未知类型")
            }
            citations.append(citation)
        
        return citations
    
    def _extract_search_engines(self, news_sources: list) -> list:
        """提取使用的搜索引擎"""
        engines = set()
        for source in news_sources:
            engine = source.get("search_engine", "")
            if engine:
                engines.add(engine)
        return list(engines)
    
    def _count_professional_sites(self, news_sources: list) -> int:
        """统计专业网站数量"""
        professional_count = 0
        for source in news_sources:
            search_engine = source.get("search_engine", "")
            if "专业网站搜索" in search_engine:
                professional_count += 1
        return professional_count
    
    def _generate_structured_summary(self, result: Dict[str, Any]) -> Dict:
        """生成结构化分析摘要"""
        analysis_content = result.get("analysis_content", "")
        
        summary = {
            "analysis_quality": {
                "content_length": len(analysis_content),
                "data_quality": result.get("data_quality_score", 0.0),
                "news_coverage": result.get("news_count", 0),
                "professional_level": "高" if len(analysis_content) > 2000 else "中" if len(analysis_content) > 1000 else "低"
            },
            "key_insights": self._extract_key_insights(analysis_content),
            "risk_factors": self._extract_risk_factors(analysis_content),
            "investment_suggestions": self._extract_investment_suggestions(analysis_content)
        }
        
        return summary
    
    def _extract_key_insights(self, content: str) -> list:
        """提取关键洞察"""
        insights = []
        
        # 简单的关键词提取逻辑
        key_phrases = [
            "核心观点", "主要驱动", "关键因素", "重要变化", "显著影响",
            "核心逻辑", "主要原因", "关键数据", "重要信号", "核心支撑"
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if any(phrase in line for phrase in key_phrases) and len(line) > 20:
                insights.append(line[:200])  # 限制长度
                if len(insights) >= 5:  # 最多5个洞察
                    break
        
        return insights
    
    def _extract_risk_factors(self, content: str) -> list:
        """提取风险因素"""
        risks = []
        
        risk_keywords = [
            "风险", "不确定", "压力", "下行", "威胁", "挑战",
            "警惕", "关注", "谨慎", "波动", "冲击"
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in risk_keywords) and len(line) > 20:
                risks.append(line[:200])
                if len(risks) >= 3:  # 最多3个风险
                    break
        
        return risks
    
    def _extract_investment_suggestions(self, content: str) -> list:
        """提取投资建议"""
        suggestions = []
        
        suggestion_keywords = [
            "建议", "策略", "操作", "配置", "布局", "关注",
            "买入", "卖出", "持有", "减仓", "加仓", "观望"
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in suggestion_keywords) and len(line) > 20:
                suggestions.append(line[:200])
                if len(suggestions) >= 3:  # 最多3个建议
                    break
        
        return suggestions

# 创建全局适配器实例
_improved_news_adapter = None

def get_improved_news_adapter(deepseek_api_key: str):
    """获取改进版新闻分析适配器实例"""
    global _improved_news_adapter
    if _improved_news_adapter is None:
        _improved_news_adapter = StreamlitImprovedNewsAdapter(deepseek_api_key)
    return _improved_news_adapter

def analyze_improved_news_for_streamlit(commodity: str, deepseek_api_key: str,
                                      analysis_date: str = None, days_back: int = 7) -> Dict[str, Any]:
    """
    Streamlit系统调用的改进版新闻分析接口
    
    Args:
        commodity: 品种名称
        deepseek_api_key: DeepSeek API密钥
        analysis_date: 分析日期
        days_back: 搜索天数
        
    Returns:
        Dict: 格式化的分析结果
    """
    adapter = get_improved_news_adapter(deepseek_api_key)
    return adapter.analyze_news_for_streamlit(commodity, analysis_date, days_back)

# 测试函数
if __name__ == "__main__":
    print("🧪 测试Streamlit改进版新闻分析适配器")
    print("=" * 60)
    
    # 测试分析
    test_commodity = "螺纹钢"
    test_api_key = "your_deepseek_api_key_here"
    
    if test_api_key == "your_deepseek_api_key_here":
        print("❌ 请先配置DeepSeek API密钥进行测试")
    else:
        print(f"📊 测试分析品种: {test_commodity}")
        
        result = analyze_improved_news_for_streamlit(
            commodity=test_commodity,
            deepseek_api_key=test_api_key,
            days_back=7
        )
        
        if result.get("success"):
            print("✅ 测试成功!")
            print(f"📈 品种: {result['commodity']} ({result['symbol']})")
            print(f"📅 分析日期: {result['analysis_date']}")
            print(f"📊 新闻数量: {result['news_count']}")
            print(f"🎯 数据质量: {result['data_quality_score']:.1%}")
            
            if "ai_analysis" in result:
                analysis_length = len(result['ai_analysis'])
                print(f"🤖 AI分析: {analysis_length} 字符")
                
                # 检查是否包含Markdown符号
                markdown_symbols = ['##', '**', '*', '```', '- ', '> ']
                has_markdown = any(symbol in result['ai_analysis'] for symbol in markdown_symbols)
                if has_markdown:
                    print("⚠️ 检测到Markdown符号，需要进一步清理")
                else:
                    print("✅ 分析内容无Markdown符号")
            
            if "citations" in result:
                print(f"🔗 新闻引用: {len(result['citations'])} 条")
                
                # 显示前3个引用示例
                for i, citation in enumerate(result['citations'][:3], 1):
                    print(f"  [{i}] {citation['title'][:50]}...")
                    print(f"      来源: {citation['source']}")
                    print(f"      链接: {citation['url'][:50]}...")
                    
        else:
            print(f"❌ 测试失败: {result.get('error', '未知错误')}")
    
    print("\n🎉 测试完成!")
