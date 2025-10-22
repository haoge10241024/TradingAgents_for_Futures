#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极AI期限结构分析系统
图文融合 + 专业完整 + 交互式界面
"""

import pandas as pd
import numpy as np
import requests
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import seaborn as sns
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
import plotly.express as px
from IPython.display import display, Markdown, HTML
import base64
from io import BytesIO

# 设置中文字体和样式
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False
plt.style.use('default')

warnings.filterwarnings('ignore')

class UltimateTermStructureAnalyzer:
    """终极期限结构分析器 - 完整专业版本"""
    
    def __init__(self, deepseek_api_key: str = "sk-293dec7fabb54606b4f8d4f606da3383", 
                 serper_api_key: str = "d3654e36956e0bf331e901886c49c602cea72eb1", 
                 data_dir: str = r"D:\Cursor\cursor项目\TradingAgent\qihuo\database"):
        self.deepseek_api_key = deepseek_api_key
        self.serper_api_key = serper_api_key
        self.data_dir = Path(data_dir)
        
        # API配置
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"
        self.serper_url = "https://google.serper.dev/search"
        
        # 引用管理系统
        self.references = []
        self.reference_counter = 0
        
        # 图表管理系统
        self.chart_counter = 0
        self.charts_html = []
        
        # 品种配置
        self.base_variety_config = {
            "C": {"chinese_name": "玉米", "type": "农产品", "exchange": "大商所"},
            "M": {"chinese_name": "豆粕", "type": "农产品", "exchange": "大商所"},
            "RM": {"chinese_name": "菜籽粕", "type": "农产品", "exchange": "郑商所"},
            "CF": {"chinese_name": "棉花", "type": "农产品", "exchange": "郑商所"},
            "SR": {"chinese_name": "白糖", "type": "农产品", "exchange": "郑商所"},
            "RB": {"chinese_name": "螺纹钢", "type": "黑色金属", "exchange": "上期所"},
            "I": {"chinese_name": "铁矿石", "type": "黑色金属", "exchange": "大商所"},
            "J": {"chinese_name": "焦炭", "type": "黑色金属", "exchange": "大商所"},
            "JM": {"chinese_name": "焦煤", "type": "黑色金属", "exchange": "大商所"},
            "CU": {"chinese_name": "沪铜", "type": "有色金属", "exchange": "上期所"},
            "AL": {"chinese_name": "沪铝", "type": "有色金属", "exchange": "上期所"},
            "ZN": {"chinese_name": "沪锌", "type": "有色金属", "exchange": "上期所"},
            "PB": {"chinese_name": "沪铅", "type": "有色金属", "exchange": "上期所"},
            "NI": {"chinese_name": "沪镍", "type": "有色金属", "exchange": "上期所"},
            "SN": {"chinese_name": "沪锡", "type": "有色金属", "exchange": "上期所"},
            "AU": {"chinese_name": "沪金", "type": "贵金属", "exchange": "上期所"},
            "AG": {"chinese_name": "沪银", "type": "贵金属", "exchange": "上期所"},
            "SC": {"chinese_name": "原油", "type": "能源化工", "exchange": "上期能源"},
            "FU": {"chinese_name": "燃料油", "type": "能源化工", "exchange": "上期所"},
            "BU": {"chinese_name": "沥青", "type": "能源化工", "exchange": "上期所"},
            "RU": {"chinese_name": "橡胶", "type": "能源化工", "exchange": "上期所"},
            "L": {"chinese_name": "聚乙烯", "type": "化工", "exchange": "大商所"},
            "V": {"chinese_name": "PVC", "type": "化工", "exchange": "大商所"},
            "PP": {"chinese_name": "聚丙烯", "type": "化工", "exchange": "大商所"},
            "EG": {"chinese_name": "乙二醇", "type": "化工", "exchange": "大商所"},
            "EB": {"chinese_name": "苯乙烯", "type": "化工", "exchange": "大商所"},
            "PG": {"chinese_name": "液化石油气", "type": "化工", "exchange": "大商所"},
            "SA": {"chinese_name": "纯碱", "type": "化工", "exchange": "郑商所"},
            "FG": {"chinese_name": "玻璃", "type": "化工", "exchange": "郑商所"},
            "MA": {"chinese_name": "甲醇", "type": "化工", "exchange": "郑商所"},
            "TA": {"chinese_name": "PTA", "type": "化工", "exchange": "郑商所"},
            "PF": {"chinese_name": "短纤", "type": "化工", "exchange": "郑商所"},
            "PK": {"chinese_name": "花生", "type": "农产品", "exchange": "郑商所"},
            "AP": {"chinese_name": "苹果", "type": "农产品", "exchange": "郑商所"},
            "CJ": {"chinese_name": "红枣", "type": "农产品", "exchange": "郑商所"},
            "LH": {"chinese_name": "生猪", "type": "农产品", "exchange": "大商所"},
            "JD": {"chinese_name": "鸡蛋", "type": "农产品", "exchange": "大商所"},
            "CS": {"chinese_name": "玉米淀粉", "type": "农产品", "exchange": "大商所"},
            "A": {"chinese_name": "豆一", "type": "农产品", "exchange": "大商所"},
            "B": {"chinese_name": "豆二", "type": "农产品", "exchange": "大商所"},
            "Y": {"chinese_name": "豆油", "type": "农产品", "exchange": "大商所"},
            "P": {"chinese_name": "棕榈油", "type": "农产品", "exchange": "大商所"},
            "OI": {"chinese_name": "菜籽油", "type": "农产品", "exchange": "郑商所"},
            "RS": {"chinese_name": "菜籽", "type": "农产品", "exchange": "郑商所"},
            "WH": {"chinese_name": "强麦", "type": "农产品", "exchange": "郑商所"},
            "PM": {"chinese_name": "普麦", "type": "农产品", "exchange": "郑商所"},
            "RI": {"chinese_name": "早籼稻", "type": "农产品", "exchange": "郑商所"},
            "LR": {"chinese_name": "晚籼稻", "type": "农产品", "exchange": "郑商所"},
            "JR": {"chinese_name": "粳稻", "type": "农产品", "exchange": "郑商所"},
            "SF": {"chinese_name": "硅铁", "type": "黑色金属", "exchange": "郑商所"},
            "SM": {"chinese_name": "锰硅", "type": "黑色金属", "exchange": "郑商所"},
            "ZC": {"chinese_name": "动力煤", "type": "能源化工", "exchange": "郑商所"},
            "PS": {"chinese_name": "多晶硅", "type": "化工", "exchange": "大商所"},
            "PX": {"chinese_name": "对二甲苯", "type": "化工", "exchange": "大商所"},
            "BC": {"chinese_name": "国际铜", "type": "有色金属", "exchange": "上期能源"},
            "EC": {"chinese_name": "欧线集运", "type": "其他", "exchange": "上期所"},
            "LC": {"chinese_name": "碳酸锂", "type": "有色金属", "exchange": "广期所"},
            "SI": {"chinese_name": "工业硅", "type": "有色金属", "exchange": "广期所"}
        }
        
        self.variety_config = self.base_variety_config
        
        print("🚀 终极期限结构分析系统初始化完成")
        print(f"📁 数据目录: {self.data_dir}")
        print("🔑 DeepSeek API: 已配置")
        print("🔍 Serper API: 已配置")
        print(f"📊 发现 {len(self.variety_config)} 个可用品种")
    
    def start_interactive_analysis(self):
        """启动交互式分析界面"""
        
        print("\n" + "="*80)
        print("🎯 终极AI期限结构分析系统")
        print("📊 专业级图文融合分析报告")
        print("="*80)
        
        # 显示支持的品种
        self.show_supported_varieties()
        
        while True:
            print("\n" + "-"*60)
            print("🔍 请输入分析参数:")
            
            # 获取用户输入
            variety = input("📈 品种代码 (如: C, RB, V): ").strip().upper()
            if not variety:
                print("❌ 品种代码不能为空")
                continue
            
            analysis_date = input("📅 分析日期 (格式: 2025-01-10, 回车使用今日): ").strip()
            if not analysis_date:
                analysis_date = datetime.now().strftime("%Y-%m-%d")
            
            model_mode = input("🤖 模型模式 (chat/reasoner, 回车默认chat): ").strip().lower()
            if not model_mode:
                model_mode = "chat"
            elif model_mode not in ["chat", "reasoner"]:
                print("❌ 模型模式只能是 chat 或 reasoner")
                continue
            
            # 确认参数
            print(f"\n✅ 分析参数确认:")
            print(f"   品种: {variety}")
            print(f"   日期: {analysis_date}")
            print(f"   模型: {model_mode}")
            
            confirm = input("\n🚀 开始分析? (y/n, 回车确认): ").strip().lower()
            if confirm in ['', 'y', 'yes']:
                break
            elif confirm in ['n', 'no']:
                print("❌ 分析已取消")
                return None
        
        # 执行分析
        print(f"\n🎯 开始分析 {variety} 期货...")
        result = self.analyze_variety(variety, analysis_date, model_mode)
        
        # 询问是否继续分析其他品种
        while True:
            continue_analysis = input("\n🔄 是否继续分析其他品种? (y/n): ").strip().lower()
            if continue_analysis in ['n', 'no']:
                print("👋 感谢使用终极AI期限结构分析系统!")
                break
            elif continue_analysis in ['y', 'yes']:
                self.start_interactive_analysis()
                break
        
        return result
    
    def analyze_variety(self, variety: str, analysis_date: str = None, model_mode: str = "chat") -> Dict:
        """分析指定品种的期限结构 - 完整专业版本"""
        
        # 清空之前的引用和图表
        self._clear_references()
        self._clear_charts()
        
        if variety not in self.variety_config:
            variety = self._guess_variety_from_input(variety)
            if not variety:
                print("❌ 品种识别失败，请检查输入")
                return {"error": "无法识别品种"}
        
        chinese_name = self.variety_config[variety]["chinese_name"]
        analysis_date = analysis_date or datetime.now().strftime("%Y-%m-%d")
        
        print(f"🔍 开始分析 {variety}({chinese_name}) 期限结构")
        print(f"📅 分析日期: {analysis_date}")
        print(f"🤖 模型模式: {model_mode}")
        print("="*80)
        
        try:
            # 步骤1: 收集真实数据
            print("📊 步骤1: 收集真实数据...")
            real_data = self._collect_real_data(variety)
            
            # 步骤2: 搜索补充数据
            print("🔍 步骤2: 搜索补充数据...")
            external_data = self._search_supplementary_data(variety, chinese_name)
            
            # 步骤3: 数据整合与分析
            print("⚙️ 步骤3: 数据整合与分析...")
            integrated_analysis = self._integrate_and_analyze(variety, real_data, external_data)
            
            # 步骤4: 生成图表
            print("📊 步骤4: 生成专业图表...")
            self._generate_all_charts(variety, real_data, integrated_analysis)
            
            # 步骤5: 生成完整报告
            print("🤖 步骤5: 生成完整专业报告...")
            report = self._generate_complete_report(variety, chinese_name, integrated_analysis, real_data, model_mode)
            
            print("✅ 分析完成!")
            
            # 显示完整报告
            self._display_complete_report(variety, chinese_name, analysis_date, model_mode, report)
            
            return {
                "variety": variety,
                "chinese_name": chinese_name,
                "analysis_date": analysis_date,
                "model_mode": model_mode,
                "integrated_analysis": integrated_analysis,
                "report": report,
                "charts": self.charts_html,
                "references": self.references
            }
            
        except Exception as e:
            print(f"❌ 分析过程出错: {str(e)}")
            return {
                "error": str(e),
                "charts": self.charts_html,
                "references": self.references
            }
    
    def _clear_charts(self):
        """清空图表信息"""
        self.charts_html = []
        self.chart_counter = 0
    
    def _clear_references(self):
        """清空引用信息"""
        self.references = []
        self.reference_counter = 0
    
    def _collect_real_data(self, variety: str) -> Dict:
        """收集真实数据"""
        real_data = {}
        
        # 加载期限结构数据
        print("  📈 加载期限结构数据...")
        real_data["term_structure"] = self._load_term_structure_data(variety)
        
        # 加载库存数据
        print("  📦 加载库存数据...")
        real_data["inventory"] = self._load_inventory_data(variety)
        
        # 加载基差数据
        print("  📊 加载基差数据...")
        real_data["basis"] = self._load_basis_data(variety)
        
        # 加载仓单数据
        print("  📋 加载仓单数据...")
        real_data["receipt"] = self._load_receipt_data(variety)
        
        # 加载持仓数据
        print("  👥 加载持仓数据...")
        real_data["positioning"] = self._load_positioning_data(variety)
        
        # 加载技术分析数据
        print("  📉 加载技术分析数据...")
        real_data["technical"] = self._load_technical_data(variety)
        
        return real_data
    
    def _load_term_structure_data(self, variety: str) -> Dict:
        """加载期限结构数据"""
        try:
            file_path = self.data_dir / "term_structure" / variety / "term_structure.csv"
            
            if not file_path.exists():
                return {"error": "期限结构数据文件不存在，将通过联网搜索补充数据"}
            
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {"error": "期限结构数据文件为空"}
            
            # 获取最新日期的数据
            latest_date = df['date'].max()
            latest_data = df[df['date'] == latest_date].copy()
            
            # 按合约月份排序
            latest_data = latest_data.sort_values('symbol').copy()
            
            # 提取数据
            contracts = latest_data['symbol'].tolist()
            prices = latest_data['close'].tolist()
            volumes = latest_data['volume'].tolist()
            open_interests = latest_data['open_interest'].tolist()
            roll_yields = latest_data['roll_yield'].tolist()

            # 确保数据类型正确
            if not isinstance(prices, list):
                prices = list(prices)
            if not isinstance(contracts, list):
                contracts = list(contracts)
            if not isinstance(volumes, list):
                volumes = list(volumes)

            # 计算价差
            spreads = []
            if len(prices) > 1:
                for i in range(len(prices) - 1):
                    spread = prices[i] - prices[i + 1]
                    spreads.append(spread)
            
            # 计算基本统计
            near_price = prices[0] if prices else 0
            far_price = prices[-1] if prices else 0
            absolute_spread = near_price - far_price
            relative_spread = (absolute_spread / far_price * 100) if far_price != 0 else 0
            
            # 判断结构类型
            if absolute_spread > 10:
                structure_type = "Backwardation(贴水)"
            elif absolute_spread < -10:
                structure_type = "Contango(升水)"
            else:
                structure_type = "Flat(平坦)"
            
            # 计算整体斜率
            if len(prices) > 1:
                overall_slope = (prices[-1] - prices[0]) / (len(prices) - 1)
            else:
                overall_slope = 0
            
            return {
                "contracts": contracts,
                "prices": prices,
                "volumes": volumes,
                "open_interests": open_interests,
                "roll_yields": roll_yields,
                "spreads": spreads,
                "structure_type": structure_type,
                "near_price": near_price,
                "far_price": far_price,
                "absolute_spread": absolute_spread,
                "relative_spread": relative_spread,
                "overall_slope": overall_slope,
                "contract_count": len(contracts),
                "data_date": str(latest_date)
            }
            
        except Exception as e:
            return {"error": f"期限结构数据加载失败: {str(e)}"}
    
    def _load_inventory_data(self, variety: str) -> Dict:
        """加载库存数据"""
        try:
            file_path = self.data_dir / "inventory" / variety / "inventory.csv"
            
            if not file_path.exists():
                return {"error": f"库存数据文件不存在: {file_path}"}
            
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {"error": "库存数据文件为空"}
            
            # 获取最新数据
            latest_value = df['value'].iloc[-1]
            
            # 计算历史分位数
            historical_percentile = ((df['value'] <= latest_value).mean() * 100).item()
            
            # 计算趋势
            if len(df) >= 5:
                recent_trend = df['value'].tail(5).diff().mean().item()
                if recent_trend > 0:
                    trend_analysis = "温和上升"
                elif recent_trend < 0:
                    trend_analysis = "温和下降"
                else:
                    trend_analysis = "基本稳定"
            else:
                trend_analysis = "数据不足"
            
            return {
                "current_value": latest_value,
                "historical_percentile": historical_percentile,
                "trend_analysis": trend_analysis,
                "data_points": len(df)
            }
            
        except Exception as e:
            return {"error": f"库存数据加载失败: {str(e)}"}
    
    def _load_basis_data(self, variety: str) -> Dict:
        """加载基差数据"""
        try:
            file_path = self.data_dir / "basis" / variety / "basis_data.csv"
            
            if not file_path.exists():
                return {"error": "基差数据文件不存在"}
            
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {"error": "基差数据文件为空"}
            
            # 获取最新数据
            latest_row = df.iloc[-1]
            
            current_near_basis = latest_row.get('near_basis', 0)
            current_dom_basis = latest_row.get('dom_basis', 0)
            
            # 计算基差趋势
            if len(df) >= 5:
                recent_basis_trend = df['near_basis'].tail(5).diff().mean().item()
                if recent_basis_trend > 10:
                    basis_trend = "基差快速走强"
                elif recent_basis_trend > 0:
                    basis_trend = "基差温和走强"
                elif recent_basis_trend < -10:
                    basis_trend = "基差快速走弱"
                elif recent_basis_trend < 0:
                    basis_trend = "基差温和走弱"
                else:
                    basis_trend = "基差基本稳定"
            else:
                basis_trend = "数据不足"
            
            return {
                "current_near_basis": current_near_basis,
                "current_dom_basis": current_dom_basis,
                "basis_trend": basis_trend,
                "spot_price": latest_row.get('spot_price', 0),
                "near_contract_price": latest_row.get('near_contract_price', 0),
                "dominant_contract_price": latest_row.get('dominant_contract_price', 0)
            }
            
        except Exception as e:
            return {"error": f"基差数据加载失败: {str(e)}"}
    
    def _load_receipt_data(self, variety: str) -> Dict:
        """加载仓单数据"""
        try:
            file_path = self.data_dir / "receipt" / variety / "receipt.csv"
            
            if not file_path.exists():
                return {"error": "仓单数据文件不存在"}
            
            df = pd.read_csv(file_path)
            
            if df.empty:
                return {"error": "仓单数据文件为空"}
            
            return {
                "data_available": True,
                "data_points": len(df)
            }
            
        except Exception as e:
            return {"error": f"仓单数据加载失败: {str(e)}"}
    
    def _load_positioning_data(self, variety: str) -> Dict:
        """加载持仓数据"""
        try:
            positioning_dir = self.data_dir / "positioning" / variety
            
            if not positioning_dir.exists():
                return {"error": "持仓数据目录不存在"}
            
            # 尝试加载多空持仓数据
            files_to_check = [
                "long_position_ranking.csv",
                "short_position_ranking.csv", 
                "volume_ranking.csv"
            ]
            
            available_files = []
            for file_name in files_to_check:
                file_path = positioning_dir / file_name
                if file_path.exists():
                    available_files.append(file_name)
            
            if not available_files:
                return {"error": "持仓数据文件不存在"}
            
            return {
                "data_available": True,
                "available_files": available_files
            }
            
        except Exception as e:
            return {"error": f"持仓数据加载失败: {str(e)}"}
    
    def _load_technical_data(self, variety: str) -> Dict:
        """加载技术分析数据"""
        try:
            technical_dir = self.data_dir / "technical_analysis" / variety
            
            if not technical_dir.exists():
                return {"error": "技术分析数据目录不存在"}
            
            # 检查主要技术指标文件
            main_indicators_path = technical_dir / "main_indicators.csv"
            
            if not main_indicators_path.exists():
                return {"error": "主要技术指标文件不存在"}
            
            return {
                "data_available": True,
                "indicators_available": True
            }
            
        except Exception as e:
            return {"error": f"技术分析数据加载失败: {str(e)}"}
    
    def _search_supplementary_data(self, variety: str, chinese_name: str) -> Dict:
        """搜索补充数据"""
        external_data = {}
        
        if not self.serper_api_key:
            external_data["note"] = "未配置Serper API，跳过外部数据搜索"
            return external_data
        
        try:
            exchange = self.variety_config[variety]["exchange"]
            
            # 1. 搜索交易所费用信息
            print("    🔍 搜索交易所费用信息...")
            fees_query = f"{exchange} {chinese_name} 期货 交割费用 仓储费 手续费标准 2024"
            external_data["exchange_fees"] = self._serper_search(fees_query, max_results=3)
            
            # 2. 搜索行业新闻
            print("    📰 搜索行业新闻...")
            news_query = f"{chinese_name} 期货 行业动态 供需 2024"
            external_data["industry_news"] = self._serper_search(news_query, max_results=3)
            
            # 3. 搜索市场展望
            print("    🔮 搜索市场展望...")
            outlook_query = f"{chinese_name} 期货 市场展望 价格预测 分析"
            external_data["market_outlook"] = self._serper_search(outlook_query, max_results=2)
            
            # 4. 搜索供需数据
            print("    📊 搜索供需数据...")
            supply_query = f"{chinese_name} 产量 消费量 库存 供需平衡 2024"
            external_data["supply_demand"] = self._serper_search(supply_query, max_results=2)
            
            time.sleep(1)  # 避免API限流
            
        except Exception as e:
            external_data["error"] = f"外部数据搜索失败: {str(e)}"
        
        return external_data
    
    def _serper_search(self, query: str, max_results: int = 3) -> Dict:
        """使用Serper API搜索"""
        try:
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'num': max_results,
                'hl': 'zh-cn',
                'gl': 'cn'
            }
            
            response = requests.post(self.serper_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取有用信息并添加引用
                search_results = []
                if 'organic' in result:
                    for item in result['organic'][:max_results]:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        link = item.get('link', '')
                        
                        # 为每个搜索结果添加引用标记
                        reference_mark = self._add_reference(title, link, snippet)
                        
                        search_results.append({
                            'title': title,
                            'snippet': snippet,
                            'link': link,
                            'reference': reference_mark  # 添加引用标记
                        })
                
                return {
                    'results': search_results,
                    'query': query,
                    'total_results': len(search_results)
                }
            else:
                return {'error': f'搜索API请求失败: {response.status_code}'}
                
        except Exception as e:
            return {'error': f'搜索过程出错: {str(e)}'}
    
    def _add_reference(self, title: str, link: str, snippet: str = "") -> str:
        """添加引用并返回引用标记"""
        self.reference_counter += 1
        reference_mark = f"[{self.reference_counter}]"
        
        self.references.append({
            "id": self.reference_counter,
            "title": title,
            "link": link,
            "snippet": snippet,
            "mark": reference_mark
        })
        
        return reference_mark
    
    def _integrate_and_analyze(self, variety: str, real_data: Dict, external_data: Dict) -> Dict:
        """数据整合与分析"""
        integrated_analysis = {}
        
        # 1. 数据质量评估
        integrated_analysis["data_quality"] = self._assess_data_quality(real_data)
        
        # 2. Full Carry分析 - 恢复完整版本
        integrated_analysis["full_carry_analysis"] = self._analyze_full_carry(variety, real_data, external_data)
        
        # 3. Convenience Yield分析 - 恢复完整版本
        integrated_analysis["convenience_yield_analysis"] = self._analyze_convenience_yield(real_data, external_data)
        
        # 4. 结构分析
        integrated_analysis["structure_analysis"] = self._analyze_structure_characteristics(real_data)
        
        # 5. 价差分析
        integrated_analysis["spread_analysis"] = self._analyze_spread_patterns(real_data)
        
        # 6. 产业结构分析 - 新增
        integrated_analysis["industry_analysis"] = self._analyze_industry_structure(variety, real_data, external_data)
        
        # 7. 风险评估
        integrated_analysis["risk_assessment"] = self._assess_risks(real_data, integrated_analysis)
        
        # 8. 外部数据
        integrated_analysis["external_data"] = external_data
        
        return integrated_analysis
    
    def _assess_data_quality(self, real_data: Dict) -> Dict:
        """评估数据质量"""
        total_sources = 6  # term_structure, inventory, basis, receipt, positioning, technical
        available_sources = []
        missing_sources = []
        
        for source_name, data in real_data.items():
            if isinstance(data, dict) and "error" not in data and len(data) > 0:
                available_sources.append(source_name)
            elif isinstance(data, dict) and "error" not in data:
                # 检查是否有其他有效字段
                has_valid_data = any(key for key in data.keys() if key != "error")
                if has_valid_data:
                    available_sources.append(source_name)
                else:
                    missing_sources.append(source_name)
            else:
                missing_sources.append(source_name)
        
        quality_percentage = (len(available_sources) / total_sources) * 100
        
        if quality_percentage >= 80:
            quality_level = "优秀"
        elif quality_percentage >= 60:
            quality_level = "良好"
        elif quality_percentage >= 40:
            quality_level = "一般"
        else:
            quality_level = "较差"
        
        return {
            "quality_percentage": round(quality_percentage, 2),
            "quality_level": quality_level,
            "available_sources": available_sources,
            "missing_sources": missing_sources,
            "recommendation": "数据质量良好，可进行深度分析" if quality_percentage >= 60 else "数据不完整，分析结果可能受限"
        }
    
    def _analyze_full_carry(self, variety: str, real_data: Dict, external_data: Dict = None) -> Dict:
        """分析Full Carry - 基于真实的交易所费用数据"""
        
        term_data = real_data.get("term_structure", {})
        if "error" in term_data:
            return {"error": "期限结构数据不可用，无法计算Full Carry"}
        
        prices = term_data.get("prices", [])
        spreads = term_data.get("spreads", [])
        
        if not prices or not spreads:
            return {"error": "价格数据不完整，无法计算Full Carry"}
        
        # 尝试从外部搜索数据获取交易所费用信息
        exchange_fees_data = None
        if external_data and "exchange_fees" in external_data:
            exchange_fees_results = external_data["exchange_fees"].get("results", [])
            if exchange_fees_results:
                exchange_fees_data = exchange_fees_results[0]  # 使用第一个搜索结果
        
        if not exchange_fees_data:
            return {
                "status": "数据缺失",
                "error": "无法获取真实的交易所费用数据",
                "suggestion": "需要通过联网搜索获取具体的仓储费、交割费等数据",
                "data_source": "数据缺失",
                "note": "Full Carry计算需要真实的交易所费用数据，不能使用估算值"
            }
        
        # 如果有真实数据，进行计算
        return {
            "status": "需要人工解析",
            "exchange_data": exchange_fees_data,
            "data_source": f"网络搜索结果 {exchange_fees_data.get('reference', '')}",
            "note": "已获取交易所费用信息，需要从搜索结果中提取具体数值进行计算",
            "search_result": {
                "title": exchange_fees_data.get("title", ""),
                "snippet": exchange_fees_data.get("snippet", ""),
                "link": exchange_fees_data.get("link", ""),
                "reference": exchange_fees_data.get("reference", "")
            }
        }
    
    def _analyze_convenience_yield(self, real_data: Dict, external_data: Dict = None) -> Dict:
        """分析Convenience Yield - 基于真实数据，不使用估算"""
        
        inventory_data = real_data.get("inventory", {})
        basis_data = real_data.get("basis", {})
        term_data = real_data.get("term_structure", {})
        
        if "error" in inventory_data:
            return {"error": "库存数据不可用，无法分析便利收益"}
        
        inventory_percentile = inventory_data.get("historical_percentile", None)
        if inventory_percentile is None:
            return {"error": "缺少库存历史分位数数据"}
        
        # 便利收益需要通过实际的期限结构和基差数据计算，而不是估算
        if "error" in term_data or "error" in basis_data:
            return {
                "status": "数据不完整",
                "error": "便利收益计算需要完整的期限结构和基差数据",
                "available_data": {
                    "inventory_percentile": inventory_percentile,
                    "inventory_signal": "供应紧张" if inventory_percentile < 25 else "供应充足"
                },
                "data_source": "本地库存数据",
                "note": "便利收益应通过 Convenience Yield = Storage Cost + Interest Rate - (F-S)/S 公式计算，需要真实的仓储成本和利率数据"
            }
        
        # 如果有完整数据，提供基础分析但不编造数值
        return {
            "status": "基础分析可用",
            "inventory_percentile": inventory_percentile,
            "inventory_signal": "供应紧张" if inventory_percentile < 25 else "供应充足",
            "market_implication": "支持Backwardation结构" if inventory_percentile < 25 else "支持Contango结构",
            "data_source": "本地库存数据分析",
            "note": "便利收益的具体数值需要通过真实的仓储成本、利率和期限结构数据计算，不能使用估算值",
            "calculation_needed": "Convenience Yield = Storage Cost + Interest Rate - (Forward Price - Spot Price) / Spot Price"
        }
    
    def _analyze_structure_characteristics(self, real_data: Dict) -> Dict:
        """分析结构特征"""
        
        term_data = real_data.get("term_structure", {})
        if "error" in term_data:
            return {"error": "期限结构数据不可用"}
        
        # 增强的量化分析
        enhanced_analysis = self._calculate_enhanced_metrics(term_data)
        
        return enhanced_analysis
    
    def _calculate_enhanced_metrics(self, term_data: Dict) -> Dict:
        """计算增强的量化指标"""
        
        contracts = term_data.get("contracts", [])
        prices = term_data.get("prices", [])
        volumes = term_data.get("volumes", [])
        open_interests = term_data.get("open_interests", [])
        roll_yields = term_data.get("roll_yields", [])
        spreads = term_data.get("spreads", [])
        
        if not contracts or not prices:
            return {"error": "数据不足"}
        
        # 基本指标
        near_price = prices[0]
        far_price = prices[-1]
        absolute_spread = near_price - far_price
        relative_spread = (absolute_spread / far_price * 100) if far_price != 0 else 0
        
        # 计算整体斜率
        if len(prices) > 1:
            overall_slope = (prices[-1] - prices[0]) / (len(prices) - 1)
        else:
            overall_slope = 0
        
        # 流动性分析
        liquidity_analysis = {}
        if volumes:
            total_volume = sum(volumes)
            total_oi = sum(open_interests)
            
            # 主力合约识别
            max_volume_idx = volumes.index(max(volumes))
            main_contract = contracts[max_volume_idx] if contracts else "未知"
            main_volume_ratio = (max(volumes) / total_volume * 100) if total_volume > 0 else 0
            main_oi_ratio = (open_interests[max_volume_idx] / total_oi * 100) if total_oi > 0 else 0
            
            # 集中度分析
            sorted_volumes = sorted(volumes, reverse=True)
            top3_volume_ratio = (sum(sorted_volumes[:3]) / total_volume * 100) if total_volume > 0 else 0
            
            liquidity_analysis = {
                "total_volume": total_volume,
                "total_oi": total_oi,
                "main_contract": main_contract,
                "main_volume_ratio": round(main_volume_ratio, 2),
                "main_oi_ratio": round(main_oi_ratio, 2),
                "top3_concentration": round(top3_volume_ratio, 2),
                "liquidity_grade": "优秀" if main_volume_ratio > 50 else "良好" if main_volume_ratio > 30 else "一般"
            }
        
        # 价差波动分析
        spread_analysis = {}
        if spreads:
            import numpy as np
            spread_analysis = {
                "spread_mean": np.mean(spreads),
                "spread_std": np.std(spreads),
                "spread_volatility": (np.std(spreads) / abs(np.mean(spreads)) * 100) if np.mean(spreads) != 0 else 0,
                "max_spread": max(spreads),
                "min_spread": min(spreads)
            }
        
        return {
            "structure_type": term_data.get("structure_type", "未知"),
            "near_price": near_price,
            "far_price": far_price,
            "absolute_spread": absolute_spread,
            "relative_spread": round(relative_spread, 2),
            "overall_slope": round(overall_slope, 4),
            "contract_count": len(contracts),
            "price_range": f"{min(prices):.2f} - {max(prices):.2f}",
            "liquidity_analysis": liquidity_analysis,
            "spread_analysis": spread_analysis,
            "structure_strength": self._assess_structure_strength(absolute_spread, relative_spread),
            "trend_direction": "上升趋势" if overall_slope > 0 else "下降趋势" if overall_slope < 0 else "平稳"
        }
    
    def _assess_structure_strength(self, absolute_spread: float, relative_spread: float) -> str:
        """评估结构强度"""
        if abs(relative_spread) > 5:
            return "极强"
        elif abs(relative_spread) > 2:
            return "强"
        elif abs(relative_spread) > 0.5:
            return "中等"
        else:
            return "弱"
    
    def _analyze_spread_patterns(self, real_data: Dict) -> Dict:
        """分析价差模式"""
        
        term_data = real_data.get("term_structure", {})
        if "error" in term_data:
            return {"error": "期限结构数据不可用"}
        
        contracts = term_data.get("contracts", [])
        prices = term_data.get("prices", [])
        volumes = term_data.get("volumes", [])
        spreads = term_data.get("spreads", [])
        
        if len(contracts) < 2:
            return {"error": "合约数量不足，无法分析价差"}
        
        # 价差分段分析（三段式）
        spread_segments = self._analyze_three_segment_spreads(contracts, prices, volumes)
        
        # 价差节奏分析
        rhythm_analysis = self._analyze_spread_rhythm(spreads)
        
        # 便利收益信号
        convenience_signals = self._analyze_convenience_yield_signals(spreads, volumes)
        
        return {
            "spread_segments": spread_segments,
            "rhythm_analysis": rhythm_analysis,
            "convenience_signals": convenience_signals,
            "overall_assessment": self._assess_spread_opportunities(spread_segments, rhythm_analysis)
        }
    
    def _analyze_three_segment_spreads(self, contracts: List[str], prices: List[float], volumes: List[float]) -> Dict:
        """三段式价差分析"""
        
        if len(contracts) < 3:
            return {"note": "合约数量不足，无法进行三段式分析"}
        
        # 识别主力合约（成交量最大）
        main_idx = volumes.index(max(volumes)) if volumes else 1
        
        # 近月-主力价差
        near_main_spread = prices[0] - prices[main_idx] if main_idx > 0 else 0
        
        # 主力-次主力价差
        if len(contracts) > 2:
            # 找到成交量第二大的合约
            sorted_vol_idx = sorted(enumerate(volumes), key=lambda x: x[1], reverse=True)
            second_main_idx = sorted_vol_idx[1][0] if len(sorted_vol_idx) > 1 else main_idx + 1
            main_second_spread = prices[main_idx] - prices[second_main_idx]
        else:
            main_second_spread = 0
        
        # 远月价差
        far_spread = prices[-2] - prices[-1] if len(prices) >= 2 else 0
        
        # 解释各段价差含义
        interpretations = {
            "near_main": self._interpret_near_main_spread(near_main_spread),
            "main_second": self._interpret_main_second_spread(main_second_spread),
            "far": self._interpret_far_spread(far_spread)
        }
        
        return {
            "near_main_spread": near_main_spread,
            "main_second_spread": main_second_spread,
            "far_spread": far_spread,
            "main_contract": contracts[main_idx] if main_idx < len(contracts) else "未知",
            "interpretations": interpretations
        }
    
    def _interpret_near_main_spread(self, spread: float) -> str:
        """解释近月-主力价差"""
        if spread > 50:
            return "现货库存紧张溢价明显，存在逼仓风险"
        elif spread > 0:
            return "现货相对紧张，近月有一定溢价"
        elif spread < -50:
            return "现货供应充足，近月贴水明显"
        else:
            return "现货供需相对平衡"
    
    def _interpret_main_second_spread(self, spread: float) -> str:
        """解释主力-次主力价差"""
        if spread > 20:
            return "市场预期供需矛盾加剧，适合正套"
        elif spread > 0:
            return "市场预期偏紧，可关注正套机会"
        elif spread < -20:
            return "市场预期供需矛盾缓解，适合反套"
        else:
            return "市场预期相对中性"
    
    def _interpret_far_spread(self, spread: float) -> str:
        """解释远月价差"""
        if abs(spread) > 30:
            return "远期故事活跃，注意快速反转风险"
        elif abs(spread) > 10:
            return "远期预期存在分歧"
        else:
            return "远期预期相对稳定"
    
    def _analyze_spread_rhythm(self, spreads: List[float]) -> Dict:
        """分析价差节奏"""
        
        if not spreads:
            return {"note": "缺少价差数据"}
        
        # 简单的节奏分析（需要历史数据支持）
        avg_spread = sum(spreads) / len(spreads)
        max_spread = max(spreads)
        min_spread = min(spreads)
        
        # 判断当前节奏
        if avg_spread > 0:
            current_rhythm = "近强远弱"
        elif avg_spread < 0:
            current_rhythm = "近弱远强"
        else:
            current_rhythm = "相对均衡"
        
        return {
            "current_rhythm": current_rhythm,
            "avg_spread": avg_spread,
            "spread_range": max_spread - min_spread,
            "note": "完整的节奏分析需要历史价差数据支持"
        }
    
    def _analyze_convenience_yield_signals(self, spreads: List[float], volumes: List[float]) -> Dict:
        """分析便利收益信号"""
        
        if not spreads or not volumes:
            return {"note": "数据不足"}
        
        near_spread = spreads[0] if spreads else 0
        near_volume = volumes[0] if volumes else 0
        total_volume = sum(volumes)
        
        # 便利收益信号判断
        if near_spread > 0 and near_volume / total_volume > 0.3:
            signal = "高便利收益信号"
        elif near_spread < 0:
            signal = "低便利收益信号"
        else:
            signal = "中性信号"
        
        return {
            "signal": signal,
            "near_spread": near_spread,
            "volume_concentration": near_volume / total_volume if total_volume > 0 else 0
        }
    
    def _assess_spread_opportunities(self, segments: Dict, rhythm: Dict) -> Dict:
        """评估价差交易机会"""
        
        opportunities = []
        risk_level = "中等"
        
        # 基于三段式分析
        if "near_main_spread" in segments:
            near_main = segments["near_main_spread"]
            if near_main > 50:
                opportunities.append("近月-主力反套机会")
                risk_level = "较高"
            elif near_main < -30:
                opportunities.append("近月-主力正套机会")
        
        if "main_second_spread" in segments:
            main_second = segments["main_second_spread"]
            if main_second > 20:
                opportunities.append("主力-次主力反套机会")
            elif main_second < -20:
                opportunities.append("主力-次主力正套机会")
        
        # 基于节奏分析
        current_rhythm = rhythm.get("current_rhythm", "")
        if "近强远弱" in current_rhythm:
            opportunities.append("关注价差收敛机会")
        elif "近弱远强" in current_rhythm:
            opportunities.append("关注价差扩大机会")
        
        return {
            "opportunities": opportunities,
            "risk_level": risk_level,
            "recommendation": "谨慎操作" if risk_level == "较高" else "可适度参与"
        }
    
    def _analyze_industry_structure(self, variety: str, real_data: Dict, external_data: Dict) -> Dict:
        """产业结构分析 - 新增模块"""
        
        variety_info = self.variety_config.get(variety, {})
        variety_type = variety_info.get("type", "未知")
        chinese_name = variety_info.get("chinese_name", "未知")
        
        # 基于品种类型的产业特征分析
        industry_characteristics = self._get_industry_characteristics(variety_type, chinese_name)
        
        # 结合外部搜索数据的产业分析
        supply_demand_analysis = {}
        if external_data and "supply_demand" in external_data:
            supply_results = external_data["supply_demand"].get("results", [])
            if supply_results:
                supply_demand_analysis = {
                    "data_available": True,
                    "search_results": supply_results,
                    "analysis_note": "基于外部搜索的供需数据分析"
                }
        
        return {
            "variety_type": variety_type,
            "industry_characteristics": industry_characteristics,
            "supply_demand_analysis": supply_demand_analysis,
            "structure_impact": self._analyze_structure_impact_factors(variety_type, real_data)
        }
    
    def _get_industry_characteristics(self, variety_type: str, chinese_name: str) -> Dict:
        """获取产业特征"""
        
        characteristics = {
            "农产品": {
                "seasonality": "强",
                "storage_cost": "中等",
                "convenience_yield": "高（收获季节）",
                "structure_tendency": "季节性Backwardation",
                "key_factors": ["天气", "种植面积", "库存消费比", "政策调控"]
            },
            "黑色金属": {
                "seasonality": "弱",
                "storage_cost": "低",
                "convenience_yield": "低",
                "structure_tendency": "Contango为主",
                "key_factors": ["钢厂利润", "库存水平", "基建需求", "环保政策"]
            },
            "有色金属": {
                "seasonality": "弱",
                "storage_cost": "低",
                "convenience_yield": "中等",
                "structure_tendency": "跟随宏观",
                "key_factors": ["美元指数", "库存", "下游需求", "矿山供应"]
            },
            "化工": {
                "seasonality": "中等",
                "storage_cost": "高",
                "convenience_yield": "中等",
                "structure_tendency": "Contango为主",
                "key_factors": ["原料成本", "装置检修", "下游需求", "环保限产"]
            },
            "能源化工": {
                "seasonality": "中等",
                "storage_cost": "高",
                "convenience_yield": "高",
                "structure_tendency": "Backwardation倾向",
                "key_factors": ["国际油价", "炼厂利润", "库存", "地缘政治"]
            }
        }
        
        return characteristics.get(variety_type, {
            "seasonality": "未知",
            "storage_cost": "未知",
            "convenience_yield": "未知",
            "structure_tendency": "未知",
            "key_factors": ["供需平衡", "库存水平", "宏观环境"]
        })
    
    def _analyze_structure_impact_factors(self, variety_type: str, real_data: Dict) -> Dict:
        """分析结构影响因素"""
        
        factors = {}
        
        # 库存因素
        inventory_data = real_data.get("inventory", {})
        if "error" not in inventory_data:
            inventory_percentile = inventory_data.get("historical_percentile", 50)
            factors["inventory_impact"] = {
                "level": "低库存" if inventory_percentile < 25 else "高库存" if inventory_percentile > 75 else "正常库存",
                "structure_bias": "支持Backwardation" if inventory_percentile < 25 else "支持Contango" if inventory_percentile > 75 else "中性"
            }
        
        # 基差因素
        basis_data = real_data.get("basis", {})
        if "error" not in basis_data:
            near_basis = basis_data.get("current_near_basis", 0)
            factors["basis_impact"] = {
                "level": "正基差" if near_basis > 0 else "负基差",
                "structure_bias": "支持Backwardation" if near_basis > 0 else "支持Contango"
            }
        
        return factors
    
    def _assess_risks(self, real_data: Dict, integrated_analysis: Dict) -> Dict:
        """风险评估"""
        
        risks = []
        risk_score = 0
        
        # 库存风险
        inventory_data = real_data.get("inventory", {})
        if "error" not in inventory_data:
            percentile = inventory_data.get("historical_percentile", 50)
            if percentile < 10:
                risks.append("极低库存风险")
                risk_score += 3
            elif percentile > 90:
                risks.append("高库存压力风险")
                risk_score += 2
        
        # 基差风险
        basis_data = real_data.get("basis", {})
        if "error" not in basis_data:
            near_basis = basis_data.get("current_near_basis", 0)
            if abs(near_basis) > 500:
                risks.append("基差异常风险")
                risk_score += 2
        
        # 流动性风险
        structure_data = integrated_analysis.get("structure_analysis", {})
        if "error" not in structure_data:
            liquidity = structure_data.get("liquidity_analysis", {})
            if liquidity.get("liquidity_grade") == "一般":
                risks.append("流动性风险")
                risk_score += 1
        
        # 确定风险等级
        if risk_score >= 5:
            risk_level = "高风险"
        elif risk_score >= 3:
            risk_level = "中等风险"
        elif risk_score >= 1:
            risk_level = "低风险"
        else:
            risk_level = "风险较小"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "identified_risks": risks,
            "recommendation": "谨慎操作" if risk_score >= 3 else "风险可控，可正常操作"
        }
    
    def _guess_variety_from_input(self, user_input: str) -> Optional[str]:
        """从用户输入猜测品种"""
        
        user_input_upper = user_input.upper()
        
        # 直接匹配品种代码
        if user_input_upper in self.variety_config:
            return user_input_upper
        
        # 中文名称匹配
        chinese_mapping = {
            '玉米': 'C', '豆粕': 'M', '菜籽粕': 'RM', '棉花': 'CF', '白糖': 'SR',
            '螺纹钢': 'RB', '铁矿石': 'I', '焦炭': 'J', '焦煤': 'JM',
            '沪铜': 'CU', '沪铝': 'AL', '沪锌': 'ZN', '沪铅': 'PB', '沪镍': 'NI', '沪锡': 'SN',
            '沪金': 'AU', '沪银': 'AG', '原油': 'SC', '燃料油': 'FU', '沥青': 'BU', '橡胶': 'RU',
            '聚乙烯': 'L', 'PVC': 'V', '聚丙烯': 'PP', '乙二醇': 'EG', '苯乙烯': 'EB',
            '液化石油气': 'PG', '纯碱': 'SA', '玻璃': 'FG', '甲醇': 'MA', 'PTA': 'TA',
            '短纤': 'PF', '花生': 'PK', '苹果': 'AP', '红枣': 'CJ', '生猪': 'LH', '鸡蛋': 'JD',
            '玉米淀粉': 'CS', '豆一': 'A', '豆二': 'B', '豆油': 'Y', '棕榈油': 'P',
            '菜籽油': 'OI', '菜籽': 'RS', '强麦': 'WH', '普麦': 'PM', '早籼稻': 'RI',
            '晚籼稻': 'LR', '粳稻': 'JR', '硅铁': 'SF', '锰硅': 'SM', '动力煤': 'ZC',
            '多晶硅': 'PS', '对二甲苯': 'PX', '国际铜': 'BC', '欧线集运': 'EC',
            '碳酸锂': 'LC', '工业硅': 'SI'
        }
        
        for chinese, code in chinese_mapping.items():
            if chinese in user_input:
                return code
        
        return None
    
    def _generate_all_charts(self, variety: str, real_data: Dict, integrated_analysis: Dict):
        """生成所有图表"""
        
        # 图1: 期限结构曲线图
        term_data = real_data.get("term_structure", {})
        if "error" not in term_data:
            chart1 = self._create_term_structure_chart(term_data, variety)
            self.charts_html.append({
                "id": 1,
                "title": f"图1: {variety}期货期限结构曲线图",
                "html": chart1
            })
        
        # 图2: 价差分析图
        if "error" not in term_data:
            chart2 = self._create_spread_analysis_chart(term_data, variety)
            self.charts_html.append({
                "id": 2,
                "title": f"图2: {variety}期货价差分析图",
                "html": chart2
            })
        
        # 图3: 库存分位数图
        inventory_data = real_data.get("inventory", {})
        if "error" not in inventory_data:
            chart3 = self._create_inventory_chart(inventory_data, variety)
            self.charts_html.append({
                "id": 3,
                "title": f"图3: {variety}库存历史分位数图",
                "html": chart3
            })
        
        # 图4: 风险评估雷达图
        risk_data = integrated_analysis.get("risk_assessment", {})
        if "error" not in risk_data:
            chart4 = self._create_risk_assessment_chart(risk_data, variety)
            self.charts_html.append({
                "id": 4,
                "title": f"图4: {variety}期货风险评估雷达图",
                "html": chart4
            })
    
    def _create_term_structure_chart(self, term_data: Dict, variety: str):
        """创建期限结构图表"""
        try:
            contracts = term_data.get("contracts", [])
            prices = term_data.get("prices", [])
            volumes = term_data.get("volumes", [])
            
            if not contracts or not prices:
                return "<p>期限结构数据不足</p>"
            
            # 创建Plotly图表
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('期限结构曲线', '成交量分布'),
                vertical_spacing=0.15,
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            # 期限结构曲线
            fig.add_trace(
                go.Scatter(
                    x=contracts, 
                    y=prices,
                    mode='lines+markers',
                    name='期限结构',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ),
                row=1, col=1
            )
            
            # 成交量柱状图
            if volumes:
                fig.add_trace(
                    go.Bar(
                        x=contracts,
                        y=volumes,
                        name='成交量',
                        marker_color='#ff7f0e',
                        opacity=0.7
                    ),
                    row=2, col=1
                )
            
            # 更新布局
            fig.update_layout(
                title=f'{variety}期货期限结构分析图',
                height=600,
                showlegend=True,
                template='plotly_white',
                font=dict(family="Microsoft YaHei", size=12)
            )
            
            fig.update_xaxes(title_text="合约", row=1, col=1)
            fig.update_yaxes(title_text="价格 (元/吨)", row=1, col=1)
            fig.update_xaxes(title_text="合约", row=2, col=1)
            fig.update_yaxes(title_text="成交量 (手)", row=2, col=1)
            
            # 返回Plotly对象而不是HTML字符串
            return fig
            
        except Exception as e:
            return f'<p style="color: red;">图表生成失败: {str(e)}</p>'
    
    def _create_spread_analysis_chart(self, term_data: Dict, variety: str):
        """创建价差分析图表"""
        try:
            spreads = term_data.get("spreads", [])
            contracts = term_data.get("contracts", [])
            
            if not spreads or len(spreads) < 1:
                return "<p>价差数据不足</p>"
            
            # 创建价差图表
            fig = go.Figure()
            
            # 价差柱状图
            spread_labels = [f"{contracts[i]}-{contracts[i+1]}" for i in range(len(spreads))] if len(contracts) > len(spreads) else [f"价差{i+1}" for i in range(len(spreads))]
            
            colors = ['red' if spread < 0 else 'green' for spread in spreads]
            
            fig.add_trace(
                go.Bar(
                    x=spread_labels,
                    y=spreads,
                    name='价差',
                    marker_color=colors,
                    opacity=0.8
                )
            )
            
            # 添加零线
            fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
            
            # 更新布局
            fig.update_layout(
                title=f'{variety}期货价差分析图',
                xaxis_title="合约价差",
                yaxis_title="价差 (元/吨)",
                height=400,
                template='plotly_white',
                font=dict(family="Microsoft YaHei", size=12)
            )
            
            # 返回Plotly对象而不是HTML字符串
            return fig
            
        except Exception as e:
            return f'<p style="color: red;">价差图表生成失败: {str(e)}</p>'
    
    def _create_inventory_chart(self, inventory_data: Dict, variety: str):
        """创建库存分析图表"""
        try:
            if "error" in inventory_data:
                return "<p>库存数据不可用</p>"
            
            # 获取库存数据
            inventory_percentile = inventory_data.get("historical_percentile", 0)
            
            # 创建库存分位数图表
            fig = go.Figure()
            
            # 添加库存分位数指示器
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=inventory_percentile,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': f"{variety}库存历史分位数"},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 25], 'color': "lightgray"},
                            {'range': [25, 75], 'color': "gray"},
                            {'range': [75, 100], 'color': "darkgray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': inventory_percentile
                        }
                    }
                )
            )
            
            fig.update_layout(
                height=300,
                font=dict(family="Microsoft YaHei", size=12)
            )
            
            # 返回Plotly对象而不是HTML字符串
            return fig
            
        except Exception as e:
            return f'<p style="color: red;">库存图表生成失败: {str(e)}</p>'
    
    def _create_risk_assessment_chart(self, risk_data: Dict, variety: str):
        """创建风险评估图表"""
        try:
            if "error" in risk_data:
                return "<p>风险数据不可用</p>"
            
            risk_score = risk_data.get("risk_score", 0)
            
            # 创建风险评估雷达图
            categories = ['市场风险', '流动性风险', '基差风险', '库存风险', '政策风险']
            
            # 基于风险评分生成各维度风险值
            base_risk = risk_score / 10 * 10
            values = [
                base_risk,  # 市场风险
                3,  # 流动性风险
                4,  # 基差风险
                8 if "极低库存风险" in risk_data.get("identified_risks", []) else 2,  # 库存风险
                3   # 政策风险
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=f'{variety}风险评估',
                line_color='red' if risk_score > 6 else 'orange' if risk_score > 3 else 'green'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 10]
                    )),
                title=f"{variety}期货风险评估雷达图",
                height=400,
                font=dict(family="Microsoft YaHei", size=12)
            )
            
            # 返回Plotly对象而不是HTML字符串
            return fig
            
        except Exception as e:
            return f'<p style="color: red;">风险图表生成失败: {str(e)}</p>'
    
    def _generate_complete_report(self, variety: str, chinese_name: str, integrated_analysis: Dict, real_data: Dict, model_mode: str) -> str:
        """生成完整专业报告"""
        
        try:
            # 构建完整的提示词
            prompt = self._build_complete_prompt(variety, chinese_name, integrated_analysis, real_data)
            
            # 调用AI生成报告
            if model_mode == "reasoner":
                model_name = "deepseek-reasoner"
            else:
                model_name = "deepseek-chat"
            
            print(f"    🤖 调用{model_name}模型生成完整专业报告...")
            
            headers = {
                'Authorization': f'Bearer {self.deepseek_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 8192,
                'stream': False
            }
            
            response = requests.post(self.deepseek_url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    ai_content = result['choices'][0]['message']['content']
                    return ai_content
                else:
                    return "AI响应格式异常"
            else:
                return f"AI API调用失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"报告生成失败: {str(e)}"
    
    def _build_complete_prompt(self, variety: str, chinese_name: str, integrated_analysis: Dict, real_data: Dict) -> str:
        """构建完整的AI提示词"""
        
        # 获取外部数据引用标记
        reference_marks = []
        external_data = integrated_analysis.get("external_data", {})
        for data_type in ["exchange_fees", "industry_news", "market_outlook", "supply_demand"]:
            if data_type in external_data:
                results = external_data[data_type].get("results", [])
                for result in results:
                    if "reference" in result:
                        reference_marks.append(result["reference"])
        
        prompt = f"""
