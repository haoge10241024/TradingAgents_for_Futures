# ============================================================================
# 专业期货持仓数据AI分析系统
# 完全基于AI的专业分析框架 - 数据准备 + AI专业分析
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
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False

print("🚀 专业期货持仓数据AI分析系统")
print("=" * 80)

# ============================================================================
# 1. 配置和数据结构
# ============================================================================

# 基础配置
BASE_DIR = Path(r"D:\Cursor\cursor项目\TradingAgent")
POSITIONING_ROOT = BASE_DIR / "qihuo" / "database" / "positioning"
OUTPUT_DIR = BASE_DIR / "qihuo" / "output"

# DeepSeek API配置
# 请在配置文件中设置API密钥，或通过环境变量 DEEPSEEK_API_KEY
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY_HERE")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"

@dataclass
class EnhancedPositionMetrics:
    """增强版持仓指标数据结构 - 为AI分析准备的完整数据"""
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
    spider_web_dB: int = 0  # 多头变动
    spider_web_dS: int = 0  # 空头变动
    spider_web_signal_strength: float = 0.0  # 信号强度
    
    # 聪明钱指标
    oi_volume_ratio: float = 0.0  # 持仓/成交比
    position_efficiency: float = 0.0  # 持仓效率
    smart_money_score: float = 0.0  # 聪明钱评分
    
    # 集中度指标
    long_concentration: float = 0.0  # 多单集中度(HHI)
    short_concentration: float = 0.0  # 空单集中度(HHI)
    volume_concentration: float = 0.0  # 成交集中度
    concentration_differential: float = 0.0  # 集中度差异
    
    # 席位行为数据
    retail_net_change: int = 0  # 散户净变化
    institutional_net_change: int = 0  # 机构净变化
    foreign_net_change: int = 0  # 外资净变化
    hedging_net_change: int = 0  # 套保净变化
    retail_vs_smart_money: int = 0  # 散户vs聪明钱对比
    
    # 派生技术指标
    net_position_top20: int = 0
    net_change_top20: int = 0
    long_short_ratio: float = 0.0
    position_momentum: float = 0.0  # 持仓动量
    volatility_index: float = 0.0  # 波动率指数
    
    # 趋势指标(需要历史数据计算)
    net_change_trend_5d: float = 0.0  # 5日净变化趋势
    position_trend_5d: float = 0.0  # 5日净持仓趋势
    concentration_trend_5d: float = 0.0  # 5日集中度趋势
    
    # 市场情绪指标
    market_sentiment_score: float = 0.0  # 市场情绪评分
    consensus_level: float = 0.0  # 共识度

# ============================================================================
# 2. 席位分类系统
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
# 3. 数据处理器 - 为AI准备结构化数据
# ============================================================================

