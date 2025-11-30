#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业AI基差分析系统 - 基于深度理论的四维度分析框架
集成品质、空间、时间、库存四大维度分析框架
严禁数据编造，确保分析诚实性
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import warnings
import time
from dataclasses import dataclass
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
from io import BytesIO

warnings.filterwarnings('ignore')

# 配置参数
DATA_ROOT = Path(r"D:\Cursor\cursor项目\TradingAgent\qihuo\database")
OUTPUT_DIR = Path(r"D:\Cursor\cursor项目\TradingAgent\qihuo\output")

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API配置
DEEPSEEK_API_KEY = "sk-293dec7fabb54606b4f8d4f606da3383"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
SERPER_API_KEY = "04555ec0f2ce150d1cb628c7a80e2e433e193535"
SERPER_BASE_URL = "https://google.serper.dev/search"

# 品种中文名称映射（扩展版 - 支持更多品种）
VARIETY_NAMES = {
    # 贵金属
    'AU': '黄金', 'AG': '白银',
    
    # 有色金属  
    'CU': '沪铜', 'AL': '沪铝', 'ZN': '沪锌', 'PB': '沪铅', 'NI': '沪镍', 'SN': '沪锡',
    'BC': '国际铜', 'AO': '氧化铝',
    
    # 黑色金属
    'RB': '螺纹钢', 'HC': '热轧卷板', 'I': '铁矿石', 'JM': '焦煤', 'J': '焦炭', 
    'SS': '不锈钢', 'WR': '线材', 'FG': '玻璃', 'SA': '纯碱',
    
    # 能源化工
    'SC': '原油', 'FU': '燃料油', 'LU': '低硫燃料油', 'BU': '沥青', 'RU': '橡胶', 
    'NR': '20号胶', 'BR': '丁二烯橡胶', 'SP': '纸浆', 'LG': '液化气',
    'TA': 'PTA', 'MA': '甲醇', 'PP': '聚丙烯', 'V': 'PVC', 'L': '聚乙烯',
    'EB': '苯乙烯', 'EG': '乙二醇', 'PG': '液化石油气', 'PF': '短纤',
    'UR': '尿素', 'SF': '硅铁', 'SM': '锰硅', 'PS': '多晶硅', 'LC': '碳酸锂', 
    'SI': '工业硅', 'PX': '对二甲苯', 'PR': '丙烯',
    
    # 农产品
    'A': '豆一', 'B': '豆二', 'M': '豆粕', 'Y': '豆油', 'C': '玉米', 'CS': '玉米淀粉',
    'CF': '棉花', 'CY': '棉纱', 'SR': '白糖', 'P': '棕榈油', 'OI': '菜籽油', 'RM': '菜粕',
    'RS': '菜籽', 'JD': '鸡蛋', 'LH': '生猪', 'PK': '花生', 'AP': '苹果', 'CJ': '红枣',
    'WH': '强麦', 'PM': '普麦', 'RI': '早籼稻', 'LR': '晚籼稻', 'JR': '粳稻',
    
    # 其他
    'SH': '纸浆'
}

# akshare品种代码映射（用于联网API调用）
AKSHARE_SYMBOL_MAPPING = {
    # 主要品种的akshare符号映射
    'RB': 'RB', 'CU': 'CU', 'AL': 'AL', 'ZN': 'ZN', 'PB': 'PB', 'NI': 'NI',
    'AU': 'AU', 'AG': 'AG', 'I': 'I', 'J': 'J', 'JM': 'JM', 'HC': 'HC',
    'FU': 'FU', 'BU': 'BU', 'RU': 'RU', 'TA': 'TA', 'MA': 'MA', 'PP': 'PP',
    'V': 'V', 'L': 'L', 'EB': 'EB', 'EG': 'EG', 'PG': 'PG', 'M': 'M',
    'Y': 'Y', 'A': 'A', 'C': 'C', 'CF': 'CF', 'SR': 'SR', 'P': 'P',
    'OI': 'OI', 'RM': 'RM', 'JD': 'JD', 'LH': 'LH', 'AP': 'AP', 'CJ': 'CJ',
    'FG': 'FG', 'SA': 'SA', 'UR': 'UR', 'SF': 'SF', 'SM': 'SM', 'SS': 'SS',
    'SN': 'SN', 'WR': 'WR', 'SP': 'SP', 'NR': 'NR', 'BR': 'BR', 'PF': 'PF',
    'CY': 'CY', 'LU': 'LU', 'PS': 'PS', 'LC': 'LC', 'SI': 'SI', 'PX': 'PX',
    'PR': 'PR', 'B': 'B', 'CS': 'CS', 'PK': 'PK', 'RS': 'RS', 'AO': 'AO',
    'BC': 'BC', 'SC': 'SC', 'LG': 'LG'
}

# 品种分类（用于季节性分析）
VARIETY_CATEGORIES = {
    "非标农产品": ['C', 'JD', 'LH', 'CF', 'SR', 'A'],  # 具有明显品质差异
    "标准化农产品": ['M', 'Y', 'P', 'OI', 'RM'],  # 工业化加工品
    "工业品": ['RB', 'HC', 'I', 'JM', 'CU', 'AL', 'ZN', 'PB', 'NI'],
    "能源化工": ['FU', 'BU', 'RU', 'TA', 'MA', 'PP', 'V', 'L', 'EB', 'EG']
}

@dataclass
class BasisDataPackage:
    """基差数据包（增强版）"""
    # 本地数据
    basis_data: pd.DataFrame
    inventory_data: pd.DataFrame
    term_structure_data: pd.DataFrame
    positioning_data: Dict
    receipt_data: pd.DataFrame
    
    # 联网数据（新增）
    online_basis_data: pd.DataFrame = None
    online_search_results: Dict = None
    
    # 元数据
    variety: str = ""
    variety_name: str = ""
    analysis_date: str = ""
    data_quality: Dict[str, str] = None
    
    # 新增字段
    analysis_mode: str = "local_only"  # "local_only", "hybrid", "network_only"
    data_sources: list = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.online_basis_data is None:
            self.online_basis_data = pd.DataFrame()
        if self.online_search_results is None:
            self.online_search_results = {}
        if self.data_quality is None:
            self.data_quality = {}
        if self.data_sources is None:
            self.data_sources = []

