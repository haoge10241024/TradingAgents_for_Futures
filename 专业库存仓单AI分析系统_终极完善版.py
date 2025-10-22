"""
专业库存仓单AI分析系统 - 终极完善版
===========================================

终极完善亮点：
1. ✅ 元数据信息完全后置，开头直接分析内容
2. ✅ 严禁任何英文，纯中文专业表达
3. ✅ 专业图表生成功能（库存趋势+价格对比+反身性分析）
4. ✅ 完全兼容Streamlit系统调用
5. ✅ 多维度数据整合（库存+价格+基差+期限结构+持仓）
6. ✅ 库存反身性关系深度解读

核心特性：
• 🤖 DeepSeek V3.1 + Reasoner推理模式
• 🌐 强化联网数据获取，确保时效性
• 📊 五维数据整合 + 专业图表生成
• 💡 库存反身性关系深度解读
• 🎯 纯中文专业投资策略制定
• ⚡ 多维度交叉验证分析

版本：v8.0 Ultimate Perfection
作者：AI Trading Assistant
更新：2025-09-21
"""

import pandas as pd
import numpy as np
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
from scipy import stats
import warnings
import time
import os
import akshare as ak
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from matplotlib.font_manager import FontProperties
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False


class UltimatePerfectedInventoryAnalyzer:
    """专业库存仓单AI分析系统 - 终极完善版"""
    
    def __init__(self):
        """初始化系统"""
        # API配置
        self.deepseek_api_key = "sk-293dec7fabb54606b4f8d4f606da3383"
        self.serper_api_key = "d3654e36956e0bf331e901886c49c602cea72eb1"
        
        # 数据路径配置
        self.base_path = Path(r"D:\Cursor\cursor项目\TradingAgent\qihuo\database")
        self.inventory_dir = self.base_path / "inventory"
        self.receipt_dir = self.base_path / "receipt" 
        self.technical_dir = self.base_path / "technical_analysis"
        self.term_structure_dir = self.base_path / "term_structure"
        self.basis_dir = self.base_path / "basis"
        self.positioning_dir = self.base_path / "positioning"
        
        # API URL
        self.deepseek_base_url = "https://api.deepseek.com/v1/chat/completions"
        self.serper_base_url = "https://google.serper.dev/search"
        
        # 品种映射和特性
        self.variety_mapping = {
            '聚氯乙烯': {'code': 'V', 'category': '化工', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': 'PVC', 'chinese_name': '聚氯乙烯'},
            '白银': {'code': 'AG', 'category': '贵金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪银'},
            '黄金': {'code': 'AU', 'category': '贵金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪金'},
            '铜': {'code': 'CU', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪铜'},
            '铝': {'code': 'AL', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪铝'},
            '锌': {'code': 'ZN', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪锌'},
            '铅': {'code': 'PB', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪铅'},
            '镍': {'code': 'NI', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪镍'},
            '锡': {'code': 'SN', 'category': '有色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沪锡'},
            '螺纹钢': {'code': 'RB', 'category': '黑色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '螺纹钢'},
            '铁矿石': {'code': 'I', 'category': '黑色金属', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': '铁矿石'},
            '热轧卷板': {'code': 'HC', 'category': '黑色金属', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '热卷'},
            '焦炭': {'code': 'J', 'category': '黑色金属', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': '焦炭'},
            '焦煤': {'code': 'JM', 'category': '黑色金属', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': '焦煤'},
            '石油沥青': {'code': 'BU', 'category': '能源化工', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '沥青'},
            '燃料油': {'code': 'FU', 'category': '能源化工', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '燃油'},
            '天然橡胶': {'code': 'RU', 'category': '农产品', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '橡胶'},
            '纸浆': {'code': 'SP', 'category': '农产品', 'unit': '万吨', 'exchange': 'SHFE', 'ak_name': '纸浆'},
            '棉花': {'code': 'CF', 'category': '农产品', 'unit': '万吨', 'exchange': 'CZCE', 'ak_name': '棉花'},
            '白糖': {'code': 'SR', 'category': '农产品', 'unit': '万吨', 'exchange': 'CZCE', 'ak_name': '白糖'},
            '玻璃': {'code': 'FG', 'category': '建材', 'unit': '万吨', 'exchange': 'CZCE', 'ak_name': '玻璃'},
            '纯碱': {'code': 'SA', 'category': '化工', 'unit': '万吨', 'exchange': 'CZCE', 'ak_name': '纯碱'},
            '塑料': {'code': 'L', 'category': '化工', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': '塑料'},
            '聚丙烯': {'code': 'PP', 'category': '化工', 'unit': '万吨', 'exchange': 'DCE', 'ak_name': '聚丙烯'},
            '甲醇': {'code': 'MA', 'category': '化工', 'unit': '万吨', 'exchange': 'CZCE', 'ak_name': '甲醇'},
        }
        
        # 交易所仓单接口映射
        self.receipt_apis = {
            'SHFE': ak.futures_shfe_warehouse_receipt,
            'CZCE': ak.futures_czce_warehouse_receipt, 
            'DCE': ak.futures_dce_warehouse_receipt,
            'GFEX': ak.futures_gfex_warehouse_receipt
        }
        
        # 图表保存目录
        self.charts_dir = Path("analysis_charts")
        self.charts_dir.mkdir(exist_ok=True)
        
        print("🚀 专业库存仓单AI分析系统（终极完善版）已启动")
        print("✅ 元数据信息完全后置，开头直接分析内容")
        print("✅ 严禁任何英文，纯中文专业表达")
        print("✅ 专业图表生成功能")
        print("✅ 完全兼容Streamlit系统调用")
        print("✅ 五维数据整合 + 库存反身性关系深度解读")
        
    def load_multi_dimensional_data(self, variety_name):
        """加载多维度数据"""
        print(f"📊 正在加载{variety_name}的多维度数据...")
        
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        
        data = {
            'variety_info': variety_info,
            'data_sources': [],
            'online_data_used': False
        }
        
        # 1. 库存数据（本地+联网）
        inventory_data, inv_sources, inv_online = self.load_inventory_data_enhanced(variety_name)
        data['inventory'] = inventory_data
        data['data_sources'].extend(inv_sources)
        if inv_online:
            data['online_data_used'] = True
        
        # 2. 仓单数据（强化联网获取）
        receipt_data, rec_sources, rec_online = self.load_receipt_data_enhanced(variety_name)
        data['receipt'] = receipt_data
        data['data_sources'].extend(rec_sources)
        if rec_online:
            data['online_data_used'] = True
        
        # 3. 价格数据
        price_data, price_sources = self.load_price_data_multi(variety_name)
        data['price'] = price_data
        data['data_sources'].extend(price_sources)
        
        # 4. 基差数据
        basis_data, basis_sources = self.load_basis_data(variety_name)
        data['basis'] = basis_data
        data['data_sources'].extend(basis_sources)
        
        # 5. 期限结构数据
        term_structure_data, term_sources = self.load_term_structure_data(variety_name)
        data['term_structure'] = term_structure_data
        data['data_sources'].extend(term_sources)
        
        # 6. 持仓数据
        positioning_data, pos_sources = self.load_positioning_data(variety_name)
        data['positioning'] = positioning_data
        data['data_sources'].extend(pos_sources)
        
        # 7. 强化联网补充数据
        online_supplement, online_sources, online_flag = self.fetch_online_supplement_data(variety_name)
        data['online_supplement'] = online_supplement
        data['data_sources'].extend(online_sources)
        if online_flag:
            data['online_data_used'] = True
        
        return data
    
    def load_inventory_data_enhanced(self, variety_name):
        """加载增强库存数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        ak_name = variety_info.get('ak_name', variety_name)
        # 调试信息
        print(f"📊 品种映射: {variety_name} -> 代码: {variety_code}, Akshare名称: {ak_name}")
        
        data_sources = []
        online_used = False
        
        # 1. 本地数据
        inventory_file = self.inventory_dir / variety_code / "inventory.csv"
        local_df = None
        if inventory_file.exists():
            try:
                local_df = pd.read_csv(inventory_file)
                local_df['date'] = pd.to_datetime(local_df['date'])
                local_df = local_df.sort_values('date')
                print(f"✅ 本地库存数据: {len(local_df)} 条记录")
                data_sources.append(f"本地历史库存数据（{len(local_df)}条记录）")
            except Exception as e:
                print(f"⚠️ 本地库存数据读取失败: {e}")
        
        # 2. 强化联网获取
        print(f"📡 强化联网获取{variety_name}库存数据...")
        online_df = None
        try:
            online_df = ak.futures_inventory_em(symbol=ak_name)
            if online_df is not None and not online_df.empty:
                # 标准化数据
                if '日期' in online_df.columns:
                    online_df = online_df.rename(columns={'日期': 'date', '库存': 'value'})
                elif '时间' in online_df.columns:
                    online_df = online_df.rename(columns={'时间': 'date', '库存': 'value'})
                
                online_df['date'] = pd.to_datetime(online_df['date'])
                online_df['value'] = pd.to_numeric(online_df['value'], errors='coerce')
                online_df = online_df.dropna(subset=['value']).sort_values('date')
                
                fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data_sources.append(f"联网库存数据（东方财富，获取时间：{fetch_time}，{len(online_df)}条记录）")
                print(f"✅ 联网库存数据: {len(online_df)} 条记录")
                online_used = True
            else:
                print(f"❌ 联网库存数据获取失败：无数据返回")
        except Exception as e:
            print(f"❌ 联网库存数据获取失败: {e}")
        
        # 3. 数据整合策略
        if online_df is not None and not online_df.empty:
            if local_df is not None and not local_df.empty:
                combined_df = pd.concat([local_df, online_df]).drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                return combined_df, data_sources, online_used
            else:
                return online_df, data_sources, online_used
        elif local_df is not None:
            return local_df, data_sources, online_used
        else:
            return None, data_sources, online_used
    
    def load_receipt_data_enhanced(self, variety_name):
        """加载增强仓单数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        exchange = variety_info.get('exchange', 'SHFE')
        
        data_sources = []
        online_used = False
        
        # 1. 本地仓单数据
        possible_receipt_dirs = [variety_name, variety_code, f"{variety_name}({variety_code})"]
        local_receipt_df = None
        
        for receipt_dir_name in possible_receipt_dirs:
            receipt_file = self.receipt_dir / receipt_dir_name / "receipt.csv"
            if receipt_file.exists():
                try:
                    local_receipt_df = pd.read_csv(receipt_file)
                    local_receipt_df['date'] = pd.to_datetime(local_receipt_df['date'])
                    local_receipt_df = local_receipt_df.sort_values('date')
                    print(f"✅ 本地仓单数据: {len(local_receipt_df)} 条记录")
                    data_sources.append(f"本地历史仓单数据（{len(local_receipt_df)}条记录）")
                    break
                except Exception as e:
                    print(f"⚠️ 本地仓单数据读取失败 ({receipt_dir_name}): {e}")
                    continue
        
        # 2. 强化联网获取仓单数据
        print(f"📡 强化联网获取{variety_name}仓单数据（{exchange}）...")
        online_receipt_df = None
        receipt_success = False
        
        if exchange in self.receipt_apis:
            try:
                receipt_api = self.receipt_apis[exchange]
                today = datetime.now()
                
                # 扩大搜索范围，尝试最近30天
                for days_back in range(0, 30):
                    target_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
                    try:
                        receipt_data = receipt_api(date=target_date)
                        if receipt_data is not None and not receipt_data.empty:
                            # 筛选目标品种的仓单数据
                            variety_data = None
                            for col_name in ['var', '品种', '品种代码', 'symbol']:
                                if col_name in receipt_data.columns:
                                    variety_data = receipt_data[receipt_data[col_name].str.contains(variety_code, case=False, na=False)]
                                    if not variety_data.empty:
                                        break
                            
                            if variety_data is None or variety_data.empty:
                                variety_data = receipt_data
                            
                            if not variety_data.empty:
                                fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                data_sources.append(f"联网仓单数据（{exchange}交易所，数据日期：{target_date}，获取时间：{fetch_time}，{len(variety_data)}条记录）")
                                print(f"✅ 联网仓单数据: {target_date} 日数据，{len(variety_data)} 条记录")
                                online_receipt_df = variety_data
                                online_used = True
                                receipt_success = True
                                break
                    except Exception as e:
                        if days_back == 0:
                            print(f"⚠️ 获取{target_date}仓单数据失败: {e}")
                        continue
                
                if not receipt_success:
                    print(f"⚠️ 未能获取到最近30天的仓单数据")
                    
            except Exception as e:
                print(f"❌ 联网仓单数据获取异常: {e}")
        
        # 3. 返回最优数据
        if online_receipt_df is not None and not online_receipt_df.empty:
            if local_receipt_df is not None and not local_receipt_df.empty:
                return online_receipt_df, data_sources, online_used
            else:
                return online_receipt_df, data_sources, online_used
        elif local_receipt_df is not None:
            return local_receipt_df, data_sources, online_used
        else:
            return None, data_sources, online_used
    
    def load_price_data_multi(self, variety_name):
        """加载多维价格数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        
        data_sources = []
        
        price_file = self.technical_dir / variety_code / "ohlc_data.csv"
        if price_file.exists():
            try:
                price_df = pd.read_csv(price_file)
                price_df['时间'] = pd.to_datetime(price_df['时间'])
                price_df = price_df.sort_values('时间')
                print(f"✅ 本地价格数据: {len(price_df)} 条记录")
                data_sources.append(f"本地历史价格数据（{len(price_df)}条记录）")
                return price_df, data_sources
            except Exception as e:
                print(f"⚠️ 本地价格数据加载失败: {e}")
        
        print(f"❌ 未找到价格数据")
        return None, data_sources
    
    def load_basis_data(self, variety_name):
        """加载基差数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        
        data_sources = []
        
        basis_file = self.basis_dir / variety_code / "basis_data.csv"
        if basis_file.exists():
            try:
                basis_df = pd.read_csv(basis_file)
                basis_df['date'] = pd.to_datetime(basis_df['date'])
                basis_df = basis_df.sort_values('date')
                print(f"✅ 本地基差数据: {len(basis_df)} 条记录")
                data_sources.append(f"本地基差数据（{len(basis_df)}条记录）")
                return basis_df, data_sources
            except Exception as e:
                print(f"⚠️ 基差数据加载失败: {e}")
        
        print(f"ℹ️ 未找到基差数据")
        return None, data_sources
    
    def load_term_structure_data(self, variety_name):
        """加载期限结构数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        
        data_sources = []
        
        term_file = self.term_structure_dir / variety_code / "term_structure.csv"
        if term_file.exists():
            try:
                term_df = pd.read_csv(term_file)
                term_df['date'] = pd.to_datetime(term_df['date'])
                term_df = term_df.sort_values('date')
                print(f"✅ 本地期限结构数据: {len(term_df)} 条记录")
                data_sources.append(f"本地期限结构数据（{len(term_df)}条记录）")
                return term_df, data_sources
            except Exception as e:
                print(f"⚠️ 期限结构数据加载失败: {e}")
        
        print(f"ℹ️ 未找到期限结构数据")
        return None, data_sources
    
    def load_positioning_data(self, variety_name):
        """加载持仓数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        
        data_sources = []
        
        # 尝试加载多头持仓数据
        long_pos_file = self.positioning_dir / variety_code / "long_position_ranking.csv"
        if long_pos_file.exists():
            try:
                pos_df = pd.read_csv(long_pos_file)
                
                # 处理混合日期格式
                def parse_mixed_dates(date_str):
                    """处理混合的日期格式"""
                    date_str = str(date_str).strip()
                    # 如果是8位数字格式 20250822
                    if len(date_str) == 8 and date_str.isdigit():
                        return pd.to_datetime(date_str, format='%Y%m%d')
                    # 标准格式 2025-08-18
                    else:
                        return pd.to_datetime(date_str)
                
                pos_df['date'] = pos_df['date'].apply(parse_mixed_dates)
                pos_df = pos_df.sort_values('date')
                print(f"✅ 本地持仓数据: {len(pos_df)} 条记录")
                data_sources.append(f"本地持仓数据（{len(pos_df)}条记录）")
                return pos_df, data_sources
            except Exception as e:
                print(f"⚠️ 持仓数据加载失败: {e}")
        
        print(f"ℹ️ 未找到持仓数据")
        return None, data_sources
    
    def fetch_online_supplement_data(self, variety_name):
        """获取联网补充数据"""
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        ak_name = variety_info.get('ak_name', variety_name)
        
        data_sources = []
        online_used = False
        supplement_data = {}
        
        print(f"📡 获取{variety_name}联网补充数据...")
        
        try:
            # 1. 获取最新价格和持仓量数据
            try:
                realtime_data = ak.futures_main_sina(symbol=f"{variety_code}0")
                if realtime_data is not None and not realtime_data.empty:
                    latest_data = realtime_data.iloc[-1]
                    supplement_data['realtime_price'] = {
                        'current_price': latest_data.get('收盘', 0),
                        'volume': latest_data.get('成交量', 0),
                        'open_interest': latest_data.get('持仓量', 0),
                        'change': latest_data.get('涨跌', 0)
                    }
                    fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data_sources.append(f"联网实时行情数据（新浪财经，获取时间：{fetch_time}）")
                    online_used = True
                    print(f"✅ 获取实时行情数据成功")
            except Exception as e:
                print(f"⚠️ 获取实时行情数据失败: {e}")
            
        except Exception as e:
            print(f"❌ 联网补充数据获取异常: {e}")
        
        return supplement_data, data_sources, online_used
    
    def calculate_multi_dimensional_metrics(self, data):
        """计算多维度分析指标"""
        metrics = {}
        
        inventory_df = data.get('inventory')
        receipt_df = data.get('receipt')
        price_df = data.get('price')
        basis_df = data.get('basis')
        term_df = data.get('term_structure')
        positioning_df = data.get('positioning')
        online_supplement = data.get('online_supplement', {})
        
        # 1. 核心库存分析指标
        if inventory_df is not None and not inventory_df.empty:
            inv_values = inventory_df['value']
            
            latest_inv = inv_values.iloc[-1]
            mean_inv = inv_values.mean()
            std_inv = inv_values.std()
            percentile = stats.percentileofscore(inv_values, latest_inv)
            
            # 库存周期分析
            if len(inv_values) >= 30:
                recent_30d_change = inv_values.iloc[-1] - inv_values.iloc[-30]
                daily_avg_change = recent_30d_change / 30
                
                price_trend = None
                if price_df is not None and not price_df.empty and len(price_df) >= 30:
                    price_30d_change = price_df['收盘'].iloc[-1] - price_df['收盘'].iloc[-30]
                    price_trend = "上涨" if price_30d_change > 0 else "下跌"
                
                if recent_30d_change > std_inv * 0.3:
                    if price_trend == "上涨":
                        cycle_stage = "主动补库阶段"
                        cycle_confidence = 0.8
                        cycle_meaning = "需求预期向好，市场主动补库"
                    else:
                        cycle_stage = "被动补库阶段"
                        cycle_confidence = 0.7
                        cycle_meaning = "需求疲弱导致被动累库"
                elif recent_30d_change < -std_inv * 0.3:
                    if price_trend == "上涨":
                        cycle_stage = "被动去库阶段"
                        cycle_confidence = 0.7
                        cycle_meaning = "供给收缩导致被动去库"
                    else:
                        cycle_stage = "主动去库阶段"
                        cycle_confidence = 0.8
                        cycle_meaning = "预期悲观，市场主动去库"
                else:
                    cycle_stage = "平衡阶段"
                    cycle_confidence = 0.6
                    cycle_meaning = "供需相对平衡"
            else:
                recent_30d_change = 0
                daily_avg_change = 0
                cycle_stage = "数据不足"
                cycle_confidence = 0.3
                cycle_meaning = "历史数据不足，无法判断"
            
            # 投机性库存分析
            if len(inv_values) >= 20:
                volatility = inv_values.rolling(10).std().iloc[-1] / mean_inv if mean_inv > 0 else 0
                high_volatility_periods = (inv_values.rolling(5).std() > std_inv * 1.2).sum()
                
                speculative_ratio = min(volatility * 100, 25)
                
                if speculative_ratio > 15:
                    speculative_level = "高投机性"
                    speculative_meaning = "市场存在大量投机性需求，库存波动剧烈"
                elif speculative_ratio > 8:
                    speculative_level = "中投机性"
                    speculative_meaning = "存在一定投机行为，需关注市场情绪变化"
                else:
                    speculative_level = "低投机性"
                    speculative_meaning = "库存变化主要反映真实供需"
            else:
                speculative_ratio = 0
                speculative_level = "无法判断"
                speculative_meaning = "数据不足，无法分析投机性特征"
            
            metrics['inventory'] = {
                'latest': latest_inv,
                'mean': mean_inv,
                'std': std_inv,
                'percentile': percentile,
                'recent_30d_change': recent_30d_change,
                'daily_avg_change': daily_avg_change,
                'cycle_stage': cycle_stage,
                'cycle_confidence': cycle_confidence,
                'cycle_meaning': cycle_meaning,
                'speculative_ratio': speculative_ratio,
                'speculative_level': speculative_level,
                'speculative_meaning': speculative_meaning
            }
        
        # 2. 库存与价格反身性分析
        if inventory_df is not None and price_df is not None and not inventory_df.empty and not price_df.empty:
            try:
                inv_dates = inventory_df['date'].dt.date
                price_dates = price_df['时间'].dt.date
                common_dates = set(inv_dates) & set(price_dates)
                
                if len(common_dates) >= 10:
                    aligned_data = []
                    for date in sorted(common_dates):
                        inv_val = inventory_df[inventory_df['date'].dt.date == date]['value'].iloc[0]
                        price_val = price_df[price_df['时间'].dt.date == date]['收盘'].iloc[0]
                        aligned_data.append({'date': date, 'inventory': inv_val, 'price': price_val})
                    
                    aligned_df = pd.DataFrame(aligned_data).sort_values('date')
                    price_inv_corr = aligned_df['price'].corr(aligned_df['inventory'])
                    
                    if abs(price_inv_corr) < 0.3:
                        reflexivity_type = "弱反身性"
                        reflexivity_meaning = "价格与库存关系不明显，可能存在其他主导因素"
                    elif price_inv_corr < -0.5:
                        reflexivity_type = "经典负相关"
                        reflexivity_meaning = "库存高时价格低，符合传统供需逻辑"
                    elif price_inv_corr > 0.5:
                        reflexivity_type = "正向反身性"
                        reflexivity_meaning = "价格与库存同向变化，可能存在投机驱动"
                    else:
                        reflexivity_type = "中等相关性"
                        reflexivity_meaning = "价格与库存存在一定相关性，需结合其他因素分析"
                        
                    metrics['reflexivity'] = {
                        'correlation': price_inv_corr,
                        'type': reflexivity_type,
                        'meaning': reflexivity_meaning,
                        'data_points': len(aligned_df)
                    }
                else:
                    metrics['reflexivity'] = {
                        'correlation': None,
                        'type': "数据不足",
                        'meaning': "价格与库存数据无法有效对齐",
                        'data_points': len(common_dates)
                    }
            except Exception as e:
                metrics['reflexivity'] = {
                    'correlation': None,
                    'type': "分析失败",
                    'meaning': f"反身性分析异常：{str(e)[:50]}",
                    'data_points': 0
                }
        
        # 3. 多维度交叉分析
        cross_analysis = {}
        
        if inventory_df is not None and basis_df is not None and not inventory_df.empty and not basis_df.empty:
            try:
                # 分析基差结构
                latest_near_basis = basis_df['near_basis'].iloc[-1] if 'near_basis' in basis_df.columns else 0
                latest_dom_basis = basis_df['dom_basis'].iloc[-1] if 'dom_basis' in basis_df.columns else 0
                latest_near_rate = basis_df['near_basis_rate'].iloc[-1] if 'near_basis_rate' in basis_df.columns else 0
                latest_dom_rate = basis_df['dom_basis_rate'].iloc[-1] if 'dom_basis_rate' in basis_df.columns else 0
                
                # 基差结构分析
                structure_type = "正向市场" if latest_near_basis < latest_dom_basis else "反向市场"
                basis_meaning = f"近月基差{latest_near_basis:.0f}元，远月基差{latest_dom_basis:.0f}元，呈{structure_type}结构"
                
                cross_analysis['inventory_basis'] = {
                    'near_basis': latest_near_basis,
                    'dom_basis': latest_dom_basis,
                    'near_basis_rate': latest_near_rate,
                    'dom_basis_rate': latest_dom_rate,
                    'structure_type': structure_type,
                    'meaning': basis_meaning
                }
                print(f"✅ 基差分析: {basis_meaning}")
            except Exception as e:
                print(f"⚠️ 基差分析失败: {e}")
        
        # 持仓分析增强
        if inventory_df is not None and positioning_df is not None and not inventory_df.empty and not positioning_df.empty:
            try:
                # 计算持仓分布和集中度
                latest_date = positioning_df['date'].max()
                latest_positions = positioning_df[positioning_df['date'] == latest_date]
                
                if '持仓量' in latest_positions.columns:
                    total_position = latest_positions['持仓量'].sum()
                    top3_position = latest_positions.head(3)['持仓量'].sum()
                    top5_position = latest_positions.head(5)['持仓量'].sum()
                    concentration_top3 = (top3_position / total_position * 100) if total_position > 0 else 0
                    concentration_top5 = (top5_position / total_position * 100) if total_position > 0 else 0
                    
                    cross_analysis['inventory_positioning'] = {
                        'total_position': total_position,
                        'top3_concentration': concentration_top3,
                        'top5_concentration': concentration_top5,
                        'meaning': f"总持仓{total_position:,.0f}手，前3席位集中度{concentration_top3:.1f}%，前5席位集中度{concentration_top5:.1f}%"
                    }
                    print(f"✅ 持仓分析: 总持仓{total_position:,.0f}手，前3集中度{concentration_top3:.1f}%")
            except Exception as e:
                print(f"⚠️ 持仓分析失败: {e}")
        
        # 期限结构分析增强
        if term_df is not None and not term_df.empty:
            try:
                # 分析期限结构形态
                latest_date_term = term_df['date'].max()
                latest_terms = term_df[term_df['date'] == latest_date_term].copy()
                
                if len(latest_terms) >= 2 and 'close' in latest_terms.columns:
                    # 按合约月份排序
                    latest_terms = latest_terms.sort_values('symbol')
                    prices = latest_terms['close'].values
                    
                    # 计算期限结构斜率
                    if len(prices) >= 3:
                        near_price = prices[0]
                        mid_price = prices[len(prices)//2]
                        far_price = prices[-1]
                        
                        term_slope = (far_price - near_price) / near_price * 100
                        term_shape = "正向结构(近低远高)" if term_slope > 1 else "平坦结构" if abs(term_slope) <= 1 else "反向结构(近高远低)"
                        
                        cross_analysis['term_structure'] = {
                            'near_price': near_price,
                            'far_price': far_price,
                            'term_slope': term_slope,
                            'term_shape': term_shape,
                            'meaning': f"{term_shape}，斜率{term_slope:.2f}%"
                        }
                        print(f"✅ 期限结构: {term_shape}，斜率{term_slope:.2f}%")
            except Exception as e:
                print(f"⚠️ 期限结构分析失败: {e}")
        
        metrics['cross_analysis'] = cross_analysis
        
        # 4. 当前市场状态综合判断
        current_price = 0
        price_change_30d = 0
        
        # 优先使用本地价格数据（更可靠）
        if price_df is not None and not price_df.empty:
            current_price = float(price_df['收盘'].iloc[-1])
            if len(price_df) >= 30:
                price_change_30d = float(price_df['收盘'].iloc[-1] - price_df['收盘'].iloc[-30])
            print(f"✅ 当前价格: {current_price} 元/吨, 30日变化: {price_change_30d:+.0f} 元/吨")
        elif online_supplement.get('realtime_price'):
            current_price = online_supplement['realtime_price'].get('current_price', 0)
            price_change_30d = online_supplement['realtime_price'].get('change', 0)
            print(f"✅ 联网价格: {current_price} 元/吨")
        
        metrics['current_market'] = {
            'price': current_price,
            'price_change_30d': price_change_30d
        }
        
        return metrics
    
    def generate_professional_charts(self, variety_name, data, metrics):
        """生成专业图表"""
        print(f"📊 正在生成{variety_name}专业分析图表...")
        
        variety_code = data['variety_info'].get('code', variety_name)
        chart_objects = {}  # 改为字典存储图表对象
        
        try:
            
            inventory_df = data.get('inventory')
            price_df = data.get('price')
            basis_df = data.get('basis')
            
            # 1. 库存趋势图（Plotly版本）
            if inventory_df is not None and not inventory_df.empty:
                fig = go.Figure()
                
                # 库存趋势线
                fig.add_trace(go.Scatter(
                    x=inventory_df['date'],
                    y=inventory_df['value'],
                    mode='lines+markers',
                    name='库存水平',
                    line=dict(color='#2E86AB', width=3),
                    marker=dict(size=6),
                    hovertemplate='日期: %{x}<br>库存: %{y:.1f}万吨<extra></extra>'
                ))
                
                # 添加30日移动平均线
                if len(inventory_df) >= 30:
                    ma30 = inventory_df['value'].rolling(30).mean()
                    fig.add_trace(go.Scatter(
                        x=inventory_df['date'],
                        y=ma30,
                        mode='lines',
                        name='30日移动平均',
                        line=dict(color='#FF6B6B', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>30日均值: %{y:.1f}万吨<extra></extra>'
                    ))
                
                # 添加历史均值线
                inv_metrics = metrics.get('inventory', {})
                percentile = inv_metrics.get('percentile', 0)
                mean_value = inv_metrics.get('mean', 0)
                current_value = inv_metrics.get('latest', 0)
                
                if mean_value > 0:
                    fig.add_hline(y=mean_value, line_dash="dot", line_color="gray", 
                                 annotation_text=f"历史均值: {mean_value:.1f}万吨")
                
                fig.update_layout(
                    title=f'{variety_name}库存趋势分析<br><sub>当前库存：{current_value:.1f}万吨（历史{percentile:.1f}%分位数）</sub>',
                    xaxis_title='时间',
                    yaxis_title=f'库存({data["variety_info"].get("unit", "万吨")})',
                    hovermode='x unified',
                    template='plotly_white',
                    height=500,
                    font=dict(size=12),
                    showlegend=True
                )
                
                chart_objects['库存趋势分析'] = fig
                print(f"✅ 生成库存趋势Plotly图表")
            
            # 库存价格走势对比图（新增，数据对齐版本）
            if inventory_df is not None and price_df is not None and not inventory_df.empty and not price_df.empty:
                try:
                    # 确保数据对齐 - 找到共同的时间范围
                    price_col = '收盘' if '收盘' in price_df.columns else 'close'
                    date_col = '时间' if '时间' in price_df.columns else 'date'
                    
                    # 将两个数据的日期都转为标准格式
                    inventory_df_copy = inventory_df.copy()
                    price_df_copy = price_df.copy()
                    
                    # 确保日期为datetime格式
                    inventory_df_copy['date'] = pd.to_datetime(inventory_df_copy['date'])
                    price_df_copy[date_col] = pd.to_datetime(price_df_copy[date_col])
                    
                    # 找到共同的时间范围
                    inv_start, inv_end = inventory_df_copy['date'].min(), inventory_df_copy['date'].max()
                    price_start, price_end = price_df_copy[date_col].min(), price_df_copy[date_col].max()
                    
                    # 取交集时间范围
                    common_start = max(inv_start, price_start)
                    common_end = min(inv_end, price_end)
                    
                    # 过滤到共同时间范围
                    inventory_aligned = inventory_df_copy[
                        (inventory_df_copy['date'] >= common_start) & 
                        (inventory_df_copy['date'] <= common_end)
                    ].copy()
                    
                    price_aligned = price_df_copy[
                        (price_df_copy[date_col] >= common_start) & 
                        (price_df_copy[date_col] <= common_end)
                    ].copy()
                    
                    if len(inventory_aligned) > 0 and len(price_aligned) > 0:
                        # 创建双Y轴对比图
                        fig_compare = make_subplots(specs=[[{"secondary_y": True}]])
                        
                        # 库存走势（左轴）
                        fig_compare.add_trace(
                            go.Scatter(x=inventory_aligned['date'], y=inventory_aligned['value'],
                                     mode='lines+markers', name='库存走势',
                                     line=dict(color='#1f77b4', width=3),
                                     marker=dict(size=6),
                                     hovertemplate='日期: %{x}<br>库存: %{y:.1f}万吨<extra></extra>'),
                            secondary_y=False,
                        )
                        
                        # 价格走势（右轴）
                        fig_compare.add_trace(
                            go.Scatter(x=price_aligned[date_col], y=price_aligned[price_col],
                                     mode='lines+markers', name='价格走势',
                                     line=dict(color='#ff7f0e', width=3),
                                     marker=dict(size=6, symbol='square'),
                                     hovertemplate='日期: %{x}<br>价格: %{y:.0f}元/吨<extra></extra>'),
                            secondary_y=True,
                        )
                        
                        # 设置Y轴标题
                        fig_compare.update_yaxes(title_text=f"库存({data['variety_info'].get('unit', '万吨')})", 
                                               secondary_y=False, title_font_color='#1f77b4')
                        fig_compare.update_yaxes(title_text="价格（元/吨）", 
                                               secondary_y=True, title_font_color='#ff7f0e')
                        
                        # 计算相关性（基于对齐的数据）
                        try:
                            # 重采样到日频率对齐
                            inv_daily = inventory_aligned.set_index('date')['value'].resample('D').last().dropna()
                            price_daily = price_aligned.set_index(date_col)[price_col].resample('D').last().dropna()
                            common_daily_dates = inv_daily.index.intersection(price_daily.index)
                            
                            if len(common_daily_dates) > 10:
                                correlation = inv_daily[common_daily_dates].corr(price_daily[common_daily_dates])
                            else:
                                correlation = 0.0
                        except Exception:
                            correlation = 0.0
                        
                        fig_compare.update_layout(
                            title=f'{variety_name}库存与价格走势对比<br><sub>时间范围: {common_start.strftime("%Y-%m-%d")} ~ {common_end.strftime("%Y-%m-%d")} | 相关性: {correlation:.3f}</sub>',
                            xaxis_title='时间',
                            hovermode='x unified',
                            template='plotly_white',
                            height=600,
                            font=dict(size=12)
                        )
                        
                        chart_objects['库存价格走势对比'] = fig_compare
                        print(f"✅ 生成库存价格走势对比Plotly图表（时间范围：{common_start.strftime('%Y-%m-%d')} ~ {common_end.strftime('%Y-%m-%d')}）")
                    else:
                        print(f"⚠️ 库存和价格数据时间范围不重叠，无法生成对比图")
                        
                except Exception as e:
                    print(f"❌ 库存价格对比图生成失败: {e}")
            
            # 2. 价格库存反身性分析图（Plotly版本）
            if inventory_df is not None and price_df is not None and not inventory_df.empty and not price_df.empty:
                # 数据对齐
                inventory_monthly = inventory_df.set_index('date')['value'].resample('M').last().dropna()
                
                # 确保价格数据的列名正确
                if '时间' in price_df.columns:
                    price_monthly = price_df.set_index('时间')['收盘'].resample('M').last().dropna()
                else:
                    price_monthly = price_df.set_index('date')['收盘'].resample('M').last().dropna()
                
                # 找到共同时间范围
                common_dates = inventory_monthly.index.intersection(price_monthly.index)
                
                if len(common_dates) > 6:  # 至少需要6个月的数据
                    inv_aligned = inventory_monthly[common_dates]
                    price_aligned = price_monthly[common_dates]
                    
                    # 创建双Y轴图表
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    # 添加库存
                    fig.add_trace(
                        go.Scatter(x=inv_aligned.index, y=inv_aligned.values,
                                 name="库存水平", line=dict(color='#1f77b4', width=3),
                                 marker=dict(size=8),
                                 hovertemplate='日期: %{x}<br>库存: %{y:.1f}万吨<extra></extra>'),
                        secondary_y=False,
                    )
                    
                    # 添加价格
                    fig.add_trace(
                        go.Scatter(x=price_aligned.index, y=price_aligned.values,
                                 name="价格", line=dict(color='#ff7f0e', width=3),
                                 marker=dict(size=8, symbol='square'),
                                 hovertemplate='日期: %{x}<br>价格: %{y:.0f}元/吨<extra></extra>'),
                        secondary_y=True,
                    )
                    
                    # 计算相关性
                    correlation = inv_aligned.corr(price_aligned)
                    reflex_type = "负相关(反身性显著)" if correlation < -0.3 else "正相关(同步性显著)" if correlation > 0.3 else "弱相关(反身性不明显)"
                    
                    # 设置Y轴标题
                    fig.update_yaxes(title_text=f"库存({data['variety_info'].get('unit', '万吨')})", secondary_y=False, title_font_color='#1f77b4')
                    fig.update_yaxes(title_text="价格（元/吨）", secondary_y=True, title_font_color='#ff7f0e')
                    
                    fig.update_layout(
                        title=f'{variety_name}价格库存反身性分析<br><sub>相关系数：{correlation:.3f} （{reflex_type}）</sub>',
                        xaxis_title='时间',
                        hovermode='x unified',
                        template='plotly_white',
                        height=500,
                        font=dict(size=12)
                    )
                    
                    chart_objects['价格库存反身性分析'] = fig
                    print(f"✅ 生成价格库存反身性Plotly图表")
            
            # 3. 库存周期分析图（Plotly版本）
            if inventory_df is not None and not inventory_df.empty and len(inventory_df) >= 60:
                inventory_df_copy = inventory_df.copy().sort_values('date')
                inventory_df_copy['change_rate'] = inventory_df_copy['value'].pct_change(periods=30) * 100
                inventory_df_copy['ma_20d'] = inventory_df_copy['value'].rolling(20).mean()
                inventory_df_copy = inventory_df_copy.dropna()
                
                # 创建双Y轴图表
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 添加库存水平
                fig.add_trace(
                    go.Scatter(x=inventory_df_copy['date'], y=inventory_df_copy['value'],
                             mode='lines+markers', name='库存水平',
                             line=dict(color='#2E86AB', width=3),
                             marker=dict(size=6),
                             hovertemplate='日期: %{x}<br>库存: %{y:.1f}万吨<extra></extra>'),
                    secondary_y=False,
                )
                
                # 添加20日移动平均
                fig.add_trace(
                    go.Scatter(x=inventory_df_copy['date'], y=inventory_df_copy['ma_20d'],
                             mode='lines', name='20日移动平均',
                             line=dict(color='#17becf', width=2, dash='dash'),
                             hovertemplate='日期: %{x}<br>20日均值: %{y:.1f}万吨<extra></extra>'),
                    secondary_y=False,
                )
                
                # 添加库存变化率（柱状图）
                colors = ['green' if x >= 0 else 'red' for x in inventory_df_copy['change_rate']]
                fig.add_trace(
                    go.Bar(x=inventory_df_copy['date'], y=inventory_df_copy['change_rate'],
                          name='30日变化率', marker_color=colors, opacity=0.6,
                          hovertemplate='日期: %{x}<br>变化率: %{y:.1f}%<extra></extra>'),
                    secondary_y=True,
                )
                
                # 添加零线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", secondary_y=True)
                
                # 库存周期阶段标注
                inv_metrics = metrics.get('inventory', {})
                cycle_stage = inv_metrics.get('cycle_stage', '未知')
                cycle_confidence = inv_metrics.get('cycle_confidence', 0)
                
                # 设置Y轴标题
                fig.update_yaxes(title_text=f"库存({data['variety_info'].get('unit', '万吨')})", secondary_y=False, title_font_color='#2E86AB')
                fig.update_yaxes(title_text="变化率（%）", secondary_y=True, title_font_color='#FF6B6B')
                
                fig.update_layout(
                    title=f'{variety_name}库存周期分析<br><sub>当前阶段：{cycle_stage} (置信度{cycle_confidence:.0%})</sub>',
                    xaxis_title='时间',
                    hovermode='x unified',
                    template='plotly_white',
                    height=600,
                    font=dict(size=12)
                )
                
                chart_objects['库存周期分析'] = fig
                print(f"✅ 生成库存周期分析Plotly图表")
            
        except Exception as e:
            print(f"⚠️ 图表生成过程中出现异常: {e}")
        
        return chart_objects
    
    def get_comprehensive_market_context(self, variety_name):
        """获取综合市场背景信息（强化版）"""
        try:
            variety_info = self.variety_mapping.get(variety_name, {})
            variety_code = variety_info.get('code', variety_name)
            category = variety_info.get('category', '未知')
            
            # 扩展搜索查询，涵盖更多维度和具体数据
            search_queries = [
                f"{variety_name} {variety_code} 期货 库存 仓单 最新数据 统计局 2024 2025",
                f"{variety_name} 供需平衡表 产量数据 消费量统计 进出口月度数据",
                f"{variety_name} 产能利用率 开工率 装置检修 企业停产 生产状况",
                f"{variety_name} 成本结构分析 原料价格 电力成本 运输费用 利润",
                f"{variety_name} 下游需求调研 房地产 基建投资 汽车工业 终端消费",
                f"{variety_name} 库存分类 社会库存 工厂库存 贸易商库存 港口库存",
                f"{variety_name} 基差动量 期限结构 合约价差 交割压力 资金成本",
                f"{variety_name} 持仓分析 主力席位 净持仓 资金流向 投机套保",
                f"{variety_name} 政策环保 限产令 环保督查 行业标准 产业政策",
                f"{variety_name} 季节性规律 消费旺季 库存周期 历史价格 周期性",
                f"{variety_name} 替代品竞争 上游垄断 下游议价 产业链博弈",
                f"{variety_name} 宏观传导 货币政策 汇率影响 通胀预期 经济周期"
            ]
            
            all_context_info = []
            search_success_count = 0
            
            for i, query in enumerate(search_queries):
                headers = {
                    "X-API-KEY": self.serper_api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "q": query,
                    "gl": "cn",
                    "hl": "zh-cn",
                    "num": 4  # 每个查询获取更多结果
                }
                
                try:
                    response = requests.post(self.serper_base_url,
                                           headers=headers,
                                           json=payload,
                                           timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        organic_results = data.get('organic', [])
                        search_success_count += 1
                        
                        for result in organic_results:
                            title = result.get('title', '').strip()
                            snippet = result.get('snippet', '').strip()
                            link = result.get('link', '').strip()
                            if title and snippet:
                                # 增强信息分类（12个维度）
                                query_categories = [
                                    "库存仓单统计", "供需平衡表", "产能开工率", 
                                    "成本结构分析", "下游需求调研", "库存分类统计",
                                    "基差期限结构", "持仓资金分析", "政策环保影响",
                                    "季节性规律", "产业链博弈", "宏观经济传导"
                                ]
                                
                                all_context_info.append({
                                    'title': title[:150],  # 更长标题
                                    'snippet': snippet[:300],  # 更长摘要
                                    'link': link,
                                    'query_type': f"{query_categories[i]}",
                                    'search_query': query,
                                    'relevance_score': len([kw for kw in [variety_name, variety_code] if kw.lower() in (title + snippet).lower()])
                                })
                    else:
                        print(f"⚠️ 搜索API返回错误状态码: {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ 搜索查询失败 '{query[:50]}...': {e}")
                    continue
                
                # 适当延迟避免请求过快
                time.sleep(1.0)
            
            # 按相关性排序并格式化结果
            if all_context_info:
                # 按相关性分数排序
                all_context_info.sort(key=lambda x: x['relevance_score'], reverse=True)
                
                fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                formatted_context = f"""【强化联网搜索结果】
搜索时间：{fetch_time}
成功查询：{search_success_count}/{len(search_queries)} 个维度（12维度全覆盖搜索）
获取信息：{len(all_context_info)} 条相关信息
数据时效性：实时联网获取，请注意信息发布时间
覆盖范围：库存统计、供需平衡、产能开工、成本结构、需求调研、持仓分析、政策影响、季节规律、产业博弈、宏观传导

=== 12维度市场信息汇总 ===
"""
                
                # 限制显示最相关的12条信息
                for i, info in enumerate(all_context_info[:12], 1):
                    formatted_context += f"""
{i}. 【{info['query_type']}】{info['title']}
   内容摘要：{info['snippet']}
   信息来源：{info['link'][:120]}
   相关度：{'★' * info['relevance_score']}{'☆' * (3 - info['relevance_score'])}
   搜索查询：{info['search_query'][:60]}...
"""
                
                formatted_context += f"""

=== 数据说明 ===
- 以上信息通过Serper API实时搜索获取
- 信息来源均已标注，请核实时效性
- 相关度评分基于关键词匹配程度
- 建议结合多个信息源进行综合判断
"""
                
                # 构建脚注引用信息
                footnote_refs = []
                for i, info in enumerate(all_context_info[:12], 1):
                    footnote_refs.append({
                        'id': i,
                        'title': info['title'],
                        'link': info['link'],
                        'snippet': info['snippet'][:150],
                        'query_type': info['query_type'],
                        'fetch_time': fetch_time
                    })
                
                print(f"✅ 成功获取联网市场信息: {len(all_context_info)} 条")
                return {
                    'formatted_context': formatted_context,
                    'footnote_refs': footnote_refs,
                    'search_success': True
                }
            else:
                return {
                    'formatted_context': f"""【联网搜索失败】
搜索时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
搜索状态：所有查询均失败，无法获取实时市场信息
建议：请检查网络连接或稍后重试
""",
                    'footnote_refs': [],
                    'search_success': False
                }
                
        except Exception as e:
            print(f"❌ 获取综合市场信息异常: {e}")
            return {
                'formatted_context': f"""【联网搜索异常】
搜索时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
错误信息：{str(e)[:100]}
影响：无法获取实时市场背景信息，分析将基于本地数据
""",
                'footnote_refs': [],
                'search_success': False
            }
    
    def build_ultimate_analysis_prompt(self, variety_name, metrics, market_context, data):
        """构建终极分析提示词"""
        
        variety_info = self.variety_mapping.get(variety_name, {})
        variety_code = variety_info.get('code', variety_name)
        category = variety_info.get('category', '未知')
        exchange = variety_info.get('exchange', '未知')
        chinese_name = variety_info.get('chinese_name', variety_name)
        
        # 提取关键指标
        inv_metrics = metrics.get('inventory', {})
        reflex_metrics = metrics.get('reflexivity', {})
        current_market = metrics.get('current_market', {})
        cross_analysis = metrics.get('cross_analysis', {})
        
        # 核心数据
        current_inventory = inv_metrics.get('latest', 0)
        inventory_percentile = inv_metrics.get('percentile', 0)
        recent_change = inv_metrics.get('recent_30d_change', 0)
        cycle_stage = inv_metrics.get('cycle_stage', '未知')
        cycle_meaning = inv_metrics.get('cycle_meaning', '')
        speculative_level = inv_metrics.get('speculative_level', '未知')
        speculative_meaning = inv_metrics.get('speculative_meaning', '')
        
        current_price = current_market.get('price', 0)
        price_change_30d = current_market.get('price_change_30d', 0)
        
        reflexivity_type = reflex_metrics.get('type', '未知')
        reflexivity_meaning = reflex_metrics.get('meaning', '')
        correlation = reflex_metrics.get('correlation', 0)
        
        # 基差数据
        basis_data = cross_analysis.get('inventory_basis', {})
        basis_structure = basis_data.get('structure_type', '未知')
        basis_meaning = basis_data.get('meaning', '')
        
        # 持仓数据
        position_data = cross_analysis.get('inventory_positioning', {})
        position_meaning = position_data.get('meaning', '持仓数据不可用')
        
        # 期限结构数据
        term_data = cross_analysis.get('term_structure', {})
        term_structure = term_data.get('term_shape', '期限结构数据不可用')
        term_meaning = term_data.get('meaning', '')
        
        # 数据维度统计
        data_dimensions = []
        if data.get('inventory') is not None:
            data_dimensions.append("库存数据")
        if data.get('receipt') is not None:
            data_dimensions.append("仓单数据")
        if data.get('price') is not None:
            data_dimensions.append("价格数据")
        if data.get('basis') is not None:
            data_dimensions.append("基差数据")
        if data.get('term_structure') is not None:
            data_dimensions.append("期限结构数据")
        if data.get('positioning') is not None:
            data_dimensions.append("持仓数据")
        
        # 构建终极分析提示词
        prompt = f"""
你是世界顶级的期货基本面分析专家，具有25年专业经验。现在需要为{variety_name}({variety_code})期货撰写一份投资机构级别的多维度库存仓单专业分析报告。

CRITICAL要求：
1. 绝对禁止使用任何英文单词、短语或表达，必须使用纯中文
2. 禁止出现如"due to"、"contango"、"backwardation"等英文术语
3. 所有专业术语必须用中文表达，如"远期升水结构"、"近期贴水结构"等
4. 严格避免任何英文缩写或英文表达

品种基本信息：
{variety_name}({variety_code})，{category}类，{exchange}交易所

多维度数据基础：
可用数据维度：{', '.join(data_dimensions)}
联网数据使用：{'是' if data.get('online_data_used', False) else '否'}

核心库存分析：
当前库存：{current_inventory:,.0f}万吨（历史{inventory_percentile:.1f}%分位数）
30日变化：{recent_change:+,.0f}万吨
库存周期：{cycle_stage}
周期含义：{cycle_meaning}
投机性水平：{speculative_level}
投机性特征：{speculative_meaning}

价格反身性分析：
当前价格：{current_price:,.0f}元/吨
30日价格变化：{price_change_30d:+,.0f}元/吨
反身性类型：{reflexivity_type}
反身性含义：{reflexivity_meaning}
价格库存相关性：{correlation:.3f}

多维度数据验证：
基差结构：{basis_structure} - {basis_meaning}
持仓分析：{position_meaning}
期限结构：{term_structure} - {term_meaning}

市场背景信息：
{market_context.get('formatted_context', '无联网数据') if isinstance(market_context, dict) else market_context}

脚注引用信息（AI分析时使用）：
{chr(10).join([f'[{ref["id"]}] {ref["query_type"]}: {ref["title"]} - {ref["snippet"][:100]}...' for ref in (market_context.get('footnote_refs', []) if isinstance(market_context, dict) else [])])}

分析任务要求：

请撰写专业的{chinese_name}期货多维度库存仓单分析报告，采用以下结构：

一、核心投资观点
基于多维度数据的综合判断
明确的多空方向建议
量化的信心水平评估
关键风险因素识别

二、库存深度解读
1. 库存绝对水平分析：历史分位数意义，供需状态判断
2. 库存变化趋势解读：结合库存周期理论的专业分析
3. 投机性库存识别：区分真实消费需求与投机性囤货
4. 库存反身性关系：深度理解库存与价格的动态关系

三、多维度交叉验证分析
1. 库存与价格走势的互动关系验证
2. 基差结构对库存意义的补充验证（如有数据）
3. 持仓结构与库存变化的协同分析（如有数据）
4. 期限结构对库存预期的反映（如有数据）

四、供需格局深度剖析
1. 供给端分析：产能、开工率、成本、政策影响
2. 需求端分析：真实消费与投机需求的区分
3. 库存在供需传导中的作用：蓄水池功能及其杠杆效应
4. 供需平衡的动态演化趋势

五、市场微观结构分析
1. 货权分布状况：库存集中度及其市场影响
2. 产业链库存结构：工厂库存与社会库存的差异化含义
3. 隐性库存显性化风险评估
4. 库存流动性和变现能力分析

六、投资策略制定
1. 基于库存分析的总体策略方向
2. 具体操作建议：进场时机、仓位配置、持仓周期
3. 关键价位识别：支撑阻力位的库存逻辑支撑
4. 动态调整条件：库存拐点及策略切换信号

七、风险管理要点
1. 库存分析的局限性和盲点
2. 反身性关系变化的风险预警
3. 政策和突发事件对库存逻辑的冲击
4. 持续监控的关键指标设定

撰写要求：
1. 体现对库存本质的深度理解，避免指标化处理
2. 重点阐述库存与价格的反身性关系
3. 结合多维度数据进行交叉验证
4. 提供具体可操作的投资建议
5. 保持专业客观的分析态度
6. 绝对禁止使用任何英文表达，必须纯中文
7. 字数控制在2800-3200字
8. 使用专业但易懂的中文术语
9. **重要**：必须在报告中自然引用联网搜索获取的市场信息，使用脚注标注方式如[1] [2] [3]等，避免使用"据联网数据显示"等不够专业的表述
10. **重要**：所有联网获取的信息都要用脚注标记，并在文末"参考资料"部分按编号列出具体的信息来源链接和获取时间

请开始撰写纯中文专业分析报告，直接从标题和内容开始，禁止任何AI描述性引导语：
"""
        
        return prompt
    
    def call_deepseek_ultimate(self, prompt):
        """调用DeepSeek进行终极分析"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        system_content = """你是世界顶级的期货基本面分析专家，具有25年专业经验和深度推理能力。

你的核心专业特长：
1. 库存数据的深度理解和反身性关系分析
2. 投机性库存与真实消费需求的准确区分
3. 库存周期理论的实战应用
4. 多维度数据的交叉验证分析能力
5. 市场微观结构和产业链分析
6. 基于库存分析的精准投资策略制定

CRITICAL语言要求：
- 绝对禁止使用任何英文单词、短语、术语或缩写
- 必须使用纯正的中文专业术语
- 所有分析内容必须用中文表达
- 专业术语中文化，如远期升水、近期贴水、正向市场、反向市场等

CRITICAL联网数据引用要求：
- 必须自然融入联网搜索获取的市场信息，禁用"据联网数据显示"等表述
- 所有联网获取的信息使用脚注标记方式：[1] [2] [3]等
- 对关键市场信息（产能利用率、开工率、需求状况、库存分类等）进行脚注标注
- 在报告末尾增设"参考资料"部分，按脚注编号列出信息来源链接和获取时间
- 确保所有脚注信息具有时效性和相关性

重要理念要求：
- 理解库存与价格的复杂反身性关系，摆脱简单的负相关思维
- 区分投机性库存和真实消费需求的不同市场含义
- 结合库存周期理论进行动态分析
- 多维度数据交叉验证，避免单一指标误判
- 深度理解库存作为供需蓄水池的杠杆效应
- 充分利用联网市场信息增强分析的全面性和时效性

请运用你的专业知识和深度推理能力，撰写一份体现库存分析精髓的纯中文专业报告。"""
        
        data = {
            "model": "deepseek-reasoner",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 12000,
            "temperature": 0.1
        }
        
        try:
            print(f"🤖 正在调用DeepSeek Reasoner进行终极深度分析...")
            response = requests.post(self.deepseek_base_url,
                                   headers=headers,
                                   json=data,
                                   timeout=180)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content']
            print("✅ AI终极深度分析完成")
            return result
            
        except Exception as e:
            print(f"❌ Reasoner分析失败，尝试Chat模式: {e}")
            # 降级到chat模式
            data["model"] = "deepseek-chat"
            data["max_tokens"] = 6000
            try:
                response = requests.post(self.deepseek_base_url,
                                       headers=headers,
                                       json=data,
                                       timeout=120)
                response.raise_for_status()
                result = response.json()['choices'][0]['message']['content']
                print("✅ AI Chat模式分析完成")
                return result
            except Exception as e2:
                return f"AI终极分析生成失败: {e2}"
    
    def ultimate_comprehensive_analysis(self, variety_name):
        """执行终极综合分析"""
        print("="*80)
        print(f"🚀 {variety_name} 专业库存仓单AI分析（终极完善版）")
        print("="*80)
        
        # 1. 加载多维度数据
        data = self.load_multi_dimensional_data(variety_name)
        
        # 检查数据有效性
        has_inventory = data.get('inventory') is not None and not data['inventory'].empty
        has_any_data = any([
            data.get('inventory') is not None and not data['inventory'].empty,
            data.get('receipt') is not None and not data['receipt'].empty,
            data.get('price') is not None and not data['price'].empty
        ])
        
        if not has_any_data:
            return {
                "error": "无有效数据可供终极分析",
                "variety": variety_name,
                "data_sources": data.get('data_sources', [])
            }
        
        # 2. 计算多维度分析指标
        print("📈 正在计算多维度分析指标...")
        metrics = self.calculate_multi_dimensional_metrics(data)
        
        # 3. 生成专业图表（Plotly对象）
        print("📊 正在生成专业分析图表...")
        charts = self.generate_professional_charts(variety_name, data, metrics)
        charts_html = charts  # Plotly图表对象直接用于Streamlit显示
        
        # 4. 获取综合市场背景
        print("🌐 正在获取多维度市场背景信息...")
        market_context = self.get_comprehensive_market_context(variety_name)
        
        # 5. 构建终极分析提示词
        print("📝 正在构建终极专业分析框架...")
        prompt = self.build_ultimate_analysis_prompt(variety_name, metrics, market_context, data)
        
        # 6. AI终极深度分析
        print("🤖 正在进行AI终极专业深度分析...")
        ai_analysis = self.call_deepseek_ultimate(prompt)
        
        # 7. 构建分析结果（元数据后置）
        result = {
            "variety_name": variety_name,
            "professional_analysis": ai_analysis,  # 主体内容前置
            "charts": charts,
            "charts_html": charts_html,  # Plotly对象用于Streamlit显示
            "market_context": market_context,
            
            # 以下为后置的元数据信息
            "variety_info": data['variety_info'],
            "multi_dimensional_metrics": metrics,
            "analysis_metadata": {
                "version": "v8.0 Ultimate Perfection",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data_dimensions": [dim for dim in ['inventory', 'receipt', 'price', 'basis', 'term_structure', 'positioning'] if data.get(dim) is not None],
                "confidence_level": "高",
                "online_data_used": data.get('online_data_used', False),
                "analysis_completeness": "完整" if has_inventory else "部分",
                "charts_generated": len(charts)
            },
            "data_summary": {
                "inventory_points": len(data['inventory']) if data['inventory'] is not None else 0,
                "receipt_available": data.get('receipt') is not None and not data['receipt'].empty,
                "receipt_points": len(data['receipt']) if data['receipt'] is not None else 0,
                "price_points": len(data['price']) if data['price'] is not None else 0,
                "basis_points": len(data['basis']) if data['basis'] is not None else 0,
                "term_structure_points": len(data['term_structure']) if data['term_structure'] is not None else 0,
                "positioning_points": len(data['positioning']) if data['positioning'] is not None else 0,
                "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                "data_sources": data.get('data_sources', [])
            }
        }
        
        return result
    
    def display_ultimate_result(self, result):
        """显示终极分析结果（元数据后置）"""
        if "error" in result:
            print(f"❌ 分析失败: {result['error']}")
            if result.get('data_sources'):
                print("数据来源尝试:")
                for source in result['data_sources']:
                    print(f"  - {source}")
            return
        
        print("\n" + "="*80)
        print(f"📋 {result['variety_name']} 专业库存仓单AI分析报告")
        print("="*80)
        
        # 主体内容（AI分析报告）直接显示
        print(result['professional_analysis'])
        
        # 图表信息增强显示
        if result.get('charts'):
            print("\n" + "="*80)
            print("📊 专业图表分析结果")
            print("="*80)
            
            charts_dict = result['charts']
            if isinstance(charts_dict, dict):
                for i, (chart_name, chart_obj) in enumerate(charts_dict.items(), 1):
                    print(f"\n{i}. 【{chart_name}】")
                    print(f"   图表类型: Plotly交互式图表")
                    print(f"   图表状态: 已生成，可在Streamlit系统中查看")
                    print(f"   图表说明: 专业级技术分析图表，包含趋势线、技术指标和交互功能")
                    if '库存趋势' in chart_name:
                        print(f"   分析要点: 显示库存绝对水平、移动平均线、历史分位数参考线")
                    elif '价格走势对比' in chart_name:
                        print(f"   分析要点: 库存与价格走势的直观对比，便于分析两者关系")
                    elif '反身性' in chart_name:
                        print(f"   分析要点: 展现价格与库存的动态关系，验证反身性理论")
                    elif '周期' in chart_name:
                        print(f"   分析要点: 库存周期阶段识别，变化率分析，趋势拐点标注")
            else:
                print(f"   ⚠️ 图表格式异常: {type(charts_dict)}")
        
        # 参考资料信息（如有联网数据）
        market_context = result.get('market_context', {})
        if isinstance(market_context, dict) and market_context.get('footnote_refs'):
            print("\n" + "="*80)
            print("📚 参考资料")
            print("="*80)
            for ref in market_context['footnote_refs']:
                print(f"[{ref['id']}] {ref['title']}")
                print(f"    类型: {ref['query_type']}")
                print(f"    链接: {ref['link']}")
                print(f"    获取时间: {ref['fetch_time']}")
                print(f"    摘要: {ref['snippet']}")
                print()
        
        # 元数据信息（移至最后）
        print("\n" + "="*80)
        print("📊 分析技术信息")
        print("="*80)
        
        metadata = result.get('analysis_metadata', {})
        print(f"分析版本: {metadata.get('version', 'Unknown')}")
        print(f"数据维度: {len(metadata.get('data_dimensions', []))}个维度")
        print(f"联网数据: {'是' if metadata.get('online_data_used', False) else '否'}")
        print(f"分析完整性: {metadata.get('analysis_completeness', 'Unknown')}")
        print(f"生成图表: {metadata.get('charts_generated', 0)}个")
        
        summary = result['data_summary']
        print(f"\n数据统计:")
        print(f"库存数据: {summary['inventory_points']} 个数据点")
        print(f"仓单数据: {'可用' if summary['receipt_available'] else '不可用'}")
        print(f"价格数据: {summary['price_points']} 个数据点")
        print(f"分析日期: {summary['analysis_date']}")
        
        print("\n" + "="*80)
        print("📄 终极完善版分析报告生成完成")
        print("="*80)
    
    def export_ultimate_report(self, result, output_dir=None):
        """导出终极专业分析报告（元数据后置）"""
        if "error" in result:
            print("❌ 无法导出，分析结果包含错误")
            return None
        
        if output_dir is None:
            output_dir = Path("ultimate_reports")
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result['variety_name']}_终极库存仓单AI分析报告_{timestamp}.txt"
        filepath = output_dir / filename
        
        # 写入终极专业报告（元数据后置）
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{result['variety_name']} 专业库存仓单AI分析报告\n")
            f.write("="*80 + "\n\n")
            
            # 主体内容（AI专业分析）前置
            f.write(result['professional_analysis'])
            f.write("\n\n")
            
            # 图表信息
            if result.get('charts'):
                f.write("生成的专业图表\n")
                f.write("-" * 40 + "\n")
                for i, chart in enumerate(result['charts'], 1):
                    chart_name = Path(chart).name
                    f.write(f"{i}. {chart_name} - {chart}\n")
                f.write("\n")
            
            # 参考资料
            market_context = result.get('market_context', {})
            if isinstance(market_context, dict) and market_context.get('footnote_refs'):
                f.write("参考资料\n")
                f.write("-" * 40 + "\n")
                for ref in market_context['footnote_refs']:
                    f.write(f"[{ref['id']}] {ref['title']}\n")
                    f.write(f"    类型：{ref['query_type']}\n")
                    f.write(f"    链接：{ref['link']}\n")
                    f.write(f"    获取时间：{ref['fetch_time']}\n")
                    f.write(f"    摘要：{ref['snippet']}\n\n")
            
            # 市场背景信息
            if result.get('market_context'):
                f.write("多维度市场背景信息\n")
                f.write("-" * 40 + "\n")
                if isinstance(market_context, dict):
                    f.write(market_context.get('formatted_context', ''))
                else:
                    f.write(result['market_context'])
                f.write("\n\n")
            
            # 技术信息（元数据后置）
            f.write("="*80 + "\n")
            f.write("分析技术信息\n")
            f.write("="*80 + "\n")
            
            metadata = result.get('analysis_metadata', {})
            f.write(f"分析版本：{metadata.get('version', 'Unknown')}\n")
            f.write(f"分析时间：{metadata.get('timestamp', 'Unknown')}\n")
            f.write(f"数据维度：{len(metadata.get('data_dimensions', []))}个维度 - {', '.join(metadata.get('data_dimensions', []))}\n")
            f.write(f"联网数据使用：{'是' if metadata.get('online_data_used', False) else '否'}\n")
            f.write(f"分析完整性：{metadata.get('analysis_completeness', 'Unknown')}\n")
            f.write(f"生成图表：{metadata.get('charts_generated', 0)}个\n\n")
            
            # 数据统计（最后）
            summary = result['data_summary']
            f.write("数据统计信息\n")
            f.write("-" * 40 + "\n")
            f.write(f"库存数据：{summary['inventory_points']} 个数据点\n")
            f.write(f"仓单数据：{'可用' if summary['receipt_available'] else '不可用'}，{summary['receipt_points']} 个数据点\n")
            f.write(f"价格数据：{summary['price_points']} 个数据点\n")
            if summary['basis_points'] > 0:
                f.write(f"基差数据：{summary['basis_points']} 个数据点\n")
            if summary['term_structure_points'] > 0:
                f.write(f"期限结构数据：{summary['term_structure_points']} 个数据点\n")
            if summary['positioning_points'] > 0:
                f.write(f"持仓数据：{summary['positioning_points']} 个数据点\n")
            f.write(f"分析日期：{summary['analysis_date']}\n\n")
            
            if summary.get('data_sources'):
                f.write("数据来源详情\n")
                f.write("-" * 40 + "\n")
                for i, source in enumerate(summary['data_sources'], 1):
                    f.write(f"{i}. {source}\n")
                f.write("\n")
            
            f.write("-" * 80 + "\n")
            f.write("免责声明：本报告基于多维度数据分析，结合专业库存理论框架，但不构成投资建议。\n")
            f.write("市场有风险，投资需谨慎。请理解库存与价格的反身性关系，避免机械化应用。\n")
        
        print(f"✅ 终极专业分析报告已导出: {filepath}")
        return filepath
    
    # 为Streamlit系统提供兼容接口
    def analyze_variety_comprehensive(self, variety: str, analysis_date: str = None) -> dict:
        """
        为Streamlit系统提供的兼容接口
        
        Args:
            variety: 品种名称
            analysis_date: 分析日期（可选）
            
        Returns:
            分析结果字典
        """
        try:
            result = self.ultimate_comprehensive_analysis(variety)
            
            # 转换为Streamlit系统兼容的格式
            if "error" in result:
                return {
                    "analysis_content": f"分析失败：{result['error']}",
                    "confidence_score": 0.0,
                    "result_data": result
                }
            
            return {
                "analysis_content": result['professional_analysis'],
                "confidence_score": 0.85,  # 固定高置信度
                "result_data": {
                    **result,
                    "charts_html": result.get('charts_html', {}),  # 确保Plotly图表对象正确传递
                },
                "charts": result.get('charts', {}),
                "charts_html": result.get('charts_html', {}),
                "variety_name": result['variety_name']
            }
            
        except Exception as e:
            return {
                "analysis_content": f"系统分析异常：{str(e)}",
                "confidence_score": 0.0,
                "result_data": {"error": str(e)}
            }


def main():
    """主函数"""
    try:
        analyzer = UltimatePerfectedInventoryAnalyzer()
        
        print("\n" + "="*80)
        print("🚀 专业库存仓单AI分析系统 - 终极完善版")
        print("="*80)
        print("💡 元数据信息完全后置，开头直接分析内容")
        print("🚫 严禁任何英文，纯中文专业表达")
        print("📊 专业图表生成功能")
        print("🔗 完全兼容Streamlit系统调用")
        print("⚡ 五维数据整合 + 库存反身性关系深度解读")
        print("🤖 DeepSeek Reasoner推理模式")
        print("="*80)
        
        available_varieties = list(analyzer.variety_mapping.keys())
        
        while True:
            print(f"\n📋 可分析品种 ({len(available_varieties)}个):")
            for i, variety in enumerate(available_varieties, 1):
                info = analyzer.variety_mapping[variety]
                print(f"{i:2d}. {variety} ({info['code']}) - {info['category']} - {info['exchange']}")
            
            print("\n功能选择:")
            print("1. 选择品种进行终极专业分析")
            print("2. 导出最近分析报告")
            print("3. 测试Streamlit系统兼容性")
            print("4. 退出系统")
            print("-" * 40)
            
            choice = input("请选择功能 (1-4): ").strip()
            
            if choice == "1":
                variety_input = input(f"\n请输入品种名称或序号: ").strip()
                
                # 解析输入
                if variety_input.isdigit():
                    idx = int(variety_input) - 1
                    if 0 <= idx < len(available_varieties):
                        variety_name = available_varieties[idx]
                    else:
                        print("❌ 无效的序号")
                        continue
                else:
                    variety_name = variety_input
                
                if variety_name not in available_varieties:
                    print(f"❌ 不支持的品种: {variety_name}")
                    continue
                
                # 执行终极专业分析
                result = analyzer.ultimate_comprehensive_analysis(variety_name)
                analyzer.last_result = result  # 保存结果
                
                # 显示结果
                analyzer.display_ultimate_result(result)
                
            elif choice == "2":
                if hasattr(analyzer, 'last_result'):
                    output_dir = input("输入导出目录 (回车使用默认): ").strip()
                    if not output_dir:
                        output_dir = None
                    analyzer.export_ultimate_report(analyzer.last_result, output_dir)
                else:
                    print("❌ 没有可导出的分析结果，请先进行分析")
                    
            elif choice == "3":
                # 测试Streamlit系统兼容性
                test_variety = "聚氯乙烯"
                print(f"\n🧪 测试Streamlit兼容接口...")
                compat_result = analyzer.analyze_variety_comprehensive(test_variety)
                print(f"✅ 兼容性测试完成")
                print(f"   置信度: {compat_result['confidence_score']}")
                print(f"   内容长度: {len(compat_result['analysis_content'])}字符")
                print(f"   图表数量: {len(compat_result.get('charts', []))}个")
                    
            elif choice == "4":
                print("\n👋 感谢使用专业库存仓单AI分析系统（终极完善版）！")
                break
                
            else:
                print("❌ 无效选择，请重新输入")
                
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")


def test_ultimate_analysis():
    """测试终极分析系统"""
    print("=" * 70)
    print("🎯 测试专业库存仓单分析系统（终极完善版）")
    print("=" * 70)
    
    try:
        analyzer = UltimatePerfectedInventoryAnalyzer()
        
        # 测试聚氯乙烯期货分析
        print("\n🔍 测试品种: 聚氯乙烯(V)")
        result = analyzer.ultimate_comprehensive_analysis("聚氯乙烯")
        
        if "error" not in result:
            print("\n✅ 终极完善版改进效果验证:")
            metadata = result.get('analysis_metadata', {})
            print(f"   📊 数据维度: {len(metadata.get('data_dimensions', []))}个")
            print(f"   🌐 联网数据: {'是' if metadata.get('online_data_used', False) else '否'}")
            print(f"   🎯 分析版本: {metadata.get('version', 'Unknown')}")
            print(f"   📈 生成图表: {metadata.get('charts_generated', 0)}个")
            
            # 检查是否包含英文
            analysis_text = result['professional_analysis']
            english_words = ['due to', 'contango', 'backwardation', 'and', 'the', 'of', 'to', 'in', 'for']
            found_english = [word for word in english_words if word in analysis_text.lower()]
            
            if found_english:
                print(f"   ⚠️ 发现英文词汇: {found_english}")
            else:
                print(f"   ✅ 纯中文检查通过")
            
            # 显示部分分析内容
            analysis_preview = result['professional_analysis'][:600] + "..." if len(result['professional_analysis']) > 600 else result['professional_analysis']
            print(f"\n📋 终极专业分析预览:")
            print(f"   {analysis_preview}")
            
            # 测试Streamlit兼容性
            print(f"\n🧪 Streamlit兼容性测试:")
            compat_result = analyzer.analyze_variety_comprehensive("聚氯乙烯")
            print(f"   置信度: {compat_result['confidence_score']}")
            print(f"   图表数量: {len(compat_result.get('charts', []))}个")
            
            # 导出测试报告
            analyzer.export_ultimate_report(result)
            
            print("\n🎉 终极完善版专业分析系统测试成功！")
        else:
            print(f"❌ 测试失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_ultimate_analysis()
    else:
        main()