class ProfessionalDataProcessor:
    """专业数据处理器 - 为AI分析准备完整的结构化数据"""
    
    def __init__(self):
        self.top_n_seats = 20
        self.classifier = SeatClassifier()
    
    def prepare_comprehensive_data(self, symbol: str, days_back: int = 30) -> List[EnhancedPositionMetrics]:
        """为AI分析准备完整的结构化数据"""
        symbol_dir = POSITIONING_ROOT / symbol
        
        if not symbol_dir.exists():
            print(f"⚠️ {symbol}: 数据目录不存在")
            return []
        
        # 读取三个文件
        long_file = symbol_dir / "long_position_ranking.csv"
        short_file = symbol_dir / "short_position_ranking.csv" 
        volume_file = symbol_dir / "volume_ranking.csv"
        
        if not all(f.exists() for f in [long_file, short_file, volume_file]):
            print(f"⚠️ {symbol}: 数据文件不完整")
            return []
        
        long_df = pd.read_csv(long_file)
        short_df = pd.read_csv(short_file)
        volume_df = pd.read_csv(volume_file)
        
        metrics_list = []
        
        # 按日期分组处理
        dates = sorted(long_df['date'].unique())[-days_back:]
        
        for i, date in enumerate(dates):
            long_day = long_df[long_df['date'] == date].head(self.top_n_seats)
            short_day = short_df[short_df['date'] == date].head(self.top_n_seats)
            volume_day = volume_df[volume_df['date'] == date].head(self.top_n_seats)
            
            if long_day.empty or short_day.empty:
                continue
                
            metrics = self._calculate_comprehensive_metrics(symbol, str(date), long_day, short_day, volume_day)
            metrics_list.append(metrics)
        
        # 计算趋势指标
        self._calculate_trend_indicators(metrics_list)
        
        return metrics_list
    
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
        # 基于多个维度计算情绪评分
        score = 0.0
        
        # 净持仓方向
        if metrics.net_position_top20 > 0:
            score += 0.3
        elif metrics.net_position_top20 < 0:
            score -= 0.3
        
        # 净变化方向
        if metrics.net_change_top20 > 0:
            score += 0.2
        elif metrics.net_change_top20 < 0:
            score -= 0.2
        
        # 集中度差异
        score += metrics.concentration_differential * 0.5
        
        # 聪明钱倾向
        if metrics.smart_money_score > 0.1:
            if metrics.net_change_top20 > 0:
                score += 0.2
            else:
                score -= 0.2
        
        return max(-1.0, min(1.0, score))
    
    def _calculate_consensus_level(self, long_df: pd.DataFrame, short_df: pd.DataFrame) -> float:
        """计算市场共识度"""
        # 基于持仓变化的一致性计算共识度
        long_changes = long_df['比上交易增减'].values
        short_changes = short_df['比上交易增减'].values
        
        # 计算变化方向的一致性
        long_positive_ratio = (long_changes > 0).mean()
        short_positive_ratio = (short_changes > 0).mean()
        
        # 共识度 = 1 - 分歧度
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
            
            # 5日趋势
            net_changes = [m.net_change_top20 for m in recent_5]
            net_positions = [m.net_position_top20 for m in recent_5]
            concentrations = [m.long_concentration - m.short_concentration for m in recent_5]
            
            # 计算相关性作为趋势指标
            x = list(range(5))
            if len(set(net_changes)) > 1:
                current.net_change_trend_5d = np.corrcoef(x, net_changes)[0, 1]
            if len(set(net_positions)) > 1:
                current.position_trend_5d = np.corrcoef(x, net_positions)[0, 1]
            if len(set(concentrations)) > 1:
                current.concentration_trend_5d = np.corrcoef(x, concentrations)[0, 1]
            
            # 波动率指数
            if i >= 9:  # 需要10天数据
                recent_10_changes = [m.net_change_top20 for m in metrics_list[i-9:i+1]]
                current.volatility_index = float(np.std(recent_10_changes))

# ============================================================================
# 4. 专业AI分析客户端
# ============================================================================