class SerperSearchClient:
    """SERPER搜索客户端 - 获取实时市场数据"""
    
    def __init__(self, api_key: str = SERPER_API_KEY):
        self.api_key = api_key
        self.base_url = SERPER_BASE_URL
        self.search_results = []  # 存储搜索结果用于引用标注
        
    def search_with_citation(self, query: str, num_results: int = 5) -> Dict:
        """执行搜索并返回带引用标注的结果"""
        try:
            payload = {
                "q": query,
                "num": num_results,
                "gl": "cn",
                "hl": "zh"
            }
            
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # 为每个搜索结果添加引用编号
            if "organic" in result:
                for i, item in enumerate(result["organic"]):
                    citation_id = f"[{len(self.search_results) + 1}]"
                    item["citation_id"] = citation_id
                    self.search_results.append({
                        "id": citation_id,
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
            
            return result
            
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}"}
    
    def get_citations(self) -> List[Dict]:
        """获取所有引用信息"""
        return self.search_results.copy()

class MultidimensionalBasisAnalyzer:
    """多维度基差分析器（联网增强版）"""
    
    def __init__(self):
        self.searcher = SerperSearchClient()
        self.akshare_available = self._check_akshare_availability()
        print("🚀 多维度基差分析器初始化完成")
        if self.akshare_available:
            print("✅ akshare可用，支持联网数据获取")
        else:
            print("⚠️ akshare不可用，仅支持本地数据和搜索增强")
    
    def _check_akshare_availability(self) -> bool:
        """检查akshare是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            return False
        
    def fetch_online_basis_data(self, variety: str, analysis_date: str = None, days_back: int = 90) -> Tuple[pd.DataFrame, List[str]]:
        """联网获取基差数据"""
        
        if not self.akshare_available:
            return pd.DataFrame(), ["akshare不可用"]
        
        print(f"📡 联网获取{variety}基差数据...")
        data_sources = []
        combined_data = pd.DataFrame()
        
        try:
            import akshare as ak
            
            # 获取akshare符号
            ak_symbol = AKSHARE_SYMBOL_MAPPING.get(variety, variety)
            
            # 计算日期范围
            if analysis_date:
                end_date = pd.to_datetime(analysis_date)
            else:
                end_date = pd.Timestamp.now()
            
            start_date = end_date - pd.Timedelta(days=days_back)
            
            # 方法1: 获取历史基差数据
            try:
                print(f"  📊 获取{variety}历史基差数据...")
                
                basis_data = ak.futures_spot_price_daily(
                    start_day=start_date.strftime('%Y%m%d'),
                    end_day=end_date.strftime('%Y%m%d'),
                    vars_list=[ak_symbol]
                )
                
                if basis_data is not None and not basis_data.empty:
                    # 数据预处理
                    if 'date' in basis_data.columns:
                        basis_data['date'] = pd.to_datetime(basis_data['date'])
                    
                    combined_data = basis_data
                    data_sources.append(f"akshare历史基差数据（{len(basis_data)}条）")
                    print(f"  ✅ 获取历史基差数据成功：{len(basis_data)}条记录")
                else:
                    print(f"  ⚠️ 历史基差数据为空")
                    
            except Exception as e:
                print(f"  ❌ 获取历史基差数据失败: {e}")
            
            # 方法2: 获取最新基差数据
            try:
                print(f"  📊 获取{variety}最新基差数据...")
                
                latest_basis = ak.futures_spot_price(
                    date=end_date.strftime('%Y%m%d'),
                    vars_list=[ak_symbol]
                )
                
                if latest_basis is not None and not latest_basis.empty:
                    # 如果没有历史数据，使用最新数据作为基础
                    if combined_data.empty:
                        combined_data = latest_basis
                    
                    data_sources.append(f"akshare最新基差数据（{end_date.strftime('%Y-%m-%d')}）")
                    print(f"  ✅ 获取最新基差数据成功")
                else:
                    print(f"  ⚠️ 最新基差数据为空")
                    
            except Exception as e:
                print(f"  ❌ 获取最新基差数据失败: {e}")
            
            # 数据标准化
            if not combined_data.empty:
                combined_data = self._standardize_basis_data(combined_data, variety)
                print(f"✅ 联网基差数据获取完成：{len(combined_data)}条记录")
            else:
                print(f"❌ 未获取到{variety}的联网基差数据")
            
        except Exception as e:
            print(f"❌ 联网基差数据获取异常: {e}")
            data_sources.append(f"数据获取失败: {str(e)}")
        
        return combined_data, data_sources
    
    def _standardize_basis_data(self, df: pd.DataFrame, variety: str) -> pd.DataFrame:
        """标准化基差数据格式"""
        
        if df.empty:
            return df
        
        try:
            # 确保必需的列存在
            existing_columns = df.columns.tolist()
            
            # 如果有var列且等于当前品种，保留数据
            if 'var' in existing_columns:
                ak_symbol = AKSHARE_SYMBOL_MAPPING.get(variety, variety)
                df = df[df['var'] == ak_symbol].copy()
            
            # 标准化列名映射
            column_mapping = {
                'dom_basis': 'main_basis',        # 主力基差
                'near_basis': 'continuous_basis',  # 连续基差
                'sp': 'spot_price',               # 现货价格
                'dom_price': 'main_price',        # 主力合约价格
                'near_price': 'continuous_price', # 连续合约价格
                'dom_basis_rate': 'main_basis_rate',
                'near_basis_rate': 'continuous_basis_rate'
            }
            
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df[new_name] = df[old_name]
            
            # 确保日期格式正确
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
            
            # 计算基差如果缺失
            if 'spot_price' in df.columns and 'main_price' in df.columns:
                if 'main_basis' not in df.columns and 'dom_basis' not in df.columns:
                    df['main_basis'] = df['spot_price'] - df['main_price']
            
            return df
            
        except Exception as e:
            print(f"⚠️ 基差数据标准化失败: {e}")
            return df
    
    def load_comprehensive_data(self, variety: str, analysis_date: str = None) -> BasisDataPackage:
        """加载综合数据包（增强版 - 支持联网数据）"""
        
        variety_name = VARIETY_NAMES.get(variety, variety)
        print(f"📊 开始加载{variety}({variety_name})的综合数据...")
        
        data_quality = {}
        data_sources = []
        
        # 1. 加载本地基差数据
        basis_file = DATA_ROOT / "basis" / variety / "basis_data.csv"
        if basis_file.exists():
            try:
                basis_data = pd.read_csv(basis_file)
                if analysis_date:
                    basis_data = basis_data[basis_data['date'] <= analysis_date]
                data_quality['basis'] = '可用' if not basis_data.empty else '数据为空'
                if not basis_data.empty:
                    data_sources.append(f"本地基差数据（{len(basis_data)}条）")
                    print(f"✅ 本地基差数据加载成功：{len(basis_data)}条记录")
            except Exception as e:
                basis_data = pd.DataFrame()
                data_quality['basis'] = f'读取失败: {str(e)}'
        else:
            basis_data = pd.DataFrame()
            data_quality['basis'] = '文件不存在'
            print(f"ℹ️ 本地基差数据文件不存在，尝试联网获取...")
        
        # 2. 联网获取基差数据（如果本地数据不足或不存在）
        online_basis_data = pd.DataFrame()
        if basis_data.empty or len(basis_data) < 30:  # 如果本地数据为空或数据量不足
            online_basis_data, online_sources = self.fetch_online_basis_data(variety, analysis_date)
            data_sources.extend(online_sources)
        
        # 3. 联网搜索市场信息
        search_results = {}
        try:
            print(f"🔍 搜索{variety_name}市场信息...")
            search_queries = [
                f"{variety_name} 基差 现货价格 最新",
                f"{variety_name} 期货现货 升贴水 分析"
            ]
            
            for query in search_queries:
                try:
                    result = self.searcher.search_with_citation(query, num_results=3)
                    if "organic" in result:
                        search_results[query] = result["organic"]
                    time.sleep(1)  # 避免请求过快
                except Exception as e:
                    print(f"⚠️ 搜索查询失败 '{query}': {e}")
            
            if search_results:
                data_sources.append(f"联网市场信息（{len(search_results)}个查询）")
            
        except Exception as e:
            print(f"⚠️ 联网搜索失败: {e}")
        
        # 4. 确定分析模式
        has_local_basis = not basis_data.empty
        has_online_basis = not online_basis_data.empty
        
        if has_local_basis and has_online_basis:
            analysis_mode = "hybrid"
            print(f"✅ 使用混合分析模式（本地数据 + 联网数据）")
        elif has_local_basis:
            analysis_mode = "local_only" 
            print(f"✅ 使用本地数据分析模式")
        elif has_online_basis:
            analysis_mode = "network_only"
            print(f"✅ 使用纯网络分析模式")
        else:
            analysis_mode = "limited"
            print(f"⚠️ 使用受限分析模式（基差数据获取困难）")
        
        # 2. 库存数据
        inventory_file = DATA_ROOT / "inventory" / variety / "inventory.csv"
        if inventory_file.exists():
            try:
                inventory_data = pd.read_csv(inventory_file)
                if analysis_date:
                    inventory_data = inventory_data[inventory_data['date'] <= analysis_date]
                data_quality['inventory'] = '可用' if not inventory_data.empty else '数据为空'
            except Exception as e:
                inventory_data = pd.DataFrame()
                data_quality['inventory'] = f'读取失败: {str(e)}'
        else:
            inventory_data = pd.DataFrame()
            data_quality['inventory'] = '文件不存在'
        
        # 3. 期限结构数据
        term_structure_file = DATA_ROOT / "term_structure" / variety / "term_structure.csv"
        if term_structure_file.exists():
            try:
                term_structure_data = pd.read_csv(term_structure_file)
                if analysis_date:
                    # 期限结构数据的日期格式可能是YYYYMMDD
                    if 'date' in term_structure_data.columns:
                        term_structure_data['date'] = pd.to_datetime(term_structure_data['date'], format='%Y%m%d', errors='coerce')
                        if analysis_date:
                            analysis_dt = pd.to_datetime(analysis_date)
                            term_structure_data = term_structure_data[term_structure_data['date'] <= analysis_dt]
                data_quality['term_structure'] = '可用' if not term_structure_data.empty else '数据为空'
            except Exception as e:
                term_structure_data = pd.DataFrame()
                data_quality['term_structure'] = f'读取失败: {str(e)}'
        else:
            term_structure_data = pd.DataFrame()
            data_quality['term_structure'] = '文件不存在'
        
        # 4. 持仓数据
        positioning_summary_file = DATA_ROOT / "positioning" / variety / "positioning_summary.json"
        if positioning_summary_file.exists():
            try:
                with open(positioning_summary_file, 'r', encoding='utf-8') as f:
                    positioning_data = json.load(f)
                data_quality['positioning'] = '可用'
            except Exception as e:
                positioning_data = {}
                data_quality['positioning'] = f'读取失败: {str(e)}'
        else:
            positioning_data = {}
            data_quality['positioning'] = '文件不存在'
        
        # 5. 加载其他本地数据（保持原有逻辑）
        inventory_file = DATA_ROOT / "inventory" / variety / "inventory.csv"
        if inventory_file.exists():
            try:
                inventory_data = pd.read_csv(inventory_file)
                if analysis_date:
                    inventory_data = inventory_data[inventory_data['date'] <= analysis_date]
                data_quality['inventory'] = '可用' if not inventory_data.empty else '数据为空'
                if not inventory_data.empty:
                    data_sources.append(f"本地库存数据（{len(inventory_data)}条）")
            except Exception as e:
                inventory_data = pd.DataFrame()
                data_quality['inventory'] = f'读取失败: {str(e)}'
        else:
            inventory_data = pd.DataFrame()
            data_quality['inventory'] = '文件不存在'
        
        # 6. 期限结构数据
        term_structure_file = DATA_ROOT / "term_structure" / variety / "term_structure.csv"
        if term_structure_file.exists():
            try:
                term_structure_data = pd.read_csv(term_structure_file)
                if analysis_date:
                    if 'date' in term_structure_data.columns:
                        term_structure_data['date'] = pd.to_datetime(term_structure_data['date'], format='%Y%m%d', errors='coerce')
                        if analysis_date:
                            analysis_dt = pd.to_datetime(analysis_date)
                            term_structure_data = term_structure_data[term_structure_data['date'] <= analysis_dt]
                data_quality['term_structure'] = '可用' if not term_structure_data.empty else '数据为空'
                if not term_structure_data.empty:
                    data_sources.append(f"本地期限结构数据（{len(term_structure_data)}条）")
            except Exception as e:
                term_structure_data = pd.DataFrame()
                data_quality['term_structure'] = f'读取失败: {str(e)}'
        else:
            term_structure_data = pd.DataFrame()
            data_quality['term_structure'] = '文件不存在'
        
        # 7. 持仓数据
        positioning_summary_file = DATA_ROOT / "positioning" / variety / "positioning_summary.json"
        if positioning_summary_file.exists():
            try:
                with open(positioning_summary_file, 'r', encoding='utf-8') as f:
                    positioning_data = json.load(f)
                data_quality['positioning'] = '可用'
                data_sources.append("本地持仓汇总数据")
            except Exception as e:
                positioning_data = {}
                data_quality['positioning'] = f'读取失败: {str(e)}'
        else:
            positioning_data = {}
            data_quality['positioning'] = '文件不存在'
        
        # 8. 仓单数据
        receipt_file = DATA_ROOT / "receipt" / variety / "receipt.csv"
        if receipt_file.exists():
            try:
                receipt_data = pd.read_csv(receipt_file)
                if analysis_date:
                    receipt_data = receipt_data[receipt_data['date'] <= analysis_date]
                data_quality['receipt'] = '可用' if not receipt_data.empty else '数据为空'
                if not receipt_data.empty:
                    data_sources.append(f"本地仓单数据（{len(receipt_data)}条）")
            except Exception as e:
                receipt_data = pd.DataFrame()
                data_quality['receipt'] = f'读取失败: {str(e)}'
        else:
            receipt_data = pd.DataFrame()
            data_quality['receipt'] = '文件不存在'
        
        print(f"✅ 数据加载完成，分析模式：{analysis_mode}，数据源：{len(data_sources)}个")
        
        # 返回增强版数据包
        return BasisDataPackage(
            # 本地数据
            basis_data=basis_data,
            inventory_data=inventory_data,
            term_structure_data=term_structure_data,
            positioning_data=positioning_data,
            receipt_data=receipt_data,
            
            # 联网数据
            online_basis_data=online_basis_data,
            online_search_results=search_results,
            
            # 元数据
            variety=variety,
            variety_name=variety_name,
            analysis_date=analysis_date or datetime.now().strftime('%Y-%m-%d'),
            data_quality=data_quality,
            analysis_mode=analysis_mode,
            data_sources=data_sources
        )
    
    def analyze_continuous_basis(self, data_package: BasisDataPackage) -> Dict:
        """连续基差分析（时间维度）"""
        
        if data_package.basis_data.empty:
            return {"error": "基差数据不可用"}
        
        df = data_package.basis_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        if len(df) == 0:
            return {"error": "基差数据为空"}
        
        latest = df.iloc[-1]
        
        analysis = {
            "current_continuous_basis": float(latest['near_basis']) if pd.notna(latest.get('near_basis')) else None,
            "current_main_basis": float(latest['dom_basis']) if pd.notna(latest.get('dom_basis')) else None,
            "basis_spread": None,
            "convergence_analysis": {},
            "time_decay_characteristic": "连续基差具有期权时间衰减特征"
        }
        
        # 基差价差计算
        if pd.notna(latest.get('dom_basis')) and pd.notna(latest.get('near_basis')):
            analysis["basis_spread"] = float(latest['dom_basis'] - latest['near_basis'])
        
        # 收敛性分析
        if len(df) >= 30 and 'near_basis' in df.columns:
            near_basis_std = df['near_basis'].std()
            recent_volatility = df['near_basis'].tail(10).std()
            
            analysis["convergence_analysis"] = {
                "historical_volatility": float(near_basis_std) if pd.notna(near_basis_std) else None,
                "recent_volatility": float(recent_volatility) if pd.notna(recent_volatility) else None,
                "convergence_tendency": "收敛" if recent_volatility < near_basis_std else "发散"
            }
        
        return analysis
    
    def analyze_seasonal_pattern(self, data_package: BasisDataPackage) -> Dict:
        """季节性基差分析"""
        
        if data_package.basis_data.empty:
            return {"error": "基差数据不可用"}
        
        df = data_package.basis_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        
        # 计算月度基差均值
        monthly_avg = df.groupby('month')['dom_basis'].mean().to_dict()
        
        # 当前月份基差与历史同期对比
        current_month = datetime.now().month
        current_basis = df.iloc[-1]['dom_basis'] if not df.empty and 'dom_basis' in df.columns else None
        historical_same_month = monthly_avg.get(current_month)
        
        analysis = {
            "monthly_average_basis": monthly_avg,
            "current_month": current_month,
            "current_basis": float(current_basis) if pd.notna(current_basis) else None,
            "historical_same_month_avg": float(historical_same_month) if pd.notna(historical_same_month) else None,
            "seasonal_deviation": None,
            "seasonal_strength": "未知"
        }
        
        # 季节性偏离计算
        if pd.notna(current_basis) and pd.notna(historical_same_month):
            deviation = current_basis - historical_same_month
            analysis["seasonal_deviation"] = float(deviation)
            
            if abs(deviation) > 50:
                analysis["seasonal_strength"] = "强偏离"
            elif abs(deviation) > 20:
                analysis["seasonal_strength"] = "中等偏离"
            else:
                analysis["seasonal_strength"] = "正常范围"
        
        return analysis
    
    def analyze_inventory_basis_relationship(self, data_package: BasisDataPackage) -> Dict:
        """库存-基差关系分析（库存理论）"""
        
        analysis = {
            "inventory_level": "未知",
            "basis_level": "未知",
            "region_classification": "未确定",
            "theoretical_framework": "基于库存理论的三区域分析框架",
            "trading_implications": []
        }
        
        # 库存水平评估
        if not data_package.inventory_data.empty:
            inventory_df = data_package.inventory_data.copy()
            inventory_df['date'] = pd.to_datetime(inventory_df['date'])
            
            if len(inventory_df) > 0 and 'value' in inventory_df.columns:
                current_inventory = inventory_df.iloc[-1]['value']
                historical_inventory = inventory_df['value']
                
                percentile = (historical_inventory <= current_inventory).mean() * 100
                
                if percentile <= 20:
                    analysis["inventory_level"] = "极低库存"
                    analysis["region_classification"] = "区域A - 货权集中"
                elif percentile <= 80:
                    analysis["inventory_level"] = "正常库存"
                    analysis["region_classification"] = "区域B - 正常波动"
                else:
                    analysis["inventory_level"] = "高库存"
                    analysis["region_classification"] = "区域C - 库存压制"
        
        # 基差水平评估
        if not data_package.basis_data.empty and 'dom_basis' in data_package.basis_data.columns:
            basis_df = data_package.basis_data.copy()
            if len(basis_df) > 0:
                current_basis = basis_df.iloc[-1]['dom_basis']
                
                if pd.notna(current_basis):
                    if current_basis > 50:
                        analysis["basis_level"] = "强升水"
                    elif current_basis > 0:
                        analysis["basis_level"] = "弱升水"
                    elif current_basis > -50:
                        analysis["basis_level"] = "弱贴水"
                    else:
                        analysis["basis_level"] = "强贴水"
        
        # 交易含义
        if analysis["inventory_level"] == "极低库存" and analysis["basis_level"] in ["强贴水", "弱贴水"]:
            analysis["trading_implications"].append("供应紧张，基差走强预期")
        elif analysis["inventory_level"] == "高库存" and analysis["basis_level"] in ["强升水", "弱升水"]:
            analysis["trading_implications"].append("库存压制，基差走弱预期")
        
        return analysis
    
    def analyze_spatial_basis_differences(self, data_package: BasisDataPackage, external_data: Dict) -> Dict:
        """空间基差差异分析"""
        
        analysis = {
            "delivery_warehouse_analysis": "基准库分析",
            "regional_imbalance": "空间不均衡特征",
            "arbitrage_opportunities": [],
            "spatial_spread_analysis": "区域价差分析"
        }
        
        # 从外部搜索数据中提取区域价格信息
        if external_data.get("regional_premium_discount", {}).get("results"):
            regional_data = external_data["regional_premium_discount"]["results"]
            analysis["regional_price_info"] = [
                f"区域价格信息: {item['title']} - {item['snippet']}"
                for item in regional_data[:3]
            ]
        
        # 基于品种特性的空间分析
        variety = data_package.variety
        if variety in ['C', 'A', 'M']:  # 农产品
            analysis["spatial_characteristics"] = "农产品基准库靠近产区，存在明显的季节性运输成本差异"
        elif variety in ['CU', 'AL', 'ZN']:  # 有色金属
            analysis["spatial_characteristics"] = "有色金属基准库靠近港口，进口依赖度高"
        elif variety in ['RB', 'HC', 'I']:  # 黑色系
            analysis["spatial_characteristics"] = "黑色系基准库分布广泛，区域供需差异显著"
        else:
            analysis["spatial_characteristics"] = "品种空间特征待分析"
        
        return analysis
    
    def analyze_quality_basis_differences(self, data_package: BasisDataPackage) -> Dict:
        """品质差异基差分析"""
        
        variety = data_package.variety
        analysis = {
            "quality_standardization": "标准化程度",
            "premium_discount_structure": "升贴水结构",
            "quality_spread_analysis": "品质价差分析"
        }
        
        # 根据品种分类进行品质分析
        if variety in VARIETY_CATEGORIES.get("非标农产品", []):
            analysis.update({
                "quality_standardization": "非标准化商品，存在明显品质差异",
                "premium_discount_structure": "交割标准以上升水，以下贴水",
                "market_segmentation": "需求市场按品质进行分割",
                "hedonic_price_model": "可应用特征价格模型分析品质价差"
            })
        elif variety in VARIETY_CATEGORIES.get("标准化农产品", []):
            analysis.update({
                "quality_standardization": "工业化加工品，标准化程度高",
                "premium_discount_structure": "品质差异较小，升贴水幅度有限",
                "market_segmentation": "市场统一性较强"
            })
        else:
            analysis.update({
                "quality_standardization": "工业品标准化程度高",
                "premium_discount_structure": "严格按交割标准执行",
                "market_segmentation": "市场统一性强"
            })
        
        return analysis
    
    def create_professional_charts(self, data_package: BasisDataPackage) -> Dict:
        """创建专业图表"""
        
        charts = {}
        
        # 1. 基差走势图
        if not data_package.basis_data.empty:
            basis_chart = self._create_basis_trend_chart(data_package.basis_data, data_package.variety_name)
            charts['basis_trend'] = basis_chart
        
        # 2. 库存水平图
        if not data_package.inventory_data.empty:
            inventory_chart = self._create_inventory_chart(data_package.inventory_data, data_package.variety_name)
            charts['inventory_level'] = inventory_chart
        
        # 3. 期限结构图
        if not data_package.term_structure_data.empty:
            term_structure_chart = self._create_term_structure_chart(data_package.term_structure_data, data_package.variety_name)
            charts['term_structure'] = term_structure_chart
        
        # 4. 季节性基差对比图
        if not data_package.basis_data.empty:
            seasonal_chart = self._create_seasonal_basis_chart(data_package.basis_data, data_package.variety_name)
            charts['seasonal_pattern'] = seasonal_chart
        
        return charts
    
    def _create_basis_trend_chart(self, basis_data: pd.DataFrame, variety_name: str):
        """创建基差走势图"""
        
        df = basis_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(60)  # 最近60天
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=['基差走势', '基差收敛性分析'],
            vertical_spacing=0.1
        )
        
        # 主力基差线
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df['dom_basis'],
                name='主力基差',
                line=dict(color='blue', width=2),
                mode='lines'
            ),
            row=1, col=1
        )
        
        # 连续基差线
        if 'near_basis' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['near_basis'],
                    name='连续基差',
                    line=dict(color='red', width=2),
                    mode='lines'
                ),
                row=1, col=1
            )
        
        # 基差收敛性（滚动标准差）
        if len(df) >= 10:
            rolling_std = df['dom_basis'].rolling(10).std()
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=rolling_std,
                    name='10日滚动波动率',
                    line=dict(color='green', width=1),
                    mode='lines'
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title=f'{variety_name} 基差走势分析',
            height=600,
            showlegend=True
        )
        
        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="基差 (元/吨)", row=1, col=1)
        fig.update_yaxes(title_text="波动率", row=2, col=1)
        
        return fig  # 返回Plotly对象而不是HTML字符串
    
    def _create_inventory_chart(self, inventory_data: pd.DataFrame, variety_name: str):
        """创建库存水平图"""
        
        df = inventory_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(90)  # 最近90天
        
        # 计算历史分位数
        current_inventory = df.iloc[-1]['value']
        percentile = (df['value'] <= current_inventory).mean() * 100
        
        fig = go.Figure()
        
        # 库存走势
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df['value'],
                name='库存水平',
                line=dict(color='purple', width=2),
                mode='lines+markers'
            )
        )
        
        # 添加分位数线
        percentiles = [20, 50, 80]
        colors = ['red', 'orange', 'green']
        for p, color in zip(percentiles, colors):
            pct_value = df['value'].quantile(p/100)
            fig.add_hline(
                y=pct_value, 
                line_dash="dash", 
                line_color=color,
                annotation_text=f"{p}%分位数: {pct_value:.0f}"
            )
        
        fig.update_layout(
            title=f'{variety_name} 库存水平分析 (当前分位数: {percentile:.1f}%)',
            xaxis_title="日期",
            yaxis_title="库存 (万吨)",
            height=400
        )
        
        return fig  # 返回Plotly对象而不是HTML字符串
    
    def _create_term_structure_chart(self, term_structure_data: pd.DataFrame, variety_name: str):
        """创建期限结构图"""
        
        df = term_structure_data.copy()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
            latest_data = df[df['date'] == df['date'].max()]
        else:
            latest_data = df.tail(10)  # 取最新10条记录
        
        if latest_data.empty:
            return "<p>期限结构数据不足，无法生成图表</p>"
        
        fig = go.Figure()
        
        # 按合约月份排序
        if 'symbol' in latest_data.columns and 'close' in latest_data.columns:
            latest_data = latest_data.sort_values('symbol')
            
            fig.add_trace(
                go.Scatter(
                    x=latest_data['symbol'], 
                    y=latest_data['close'],
                    name='合约价格',
                    line=dict(color='blue', width=3),
                    mode='lines+markers',
                    marker=dict(size=8)
                )
            )
        
        fig.update_layout(
            title=f'{variety_name} 期限结构曲线',
            xaxis_title="合约月份",
            yaxis_title="价格 (元/吨)",
            height=400
        )
        
        return fig  # 返回Plotly对象而不是HTML字符串
    
    def _create_seasonal_basis_chart(self, basis_data: pd.DataFrame, variety_name: str):
        """创建季节性基差对比图"""
        
        df = basis_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        
        # 计算月度统计
        monthly_stats = df.groupby('month')['dom_basis'].agg(['mean', 'std', 'count']).reset_index()
        monthly_stats = monthly_stats[monthly_stats['count'] >= 3]  # 至少3个数据点
        
        if monthly_stats.empty:
            return "<p>季节性数据不足，无法生成图表</p>"
        
        fig = go.Figure()
        
        # 月度均值
        fig.add_trace(
            go.Scatter(
                x=monthly_stats['month'], 
                y=monthly_stats['mean'],
                name='历史月度均值',
                line=dict(color='blue', width=2),
                mode='lines+markers'
            )
        )
        
        # 标准差区间
        fig.add_trace(
            go.Scatter(
                x=monthly_stats['month'], 
                y=monthly_stats['mean'] + monthly_stats['std'],
                name='上限 (+1σ)',
                line=dict(color='lightblue', width=1),
                mode='lines',
                showlegend=False
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=monthly_stats['month'], 
                y=monthly_stats['mean'] - monthly_stats['std'],
                name='下限 (-1σ)',
                line=dict(color='lightblue', width=1),
                mode='lines',
                fill='tonexty',
                fillcolor='rgba(173,216,230,0.3)',
                showlegend=False
            )
        )
        
        # 当前月份标记
        current_month = datetime.now().month
        current_basis = df[df['month'] == current_month]['dom_basis'].iloc[-1] if len(df[df['month'] == current_month]) > 0 else None
        
        if current_basis is not None:
            fig.add_trace(
                go.Scatter(
                    x=[current_month], 
                    y=[current_basis],
                    name=f'当前({current_month}月)',
                    mode='markers',
                    marker=dict(color='red', size=12, symbol='star')
                )
            )
        
        fig.update_layout(
            title=f'{variety_name} 季节性基差规律',
            xaxis_title="月份",
            yaxis_title="基差 (元/吨)",
            height=400
        )
        
        return fig  # 返回Plotly对象而不是HTML字符串
    
    def search_enhanced_market_context(self, data_package: BasisDataPackage) -> Dict:
        """搜索增强的市场背景分析"""
        
        variety = data_package.variety
        variety_name = data_package.variety_name
        
        # 定制化搜索查询
        search_queries = [
            f"{variety_name}期货 现货价格 基差 最新 2025年",
            f"{variety_name}库存 仓单 供需平衡 2025年",
            f"{variety_name}区域价差 升贴水 交割 最新",
            f"{variety_name}季节性规律 基差走势 历史分析",
            f"{variety_name}产业链 上下游 利润 成本分析"
        ]
        
        market_context = {
            "price_basis_info": {},
            "inventory_supply_demand": {},
            "regional_premium_discount": {},
            "seasonal_patterns": {},
            "industry_chain_analysis": {},
            "search_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        context_keys = [
            "price_basis_info", "inventory_supply_demand", 
            "regional_premium_discount", "seasonal_patterns", 
            "industry_chain_analysis"
        ]
        
        for i, query in enumerate(search_queries):
            print(f"  🔍 搜索中: {query}")
            result = self.searcher.search_with_citation(query, num_results=3)
            
            if "error" not in result and "organic" in result:
                context_key = context_keys[i]
                market_context[context_key] = {
                    "query": query,
                    "results": []
                }
                
                for item in result["organic"]:
                    market_context[context_key]["results"].append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "citation_id": item.get("citation_id", "")
                    })
            
            time.sleep(0.5)
        
        return market_context
    
    def create_comprehensive_analysis_prompt(self, data_package: BasisDataPackage, 
                                           continuous_analysis: Dict,
                                           seasonal_analysis: Dict,
                                           inventory_analysis: Dict,
                                           spatial_analysis: Dict,
                                           quality_analysis: Dict,
                                           market_context: Dict) -> str:
        """创建综合分析prompt"""
        
        # 构建市场背景信息（带引用）
        market_info = ""
        for section_name, section_data in market_context.items():
            if isinstance(section_data, dict) and "results" in section_data:
                market_info += f"\n{section_name}:\n"
                for result in section_data["results"][:2]:
                    citation = result.get("citation_id", "")
                    market_info += f"- {citation} {result['title']}: {result['snippet']}\n"
        
        prompt = f"""
你是中国期货市场顶级基差分析专家，拥有20年实战经验。请基于以下真实数据和理论框架进行专业分析。

重要分析原则:
1. 严禁编造任何数据、比率、成本参数
2. 所有结论必须基于提供的真实数据
3. 联网搜索的信息已标注引用编号，请在分析中使用
4. 不使用任何markdown符号（如 #、**、###等），采用纯文本格式
5. 分析报告要兼具专业性和可读性

分析标的: {data_package.variety}（{data_package.variety_name}）
分析时点: {data_package.analysis_date}

⚠️ 重要提醒: 
- 本次分析的品种代码是 {data_package.variety}，对应品种名称是 {data_package.variety_name}
- 请确保所有分析内容都围绕 {data_package.variety} 品种进行，不要混淆其他品种
- 合约代码应使用 {data_package.variety}XXXX 格式，如 {data_package.variety}2410、{data_package.variety}2501 等
- 严禁使用其他品种的合约代码或品种名称

数据质量评估:
- 基差数据: {data_package.data_quality.get('basis', '未知')}
- 库存数据: {data_package.data_quality.get('inventory', '未知')}
- 期限结构数据: {data_package.data_quality.get('term_structure', '未知')}
- 持仓数据: {data_package.data_quality.get('positioning', '未知')}
- 仓单数据: {data_package.data_quality.get('receipt', '未知')}

{market_info}

一、连续基差与时间维度分析
当前连续基差: {continuous_analysis.get('current_continuous_basis', 'N/A')} 元/吨
当前主力基差: {continuous_analysis.get('current_main_basis', 'N/A')} 元/吨
基差价差: {continuous_analysis.get('basis_spread', 'N/A')} 元/吨
收敛特征: {continuous_analysis.get('convergence_analysis', {})}

二、季节性基差规律分析
当前月份: {seasonal_analysis.get('current_month', 'N/A')}月
当前基差: {seasonal_analysis.get('current_basis', 'N/A')} 元/吨
历史同期均值: {seasonal_analysis.get('historical_same_month_avg', 'N/A')} 元/吨
季节性偏离: {seasonal_analysis.get('seasonal_deviation', 'N/A')} 元/吨
季节性强度: {seasonal_analysis.get('seasonal_strength', '未知')}

三、库存-基差关系分析（库存理论）
库存水平: {inventory_analysis.get('inventory_level', '未知')}
基差水平: {inventory_analysis.get('basis_level', '未知')}
区域分类: {inventory_analysis.get('region_classification', '未确定')}
交易含义: {inventory_analysis.get('trading_implications', [])}

四、空间基差差异分析
空间特征: {spatial_analysis.get('spatial_characteristics', '未知')}
区域不均衡: {spatial_analysis.get('regional_imbalance', '分析中')}

五、品质差异基差分析
标准化程度: {quality_analysis.get('quality_standardization', '未知')}
升贴水结构: {quality_analysis.get('premium_discount_structure', '未知')}
市场分割: {quality_analysis.get('market_segmentation', '未知')}

请按以下框架进行深度分析（每部分600-800字）:

第一部分: 连续基差收敛性与时间衰减分析
基于连续基差的时间衰减特征，分析当前基差收敛情况，结合主力合约切换的跳跃现象，评估基差走势。

第二部分: 季节性基差规律与历史对比
基于月度基差均值和当前季节性偏离，分析季节性走强或走弱的可能性，结合产业生产消费周期。

第三部分: 库存理论框架下的基差-库存关系
基于库存理论的三区域分析框架，评估当前市场所处阶段。必须在首次提到区域分类时详细解释：
- 区域A（货权集中）：库存极低（历史分位数≤20%），现货稀缺，基差通常呈现强升水
- 区域B（正常波动）：库存正常（历史分位数20%-80%），供需相对平衡，基差波动适中  
- 区域C（库存压制）：库存高企（历史分位数≥80%），供应充裕，基差承受压力
然后分析当前市场所处的具体区域及其交易含义。

重要要求：必须明确标注库存数据来源，包括：
- 数据来源：上期所库存数据（本地数据库）
- 数据路径：qihuo/database/inventory/品种/inventory.csv
- 数据特征：日度更新，完整无缺失，真实可靠
- 历史分位数计算基于完整历史数据序列

第四部分: 空间不均衡与区域基差差异
分析基差的空间属性，评估区域市场强弱差异，识别空间套利机会。

第五部分: 品质差异对基差结构的影响
基于品种标准化程度，分析品质差异如何影响基差结构和升贴水关系。

第六部分: 综合交易策略与风险管理
整合四维分析结果，提出具体的期现套利、跨期套利策略，明确风险控制措施。

输出要求:
- 严格基于真实数据，禁止编造
- 专业术语准确，逻辑清晰
- 总字数3000-4000字
- 引用外部信息时使用标注的引用编号
- 严禁使用任何markdown符号（包括但不限于: #、##、###、**、*、_、```等），采用纯文本格式
- 绝对不允许使用任何形式的标题符号，包括 # ## ### 等，所有标题都用纯文本表示
- 在相应分析中引用对应图表，格式如"如图1所示"或"图2显示"
- 每个部分结尾要有明确的结论
"""
        
        return prompt

class EnhancedDeepSeekClient:
    """增强版DeepSeek客户端"""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.base_url = DEEPSEEK_BASE_URL
        
    def chat(self, messages: List[Dict], model: str = "deepseek-chat", 
             temperature: float = 0.1, max_tokens: int = 4000) -> str:
        """发送聊天请求"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            return f"分析失败: {str(e)}"

class ProfessionalBasisAnalysisSystem:
    """专业基差分析系统 - 四维度分析框架"""
    
    def __init__(self):
        self.analyzer = MultidimensionalBasisAnalyzer()
        self.llm_client = EnhancedDeepSeekClient()
        print("🤖 专业基差分析系统初始化完成")
        print("📊 集成四维度分析框架: 品质、空间、时间、库存")
    
    def get_available_varieties(self) -> List[str]:
        """获取可用品种列表（扩展版 - 支持本地数据+联网获取）"""
        # 返回扩展的品种列表，理论上支持所有在VARIETY_NAMES中的品种
        return sorted(list(VARIETY_NAMES.keys()))
    
    def show_available_varieties(self):
        """显示可用品种（增强版 - 显示本地数据和联网获取状态）"""
        varieties = self.get_available_varieties()
        
        # 检查本地数据可用性
        local_varieties = []
        basis_dir = DATA_ROOT / "basis"
        if basis_dir.exists():
            for d in basis_dir.iterdir():
                if d.is_dir() and (d / "basis_data.csv").exists():
                    local_varieties.append(d.name)
        
        # 按板块分类
        categories = {
            "贵金属": ['AU', 'AG'],
            "有色金属": ['CU', 'AL', 'ZN', 'PB', 'NI', 'SN', 'BC', 'AO'],
            "黑色系": ['RB', 'HC', 'I', 'JM', 'J', 'SS', 'WR', 'FG', 'SA'],
            "能源化工": ['SC', 'FU', 'LU', 'BU', 'RU', 'NR', 'BR', 'SP', 'LG', 'TA', 'MA', 'PP', 'V', 'L', 'EB', 'EG', 'PG', 'PF', 'UR', 'SF', 'SM', 'PS', 'LC', 'SI', 'PX', 'PR'],
            "农产品": ['A', 'B', 'M', 'Y', 'C', 'CS', 'CF', 'CY', 'SR', 'P', 'OI', 'RM', 'RS', 'JD', 'LH', 'PK', 'AP', 'CJ', 'WH', 'PM', 'RI', 'LR', 'JR'],
            "其他": ['SH']
        }
        
        print("\n" + "="*90)
        print("📊 可用品种列表 - 联网增强版基差分析系统")
        print("="*90)
        print("图例: ✅ 本地数据  🌐 联网获取  ⭐ 混合模式")
        print("="*90)
        
        total_local = 0
        total_network = 0
        
        for category, symbols in categories.items():
            available_in_category = [s for s in symbols if s in varieties]
            if available_in_category:
                print(f"\n{category} ({len(available_in_category)}个):")
                for symbol in available_in_category:
                    name = VARIETY_NAMES.get(symbol, symbol)
                    if symbol in local_varieties:
                        print(f"  ✅ {symbol}({name}) - 本地数据可用")
                        total_local += 1
                    else:
                        print(f"  🌐 {symbol}({name}) - 联网获取")
                        total_network += 1
        
        print(f"\n" + "="*90)
        print(f"📈 分析能力:")
        print(f"  ✅ 本地数据品种: {total_local}个 (混合分析模式)")
        print(f"  🌐 联网获取品种: {total_network}个 (纯网络分析模式)")
        print(f"  📊 总支持品种: {len(varieties)}个")
        
        print(f"\n🚀 系统特色:")
        print(f"  • 本地数据优先，联网补充的智能策略")
        print(f"  • 自动判断分析模式，无需用户关心数据来源") 
        print(f"  • 理论上支持所有中国期货品种分析")
        print(f"  • akshare API + Serper搜索双重数据保障")
        print("="*90)
    
    def analyze_variety_comprehensive(self, variety: str, analysis_date: str = None, 
                                    use_reasoner: bool = False) -> Dict:
        """综合四维度基差分析"""
        
        print(f"\n🚀 开始分析 {variety}({VARIETY_NAMES.get(variety, variety)}) - 四维度分析框架")
        print("=" * 80)
        
        # 1. 加载综合数据包
        print("📊 步骤1: 加载多源数据...")
        data_package = self.analyzer.load_comprehensive_data(variety, analysis_date)
        
        if data_package.basis_data.empty:
            return {"error": f"品种 {variety} 的基差数据不可用"}
        
        # 2. 四维度分析
        print("🔍 步骤2: 执行四维度分析...")
        
        # 时间维度 - 连续基差分析
        continuous_analysis = self.analyzer.analyze_continuous_basis(data_package)
        
        # 季节性分析
        seasonal_analysis = self.analyzer.analyze_seasonal_pattern(data_package)
        
        # 库存维度 - 库存基差关系
        inventory_analysis = self.analyzer.analyze_inventory_basis_relationship(data_package)
        
        # 空间维度 - 区域差异分析  
        spatial_analysis = self.analyzer.analyze_spatial_basis_differences(data_package, {})
        
        # 品质维度 - 品质差异分析
        quality_analysis = self.analyzer.analyze_quality_basis_differences(data_package)
        
        # 3. 搜索增强市场背景
        print("🌐 步骤3: 搜索市场背景信息...")
        market_context = self.analyzer.search_enhanced_market_context(data_package)
        
        # 更新空间分析（包含搜索结果）
        spatial_analysis = self.analyzer.analyze_spatial_basis_differences(data_package, market_context)
        
        # 4. 生成专业图表
        print("📊 步骤4: 生成专业图表...")
        professional_charts = self.analyzer.create_professional_charts(data_package)
        
        # 5. 生成综合分析prompt
        print("🧠 步骤5: 生成AI分析...")
        prompt = self.analyzer.create_comprehensive_analysis_prompt(
            data_package, continuous_analysis, seasonal_analysis,
            inventory_analysis, spatial_analysis, quality_analysis, market_context
        )
        
        # 6. AI深度分析
        model = "deepseek-reasoner" if use_reasoner else "deepseek-chat"
        messages = [
            {
                "role": "system",
                "content": "你是专业的期货基差分析师，严格基于事实数据进行四维度分析，绝不编造信息。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        ai_analysis = self.llm_client.chat(messages, model=model, temperature=0.1, max_tokens=5000)
        
        # 7. 整合结果
        result = {
            "variety": variety,
            "variety_name": data_package.variety_name,
            "analysis_date": data_package.analysis_date,
            "analysis_framework": "四维度基差分析框架",
            "analysis_mode": "Reasoner深度推理" if use_reasoner else "标准分析",
            "data_quality": data_package.data_quality,
            "continuous_basis_analysis": continuous_analysis,
            "seasonal_analysis": seasonal_analysis,
            "inventory_basis_analysis": inventory_analysis,
            "spatial_analysis": spatial_analysis,
            "quality_analysis": quality_analysis,
            "market_context": market_context,
            "professional_charts": professional_charts,
            "ai_comprehensive_analysis": ai_analysis,
            "external_citations": self.analyzer.searcher.get_citations(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 8. 显示结果
        self.display_comprehensive_result(result)
        
        return result
    
    def display_comprehensive_result(self, result: Dict):
        """显示综合分析结果"""
        
        variety = result["variety"]
        variety_name = result["variety_name"]
        analysis_date = result["analysis_date"]
        
        print("\n" + "="*100)
        print(f"🎯 {variety}({variety_name}) 专业基差分析报告")
        print(f"📅 分析日期: {analysis_date}")
        print(f"🧠 分析模式: {result['analysis_mode']}")
        print(f"📊 分析框架: {result['analysis_framework']}")
        print("="*100)
        
        # 数据质量概览
        print("\n📋 数据质量评估:")
        for data_type, quality in result["data_quality"].items():
            status = "✅" if quality == "可用" else "❌"
            print(f"  {status} {data_type}: {quality}")
        
        # 核心指标概览
        continuous = result["continuous_basis_analysis"]
        seasonal = result["seasonal_analysis"]
        inventory = result["inventory_basis_analysis"]
        
        print(f"\n🔍 核心指标概览:")
        print(f"  连续基差: {continuous.get('current_continuous_basis', 'N/A')} 元/吨")
        print(f"  主力基差: {continuous.get('current_main_basis', 'N/A')} 元/吨")
        print(f"  季节性偏离: {seasonal.get('seasonal_deviation', 'N/A')} 元/吨")
        print(f"  库存水平: {inventory.get('inventory_level', '未知')}")
        print(f"  区域分类: {inventory.get('region_classification', '未确定')}")
        
        # AI分析结果与图表集成显示
        print(f"\n🧠 AI综合分析结果:")
        print("-" * 80)
        
        # 分段显示分析内容，并在相应位置插入图表
        ai_analysis = result["ai_comprehensive_analysis"]
        charts = result.get("professional_charts", {})
        
        # 将分析内容按部分分割
        sections = ai_analysis.split("第一部分:")
        if len(sections) > 1:
            # 显示前言
            print(sections[0].strip())
            
            # 处理各个部分
            remaining_content = "第一部分:" + sections[1]
            parts = remaining_content.split("第")
            
            for i, part in enumerate(parts):
                if not part.strip():
                    continue
                
                if i == 0:
                    print(f"\n第{part}")
                else:
                    print(f"\n第{part}")
                
                # 在相应部分后插入图表
                if "一部分:" in part and 'basis_trend' in charts:
                    print("\n" + "="*60)
                    print("📊 图1: 基差走势分析")
                    print("="*60)
                    # 这里显示图表的文字描述，实际HTML图表会在下方显示
                    print("基差走势图显示了主力基差和连续基差的变化趋势，以及收敛性分析")
                    
                elif "二部分:" in part and 'seasonal_pattern' in charts:
                    print("\n" + "="*60)
                    print("📊 图2: 季节性基差规律")
                    print("="*60)
                    print("季节性图表显示了月度基差均值、标准差区间以及当前月份的位置")
                    
                elif "三部分:" in part and 'inventory_level' in charts:
                    print("\n" + "="*60)
                    print("📊 图3: 库存水平分析")
                    print("="*60)
                    print("库存图表显示了库存走势以及历史分位数参考线")
                    
                elif "五部分:" in part and 'term_structure' in charts:
                    print("\n" + "="*60)
                    print("📊 图4: 期限结构曲线")
                    print("="*60)
                    print("期限结构图表显示了各合约的价格分布情况")
        else:
            print(ai_analysis)
        
        print("-" * 80)
        
        # 显示专业图表
        if result.get("professional_charts"):
            print(f"\n📊 专业图表集成展示:")
            print("="*80)
            charts = result["professional_charts"]
            
            if 'basis_trend' in charts:
                print("\n📈 图1: 基差走势分析")
                print("-"*40)
                try:
                    # 尝试在支持HTML的环境中显示图表
                    from IPython.display import display, HTML
                    display(HTML(charts['basis_trend']))
                except:
                    # 在命令行环境中显示图表描述
                    print("基差走势图包含：")
                    print("- 主力基差走势线（蓝色）")
                    print("- 连续基差走势线（红色）") 
                    print("- 10日滚动波动率（绿色，下图）")
                    print("- 显示基差收敛性和时间衰减特征")
                    
            if 'seasonal_pattern' in charts:
                print("\n📊 图2: 季节性基差规律")
                print("-"*40)
                try:
                    from IPython.display import display, HTML
                    display(HTML(charts['seasonal_pattern']))
                except:
                    print("季节性基差图包含：")
                    print("- 月度基差均值曲线（蓝色）")
                    print("- 标准差区间（浅蓝色阴影）")
                    print("- 当前月份位置标记（红色星标）")
                    print("- 显示季节性偏离程度")
                    
            if 'inventory_level' in charts:
                print("\n📦 图3: 库存水平分析")
                print("-"*40)
                try:
                    from IPython.display import display, HTML
                    display(HTML(charts['inventory_level']))
                except:
                    print("库存水平图包含：")
                    print("- 库存走势线（紫色）")
                    print("- 20%分位数线（红色虚线）")
                    print("- 50%分位数线（橙色虚线）")
                    print("- 80%分位数线（绿色虚线）")
                    print("- 显示当前库存历史分位数")
                    
            if 'term_structure' in charts:
                print("\n📉 图4: 期限结构曲线")
                print("-"*40)
                try:
                    from IPython.display import display, HTML
                    display(HTML(charts['term_structure']))
                except:
                    print("期限结构图包含：")
                    print("- 各合约价格曲线（蓝色）")
                    print("- 合约按月份排序")
                    print("- 显示Contango/Backwardation结构")
                    print("- 反映市场对未来价格预期")
            
            print("\n💡 图表说明：")
            print("- 在Jupyter环境中可查看交互式图表")
            print("- 在命令行环境中显示图表描述")
            print("="*80)
        
        # 外部引用信息
        if result.get("external_citations"):
            print(f"\n📚 外部数据来源:")
            for citation in result["external_citations"][:10]:  # 显示前10个引用
                print(f"  {citation['id']} {citation['title']}")
                print(f"      链接: {citation['link']}")
        
        print(f"\n⏰ 分析完成时间: {result['timestamp']}")
        print("="*100)
    
    def _save_charts_to_files(self, charts: Dict, variety: str, analysis_date: str):
        """保存图表到文件"""
        
        try:
            # 创建输出目录
            chart_dir = OUTPUT_DIR / "charts" / variety
            chart_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存各个图表
            chart_names = {
                'basis_trend': '基差走势分析',
                'seasonal_pattern': '季节性基差规律', 
                'inventory_level': '库存水平分析',
                'term_structure': '期限结构曲线'
            }
            
            for chart_key, chart_html in charts.items():
                if chart_key in chart_names:
                    filename = f"{variety}_{chart_key}_{analysis_date}.html"
                    filepath = chart_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(chart_html)
                    
                    print(f"    📁 {chart_names[chart_key]}: {filepath}")
            
        except Exception as e:
            print(f"    ❌ 图表保存失败: {str(e)}")
    
    def start_interactive_analysis(self):
        """启动交互式分析"""
        
        print("\n" + "="*100)
        print("🤖 专业AI基差分析系统 - 四维度分析框架")
        print("📊 集成品质、空间、时间、库存四大维度分析")
        print("✅ 严禁数据编造，确保分析诚实性")
        print("🌐 集成实时搜索，标注外部引用")
        print("="*100)
        
        while True:
            try:
                print("\n" + "-"*60)
                print("请输入分析参数 (输入 'quit' 退出，'help' 查看帮助):")
                
                # 获取用户输入
                user_input = input("\n请输入命令: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 感谢使用专业基差分析系统！")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'varieties':
                    self.show_available_varieties()
                    continue
                
                # 解析输入参数
                if ',' in user_input:
                    parts = [p.strip() for p in user_input.split(',')]
                else:
                    parts = [user_input]
                
                if len(parts) < 1:
                    print("❌ 请至少输入品种代码")
                    continue
                
                variety = parts[0].upper()
                analysis_date = parts[1] if len(parts) > 1 and parts[1] else None
                model_mode = parts[2] if len(parts) > 2 else "chat"
                
                # 验证品种
                available_varieties = self.get_available_varieties()
                if variety not in available_varieties:
                    print(f"❌ 品种 {variety} 不可用")
                    print("💡 输入 'varieties' 查看可用品种")
                    continue
                
                # 验证日期
                if analysis_date:
                    try:
                        datetime.strptime(analysis_date, '%Y-%m-%d')
                    except ValueError:
                        print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
                        continue
                
                # 验证模型模式
                use_reasoner = model_mode.lower() in ['reasoner', 'r']
                
                # 执行分析
                print(f"\n🚀 开始分析 {variety}...")
                if analysis_date:
                    print(f"📅 分析日期: {analysis_date}")
                print(f"🤖 分析模型: {'DeepSeek Reasoner' if use_reasoner else 'DeepSeek Chat'}")
                
                result = self.analyze_variety_comprehensive(variety, analysis_date, use_reasoner)
                
                if "error" in result:
                    print(f"❌ 分析失败: {result['error']}")
                else:
                    print("\n✅ 分析完成！")
                
            except KeyboardInterrupt:
                print("\n\n👋 分析已中断，感谢使用！")
                break
            except Exception as e:
                print(f"❌ 发生错误: {str(e)}")
                continue
    
    def show_help(self):
        """显示帮助信息"""
        print("\n" + "="*80)
        print("📖 使用帮助")
        print("="*80)
        print("输入格式: 品种代码[,分析日期,模型模式]")
        print("\n参数说明:")
        print("  品种代码: 必需，如 RB, CU, M 等")
        print("  分析日期: 可选，格式 YYYY-MM-DD，默认为最新数据")
        print("  模型模式: 可选，chat(默认) 或 reasoner")
        print("\n使用示例:")
        print("  RB                    # 分析螺纹钢，使用默认参数")
        print("  CU,2025-01-01         # 分析沪铜，指定日期")
        print("  M,,reasoner           # 分析豆粕，使用Reasoner模型")
        print("  RM,2024-12-01,r       # 分析菜粕，指定日期和Reasoner模型")
        print("\n其他命令:")
        print("  varieties             # 查看可用品种")
        print("  help                  # 显示帮助")
        print("  quit                  # 退出系统")
        print("="*80)

# 主程序入口
if __name__ == "__main__":
    system = ProfessionalBasisAnalysisSystem()
    system.start_interactive_analysis()