请为{chinese_name}({variety})期货生成一份专业的期限结构分析报告。

报告要求：
1. 不使用任何Markdown格式符号（如#、**等）
2. 在文段中必须引用对应的图表（图1、图2、图3、图4）
3. 在文段中必须标注外部搜索信息的引用：{reference_marks}
4. 报告结构必须包含以下完整内容：

第一部分：期限结构现状分析
- 当前结构类型和特征
- 必须引用"如图1期限结构曲线图所示"
- 价格分布和成交量特征分析
- 必须引用"从图2价差分析图可以看出"

第二部分：Full Carry理论验证
- Full Carry概念解释和理论分析
- 基于真实交易所费用数据的计算（如有搜索到的费用信息，必须标注引用）
- 实际价差与理论价差的偏离分析
- 套利机会识别

第三部分：Convenience Yield深度解读
- Convenience Yield概念解释
- 必须引用"结合图3库存分位数图"
- 库存水平对便利收益的影响
- 对期限结构的作用机制

第四部分：价差分析与产业结构
- 三段式价差分析（近月-主力、主力-次主力、远月）
- 产业结构特征对期限结构的影响
- 基于品种特性的结构解释

第五部分：风险评估与操作建议
- 必须引用"图4风险评估雷达图表明"
- 多维度风险分析
- 具体操作建议（正套/反套/观望）

