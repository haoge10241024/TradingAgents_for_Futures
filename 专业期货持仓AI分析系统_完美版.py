# ============================================================================
# 专业期货持仓数据AI分析系统 - 完美版
# 交互式用户界面 + DeepSeek v3.1 Reasoner + Serper + 历史对比分析
# ============================================================================

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import json
import warnings
from dataclasses import dataclass, asdict
import httpx
import time
import requests
from scipy import stats
import asyncio
import aiohttp

warnings.filterwarnings('ignore')

print("🚀 专业期货持仓数据AI分析系统 - 完美版")
print("🔥 交互式界面 + DeepSeek v3.1 Reasoner + Serper + 历史对比分析")
print("=" * 80)

# ============================================================================
# 1. 配置和数据结构
# ============================================================================

# 基础配置
BASE_DIR = Path(r"D:\Cursor\cursor项目\TradingAgent")
POSITIONING_ROOT = BASE_DIR / "qihuo" / "database" / "positioning"
OUTPUT_DIR = BASE_DIR / "qihuo" / "output"

# DeepSeek API配置 - v3.1
DEEPSEEK_API_KEY = "sk-293dec7fabb54606b4f8d4f606da3383"
DEEPSEEK_MODEL_REASONER = "deepseek-reasoner"  # v3.1 Reasoner模式
DEEPSEEK_MODEL_CHAT = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

# Serper API配置
SERPER_API_KEY = "04555ec0f2ce150d1cb628c7a80e2e433e193535"
SERPER_BASE_URL = "https://google.serper.dev/search"

# 品种中文名称映射
SYMBOL_NAMES = {
    'RB': '螺纹钢', 'CU': '沪铜', 'AL': '沪铝', 'I': '铁矿石', 'J': '焦炭', 'JM': '焦煤',
    'MA': '甲醇', 'TA': 'PTA', 'CF': '郑棉', 'SR': '白糖', 'M': '豆粕', 'Y': '豆油',
    'P': '棕榈油', 'A': '豆一', 'C': '玉米', 'AU': '沪金', 'AG': '沪银', 'ZN': '沪锌',
    'NI': '镍', 'PB': '沪铅', 'SN': '锡', 'FU': '燃油', 'BU': '沥青', 'RU': '橡胶',
    'L': '塑料', 'V': 'PVC', 'PP': '聚丙烯', 'EG': '乙二醇', 'EB': '苯乙烯'
}

# JSON序列化辅助函数
def json_serialize_helper(obj):
    """处理numpy类型的JSON序列化"""
    if isinstance(obj, (np.integer, np.floating, np.ndarray)):
        return obj.item() if hasattr(obj, 'item') else float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime('%Y-%m-%d') if hasattr(obj, 'strftime') else str(obj)
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

@dataclass
class EnhancedPositionMetrics:
    """增强版持仓指标数据结构"""
    date: str
    symbol: str
    
    # 基础持仓数据
    long_top5_total: int = 0
    long_top10_total: int = 0
    long_top20_total: int = 0
    short_top5_total: int = 0
    short_top10_total: int = 0
    short_top20_total: int = 0
    volume_top20_total: int = 0
    
    # 持仓变化数据
    long_top5_change: int = 0
    long_top10_change: int = 0
    long_top20_change: int = 0
    short_top5_change: int = 0
    short_top10_change: int = 0
    short_top20_change: int = 0
    
    # 蜘蛛网策略数据
    spider_web_dB: int = 0
    spider_web_dS: int = 0
    spider_web_signal_strength: float = 0.0
    
    # 聪明钱指标
    oi_volume_ratio: float = 0.0
    position_efficiency: float = 0.0
    smart_money_score: float = 0.0
    
    # 集中度指标
    long_concentration: float = 0.0
    short_concentration: float = 0.0
    volume_concentration: float = 0.0
    concentration_differential: float = 0.0
    
    # 席位行为数据
    retail_net_change: int = 0
    institutional_net_change: int = 0
    foreign_net_change: int = 0
    hedging_net_change: int = 0
    retail_vs_smart_money: int = 0
    
    # 派生技术指标
    net_position_top20: int = 0
    net_change_top20: int = 0
    long_short_ratio: float = 0.0
    position_momentum: float = 0.0
    volatility_index: float = 0.0
    
    # 趋势指标
    net_change_trend_5d: float = 0.0
    position_trend_5d: float = 0.0
    concentration_trend_5d: float = 0.0
    
    # 市场情绪指标
    market_sentiment_score: float = 0.0
    consensus_level: float = 0.0

# ============================================================================
# 2. 交互式用户界面
# ============================================================================

def show_available_symbols():
    """显示可用的期货品种"""
    print("\n📋 可用期货品种:")
    print("=" * 60)
    
    # 按板块分类显示
    categories = {
        '🌾 农产品': ['A', 'B', 'C', 'M', 'Y', 'P', 'CF', 'SR', 'TA', 'MA'],
        '⚫ 黑色系': ['RB', 'I', 'J', 'JM'],
        '🟨 有色金属': ['CU', 'AL', 'ZN', 'PB', 'NI', 'SN', 'AU', 'AG'],
        '🛢️ 能源化工': ['FU', 'BU', 'RU', 'L', 'V', 'PP', 'EG', 'EB']
    }
    
    for category, symbols in categories.items():
        print(f"\n{category}:")
        for symbol in symbols:
            name = SYMBOL_NAMES.get(symbol, symbol)
            print(f"   {symbol:<4} - {name}")

def get_user_input():
    """获取用户输入"""
    print("\n🎯 专业期货持仓数据AI分析系统")
    print("=" * 60)
    
    # 显示可用品种
    show_available_symbols()
    
    # 获取品种
    while True:
        symbol = input("\n📊 请输入要分析的期货品种代码 (如: RB): ").upper().strip()
        if symbol in SYMBOL_NAMES:
            break
        else:
            print(f"❌ 无效品种代码: {symbol}")
            print("💡 请从上面的列表中选择有效的品种代码")
    
    # 获取分析天数
    print(f"\n📅 分析时间范围设置:")
    print("   1. 短期分析 (10天)")
    print("   2. 中期分析 (20天)")  
    print("   3. 长期分析 (30天)")
    print("   4. 自定义天数")
    
    while True:
        choice = input("请选择分析时间范围 (1-4): ").strip()
        if choice == '1':
            days_back = 10
            break
        elif choice == '2':
            days_back = 20
            break
        elif choice == '3':
            days_back = 30
            break
        elif choice == '4':
            try:
                days_back = int(input("请输入自定义天数 (5-60): "))
                if 5 <= days_back <= 60:
                    break
                else:
                    print("❌ 天数必须在5-60之间")
            except ValueError:
                print("❌ 请输入有效数字")
        else:
            print("❌ 请输入1-4之间的数字")
    
    # 获取AI模型选择
    print(f"\n🤖 AI分析模型选择:")
    print("   1. DeepSeek Chat (快速分析)")
    print("   2. DeepSeek v3.1 Reasoner (深度推理分析) - 推荐")
    print("   3. 智能选择 (系统根据数据复杂度自动选择)")
    
    while True:
        model_choice = input("请选择AI模型 (1-3, 默认2): ").strip() or '2'
        if model_choice in ['1', '2', '3']:
            break
        else:
            print("❌ 请输入1-3之间的数字")
    
    model_map = {
        '1': 'chat',
        '2': 'reasoner', 
        '3': 'auto'
    }
    
    model_type = model_map[model_choice]
    
    # 确认分析参数
    symbol_name = SYMBOL_NAMES.get(symbol, symbol)
    model_name = {
        'chat': 'DeepSeek Chat',
        'reasoner': 'DeepSeek v3.1 Reasoner',
        'auto': '智能选择'
    }[model_type]
    
    print(f"\n✅ 分析参数确认:")
    print(f"   📊 分析品种: {symbol} ({symbol_name})")
    print(f"   📅 分析天数: {days_back}天")
    print(f"   🤖 AI模型: {model_name}")
    print(f"   🌐 实时搜索: 启用Serper市场情报")
    print(f"   ⏱️ 预计耗时: 2-5分钟")
    
    confirm = input("\n确认开始分析? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ 分析已取消")
        return None
    
    return {
        'symbol': symbol,
        'symbol_name': symbol_name,
        'days_back': days_back,
        'model_type': model_type
    }