class ProfessionalAIAnalyst:
    """专业AI分析师 - 完全基于AI的期货持仓分析"""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.model = DEEPSEEK_MODEL
        self.base_url = DEEPSEEK_BASE_URL
    
    def comprehensive_positioning_analysis(self, symbol: str, metrics_data: List[EnhancedPositionMetrics]) -> Optional[Dict]:
        """综合持仓数据AI分析"""
        
        if not self.api_key or not metrics_data:
            return None
        
        # 构建专业分析prompt
        system_prompt = self._build_professional_analysis_prompt()
        
        # 准备数据
        analysis_data = self._prepare_analysis_data(symbol, metrics_data)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        request_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(analysis_data, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(self.base_url, headers=headers, json=request_data)
                response.raise_for_status()
                
                data = response.json()
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
                    
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def _build_professional_analysis_prompt(self) -> str:
        """构建专业分析prompt"""
        return """
你是资深的商品期货持仓数据分析专家，拥有15年的期货市场分析经验，专精于通过持仓数据预判市场走势。

## 分析方法论

### 1. 蜘蛛网策略分析 (Spider Web Strategy)
**核心原理**: 基于期货交易所公布的前20名会员持仓变动数据，捕捉"聪明资金"动向
**关键指标**: 
- dB (多头变动): spider_web_dB，反映多头资金增减
- dS (空头变动): spider_web_dS，反映空头资金增减
**信号判断**:
- dB > 0 且 dS < 0: 多头增仓+空头减仓 → 强烈看多信号
- dB < 0 且 dS > 0: 多头减仓+空头增仓 → 强烈看空信号  
- dB 和 dS 同向: 可能存在分歧或套利行为，需结合其他指标
**信号强度**: spider_web_signal_strength = |dB| + |dS|，数值越大信号越强

### 2. 聪明钱分析 (Smart Money Analysis)
**核心原理**: 通过持仓/成交比识别知情资金，聪明钱通常持仓时间长、交易频率低
**关键指标**:
- oi_volume_ratio: 持仓/成交比，>2.0 表示聪明钱活跃
- position_efficiency: 持仓效率，>0.1 表示资金使用高效
- smart_money_score: 聪明钱评分 = oi_volume_ratio × position_efficiency
**判断逻辑**: 当聪明钱活跃且净持仓变化明显时，跟随其方向

### 3. 家人席位反向策略 (Retail Reverse Strategy)  
**核心原理**: 散户通常是市场的反向指标，与机构外资行为相反时信号更强
**关键指标**:
- retail_net_change: 散户净持仓变化
- institutional_net_change: 机构净持仓变化  
- foreign_net_change: 外资净持仓变化
- retail_vs_smart_money: 散户vs聪明钱对比
**信号强度**: 散户与机构外资方向相反时信号最强，仅散户有方向时信号中等

### 4. 持仓集中度分析 (Concentration Analysis)
**核心原理**: 大户控盘程度反映市场影响力，集中度变化预示趋势转换
**关键指标**:
- long_concentration/short_concentration: 多空单集中度(HHI指数)
- concentration_differential: 集中度差异
- concentration_trend_5d: 5日集中度趋势
**判断标准**: 集中度>0.15且上升趋势表示大户控盘加强

### 5. 趋势与情绪分析
**关键指标**:
- net_change_trend_5d/position_trend_5d: 5日趋势相关性
- market_sentiment_score: 市场情绪评分(-1到1)
- consensus_level: 市场共识度(0到1)
- volatility_index: 波动率指数

## 输出要求

请基于提供的结构化数据进行专业分析，输出严格JSON格式：

```json
{
  "spider_web_analysis": {
    "signal": "强烈看多|看多|中性|看空|强烈看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "详细分析过程，包括dB、dS数值及其含义",
    "key_metrics": {"dB": 数值, "dS": 数值, "signal_strength": 数值}
  },
  "smart_money_analysis": {
    "signal": "看多|中性|看空", 
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0,
    "reasoning": "聪明钱活跃度分析，持仓效率评估",
    "key_metrics": {"oi_volume_ratio": 数值, "smart_money_score": 数值}
  },
  "retail_reverse_analysis": {
    "signal": "看多|中性|看空",
    "strength": 0.0-1.0, 
    "confidence": 0.0-1.0,
    "reasoning": "散户vs机构外资行为对比分析",
    "key_metrics": {"retail_net": 数值, "smart_money_net": 数值}
  },
  "concentration_analysis": {
    "signal": "看多|中性|看空",
    "strength": 0.0-1.0,
    "confidence": 0.0-1.0, 
    "reasoning": "持仓集中度变化及其市场含义",
    "key_metrics": {"long_conc": 数值, "short_conc": 数值, "trend": 数值}
  },
  "comprehensive_conclusion": {
    "overall_signal": "强烈看多|看多|中性|看空|强烈看空",
    "confidence": 0.0-1.0,
    "time_horizon": "短期(1-3天)|中期(1-2周)|长期(1个月+)",
    "key_factors": ["关键因素1", "关键因素2", "关键因素3"],
    "supporting_evidence": "支撑证据的详细描述",
    "risk_factors": ["风险因素1", "风险因素2"],
    "market_regime": "趋势市|震荡市|转折期",
    "sentiment_assessment": "极度乐观|乐观|中性|悲观|极度悲观"
  },
  "trading_recommendations": {
    "primary_strategy": "具体交易策略建议",
    "entry_timing": "入场时机建议", 
    "position_sizing": "建议仓位大小",
    "stop_loss": "止损位建议",
    "profit_target": "目标位建议",
    "risk_management": "风险管理要点"
  },
  "professional_insights": {
    "market_microstructure": "市场微观结构分析",
    "institutional_behavior": "机构行为模式观察", 
    "contrarian_signals": "反向指标识别",
    "momentum_analysis": "动量特征分析",
    "regime_change_probability": "市场状态转换概率评估"
  }
}
```

## 分析要求
1. 严格基于数据进行分析，不编造数值
2. 体现专业期货分析师的思维深度
3. 结合多个策略进行综合判断
4. 提供具体可操作的交易建议
5. 识别关键风险点和机会窗口
6. 保持客观中性的专业态度
"""
    
    def _prepare_analysis_data(self, symbol: str, metrics_list: List[EnhancedPositionMetrics]) -> Dict:
        """为AI准备分析数据"""
        
        if not metrics_list:
            return {}
        
        latest = metrics_list[-1]
        
        # 最近5天数据（简化版本）
        recent_data = []
        for m in metrics_list[-5:]:
            simplified = {
                'date': m.date,
                'net_position': m.net_position_top20,
                'net_change': m.net_change_top20,
                'spider_web_dB': m.spider_web_dB,
                'spider_web_dS': m.spider_web_dS,
                'smart_money_score': m.smart_money_score,
                'long_concentration': m.long_concentration,
                'short_concentration': m.short_concentration,
                'retail_net_change': m.retail_net_change,
                'institutional_net_change': m.institutional_net_change
            }
            recent_data.append(simplified)
        
        # 趋势统计
        trend_stats = {}
        if len(metrics_list) >= 5:
            recent_5 = metrics_list[-5:]
            trend_stats = {
                "net_change_trend": [m.net_change_top20 for m in recent_5],
                "net_position_trend": [m.net_position_top20 for m in recent_5],
                "long_concentration_trend": [m.long_concentration for m in recent_5],
                "short_concentration_trend": [m.short_concentration for m in recent_5],
                "smart_money_score_trend": [m.smart_money_score for m in recent_5]
            }
        
        # 关键统计指标
        key_statistics = {
            "avg_net_change_5d": float(np.mean([m.net_change_top20 for m in metrics_list[-5:]])),
            "std_net_change_5d": float(np.std([m.net_change_top20 for m in metrics_list[-5:]])),
            "max_net_position": max(m.net_position_top20 for m in metrics_list),
            "min_net_position": min(m.net_position_top20 for m in metrics_list),
            "avg_smart_money_score": float(np.mean([m.smart_money_score for m in metrics_list[-10:]])),
            "current_vs_avg_position": latest.net_position_top20 - np.mean([m.net_position_top20 for m in metrics_list[:-1]])
        }
        
        return {
            "symbol": symbol,
            "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_period": f"{metrics_list[0].date} 至 {metrics_list[-1].date}",
            "total_days": len(metrics_list),
            
            # 当前数据
            "latest_metrics": asdict(latest),
            
            # 最近趋势
            "recent_5_days": recent_data,
            "trend_statistics": trend_stats,
            "key_statistics": key_statistics,
            
            # 策略特定数据
            "spider_web_data": {
                "current_dB": latest.spider_web_dB,
                "current_dS": latest.spider_web_dS,
                "signal_strength": latest.spider_web_signal_strength,
                "recent_dB_trend": [m.spider_web_dB for m in metrics_list[-5:]],
                "recent_dS_trend": [m.spider_web_dS for m in metrics_list[-5:]]
            },
            
            "smart_money_data": {
                "current_score": latest.smart_money_score,
                "oi_volume_ratio": latest.oi_volume_ratio,
                "position_efficiency": latest.position_efficiency,
                "trend": [m.smart_money_score for m in metrics_list[-5:]]
            },
            
            "seat_behavior_data": {
                "retail_net": latest.retail_net_change,
                "institutional_net": latest.institutional_net_change,
                "foreign_net": latest.foreign_net_change,
                "retail_vs_smart": latest.retail_vs_smart_money,
                "recent_retail_trend": [m.retail_net_change for m in metrics_list[-5:]]
            },
            
            "concentration_data": {
                "long_concentration": latest.long_concentration,
                "short_concentration": latest.short_concentration,
                "differential": latest.concentration_differential,
                "trend_5d": latest.concentration_trend_5d
            }
        }

# ============================================================================
# 5. 主分析引擎
# ============================================================================

class ProfessionalPositioningAnalysisEngine:
    """专业持仓分析引擎"""
    
    def __init__(self):
        self.data_processor = ProfessionalDataProcessor()
        self.ai_analyst = ProfessionalAIAnalyst()
    
    def analyze_symbol_professional(self, symbol: str, days_back: int = 30) -> Dict:
        """专业品种分析"""
        
        print(f"🔍 开始专业分析品种: {symbol}")
        print("-" * 50)
        
        # 1. 数据准备
        print("📊 准备分析数据...")
        metrics_data = self.data_processor.prepare_comprehensive_data(symbol, days_back)
        
        if not metrics_data:
            return {
                'symbol': symbol,
                'status': 'failed',
                'reason': '无可用数据',
                'analysis_time': datetime.now().isoformat()
            }
        
        print(f"✅ 成功准备 {len(metrics_data)} 天的完整数据")
        
        # 2. AI专业分析
        print("🤖 执行AI专业分析...")
        ai_analysis = self.ai_analyst.comprehensive_positioning_analysis(symbol, metrics_data)
        
        if ai_analysis and not ai_analysis.get('analysis_failed'):
            print("✅ AI专业分析完成")
        else:
            print("⚠️ AI分析失败，返回基础数据")
        
        # 3. 构建结果
        result = {
            'symbol': symbol,
            'status': 'success',
            'analysis_time': datetime.now().isoformat(),
            'data_period': f"{metrics_data[0].date} ~ {metrics_data[-1].date}",
            'days_analyzed': len(metrics_data),
            
            # AI专业分析结果
            'ai_professional_analysis': ai_analysis,
            
            # 最新数据快照
            'latest_metrics': asdict(metrics_data[-1]) if metrics_data else {},
            
            # 原始数据（供进一步分析）
            'raw_metrics_data': [asdict(m) for m in metrics_data[-10:]]
        }
        
        return result
    
    def batch_analyze_professional(self, symbols: List[str], days_back: int = 30) -> Dict:
        """批量专业分析"""
        print(f"🚀 开始批量专业分析 {len(symbols)} 个品种")
        print("=" * 80)
        
        results = {}
        successful = 0
        start_time = time.time()
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 分析品种: {symbol}")
            try:
                result = self.analyze_symbol_professional(symbol, days_back)
                results[symbol] = result
                
                if result['status'] == 'success':
                    successful += 1
                    # 尝试提取AI分析结论
                    ai_analysis = result.get('ai_professional_analysis', {})
                    if ai_analysis and not ai_analysis.get('parsing_error'):
                        conclusion = ai_analysis.get('comprehensive_conclusion', {})
                        overall_signal = conclusion.get('overall_signal', '未知')
                        confidence = conclusion.get('confidence', 0.0)
                        print(f"🎯 AI分析结论: {overall_signal} (置信度: {confidence:.2f})")
                    else:
                        print("🎯 AI分析完成（需查看详细结果）")
                        
            except Exception as e:
                results[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'reason': str(e),
                    'analysis_time': datetime.now().isoformat()
                }
                print(f"❌ 分析失败: {e}")
        
        total_time = time.time() - start_time
        
        # 生成汇总
        summary = self._generate_professional_summary(results)
        
        return {
            'analysis_time': datetime.now().isoformat(),
            'total_symbols': len(symbols),
            'successful_analyses': successful,
            'processing_time_seconds': round(total_time, 2),
            'professional_summary': summary,
            'detailed_results': results
        }
    
    def _generate_professional_summary(self, results: Dict) -> Dict:
        """生成专业汇总"""
        signal_counts = {'强烈看多': 0, '看多': 0, '中性': 0, '看空': 0, '强烈看空': 0, '未知': 0}
        high_confidence_signals = []
        
        for symbol, result in results.items():
            if result.get('status') == 'success':
                ai_analysis = result.get('ai_professional_analysis', {})
                if ai_analysis and not ai_analysis.get('parsing_error'):
                    conclusion = ai_analysis.get('comprehensive_conclusion', {})
                    signal = conclusion.get('overall_signal', '未知')
                    confidence = conclusion.get('confidence', 0.0)
                    
                    if signal in signal_counts:
                        signal_counts[signal] += 1
                    else:
                        signal_counts['未知'] += 1
                    
                    if confidence >= 0.7:
                        high_confidence_signals.append({
                            'symbol': symbol,
                            'signal': signal,
                            'confidence': confidence
                        })
        
        return {
            'signal_distribution': signal_counts,
            'high_confidence_signals': sorted(high_confidence_signals, key=lambda x: x['confidence'], reverse=True),
            'market_sentiment_overview': self._assess_overall_sentiment(signal_counts)
        }
    
    def _assess_overall_sentiment(self, signal_counts: Dict) -> str:
        """评估整体市场情绪"""
        total = sum(signal_counts.values())
        if total == 0:
            return "无法评估"
        
        bullish = signal_counts.get('强烈看多', 0) + signal_counts.get('看多', 0)
        bearish = signal_counts.get('强烈看空', 0) + signal_counts.get('看空', 0)
        neutral = signal_counts.get('中性', 0)
        
        bullish_ratio = bullish / total
        bearish_ratio = bearish / total
        
        if bullish_ratio > 0.6:
            return "市场整体偏多"
        elif bearish_ratio > 0.6:
            return "市场整体偏空"
        elif neutral / total > 0.5:
            return "市场观望情绪浓厚"
        else:
            return "市场分歧较大"
    
    def save_professional_report(self, analysis_results: Dict, filename: str = None) -> Path:
        """保存专业分析报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"professional_positioning_analysis_{timestamp}.json"
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 专业分析报告已保存: {output_file}")
        return output_file

# ============================================================================
# 6. 使用示例和主程序
# ============================================================================

def professional_single_analysis(symbol: str, days_back: int = 30):
    """专业单品种分析"""
    engine = ProfessionalPositioningAnalysisEngine()
    result = engine.analyze_symbol_professional(symbol, days_back)
    
    if result['status'] != 'success':
        print(f"❌ {symbol} 分析失败: {result['reason']}")
        return result
    
    print(f"\n🎯 {symbol} 专业分析结果")
    print("=" * 60)
    
    ai_analysis = result.get('ai_professional_analysis', {})
    
    if ai_analysis and not ai_analysis.get('analysis_failed') and not ai_analysis.get('parsing_error'):
        # 显示各策略分析
        strategies = ['spider_web_analysis', 'smart_money_analysis', 'retail_reverse_analysis', 'concentration_analysis']
        
        for strategy in strategies:
            if strategy in ai_analysis:
                analysis = ai_analysis[strategy]
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
        
        # 综合结论
        if 'comprehensive_conclusion' in ai_analysis:
            conclusion = ai_analysis['comprehensive_conclusion']
            print(f"\n🎯 综合结论:")
            print(f"   总体信号: {conclusion.get('overall_signal', '未知')}")
            print(f"   置信度: {conclusion.get('confidence', 0.0):.2f}")
            print(f"   时间周期: {conclusion.get('time_horizon', '未知')}")
            print(f"   关键因素: {', '.join(conclusion.get('key_factors', []))}")
            print(f"   市场状态: {conclusion.get('market_regime', '未知')}")
            print(f"   情绪评估: {conclusion.get('sentiment_assessment', '未知')}")
        
        # 交易建议
        if 'trading_recommendations' in ai_analysis:
            trading = ai_analysis['trading_recommendations']
            print(f"\n💡 交易建议:")
            print(f"   主要策略: {trading.get('primary_strategy', '无')}")
            print(f"   入场时机: {trading.get('entry_timing', '无')}")
            print(f"   仓位建议: {trading.get('position_sizing', '无')}")
            print(f"   止损建议: {trading.get('stop_loss', '无')}")
            
        # 专业洞察
        if 'professional_insights' in ai_analysis:
            insights = ai_analysis['professional_insights']
            print(f"\n🔬 专业洞察:")
            for key, value in insights.items():
                key_name = {
                    'market_microstructure': '市场微观结构',
                    'institutional_behavior': '机构行为模式',
                    'contrarian_signals': '反向信号识别',
                    'momentum_analysis': '动量特征分析',
                    'regime_change_probability': '状态转换概率'
                }.get(key, key)
                print(f"   {key_name}: {value}")
                
    else:
        print("⚠️ AI分析结果解析失败或分析出错")
        if ai_analysis.get('raw_analysis'):
            print(f"原始分析: {ai_analysis['raw_analysis'][:500]}...")
    
    return result

def professional_batch_analysis():
    """专业批量分析"""
    engine = ProfessionalPositioningAnalysisEngine()
    
    # 主要品种
    symbols = ['RB', 'CU', 'AL', 'I', 'J', 'JM', 'MA', 'TA', 'CF', 'SR', 'M', 'Y', 'P', 'A', 'C']
    
    print("🎯 专业期货持仓数据AI分析系统")
    print(f"📋 分析品种: {', '.join(symbols)}")
    print(f"📅 分析周期: 最近30个交易日")
    print(f"🤖 AI模型: {DEEPSEEK_MODEL}")
    
    results = engine.batch_analyze_professional(symbols, days_back=30)
    
    # 保存报告
    report_file = engine.save_professional_report(results)
    
    # 显示汇总
    summary = results['professional_summary']
    print(f"\n📊 专业分析汇总:")
    print(f"   ✅ 成功分析: {results['successful_analyses']}/{results['total_symbols']} 个品种")
    print(f"   ⏱️ 处理时间: {results['processing_time_seconds']} 秒")
    
    print(f"\n📈 信号分布:")
    for signal, count in summary['signal_distribution'].items():
        if count > 0:
            print(f"   {signal}: {count} 个品种")
    
    print(f"\n🌡️ 市场情绪: {summary['market_sentiment_overview']}")
    
    if summary['high_confidence_signals']:
        print(f"\n🔥 高置信度信号 (≥0.7):")
        for item in summary['high_confidence_signals'][:10]:
            print(f"   {item['symbol']}: {item['signal']} (置信度: {item['confidence']:.2f})")
    
    return results

if __name__ == "__main__":
    print("🚀 专业期货持仓数据AI分析系统已加载")
    print("\n使用方法:")
    print("1. 单品种专业分析: result = professional_single_analysis('RB')")
    print("2. 批量专业分析: results = professional_batch_analysis()")
    print("\n💡 所有分析逻辑完全由AI完成，确保专业性和客观性")