写作风格要求：
1. 使用专业分析师语言："我们认为"、"值得注意的是"、"建议关注"
2. 每段不超过150字，逻辑清晰
3. 每个分析都要回答"对投资有什么意义"
4. 数据来源必须明确标注
5. 外部搜索信息必须用引用标记{reference_marks}标注

可用数据：
{self._format_complete_data(integrated_analysis, real_data)}

请严格按照以上要求生成报告，确保图表引用和外部信息标注准确。
"""
        
        return prompt
    
    def _format_complete_data(self, integrated_analysis: Dict, real_data: Dict) -> str:
        """格式化完整数据用于AI分析"""
        
        formatted_data = ""
        
        # 数据质量
        data_quality = integrated_analysis.get("data_quality", {})
        formatted_data += f"数据质量: {data_quality.get('quality_level', '未知')} ({data_quality.get('quality_percentage', 0)}%)\n"
        
        # 期限结构分析
        structure_analysis = integrated_analysis.get("structure_analysis", {})
        if "error" not in structure_analysis:
            formatted_data += f"期限结构类型: {structure_analysis.get('structure_type', '未知')}\n"
            formatted_data += f"近月价格: {structure_analysis.get('near_price', 0):.2f}元/吨\n"
            formatted_data += f"远月价格: {structure_analysis.get('far_price', 0):.2f}元/吨\n"
            formatted_data += f"绝对价差: {structure_analysis.get('absolute_spread', 0):.2f}元/吨\n"
            formatted_data += f"相对价差: {structure_analysis.get('relative_spread', 0):.2f}%\n"
        
        # Full Carry分析
        full_carry = integrated_analysis.get("full_carry_analysis", {})
        if "status" in full_carry:
            formatted_data += f"Full Carry状态: {full_carry.get('status', '未知')}\n"
            if full_carry.get("search_result"):
                search_result = full_carry["search_result"]
                formatted_data += f"交易所费用搜索结果: {search_result.get('title', '')} - {search_result.get('reference', '')}\n"
        
        # 便利收益分析
        convenience_yield = integrated_analysis.get("convenience_yield_analysis", {})
        if "status" in convenience_yield:
            formatted_data += f"便利收益状态: {convenience_yield.get('status', '未知')}\n"
            if "inventory_percentile" in convenience_yield:
                formatted_data += f"库存分位数: {convenience_yield.get('inventory_percentile', 0):.2f}%\n"
                formatted_data += f"库存信号: {convenience_yield.get('inventory_signal', '未知')}\n"
        
        # 价差分析
        spread_analysis = integrated_analysis.get("spread_analysis", {})
        if "error" not in spread_analysis:
            segments = spread_analysis.get("spread_segments", {})
            if segments:
                formatted_data += f"近月-主力价差: {segments.get('near_main_spread', 0):.2f}元/吨\n"
                formatted_data += f"主力-次主力价差: {segments.get('main_second_spread', 0):.2f}元/吨\n"
                formatted_data += f"主力合约: {segments.get('main_contract', '未知')}\n"
        
        # 产业分析
        industry_analysis = integrated_analysis.get("industry_analysis", {})
        if "error" not in industry_analysis:
            formatted_data += f"品种类型: {industry_analysis.get('variety_type', '未知')}\n"
            characteristics = industry_analysis.get("industry_characteristics", {})
            if characteristics:
                formatted_data += f"季节性: {characteristics.get('seasonality', '未知')}\n"
                formatted_data += f"仓储成本: {characteristics.get('storage_cost', '未知')}\n"
                formatted_data += f"便利收益特征: {characteristics.get('convenience_yield', '未知')}\n"
        
        # 风险评估
        risk_assessment = integrated_analysis.get("risk_assessment", {})
        formatted_data += f"风险等级: {risk_assessment.get('risk_level', '未知')}\n"
        formatted_data += f"风险评分: {risk_assessment.get('risk_score', 0)}\n"
        identified_risks = risk_assessment.get("identified_risks", [])
        if identified_risks:
            formatted_data += f"主要风险: {', '.join(identified_risks)}\n"
        
        # 外部数据
        external_data = integrated_analysis.get("external_data", {})
        if external_data and "error" not in external_data:
            formatted_data += "外部搜索数据: 已获取交易所费用、行业新闻、市场展望、供需数据\n"
        
        return formatted_data
    
    def _display_complete_report(self, variety: str, chinese_name: str, analysis_date: str, model_mode: str, report: str):
        """显示完整报告"""
        
        # 显示报告标题
        title_html = f"""
        <div style='text-align: center; margin: 30px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; border-radius: 15px;'>
            <h1 style='color: white; font-size: 28px; margin-bottom: 10px;'>
                📊 {chinese_name}({variety}) 期限结构AI分析报告
            </h1>
            <p style='color: #f8f9fa; font-size: 16px; margin: 0;'>
                分析时间: {analysis_date} | 模型: {model_mode} | 终极专业版本
            </p>
        </div>
        """
        display(HTML(title_html))
        
        # 显示图表组合
        self._display_chart_combination()
        
        # 显示AI分析报告
        self._display_final_report(report)
        
        # 显示引用列表
        self._display_references()
    
    def _display_chart_combination(self):
        """显示图表组合"""
        
        display(HTML("<h3 style='color: #2c3e50; margin-top: 30px;'>📊 专业图表分析组合</h3>"))
        
        for chart in self.charts_html:
            display(HTML(f"<h4 style='color: #34495e;'>{chart['title']}</h4>"))
            # 检查是否是Plotly对象
            if hasattr(chart['html'], 'show'):
                # 如果是Plotly对象，直接显示
                chart['html'].show()
            elif isinstance(chart['html'], str):
                # 如果是HTML字符串，使用HTML显示
                display(HTML(chart['html']))
            else:
                # 其他情况，尝试转换为HTML
                display(HTML(str(chart['html'])))
    
    def _display_final_report(self, report: str):
        """显示最终报告"""
        
        # 清理报告内容，移除Markdown符号
        clean_report = self._clean_markdown_symbols(report)
        
        report_html = f"""
        <div style='background: white; padding: 30px; border-radius: 15px; 
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin: 30px 0;
                    border-left: 5px solid #3498db;'>
            <h3 style='color: #2c3e50; margin-bottom: 20px; font-size: 24px;'>
                🤖 AI深度分析报告（终极专业版）
            </h3>
            <div style='line-height: 1.8; font-size: 15px; color: #2c3e50;'>
                {self._format_report_content(clean_report)}
            </div>
        </div>
        """
        
        display(HTML(report_html))
    
    def _clean_markdown_symbols(self, text: str) -> str:
        """清理Markdown符号"""
        # 移除标题符号
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        # 移除粗体符号
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # 移除斜体符号
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        return text
    
    def _format_report_content(self, content: str) -> str:
        """格式化报告内容"""
        # 将换行符转换为HTML格式
        content = content.replace('\n\n', '</p><p style="margin: 15px 0;">')
        content = content.replace('\n', '<br>')
        
        # 添加段落标签
        if not content.startswith('<p'):
            content = '<p style="margin: 15px 0;">' + content
        if not content.endswith('</p>'):
            content = content + '</p>'
        
        return content
    
    def _display_references(self):
        """显示引用列表"""
        
        if not self.references:
            return
        
        reference_html = """
        <div style='background: #f8f9fa; padding: 25px; border-radius: 15px; 
                    margin: 30px 0; border: 1px solid #e9ecef;'>
            <h3 style='color: #495057; margin-bottom: 20px;'>📚 参考资料与数据来源</h3>
            <p style='color: #6c757d; margin-bottom: 20px;'>本报告中标注的网络搜索信息来源如下：</p>
        """
        
        for ref in self.references:
            reference_html += f"""
            <div style='margin-bottom: 15px; padding: 15px; background: white; 
                        border-radius: 8px; border-left: 3px solid #007bff;'>
                <p style='margin: 0; font-weight: bold; color: #007bff;'>{ref['mark']} {ref['title']}</p>
                <p style='margin: 5px 0; color: #6c757d; font-size: 14px;'>
                    链接：<a href="{ref['link']}" target="_blank" style='color: #007bff;'>{ref['link']}</a>
                </p>
                {f"<p style='margin: 5px 0; color: #495057; font-size: 13px;'>摘要：{ref['snippet'][:200]}...</p>" if ref['snippet'] else ""}
            </div>
            """
        
        reference_html += f"""
            <hr style='margin: 20px 0; border: none; height: 1px; background: #dee2e6;'>
            <p style='text-align: center; color: #6c757d; font-style: italic; margin: 0;'>
                共引用 {len(self.references)} 个外部数据源
            </p>
        </div>
        """
        
        display(HTML(reference_html))
    
    def show_supported_varieties(self):
        """显示支持的品种列表"""
        print("\n📊 支持的期货品种:")
        print("="*60)
        
        # 按类型分组显示
        type_groups = {}
        for code, info in self.variety_config.items():
            variety_type = info["type"]
            if variety_type not in type_groups:
                type_groups[variety_type] = []
            type_groups[variety_type].append((code, info["chinese_name"], info["exchange"]))
        
        for variety_type, varieties in type_groups.items():
            print(f"\n📋 {variety_type}:")
            for code, name, exchange in varieties:
                print(f"  {code:4s} - {name:8s} ({exchange})")
        
        print(f"\n💡 输入品种代码开始分析")

def main():
    """主函数 - 启动交互式分析"""
    
    # 创建分析器
    analyzer = UltimateTermStructureAnalyzer()
    
    # 启动交互式分析
    analyzer.start_interactive_analysis()

if __name__ == "__main__":
    main()
