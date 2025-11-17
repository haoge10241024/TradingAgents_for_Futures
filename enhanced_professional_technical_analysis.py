#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版专业技术分析系统
- 专业研究报告行文风格
- 集成专业图表到报告中
- 确保数据真实性和来源标注
"""

import pandas as pd
import numpy as np
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import warnings
import time
from typing import Dict, List, Tuple, Optional, Any
import sys
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from IPython.display import display, HTML
import base64
from io import BytesIO

warnings.filterwarnings('ignore')

# 项目路径配置
BASE_DIR = Path(r"D:\Cursor\cursor项目\TradingAgent")
TECHNICAL_ROOT = BASE_DIR / "qihuo" / "database" / "technical_analysis"
OUTPUT_DIR = BASE_DIR / "qihuo" / "output" / "enhanced_technical_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API配置
DEEPSEEK_API_KEY = "sk-293dec7fabb54606b4f8d4f606da3383"
DEEPSEEK_API_URL = "https://api.deepseek.com"
SERPER_API_KEY = "04555ec0f2ce150d1cb628c7a80e2e433e193535"
SERPER_API_URL = "https://google.serper.dev/search"

# 期货品种配置
SYMBOL_NAMES = {
    "RB": "螺纹钢", "HC": "热轧卷板", "I": "铁矿石", "J": "焦炭", "JM": "焦煤", "SS": "不锈钢",
    "CU": "沪铜", "AL": "沪铝", "ZN": "沪锌", "NI": "沪镍", "SN": "沪锡", "PB": "沪铅", "AO": "氧化铝",
    "AU": "黄金", "AG": "白银", "RU": "橡胶", "NR": "20号胶", "BU": "沥青", "FU": "燃料油",
    "LU": "低硫燃料油", "PG": "液化石油气", "EB": "苯乙烯", "EG": "乙二醇", "MA": "甲醇", 
    "TA": "PTA", "PX": "对二甲苯", "PL": "聚烯烃", "PF": "短纤", "CY": "PVC", "PR": "丙烯", "SC": "原油",
    "SR": "白糖", "CF": "棉花", "AP": "苹果", "CJ": "红枣", "SP": "纸浆", "P": "棕榈油",
    "Y": "豆油", "M": "豆粕", "RM": "菜粕", "OI": "菜籽油", "RS": "菜籽", "PK": "花生",
    "A": "豆一", "B": "豆二", "C": "玉米", "CS": "玉米淀粉", "JD": "鸡蛋", "LH": "生猪",
    "FG": "玻璃", "SA": "纯碱", "L": "聚乙烯", "PP": "聚丙烯", "V": "PVC", "UR": "尿素",
    "SF": "硅铁", "SM": "锰硅"
}

class EnhancedProfessionalTechnicalAnalyzer:
    """增强版专业技术分析器 - 集成专业图表和报告"""
    
    def __init__(self, deepseek_key: str = DEEPSEEK_API_KEY, serper_key: str = SERPER_API_KEY):
        self.deepseek_key = deepseek_key
        self.serper_key = serper_key
        self.charts = {}  # 存储生成的图表
        self.external_citations = []  # 存储外部引用
    
    def load_technical_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """加载技术分析数据"""
        try:
            symbol_dir = TECHNICAL_ROOT / symbol
            
            # 检查数据文件
            tech_file = symbol_dir / "technical_indicators.csv"
            ohlc_file = symbol_dir / "ohlc_data.csv"
            
            if not tech_file.exists() or not ohlc_file.exists():
                print(f"❌ {symbol} 技术数据文件不存在")
                return None
            
            # 加载并合并数据
            df_tech = pd.read_csv(tech_file)
            df_ohlc = pd.read_csv(ohlc_file)
            
            # 处理日期字段
            if '时间' in df_tech.columns:
                df_tech['date'] = pd.to_datetime(df_tech['时间'])
            if '时间' in df_ohlc.columns:
                df_ohlc['date'] = pd.to_datetime(df_ohlc['时间'])
            
            # 标准化OHLC列名
            ohlc_mapping = {
                '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close',
                '成交量': 'volume', '持仓量': 'open_interest'
            }
            df_ohlc = df_ohlc.rename(columns=ohlc_mapping)
            
            # 合并数据
            df = pd.merge(df_ohlc, df_tech, on='date', how='inner')
            df = df.sort_values('date').reset_index(drop=True)
            
            # 取最近60个交易日
            df_recent = df.tail(60).copy()
            
            print(f"✅ {symbol} 本地数据加载成功: {len(df_recent)}条记录")
            return df_recent
            
        except Exception as e:
            print(f"❌ 加载 {symbol} 数据失败: {e}")
            return None
    
    def search_market_info(self, query: str, max_results: int = 5) -> List[Dict]:
        """搜索市场信息并记录引用"""
        try:
            headers = {
                'X-API-KEY': self.serper_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'q': query,
                'num': max_results,
                'hl': 'zh-cn',
                'gl': 'cn'
            }
            
            response = requests.post(SERPER_API_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                market_info = []
                
                for i, result in enumerate(results.get('organic', [])[:max_results], 1):
                    info = {
                        'title': result.get('title', ''),
                        'snippet': result.get('snippet', ''),
                        'link': result.get('link', ''),
                        'citation_id': f"[{i}]"
                    }
                    market_info.append(info)
                    
                    # 记录外部引用
                    self.external_citations.append({
                        'id': f"[{i}]",
                        'title': result.get('title', ''),
                        'url': result.get('link', ''),
                        'source': 'Serper搜索'
                    })
                
                print(f"✅ 搜索到 {len(market_info)} 条市场信息")
                return market_info
            else:
                print(f"❌ 搜索失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 搜索市场信息失败: {e}")
            return []
    
    def create_professional_charts(self, df: pd.DataFrame, symbol: str, comprehensive_data: Dict) -> Dict[str, Any]:
        """创建专业技术分析图表"""
        charts = {}
        
        try:
            # 图表1: K线图与技术指标
            fig1 = make_subplots(
                rows=4, cols=1,
                subplot_titles=(
                    f'{SYMBOL_NAMES.get(symbol, symbol)}价格走势与均线系统',
                    'MACD动量指标',
                    'RSI相对强弱指标',
                    '成交量分析'
                ),
                vertical_spacing=0.05,
                row_heights=[0.4, 0.2, 0.2, 0.2],
                specs=[[{"secondary_y": False}],
                       [{"secondary_y": False}],
                       [{"secondary_y": False}],
                       [{"secondary_y": False}]]
            )
            
            # K线图
            fig1.add_trace(
                go.Candlestick(
                    x=df['date'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='K线',
                    increasing_line_color='red',
                    decreasing_line_color='green'
                ),
                row=1, col=1
            )
            
            # 添加均线
            for ma in ['MA5', 'MA20', 'MA60']:
                if ma in df.columns:
                    fig1.add_trace(
                        go.Scatter(
                            x=df['date'],
                            y=df[ma],
                            mode='lines',
                            name=ma,
                            line=dict(width=1)
                        ),
                        row=1, col=1
                    )
            
            # MACD
            if 'MACD' in df.columns:
                fig1.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['MACD'],
                        mode='lines',
                        name='MACD',
                        line=dict(color='blue')
                    ),
                    row=2, col=1
                )
                
                if 'MACD_SIGNAL' in df.columns:
                    fig1.add_trace(
                        go.Scatter(
                            x=df['date'],
                            y=df['MACD_SIGNAL'],
                            mode='lines',
                            name='MACD信号线',
                            line=dict(color='red', dash='dash')
                        ),
                        row=2, col=1
                    )
            
            # RSI
            if 'RSI14' in df.columns:
                fig1.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['RSI14'],
                        mode='lines',
                        name='RSI14',
                        line=dict(color='purple')
                    ),
                    row=3, col=1
                )
                
                # 添加超买超卖线
                fig1.add_hline(y=70, line_dash="dash", line_color="red", 
                              annotation_text="超买线(70)", row=3, col=1)
                fig1.add_hline(y=30, line_dash="dash", line_color="green", 
                              annotation_text="超卖线(30)", row=3, col=1)
            
            # 成交量
            fig1.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['volume'],
                    name='成交量',
                    marker_color='lightblue'
                ),
                row=4, col=1
            )
            
            fig1.update_layout(
                title=f'{SYMBOL_NAMES.get(symbol, symbol)}({symbol}) 技术分析综合图表',
                height=800,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            # 保存图表对象
            charts['technical_overview'] = fig1
            
            # 图表2: 支撑阻力分析
            fig2 = go.Figure()
            
            # 价格线
            fig2.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['close'],
                    mode='lines',
                    name='收盘价',
                    line=dict(color='black', width=2)
                )
            )
            
            # 支撑阻力位
            support = comprehensive_data.get('support_resistance', {}).get('support', 0)
            resistance = comprehensive_data.get('support_resistance', {}).get('resistance', 0)
            
            if support > 0:
                fig2.add_hline(
                    y=support,
                    line_dash="solid",
                    line_color="green",
                    annotation_text=f"支撑位: {support}"
                )
            
            if resistance > 0:
                fig2.add_hline(
                    y=resistance,
                    line_dash="solid", 
                    line_color="red",
                    annotation_text=f"阻力位: {resistance}"
                )
            
            fig2.update_layout(
                title=f'{SYMBOL_NAMES.get(symbol, symbol)} 支撑阻力分析',
                height=400,
                xaxis_title='日期',
                yaxis_title='价格'
            )
            
            charts['support_resistance'] = fig2
            
            # 图表3: 持仓量与价格关系
            if 'open_interest' in df.columns:
                fig3 = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('价格走势', '持仓量变化'),
                    vertical_spacing=0.1
                )
                
                fig3.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['close'],
                        mode='lines',
                        name='收盘价',
                        line=dict(color='blue')
                    ),
                    row=1, col=1
                )
                
                fig3.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df['open_interest'],
                        mode='lines',
                        name='持仓量',
                        line=dict(color='orange')
                    ),
                    row=2, col=1
                )
                
                fig3.update_layout(
                    title=f'{SYMBOL_NAMES.get(symbol, symbol)} 持仓量与价格关系分析',
                    height=500
                )
                
                charts['oi_price_analysis'] = fig3
            
            print(f"✅ 生成 {len(charts)} 个专业图表")
            return charts
            
        except Exception as e:
            print(f"❌ 创建图表失败: {e}")
            return {}
    
    def call_deepseek_reasoner(self, messages: List[Dict], max_tokens: int = 8000) -> Tuple[str, str]:
        """调用DeepSeek Reasoner"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.deepseek_key,
                base_url=DEEPSEEK_API_URL
            )
            
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.1,
                stream=False
            )
            
            message = response.choices[0].message
            reasoning_content = message.reasoning_content if hasattr(message, 'reasoning_content') else ""
            final_answer = message.content
            
            return reasoning_content, final_answer
            
        except Exception as e:
            print(f"❌ DeepSeek调用失败: {e}")
            return "", ""
    
    def generate_enhanced_analysis_prompt(self, comprehensive_data: Dict, market_info: List[Dict]) -> str:
        """生成增强版分析提示词"""
        
        # 构建市场信息部分
        market_context = ""
        if market_info:
            market_context = "\n\n【市场背景信息】\n"
            for info in market_info:
                market_context += f"{info['citation_id']} {info['title']}: {info['snippet']}\n"
        
        prompt = f"""
作为资深期货技术分析专家，请基于以下真实数据进行专业的技术分析报告。

【核心技术数据】
品种: {comprehensive_data['symbol_name']}({comprehensive_data['symbol']})
当前价格: {comprehensive_data['current_price']}
价格变化: 5日{comprehensive_data['price_change_5d']}%, 20日{comprehensive_data['price_change_20d']}%

技术指标数据:
- RSI14: {comprehensive_data['rsi']}
- MACD: {comprehensive_data['macd']} (信号线: {comprehensive_data['macd_signal']})
- 均线系统: MA5({comprehensive_data['ma5']}) MA20({comprehensive_data['ma20']}) MA60({comprehensive_data['ma60']})
- 布林带: 上轨{comprehensive_data['bb_upper']} 中轨{comprehensive_data['bb_middle']} 下轨{comprehensive_data['bb_lower']}
- ATR14: {comprehensive_data['atr']}
- 成交量: {comprehensive_data['volume']} (20日均量: {comprehensive_data['volume_ma20']})
- 持仓量: {comprehensive_data['open_interest']}

综合分析结果:
- 趋势评分: {comprehensive_data['trend_analysis']['trend_score']}/100
- 动量评分: {comprehensive_data['momentum_analysis']['momentum_score']}/100
- 均线排列: {comprehensive_data['trend_analysis']['ma_alignment']}
- 量价关系: {comprehensive_data['volume_analysis']['volume_price_relation']}
- 风险等级: {comprehensive_data['risk_assessment']['overall_risk']}
{market_context}

【报告要求】
请按照专业研究报告的格式撰写技术分析报告，具备以下特点:

1. 行文专业且具可读性，避免使用markdown符号
2. 结构清晰，逻辑严谨
3. 基于真实数据进行分析，不编造信息
4. 在适当位置提及"如图X所示"来引用图表
5. 如使用市场信息，请标注引用编号

报告结构:
一、市场概况与价格表现
二、技术指标深度解析 (如图1所示)
三、趋势分析与方向判断
四、支撑阻力位分析 (如图2所示)  
五、资金流向与持仓分析 (如图3所示)
六、风险评估与操作建议
七、后市展望

请确保每个部分都有具体的数据支撑和专业的分析判断。
"""
        return prompt
    
    def extract_comprehensive_data(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """提取综合技术数据"""
        if df.empty:
            return {}
        
        try:
            latest = df.iloc[-1]
            prev_5 = df.iloc[-6] if len(df) >= 6 else df.iloc[0]
            prev_20 = df.iloc[-21] if len(df) >= 21 else df.iloc[0]
            
            def safe_get(series, key, default=0):
                try:
                    value = series.get(key, default)
                    return round(float(value), 2) if pd.notna(value) and value != 0 else default
                except:
                    return default
            
            # 基础价格数据
            current_price = latest['close']
            price_change_5d = ((current_price - prev_5['close']) / prev_5['close'] * 100) if prev_5['close'] > 0 else 0
            price_change_20d = ((current_price - prev_20['close']) / prev_20['close'] * 100) if prev_20['close'] > 0 else 0
            
            # 趋势分析
            trend_analysis = self.analyze_trend_comprehensive(df)
            momentum_analysis = self.analyze_momentum_comprehensive(df)
            support_resistance = self.identify_key_levels(df)
            volume_analysis = self.analyze_volume_comprehensive(df)
            risk_assessment = self.assess_risk_levels(df)
            
            comprehensive_data = {
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol, symbol),
                "latest_date": latest['date'].strftime('%Y-%m-%d'),
                "current_price": round(current_price, 2),
                "price_change_5d": round(price_change_5d, 2),
                "price_change_20d": round(price_change_20d, 2),
                
                # OHLC数据
                "open": round(latest['open'], 2),
                "high": round(latest['high'], 2),
                "low": round(latest['low'], 2),
                "volume": int(latest['volume']) if pd.notna(latest['volume']) else 0,
                "open_interest": int(latest['open_interest']) if pd.notna(latest['open_interest']) else 0,
                
                # 技术指标
                "ma5": safe_get(latest, 'MA5'),
                "ma20": safe_get(latest, 'MA20'),
                "ma60": safe_get(latest, 'MA60'),
                "rsi": safe_get(latest, 'RSI14'),
                "macd": safe_get(latest, 'MACD'),
                "macd_signal": safe_get(latest, 'MACD_SIGNAL'),
                "bb_upper": safe_get(latest, 'BOLL_UP'),
                "bb_middle": safe_get(latest, 'BOLL_MID'),
                "bb_lower": safe_get(latest, 'BOLL_LOW'),
                "atr": safe_get(latest, 'ATR14'),
                "volume_ma20": safe_get(latest, 'VOL_MA20'),
                
                # 分析结果
                "trend_analysis": trend_analysis,
                "momentum_analysis": momentum_analysis,
                "support_resistance": support_resistance,
                "volume_analysis": volume_analysis,
                "risk_assessment": risk_assessment,
            }
            
            return comprehensive_data
            
        except Exception as e:
            print(f"❌ 提取综合数据失败: {e}")
            return {}
    
    def analyze_trend_comprehensive(self, df: pd.DataFrame) -> Dict[str, Any]:
        """综合趋势分析"""
        try:
            latest = df.iloc[-1]
            
            # 多时间框架趋势
            short_trend = self.calculate_trend_strength(df.tail(5))
            medium_trend = self.calculate_trend_strength(df.tail(20))
            long_trend = self.calculate_trend_strength(df.tail(60))
            
            # 均线排列
            ma5, ma20, ma60 = latest.get('MA5', 0), latest.get('MA20', 0), latest.get('MA60', 0)
            price = latest['close']
            
            if ma5 > ma20 > ma60 and price > ma5:
                ma_alignment = "多头排列"
                trend_score = 80 + short_trend * 0.2
            elif ma5 < ma20 < ma60 and price < ma5:
                ma_alignment = "空头排列"
                trend_score = 20 - short_trend * 0.2
            else:
                ma_alignment = "震荡整理"
                trend_score = 50
            
            return {
                "short_trend": short_trend,
                "medium_trend": medium_trend,
                "long_trend": long_trend,
                "ma_alignment": ma_alignment,
                "trend_score": max(0, min(100, trend_score))
            }
        except:
            return {"error": "趋势分析失败"}
    
    def calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """计算趋势强度"""
        if len(df) < 2:
            return 0
        
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
        return max(-100, min(100, price_change))
    
    def analyze_momentum_comprehensive(self, df: pd.DataFrame) -> Dict[str, Any]:
        """综合动量分析"""
        try:
            latest = df.iloc[-1]
            
            rsi = latest.get('RSI14', 50)
            macd = latest.get('MACD', 0)
            macd_signal = latest.get('MACD_SIGNAL', 0)
            
            # RSI状态
            if rsi > 70:
                rsi_status = "超买"
            elif rsi < 30:
                rsi_status = "超卖"
            else:
                rsi_status = "正常"
            
            # MACD状态
            if macd > macd_signal:
                macd_status = "金叉"
            else:
                macd_status = "死叉"
            
            # 动量评分
            momentum_score = (rsi + (50 if macd > macd_signal else -50) + 50) / 2
            
            return {
                "rsi_value": rsi,
                "rsi_status": rsi_status,
                "macd_status": macd_status,
                "momentum_score": round(max(0, min(100, momentum_score)), 1)
            }
        except:
            return {"error": "动量分析失败"}
    
    def identify_key_levels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """识别关键支撑阻力位"""
        try:
            recent_df = df.tail(20)
            
            # 近期高低点
            recent_high = recent_df['high'].max()
            recent_low = recent_df['low'].min()
            current_price = df['close'].iloc[-1]
            
            # 简单的支撑阻力识别
            support = recent_low * 0.99  # 稍低于近期最低点
            resistance = recent_high * 1.01  # 稍高于近期最高点
            
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "recent_high": round(recent_high, 2),
                "recent_low": round(recent_low, 2)
            }
        except:
            return {"error": "支撑阻力分析失败"}
    
    def analyze_volume_comprehensive(self, df: pd.DataFrame) -> Dict[str, Any]:
        """综合成交量分析"""
        try:
            latest = df.iloc[-1]
            
            current_vol = latest['volume']
            avg_vol_20 = df['volume'].tail(20).mean()
            
            # 量比分析
            volume_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1
            
            if volume_ratio > 2:
                volume_status = "放量"
            elif volume_ratio > 1.5:
                volume_status = "温和放量"
            elif volume_ratio < 0.5:
                volume_status = "缩量"
            elif volume_ratio < 0.8:
                volume_status = "温和缩量"
            else:
                volume_status = "正常"
            
            # 量价关系
            price_change = (latest['close'] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            
            if price_change > 0 and volume_ratio > 1.2:
                volume_price = "量价齐升"
            elif price_change < 0 and volume_ratio > 1.2:
                volume_price = "量增价跌"
            elif price_change > 0 and volume_ratio < 0.8:
                volume_price = "价升量缩"
            elif price_change < 0 and volume_ratio < 0.8:
                volume_price = "量价齐跌"
            else:
                volume_price = "量价平衡"
            
            return {
                "current_volume": int(current_vol),
                "volume_ratio": round(volume_ratio, 2),
                "volume_status": volume_status,
                "volume_price_relation": volume_price
            }
        except:
            return {"error": "成交量分析失败"}
    
    def assess_risk_levels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """评估风险等级"""
        try:
            latest = df.iloc[-1]
            atr = latest.get('ATR14', 0)
            current_price = latest['close']
            
            # 基于ATR的风险评估
            risk_ratio = (atr / current_price * 100) if current_price > 0 else 0
            
            if risk_ratio > 5:
                overall_risk = "高风险"
            elif risk_ratio > 3:
                overall_risk = "中等风险"
            else:
                overall_risk = "低风险"
            
            return {
                "overall_risk": overall_risk,
                "risk_ratio": round(risk_ratio, 2),
                "atr_value": round(atr, 2)
            }
        except:
            return {"error": "风险评估失败"}
    
    def analyze_symbol_enhanced(self, symbol: str, include_market_info: bool = True, display_result: bool = True) -> Optional[Dict[str, Any]]:
        """增强版品种分析"""
        print(f"\n🎯 开始增强版专业分析 {symbol} ({SYMBOL_NAMES.get(symbol, symbol)})...")
        print("=" * 80)
        
        try:
            # 1. 加载技术数据
            df = self.load_technical_data(symbol)
            if df is None or df.empty:
                print(f"❌ {symbol} 数据加载失败")
                return None
            
            # 2. 提取综合数据
            comprehensive_data = self.extract_comprehensive_data(df, symbol)
            if not comprehensive_data:
                print(f"❌ {symbol} 综合数据提取失败")
                return None
            
            print(f"📊 综合数据提取成功")
            
            # 3. 创建专业图表
            charts = self.create_professional_charts(df, symbol, comprehensive_data)
            
            # 4. 搜索市场信息（可选）
            market_info = []
            if include_market_info:
                search_query = f"{SYMBOL_NAMES.get(symbol, symbol)} 期货 最新消息 技术分析"
                market_info = self.search_market_info(search_query)
            
            # 5. 生成增强版分析提示词
            prompt = self.generate_enhanced_analysis_prompt(comprehensive_data, market_info)
            
            # 6. 调用DeepSeek Reasoner
            messages = [
                {
                    "role": "system", 
                    "content": "你是一位资深的期货技术分析专家，具有20年实战经验。请撰写专业的技术分析研究报告，确保所有分析都基于提供的真实数据，不要编造任何信息。报告应具备专业性和可读性，避免使用markdown符号。"
                },
                {"role": "user", "content": prompt}
            ]
            
            reasoning_content, final_analysis = self.call_deepseek_reasoner(messages, max_tokens=8000)
            
            if not final_analysis:
                print(f"❌ AI分析失败")
                return None
            
            # 7. 整理分析结果
            analysis_result = {
                "symbol": symbol,
                "symbol_name": SYMBOL_NAMES.get(symbol, symbol),
                "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "comprehensive_data": comprehensive_data,
                "market_info": market_info,
                "reasoning_process": reasoning_content,
                "professional_analysis": final_analysis,
                "professional_charts": charts,
                "external_citations": self.external_citations,
                "data_date": comprehensive_data['latest_date'],
                "analysis_version": "Enhanced Professional v4.0",
                "data_source": "本地数据库 + Serper搜索",
                "chart_count": len(charts),
                "citation_count": len(self.external_citations)
            }
            
            # 8. 显示结果
            if display_result:
                self.display_enhanced_result(analysis_result)
            
            print(f"✅ {symbol} 增强版专业分析完成")
            return analysis_result
            
        except Exception as e:
            print(f"❌ 分析 {symbol} 时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def display_enhanced_result(self, result: Dict[str, Any]):
        """显示增强版分析结果"""
        print(f"\n{'='*90}")
        print(f"📊 {result['symbol_name']}({result['symbol']}) 增强版专业技术分析报告")
        print(f"{'='*90}")
        print(f"📅 分析时间: {result['analysis_time']}")
        print(f"📊 数据日期: {result['data_date']}")
        print(f"🚀 分析版本: {result['analysis_version']}")
        print(f"📈 专业图表: {result['chart_count']} 个")
        print(f"📚 外部引用: {result['citation_count']} 个")
        
        # 核心数据概览
        data = result['comprehensive_data']
        print(f"\n📋 核心数据概览:")
        print("-" * 50)
        print(f"💰 当前价格: {data['current_price']}")
        print(f"📈 价格变化: 5日{data['price_change_5d']}% | 20日{data['price_change_20d']}%")
        print(f"🔄 RSI: {data['rsi']} | 动量评分: {data['momentum_analysis']['momentum_score']}/100")
        print(f"📊 趋势评分: {data['trend_analysis']['trend_score']}/100")
        print(f"🎯 均线排列: {data['trend_analysis']['ma_alignment']}")
        print(f"⚖️ 风险等级: {data['risk_assessment']['overall_risk']}")
        
        # 显示专业图表信息
        if result['professional_charts']:
            print(f"\n📈 专业图表生成完成:")
            print("-" * 30)
            for chart_name in result['professional_charts'].keys():
                print(f"✅ {chart_name}")
        
        # 显示外部引用
        if result['external_citations']:
            print(f"\n📚 外部数据来源:")
            print("-" * 30)
            for citation in result['external_citations'][:3]:  # 显示前3个
                print(f"{citation['id']} {citation['title']}")
                print(f"   来源: {citation['source']}")
        
        print(f"\n📝 专业分析报告:")
        print("-" * 50)
        print(result['professional_analysis'])
    
    def display_analysis_result_jupyter(self, result: Dict[str, Any]):
        """在Jupyter中显示分析结果（包含图表）"""
        if not result:
            print("❌ 分析结果为空")
            return
        
        # 显示基本信息
        info_html = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>📊 {result['symbol_name']}({result['symbol']}) 增强版专业技术分析报告</h2>
            <p><strong>📅 分析时间:</strong> {result['analysis_time']}</p>
            <p><strong>📊 数据日期:</strong> {result['data_date']}</p>
            <p><strong>🚀 分析版本:</strong> {result['analysis_version']}</p>
            <p><strong>📈 专业图表:</strong> {result['chart_count']} 个 | <strong>📚 外部引用:</strong> {result['citation_count']} 个</p>
        </div>
        """
        display(HTML(info_html))
        
        # 显示核心指标
        data = result['comprehensive_data']
        indicators_html = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 5px solid #007bff;">
            <h3>🔍 核心技术指标</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; margin-top: 15px;">
                <div><strong>💰 当前价格:</strong> {data['current_price']}</div>
                <div><strong>📈 5日涨跌:</strong> {data['price_change_5d']}%</div>
                <div><strong>📊 20日涨跌:</strong> {data['price_change_20d']}%</div>
                <div><strong>🔄 RSI14:</strong> {data['rsi']}</div>
                <div><strong>📊 趋势评分:</strong> {data['trend_analysis']['trend_score']}/100</div>
                <div><strong>🎯 均线排列:</strong> {data['trend_analysis']['ma_alignment']}</div>
                <div><strong>⚖️ 风险等级:</strong> {data['risk_assessment']['overall_risk']}</div>
                <div><strong>📊 量价关系:</strong> {data['volume_analysis']['volume_price_relation']}</div>
            </div>
        </div>
        """
        display(HTML(indicators_html))
        
        # 显示专业分析报告
        analysis_html = f"""
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h3>📝 专业技术分析报告</h3>
            <div style="line-height: 1.6; margin-top: 15px;">
                {result['professional_analysis'].replace('\n', '<br>')}
            </div>
        </div>
        """
        display(HTML(analysis_html))
        
        # 显示专业图表
        if result['professional_charts']:
            charts_html = """
            <div style="margin: 20px 0;">
                <h3>📈 专业技术图表</h3>
            </div>
            """
            display(HTML(charts_html))
            
            for chart_name, chart_html in result['professional_charts'].items():
                display(HTML(chart_html))
        
        # 显示外部引用
        if result['external_citations']:
            citations_html = """
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 5px solid #ffc107;">
                <h3>📚 外部数据来源</h3>
                <p style="margin-bottom: 15px;">以下信息通过Serper搜索获取，已标注数据来源：</p>
            """
            
            for citation in result['external_citations']:
                citations_html += f"""
                <div style="margin-bottom: 10px; padding: 10px; background: white; border-radius: 5px;">
                    <strong>{citation['id']}</strong> {citation['title']}<br>
                    <small style="color: #666;">来源: {citation['source']} | 
                    <a href="{citation['url']}" target="_blank">查看原文</a></small>
                </div>
                """
            
            citations_html += "</div>"
            display(HTML(citations_html))


# 便捷函数
def analyze_enhanced_technical(symbol: str, include_market_info: bool = True, display_result: bool = True) -> Optional[Dict[str, Any]]:
    """便捷的增强版技术分析函数"""
    analyzer = EnhancedProfessionalTechnicalAnalyzer()
    return analyzer.analyze_symbol_enhanced(symbol, include_market_info, display_result)

def analyze_enhanced_technical_jupyter(symbol: str, include_market_info: bool = True) -> Optional[Dict[str, Any]]:
    """Jupyter环境专用的增强版技术分析"""
    analyzer = EnhancedProfessionalTechnicalAnalyzer()
    result = analyzer.analyze_symbol_enhanced(symbol, include_market_info, display_result=False)
    if result:
        analyzer.display_analysis_result_jupyter(result)
    return result

if __name__ == "__main__":
    print("🚀 增强版专业技术分析系统")
    print("=" * 50)
    print("💡 使用方法:")
    print("1. 标准分析: analyze_enhanced_technical('RB')")
    print("2. Jupyter分析: analyze_enhanced_technical_jupyter('RB')")
    print("3. 支持品种: RB, CU, AU, M, RM, JD 等")
    print("\n✨ 新增特性:")
    print("- 专业研究报告行文风格")
    print("- 集成专业图表到报告中")
    print("- 数据来源标注")
    print("- Jupyter环境优化显示")