# ============================================================================
# 3. Serper实时市场情报系统 - 增强版
# ============================================================================

class EnhancedSerperIntelligence:
    """增强版Serper实时市场情报系统"""
    
    def __init__(self, api_key: str = SERPER_API_KEY):
        self.api_key = api_key
        self.base_url = SERPER_BASE_URL
    
    async def comprehensive_market_search(self, symbol: str, symbol_name: str) -> Dict:
        """综合市场搜索"""
        print(f"🌐 正在搜索{symbol_name}({symbol})的实时市场情报...")
        
        try:
            # 并行搜索多个维度
            tasks = [
                self._search_news(symbol, symbol_name),
                self._search_sentiment(symbol, symbol_name),
                self._search_institutional_views(symbol, symbol_name),
                self._search_technical_analysis(symbol, symbol_name)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            news_data = results[0] if not isinstance(results[0], Exception) else []
            sentiment_data = results[1] if not isinstance(results[1], Exception) else {}
            institutional_data = results[2] if not isinstance(results[2], Exception) else []
            technical_data = results[3] if not isinstance(results[3], Exception) else []
            
            print(f"✅ 获取市场情报: 新闻{len(news_data)}条, 机构观点{len(institutional_data)}条")
            
            return {
                'news_analysis': news_data,
                'sentiment_analysis': sentiment_data,
                'institutional_views': institutional_data,
                'technical_signals': technical_data,
                'search_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ 市场情报搜索失败: {e}")
            return {'error': str(e)}
    
    async def _search_news(self, symbol: str, symbol_name: str) -> List[Dict]:
        """搜索相关新闻"""
        queries = [
            f"{symbol_name}期货 最新消息",
            f"{symbol}期货 持仓 分析",
            f"{symbol_name} 价格 走势"
        ]
        
        all_news = []
        for query in queries:
            try:
                payload = {
                    "q": query,
                    "num": 5,
                    "hl": "zh-cn",
                    "gl": "cn",
                    "tbs": "qdr:w1"  # 最近一周
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url,
                        headers={'X-API-KEY': self.api_key, 'Content-Type': 'application/json'},
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for item in data.get('organic', [])[:3]:
                                all_news.append({
                                    'title': item.get('title', ''),
                                    'snippet': item.get('snippet', ''),
                                    'source': item.get('source', ''),
                                    'date': item.get('date', ''),
                                    'relevance': self._calculate_relevance(item.get('title', '') + ' ' + item.get('snippet', ''), symbol_name)
                                })
            except:
                continue
        
        # 按相关性排序，返回前10条
        all_news.sort(key=lambda x: x['relevance'], reverse=True)
        return all_news[:10]
    
    async def _search_sentiment(self, symbol: str, symbol_name: str) -> Dict:
        """搜索市场情绪"""
        try:
            payload = {
                "q": f"{symbol_name}期货 看多 看空 预测",
                "num": 10,
                "hl": "zh-cn",
                "gl": "cn"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers={'X-API-KEY': self.api_key, 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._analyze_sentiment(data.get('organic', []), symbol_name)
            
            return {'sentiment': '中性', 'confidence': 0.0}
            
        except Exception as e:
            return {'sentiment': '未知', 'confidence': 0.0, 'error': str(e)}
    
    async def _search_institutional_views(self, symbol: str, symbol_name: str) -> List[Dict]:
        """搜索机构观点"""
        try:
            payload = {
                "q": f"{symbol_name}期货 机构 研报 观点",
                "num": 8,
                "hl": "zh-cn",
                "gl": "cn"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers={'X-API-KEY': self.api_key, 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_institutional_views(data.get('organic', []))
            
            return []
            
        except:
            return []
    
    async def _search_technical_analysis(self, symbol: str, symbol_name: str) -> List[Dict]:
        """搜索技术分析"""
        try:
            payload = {
                "q": f"{symbol_name}期货 技术分析 支撑 阻力",
                "num": 5,
                "hl": "zh-cn",
                "gl": "cn"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers={'X-API-KEY': self.api_key, 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_technical_signals(data.get('organic', []))
            
            return []
            
        except:
            return []
    
    def _calculate_relevance(self, text: str, symbol_name: str) -> float:
        """计算相关性得分"""
        keywords = [symbol_name, '期货', '持仓', '多空', '分析']
        score = 0.0
        for keyword in keywords:
            if keyword in text:
                score += 1.0
        return score / len(keywords)
    
    def _analyze_sentiment(self, search_results: List[Dict], symbol_name: str) -> Dict:
        """分析搜索结果中的情绪倾向"""
        bullish_keywords = ['看多', '上涨', '利好', '买入', '做多', '涨势', '突破', '支撑']
        bearish_keywords = ['看空', '下跌', '利空', '卖出', '做空', '跌势', '破位', '阻力']
        
        bullish_count = 0
        bearish_count = 0
        
        for item in search_results:
            text = (item.get('title', '') + ' ' + item.get('snippet', '')).lower()
            
            for keyword in bullish_keywords:
                bullish_count += text.count(keyword)
            for keyword in bearish_keywords:
                bearish_count += text.count(keyword)
        
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            bullish_ratio = bullish_count / total_signals
            if bullish_ratio > 0.6:
                sentiment = '偏多'
            elif bullish_ratio < 0.4:
                sentiment = '偏空'
            else:
                sentiment = '中性'
            
            confidence = min(0.8, total_signals / 20)
        else:
            sentiment = '中性'
            confidence = 0.0
        
        return {
            'sentiment': sentiment,
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'confidence': confidence,
            'total_mentions': total_signals
        }
    
    def _extract_institutional_views(self, search_results: List[Dict]) -> List[Dict]:
        """提取机构观点"""
        views = []
        institutional_keywords = ['研报', '机构', '券商', '分析师', '预测', '目标价']
        
        for item in search_results:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            
            if any(keyword in title + snippet for keyword in institutional_keywords):
                views.append({
                    'source': item.get('source', ''),
                    'title': title,
                    'content': snippet,
                    'relevance': self._calculate_relevance(title + snippet, '机构观点')
                })
        
        return views[:5]
    
    def _extract_technical_signals(self, search_results: List[Dict]) -> List[Dict]:
        """提取技术分析信号"""
        signals = []
        technical_keywords = ['技术分析', '支撑', '阻力', '突破', '回调', 'MA', 'MACD', 'RSI']
        
        for item in search_results:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            
            if any(keyword in title + snippet for keyword in technical_keywords):
                signals.append({
                    'source': item.get('source', ''),
                    'signal': title,
                    'description': snippet
                })
        
        return signals[:3]

# ============================================================================
# 4. 席位分类系统
# ============================================================================

class SeatClassifier:
    """专业席位分类器"""
    
    def __init__(self):
        self.seat_categories = {
            'retail': [
                "东方财富", "平安期货", "徽商期货", "华安期货", 
                "申银万国", "广发期货", "招商期货", "光大期货",
                "国信期货", "中投期货", "海通期货", "兴业期货",
                "东吴期货", "渤海期货", "中金财富"
            ],
            
            'top_institutional': [
                "中信期货", "国泰君安", "华泰期货", "中金期货",
                "银河期货", "东证期货", "永安期货", "南华期货",
                "中信建投", "申万期货"
            ],
            
            'institutional': [
                "中粮期货", "物产中大", "浙商期货", "中泰期货", 
                "国投期货", "方正中期", "一德期货", "宏源期货", 
                "弘业期货", "瑞达期货", "宝城期货", "五矿期货"
            ],
            
            'foreign': [
                "摩根大通", "高盛", "瑞银", "花旗", "德意志银行",
                "法国兴业银行", "巴克莱", "汇丰银行", "星展银行",
                "摩根士丹利", "野村证券", "瑞士信贷"
            ],
            
            'hedging': [
                "中储粮", "中粮集团", "嘉吉", "路易达孚", "ADM",
                "宝钢", "河钢", "沙钢", "建龙", "中铝", "五矿",
                "中石化", "中石油", "中海油", "中化集团", "中辉期货"
            ]
        }
    
    def classify_seat(self, seat_name: str) -> str:
        """席位分类"""
        for category, seats in self.seat_categories.items():
            if any(seat in seat_name for seat in seats):
                return category
        return 'unknown'

# ============================================================================
# 5. 增强数据处理器 - 加入历史对比分析
# ============================================================================

class EnhancedDataProcessor:
    """增强数据处理器 - 加入历史对比分析"""
    
    def __init__(self):
        self.top_n_seats = 20
        self.classifier = SeatClassifier()
    
    def prepare_comprehensive_data_with_history(self, symbol: str, days_back: int = 30) -> Tuple[List[EnhancedPositionMetrics], Dict]:
        """准备包含历史对比的完整数据"""
        symbol_dir = POSITIONING_ROOT / symbol
        
        if not symbol_dir.exists():
            print(f"⚠️ {symbol}: 数据目录不存在")
            return [], {}
        
        # 读取三个文件
        long_file = symbol_dir / "long_position_ranking.csv"
        short_file = symbol_dir / "short_position_ranking.csv" 
        volume_file = symbol_dir / "volume_ranking.csv"
        
        if not all(f.exists() for f in [long_file, short_file, volume_file]):
            print(f"⚠️ {symbol}: 数据文件不完整")
            return [], {}
        
        try:
            long_df = pd.read_csv(long_file)
            short_df = pd.read_csv(short_file)
            volume_df = pd.read_csv(volume_file)
            
            # 确保日期格式正确
            long_df['date'] = pd.to_datetime(long_df['date'], format='%Y%m%d', errors='coerce')
            short_df['date'] = pd.to_datetime(short_df['date'], format='%Y%m%d', errors='coerce')
            volume_df['date'] = pd.to_datetime(volume_df['date'], format='%Y%m%d', errors='coerce')
            
            # 删除无效日期
            long_df = long_df.dropna(subset=['date'])
            short_df = short_df.dropna(subset=['date'])
            volume_df = volume_df.dropna(subset=['date'])
            
        except Exception as e:
            print(f"❌ {symbol}: 数据文件读取失败 - {e}")
            return [], {}
        
        # 获取所有可用日期用于历史分析
        all_dates = sorted(long_df['date'].dt.date.unique())
        
        # 分析期间的数据
        analysis_dates = all_dates[-days_back:]
        
        # 历史对比数据（过去60天用于对比）
        historical_dates = all_dates[-60:] if len(all_dates) >= 60 else all_dates
        
        metrics_list = []
        historical_metrics = []
        
        # 处理历史数据
        for date in historical_dates:
            date_str = date.strftime('%Y-%m-%d')
            
            long_day = long_df[long_df['date'].dt.date == date].head(self.top_n_seats)
            short_day = short_df[short_df['date'].dt.date == date].head(self.top_n_seats)
            volume_day = volume_df[volume_df['date'].dt.date == date].head(self.top_n_seats)
            
            if long_day.empty or short_day.empty:
                continue
                
            metrics = self._calculate_comprehensive_metrics(symbol, date_str, long_day, short_day, volume_day)
            historical_metrics.append(metrics)
            
            # 如果是分析期间的数据，也加入分析列表
            if date in analysis_dates:
                metrics_list.append(metrics)
        
        # 计算趋势指标
        self._calculate_trend_indicators(metrics_list)
        self._calculate_trend_indicators(historical_metrics)
        
        # 生成历史对比分析
        historical_analysis = self._generate_historical_analysis(metrics_list, historical_metrics)
        
        print(f"✅ {symbol}: 成功处理 {len(metrics_list)} 天分析数据, {len(historical_metrics)} 天历史数据")
        
        return metrics_list, historical_analysis
    
    def _calculate_comprehensive_metrics(self, symbol: str, date: str, long_df: pd.DataFrame, 
                                       short_df: pd.DataFrame, volume_df: pd.DataFrame) -> EnhancedPositionMetrics:
        """计算全面的持仓指标"""
        
        metrics = EnhancedPositionMetrics(date=date, symbol=symbol)
        
        # 基础持仓量统计
        if not long_df.empty:
            metrics.long_top5_total = int(long_df.head(5)['持仓量'].sum())
            metrics.long_top10_total = int(long_df.head(10)['持仓量'].sum())
            metrics.long_top20_total = int(long_df['持仓量'].sum())
            metrics.long_top5_change = int(long_df.head(5)['比上交易增减'].sum())
            metrics.long_top10_change = int(long_df.head(10)['比上交易增减'].sum())
            metrics.long_top20_change = int(long_df['比上交易增减'].sum())
            metrics.long_concentration = self._calculate_hhi(long_df['持仓量'])
        
        if not short_df.empty:
            metrics.short_top5_total = int(short_df.head(5)['持仓量'].sum())
            metrics.short_top10_total = int(short_df.head(10)['持仓量'].sum())
            metrics.short_top20_total = int(short_df['持仓量'].sum())
            metrics.short_top5_change = int(short_df.head(5)['比上交易增减'].sum())
            metrics.short_top10_change = int(short_df.head(10)['比上交易增减'].sum())
            metrics.short_top20_change = int(short_df['比上交易增减'].sum())
            metrics.short_concentration = self._calculate_hhi(short_df['持仓量'])
        
        if not volume_df.empty:
            metrics.volume_top20_total = int(volume_df['持仓量'].sum())
            metrics.volume_concentration = self._calculate_hhi(volume_df['持仓量'])
        
        # 蜘蛛网策略数据
        metrics.spider_web_dB = metrics.long_top20_change
        metrics.spider_web_dS = metrics.short_top20_change
        metrics.spider_web_signal_strength = abs(metrics.spider_web_dB) + abs(metrics.spider_web_dS)
        
        # 聪明钱指标
        if metrics.volume_top20_total > 0:
            metrics.oi_volume_ratio = (metrics.long_top20_total + metrics.short_top20_total) / metrics.volume_top20_total
            metrics.position_efficiency = abs(metrics.long_top20_change - metrics.short_top20_change) / metrics.volume_top20_total
            metrics.smart_money_score = metrics.oi_volume_ratio * metrics.position_efficiency
        
        # 集中度指标
        metrics.concentration_differential = metrics.long_concentration - metrics.short_concentration
        
        # 席位行为分析
        seat_behavior = self._analyze_seat_behavior_detailed(symbol, date, long_df, short_df)
        metrics.retail_net_change = seat_behavior['retail_net']
        metrics.institutional_net_change = seat_behavior['institutional_net']
        metrics.foreign_net_change = seat_behavior['foreign_net']
        metrics.hedging_net_change = seat_behavior['hedging_net']
        metrics.retail_vs_smart_money = seat_behavior['retail_net'] - (seat_behavior['institutional_net'] + seat_behavior['foreign_net'])
        
        # 派生指标
        metrics.net_position_top20 = metrics.long_top20_total - metrics.short_top20_total
        metrics.net_change_top20 = metrics.long_top20_change - metrics.short_top20_change
        
        if metrics.short_top20_total > 0:
            metrics.long_short_ratio = metrics.long_top20_total / metrics.short_top20_total
        
        # 持仓动量
        if metrics.long_top20_total + metrics.short_top20_total > 0:
            metrics.position_momentum = abs(metrics.net_change_top20) / (metrics.long_top20_total + metrics.short_top20_total)
        
        # 市场情绪评分
        metrics.market_sentiment_score = self._calculate_sentiment_score(metrics)
        metrics.consensus_level = self._calculate_consensus_level(long_df, short_df)
        
        return metrics
    
    def _generate_historical_analysis(self, current_metrics: List[EnhancedPositionMetrics], 
                                    historical_metrics: List[EnhancedPositionMetrics]) -> Dict:
        """生成历史对比分析"""
        
        if not current_metrics or not historical_metrics:
            return {}
        
        latest = current_metrics[-1]
        
        # 计算历史统计
        historical_stats = {
            'spider_web_signal_percentile': self._calculate_percentile(
                [m.spider_web_signal_strength for m in historical_metrics], 
                latest.spider_web_signal_strength
            ),
            'smart_money_percentile': self._calculate_percentile(
                [m.smart_money_score for m in historical_metrics], 
                latest.smart_money_score
            ),
            'net_position_percentile': self._calculate_percentile(
                [m.net_position_top20 for m in historical_metrics], 
                latest.net_position_top20
            ),
            'concentration_percentile': self._calculate_percentile(
                [m.concentration_differential for m in historical_metrics], 
                latest.concentration_differential
            )
        }
        
        # 历史极值分析
        historical_extremes = {
            'max_signal_strength': max(m.spider_web_signal_strength for m in historical_metrics),
            'min_signal_strength': min(m.spider_web_signal_strength for m in historical_metrics),
            'max_net_position': max(m.net_position_top20 for m in historical_metrics),
            'min_net_position': min(m.net_position_top20 for m in historical_metrics),
            'max_smart_money': max(m.smart_money_score for m in historical_metrics),
            'avg_signal_strength': np.mean([m.spider_web_signal_strength for m in historical_metrics]),
            'avg_net_position': np.mean([m.net_position_top20 for m in historical_metrics])
        }
        
        # 趋势对比分析
        recent_trend = self._analyze_recent_trend(current_metrics[-10:] if len(current_metrics) >= 10 else current_metrics)
        
        return {
            'historical_percentiles': historical_stats,
            'historical_extremes': historical_extremes,
            'recent_trend_analysis': recent_trend,
            'historical_comparison_summary': self._generate_comparison_summary(latest, historical_stats, historical_extremes)
        }
    
    def _calculate_percentile(self, data_list: List[float], current_value: float) -> float:
        """计算当前值在历史数据中的百分位"""
        if not data_list or current_value is None:
            return 50.0
        
        data_array = np.array(data_list)
        percentile = (data_array <= current_value).sum() / len(data_array) * 100
        return float(percentile)
    
    def _analyze_recent_trend(self, recent_metrics: List[EnhancedPositionMetrics]) -> Dict:
        """分析最近趋势"""
        if len(recent_metrics) < 3:
            return {}
        
        # 计算各指标的趋势
        dates = list(range(len(recent_metrics)))
        
        trends = {}
        for attr in ['spider_web_signal_strength', 'smart_money_score', 'net_position_top20', 'concentration_differential']:
            values = [getattr(m, attr) for m in recent_metrics]
            if len(set(values)) > 1:
                correlation = np.corrcoef(dates, values)[0, 1]
                trends[attr] = {
                    'correlation': float(correlation),
                    'direction': '上升' if correlation > 0.3 else '下降' if correlation < -0.3 else '横盘',
                    'strength': abs(correlation)
                }
        
        return trends
    
    def _generate_comparison_summary(self, latest: EnhancedPositionMetrics, 
                                   percentiles: Dict, extremes: Dict) -> str:
        """生成对比总结"""
        summary_parts = []
        
        # 信号强度对比
        signal_pct = percentiles['spider_web_signal_percentile']
        if signal_pct > 90:
            summary_parts.append(f"当前信号强度{latest.spider_web_signal_strength:.0f}处于历史{signal_pct:.0f}%分位，属于极强信号")
        elif signal_pct > 70:
            summary_parts.append(f"当前信号强度处于历史{signal_pct:.0f}%分位，属于较强信号")
        elif signal_pct < 30:
            summary_parts.append(f"当前信号强度处于历史{signal_pct:.0f}%分位，属于较弱信号")
        
        # 净持仓对比
        position_pct = percentiles['net_position_percentile']
        if position_pct > 80:
            summary_parts.append(f"净持仓水平处于历史{position_pct:.0f}%分位，偏向多头极值")
        elif position_pct < 20:
            summary_parts.append(f"净持仓水平处于历史{position_pct:.0f}%分位，偏向空头极值")
        
        # 聪明钱对比
        smart_pct = percentiles['smart_money_percentile']
        if smart_pct > 75:
            summary_parts.append(f"聪明钱活跃度处于历史{smart_pct:.0f}%分位，高度活跃")
        elif smart_pct < 25:
            summary_parts.append(f"聪明钱活跃度处于历史{smart_pct:.0f}%分位，相对低迷")
        
        return "; ".join(summary_parts) if summary_parts else "当前各项指标处于历史正常范围内"
    
    def _calculate_hhi(self, positions: pd.Series) -> float:
        """计算赫芬达尔-赫希曼指数(HHI)"""
        if positions.empty or positions.sum() == 0:
            return 0.0
        
        shares = positions / positions.sum()
        return float((shares ** 2).sum())
    
    def _analyze_seat_behavior_detailed(self, symbol: str, date: str, long_df: pd.DataFrame, short_df: pd.DataFrame) -> Dict:
        """详细分析席位行为"""
        category_stats = {
            'retail_net': 0, 'institutional_net': 0, 'foreign_net': 0, 'hedging_net': 0
        }
        
        # 统计多单变化
        for _, row in long_df.iterrows():
            seat_name = row['会员简称']
            category = self.classifier.classify_seat(seat_name)
            change = row['比上交易增减']
            
            if category == 'retail':
                category_stats['retail_net'] += change
            elif category in ['top_institutional', 'institutional']:
                category_stats['institutional_net'] += change
            elif category == 'foreign':
                category_stats['foreign_net'] += change
            elif category == 'hedging':
                category_stats['hedging_net'] += change
        
        # 统计空单变化
        for _, row in short_df.iterrows():
            seat_name = row['会员简称']
            category = self.classifier.classify_seat(seat_name)
            change = row['比上交易增减']
            
            if category == 'retail':
                category_stats['retail_net'] -= change
            elif category in ['top_institutional', 'institutional']:
                category_stats['institutional_net'] -= change
            elif category == 'foreign':
                category_stats['foreign_net'] -= change
            elif category == 'hedging':
                category_stats['hedging_net'] -= change
        
        return category_stats
    
    def _calculate_sentiment_score(self, metrics: EnhancedPositionMetrics) -> float:
        """计算市场情绪评分"""
        score = 0.0
        
        if metrics.net_position_top20 > 0:
            score += 0.3
        elif metrics.net_position_top20 < 0:
            score -= 0.3
        
        if metrics.net_change_top20 > 0:
            score += 0.2
        elif metrics.net_change_top20 < 0:
            score -= 0.2
        
        score += metrics.concentration_differential * 0.5
        
        if metrics.smart_money_score > 0.1:
            if metrics.net_change_top20 > 0:
                score += 0.2
            else:
                score -= 0.2
        
        return max(-1.0, min(1.0, score))
    
    def _calculate_consensus_level(self, long_df: pd.DataFrame, short_df: pd.DataFrame) -> float:
        """计算市场共识度"""
        long_changes = long_df['比上交易增减'].values
        short_changes = short_df['比上交易增减'].values
        
        long_positive_ratio = (long_changes > 0).mean()
        short_positive_ratio = (short_changes > 0).mean()
        
        consensus = 1.0 - abs(0.5 - max(long_positive_ratio, 1 - long_positive_ratio, 
                                       short_positive_ratio, 1 - short_positive_ratio))
        
        return float(consensus)
    
    def _calculate_trend_indicators(self, metrics_list: List[EnhancedPositionMetrics]):
        """计算趋势指标"""
        if len(metrics_list) < 5:
            return
        
        for i in range(4, len(metrics_list)):
            current = metrics_list[i]
            recent_5 = metrics_list[i-4:i+1]
            
            net_changes = [m.net_change_top20 for m in recent_5]
            net_positions = [m.net_position_top20 for m in recent_5]
            concentrations = [m.long_concentration - m.short_concentration for m in recent_5]
            
            x = list(range(5))
            if len(set(net_changes)) > 1:
                current.net_change_trend_5d = float(np.corrcoef(x, net_changes)[0, 1])
            if len(set(net_positions)) > 1:
                current.position_trend_5d = float(np.corrcoef(x, net_positions)[0, 1])
            if len(set(concentrations)) > 1:
                current.concentration_trend_5d = float(np.corrcoef(x, concentrations)[0, 1])
            
            if i >= 9:
                recent_10_changes = [m.net_change_top20 for m in metrics_list[i-9:i+1]]
                current.volatility_index = float(np.std(recent_10_changes))

# ============================================================================
# 6. 完美AI分析客户端
# ============================================================================

class PerfectAIAnalyst:
    """完美AI分析师 - 支持模型选择 + 历史对比 + 实时情报"""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.reasoner_model = DEEPSEEK_MODEL_REASONER
        self.chat_model = DEEPSEEK_MODEL_CHAT
        self.base_url = DEEPSEEK_BASE_URL
        self.market_intel = EnhancedSerperIntelligence()
    
    async def comprehensive_analysis(self, symbol: str, symbol_name: str, metrics_data: List[EnhancedPositionMetrics], 
                                   historical_analysis: Dict, model_type: str = 'reasoner') -> Optional[Dict]:
        """综合分析 - 支持模型选择"""
        
        if not self.api_key or not metrics_data:
            return None
        
        try:
            # 1. 收集实时市场情报
            print("🌐 收集实时市场情报...")
            market_intelligence = await self.market_intel.comprehensive_market_search(symbol, symbol_name)
            
            # 2. 根据用户选择或数据复杂度选择模型
            if model_type == 'auto':
                # 智能选择模型
                data_complexity = self._assess_data_complexity(metrics_data)
                selected_model = 'reasoner' if data_complexity > 0.7 else 'chat'
                print(f"🤖 智能选择模型: {selected_model} (复杂度: {data_complexity:.2f})")
            else:
                selected_model = model_type
            
            # 3. 执行分析
            if selected_model == 'reasoner':
                print("🧠 执行DeepSeek v3.1 Reasoner深度分析...")
                result = await self._reasoner_analysis(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
            else:
                print("💬 执行DeepSeek Chat快速分析...")
                result = await self._chat_analysis(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
            
            if result and not result.get('analysis_failed'):
                print(f"✅ {selected_model.upper()}分析完成")
                result['model_used'] = selected_model
                return result
            else:
                print("⚠️ 主要分析失败，尝试备用模式")
                # 备用模式
                backup_model = 'chat' if selected_model == 'reasoner' else 'reasoner'
                if backup_model == 'reasoner':
                    result = await self._reasoner_analysis(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
                else:
                    result = await self._chat_analysis(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
                
                if result:
                    result['model_used'] = backup_model
                    result['fallback_mode'] = True
                return result
                
        except Exception as e:
            print(f"❌ 分析过程出错: {e}")
            return {"error": str(e), "analysis_failed": True}
    
    def _assess_data_complexity(self, metrics_data: List[EnhancedPositionMetrics]) -> float:
        """评估数据复杂度"""
        if not metrics_data:
            return 0.0
        
        complexity_score = 0.0
        
        # 数据量复杂度
        complexity_score += min(len(metrics_data) / 30, 0.3)
        
        # 信号强度复杂度
        latest = metrics_data[-1]
        if latest.spider_web_signal_strength > 100000:
            complexity_score += 0.2
        
        # 趋势复杂度
        if len(metrics_data) >= 5:
            recent_changes = [m.net_change_top20 for m in metrics_data[-5:]]
            volatility = np.std(recent_changes) if len(set(recent_changes)) > 1 else 0
            complexity_score += min(volatility / 50000, 0.3)
        
        # 席位行为复杂度
        if abs(latest.retail_vs_smart_money) > 10000:
            complexity_score += 0.2
        
        return min(complexity_score, 1.0)
    
    async def _reasoner_analysis(self, symbol: str, symbol_name: str, metrics_data: List[EnhancedPositionMetrics], 
                               historical_analysis: Dict, market_intelligence: Dict) -> Optional[Dict]:
        """DeepSeek v3.1 Reasoner深度分析"""
        
        system_prompt = self._build_ultimate_prompt()
        analysis_data = self._prepare_complete_analysis_data(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "model": self.reasoner_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(analysis_data, ensure_ascii=False, default=json_serialize_helper)}
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=request_data
                    # 无时间限制，确保深度分析完成
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # 尝试解析JSON
                        try:
                            result = json.loads(content)
                            return result if isinstance(result, dict) else None
                        except json.JSONDecodeError:
                            # 尝试提取JSON部分
                            import re
                            json_match = re.search(r'\{[\s\S]*\}', content)
                            if json_match:
                                try:
                                    return json.loads(json_match.group(0))
                                except json.JSONDecodeError:
                                    pass
                            
                            # 返回原始分析
                            return {"raw_analysis": content, "parsing_error": True}
                    else:
                        print(f"❌ Reasoner API调用失败: {response.status}")
                        return None
        except Exception as e:
            print(f"❌ Reasoner分析失败: {e}")
            return None
    
    async def _chat_analysis(self, symbol: str, symbol_name: str, metrics_data: List[EnhancedPositionMetrics],
                           historical_analysis: Dict, market_intelligence: Dict) -> Optional[Dict]:
        """Chat模式分析"""
        
        system_prompt = self._build_ultimate_prompt()
        analysis_data = self._prepare_complete_analysis_data(symbol, symbol_name, metrics_data, historical_analysis, market_intelligence)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(analysis_data, ensure_ascii=False, default=json_serialize_helper)}
            ],
            "temperature": 0.2,
            "max_tokens": 3500
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers=headers,
                    json=request_data
                    # 无时间限制，确保分析完成
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # 尝试解析JSON
                        try:
                            result = json.loads(content)
                            return result if isinstance(result, dict) else None
                        except json.JSONDecodeError:
                            # 尝试提取JSON部分
                            import re
                            json_match = re.search(r'\{[\s\S]*\}', content)
                            if json_match:
                                try:
                                    return json.loads(json_match.group(0))
                                except json.JSONDecodeError:
                                    pass
                            
                            # 返回原始分析
                            return {"raw_analysis": content, "parsing_error": True}
                    else:
                        print(f"❌ Chat API调用失败: {response.status}")
                        return None
        except Exception as e:
            print(f"❌ Chat分析失败: {e}")
            return None
    
    def _build_ultimate_prompt(self) -> str:
        """构建终极专业prompt"""
        return """
你是全球顶级量化对冲基金的首席期货分析师，拥有20年的期货市场分析经验。你的分析将结合持仓数据、历史对比和实时市场情报。

## 核心分析框架

### 1. 蜘蛛网策略分析 (Spider Web Strategy)
**理论基础**: 基于前20名会员持仓变动数据，捕捉"聪明资金"动向
**核心指标**: dB (多头变动), dS (空头变动)
**信号判断**:
- dB > 0 且 dS < 0: 强烈看多 (强度0.8-1.0)
- dB < 0 且 dS > 0: 强烈看空 (强度0.8-1.0)
- dB和dS同向: 需结合净变化和历史对比判断
**历史对比**: 必须结合信号强度的历史分位数进行评估

### 2. 聪明钱分析 (Smart Money Analysis)
**核心指标**: 
- OI/Volume Ratio: 持仓/成交比
- Position Efficiency: 持仓效率
- Smart Money Score: 综合评分
**历史对比**: 当前聪明钱活跃度在历史中的位置

### 3. 家人席位反向策略 (Retail Reverse Strategy)
**核心逻辑**: 散户vs机构行为分化分析
**历史验证**: 结合历史胜率进行信号强度评估

### 4. 持仓集中度分析 (Concentration Analysis)
**核心指标**: HHI指数，集中度差异，集中度趋势
**历史对比**: 当前集中度水平的历史位置

### 5. 实时市场情报整合
**数据来源**: 实时新闻、机构观点、技术分析
**分析维度**: 情绪倾向、观点统计、技术信号

### 6. 历史对比分析
**关键要素**: 
- 各指标的历史分位数
- 历史极值对比
- 趋势变化分析
- 相似历史情况的后续走势

## 输出要求 - 机构级标准

```json
{
  "spider_web_analysis": {
    "signal": "强烈看多|看多|中性|看空|强烈看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "详细分析dB、dS数值，结合历史分位数，解释信号强度和市场含义",
    "key_metrics": {
      "dB": 数值,
      "dS": 数值,
      "signal_strength": 数值,
      "historical_percentile": "历史分位数%"
    },
    "historical_comparison": "与历史同类信号的对比分析"
  },
  "smart_money_analysis": {
    "signal": "看多|中性|看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "深度分析聪明钱活跃度、效率，结合历史对比",
    "key_metrics": {
      "smart_money_score": 数值,
      "oi_volume_ratio": 数值,
      "historical_percentile": "历史分位数%"
    },
    "trend_analysis": "聪明钱行为趋势分析"
  },
  "retail_reverse_analysis": {
    "signal": "看多|中性|看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "散户vs机构行为分化分析，历史胜率评估",
    "key_metrics": {
      "retail_net": 数值,
      "institutional_net": 数值,
      "divergence_strength": "分化强度评分"
    }
  },
  "concentration_analysis": {
    "signal": "看多|中性|看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "持仓集中度变化分析，大户控盘行为评估",
    "key_metrics": {
      "concentration_differential": 数值,
      "historical_percentile": "历史分位数%",
      "trend_direction": "趋势方向"
    }
  },
  "market_intelligence_analysis": {
    "news_sentiment": "基于实时新闻的情绪分析",
    "institutional_consensus": "机构观点统计和共识度",
    "technical_signals": "技术分析信号汇总",
    "market_heat": "市场关注度和热度评估"
  },
  "historical_context": {
    "current_vs_history": "当前数据在历史中的位置评估",
    "similar_scenarios": "历史相似情况及其后续走势",
    "extreme_levels": "是否接近历史极值水平",
    "trend_sustainability": "当前趋势的可持续性评估"
  },
  "comprehensive_conclusion": {
    "overall_signal": "强烈看多|看多|中性|看空|强烈看空",
    "confidence": 0.0-1.0,
    "time_horizon": "短期(1-3天)|中期(1-2周)|长期(1个月+)",
    "key_factors": ["关键因素1", "关键因素2", "关键因素3"],
    "supporting_evidence": "支撑证据详述，包括数据对比、历史验证",
    "risk_factors": ["风险因素1", "风险因素2"],
    "market_regime": "趋势市|震荡市|转折期",
    "probability_assessment": {
      "upward_probability": "上涨概率%",
      "downward_probability": "下跌概率%",
      "sideways_probability": "横盘概率%"
    }
  },
  "trading_recommendations": {
    "primary_strategy": "具体交易策略，基于多维度分析",
    "entry_timing": "入场时机，结合技术位和数据信号",
    "position_sizing": "仓位建议，基于信号强度和风险评估",
    "stop_loss": "止损策略，包括技术止损和数据止损",
    "profit_target": "目标位设定，短中长期目标",
    "risk_management": "风险管理要点",
    "scenario_planning": "不同情况下的应对策略"
  },
  "professional_insights": {
    "market_microstructure": "市场微观结构深度分析",
    "institutional_behavior_pattern": "机构行为模式识别",
    "contrarian_signal_strength": "反向指标强度评估",
    "momentum_characteristics": "动量特征和持续性",
    "regime_change_probability": "市场状态转换概率",
    "cross_asset_implications": "对相关资产的影响",
    "seasonality_considerations": "季节性因素考量",
    "volatility_outlook": "波动率前景预测"
  }
}
```

## 分析要求
1. **数据驱动**: 严格基于真实数据和历史对比
2. **逻辑严密**: 每个结论都有充分支撑
3. **历史验证**: 必须结合历史分位数和相似情况
4. **实时整合**: 融合实时市场情报
5. **风险意识**: 充分识别各种风险
6. **可操作性**: 提供具体可执行建议
7. **专业深度**: 体现顶级分析师水准

请基于提供的完整数据（包括历史对比和实时情报）进行深度专业分析。
"""
    
    def _prepare_complete_analysis_data(self, symbol: str, symbol_name: str, metrics_list: List[EnhancedPositionMetrics], 
                                      historical_analysis: Dict, market_intelligence: Dict) -> Dict:
        """准备完整分析数据"""
        
        if not metrics_list:
            return {}
        
        latest = metrics_list[-1]
        
        # 最近数据
        recent_data = []
        for m in metrics_list[-min(10, len(metrics_list)):]:
            comprehensive = {
                'date': m.date,
                'spider_web_dB': m.spider_web_dB,
                'spider_web_dS': m.spider_web_dS,
                'spider_web_signal_strength': m.spider_web_signal_strength,
                'net_change': m.net_change_top20,
                'net_position': m.net_position_top20,
                'smart_money_score': m.smart_money_score,
                'long_concentration': m.long_concentration,
                'short_concentration': m.short_concentration,
                'retail_net_change': m.retail_net_change,
                'institutional_net_change': m.institutional_net_change,
                'long_short_ratio': m.long_short_ratio,
                'market_sentiment_score': m.market_sentiment_score
            }
            recent_data.append(comprehensive)
        
        return {
            "symbol": symbol,
            "symbol_name": symbol_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "data_period": f"{metrics_list[0].date} ~ {metrics_list[-1].date}",
            "analysis_days": len(metrics_list),
            
            # 当前核心数据
            "current_metrics": {
                "spider_web_dB": latest.spider_web_dB,
                "spider_web_dS": latest.spider_web_dS,
                "spider_web_signal_strength": latest.spider_web_signal_strength,
                "net_change_top20": latest.net_change_top20,
                "net_position_top20": latest.net_position_top20,
                "smart_money_score": latest.smart_money_score,
                "oi_volume_ratio": latest.oi_volume_ratio,
                "position_efficiency": latest.position_efficiency,
                "long_concentration": latest.long_concentration,
                "short_concentration": latest.short_concentration,
                "concentration_differential": latest.concentration_differential,
                "retail_net_change": latest.retail_net_change,
                "institutional_net_change": latest.institutional_net_change,
                "foreign_net_change": latest.foreign_net_change,
                "retail_vs_smart_money": latest.retail_vs_smart_money,
                "long_short_ratio": latest.long_short_ratio,
                "position_momentum": latest.position_momentum,
                "volatility_index": latest.volatility_index,
                "market_sentiment_score": latest.market_sentiment_score,
                "consensus_level": latest.consensus_level
            },
            
            # 历史数据和趋势
            "recent_data_series": recent_data,
            
            # 历史对比分析
            "historical_analysis": historical_analysis,
            
            # 实时市场情报
            "market_intelligence": market_intelligence,
            
            # 趋势指标
            "trend_indicators": {
                "net_change_trend_5d": latest.net_change_trend_5d,
                "position_trend_5d": latest.position_trend_5d,
                "concentration_trend_5d": latest.concentration_trend_5d
            }
        }

# ============================================================================
# 7. 完美分析引擎
# ============================================================================

class PerfectAnalysisEngine:
    """完美分析引擎 - 交互式 + 历史对比 + 实时情报"""
    
    def __init__(self):
        self.data_processor = EnhancedDataProcessor()
        self.ai_analyst = PerfectAIAnalyst()
    
    async def interactive_analysis(self):
        """交互式分析"""
        
        print("🎯 专业期货持仓数据AI分析系统 - 完美版")
        print("=" * 80)
        
        # 获取用户输入
        user_input = get_user_input()
        if not user_input:
            return
        
        symbol = user_input['symbol']
        symbol_name = user_input['symbol_name']
        days_back = user_input['days_back']
        model_type = user_input['model_type']
        
        print(f"\n🚀 开始分析...")
        print("=" * 60)
        
        # 1. 数据准备
        print("📊 准备分析数据...")
        metrics_data, historical_analysis = self.data_processor.prepare_comprehensive_data_with_history(symbol, days_back)
        
        if not metrics_data:
            print(f"❌ {symbol} 数据准备失败")
            return
        
        print(f"✅ 数据准备完成: {len(metrics_data)}天分析数据")
        
        # 2. AI分析
        ai_result = await self.ai_analyst.comprehensive_analysis(
            symbol, symbol_name, metrics_data, historical_analysis, model_type
        )
        
        if not ai_result or ai_result.get('analysis_failed'):
            print("❌ AI分析失败")
            return
        
        # 3. 显示结果
        self._display_analysis_results(symbol, symbol_name, ai_result)
        
        # 4. 保存报告
        self._save_analysis_report(symbol, ai_result)
    
    def _display_analysis_results(self, symbol: str, symbol_name: str, ai_result: Dict):
        """显示分析结果"""
        
        print(f"\n🎯 {symbol} ({symbol_name}) 完美分析结果")
        print("=" * 80)
        
        # 显示使用的模型
        model_used = ai_result.get('model_used', '未知')
        fallback = ai_result.get('fallback_mode', False)
        model_info = f"{model_used.upper()}" + (" (备用模式)" if fallback else "")
        print(f"🤖 使用模型: {model_info}")
        
        # 显示实时市场情报
        if 'market_intelligence_analysis' in ai_result:
            intel = ai_result['market_intelligence_analysis']
            print(f"\n🌐 实时市场情报:")
            print(f"   新闻情绪: {intel.get('news_sentiment', '未知')}")
            print(f"   机构共识: {intel.get('institutional_consensus', '未知')}")
            print(f"   技术信号: {intel.get('technical_signals', '未知')}")
            print(f"   市场热度: {intel.get('market_heat', '未知')}")
        
        # 显示历史对比
        if 'historical_context' in ai_result:
            context = ai_result['historical_context']
            print(f"\n📊 历史对比分析:")
            print(f"   历史位置: {context.get('current_vs_history', '未知')}")
            print(f"   相似情况: {context.get('similar_scenarios', '未知')}")
            print(f"   极值水平: {context.get('extreme_levels', '未知')}")
        
        # 显示各策略分析
        strategies = ['spider_web_analysis', 'smart_money_analysis', 'retail_reverse_analysis', 'concentration_analysis']
        
        for strategy in strategies:
            if strategy in ai_result:
                analysis = ai_result[strategy]
                signal = analysis.get('signal', '未知')
                strength = analysis.get('strength', 0.0)
                confidence = analysis.get('confidence', 0.0)
                reasoning = analysis.get('reasoning', '无')
                
                strategy_name = {
                    'spider_web_analysis': '🕸️ 蜘蛛网策略',
                    'smart_money_analysis': '🧠 聪明钱分析', 
                    'retail_reverse_analysis': '🔄 家人席位反向',
                    'concentration_analysis': '📊 持仓集中度'
                }.get(strategy, strategy)
                
                print(f"\n{strategy_name}:")
                print(f"   信号: {signal} | 强度: {strength:.2f} | 置信度: {confidence:.2f}")
                print(f"   分析: {reasoning}")
                
                # 显示历史对比
                if 'historical_comparison' in analysis:
                    print(f"   历史对比: {analysis['historical_comparison']}")
        
        # 综合结论
        if 'comprehensive_conclusion' in ai_result:
            conclusion = ai_result['comprehensive_conclusion']
            print(f"\n🎯 综合结论:")
            print(f"   总体信号: {conclusion.get('overall_signal', '未知')}")
            print(f"   置信度: {conclusion.get('confidence', 0.0):.2f}")
            print(f"   时间周期: {conclusion.get('time_horizon', '未知')}")
            print(f"   关键因素: {', '.join(conclusion.get('key_factors', []))}")
            print(f"   市场状态: {conclusion.get('market_regime', '未知')}")
            
            # 概率评估
            if 'probability_assessment' in conclusion:
                prob = conclusion['probability_assessment']
                print(f"   概率评估: 上涨{prob.get('upward_probability', 'N/A')} | 下跌{prob.get('downward_probability', 'N/A')} | 横盘{prob.get('sideways_probability', 'N/A')}")
        
        # 交易建议
        if 'trading_recommendations' in ai_result:
            trading = ai_result['trading_recommendations']
            print(f"\n💡 交易建议:")
            print(f"   主要策略: {trading.get('primary_strategy', '无')}")
            print(f"   入场时机: {trading.get('entry_timing', '无')}")
            print(f"   仓位建议: {trading.get('position_sizing', '无')}")
            print(f"   止损建议: {trading.get('stop_loss', '无')}")
            print(f"   目标位: {trading.get('profit_target', '无')}")
            
            if 'scenario_planning' in trading:
                print(f"   情景规划: {trading['scenario_planning']}")
        
        # 专业洞察
        if 'professional_insights' in ai_result:
            insights = ai_result['professional_insights']
            print(f"\n🔬 专业洞察:")
            insight_items = [
                ('market_microstructure', '市场微观结构'),
                ('institutional_behavior_pattern', '机构行为模式'),
                ('regime_change_probability', '状态转换概率'),
                ('volatility_outlook', '波动率前景')
            ]
            
            for key, name in insight_items:
                if key in insights and insights[key]:
                    print(f"   {name}: {insights[key]}")
    
    def _save_analysis_report(self, symbol: str, ai_result: Dict):
        """保存分析报告"""
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"perfect_analysis_{symbol}_{timestamp}.json"
            
            output_file = OUTPUT_DIR / filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(ai_result, f, ensure_ascii=False, indent=2, default=json_serialize_helper)
            
            print(f"\n📄 分析报告已保存: {output_file}")
            
        except Exception as e:
            print(f"⚠️ 报告保存失败: {e}")

# ============================================================================
# 8. 主程序入口
# ============================================================================

async def main():
    """主程序"""
    engine = PerfectAnalysisEngine()
    await engine.interactive_analysis()

def jupyter_run():
    """Jupyter环境运行"""
    import asyncio
    
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except ImportError:
        pass
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        task = asyncio.create_task(main())
        return task
    else:
        return asyncio.run(main())

if __name__ == "__main__":
    print("🚀 专业期货持仓数据AI分析系统已加载 - 完美版")
    print("🔥 特性:")
    print("   ✅ 交互式用户界面")
    print("   ✅ DeepSeek v3.1 Reasoner + Chat模式选择")
    print("   ✅ Serper实时市场情报搜索")
    print("   ✅ 历史对比分析")
    print("   ✅ 无时间限制，确保分析质量")
    print("   ✅ 机构级专业分析标准")
    print("\n使用方法:")
    print("1. 交互式分析: await main()")
    print("2. Jupyter环境: jupyter_run()")
    print("\n💡 这是真正完美的专业AI分析系统！")
    
    # 检测运行环境并选择合适的启动方式
    try:
        # 检测是否在Jupyter环境中
        import IPython
        if IPython.get_ipython() is not None:
            print("\n🔍 检测到Jupyter环境，请使用以下命令启动分析:")
            print("   jupyter_run()")
        else:
            # 命令行环境
            asyncio.run(main())
    except ImportError:
        # 不在Jupyter环境中，直接运行
        try:
            asyncio.run(main())
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                print("\n⚠️ 检测到事件循环冲突，请使用: jupyter_run()")
            else:
                raise e
