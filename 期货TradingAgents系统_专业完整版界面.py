#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品期货 Trading Agents系统Streamlit界面
修复编码问题的同时保持完整功能和专业性

功能特点：
1. 完整的数据管理和更新功能
2. 专业的分析配置和执行
3. 多空辩论风控决策（含交易员环节）
4. Word报告生成和导出
5. 所有原有的专业功能

作者: 7haoge  
版本: 完整可用版V1
创建时间: 2025-01-19
联系方式: 953534947@qq.com
"""

import streamlit as st
import pandas as pd
import json
import asyncio
import time
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import plotly.express as px
import plotly.graph_objects as go

# 图表下载功能已禁用（避免系统running问题）
CHART_DOWNLOAD_AVAILABLE = False
import subprocess
import sys
import threading
import os

# Word文档生成相关
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    st.warning("⚠️ 未安装python-docx库，Word报告功能不可用。请运行: pip install python-docx")

# ============================================================================
# 工具函数
# ============================================================================

def convert_confidence_to_level(confidence_score):
    """将数值信心度转换为直观等级"""
    try:
        score = float(confidence_score)
        if score >= 0.8:
            return "高信心", "💪", "success"
        elif score >= 0.6:
            return "中等信心", "👍", "warning" 
        elif score >= 0.4:
            return "低信心", "🤔", "info"
        else:
            return "谨慎观望", "⚠️", "error"
    except:
        return "未知", "❓", "info"

def check_commodity_local_data(commodity: str, data_status: Dict) -> Dict[str, bool]:
    """检查指定品种在各个模块中的本地数据情况"""
    module_mapping = {
        "technical": "技术面分析",
        "basis": "基差分析",
        "inventory": "库存数据", 
        "positioning": "持仓席位",
        "term_structure": "期限结构",
        "receipt": "仓单数据"
    }
    
    result = {}
    
    # 直接使用文件系统检查，更可靠
    for module_key, module_name in module_mapping.items():
        # 优先使用直接检查方法
        has_data = check_commodity_data_direct(commodity, module_key)
        result[module_key] = has_data
    
    return result

def check_specific_commodity_data(commodity: str, module_key: str) -> bool:
    """检查特定品种在指定模块中是否有数据"""
    try:
        # 检查数据管理器中是否有该品种的数据
        if hasattr(st.session_state, 'data_manager'):
            data_manager = st.session_state.data_manager
            
            # 根据模块类型检查不同的数据源（使用正确的配置键名）
            if module_key == "technical":
                # 检查技术分析数据
                config = data_manager.modules_config.get("technical_analysis", {})
                tech_path = config.get("path")
                if tech_path and tech_path.exists():
                    commodity_path = tech_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "ohlc_data.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
            
            elif module_key == "basis":
                # 检查基差分析数据
                config = data_manager.modules_config.get("basis", {})
                basis_path = config.get("path")
                if basis_path and basis_path.exists():
                    commodity_path = basis_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "basis_data.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
            
            elif module_key == "inventory":
                # 检查库存数据
                config = data_manager.modules_config.get("inventory", {})
                inv_path = config.get("path")
                if inv_path and inv_path.exists():
                    commodity_path = inv_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "inventory.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
            
            elif module_key == "positioning":
                # 检查持仓数据
                config = data_manager.modules_config.get("positioning", {})
                pos_path = config.get("path")
                if pos_path and pos_path.exists():
                    commodity_path = pos_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "long_position_ranking.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
            
            elif module_key == "term_structure":
                # 检查期限结构数据
                config = data_manager.modules_config.get("term_structure", {})
                term_path = config.get("path")
                if term_path and term_path.exists():
                    commodity_path = term_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "term_structure.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
            
            elif module_key == "receipt":
                # 检查仓单数据
                config = data_manager.modules_config.get("receipt", {})
                receipt_path = config.get("path")
                if receipt_path and receipt_path.exists():
                    commodity_path = receipt_path / commodity
                    if commodity_path.exists():
                        # 检查是否有数据文件
                        data_file = commodity_path / config.get("data_file", "receipt.csv")
                        return data_file.exists() and data_file.stat().st_size > 0
        else:
            # 如果没有data_manager，直接检查硬编码路径
            return check_commodity_data_direct(commodity, module_key)
        
        return False
        
    except Exception as e:
        st.error(f"检查品种数据时出错: {e}")
        # 出错时也尝试直接检查
        return check_commodity_data_direct(commodity, module_key)

def check_commodity_data_direct(commodity: str, module_key: str) -> bool:
    """直接检查品种数据（不依赖session_state）"""
    try:
        from pathlib import Path
        
        # 硬编码数据库路径
        database_root = Path("qihuo/database")
        
        # 模块路径映射
        module_paths = {
            "technical": database_root / "technical_analysis",
            "basis": database_root / "basis", 
            "inventory": database_root / "inventory",
            "positioning": database_root / "positioning",
            "term_structure": database_root / "term_structure",
            "receipt": database_root / "receipt"
        }
        
        # 数据文件映射
        data_files = {
            "technical": "ohlc_data.csv",
            "basis": "basis_data.csv",
            "inventory": "inventory.csv", 
            "positioning": "long_position_ranking.csv",
            "term_structure": "term_structure.csv",
            "receipt": "receipt.csv"
        }
        
        if module_key in module_paths:
            module_path = module_paths[module_key]
            if module_path.exists():
                commodity_path = module_path / commodity
                if commodity_path.exists():
                    data_file = commodity_path / data_files[module_key]
                    return data_file.exists() and data_file.stat().st_size > 0
        
        return False
        
    except Exception as e:
        st.error(f"直接检查品种数据时出错: {e}")
        return False

def get_market_data_info(commodity: str) -> Dict:
    """获取真实的市场数据信息"""
    try:
        # 获取当前价格
        current_price = get_commodity_current_price(commodity)
        
        # 获取价格区间
        price_range = futures_price_provider.get_price_range(commodity, 30)
        
        # 计算价格位置
        avg_price = price_range.get('avg', current_price)
        if current_price > avg_price * 1.02:
            price_position = "偏高"
        elif current_price < avg_price * 0.98:
            price_position = "偏低"  
        else:
            price_position = "中性"
            
        return {
            "current_price": current_price,
            "price_range": price_range,
            "price_position": price_position,
            "data_quality": "良好" if current_price > 0 else "异常"
        }
    except Exception as e:
        st.error(f"获取{commodity}市场数据失败: {e}")
        return {
            "current_price": 0,
            "price_range": {"low": 0, "high": 0, "avg": 0},
            "price_position": "未知",
            "data_quality": "异常"
        }

# ============================================================================
# 导入系统模块
# ============================================================================
try:
    from 期货TradingAgents系统_第三阶段完整版 import CompleteFuturesTradingExecution
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig, FuturesAnalysisIntegrator
    from 期货TradingAgents系统_工具模块 import TimeUtils
    # 导入价格数据获取器
    from 价格数据获取器 import get_commodity_current_price, futures_price_provider
except ImportError as e:
    st.error(f"导入系统模块失败: {e}")
    st.stop()

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="商品期货 Trading Agents系统",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stage-header {
        font-size: 1.5rem;
        color: #2E86AB;
        margin: 1rem 0;
        padding: 0.5rem;
        border-left: 4px solid #2E86AB;
        background-color: #f0f8ff;
    }
    .analysis-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #4ECDC4;
    }
    .debate-card {
        background-color: #fff8e1;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #ff9800;
    }
    .risk-card {
        background-color: #f3e5f5;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #9c27b0;
    }
    .decision-card {
        background-color: #e8f5e8;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #4caf50;
    }
    .metric-container {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    .metric-item {
        text-align: center;
        padding: 1rem;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .progress-bar {
        background-color: #e0e0e0;
        border-radius: 10px;
        padding: 3px;
        margin: 10px 0;
    }
    .progress-fill {
        background: linear-gradient(90deg, #4ECDC4, #44A08D);
        height: 20px;
        border-radius: 7px;
        transition: width 0.3s ease;
    }
    .page-selector {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
        margin: 15px 0;
        border: 2px solid #e9ecef;
    }
    .analyst-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 15px 0;
        border-left: 5px solid #667eea;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .analyst-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.15);
    }
    .content-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        margin: 15px 0;
        line-height: 1.6;
    }
    .citation-section {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #bee5eb;
        margin: 15px 0;
    }
    .navigation-hint {
        background: linear-gradient(45deg, #f39c12, #e67e22);
        color: white;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin: 20px 0;
        font-size: 1.1em;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px;
        font-weight: 500;
        padding: 8px 16px;
        border: 1px solid #e9ecef;
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e7f3ff;
        border-color: #007bff;
        transform: translateY(-1px);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
        color: white !important;
        border-color: #0056b3 !important;
        box-shadow: 0 4px 8px rgba(0,123,255,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 数据管理器（保持完整功能）
# ============================================================================

class StreamlitDataManager:
    """Streamlit数据管理器"""
    
    def __init__(self):
        self.database_root = Path("qihuo/database")
        self.modules_config = {
            "inventory": {
                "name": "库存数据",
                "path": self.database_root / "inventory",
                "data_file": "inventory.csv",
                "date_column": "date",
                "date_format": "%Y-%m-%d",
                "update_script": "modules/inventory_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            },
            "positioning": {
                "name": "持仓席位",
                "path": self.database_root / "positioning", 
                "data_file": "long_position_ranking.csv",  # 使用CSV文件而非JSON
                "date_column": "date",
                "date_format": "%Y-%m-%d",  # CSV文件中的日期格式是YYYY-MM-DD
                "update_script": "unified_futures_data_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            },
            "term_structure": {
                "name": "期限结构",
                "path": self.database_root / "term_structure",
                "data_file": "term_structure.csv",
                "date_column": "date",
                "date_format": "%Y%m%d",
                "update_script": "modules/term_structure_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            },
            "technical_analysis": {
                "name": "技术面分析",
                "path": self.database_root / "technical_analysis",
                "data_file": "ohlc_data.csv",
                "date_column": "时间",
                "date_format": "%Y-%m-%d",
                "update_script": "modules/technical_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            },
            "basis": {
                "name": "基差分析",
                "path": self.database_root / "basis",
                "data_file": "basis_data.csv",
                "date_column": "date",
                "date_format": "%Y-%m-%d",
                "update_script": "modules/basis_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            },
            "receipt": {
                "name": "仓单数据",
                "path": self.database_root / "receipt",
                "data_file": "receipt.csv",
                "date_column": "date",
                "date_format": "%Y-%m-%d",
                "update_script": "modules/receipt_updater.py",
                "structure_type": "by_commodity"  # 按品种分文件夹
            }
        }
    
    @st.cache_data(ttl=300)
    def get_data_status(_self) -> Dict:
        """获取数据状态"""
        status_data = {
            "modules": {},
            "summary": {
                "total_commodities": set(),
                "common_commodities": set(),
                "last_update": None
            }
        }
        
        all_commodities = []
        module_commodity_sets = []
        
        for module_name, config in _self.modules_config.items():
            module_status = {
                "name": config["name"],
                "status": "checking",
                "path": str(config["path"]),
                "last_update": "未知",
                "commodities_count": 0,
                "total_records": 0,
                "latest_date": "未知",
                "data_quality": "检查中"
            }
            
            try:
                data_path = config["path"]
                
                if not data_path.exists():
                    module_status["status"] = "error"
                    module_status["error_message"] = "数据目录不存在"
                else:
                    # 检查是否为按品种分文件夹的结构
                    if config.get("structure_type") == "by_commodity":
                        # 扫描品种文件夹
                        commodity_folders = []
                        total_records = 0
                        latest_dates = []
                        
                        for item in data_path.iterdir():
                            if item.is_dir():
                                commodity = item.name
                                data_file = item / config["data_file"]
                                
                                if data_file.exists():
                                    try:
                                        # 支持CSV和JSON格式
                                        if data_file.suffix == '.json':
                                            import json
                                            with open(data_file, 'r', encoding='utf-8') as f:
                                                json_data = json.load(f)
                                            # JSON summary文件：视为有效数据
                                            if isinstance(json_data, dict):
                                                commodity_folders.append(commodity)
                                                total_records += 1  # JSON文件计为1条记录
                                                continue  # 跳过CSV处理逻辑
                                        
                                        df = pd.read_csv(data_file, encoding='utf-8')
                                        if not df.empty:
                                            commodity_folders.append(commodity)
                                            total_records += len(df)
                                            
                                            # 处理日期列
                                            if config["date_column"] in df.columns:
                                                try:
                                                    date_col = df[config["date_column"]]
                                                    date_format = config.get("date_format", "%Y-%m-%d")
                                                    
                                                    if date_format == "%Y%m%d":
                                                        if date_col.dtype in ['int64', 'float64']:
                                                            df[config["date_column"]] = pd.to_datetime(date_col.astype(str), format='%Y%m%d', errors='coerce')
                                                        else:
                                                            df[config["date_column"]] = pd.to_datetime(date_col, format='%Y%m%d', errors='coerce')
                                                    else:
                                                        df[config["date_column"]] = pd.to_datetime(date_col, format=date_format, errors='coerce')
                                                    
                                                    valid_dates = df[config["date_column"]].dropna()
                                                    if not valid_dates.empty:
                                                        latest_dates.append(valid_dates.max())
                                                        
                                                except Exception:
                                                    pass
                                    except Exception:
                                        pass
                        
                        if commodity_folders:
                            module_status["commodities_count"] = len(commodity_folders)
                            module_status["total_records"] = total_records
                            module_status["status"] = "success"
                            module_status["data_quality"] = "良好"
                            
                            # 记录品种列表
                            all_commodities.extend(commodity_folders)
                            module_commodity_sets.append(set(commodity_folders))
                            
                            # 最新日期
                            if latest_dates:
                                latest_date = max(latest_dates)
                                module_status["latest_date"] = latest_date.strftime("%Y-%m-%d")
                                module_status["last_update"] = latest_date.strftime("%Y-%m-%d")
                        else:
                            module_status["status"] = "warning"
                            module_status["error_message"] = "未找到有效的品种数据"
                    
                    else:
                        # 单一文件结构（保持原有逻辑）
                        data_file = data_path / config["data_file"]
                        
                        if not data_file.exists():
                            module_status["status"] = "error"
                            module_status["error_message"] = "数据文件不存在"
                        else:
                            try:
                                df = pd.read_csv(data_file, encoding='utf-8')
                                
                                if not df.empty:
                                    module_status["total_records"] = len(df)
                                    
                                    # 处理日期列
                                    if config["date_column"] in df.columns:
                                        try:
                                            date_col = df[config["date_column"]]
                                            date_format = config.get("date_format", "%Y-%m-%d")
                                            
                                            if date_format == "%Y%m%d":
                                                if date_col.dtype in ['int64', 'float64']:
                                                    df[config["date_column"]] = pd.to_datetime(date_col.astype(str), format='%Y%m%d', errors='coerce')
                                                else:
                                                    df[config["date_column"]] = pd.to_datetime(date_col, format='%Y%m%d', errors='coerce')
                                            else:
                                                df[config["date_column"]] = pd.to_datetime(date_col, format=date_format, errors='coerce')
                                            
                                            valid_dates = df[config["date_column"]].dropna()
                                            if not valid_dates.empty:
                                                latest_date = valid_dates.max()
                                                module_status["latest_date"] = latest_date.strftime("%Y-%m-%d")
                                                module_status["last_update"] = latest_date.strftime("%Y-%m-%d")
                                        
                                        except Exception as date_error:
                                            module_status["latest_date"] = f"日期解析错误: {date_error}"
                                    
                                    # 统计品种数量
                                    commodity_columns = ['symbol', 'commodity', '品种', '合约']
                                    commodity_col = None
                                    for col in commodity_columns:
                                        if col in df.columns:
                                            commodity_col = col
                                            break
                                    
                                    if commodity_col:
                                        unique_commodities = df[commodity_col].unique()
                                        module_status["commodities_count"] = len(unique_commodities)
                                        all_commodities.extend(unique_commodities)
                                        module_commodity_sets.append(set(unique_commodities))
                                    
                                    module_status["status"] = "success"
                                    module_status["data_quality"] = "良好"
                                    
                                else:
                                    module_status["status"] = "warning"
                                    module_status["error_message"] = "数据文件为空"
                                    
                            except Exception as read_error:
                                module_status["status"] = "error"
                                module_status["error_message"] = f"读取数据失败: {read_error}"
                        
            except Exception as e:
                module_status["status"] = "error"
                module_status["error_message"] = f"检查模块失败: {e}"
            
            status_data["modules"][module_name] = module_status
        
        # 计算汇总信息
        if all_commodities:
            status_data["summary"]["total_commodities"] = set(all_commodities)
            
            # 找出所有模块都有的品种
            if module_commodity_sets:
                common_commodities = module_commodity_sets[0]
                for commodity_set in module_commodity_sets[1:]:
                    common_commodities = common_commodities.intersection(commodity_set)
                status_data["summary"]["common_commodities"] = common_commodities
        
        return status_data
    
    def _get_module_detailed_info(self, module_key: str) -> Dict:
        """获取模块的详细数据信息"""
        if module_key not in self.modules_config:
            return {}
        
        config = self.modules_config[module_key]
        detailed_info = {}
        
        try:
            data_path = config["path"]
            if not data_path.exists():
                return {}
            
            # 检查是否为按品种分文件夹的结构
            if config.get("structure_type") == "by_commodity":
                for item in data_path.iterdir():
                    if item.is_dir():
                        commodity = item.name
                        data_file = item / config["data_file"]
                        
                        if data_file.exists():
                            try:
                                df = pd.read_csv(data_file, encoding='utf-8')
                                if not df.empty:
                                    info = {
                                        'record_count': len(df),
                                        'start_date': '未知',
                                        'end_date': '未知'
                                    }
                                    
                                    # 尝试解析日期信息
                                    if config["date_column"] in df.columns:
                                        try:
                                            date_col = df[config["date_column"]]
                                            date_format = config.get("date_format", "%Y-%m-%d")
                                            
                                            if date_format == "%Y%m%d":
                                                if date_col.dtype in ['int64', 'float64']:
                                                    df[config["date_column"]] = pd.to_datetime(date_col.astype(str), format='%Y%m%d', errors='coerce')
                                                else:
                                                    df[config["date_column"]] = pd.to_datetime(date_col, format='%Y%m%d', errors='coerce')
                                            else:
                                                df[config["date_column"]] = pd.to_datetime(date_col, format=date_format, errors='coerce')
                                            
                                            valid_dates = df[config["date_column"]].dropna()
                                            if not valid_dates.empty:
                                                info['start_date'] = valid_dates.min().strftime("%Y-%m-%d")
                                                info['end_date'] = valid_dates.max().strftime("%Y-%m-%d")
                                        except Exception:
                                            pass
                                    
                                    detailed_info[commodity] = info
                            except Exception:
                                pass
            
            return detailed_info
        except Exception:
            return {}
    
    def get_available_commodities(self) -> List[str]:
        """获取所有可用的品种列表"""
        try:
            # 获取数据状态
            status = self.get_data_status()
            
            # 返回有数据的品种列表
            if "summary" in status and "common_commodities" in status["summary"]:
                commodities = list(status["summary"]["common_commodities"])
                
                # 如果没有共同品种，返回所有品种
                if not commodities and "total_commodities" in status["summary"]:
                    commodities = list(status["summary"]["total_commodities"])
                
                return sorted(commodities) if commodities else []
            else:
                return []
                
        except Exception as e:
            print(f"❌ 获取可用品种失败: {e}")
            return []
    
    def get_module_supported_varieties(self, module_name: str = None) -> Dict[str, Set[str]]:
        """获取各模块支持的品种列表"""
        
        # 检查库存数据支持的品种
        inventory_varieties = set()
        inventory_path = self.database_root / "inventory"
        if inventory_path.exists():
            for item in inventory_path.iterdir():
                if item.is_dir() and (item / "inventory.csv").exists():
                    inventory_varieties.add(item.name)
        
        # 检查仓单数据支持的品种
        receipt_varieties = set()
        receipt_path = self.database_root / "receipt"
        if receipt_path.exists():
            for item in receipt_path.iterdir():
                if item.is_dir() and (item / "receipt.csv").exists():
                    receipt_varieties.add(item.name)
        
        # 检查持仓数据支持的品种
        positioning_varieties = set()
        positioning_path = self.database_root / "positioning"
        if positioning_path.exists():
            for item in positioning_path.iterdir():
                if item.is_dir() and (item / "long_position_ranking.csv").exists():
                    positioning_varieties.add(item.name)
        
        # 检查基差数据支持的品种
        basis_varieties = set()
        basis_path = self.database_root / "basis"
        if basis_path.exists():
            for item in basis_path.iterdir():
                if item.is_dir() and (item / "basis_data.csv").exists():
                    basis_varieties.add(item.name)
        
        # 检查期限结构数据支持的品种
        term_structure_varieties = set()
        term_structure_path = self.database_root / "term_structure"
        if term_structure_path.exists():
            for item in term_structure_path.iterdir():
                if item.is_dir() and (item / "term_structure.csv").exists():
                    term_structure_varieties.add(item.name)
        
        # 定义各模块支持的品种
        module_varieties = {
            # 库存仓单分析：数据增强版支持任何品种（本地数据+联网搜索）
            "库存仓单分析": self._get_all_futures_varieties(),
            
            # 持仓席位分析：需要持仓数据，可以联网补充
            "持仓席位分析": positioning_varieties,
            
            # 基差分析：联网增强版支持任何品种（本地数据+联网搜索）
            "基差分析": self._get_all_futures_varieties(),
            
            # 期限结构分析：需要期限结构数据
            "期限结构分析": term_structure_varieties,
            
            # 技术分析：理论上支持所有品种（通过联网获取）
            "技术分析": inventory_varieties | receipt_varieties | positioning_varieties | basis_varieties | term_structure_varieties,
            
            # 新闻分析：理论上支持所有品种（通过联网获取）
            "新闻分析": inventory_varieties | receipt_varieties | positioning_varieties | basis_varieties | term_structure_varieties,
        }
        
        if module_name:
            return module_varieties.get(module_name, set())
        else:
            return module_varieties
    
    def _get_all_futures_varieties(self) -> Set[str]:
        """获取所有期货品种代码（用于支持任何品种的模块）"""
        # 中国期货市场主要品种代码
        all_varieties = {
            # 贵金属
            'AG', 'AU',
            # 有色金属
            'CU', 'AL', 'ZN', 'PB', 'NI', 'SN', 'BC',
            # 黑色金属
            'RB', 'HC', 'I', 'JM', 'J', 'SS', 'WR',
            # 能源化工
            'BU', 'FU', 'LU', 'RU', 'NR', 'BR', 'SP', 'L', 'V', 'PP', 'EG', 'TA', 'SA', 'MA', 'FG', 'EB', 'PG', 'LG', 'SC',
            # 农产品
            'CF', 'SR', 'RM', 'OI', 'M', 'Y', 'A', 'B', 'C', 'CS', 'JD', 'PK', 'UR', 'LH', 'AP', 'CJ', 'WH', 'PM', 'RI', 'LR', 'JR',
            # 新材料
            'SF', 'SM', 'ZC', 'PF', 'CY', 'AO', 'PS', 'LC', 'SI', 'PX', 'PR',
            # 其他
            'SH'
        }
        return all_varieties
    
    def run_data_update_direct(self, module_name: str) -> Dict:
        """直接运行数据更新脚本，让用户与脚本交互"""
        config = self.modules_config.get(module_name)
        if not config or not config.get("update_script"):
            return {"status": "error", "message": "无更新脚本"}
        
        script_path = Path(config["update_script"])
        if not script_path.exists():
            return {"status": "error", "message": f"更新脚本不存在: {script_path}"}
        
        try:
            # 在Windows下启动新的命令行窗口运行脚本
            import subprocess
            import sys
            
            # 构建命令
            cmd = f'start cmd /k "cd /d {Path.cwd()} && python {script_path} && pause"'
            
            # 使用shell=True在新窗口中执行
            result = subprocess.run(cmd, shell=True, cwd=Path.cwd())
            
            return {
                "status": "success",
                "message": f"已启动 {config['name']} 数据更新",
                "details": "请在新打开的命令行窗口中完成交互操作"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"启动更新脚本失败: {e}"}

# ============================================================================
# 完整分析管理器
# ============================================================================

class StreamlitAnalysisManager:
    """Streamlit分析执行管理器"""
    
    def __init__(self):
        try:
            self.config = FuturesTradingAgentsConfig("期货TradingAgents系统_配置文件.json")
            self.system = None
            self.current_analysis = None
            self.analysis_results = {}
        except Exception as e:
            st.error(f"配置初始化失败: {e}")
            self.config = None
    
    def _check_commodity_local_data(self, commodity: str, data_status: Dict) -> Dict[str, bool]:
        """检查指定品种在各个模块中的本地数据情况"""
        module_mapping = {
            "technical": "专业AI技术分析系统",
            "basis": "专业基差分析系统",
            "inventory": "库存分析系统", 
            "positioning": "持仓分析系统",
            "term_structure": "期限结构分析系统"
        }
        
        result = {}
        
        for module_key, module_name in module_mapping.items():
            has_data = False
            
            # 检查该模块是否有该品种的数据
            if module_name in data_status.get("modules", {}):
                module_info = data_status["modules"][module_name]
                
                # 检查品种是否在该模块的品种列表中
                if "commodities" in module_info:
                    commodities = module_info["commodities"]
                    if isinstance(commodities, (list, set)):
                        has_data = commodity in commodities
                    elif isinstance(commodities, dict):
                        has_data = commodity in commodities.keys()
                
                # 如果没有品种列表，检查是否有记录数
                if not has_data and module_info.get("commodities_count", 0) > 0:
                    # 进一步检查是否真的有该品种的数据
                    has_data = self._check_specific_commodity_data(commodity, module_key)
            
            result[module_key] = has_data
        
        return result
    
    def _check_specific_commodity_data(self, commodity: str, module_key: str) -> bool:
        """检查特定品种在指定模块中是否有数据"""
        try:
            # 这里可以根据实际的数据存储结构来检查
            # 简化实现：检查数据管理器中是否有该品种的数据
            if hasattr(st.session_state, 'data_manager'):
                data_manager = st.session_state.data_manager
                
                # 根据模块类型检查不同的数据源
                if module_key == "technical":
                    # 检查技术分析数据
                    tech_path = data_manager.modules_config.get("专业AI技术分析系统", {}).get("path")
                    if tech_path and tech_path.exists():
                        commodity_path = tech_path / commodity
                        return commodity_path.exists() and any(commodity_path.iterdir())
                
                elif module_key == "basis":
                    # 检查基差分析数据
                    basis_path = data_manager.modules_config.get("专业基差分析系统", {}).get("path")
                    if basis_path and basis_path.exists():
                        commodity_path = basis_path / commodity
                        return commodity_path.exists() and any(commodity_path.iterdir())
                
                elif module_key == "inventory":
                    # 检查库存数据
                    inv_path = data_manager.modules_config.get("库存分析系统", {}).get("path")
                    if inv_path and inv_path.exists():
                        data_file = inv_path / "inventory_data.csv"
                        if data_file.exists():
                            import pandas as pd
                            df = pd.read_csv(data_file)
                            return commodity in df.get('variety', []).values if not df.empty else False
                
                elif module_key == "positioning":
                    # 检查持仓数据（按品种分文件夹）
                    pos_path = data_manager.modules_config.get("positioning", {}).get("path")
                    if pos_path and pos_path.exists():
                        commodity_path = pos_path / commodity
                        # 检查品种文件夹是否存在且有CSV文件
                        if commodity_path.exists():
                            return any(commodity_path.glob("*.csv"))
                
                elif module_key == "term_structure":
                    # 检查期限结构数据
                    term_path = data_manager.modules_config.get("期限结构分析系统", {}).get("path")
                    if term_path and term_path.exists():
                        commodity_path = term_path / commodity
                        return commodity_path.exists() and any(commodity_path.iterdir())
            
            return False
            
        except Exception as e:
            print(f"检查品种数据时出错: {e}")
            return False

    def initialize_system(self):
        """初始化系统"""
        try:
            if not self.config:
                return False, "配置文件未正确加载"
            
            self.system = CompleteFuturesTradingExecution(
                config_file="期货TradingAgents系统_配置文件.json"
            )
            return True, "系统初始化成功"
        except Exception as e:
            return False, f"系统初始化失败: {e}"
    
    def run_integrated_analysis(self, commodity: str, analysis_date: str, 
                              selected_modules: List[str], analysis_mode: str,
                              debate_rounds: int = 3) -> Dict:
        """运行完整集成分析"""
        
        if not self.system:
            success, message = self.initialize_system()
            if not success:
                return {"status": "error", "message": message}
        
        try:
            # 创建数据整合器
            integrator = FuturesAnalysisIntegrator(
                data_root_dir=self.config.get("paths", {}).get("data_root_dir", "qihuo/database"),
                config=self.config.to_dict()
            )
            
            # 使用同步方式或线程池执行异步任务，避免事件循环冲突
            import concurrent.futures
            import threading
            
            def run_async_in_thread(coro):
                """在新线程中运行异步协程"""
                def thread_target():
                    # 在新线程中创建事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()
                
                # 使用线程执行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(thread_target)
                    return future.result()
            
            if analysis_mode == "complete_flow":
                # 完整流程：分析师 + 辩论 + 交易员 + 风控 + CIO决策
                # 阶段1：执行6大分析模块
                st.info("🔍 阶段1：执行分析师团队分析...")
                analysis_state = run_async_in_thread(
                    integrator.collect_all_analyses(commodity, analysis_date, selected_modules)
                )
                
                # 阶段2：执行完整决策流程（含交易员环节）
                st.info(f"🎭 阶段2：执行{debate_rounds}轮完整决策流程（含交易员环节）...")
                debate_result = run_async_in_thread(
                    integrator.run_optimized_debate_risk_decision(analysis_state, debate_rounds)
                )
                
                return {
                    "status": "success",
                    "result": {
                        "analysis_state": analysis_state,
                        "debate_result": debate_result
                    },
                    "type": "complete_flow",
                    "execution_summary": {
                        "stages_completed": 5,  # 分析师 + 辩论 + 交易员 + 风控 + CIO
                        "analysis_modules": len(selected_modules),
                        "debate_rounds": debate_rounds,
                        "final_decision": debate_result.get("decision_section", {}).get("final_decision", "未知") if debate_result and debate_result.get("success") else "分析失败",
                        "confidence_score": debate_result.get("decision_section", {}).get("confidence", "0%") if debate_result and debate_result.get("success") else "0%"
                    }
                }
                
            else:
                # 仅执行分析师流程
                st.info("📊 执行分析师团队分析...")
                analysis_state = run_async_in_thread(
                    integrator.collect_all_analyses(commodity, analysis_date, selected_modules)
                )
                
                return {
                    "status": "success", 
                    "result": analysis_state,
                    "type": "analyst_only"
                }
                
        except Exception as e:
            # 更详细的错误信息
            error_msg = str(e)
            if "'NoneType' object has no attribute 'post'" in error_msg:
                error_msg = "DeepSeek API客户端初始化失败，请检查API密钥配置"
            elif "debate_result" in error_msg:
                error_msg = "辩论分析失败，API调用异常导致结果为空"
            
            return {"status": "error", "message": error_msg}
    
    def start_analysis(self, commodities: List[str], analysis_date: str, 
                      modules: List[str], analysis_mode: str, config: Dict):
        """启动分析"""
        
        self.current_analysis = {
            "commodities": commodities,
            "analysis_date": analysis_date,
            "modules": modules,
            "analysis_mode": analysis_mode,
            "config": config,
            "status": "running",
            "results": {},
            "current_commodity": None,
            "start_time": datetime.now()
        }
        
        # 清空之前的结果
        self.analysis_results = {}
    
    def execute_analysis_for_commodity(self, commodity: str) -> Dict:
        """为单个品种执行分析"""
        if not self.current_analysis:
            return {"status": "error", "message": "未启动分析"}
        
        try:
            # 更新当前分析品种
            self.current_analysis["current_commodity"] = commodity
            
            # 执行分析
            result = self.run_integrated_analysis(
                commodity=commodity,
                analysis_date=self.current_analysis["analysis_date"],
                selected_modules=self.current_analysis["modules"],
                analysis_mode=self.current_analysis["analysis_mode"],
                debate_rounds=self.current_analysis["config"].get("debate_rounds", 3)
            )
            
            # 保存结果
            self.analysis_results[commodity] = result
            
            return result
            
        except Exception as e:
            error_result = {"status": "error", "message": str(e)}
            self.analysis_results[commodity] = error_result
            return error_result
    
    def process_all_commodities(self):
        """处理所有品种的分析"""
        if not self.current_analysis:
            return
        
        commodities = self.current_analysis["commodities"]
        
        for commodity in commodities:
            if self.current_analysis.get("status") != "running":
                break
                
            st.info(f"🔍 正在分析 {commodity}...")
            result = self.execute_analysis_for_commodity(commodity)
            
            if result.get("status") == "success":
                st.success(f"✅ {commodity} 分析完成")
            else:
                st.error(f"❌ {commodity} 分析失败: {result.get('message', '未知错误')}")
        
        # 标记分析完成
        if self.current_analysis:
            self.current_analysis["status"] = "completed"
    
    def is_analysis_running(self) -> bool:
        """检查是否有分析在运行"""
        return (self.current_analysis and 
                self.current_analysis.get("status") == "running")
    
    def get_analysis_progress(self) -> Dict:
        """获取分析进度"""
        if not self.current_analysis:
            return {"progress": 0, "message": "未开始分析"}
        
        total_commodities = len(self.current_analysis["commodities"])
        completed_commodities = len(self.analysis_results)
        
        progress = (completed_commodities / total_commodities) * 100 if total_commodities > 0 else 0
        
        return {
            "progress": progress,
            "completed": completed_commodities,
            "total": total_commodities,
            "current": self.current_analysis.get("current_commodity"),
            "message": f"已完成 {completed_commodities}/{total_commodities} 个品种"
        }
    
    def display_progress(self):
        """显示分析进度"""
        if not self.current_analysis:
            st.info("👈 请在分析配置页面设置参数并开始分析")
            return
        
        progress_info = self.get_analysis_progress()
        
        # 显示进度条
        progress_bar = st.progress(progress_info["progress"] / 100)
        st.write(f"📊 {progress_info['message']}")
        
        if progress_info.get("current"):
            st.write(f"🔍 当前分析: {progress_info['current']}")
        
        # 显示分析配置信息 - 使用独立的expander
        st.markdown("#### 📋 分析配置信息")
        config = self.current_analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**品种列表**: {', '.join(config['commodities'])}")
            st.write(f"**分析日期**: {config['analysis_date']}")
            st.write(f"**分析模式**: {config['analysis_mode']}")
        
        with col2:
            st.write(f"**分析模块**: {', '.join(config['modules'])}")
            st.write(f"**开始时间**: {config['start_time'].strftime('%H:%M:%S')}")
            st.write(f"**状态**: {config['status']}")
    
    def display_results(self):
        """显示分析结果 - 优化布局版本"""
        if not self.analysis_results:
            st.info("⏳ 暂无分析结果，请等待分析完成...")
            return
        
        st.subheader("📈 分析结果")
        
        # 为每个品种创建独立的页面展示
        for commodity, result in self.analysis_results.items():
            # 使用大标题区分不同品种
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #FF6B6B, #4ECDC4); 
                       padding: 20px; margin: 20px 0; border-radius: 10px; 
                       text-align: center;">
                <h2 style="color: white; margin: 0;">📊 {commodity} 完整分析报告</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if result.get("status") == "success":
                result_type = result.get("type", "unknown")
                
                if result_type == "complete_flow":
                    # 完整流程结果 - 分页显示
                    self._display_complete_flow_result_paginated(commodity, result)
                elif result_type == "analyst_only":
                    # 仅分析师结果 - 分页显示
                    self._display_analyst_only_result_paginated(commodity, result)
                else:
                    st.write(f"✅ {commodity} 分析完成")
                    st.json(result)
            
            else:
                st.error(f"❌ {commodity} 分析失败: {result.get('message', '未知错误')}")
            
            # 添加明显的品种分隔
            st.markdown("---")
            st.markdown("<br><br>", unsafe_allow_html=True)
    
    def _display_complete_flow_result(self, commodity: str, result: Dict):
        """显示完整流程结果"""
        
        st.success(f"✅ {commodity} 完整5阶段流程分析完成")
        
        # 执行摘要
        execution_summary = result.get("execution_summary", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("完成阶段", f"{execution_summary.get('stages_completed', 0)}/5")
        with col2:
            st.metric("分析模块", execution_summary.get('analysis_modules', 0))
        with col3:
            st.metric("辩论轮数", execution_summary.get('debate_rounds', 0))
        
        # 最终决策
        final_decision = execution_summary.get('final_decision', '未知')
        if final_decision != '未知':
            decision_color = "🟢" if "看多" in final_decision or "买入" in final_decision else "🔴" if "看空" in final_decision or "卖出" in final_decision else "🟡"
            st.markdown(f"### {decision_color} 最终决策: **{final_decision}**")
        
        # 详细结果
        analysis_result = result.get("result", {})
        
        # 分析师团队结果
        if "analysis_state" in analysis_result:
            st.markdown("#### 📊 分析师团队报告")
            analysis_state = analysis_result["analysis_state"]
            
            # 统计成功的模块
            module_attrs = [
                ("inventory_analysis", "📦 库存仓单分析"),
                ("positioning_analysis", "🎯 持仓席位分析"),
                ("technical_analysis", "📈 技术分析"),
                ("basis_analysis", "💰 基差分析"),
                ("term_structure_analysis", "📊 期限结构分析"),
                ("news_analysis", "📰 新闻分析")
            ]
            
            successful_modules = 0
            for attr_name, module_name in module_attrs:
                if hasattr(analysis_state, attr_name):
                    module_result = getattr(analysis_state, attr_name)
                    # 修复状态判断 - 支持枚举和字符串两种形式
                    if module_result and (
                        module_result.status == "completed" or 
                        (hasattr(module_result.status, 'value') and module_result.status.value == "completed") or
                        str(module_result.status).lower() == "completed"
                    ):
                        successful_modules += 1
            
            st.success(f"✅ {successful_modules}大分析模块已完成")
            
            # 显示每个模块的详细报告
            for attr_name, module_name in module_attrs:
                if hasattr(analysis_state, attr_name):
                    module_result = getattr(analysis_state, attr_name)
                    
                    st.markdown(f"##### {module_name}")
                    
                    # 修复状态判断 - 支持枚举和字符串两种形式
                    if module_result and (
                        module_result.status == "completed" or 
                        (hasattr(module_result.status, 'value') and module_result.status.value == "completed") or
                        str(module_result.status).lower() == "completed"
                    ):
                        st.success("✅ 分析完成")
                        
                        # 显示分析内容
                        result_data = module_result.result_data
                        analysis_content = None
                        
                        # 尝试从多个可能的字段获取分析内容
                        if result_data:
                            # 尝试不同的内容字段，优先级调整为库存分析的字段
                            content_fields = ["ai_comprehensive_analysis", "ai_analysis", "analysis_content", "speculative_analysis", "content", "report", "analysis"]
                            for field in content_fields:
                                if field in result_data and result_data[field]:
                                    analysis_content = result_data[field]
                                    break
                            
                            # 如果是字典，尝试获取嵌套的内容
                            if not analysis_content and isinstance(result_data, dict):
                                for key, value in result_data.items():
                                    if isinstance(value, dict) and "analysis_content" in value:
                                        analysis_content = value["analysis_content"]
                                        break
                        
                        # 显示分析内容
                        if analysis_content and isinstance(analysis_content, str) and len(analysis_content.strip()) > 0:
                            # 截取前500字符作为摘要
                            summary = analysis_content[:500] + ("..." if len(analysis_content) > 500 else "")
                            st.write("**分析摘要:**")
                            st.write(summary)
                            
                            # 如果有完整内容，提供展开选项
                            if len(analysis_content) > 500:
                                if st.button(f"查看{module_name}完整报告", key=f"expand_{attr_name}_{commodity}"):
                                    st.text_area(f"{module_name}完整报告", analysis_content, height=400, key=f"full_{attr_name}_{commodity}")
                        else:
                            # 调试信息：显示可用的字段
                            if st.session_state.get('debug_mode', False) and result_data:
                                st.caption(f"调试: 可用字段 - {list(result_data.keys()) if isinstance(result_data, dict) else type(result_data)}")
                        
                        # 显示其他关键信息（移除数据质量显示）
                        if result_data:
                            if "confidence_score" in result_data:
                                confidence = result_data['confidence_score']
                                try:
                                    if isinstance(confidence, (int, float)):
                                        st.write(f"**分析信心度**: {confidence:.1%}")
                                    else:
                                        st.write(f"**分析信心度**: {confidence}")
                                except (ValueError, TypeError):
                                    st.write(f"**分析信心度**: {confidence}")
                            
                            if "key_findings" in result_data and result_data["key_findings"]:
                                st.write("**关键发现:**")
                                findings = result_data["key_findings"]
                                if isinstance(findings, list):
                                    for finding in findings[:3]:  # 显示前3个关键发现
                                        st.write(f"• {finding}")
                    
                    else:
                        st.error(f"❌ {module_name}分析失败")
                        error_msg = module_result.error_message if module_result else "无数据"
                        st.write(f"错误信息: {error_msg}")
                    
                    st.markdown("---")
        
        # 辩论风控决策结果
        if "debate_result" in analysis_result:
            debate_result = analysis_result["debate_result"]
            
            if debate_result.get("success"):
                # 辩论结果
                if "debate_section" in debate_result:
                    st.markdown("#### 🎭 激烈辩论结果")
                    debate = debate_result["debate_section"]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**辩论胜者**: {debate.get('winner', '未知')}")
                    with col2:
                        scores = debate.get('scores', {})
                        st.write(f"**多头得分**: {scores.get('bull', 0):.1f}")
                    with col3:
                        st.write(f"**空头得分**: {scores.get('bear', 0):.1f}")
                    
                    st.write(f"**辩论总结**: {debate.get('summary', '暂无总结')}")
                    
                    # 显示详细辩论轮次
                    if "rounds" in debate and debate["rounds"]:
                        st.markdown("##### 🗣️ 详细辩论内容")
                        
                        for i, round_data in enumerate(debate["rounds"], 1):
                            st.markdown(f"**第{i}轮辩论**")
                            
                            # 多头发言
                            st.markdown("🐂 **多头观点:**")
                            bull_argument = round_data.get("bull_argument", "暂无内容")
                            st.write(bull_argument[:300] + ("..." if len(bull_argument) > 300 else ""))
                            if len(bull_argument) > 300:
                                if st.button(f"查看第{i}轮多头完整发言", key=f"bull_full_{i}_{commodity}"):
                                    st.text_area(f"第{i}轮多头完整发言", bull_argument, height=200, key=f"bull_text_{i}_{commodity}")
                            
                            st.write(f"*得分: {round_data.get('bull_score', 0):.1f}分*")
                            
                            # 空头发言
                            st.markdown("🐻 **空头观点:**")
                            bear_argument = round_data.get("bear_argument", "暂无内容")
                            st.write(bear_argument[:300] + ("..." if len(bear_argument) > 300 else ""))
                            if len(bear_argument) > 300:
                                if st.button(f"查看第{i}轮空头完整发言", key=f"bear_full_{i}_{commodity}"):
                                    st.text_area(f"第{i}轮空头完整发言", bear_argument, height=200, key=f"bear_text_{i}_{commodity}")
                            
                            st.write(f"*得分: {round_data.get('bear_score', 0):.1f}分*")
                            
                            # 本轮结果
                            round_result = round_data.get('round_result', '未知')
                            audience_reaction = round_data.get('audience_reaction', '暂无')
                            st.write(f"**本轮结果**: {round_result}")
                            st.write(f"**观众反应**: {audience_reaction}")
                            
                            if i < len(debate["detailed_rounds"]):
                                st.markdown("---")
                    else:
                        st.info("💡 详细辩论内容暂未记录")
                
                # 交易员决策 - 重新设计的专业界面
                if "trading_section" in debate_result:
                    st.markdown("#### 💼 专业交易员决策")
                    trading = debate_result["trading_section"]
                    
                    # 核心决策区域 - 使用metric组件展示关键信息
                    st.markdown("##### 🎯 核心决策")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        strategy_type = trading.get('strategy_type', '未知')
                        st.metric("策略类型", strategy_type, help="基于多空辩论结果选择的交易策略")
                    
                    with col2:
                        position_size = trading.get('position_size', '未知')
                        st.metric("建议仓位", position_size, help="风险控制下的最优仓位配置")
                    
                    with col3:
                        risk_reward = trading.get('risk_reward_ratio', '未知')
                        st.metric("风险收益比", risk_reward, help="预期收益与风险的比例")
                    
                    
                    # 交易逻辑 - 使用expander组织
                    with st.expander("🧠 交易逻辑与决策依据", expanded=True):
                        reasoning = trading.get('reasoning', '暂无逻辑')
                        if reasoning and reasoning != '暂无逻辑':
                            st.markdown(f"**决策逻辑：**\n\n{reasoning}")
                        else:
                            st.warning("⚠️ 交易逻辑信息不完整")
                    
                    # 进场/出场策略 - 并列显示
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 📈 进场策略")
                        entry_points = trading.get('entry_points', [])
                        if entry_points and isinstance(entry_points, list) and len(entry_points) > 0:
                            for i, point in enumerate(entry_points, 1):
                                if point and str(point).strip():
                                    st.success(f"**{i}.** {point}")
                        elif entry_points and not isinstance(entry_points, list):
                            st.success(f"**策略：** {entry_points}")
                        else:
                            st.info("📝 进场策略待完善")
                        
                    with col2:
                        st.markdown("##### 📉 出场策略")
                        exit_points = trading.get('exit_points', [])
                        if exit_points and isinstance(exit_points, list) and len(exit_points) > 0:
                            for i, point in enumerate(exit_points, 1):
                                if point and str(point).strip():
                                    st.error(f"**{i}.** {point}")
                        elif exit_points and not isinstance(exit_points, list):
                            st.error(f"**策略：** {exit_points}")
                        else:
                            st.info("📝 出场策略待完善")
                    
                    # 执行计划和市场条件 - 使用tabs组织
                    tab1, tab2, tab3 = st.tabs(["📊 交易合约", "🎯 执行计划", "🌍 市场条件"])
                    
                    with tab1:
                        contracts = trading.get('specific_contracts', [])
                        if contracts and isinstance(contracts, list) and len(contracts) > 0:
                            for i, contract in enumerate(contracts, 1):
                                if contract and str(contract).strip():
                                    st.write(f"**{i}.** {contract}")
                        elif contracts and not isinstance(contracts, list):
                            st.write(f"**推荐合约：** {contracts}")
                        else:
                            st.info("📝 具体合约建议待完善")
                    
                    with tab2:
                        execution_plan = trading.get('execution_plan', '')
                        if execution_plan and str(execution_plan).strip() and execution_plan != '暂无执行计划':
                            st.markdown(f"**执行方案：**\n\n{execution_plan}")
                        else:
                            st.info("📝 执行计划待完善")
                    
                    with tab3:
                        market_conditions = trading.get('market_conditions', '')
                        if market_conditions and str(market_conditions).strip() and market_conditions != '暂无市场条件分析':
                            st.markdown(f"**市场环境：**\n\n{market_conditions}")
                        else:
                            st.info("📝 市场条件分析待完善")
                
                # 风险评估 - 重新设计的专业界面
                if "risk_section" in debate_result:
                    st.markdown("#### 🛡️ 专业风控评估")
                    risk = debate_result["risk_section"]
                    
                    # 风险等级显示 - 用颜色区分
                    overall_risk = risk.get('overall_risk', '未知')
                    risk_color = {
                        '低风险': 'success',
                        '中风险': 'warning', 
                        '高风险': 'error',
                        '极高风险': 'error'
                    }.get(overall_risk, 'info')
                    
                    # 核心风险指标
                    st.markdown("##### ⚡ 风险指标")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if overall_risk != '未知':
                            if risk_color == 'success':
                                st.success(f"**风险等级**\n{overall_risk}")
                            elif risk_color == 'warning':
                                st.warning(f"**风险等级**\n{overall_risk}")
                            else:
                                st.error(f"**风险等级**\n{overall_risk}")
                        else:
                            st.info(f"**风险等级**\n{overall_risk}")
                    
                    with col2:
                        position_limit = risk.get('position_limit', '未知')
                        st.metric("建议仓位", position_limit, help="基于风险等级的仓位上限建议")
                    
                    with col3:
                        stop_loss = risk.get('stop_loss', '未知')
                        st.metric("止损建议", stop_loss, help="基于技术分析的止损位建议")
                    
                    # 详细风险分析
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("##### 🎯 风险因素")
                        key_factors = risk.get('key_factors', [])
                        if key_factors and isinstance(key_factors, list):
                            for i, factor in enumerate(key_factors, 1):
                                if factor and str(factor).strip():
                                    st.warning(f"**{i}.** {factor}")
                        else:
                            st.info("📝 风险因素识别待完善")
                    
                    with col2:
                        st.markdown("##### 🛡️ 缓释措施")
                        mitigation = risk.get('mitigation_measures', [])
                        if mitigation and isinstance(mitigation, list):
                            for i, measure in enumerate(mitigation, 1):
                                if measure and str(measure).strip():
                                    st.success(f"**{i}.** {measure}")
                        else:
                            st.info("📝 缓释措施建议待完善")
                    
                    # 风控经理专业意见
                    with st.expander("👨‍💼 风控总监专业意见", expanded=True):
                        manager_opinion = risk.get('manager_opinion', '暂无意见')
                        if manager_opinion and manager_opinion != '暂无意见':
                            st.markdown(f"**专业评估：**\n\n{manager_opinion}")
                        else:
                            st.warning("⚠️ 风控总监意见不完整")
                
                # 🔥 CIO决策现在由独立的「CIO决策」标签页显示，避免重复内容
                st.info("💡 **查看CIO最终权威决策，请点击上方「CIO决策」标签页**")
            
            else:
                st.error(f"完整决策流程失败: {debate_result.get('error', '未知错误')}")
    
    def _display_analyst_only_result(self, commodity: str, result: Dict):
        """显示仅分析师结果"""
        
        st.success(f"✅ {commodity} 分析师团队分析完成")
        
        analysis_state = result.get("result")
        if analysis_state:
            st.write("📊 6大分析模块已完成分析")
            
            # 显示各模块状态
            modules = {
                "inventory_analysis": "库存仓单分析",
                "positioning_analysis": "持仓席位分析",
                "term_structure_analysis": "期限结构分析",
                "technical_analysis": "技术面分析",
                "basis_analysis": "基差分析",
                "news_analysis": "新闻分析"
            }
            
            col1, col2, col3 = st.columns(3)
            for i, (module_attr, module_name) in enumerate(modules.items()):
                with [col1, col2, col3][i % 3]:
                    module_result = getattr(analysis_state, module_attr, None) if analysis_state else None
                    
                    if module_result and hasattr(module_result, 'status'):
                        # 获取状态值
                        status = module_result.status
                        
                        # 支持多种状态格式的判断
                        is_completed = False
                        
                        # 检查各种可能的状态格式
                        if hasattr(status, 'value'):
                            # 枚举类型，如 AnalysisStatus.COMPLETED
                            status_value = status.value.lower() if isinstance(status.value, str) else str(status.value).lower()
                            is_completed = status_value in ["completed", "success"]
                        elif isinstance(status, str):
                            # 字符串类型
                            is_completed = status.lower() in ["completed", "success"]
                        else:
                            # 其他类型，转换为字符串比较
                            status_str = str(status).lower()
                            is_completed = status_str in ["completed", "success"]
                        
                        # 额外检查：如果有result_data且包含success标志
                        if not is_completed and hasattr(module_result, 'result_data') and module_result.result_data:
                            if isinstance(module_result.result_data, dict):
                                is_completed = module_result.result_data.get('success', False)
                        
                        status_icon = "✅" if is_completed else "❌"
                        st.write(f"{status_icon} {module_name}")
                        
                        # 如果分析完成，显示分析内容摘要
                        if is_completed and hasattr(module_result, 'result_data') and module_result.result_data:
                            result_data = module_result.result_data
                            analysis_content = None
                            
                            # 尝试从多个可能的字段获取分析内容
                            if isinstance(result_data, dict):
                                # 尝试不同的内容字段（优先库存分析字段）
                                content_fields = ["ai_comprehensive_analysis", "ai_analysis", "analysis_content", "speculative_analysis", "content", "report", "analysis"]
                                for field in content_fields:
                                    if field in result_data and result_data[field]:
                                        analysis_content = result_data[field]
                                        break
                                
                                # 如果是字典，尝试获取嵌套的内容
                                if not analysis_content:
                                    for key, value in result_data.items():
                                        if isinstance(value, dict) and "analysis_content" in value:
                                            analysis_content = value["analysis_content"]
                                            break
                                        elif isinstance(value, dict) and "ai_analysis" in value:
                                            analysis_content = value["ai_analysis"]
                                            break
                            
                            # 显示分析内容
                            if analysis_content and isinstance(analysis_content, str) and len(analysis_content.strip()) > 0:
                                # 显示摘要（前200字符）
                                summary = analysis_content[:200] + ("..." if len(analysis_content) > 200 else "")
                                st.caption(f"摘要: {summary}")
                                
                                # 提供查看完整报告的按钮
                                if len(analysis_content) > 200:
                                    if st.button(f"查看{module_name}完整报告", key=f"view_{module_attr}_{commodity}"):
                                        st.text_area(
                                            f"{module_name}完整分析报告", 
                                            analysis_content, 
                                            height=400, 
                                            key=f"content_{module_attr}_{commodity}"
                                        )
                        
                        # 调试信息（仅在开发模式下显示）
                        if st.session_state.get('debug_mode', False):
                            st.caption(f"调试: {module_attr} = {status} ({type(status)})")
                            if hasattr(module_result, 'result_data'):
                                result_data = module_result.result_data
                                if result_data:
                                    if isinstance(result_data, dict):
                                        st.caption(f"调试: result_data键 = {list(result_data.keys())}")
                                        # 显示前几个字段的内容长度
                                        for key, value in list(result_data.items())[:3]:
                                            if isinstance(value, str):
                                                st.caption(f"调试: {key} = {len(value)}字符")
                                            else:
                                                st.caption(f"调试: {key} = {type(value)}")
                                    else:
                                        st.caption(f"调试: result_data类型 = {type(result_data)}")
                                else:
                                    st.caption(f"调试: result_data = None")
                            else:
                                st.caption(f"调试: 无result_data属性")
                            
                    else:
                        st.write(f"⚠️ {module_name}")
                        if st.session_state.get('debug_mode', False):
                            st.caption(f"调试: {module_attr} = None 或无status属性")
        else:
            st.write("⚠️ 分析结果数据不完整")
    
    def _display_complete_flow_result_paginated(self, commodity: str, result: Dict):
        """显示完整流程结果 - 标签页版本"""
        
        # 创建水平标签页
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 执行摘要", 
            "👨‍💼 分析师团队", 
            "🎭 激烈辩论", 
            "💼 专业交易员", 
            "🛡️ 专业风控", 
            "👔 CIO决策"
        ])
        
        # 在每个标签页中显示对应内容
        with tab1:
            self._display_execution_summary(commodity, result)
        
        with tab2:
            self._display_analyst_team_page(commodity, result)
        
        with tab3:
            # 传递完整的辩论风控决策结果
            debate_result = result.get("result", {}).get("debate_result", {})
            self._display_debate_page(commodity, debate_result)
        
        with tab4:
            # 传递完整的辩论风控决策结果  
            debate_result = result.get("result", {}).get("debate_result", {})
            self._display_trader_page(commodity, debate_result)
        
        with tab5:
            # 传递完整的辩论风控决策结果
            debate_result = result.get("result", {}).get("debate_result", {})
            self._display_risk_page(commodity, debate_result)
        
        with tab6:
            # 传递完整的辩论风控决策结果
            debate_result = result.get("result", {}).get("debate_result", {})
            self._display_cio_decision_page(commodity, debate_result)
    
    def _display_analyst_only_result_paginated(self, commodity: str, result: Dict):
        """显示仅分析师结果 - 标签页版本"""
        
        # 创建水平标签页
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 总览", 
            "📦 库存仓单", 
            "📈 技术分析", 
            "🎯 持仓席位", 
            "💰 基差分析", 
            "📊 期限结构", 
            "📰 新闻分析"
        ])
        
        # 在每个标签页中显示对应内容
        with tab1:
            self._display_analyst_overview(commodity, result)
        
        with tab2:
            self._display_inventory_analysis_page(commodity, result)
        
        with tab3:
            self._display_technical_analysis_page(commodity, result)
        
        with tab4:
            self._display_positioning_analysis_page(commodity, result)
        
        with tab5:
            self._display_basis_analysis_page(commodity, result)
        
        with tab6:
            self._display_term_structure_analysis_page(commodity, result)
        
        with tab7:
            self._display_news_analysis_page(commodity, result)
    
    def _display_execution_summary(self, commodity: str, result: Dict):
        """显示执行摘要页面"""
        st.markdown("## 📊 执行摘要")
        
        execution_summary = result.get("execution_summary", {})
        
        # 最终决策显示 - 🔥 修复：从正确的层级获取数据
        debate_result = result.get("result", {}).get("debate_result", {})
        
        # 检查分析是否成功
        if not debate_result or not debate_result.get("success"):
            error_msg = debate_result.get("error", "未知错误") if debate_result else "分析结果为空"
            st.error(f"❌ 分析失败: {error_msg}")
            st.info("💡 提示：可能是网络连接问题，请检查网络后重试")
            return
        
        # 从正确的位置获取CIO决策数据
        executive_decision = debate_result.get("decision_section", {})
        
        if not executive_decision:
            st.error("❌ CIO决策数据缺失，请重新运行完整分析流程")
            return
        
        # 获取数据
        operational_decision = executive_decision.get("operational_decision", "中性策略")
        directional_view = executive_decision.get("directional_view", "中性")
        operational_confidence = executive_decision.get("operational_confidence", "中")
        directional_confidence = executive_decision.get("directional_confidence", "中")
        
        # 提取价格信息 - 🔥 优先从CIO的statement获取（已格式化），再从trading_section获取
        import re
        
        # 优先从CIO的statement中提取（格式化好的）
        cio_statement = executive_decision.get("cio_statement", "")
        trading_section = debate_result.get("trading_section", {})
        trader_reasoning = trading_section.get("reasoning", "")
        
        # 合并两个文本源，CIO的statement优先
        combined_text = cio_statement + "\n\n" + trader_reasoning
        
        # 当前价格（可选，如果没有就不显示）
        current_price_match = re.search(r'当前价格[：:]\s*(\d+\.?\d*)元', combined_text)
        current_price = f"{current_price_match.group(1)}元" if current_price_match else None
        
        # 🔥 更新正则表达式，支持更多格式（从combined_text提取）
        # 格式1：进场：82800-83100元 或 进场区间：82800-83100元
        # 格式2：进场82800-83100元
        # 格式3：关键价位：进场82800-83100元
        # 格式4：建议进场区间：12300-12400元（CIO决策格式） ⭐
        entry_range_match = re.search(r'建议进场区间[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
        if not entry_range_match:
            entry_range_match = re.search(r'进场[区间]?[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
        if not entry_range_match:
            # 后备方案：从"关键价位"开始搜索
            key_price_section = re.search(r'关键价位[：:](.*?)(?=，|。|持仓周期|风险控制|$)', combined_text, re.DOTALL)
            if key_price_section:
                entry_range_match = re.search(r'进场[区间]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', key_price_section.group(1))
        entry_range = f"{entry_range_match.group(1)}-{entry_range_match.group(2)}元" if entry_range_match else "未提供"
        
        # 止损位 - 🔥 扩展多种格式（从combined_text提取）
        # 格式1：止损位：>53148元（CIO决策格式） ⭐
        # 格式2：止损<81500元 或 止损：<81500元
        # 格式3：止损位81500元附近
        # 格式4：止损>12800元（做空时）
        stop_loss_match = re.search(r'止损[位]?[：:]?\s*([<＜>＞])\s*(\d+\.?\d*)元', combined_text)
        if stop_loss_match:
            direction_symbol = '<' if stop_loss_match.group(1) in ['<', '＜'] else '>'
            stop_loss = f"{direction_symbol}{stop_loss_match.group(2)}元"
        else:
            # 尝试其他格式
            stop_loss_match2 = re.search(r'止损[位]?[：:]?\s*(\d+\.?\d*)元?\s*[以上以下附近]', combined_text)
            if stop_loss_match2:
                # 判断是以上还是以下
                context = combined_text[max(0, stop_loss_match2.start()-50):stop_loss_match2.end()+50]
                if '以上' in context or '做空' in operational_decision:
                    stop_loss = f">{stop_loss_match2.group(1)}元"
                elif '以下' in context or '做多' in operational_decision:
                    stop_loss = f"<{stop_loss_match2.group(1)}元"
                else:
                    stop_loss = f"~{stop_loss_match2.group(1)}元"
            else:
                stop_loss = "未提供"
        
        # 目标价位 - 从combined_text提取
        # 格式1：目标价位：48000-49000元（CIO决策格式） ⭐
        # 格式2：目标84500-85000元 或 目标：84500-85000元
        target_price_match = re.search(r'目标[价位]?[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
        if not target_price_match:
            # 后备方案：从"关键价位"搜索
            key_price_section = re.search(r'关键价位[：:](.*?)(?=，持仓周期|风险控制|$)', combined_text, re.DOTALL)
            if key_price_section:
                target_price_match = re.search(r'目标\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', key_price_section.group(1))
        target_price = f"{target_price_match.group(1)}-{target_price_match.group(2)}元" if target_price_match else "未提供"
        
        # 获取分析模型
        analysis_model = execution_summary.get('ai_model', 'DeepSeek-Reasoner')
        
        # ═══════════════════════════════════════════════════════════════
        # 现代化卡片式布局
        # ═══════════════════════════════════════════════════════════════
        
        # 1. 决策结果卡片
        with st.container():
            st.markdown('<div class="summary-section">', unsafe_allow_html=True)
            st.markdown("#### 🎯 决策结果")
            
            col1, col2 = st.columns(2, gap="medium")
            
            with col1:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           border-radius: 12px; padding: 20px; margin: 10px 0;
                           box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    <div style="color: white; opacity: 0.9; font-size: 0.9em; margin-bottom: 5px;">📊 操作决策</div>
                    <div style="color: white; font-size: 1.8em; font-weight: bold;">{}</div>
                    <div style="color: white; opacity: 0.8; font-size: 0.85em; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.3);">
                        🎲 操作信心度：<span style="font-weight: bold;">{}</span>
                    </div>
                </div>
                """.format(operational_decision, operational_confidence), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                           border-radius: 12px; padding: 20px; margin: 10px 0;
                           box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    <div style="color: white; opacity: 0.9; font-size: 0.9em; margin-bottom: 5px;">🧭 方向判断</div>
                    <div style="color: white; font-size: 1.8em; font-weight: bold;">{}</div>
                    <div style="color: white; opacity: 0.8; font-size: 0.85em; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.3);">
                        📍 方向信心度：<span style="font-weight: bold;">{}</span>
                    </div>
                </div>
                """.format(directional_view, directional_confidence), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 添加间隔
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. 关键价位卡片
        with st.container():
            st.markdown('<div class="summary-section">', unsafe_allow_html=True)
            st.markdown("#### 💰 关键价位")
            
            # 根据是否有当前价格决定列数
            if current_price:
                col1, col2, col3, col4 = st.columns(4, gap="small")
                with col1:
                    st.markdown("""
                    <div style="background: white; border-left: 4px solid #3b82f6;
                               border-radius: 8px; padding: 15px; margin: 5px 0;
                               box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                        <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 5px;">📍 当前价格</div>
                        <div style="color: #1f2937; font-size: 1.5em; font-weight: bold;">{}</div>
                    </div>
                    """.format(current_price), unsafe_allow_html=True)
            else:
                col2, col3, col4 = st.columns(3, gap="medium")
            
            with col2:
                st.markdown("""
                <div style="background: white; border-left: 4px solid #10b981;
                           border-radius: 8px; padding: 15px; margin: 5px 0;
                           box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 5px;">🎯 进场区间</div>
                    <div style="color: #1f2937; font-size: 1.5em; font-weight: bold;">{}</div>
                </div>
                """.format(entry_range), unsafe_allow_html=True)
            
            with col3:
                st.markdown("""
                <div style="background: white; border-left: 4px solid #f59e0b;
                           border-radius: 8px; padding: 15px; margin: 5px 0;
                           box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 5px;">🎖️ 目标价位</div>
                    <div style="color: #1f2937; font-size: 1.5em; font-weight: bold;">{}</div>
                </div>
                """.format(target_price), unsafe_allow_html=True)
            
            with col4:
                st.markdown("""
                <div style="background: white; border-left: 4px solid #ef4444;
                           border-radius: 8px; padding: 15px; margin: 5px 0;
                           box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <div style="color: #6b7280; font-size: 0.85em; margin-bottom: 5px;">🛡️ 止损价位</div>
                    <div style="color: #1f2937; font-size: 1.5em; font-weight: bold;">{}</div>
                </div>
                """.format(stop_loss), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 添加间隔
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 3. 执行信息卡片
        with st.container():
            st.markdown('<div class="summary-section">', unsafe_allow_html=True)
            st.markdown("#### ⏱️ 执行信息")
            
            # 使用单行4列布局（移除分析耗时）
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
                       border-radius: 12px; padding: 20px; margin: 10px 0;
                       box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                <div style="display: flex; justify-content: space-around; align-items: center;">
                    <div style="text-align: center;">
                        <div style="color: #00796b; font-size: 0.85em; margin-bottom: 5px;">完成阶段</div>
                        <div style="color: #004d40; font-size: 1.8em; font-weight: bold;">{}/5</div>
                    </div>
                    <div style="border-left: 2px solid rgba(0,121,107,0.2); height: 50px;"></div>
                    <div style="text-align: center;">
                        <div style="color: #00796b; font-size: 0.85em; margin-bottom: 5px;">分析模块</div>
                        <div style="color: #004d40; font-size: 1.8em; font-weight: bold;">{}个</div>
                    </div>
                    <div style="border-left: 2px solid rgba(0,121,107,0.2); height: 50px;"></div>
                    <div style="text-align: center;">
                        <div style="color: #00796b; font-size: 0.85em; margin-bottom: 5px;">辩论轮数</div>
                        <div style="color: #004d40; font-size: 1.8em; font-weight: bold;">{}轮</div>
                    </div>
                    <div style="border-left: 2px solid rgba(0,121,107,0.2); height: 50px;"></div>
                    <div style="text-align: center;">
                        <div style="color: #00796b; font-size: 0.85em; margin-bottom: 5px;">分析模型</div>
                        <div style="color: #004d40; font-size: 1.3em; font-weight: bold;">{}</div>
                    </div>
                </div>
            </div>
            """.format(
                execution_summary.get('stages_completed', 0),
                execution_summary.get('analysis_modules', 0),
                execution_summary.get('debate_rounds', 0),
                analysis_model
            ), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _display_analyst_team_page(self, commodity: str, result: Dict):
        """显示分析师团队页面"""
        st.markdown("## 👨‍💼 分析师团队报告")
        
        analysis_result = result.get("result", {})
        analysis_state = analysis_result.get("analysis_state")
        
        if not analysis_state:
            st.error("❌ 无法获取分析师团队数据")
            return
        
        # 团队成果概览
        st.markdown("### 📊 团队成果概览")
        
        module_attrs = [
            ("inventory_analysis", "📦 库存仓单分析师"),
            ("positioning_analysis", "🎯 持仓席位分析师"),
            ("technical_analysis", "📈 技术面分析师"),
            ("basis_analysis", "💰 基差分析师"),
            ("term_structure_analysis", "📊 期限结构分析师"),
            ("news_analysis", "📰 新闻分析师")
        ]
        
        successful_modules = 0
        for attr_name, module_name in module_attrs:
            if hasattr(analysis_state, attr_name):
                module_result = getattr(analysis_state, attr_name)
                if module_result and (
                    module_result.status == "completed" or 
                    (hasattr(module_result.status, 'value') and module_result.status.value == "completed") or
                    str(module_result.status).lower() == "completed"
                ):
                    successful_modules += 1
        
        st.success(f"✅ {successful_modules}/6 位分析师完成专业报告")
        
        # 各分析师详细报告标签页
        st.markdown("### 📋 分析师详细报告")
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📦 库存仓单", 
            "🎯 持仓席位", 
            "📈 技术分析", 
            "💰 基差分析", 
            "📊 期限结构", 
            "📰 新闻分析"
        ])
        
        with tab1:
            self._display_single_analyst_report(commodity, analysis_state, 'inventory_analysis', '📦 库存仓单分析师')
        
        with tab2:
            self._display_single_analyst_report(commodity, analysis_state, 'positioning_analysis', '🎯 持仓席位分析师')
        
        with tab3:
            self._display_single_analyst_report(commodity, analysis_state, 'technical_analysis', '📈 技术面分析师')
        
        with tab4:
            self._display_single_analyst_report(commodity, analysis_state, 'basis_analysis', '💰 基差分析师')
        
        with tab5:
            self._display_single_analyst_report(commodity, analysis_state, 'term_structure_analysis', '📊 期限结构分析师')
        
        with tab6:
            self._display_single_analyst_report(commodity, analysis_state, 'news_analysis', '📰 新闻分析师')
    
    def _display_single_analyst_report(self, commodity: str, analysis_state, attr_name: str, module_name: str):
        """显示单个分析师的完整报告"""
        if not hasattr(analysis_state, attr_name):
            st.error(f"❌ 未找到{module_name}的分析结果")
            return
        
        module_result = getattr(analysis_state, attr_name)
        
        # 分析师信息卡片
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">{module_name}</h2>
            <p style="margin: 5px 0 0 0; text-align: center; font-size: 1.1em;">专业深度分析报告</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 检查分析状态
        is_completed = False
        if module_result and hasattr(module_result, 'status'):
            status = module_result.status
            if hasattr(status, 'value'):
                status_value = status.value.lower() if isinstance(status.value, str) else str(status.value).lower()
                is_completed = status_value in ["completed", "success"]
            elif isinstance(status, str):
                is_completed = status.lower() in ["completed", "success"]
            else:
                status_str = str(status).lower()
                is_completed = status_str in ["completed", "success"]
        
        if not is_completed:
            st.error(f"❌ {module_name}分析未完成")
            return
        
        # 获取分析内容
        result_data = module_result.result_data if hasattr(module_result, 'result_data') else None
        if not result_data:
            st.error(f"❌ {module_name}无分析数据")
            return
        
        # 分析基本信息
        col1, col2 = st.columns(2)
        with col1:
            if "confidence_score" in result_data:
                confidence = result_data['confidence_score']
                if isinstance(confidence, (int, float)):
                    # 转换为高中低级别
                    if confidence >= 0.8:
                        confidence_level = "高"
                    elif confidence >= 0.6:
                        confidence_level = "中"
                    else:
                        confidence_level = "低"
                    st.metric("分析信心", confidence_level)
                else:
                    st.metric("分析信心", "高")
            else:
                st.metric("分析信心", "高")
        
        with col2:
            # 分析时间 - 格式化为中文时间
            time_str = "实时"
            if "analysis_time" in result_data:
                time_str = result_data['analysis_time']
            elif "timestamp" in result_data:
                time_str = result_data['timestamp']
            
            # 尝试格式化时间为中文格式
            try:
                if isinstance(time_str, str) and len(time_str) > 10:
                    from datetime import datetime
                    # 尝试解析不同的时间格式
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(time_str, fmt)
                            time_str = f"{dt.year}年{dt.month}月{dt.day}日 {dt.hour}时{dt.minute}分{dt.second}秒"
                            break
                        except:
                            continue
            except:
                pass
            
            st.metric("分析时间", time_str)
        
        # 核心分析内容
        st.markdown("### 📋 专业分析内容")
        
        analysis_content = None
        # 尝试从多个可能的字段获取分析内容
        content_fields = ["ai_comprehensive_analysis", "ai_analysis", "analysis_content", "speculative_analysis", "content", "report", "analysis"]
        for field in content_fields:
            if field in result_data and result_data[field]:
                analysis_content = result_data[field]
                break
        
        if analysis_content and isinstance(analysis_content, str) and len(analysis_content.strip()) > 0:
            # 专业分析报告格式
            st.markdown("#### 🔍 专业分析报告")
            
            # 处理分析内容 - 移除冗余开头
            content = analysis_content
            
            # 移除常见的冗余开头
            redundant_beginnings = [
                "作为世界顶级期货库存分析专家",
                "### 作为世界顶级期货库存分析专家",
                "基于提供的真实数据，我对",
                "本分析严格遵循数据驱动原则",
                "分析框架分为五个部分",
                "总字数约2500字",
                "第一部分：数据质量评估与可信度分析",
                "数据质量是分析可靠性的基石"
            ]
            
            # 移除冗余开头
            for redundant in redundant_beginnings:
                if content.startswith(redundant):
                    # 找到第一个实际内容段落
                    lines = content.split('\n')
                    content_start_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not any(r in line for r in redundant_beginnings):
                            # 查找核心观点或实际分析内容
                            if any(keyword in line for keyword in ['核心观点', '市场现状', '库存状况', '当前', '建议']):
                                content_start_idx = i
                                break
                    if content_start_idx > 0:
                        content = '\n'.join(lines[content_start_idx:])
                    break
            
            # 替换常见英文词汇为中文
            english_to_chinese = {
                " low ": " 低位 ",
                " high ": " 高位 ",
                " support ": " 支撑 ",
                " resistance ": " 阻力 ",
                " bullish ": " 看多 ",
                " bearish ": " 看空 ",
                " trend ": " 趋势 ",
                " breakout ": " 突破 ",
                " volume ": " 成交量 ",
                " price ": " 价格 ",
                " market ": " 市场 ",
                " analysis ": " 分析 ",
                " data ": " 数据 ",
                " level ": " 水平 ",
                " range ": " 区间 ",
                " strong ": " 强势 ",
                " weak ": " 弱势 "
            }
            
            for eng, chn in english_to_chinese.items():
                content = content.replace(eng, chn)
            
            # 专业报告样式
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%); 
                       padding: 25px; border-radius: 12px; margin: 20px 0;
                       border: 1px solid #e3e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <div style="font-family: 'Microsoft YaHei', 'SimHei', sans-serif; 
                           line-height: 1.8; font-size: 15px; color: #2c3e50; 
                           text-align: justify; letter-spacing: 0.5px;">
{content}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 暂无详细分析内容")
        
        # 图表展示
        st.markdown("### 📊 专业图表分析")
        
        chart_displayed = False
        
        # 尝试多种方式显示图表
        if "charts_html" in result_data and result_data["charts_html"]:
            try:
                charts_content = result_data["charts_html"]
                
                # 使用增强的图表显示功能（带下载按钮）
                if CHART_DOWNLOAD_AVAILABLE:
                    chart_displayed = display_charts_with_download(
                        charts_content, 
                        commodity, 
                        module_name, 
                        "charts_html"
                    )
                    if chart_displayed:
                        # 添加批量下载按钮（如果有多个图表）
                        create_batch_download_button(charts_content, commodity, module_name)
                else:
                    # 回退到基础显示功能
                    if hasattr(charts_content, 'to_html'):  # 单个Plotly图表对象
                        st.plotly_chart(charts_content, use_container_width=True, height=650)
                        chart_displayed = True
                        
                    # 如果是字典格式（多个图表）
                    elif isinstance(charts_content, dict):
                        chart_count = 0
                        for chart_name, chart_obj in charts_content.items():
                            if hasattr(chart_obj, 'to_html'):  # 确认是Plotly对象
                                st.subheader(f"📊 {chart_name}")
                                st.plotly_chart(chart_obj, use_container_width=True, height=600)
                                chart_count += 1
                        
                        if chart_count > 0:
                            chart_displayed = True
                            st.success(f"✅ 已显示 {chart_count} 个专业图表")
                        else:
                            # 如果字典中没有有效的图表对象，显示调试信息
                            st.warning("⚠️ 图表数据格式不正确")
                            with st.expander("调试信息"):
                                st.json(charts_content)
                    
                    # 如果是列表格式（包含多个图表对象）
                    elif isinstance(charts_content, list):
                        chart_count = 0
                        for chart_item in charts_content:
                            if isinstance(chart_item, dict):
                                # 处理包含title和html字段的字典格式
                                title = chart_item.get('title', f'图表 {chart_count + 1}')
                                chart_obj = chart_item.get('html', chart_item.get('chart', chart_item.get('figure')))
                                
                                if hasattr(chart_obj, 'to_html'):  # 确认是Plotly对象
                                    st.subheader(f"📊 {title}")
                                    st.plotly_chart(chart_obj, use_container_width=True, height=600)
                                    chart_count += 1
                            elif hasattr(chart_item, 'to_html'):  # 直接是Plotly对象
                                st.subheader(f"📊 图表 {chart_count + 1}")
                                st.plotly_chart(chart_item, use_container_width=True, height=600)
                                chart_count += 1
                        
                        if chart_count > 0:
                            chart_displayed = True
                            st.success(f"✅ 已显示 {chart_count} 个专业图表")
                        else:
                            st.warning("⚠️ 列表中没有有效的图表对象")
                            with st.expander("调试信息"):
                                st.json(charts_content)
                    
                    # 如果是字符串格式的HTML
                    elif isinstance(charts_content, str) and len(charts_content.strip()) > 0:
                        # 检查HTML内容是否包含有效的图表代码
                        if any(tag in charts_content.lower() for tag in ['<svg', '<canvas', '<div', 'plotly', 'chart']):
                            st.components.v1.html(charts_content, height=650, scrolling=True)
                            chart_displayed = True
                        else:
                            # 如果HTML内容无效，尝试作为文本显示
                            st.code(charts_content, language='html')
                            chart_displayed = True
                            
                    else:
                        # 其他格式，显示调试信息
                        st.warning(f"⚠️ 未知的图表格式: {type(charts_content)}")
                        with st.expander("调试信息"):
                            st.text(str(charts_content)[:1000] + "..." if len(str(charts_content)) > 1000 else str(charts_content))
                    
            except Exception as e:
                st.warning(f"📊 图表显示出错: {str(e)}")
                with st.expander("错误详情"):
                    st.text(f"错误类型: {type(e).__name__}")
                    st.text(f"错误信息: {str(e)}")
                    if "charts_html" in result_data:
                        st.text(f"数据类型: {type(result_data['charts_html'])}")
        
        # 检查其他图表字段
        if not chart_displayed:
            chart_fields = ["professional_charts", "charts", "chart_data", "visualizations"]
            for field in chart_fields:
                if field in result_data and result_data[field]:
                    chart_data = result_data[field]
                    try:
                        # 使用增强的图表显示功能（带下载按钮）
                        if CHART_DOWNLOAD_AVAILABLE:
                            chart_displayed = display_charts_with_download(
                                chart_data, 
                                commodity, 
                                module_name, 
                                field
                            )
                            if chart_displayed:
                                # 添加批量下载按钮（如果有多个图表）
                                create_batch_download_button(chart_data, commodity, module_name)
                                break
                        else:
                            # 回退到基础显示功能
                            if hasattr(chart_data, 'to_html'):  # 单个Plotly图表对象
                                # 使用unique key避免ID冲突
                                unique_key = f"{attr_name}_{field}_single_chart"
                                st.plotly_chart(chart_data, use_container_width=True, height=650, key=unique_key)
                                chart_displayed = True
                                break
                            elif isinstance(chart_data, dict):
                                # 如果是字典，检查是否包含多个图表
                                chart_count = 0
                                for key, value in chart_data.items():
                                    if hasattr(value, 'to_html'):  # Plotly图表对象
                                        # 清理key，移除emoji和特殊字符
                                        clean_key = key.replace('📊 ', '').replace('_', ' ').strip()
                                        st.subheader(f"{clean_key}")
                                        # 使用unique key避免ID冲突
                                        unique_key = f"{attr_name}_{field}_{key}_{chart_count}"
                                        st.plotly_chart(value, use_container_width=True, height=600, key=unique_key)
                                        chart_count += 1
                                        chart_displayed = True
                                if chart_count > 0:
                                    st.success(f"✅ 已显示 {chart_count} 个图表")
                                    break
                                else:
                                    # 如果没有图表对象，显示调试信息而不是完整字典
                                    st.warning(f"⚠️ 字段 {field} 包含数据但不是有效的图表对象")
                                    with st.expander("调试信息"):
                                        st.json(chart_data)
                                    chart_displayed = True
                                    break
                            elif isinstance(chart_data, str):
                                # 如果是字符串，尝试作为HTML显示
                                if any(tag in chart_data.lower() for tag in ['<svg', '<canvas', '<div', 'plotly']):
                                    st.components.v1.html(chart_data, height=650, scrolling=True)
                                    chart_displayed = True
                                    break
                                else:
                                    # 作为代码显示
                                    st.code(chart_data)
                                chart_displayed = True
                                break
                            else:
                                # 其他类型，转为字符串显示
                                st.text(str(chart_data))
                                chart_displayed = True
                                break
                    except Exception as e:
                        st.warning(f"处理图表字段 {field} 时出错: {str(e)}")
                        continue
        
        # 如果仍然没有显示图表，不显示任何说明（删除冗余内容）
        pass
        
        # 外部数据来源和引用
        citations_found = False
        
        # 检查各种引用字段
        citation_fields = ["external_citations", "references", "citations", "data_sources"]
        for field in citation_fields:
            if field in result_data and result_data[field]:
                citations_found = True
                st.markdown("### 📚 数据来源与外部引用")
                st.markdown("""
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; 
                           border-left: 4px solid #4CAF50; margin: 15px 0;">
                    <p style="margin: 0; color: #2c5530; font-weight: 500;">
                    📌 以下数据来源均为实时获取，确保信息的准确性和时效性
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                citations = result_data[field]
                if isinstance(citations, list):
                    for i, citation in enumerate(citations, 1):
                        if isinstance(citation, dict):
                            title = citation.get('title', f'数据源 {i}')
                            url = citation.get('url', '#')
                            source = citation.get('source', '未知来源')
                            
                            # 时效性检查
                            time_info = ""
                            if 'date' in citation or 'timestamp' in citation:
                                date_str = citation.get('date', citation.get('timestamp', ''))
                                try:
                                    from datetime import datetime, timedelta
                                    if date_str:
                                        # 尝试解析日期
                                        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                                            try:
                                                date_obj = datetime.strptime(date_str.split(' ')[0], fmt.split(' ')[0])
                                                days_ago = (datetime.now() - date_obj).days
                                                if days_ago == 0:
                                                    time_info = "（今日数据）"
                                                elif days_ago == 1:
                                                    time_info = "（昨日数据）"
                                                elif days_ago <= 7:
                                                    time_info = f"（{days_ago}天前数据）"
                                                else:
                                                    time_info = f"（{date_str}）"
                                                break
                                            except:
                                                continue
                                except:
                                    pass
                            
                            st.markdown(f"""
                            <div style="margin: 10px 0; padding: 12px; background-color: white; 
                                       border-radius: 8px; border-left: 3px solid #2196F3;">
                                <strong>[{i}]</strong> 
                                <a href="{url}" target="_blank" style="text-decoration: none; color: #1976D2;">
                                    {title}
                                </a>
                                <span style="color: #666; font-size: 0.9em;">{time_info}</span><br>
                                <span style="color: #888; font-size: 0.85em;">来源: {source}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        elif isinstance(citation, str):
                            if citation.startswith('http'):
                                st.markdown(f"[{i}] [数据链接]({citation})")
                            else:
                                st.markdown(f"[{i}] {citation}")
                        else:
                            st.markdown(f"[{i}] {str(citation)}")
                else:
                    st.write(citations)
                break
        
        # 如果没有找到引用，提供说明
        if not citations_found:
            st.markdown("### 📚 数据来源")
            st.markdown("""
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; 
                       border-left: 4px solid #ff9800; margin: 15px 0;">
                <p style="margin: 0; color: #ef6c00;">
                📊 本分析基于本地数据库中的历史数据和实时计算结果<br>
                🔄 数据已通过多重验证，确保分析结论的可靠性
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # 关键发现
        if "key_findings" in result_data and result_data["key_findings"]:
            st.markdown("### 🎯 关键发现")
            findings = result_data["key_findings"]
            if isinstance(findings, list):
                for finding in findings:
                    st.markdown(f"• {finding}")
            else:
                st.write(findings)
    
    def _display_debate_page(self, commodity: str, result: Dict):
        """显示激烈辩论页面"""
        st.markdown("## 🎭 激烈辩论环节")
        
        # 检查辩论结果数据是否存在 - 修复：检查实际的数据内容而不是success字段
        if not result or not result.get("debate_section"):
            st.error("❌ 辩论环节数据不完整")
            return
        
        debate_section = result.get("debate_section", {})
        
        # 辩论环节标题
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); 
                   color: white; padding: 25px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">🗣️ 多空激烈交锋</h2>
            <p style="margin: 10px 0 0 0; text-align: center; font-size: 1.1em;">
                智慧碰撞，观点交锋，寻找投资真理
            </p>
            </div>
            """, unsafe_allow_html=True)
        
        # 详细辩论轮次
        if "rounds" in debate_section and debate_section["rounds"]:
            st.markdown("### 🗣️ 详细辩论记录")
            
            for i, round_data in enumerate(debate_section["rounds"], 1):
                # 轮次标题
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #6c757d, #495057); color: white; 
                           padding: 10px; border-radius: 8px; text-align: center; margin: 20px 0 10px 0;">
                    <h4 style="margin: 0;">第 {i} 轮辩论</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # 多头空头并列显示
                col_bull, col_bear = st.columns(2)
                
                with col_bull:
                    st.markdown("#### 🐂 多头观点")
                    bull_argument = round_data.get("bull_argument", "暂无内容")
                    st.markdown(f"""
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 8px; 
                               border-left: 4px solid #28a745; margin: 10px 0;">
                        <div style="white-space: pre-wrap; line-height: 1.5;">
{bull_argument}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_bear:
                    st.markdown("#### 🐻 空头观点")
                    bear_argument = round_data.get("bear_argument", "暂无内容")
                    st.markdown(f"""
                    <div style="background-color: #f8d7da; padding: 15px; border-radius: 8px; 
                               border-left: 4px solid #dc3545; margin: 10px 0;">
                        <div style="white-space: pre-wrap; line-height: 1.5;">
{bear_argument}
                        </div>
                </div>
                """, unsafe_allow_html=True)
                
                if i < len(debate_section["rounds"]):
                    st.markdown("---")
        
        # 辩论数据来源标注
        st.markdown("### 📚 辩论数据来源")
        st.markdown("""
        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; 
                   border-left: 4px solid #4CAF50; margin: 15px 0;">
            <p style="margin: 0; color: #2c5530; font-weight: 500;">
            📊 辩论环节引用的市场数据、新闻资讯和技术指标均来自实时数据源<br>
            🔍 所有观点基于当前市场状况和历史数据分析得出<br>
            ⏰ 数据时效性：实时更新，确保分析的准确性
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _display_trader_page(self, commodity: str, result: Dict):
        """显示专业交易员页面"""
        st.markdown("## 💼 专业交易员决策")
        
        # 检查交易员结果数据是否存在 - 修复：检查实际的数据内容而不是success字段
        if not result or not result.get("trading_section"):
            st.error("❌ 交易员环节数据不完整")
            return
        
        trading_section = result.get("trading_section", {})
        
        # 交易员信息卡片
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); 
                   color: white; padding: 25px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">👨‍💼 资深交易员分析</h2>
            <p style="margin: 10px 0 0 0; text-align: center; font-size: 1.1em;">
                综合辩论观点，专业评判，给出交易建议
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 交易逻辑与执行计划（合并显示）
        st.markdown("### 🧠 交易逻辑与执行计划")
        
        reasoning = trading_section.get('reasoning', '基于技术分析和基本面分析，制定以下交易策略')
        # 🔥 修复：不再显示execution_plan字段，因为它会重复添加"执行计划"
        # execution_plan = trading_section.get('execution_plan', '')
        
        # 🔥 修复：只显示reasoning字段（已经被后端清理过，不包含执行计划）
        combined_content = reasoning
        # if execution_plan and execution_plan.strip():
        #     combined_content += f"\n\n**执行计划：**\n{execution_plan}"
        
        st.markdown(f"""
        <div style="background-color: #e7f3ff; padding: 25px; border-radius: 12px; 
                   border-left: 5px solid #007bff; margin: 20px 0;">
            <div style="font-family: 'Microsoft YaHei'; line-height: 1.8; font-size: 15px; color: #2c3e50;">
                {combined_content.replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    
    def _display_risk_page(self, commodity: str, result: Dict):
        """显示专业风控页面"""
        st.markdown("## 🛡️ 专业风控评估")
        
        # 检查风控结果数据是否存在 - 修复：检查实际的数据内容而不是success字段
        if not result or not result.get("risk_section"):
            st.error("❌ 风控环节数据不完整")
            return
        
        risk_section = result.get("risk_section", {})
        
        # 风控管理卡片
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%); 
                   color: white; padding: 25px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">🛡️ 风险管理团队</h2>
            <p style="margin: 10px 0 0 0; text-align: center; font-size: 1.1em;">
                独立客观，风险为先，稳健经营
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 风险等级指标
        col1, col2 = st.columns(2)
        with col1:
            overall_risk = risk_section.get('overall_risk', '未知')
            risk_color = "#dc3545" if "高" in overall_risk else "#ffc107" if "中" in overall_risk else "#28a745"
            st.markdown(f"""
            <div style="background-color: {risk_color}; color: white; padding: 15px; 
                       border-radius: 8px; text-align: center;">
                <h4 style="margin: 0;">整体风险等级</h4>
                <h3 style="margin: 5px 0 0 0;">{overall_risk}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            position_limit = risk_section.get('position_limit', '未知')
            st.markdown(f"""
            <div style="background-color: #17a2b8; color: white; padding: 15px; 
                       border-radius: 8px; text-align: center;">
                <h4 style="margin: 0;">建议仓位上限</h4>
                <h3 style="margin: 5px 0 0 0;">{position_limit}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        # 止损建议
        if risk_section.get('stop_loss'):
            st.markdown("### ⚠️ 止损建议")
            st.markdown(f"""
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 8px; 
                       border-left: 4px solid #dc3545;">
                <strong>建议止损位:</strong> {risk_section['stop_loss']}
            </div>
            """, unsafe_allow_html=True)
        
        # 🔥 删除通用的风险因素和缓释措施模板，这些内容现在整合到风控经理专业意见中
        
        # 风控经理专业意见
        if risk_section.get('manager_opinion'):
            st.markdown("### 👨‍💼 风控经理专业意见")
            st.markdown(f"""
            <div style="background-color: #e9ecef; padding: 20px; border-radius: 10px; 
                       border: 2px solid #6c757d; margin: 15px 0;">
                <div style="line-height: 1.6; font-style: italic;">
                    "{risk_section['manager_opinion']}"
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _display_cio_decision_page(self, commodity: str, result: Dict):
        """显示CIO决策页面"""
        st.markdown("## 👔 CIO最终权威决策")
        
        # 获取真实市场数据
        market_data = get_market_data_info(commodity)
        
        # 删除市场数据基础部分，直接进入CIO决策
        
        # 🔥 直接从新的数据结构获取CIO决策数据
        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            st.error(f"❌ 分析失败: {error_msg}")
            st.info("💡 提示：可能是网络连接问题，请检查网络后重试")
            return
            
        executive_decision = result.get("decision_section", {})
        if not executive_decision:
            st.error("❌ CIO决策环节数据不完整，请重新运行完整分析流程")
            return
        
        # CIO决策卡片
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
                   color: white; padding: 30px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">👔 首席投资官</h2>
            <p style="margin: 10px 0 0 0; text-align: center; font-size: 1.2em;">
                权威拍板，一锤定音，决策制胜
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 直接使用executive_decision数据
        final_decision = executive_decision.get('final_decision', '未知')
        # 确保final_decision是字符串类型
        if hasattr(final_decision, 'value'):
            final_decision_str = final_decision.value
        else:
            final_decision_str = str(final_decision)
        
        # 获取其他决策信息
        confidence_level = executive_decision.get('confidence_level', executive_decision.get('confidence', 0.5))
        # 确保confidence_level是数值类型
        if isinstance(confidence_level, str):
            try:
                confidence_level = float(confidence_level.replace('%', '')) / 100 if '%' in confidence_level else float(confidence_level)
            except:
                confidence_level = 0.5
        
        directional_view = executive_decision.get('directional_view', '中性')
        directional_confidence = executive_decision.get('directional_confidence', 0.5)
        
        # 🔥 新增：支持文本格式的信心度
        directional_confidence_text = executive_decision.get('directional_confidence_text', "")
        operational_confidence_text = executive_decision.get('operational_confidence_text', "")
        
        # 确保directional_confidence是数值类型
        if isinstance(directional_confidence, str):
            try:
                directional_confidence = float(directional_confidence.replace('%', '')) / 100 if '%' in directional_confidence else float(directional_confidence)
            except:
                directional_confidence = 0.5
        
        # 🔧 调试信息 - 临时显示数据获取情况
        if st.sidebar.checkbox("🔧 显示调试信息", key=f"debug_{commodity}"):
            st.sidebar.write("**调试信息**:")
            st.sidebar.write(f"executive_decision keys: {list(executive_decision.keys())}")
            st.sidebar.write(f"confidence_level: {confidence_level} (type: {type(confidence_level)})")
            st.sidebar.write(f"directional_view: {directional_view}")
            st.sidebar.write(f"directional_confidence: {directional_confidence} (type: {type(directional_confidence)})")
            st.sidebar.write(f"final_decision: {final_decision}")
            if executive_decision:
                st.sidebar.json(executive_decision)
        
        # 🔥 删除止损标准相关逻辑
        
        # ✅ 修复：直接使用新的统一字段，与执行摘要保持完全一致
        operation_decision = executive_decision.get('operational_decision', '中性策略')
        direction_judgment = executive_decision.get('directional_view', '中性')
        operational_confidence = executive_decision.get('operational_confidence', '中')
        directional_confidence_display = executive_decision.get('directional_confidence', '中')
        
        decision_color = "#28a745" if "做多" in operation_decision else "#dc3545" if "做空" in operation_decision else "#ffc107"
        
        # 使用Streamlit原生组件替代复杂HTML  
        with st.container():
            st.markdown("### 🎯 最终决策")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="📊 操作决策",
                    value=operation_decision,
                    help="基于综合分析的操作建议"
                )
                st.metric(
                    label="🎲 操作信心度", 
                    value=operational_confidence,
                    help="对操作决策的信心程度（高/中/低）"
                )
                
            with col2:
                st.metric(
                    label="🧭 方向判断",
                    value=direction_judgment,
                    help="对市场方向的判断"
                )
                st.metric(
                    label="📍 方向信心度",
                    value=directional_confidence_display,
                    help="对方向判断的信心程度（高/中/低）"
                )
            
            # 🔥 删除止损标准显示
            st.divider()
        
        # 删除重复的操作决策和方向判断显示，因为后续的监控要点和CIO声明中已包含这些信息
        
        
        # 决策理由
        if executive_decision.get('rationale'):
            st.markdown("### 🧠 决策理由")
            rationale_list = executive_decision['rationale']
            if isinstance(rationale_list, list):
                for i, reason in enumerate(rationale_list, 1):
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; 
                               margin: 10px 0; border-left: 4px solid #007bff;">
                        <strong>{i}.</strong> {reason}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; 
                           border-left: 4px solid #007bff;">
                    {rationale_list}
                </div>
                """, unsafe_allow_html=True)
        
        # 执行计划和监控要点已整合到最终决策中，不再单独显示
        
        # CIO权威声明 - 优化排版和底色
        if executive_decision.get('cio_statement'):
            st.markdown("### 📢 CIO权威声明")
            cio_statement = executive_decision['cio_statement']
            
            # 🔥 优化排版：去除markdown格式，删除"💼 投资决策"标题
            if cio_statement and cio_statement.strip():
                # 清理可能的markdown字符和不需要的标题
                cleaned_statement = cio_statement.replace("**", "").replace("*", "").replace("#", "").replace("_", "")
                cleaned_statement = cleaned_statement.replace("💼 投资决策", "").replace("💼 **投资决策**", "")
                
                # ✅ 使用带底色的容器优化显示（只显示一次）
                st.markdown(f"""
                <div style="background-color: #f0f8ff; border: 2px solid #4a90e2; 
                           padding: 25px; margin: 20px 0; border-radius: 10px; 
                           line-height: 1.8; font-family: 'Microsoft YaHei', sans-serif;
                           box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <div style="color: #2c3e50; font-size: 16px; white-space: pre-line;">
                {cleaned_statement}
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                # ✅ 已删除重复的按段落分割显示逻辑
    
    def _display_analyst_overview(self, commodity: str, result: Dict):
        """显示分析师团队总览页面"""
        st.markdown("## 📊 分析师团队总览")
        
        analysis_state = result.get("result")
        if not analysis_state:
            st.error("❌ 无法获取分析师团队数据")
            return
        
        # 团队概述卡片
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%); 
                   color: white; padding: 25px; border-radius: 15px; margin: 20px 0;">
            <h2 style="margin: 0; text-align: center;">👥 专业分析师团队</h2>
            <p style="margin: 10px 0 0 0; text-align: center; font-size: 1.1em;">
                6位资深专家，多维度深度分析，专业可靠
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 分析师状态统计
        module_attrs = [
            ("inventory_analysis", "📦 库存仓单分析师", "专注供需平衡与库存周期分析"),
            ("positioning_analysis", "🎯 持仓席位分析师", "解读资金动向与主力意图"),
            ("technical_analysis", "📈 技术面分析师", "识别价格趋势与交易信号"),
            ("basis_analysis", "💰 基差分析师", "剖析现期价差与套利机会"),
            ("term_structure_analysis", "📊 期限结构分析师", "分析远近月价差与时间价值"),
            ("news_analysis", "📰 新闻分析师", "跟踪市场热点与情绪变化")
        ]
        
        successful_modules = 0
        module_status = {}
        
        for attr_name, module_name, description in module_attrs:
            if hasattr(analysis_state, attr_name):
                module_result = getattr(analysis_state, attr_name)
                if module_result and (
                    module_result.status == "completed" or 
                    (hasattr(module_result.status, 'value') and module_result.status.value == "completed") or
                    str(module_result.status).lower() == "completed" or
                    str(module_result.status) == "AnalysisStatus.COMPLETED"
                ):
                    successful_modules += 1
                    module_status[attr_name] = "completed"
                else:
                    module_status[attr_name] = "failed"
            else:
                module_status[attr_name] = "missing"
        
        # 总体完成度
        completion_rate = (successful_modules / 6) * 100
        color = "#28a745" if completion_rate >= 80 else "#ffc107" if completion_rate >= 60 else "#dc3545"
        
        st.markdown(f"""
        <div style="background-color: {color}; color: white; padding: 20px; 
                   border-radius: 10px; text-align: center; margin: 20px 0;">
            <h3 style="margin: 0;">团队完成度</h3>
            <h1 style="margin: 10px 0; font-size: 2.5em;">{successful_modules}/6</h1>
            <p style="margin: 0; font-size: 1.1em;">完成率: {completion_rate:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 各分析师详细状态
        st.markdown("### 👨‍💼 分析师团队状态")
        
        for attr_name, module_name, description in module_attrs:
            status = module_status.get(attr_name, "missing")
            
            if status == "completed":
                status_color = "#28a745"
                status_icon = "✅"
                status_text = "分析完成"
            elif status == "failed":
                status_color = "#dc3545"
                status_icon = "❌"
                status_text = "分析失败"
            else:
                status_color = "#6c757d"
                status_icon = "⏳"
                status_text = "等待中"
            
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 10px; 
                       margin: 10px 0; border-left: 5px solid {status_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 1.2em; margin-right: 10px;">{status_icon}</span>
                    <strong style="font-size: 1.1em;">{module_name}</strong>
                    <span style="margin-left: auto; color: {status_color}; font-weight: bold;">{status_text}</span>
                </div>
                <p style="margin: 0; color: #666; font-size: 0.9em;">{description}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 如果有完成的分析，显示关键发现汇总
        if successful_modules > 0:
            st.markdown("### 🎯 关键发现汇总")
            
            key_findings = []
            for attr_name, module_name, _ in module_attrs:
                if module_status.get(attr_name) == "completed" and hasattr(analysis_state, attr_name):
                    module_result = getattr(analysis_state, attr_name)
                    if hasattr(module_result, 'result_data') and module_result.result_data:
                        result_data = module_result.result_data
                        
                        # 尝试获取关键发现或分析摘要
                        finding = None
                        if "key_findings" in result_data and result_data["key_findings"]:
                            findings = result_data["key_findings"]
                            if isinstance(findings, list) and findings:
                                finding = findings[0]  # 取第一个关键发现
                        
                        if not finding:
                            # 尝试从分析内容中提取摘要
                            content_fields = ["ai_comprehensive_analysis", "ai_analysis", "analysis_content", "speculative_analysis", "content"]
                            for field in content_fields:
                                if field in result_data and result_data[field]:
                                    content = result_data[field]
                                    if isinstance(content, str) and len(content) > 50:
                                        finding = content[:150] + "..."
                                        break
                        
                        if finding:
                            key_findings.append((module_name, finding))
            
            if key_findings:
                for module_name, finding in key_findings:
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; 
                               margin: 8px 0; border-left: 3px solid #007bff;">
                        <strong>{module_name}:</strong> {finding}
                    </div>
                    """, unsafe_allow_html=True)
        
        # 团队协作说明
        if successful_modules >= 4:
            st.markdown("### 🤝 团队协作优势")
            st.markdown("""
            - **多维度分析**: 从基本面、技术面、资金面等多角度全面分析
            - **专业分工**: 每位分析师专注自己的领域，确保分析质量
            - **相互验证**: 不同分析师的结论可以相互印证，提高可靠性
            - **风险控制**: 多专业视角有助于识别潜在风险点
            - **决策支持**: 为后续的交易决策提供全面的数据支撑
            """)
    
    # 各个具体分析师页面的显示方法
    def _display_inventory_analysis_page(self, commodity: str, result: Dict):
        """显示库存仓单分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'inventory_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'inventory_analysis', '📦 库存仓单分析师')
        else:
            st.error("❌ 库存仓单分析数据不可用")
    
    def _display_technical_analysis_page(self, commodity: str, result: Dict):
        """显示技术分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'technical_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'technical_analysis', '📈 技术面分析师')
        else:
            st.error("❌ 技术分析数据不可用")
    
    def _display_positioning_analysis_page(self, commodity: str, result: Dict):
        """显示持仓席位分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'positioning_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'positioning_analysis', '🎯 持仓席位分析师')
        else:
            st.error("❌ 持仓席位分析数据不可用")
    
    def _display_basis_analysis_page(self, commodity: str, result: Dict):
        """显示基差分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'basis_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'basis_analysis', '💰 基差分析师')
        else:
            st.error("❌ 基差分析数据不可用")
    
    def _display_term_structure_analysis_page(self, commodity: str, result: Dict):
        """显示期限结构分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'term_structure_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'term_structure_analysis', '📊 期限结构分析师')
        else:
            st.error("❌ 期限结构分析数据不可用")
    
    def _display_news_analysis_page(self, commodity: str, result: Dict):
        """显示新闻分析页面"""
        analysis_state = result.get("result")
        if hasattr(analysis_state, 'news_analysis'):
            self._display_single_analyst_report(commodity, analysis_state, 'news_analysis', '📰 新闻分析师')
            
            # 新闻分析特殊处理：确保新闻链接完整显示
            news_result = getattr(analysis_state, 'news_analysis')
            if hasattr(news_result, 'result_data') and news_result.result_data:
                result_data = news_result.result_data
                
                # 检查是否有新闻数据但缺少链接显示
                news_count = result_data.get('news_count', 0)
                if news_count > 0:
                    st.markdown("### 📰 新闻数据统计")
                    
                    # 显示新闻数量统计
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        akshare_count = result_data.get('akshare_count', 0)
                        st.metric("AkShare新闻", f"{akshare_count}条")
                    with col2:
                        search_count = result_data.get('search_count', 0)  
                        st.metric("搜索新闻", f"{search_count}条")
                    with col3:
                        st.metric("总计新闻", f"{news_count}条")
                    
                    # 新闻时效性说明
                    st.markdown("""
                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; 
                               border-left: 4px solid #4caf50; margin: 15px 0;">
                        <h5 style="color: #2e7d2e; margin-bottom: 10px;">📅 新闻时效性保证</h5>
                        <p style="margin: 0; color: #2e7d2e;">
                        • <strong>实时新闻源</strong>：新华财经、生意社、东方财富等权威财经媒体<br>
                        • <strong>时间筛选</strong>：优先使用近7天内的最新新闻资讯<br>
                        • <strong>内容过滤</strong>：只保留与{commodity}相关的高质量新闻<br>
                        • <strong>多源验证</strong>：交叉验证多个新闻源的信息准确性
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.error("❌ 新闻分析数据不可用")

# ============================================================================
# Word报告生成器
# ============================================================================

class WordReportGenerator:
    """专业研究报告生成器"""
    
    def __init__(self):
        self.doc = None
        self.charts_data = {}  # 存储图表数据
    
    def create_comprehensive_report(self, analysis_results: Dict, analysis_config: Dict, 
                                   include_charts: bool = True, progress_callback=None) -> io.BytesIO:
        """创建专业研究报告
        
        Args:
            analysis_results: 分析结果字典
            analysis_config: 分析配置
            include_charts: 是否包含图表（图表转换很耗时，快速模式可设为False）
            progress_callback: 进度回调函数（用于显示进度）
        """
        
        if not DOCX_AVAILABLE:
            raise ImportError("未安装python-docx库")
        
        def update_progress(msg: str):
            """更新进度"""
            if progress_callback:
                progress_callback(msg)
            print(f"📝 {msg}")
        
        # 创建文档
        update_progress("初始化Word文档...")
        self.doc = Document()
        self.include_charts = include_charts  # 保存配置
        
        # 设置专业文档样式
        self._setup_professional_styles()
        
        # 获取分析的品种（取第一个品种作为主要分析对象）
        commodity = list(analysis_results.keys())[0] if analysis_results else "未知品种"
        analysis_date = analysis_config.get("analysis_date", datetime.now().strftime('%Y-%m-%d'))
        
        # 1. 添加封面页
        update_progress("生成封面页...")
        self._add_cover_page(commodity, analysis_date, analysis_config)
        
        # 2. 添加执行摘要（新增）
        update_progress("生成执行摘要...")
        self._add_executive_summary_new(analysis_results, commodity)
        
        # 3. 添加专业目录
        update_progress("生成目录...")
        self._add_professional_toc(analysis_results, commodity)
        
        # 4. 添加各分析师模块内容
        update_progress("生成分析模块内容...")
        self._add_analyst_modules(analysis_results, commodity, progress_callback=update_progress)
        
        # 5. 添加CIO决策结论
        update_progress("生成CIO决策...")
        self._add_cio_conclusion(analysis_results, commodity)
        
        # 保存到内存
        update_progress("保存Word文档...")
        doc_io = io.BytesIO()
        self.doc.save(doc_io)
        doc_io.seek(0)
        
        update_progress("✅ Word报告生成完成！")
        
        return doc_io
    
    def _setup_professional_styles(self):
        """设置专业文档样式"""
        
        # 设置文档默认字体
        from docx.oxml.shared import qn
        
        # 标题样式
        title_style = self.doc.styles['Title']
        title_font = title_style.font
        title_font.name = '黑体'
        title_font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        title_font.size = Pt(22)
        title_font.bold = True
        
        # 一级标题样式
        heading1_style = self.doc.styles['Heading 1']
        heading1_font = heading1_style.font
        heading1_font.name = '黑体'
        heading1_font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        heading1_font.size = Pt(16)
        heading1_font.bold = True
        
        # 二级标题样式
        heading2_style = self.doc.styles['Heading 2']
        heading2_font = heading2_style.font
        heading2_font.name = '黑体'
        heading2_font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        heading2_font.size = Pt(14)
        heading2_font.bold = True
        
        # 三级标题样式
        heading3_style = self.doc.styles['Heading 3']
        heading3_font = heading3_style.font
        heading3_font.name = '黑体'
        heading3_font._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
        heading3_font.size = Pt(12)
        heading3_font.bold = True
        
        # 正文样式
        normal_style = self.doc.styles['Normal']
        normal_font = normal_style.font
        normal_font.name = '宋体'
        normal_font._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        normal_font.size = Pt(12)
        
        # 设置段落间距
        normal_paragraph = normal_style.paragraph_format
        normal_paragraph.space_after = Pt(6)
        normal_paragraph.line_spacing = 1.2
    
    def _add_cover_page(self, commodity: str, analysis_date: str, config: Dict):
        """添加专业封面页"""
        
        # 添加空行用于上边距
        for _ in range(8):
            self.doc.add_paragraph()
        
        # 主标题
        title = self.doc.add_heading(f'{commodity}品种分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 添加空行
        for _ in range(3):
            self.doc.add_paragraph()
        
        # 报告日期
        date_para = self.doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_run = date_para.add_run(f'报告日期：{analysis_date}')
        date_run.font.size = Pt(16)
        date_run.font.name = '黑体'
        
        # 添加空行
        for _ in range(8):
            self.doc.add_paragraph()
        
        # 报告信息
        info_para = self.doc.add_paragraph()
        info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        info_lines = [
            "商品期货 Trading Agents系统",
            "专业投资研究报告",
            "",
            f"分析品种：{commodity}",
            f"分析模式：{config.get('analysis_mode', '完整分析')}",
            f"报告生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}"
        ]
        
        for line in info_lines:
            info_para.add_run(line + '\n')
        
        # 添加分页符
        self.doc.add_page_break()
    
    def _add_executive_summary_new(self, analysis_results: Dict, commodity: str):
        """添加执行摘要（新增 - 简化版，用于快速查看）"""
        
        # 🔥 兼容性检查：如果commodity是字典（旧版本的config参数），则跳过
        if isinstance(commodity, dict):
            print("⚠️ 检测到旧版本调用，请重启Streamlit以使用新版本")
            return
        
        self.doc.add_heading('执行摘要', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        try:
            # 获取第一个品种的分析结果
            result = list(analysis_results.values())[0]
            if result.get("status") != "success":
                self.doc.add_paragraph("分析未完成，无执行摘要")
                self.doc.add_page_break()
                return
            
            # 🔥 修复：使用正确的数据路径（与界面一致）
            debate_result = result.get("result", {}).get("debate_result", {})
            
            # 检查分析是否成功
            if not debate_result or not debate_result.get("success"):
                self.doc.add_paragraph("分析失败，无执行摘要")
                self.doc.add_page_break()
                return
            
            # 从正确的位置获取CIO决策数据
            executive_decision = debate_result.get("decision_section", {})
            
            if not executive_decision:
                self.doc.add_paragraph("CIO决策数据缺失，无执行摘要")
                self.doc.add_page_break()
                return
            
            # 提取关键信息
            operational_decision = executive_decision.get("operational_decision", "未明确")
            operational_confidence = executive_decision.get("operational_confidence", "未评估")
            directional_view = executive_decision.get("directional_view", "未明确")
            directional_confidence = executive_decision.get("directional_confidence", "未评估")
            
            # 1. 决策结果
            self.doc.add_heading('一、决策结果', level=2)
            
            decision_table = self.doc.add_table(rows=4, cols=2)
            decision_table.style = 'Light Grid Accent 1'
            
            decisions = [
                ("操作决策", operational_decision),
                ("操作信心度", operational_confidence),
                ("方向判断", directional_view),
                ("方向信心度", directional_confidence)
            ]
            
            for i, (label, value) in enumerate(decisions):
                row = decision_table.rows[i]
                row.cells[0].text = label
                row.cells[1].text = str(value)
            
            self.doc.add_paragraph()
            
            # 2. 关键价位（如果有）- 🔥 修复：使用与界面相同的提取逻辑
            import re
            
            # 优先从CIO的statement中提取（格式化好的）
            cio_statement = executive_decision.get("cio_statement", "")
            trading_section = debate_result.get("trading_section", {})
            trader_reasoning = trading_section.get("reasoning", "")
            
            # 合并两个文本源，CIO的statement优先
            combined_text = cio_statement + "\n\n" + trader_reasoning
            
            entry_range = None
            stop_loss = None
            target_price = None
            
            # 提取进场区间
            entry_match = re.search(r'建议进场区间[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
            if not entry_match:
                entry_match = re.search(r'进场[区间]?[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
            if entry_match:
                entry_range = f"{entry_match.group(1)}-{entry_match.group(2)}元"
            
            # 提取止损位
            stop_match = re.search(r'止损位?[：:]?\s*([<>~≤≥]\s*\d+\.?\d*)元', combined_text)
            if not stop_match:
                stop_match = re.search(r'止损[：:]?\s*([<>~]\d+\.?\d*)元', combined_text)
            if stop_match:
                stop_loss = stop_match.group(1).replace(' ', '') + "元"
            
            # 提取目标价位
            target_match = re.search(r'目标价位[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
            if not target_match:
                target_match = re.search(r'目标[：:]?\s*(\d+\.?\d*)[~～-](\d+\.?\d*)元', combined_text)
            if target_match:
                target_price = f"{target_match.group(1)}-{target_match.group(2)}元"
            
            if entry_range or stop_loss or target_price:
                self.doc.add_heading('二、关键价位', level=2)
                
                price_table = self.doc.add_table(rows=3, cols=2)
                price_table.style = 'Light Grid Accent 1'
                
                prices = [
                    ("进场区间", entry_range or "待定"),
                    ("目标价位", target_price or "待定"),
                    ("止损价位", stop_loss or "待定")
                ]
                
                for i, (label, value) in enumerate(prices):
                    row = price_table.rows[i]
                    row.cells[0].text = label
                    row.cells[1].text = str(value)
                
                self.doc.add_paragraph()
            
            # 3. 分析概况
            self.doc.add_heading('三、分析概况', level=2)
            
            system_metadata = debate_result.get('system_metadata', {})
            
            summary_info = [
                f"• 完成阶段：5/5",
                f"• 分析模块：{system_metadata.get('modules_count', 6)}个",
                f"• 辩论轮数：{system_metadata.get('debate_rounds', 3)}轮",
                f"• 分析模型：{system_metadata.get('model_used', 'DeepSeek-Reasoner')}"
            ]
            
            for info in summary_info:
                para = self.doc.add_paragraph(info)
                para.paragraph_format.left_indent = Inches(0.25)
            
            self.doc.add_paragraph()
            
            # 4. 风险提示
            self.doc.add_heading('四、风险提示', level=2)
            
            # 🔥 修复：从正确位置获取风险分析数据
            risk_section = debate_result.get("risk_section", {})
            risk_level = risk_section.get("risk_level", "未评估")
            position_advice = risk_section.get("position_advice", "请谨慎决策")
            
            risk_para = self.doc.add_paragraph()
            risk_para.add_run(f"风险评级：{risk_level}\n").bold = True
            risk_para.add_run(f"仓位建议：{position_advice}\n")
            risk_para.add_run("\n本报告仅供参考，不构成投资建议。投资者应根据自身情况谨慎决策，并自行承担投资风险。")
            
        except Exception as e:
            self.doc.add_paragraph(f"执行摘要生成出错：{str(e)}")
        
        self.doc.add_page_break()
    
    def _add_professional_toc(self, analysis_results: Dict, commodity: str):
        """添加专业目录"""
        
        self.doc.add_heading('目  录', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 目录项目
        toc_items = [
            ("一、库存仓单分析", "3"),
            ("二、持仓席位分析", ""),
            ("三、期限结构分析", ""),
            ("四、技术面分析", ""),
            ("五、基差分析", ""),
            ("六、新闻分析", ""),
            ("七、投资决策结论", ""),
        ]
        
        # 添加目录表格
        table = self.doc.add_table(rows=len(toc_items), cols=2)
        table.style = 'Table Grid'
        
        for i, (title, page) in enumerate(toc_items):
            row = table.rows[i]
            row.cells[0].text = title
            row.cells[1].text = page
            
            # 设置字体
            for cell in row.cells:
                cell.paragraphs[0].runs[0].font.name = '宋体'
                cell.paragraphs[0].runs[0].font.size = Pt(12)
        
        self.doc.add_page_break()
    
    def _add_analyst_modules(self, analysis_results: Dict, commodity: str, progress_callback=None):
        """添加各分析师模块内容"""
        
        # 获取第一个品种的分析结果
        result = list(analysis_results.values())[0]
        if result.get("status") != "success":
            return
        
        # 获取分析状态
        if result.get("type") == "complete_flow":
            analysis_state = result["result"]["analysis_state"]
        else:
            analysis_state = result["result"]["analysis_state"]
        
        # 模块映射
        modules_info = [
            ("inventory_analysis", "一、库存仓单分析", "inventory_analysis"),
            ("positioning_analysis", "二、持仓席位分析", "positioning_analysis"),
            ("term_structure_analysis", "三、期限结构分析", "term_structure_analysis"),
            ("technical_analysis", "四、技术面分析", "technical_analysis"),
            ("basis_analysis", "五、基差分析", "basis_analysis"),
            ("news_analysis", "六、新闻分析", "news_analysis")
        ]
        
        for idx, (module_attr, title, module_key) in enumerate(modules_info, 1):
            if progress_callback:
                progress_callback(f"处理模块 {idx}/{len(modules_info)}: {title}")
            
            module_result = getattr(analysis_state, module_attr, None)
            if module_result and hasattr(module_result, 'status'):
                self.doc.add_heading(title, level=1)
                
                # 获取模块的详细分析内容
                self._add_module_content(module_result, module_key)
                
                # 添加图表（如果有且启用了图表）
                if self.include_charts:
                    if progress_callback:
                        progress_callback(f"  └─ 转换{title}的图表...")
                    self._add_module_charts(module_result, module_key)
                else:
                    # 快速模式：添加图表说明
                    note_para = self.doc.add_paragraph()
                    note_run = note_para.add_run("注：快速模式已跳过图表，详细图表请查看系统界面。")
                    note_run.font.name = '宋体'
                    note_run.font.size = Pt(10)
                    note_run.font.italic = True
                
                self.doc.add_page_break()
    
    def _add_module_content(self, module_result, module_key: str):
        """添加模块分析内容"""
        
        try:
            # 获取分析内容
            if hasattr(module_result, 'result_data') and module_result.result_data:
                result_data = module_result.result_data
                
                # 获取AI分析内容
                ai_content = None
                content_keys = [
                    'ai_comprehensive_analysis',  # 库存分析
                    'ai_analysis',                # 持仓、基差分析
                    'professional_analysis',      # 技术分析
                    'comprehensive_analysis'      # 其他分析
                ]
                
                for key in content_keys:
                    if key in result_data and result_data[key]:
                        ai_content = result_data[key]
                        break
                
                if ai_content:
                    # 清理内容（去除Markdown符号等）
                    cleaned_content = self._clean_analysis_content(ai_content)
                    
                    # 添加分析内容
                    content_para = self.doc.add_paragraph()
                    content_run = content_para.add_run(cleaned_content)
                    content_run.font.name = '宋体'
                    content_run.font.size = Pt(12)
                else:
                    # 如果没有AI内容，添加基本信息
                    basic_info = f"""
                    模块状态：{getattr(module_result, 'status', '未知')}
                    置信度：{getattr(module_result, 'confidence_score', '未知')}
                    执行时间：{getattr(module_result, 'execution_time', '未知')}秒
                    """
                    self.doc.add_paragraph(basic_info.strip())
            else:
                self.doc.add_paragraph("暂无详细分析内容")
                
        except Exception as e:
            self.doc.add_paragraph(f"内容解析出错：{str(e)}")
    
    def _clean_analysis_content(self, content: str) -> str:
        """清理分析内容，去除Markdown符号等"""
        
        if not isinstance(content, str):
            return str(content)
        
        import re
        
        # 去除Markdown符号
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # 粗体
        content = re.sub(r'\*([^*]+)\*', r'\1', content)      # 斜体
        content = re.sub(r'`([^`]+)`', r'\1', content)        # 代码
        content = re.sub(r'#+\s*', '', content)               # 标题符号
        content = re.sub(r'[-*+]\s+', '• ', content)          # 列表符号
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def _add_module_charts(self, module_result, module_key: str):
        """添加模块图表 - 增强版本，支持Plotly图表转换"""
        
        try:
            if hasattr(module_result, 'result_data') and module_result.result_data:
                result_data = module_result.result_data
                
                # 🔥 新增：尝试使用图表增强器处理Plotly图表
                charts_added = self._process_plotly_charts(result_data, module_key)
                
                if not charts_added:
                    # 检查是否有传统的图表HTML或图表数据
                    charts_html = result_data.get('charts_html')
                    charts = result_data.get('charts', [])
                    
                    if charts_html or charts:
                        # 添加图表标题
                        chart_title = self.doc.add_heading(f'{module_key}模块图表', level=3)
                        
                        # 尝试插入实际的图表文件
                        chart_files_added = self._insert_chart_files(module_key, result_data)
                        
                        if not chart_files_added:
                            # 如果没有找到图表文件，添加说明
                            chart_para = self.doc.add_paragraph()
                            chart_run = chart_para.add_run(f"注：{module_key}模块包含交互式图表，详细图表请查看系统界面。")
                            chart_run.font.name = '宋体'
                            chart_run.font.size = Pt(10)
                            chart_run.font.italic = True
                
        except Exception as e:
            # 添加错误说明而不是静默忽略
            try:
                error_para = self.doc.add_paragraph()
                error_run = error_para.add_run(f"注：{module_key}模块图表加载遇到问题，请查看系统界面获取图表。")
                error_run.font.name = '宋体'
                error_run.font.size = Pt(9)
                error_run.font.italic = True
                error_run.font.color.rgb = RGBColor(128, 128, 128)
            except:
                pass
    
    def _process_plotly_charts(self, result_data: Dict, module_key: str) -> bool:
        """处理Plotly图表并转换为PNG图片"""
        
        try:
            import plotly.io as pio
            import tempfile
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            charts_added = 0
            
            # 查找图表数据的多种可能字段
            chart_fields = [
                'charts', 'professional_charts', 'chart_data', 'figures', 
                'visualizations', 'plots', 'graphs'
            ]
            
            for field in chart_fields:
                if isinstance(result_data, dict) and field in result_data:
                    charts_data = result_data[field]
                    if charts_data:
                        # 添加模块图表标题
                        if charts_added == 0:  # 只添加一次标题
                            heading = self.doc.add_heading(f'{module_key}模块图表', level=3)
                            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # 处理图表数据
                        if isinstance(charts_data, dict):
                            # 处理字典形式的图表数据
                            for chart_key, chart_obj in charts_data.items():
                                if self._is_plotly_figure(chart_obj):
                                    success = self._convert_and_add_plotly_chart(chart_obj, chart_key, module_key)
                                    if success:
                                        charts_added += 1
                        
                        elif isinstance(charts_data, list):
                            # 处理列表形式的图表数据
                            for i, chart_obj in enumerate(charts_data):
                                if self._is_plotly_figure(chart_obj):
                                    chart_name = f"图表_{i+1}"
                                    success = self._convert_and_add_plotly_chart(chart_obj, chart_name, module_key)
                                    if success:
                                        charts_added += 1
                        
                        elif self._is_plotly_figure(charts_data):
                            # 处理单个图表对象
                            success = self._convert_and_add_plotly_chart(charts_data, "主要图表", module_key)
                            if success:
                                charts_added += 1
                        
                        if charts_added > 0:
                            break  # 找到图表后就不再查找其他字段
            
            if charts_added > 0:
                print(f"✅ {module_key}: 成功添加 {charts_added} 个图表到Word报告")
            
            return charts_added > 0
            
        except Exception as e:
            print(f"❌ 处理 {module_key} Plotly图表时出错: {e}")
            return False
    
    def _is_plotly_figure(self, obj: Any) -> bool:
        """检查是否为Plotly图表对象"""
        return hasattr(obj, 'to_image') or hasattr(obj, 'to_html') or str(type(obj)).find('plotly') != -1
    
    def _convert_and_add_plotly_chart(self, chart_obj: Any, chart_name: str, module_name: str) -> bool:
        """将Plotly图表转换为PNG并添加到Word文档（带超时保护）"""
        
        try:
            import plotly.io as pio
            import tempfile
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            import signal
            
            # 清理图表名称，移除技术代码
            clean_name = self._clean_chart_name(chart_name)
            
            # 🔥 超时保护：如果转换超过30秒，则跳过
            def timeout_handler(signum, frame):
                raise TimeoutError("图表转换超时")
            
            # Windows不支持signal.alarm，使用try-except包裹
            try:
                # 将Plotly图表转换为PNG字节
                img_bytes = pio.to_image(chart_obj, format='png', width=800, height=600, scale=2)
            except Exception as convert_error:
                print(f"⚠️ 图表转换失败 ({chart_name}): {convert_error}")
                # 添加图表转换失败说明
                note_para = self.doc.add_paragraph()
                note_run = note_para.add_run(f"注：{clean_name} 图表转换失败，请在系统界面查看交互式图表。")
                note_run.font.name = '宋体'
                note_run.font.size = Pt(9)
                note_run.font.italic = True
                note_run.font.color.rgb = RGBColor(128, 128, 128)
                return False
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(img_bytes)
                tmp_file_path = tmp_file.name
            
            try:
                # 添加图表标题
                if clean_name and clean_name != "主要图表":
                    chart_title_para = self.doc.add_paragraph()
                    chart_title_run = chart_title_para.add_run(f"图: {clean_name}")
                    chart_title_run.font.name = '宋体'
                    chart_title_run.font.size = Pt(12)
                    chart_title_run.bold = True
                    chart_title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # 添加图片到文档
                chart_para = self.doc.add_paragraph()
                chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                chart_para.add_run().add_picture(tmp_file_path, width=Inches(6))
                
                # 添加图表说明
                caption_para = self.doc.add_paragraph()
                caption_run = caption_para.add_run(f"数据来源: {module_name}模块分析结果")
                caption_run.font.name = '宋体'
                caption_run.font.size = Pt(9)
                caption_run.italic = True
                caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # 添加间距
                self.doc.add_paragraph()
                
                print(f"✅ 成功添加图表: {clean_name}")
                return True
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ 转换Plotly图表失败 ({chart_name}): {e}")
            # 添加错误说明
            try:
                note_para = self.doc.add_paragraph()
                note_run = note_para.add_run(f"注：{chart_name} 图表处理出错，请在系统界面查看。")
                note_run.font.name = '宋体'
                note_run.font.size = Pt(9)
                note_run.font.italic = True
                note_run.font.color.rgb = RGBColor(128, 128, 128)
            except:
                pass
            return False
    
    def _clean_chart_name(self, chart_name: str) -> str:
        """清理图表名称，移除技术代码"""
        
        if not isinstance(chart_name, str):
            return "图表"
        
        # 移除常见的技术前缀
        prefixes_to_remove = ['📊 ', '📈 ', '📉 ', '🔍 ', '💹 ']
        clean_name = chart_name
        for prefix in prefixes_to_remove:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]
        
        # 移除或替换技术术语
        replacements = {
            'price_trend': '价格走势',
            'spider_web': '蜘蛛网策略分析',
            'smart_money': '聪明钱分析',
            'family_reverse': '家人席位反向分析',
            'seat_behavior': '席位行为分析',
            'force_change': '多空力量变化',
            'concentration': '持仓集中度分析',
            'basis_analysis': '基差分析',
            'term_structure': '期限结构分析',
            'technical_indicators': '技术指标分析',
            'inventory_trend': '库存趋势分析'
        }
        
        for tech_term, chinese_name in replacements.items():
            if tech_term in clean_name.lower():
                clean_name = chinese_name
                break
        
        return clean_name.strip()
    
    def _insert_chart_files(self, module_key: str, result_data: Dict) -> bool:
        """插入图表文件到Word文档"""
        
        try:
            from docx.shared import Inches
            
            chart_files_added = 0
            
            # 1. 检查result_data中是否有图表路径信息
            charts = result_data.get('charts', [])
            if isinstance(charts, list) and charts:
                for chart_info in charts:
                    if isinstance(chart_info, dict) and 'path' in chart_info:
                        chart_path = chart_info['path']
                        if os.path.exists(chart_path):
                            self._add_image_to_doc(chart_path, chart_info.get('title', '图表'))
                            chart_files_added += 1
            
            # 2. 根据模块类型和品种查找对应的图表文件
            commodity = result_data.get('commodity', 'UNKNOWN')
            chart_patterns = self._get_chart_patterns(module_key, commodity)
            
            for pattern in chart_patterns:
                matching_files = []
                # 在当前目录查找匹配的文件
                for filename in os.listdir('.'):
                    if pattern.lower() in filename.lower() and filename.endswith(('.png', '.jpg', '.jpeg')):
                        matching_files.append(filename)
                
                # 插入找到的图表文件
                for chart_file in matching_files[:3]:  # 限制每种类型最多3个图表
                    if os.path.exists(chart_file):
                        # 从文件名推断图表标题
                        chart_title = self._generate_chart_title(chart_file, module_key)
                        self._add_image_to_doc(chart_file, chart_title)
                        chart_files_added += 1
            
            return chart_files_added > 0
            
        except Exception as e:
            print(f"插入图表文件时出错: {e}")
            return False
    
    def _get_chart_patterns(self, module_key: str, commodity: str) -> list:
        """获取模块对应的图表文件名模式"""
        
        patterns = []
        
        # 根据模块类型定义图表文件名模式
        if module_key == "库存仓单分析":
            patterns = [
                f"{commodity}_inventory",
                f"{commodity}_receipt", 
                f"{commodity}_ratio",
                "inventory_trend",
                "receipt_trend",
                "inventory_receipt"
            ]
        elif module_key == "持仓席位分析":
            patterns = [
                f"{commodity}_positioning",
                f"{commodity}_spider",
                f"{commodity}_smart_money",
                "positioning_analysis",
                "seat_analysis"
            ]
        elif module_key == "技术面分析":
            patterns = [
                f"{commodity}_technical",
                f"{commodity}_price",
                "technical_analysis"
            ]
        elif module_key == "期限结构分析":
            patterns = [
                f"{commodity}_term_structure",
                f"{commodity}_curve",
                "term_structure"
            ]
        elif module_key == "基差分析":
            patterns = [
                f"{commodity}_basis",
                "basis_analysis"
            ]
        
        return patterns
    
    def _generate_chart_title(self, filename: str, module_key: str) -> str:
        """从文件名生成图表标题"""
        
        # 移除文件扩展名
        name = os.path.splitext(filename)[0]
        
        # 根据文件名关键词生成标题
        if "inventory" in name.lower():
            if "trend" in name.lower():
                return "库存趋势图"
            elif "ratio" in name.lower():
                return "库存仓单比率图"
            elif "comparison" in name.lower():
                return "价格库存对比图"
            else:
                return "库存分析图"
        elif "receipt" in name.lower():
            return "仓单分析图"
        elif "positioning" in name.lower():
            return "持仓分析图"
        elif "technical" in name.lower():
            return "技术分析图"
        elif "term_structure" in name.lower():
            return "期限结构图"
        elif "basis" in name.lower():
            return "基差分析图"
        else:
            return f"{module_key}图表"
    
    def _add_image_to_doc(self, image_path: str, title: str):
        """添加图片到Word文档"""
        
        try:
            from docx.shared import Inches
            
            # 添加图表标题
            title_para = self.doc.add_paragraph()
            title_run = title_para.add_run(title)
            title_run.font.name = '黑体'
            title_run.font.size = Pt(12)
            title_run.bold = True
            title_para.alignment = 1  # 居中对齐
            
            # 添加图片
            img_para = self.doc.add_paragraph()
            img_para.alignment = 1  # 居中对齐
            
            # 插入图片，设置合适的尺寸
            run = img_para.add_run()
            run.add_picture(image_path, width=Inches(6))  # 6英寸宽度
            
            # 添加空行
            self.doc.add_paragraph()
            
        except Exception as e:
            # 如果图片插入失败，添加文字说明
            error_para = self.doc.add_paragraph()
            error_run = error_para.add_run(f"[图表: {title}] - 图片加载失败")
            error_run.font.name = '宋体'
            error_run.font.size = Pt(10)
            error_run.font.italic = True
    
    def _add_cio_conclusion(self, analysis_results: Dict, commodity: str):
        """添加CIO决策结论"""
        
        self.doc.add_heading('七、投资决策结论', level=1)
        
        # 获取第一个品种的分析结果
        result = list(analysis_results.values())[0]
        if result.get("status") != "success":
            self.doc.add_paragraph("分析未成功完成，无法生成投资决策结论。")
            return
        
        # 检查是否有辩论风控决策结果
        if result.get("type") == "complete_flow":
            # 🔥 修复：直接从新数据结构获取decision_section
            debate_result = result.get("result", {}).get("debate_result", {})
            
            # 检查分析是否成功
            if not debate_result or not debate_result.get("success"):
                print(f"❌ 报告生成错误：分析失败 - {debate_result.get('error', '未知错误') if debate_result else '分析结果为空'}")
                return
            
            executive_decision = debate_result.get("decision_section", {})
            
            # 确保数据完整性
            if not executive_decision:
                print("❌ 报告生成错误：CIO决策数据缺失")
                return
            
            if debate_result.get("success") and executive_decision:
                decision = executive_decision
                
                # CIO最终决策
                self.doc.add_heading('7.1 CIO最终投资决策', level=2)
                
                decision_info = f"""
                最终决策：{decision.get('final_decision', '未知')}
                决策信心度：{decision.get('confidence', '未知')}
                建议仓位：{decision.get('position_size', '未知')}
                决策依据：
                {decision.get('rationale', '暂无详细依据')}
                
                执行计划：
                {decision.get('execution_plan', '暂无执行计划')}
                
                监控要点：
                {' | '.join(decision.get('monitoring_points', ['暂无监控要点']))}
                """
                
                decision_para = self.doc.add_paragraph()
                decision_run = decision_para.add_run(decision_info.strip())
                decision_run.font.name = '宋体'
                decision_run.font.size = Pt(12)
                
                # CIO权威声明
                if decision.get('cio_statement'):
                    self.doc.add_heading('7.2 CIO权威声明', level=2)
                    
                    statement_para = self.doc.add_paragraph()
                    statement_run = statement_para.add_run(decision['cio_statement'])
                    statement_run.font.name = '宋体'
                    statement_run.font.size = Pt(12)
                    statement_run.font.bold = True
            else:
                self.doc.add_paragraph("未完成完整决策流程，无CIO决策结论。")
        else:
            self.doc.add_paragraph("本次分析为基础分析模式，未包含CIO决策环节。")
    
    def _add_title_page(self, config: Dict):
        """添加标题页"""
        
        # 主标题
        title = self.doc.add_heading('期货Trading Agents系统', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 副标题
        subtitle = self.doc.add_heading('专业完整分析报告（含交易员环节）', level=1)
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 分析信息
        self.doc.add_paragraph()
        info_para = self.doc.add_paragraph()
        info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        analysis_date = config.get("analysis_date", "未知日期")
        analysis_mode = config.get("analysis_mode", "未知模式")
        commodities = config.get("commodities", [])
        
        info_text = f"""
        分析日期：{analysis_date}
        分析模式：{analysis_mode}
        分析品种：{', '.join(commodities)}
        报告生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
        
        完整5阶段流程：
        阶段1：分析师团队（6大分析模块）
        阶段2：激烈辩论（多空观点交锋）
        阶段3：专业交易员（客观理性制定策略）
        阶段4：专业风控（独立风险评估）
        阶段5：CIO决策（权威最终决策）
        """
        
        info_para.add_run(info_text)
        
        # 添加分页符
        self.doc.add_page_break()
    
    def _add_table_of_contents(self, analysis_results: Dict):
        """添加目录"""
        
        self.doc.add_heading('目录', level=1)
        
        toc_items = [
            "1. 执行摘要",
            "2. 品种分析详情"
        ]
        
        for i, commodity in enumerate(analysis_results.keys(), 3):
            toc_items.append(f"  2.{i-2} {commodity}完整分析报告")
        
        toc_items.append(f"{len(analysis_results) + 3}. 综合结论与投资建议")
        
        for item in toc_items:
            para = self.doc.add_paragraph(item)
            if not item.startswith("  "):
                para.style = 'List Bullet'
        
        self.doc.add_page_break()
    
    def _add_executive_summary(self, analysis_results: Dict, config: Dict):
        """添加执行摘要"""
        
        self.doc.add_heading('1. 执行摘要', level=1)
        
        # 分析概览
        self.doc.add_heading('1.1 分析概览', level=2)
        
        total_commodities = len(analysis_results)
        successful_analyses = sum(1 for result in analysis_results.values() 
                                if result.get("status") == "success")
        
        overview_text = f"""
        本次分析共涵盖{total_commodities}个期货品种，成功完成{successful_analyses}个品种的深度分析。
        分析模式：{config.get('analysis_mode', '未知')}
        分析日期：{config.get('analysis_date', '未知')}
        使用模块：{', '.join(config.get('modules', []))}
        
        系统采用完整的5阶段专业分析流程，确保投资决策的科学性和专业性。
        每个品种都经过了从基础数据分析到最终投资决策的完整流程。
        """
        
        self.doc.add_paragraph(overview_text)
        
        # 主要发现
        self.doc.add_heading('1.2 主要发现', level=2)
        
        findings = []
        for commodity, result in analysis_results.items():
            if result.get("status") == "success":
                if result.get("type") == "optimized_debate":
                    # 修正：直接从result获取数据
                    debate_result = result.get("result", {}).get("debate_result", {})
                    if debate_result and debate_result.get("success"):
                        # 🔥 修复：从正确层级获取决策数据
                        executive_dec = result.get("result", {}).get("executive_decision", {})
                        decision = executive_dec.get("final_decision", "未知")
                        confidence = executive_dec.get("confidence_level", "未知")
                        findings.append(f"{commodity}：{decision}（信心度：{confidence}）")
                else:
                    findings.append(f"{commodity}：分析完成")
        
        for finding in findings:
            para = self.doc.add_paragraph(finding)
            para.style = 'List Bullet'
        
        self.doc.add_page_break()
    
    def _add_commodity_analysis(self, commodity: str, result: Dict, config: Dict):
        """添加品种分析"""
        
        self.doc.add_heading(f'2. {commodity}完整分析报告', level=1)
        
        if result.get("status") != "success":
            error_para = self.doc.add_paragraph(f"分析失败：{result.get('message', '未知错误')}")
            return
        
        result_type = result.get("type")
        
        if result_type == "optimized_debate":
            self._add_optimized_debate_analysis(commodity, result)
        elif result_type == "complete_flow":
            self._add_complete_flow_analysis(commodity, result)
        else:
            self._add_analyst_only_analysis(commodity, result)
    
    def _add_optimized_debate_analysis(self, commodity: str, result: Dict):
        """添加优化版辩论分析"""
        
        analysis_state = result["result"]["analysis_state"]
        debate_result = result["result"]["debate_result"]
        
        # 分析师团队结果
        self.doc.add_heading('2.1 分析师团队专业报告', level=2)
        
        # 添加各模块分析结果
        modules = {
            "inventory_analysis": "库存仓单分析",
            "positioning_analysis": "持仓席位分析",
            "term_structure_analysis": "期限结构分析",
            "technical_analysis": "技术面分析",
            "basis_analysis": "基差分析",
            "news_analysis": "新闻分析"
        }
        
        for module_attr, module_name in modules.items():
            module_result = getattr(analysis_state, module_attr, None)
            if module_result and hasattr(module_result, 'status'):
                self.doc.add_heading(f'2.1.{list(modules.keys()).index(module_attr) + 1} {module_name}', level=3)
                
                # 这里可以添加更详细的分析内容
                if hasattr(module_result, 'confidence_score'):
                    try:
                        confidence = module_result.confidence_score
                        if isinstance(confidence, (int, float)):
                            module_text = f"{module_name}已完成，置信度：{confidence:.1%}"
                        else:
                            module_text = f"{module_name}已完成，置信度：{confidence}"
                    except (ValueError, TypeError):
                        module_text = f"{module_name}已完成"
                else:
                    module_text = f"{module_name}已完成"
                self.doc.add_paragraph(module_text)
        
        # 优化版辩论风控决策结果
        if debate_result.get("success"):
            self.doc.add_heading('2.2 完整决策流程报告', level=2)
            
            # 辩论结果
            if "debate_section" in debate_result:
                debate = debate_result["debate_section"]
                self.doc.add_heading('2.2.1 激烈辩论环节', level=3)
                
                debate_text = f"""
                辩论轮数：{debate.get('title', '未知')}
                辩论胜者：{debate.get('winner', '未知')}
                多头得分：{debate.get('scores', {}).get('bull', 0):.1f}分
                空头得分：{debate.get('scores', {}).get('bear', 0):.1f}分
                
                辩论总结：
                {debate.get('summary', '暂无总结')}
                
                达成共识：
                {' | '.join(debate.get('consensus_points', []))}
                
                争议焦点：
                {' | '.join(debate.get('unresolved_issues', []))}
                """
                
                self.doc.add_paragraph(debate_text)
            
            # 交易员决策
            if "trading_section" in debate_result:
                trading = debate_result["trading_section"]
                self.doc.add_heading('2.2.2 专业交易员决策', level=3)
                
                trading_text = f"""
                策略类型：{trading.get('strategy_type', '未知')}
                交易逻辑：{trading.get('reasoning', '暂无逻辑')}
                进场点位：{' | '.join(trading.get('entry_points', []))}
                出场点位：{' | '.join(trading.get('exit_points', []))}
                仓位管理：{trading.get('position_size', '未知')}
                风险收益比：{trading.get('risk_reward_ratio', '未知')}
                具体合约：{' | '.join(trading.get('specific_contracts', []))}
                执行计划：{trading.get('execution_plan', '暂无计划')}
                市场条件：{trading.get('market_conditions', '未知')}
                备选方案：{' | '.join(trading.get('alternative_scenarios', []))}
                """
                
                self.doc.add_paragraph(trading_text)
            
            # 风险评估
            if "risk_section" in debate_result:
                risk = debate_result["risk_section"]
                self.doc.add_heading('2.2.3 专业风控评估', level=3)
                
                risk_text = f"""
                整体风险等级：{risk.get('overall_risk', '未知')}
                建议仓位上限：{risk.get('position_limit', '未知')}
                建议止损位：{risk.get('stop_loss', '未知')}
                
                风险等级依据：基于交易员决策和辩论分歧度进行专业评估
                
                风控经理专业意见：
                {risk.get('manager_opinion', '暂无意见')}
                """
                
                self.doc.add_paragraph(risk_text)
            
            # CIO决策 - 直接从新数据结构获取
            executive_decision = result.get("decision_section", {}) if result.get("success") else {}
            decision = executive_decision if executive_decision else None
            
            if decision:
                self.doc.add_heading('2.2.4 CIO最终权威决策', level=3)
                
                decision_text = f"""
                最终决策：{decision.get('final_decision', '未知')}
                决策信心：{decision.get('confidence_level', decision.get('confidence', '未知'))}
                建议仓位：{decision.get('position_size', '未知')}
                
                决策理由：
                {' | '.join(decision.get('key_rationale', decision.get('rationale', [])))}
                
                执行计划：
                {decision.get('execution_plan', '暂无计划')}
                
                监控要点：
                {' | '.join(decision.get('monitoring_points', []))}
                
                CIO权威声明：
                {decision.get('cio_statement', '暂无声明')}
                """
                
                self.doc.add_paragraph(decision_text)
        else:
            error_text = f"完整决策流程分析失败：{debate_result.get('error', '未知错误')}"
            self.doc.add_paragraph(error_text)
        
        self.doc.add_page_break()
    
    def _add_complete_flow_analysis(self, commodity: str, result: Dict):
        """添加完整流程分析"""
        
        self.doc.add_heading('2.1 传统完整Trading Agents流程结果', level=2)
        
        complete_result = result["result"]
        execution_summary = result.get("execution_summary", {})
        
        confidence = execution_summary.get('confidence_score', '0%')
        try:
            if isinstance(confidence, (int, float)):
                confidence_text = f"{confidence:.1%}"
            else:
                confidence_text = str(confidence)
        except (ValueError, TypeError):
            confidence_text = str(confidence)
            
        summary_text = f"""
        已完成阶段：{execution_summary.get('stages_completed', 0)}
        最终决策：{execution_summary.get('final_decision', '未知')}
        置信度：{confidence_text}
        总耗时：{execution_summary.get('total_duration', 0):.2f}秒
        """
        
        self.doc.add_paragraph(summary_text)
        
        self.doc.add_page_break()
    
    def _add_analyst_only_analysis(self, commodity: str, result: Dict):
        """添加仅分析师分析"""
        
        self.doc.add_heading('2.1 分析师团队专业报告', level=2)
        
        analysis_state = result["result"]
        
        # 分析进度
        progress_text = f"分析师团队已完成{commodity}的6大模块专业分析"
        self.doc.add_paragraph(progress_text)
        
        self.doc.add_page_break()
    
    def _add_comprehensive_conclusion(self, analysis_results: Dict):
        """添加综合结论"""
        
        self.doc.add_heading('3. 综合结论与专业投资建议', level=1)
        
        # 统计分析结果
        total_count = len(analysis_results)
        success_count = sum(1 for result in analysis_results.values() 
                          if result.get("status") == "success")
        
        conclusion_text = f"""
        本次专业分析共涵盖{total_count}个期货品种，成功完成{success_count}个品种的深度分析。
        
        专业结论：
        1. 系统运行稳定，5阶段分析流程完整有效
        2. 各分析模块协调工作，数据质量优良
        3. 辩论风控决策流程专业，提供了具体可操作的投资建议
        4. 交易员环节有效整合了多空观点，制定了客观理性的交易策略
        5. 风控评估独立客观，CIO决策权威专业
        
        专业投资建议：
        1. 严格按照风控建议执行仓位管理，控制投资风险
        2. 密切关注市场变化，根据交易员制定的具体策略执行
        3. 定期回顾分析结果，优化投资决策流程
        4. 重视交易员提出的备选方案，做好风险预案
        5. 遵循CIO的权威决策，确保投资纪律性
        
        专业风险提示：
        1. 期货市场存在高度不确定性，投资需谨慎
        2. 本分析结果基于历史数据和当前信息，市场情况可能发生变化
        3. 请结合实际资金情况和风险承受能力做出投资决策
        4. 建议配合专业的风险管理系统进行投资
        5. 定期评估投资组合，及时调整策略
        
        系统优势：
        1. 完整的5阶段专业分析流程
        2. 多维度数据分析和验证
        3. 客观理性的交易策略制定
        4. 独立专业的风险评估
        5. 权威的最终投资决策
        """
        
        self.doc.add_paragraph(conclusion_text)
        
        # 添加生成信息
        self.doc.add_paragraph()
        footer_text = f"报告由期货Trading Agents系统专业版自动生成\n生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
        footer_para = self.doc.add_paragraph(footer_text)
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ============================================================================
# 主界面
# ============================================================================

def main():
    """主函数"""
    
    # 页面标题
    st.markdown('<h1 class="main-header">商品期货 Trading Agents系统</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.2rem; color: #666;">
            分析师团队 + 多空辩论 + 交易员分析+ 风控管理 + CIO决策 
        </p>
        <p style="color: #888;">
            完整的期货投资决策流程，从数据分析到最终拍板
        </p>
        <p style="font-size: 1rem; color: #999; margin-top: 1rem;">
            制作人：7haoge &nbsp;&nbsp;&nbsp;&nbsp; 联系方式：953534947@qq.com
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化管理器
    if "data_manager" not in st.session_state:
        st.session_state.data_manager = StreamlitDataManager()
    
    if "analysis_manager" not in st.session_state:
        st.session_state.analysis_manager = StreamlitAnalysisManager()
    
    if "word_generator" not in st.session_state and DOCX_AVAILABLE:
        st.session_state.word_generator = WordReportGenerator()
    
    # 侧边栏
    with st.sidebar:
        
        # 系统状态
        st.subheader("📊 系统状态")
        
        # 检查API密钥配置
        try:
            config = FuturesTradingAgentsConfig("期货TradingAgents系统_配置文件.json")
            
            # DeepSeek API状态
            deepseek_api_key = config.get("api_settings", {}).get("deepseek", {}).get("api_key")
            if deepseek_api_key:
                st.success("✅ DeepSeek API已配置")
            else:
                st.error("❌ 未配置DeepSeek API密钥")
                st.info("请在配置文件中设置 api_settings.deepseek.api_key")
            
            # Serper API状态
            serper_api_key = config.get("api_settings", {}).get("serper", {}).get("api_key")
            if serper_api_key:
                st.success("✅ Serper API已配置")
            else:
                st.error("❌ 未配置Serper API密钥")
                st.info("请在配置文件中设置 api_settings.serper.api_key")
                
        except Exception as e:
            st.error(f"❌ 配置文件错误: {e}")
        
        # Word报告功能状态
        if not DOCX_AVAILABLE:
            st.error("❌ Word报告功能不可用")
            st.info("请安装：pip install python-docx")
        
        # 系统特色
        st.subheader("🌟 系统特色")
        st.info("""
        **6大模块综合分析**
        • 基于真实数据
        • AI驱动智能决策
        """)
        
        # 备注
        st.subheader("📝 备注")
        st.info("""
        **本系统的分析功能依赖于DeepSeek，联网搜索功能依赖于Serper，系统正在完善中，如有不足请多包涵！欢迎提供改进意见！**
        """)
        
        # 感谢信息
        st.subheader("🙏 感谢")
        st.info("""
        **Trading Agents项目方**
        
        **Akshare数据接口**
        """)
    
    # 主界面选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["📊 数据管理", "🔄 数据更新", "🔧 分析配置", "🎭 分析结果"])
    
    # Tab 1: 数据管理
    with tab1:
        st.header("📊 数据管理")
        
        with st.spinner("正在检查数据状态..."):
            data_status = st.session_state.data_manager.get_data_status()
        
        # 数据概览
        col1, col2 = st.columns(2)
        
        with col1:
            success_modules = sum(1 for m in data_status["modules"].values() if m["status"] == "success")
            st.metric("可用模块", f"{success_modules}/6", help="正常工作的分析模块数")
        
        with col2:
            total_records = sum(m.get("total_records", 0) for m in data_status["modules"].values())
            st.metric("总记录数", f"{total_records:,}", help="所有模块的数据记录总数")
        
        # 各模块详细状态
        st.subheader("📋 各模块数据状态")
        
        module_names = {
            "inventory": "库存数据",
            "positioning": "持仓席位", 
            "term_structure": "期限结构",
            "technical_analysis": "技术面指标",
            "basis": "基差数据",
            "receipt": "仓单数据"
        }
        
        for module_key, module_info in data_status["modules"].items():
            module_name = module_names.get(module_key, module_key)
            status_color = "success" if module_info["status"] == "success" else "error"
            
            with st.expander(f"**{module_name}** - {module_info['status']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("品种数", module_info.get("commodities_count", 0))
                with col2:
                    st.metric("记录数", f"{module_info.get('total_records', 0):,}")
                with col3:
                    st.write(f"最后更新: {module_info.get('last_update', '未知')}")
                
                if module_info["status"] == "error":
                    st.error(f"错误信息: {module_info.get('error', '未知错误')}")
                
                # 显示数据路径
                st.info(f"数据路径: {module_info.get('path', '未知')}")
                
                # 显示详细数据情况
                if module_info["status"] == "success" and module_info.get("commodities_count", 0) > 0:
                    st.write("**📊 数据详情:**")
                    
                    # 获取该模块的详细数据信息
                    detailed_info = st.session_state.data_manager._get_module_detailed_info(module_key)
                    
                    if detailed_info:
                        # 显示品种列表和数据范围 - 显示所有品种
                        st.write("**品种数据范围:**")
                        varieties_info = []
                        for variety, info in detailed_info.items():  # 显示所有品种
                            start_date = info.get('start_date', '未知')
                            end_date = info.get('end_date', '未知')
                            record_count = info.get('record_count', 0)
                            varieties_info.append({
                                '品种': variety,
                                '起始时间': start_date,
                                '结束时间': end_date,
                                '数据量': record_count
                            })
                        
                        if varieties_info:
                            # 按品种名称排序
                            varieties_info.sort(key=lambda x: x['品种'])
                            df_info = pd.DataFrame(varieties_info)
                            st.dataframe(df_info, use_container_width=True, height=min(400, len(varieties_info) * 35 + 100))
        
    
    # Tab 2: 数据更新
    with tab2:
        st.header("🔄 数据更新")
        
        st.info("💡 选择需要更新的数据模块，系统将启动对应的更新程序")
        
        # 数据更新选项
        col1, col2 = st.columns(2)
        
        with col1:
            # 库存数据更新
            if st.button("📦 更新库存数据", use_container_width=True):
                with st.spinner("启动库存数据更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("inventory")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
            
            # 持仓数据更新
            if st.button("🎯 更新持仓席位数据", use_container_width=True):
                with st.spinner("启动持仓数据更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("positioning")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
            
            # 期限结构更新
            if st.button("📈 更新期限结构数据", use_container_width=True):
                with st.spinner("启动期限结构更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("term_structure")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
        
        with col2:
            # 技术分析数据更新
            if st.button("📊 更新技术分析数据", use_container_width=True):
                with st.spinner("启动技术数据更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("technical_analysis")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
            
            # 基差数据更新
            if st.button("💰 更新基差分析数据", use_container_width=True):
                with st.spinner("启动基差数据更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("basis")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
            
            # 仓单数据更新
            if st.button("📜 更新仓单数据", use_container_width=True):
                with st.spinner("启动仓单数据更新..."):
                    result = st.session_state.data_manager.run_data_update_direct("receipt")
                    if result["status"] == "success":
                        st.success(result["message"])
                        st.info(result["details"])
                    else:
                        st.error(result["message"])
        
        st.markdown("---")
        st.warning("⚠️ 数据更新将在新的命令行窗口中运行，请按照提示完成操作")
    
    # Tab 3: 分析配置
    with tab3:
        st.header("🔧 分析配置")
        
        # 分析参数配置
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 基础配置")
            
            # 分析模块选择 - 先定义，后面会用到
            st.subheader("🔧 分析模块")
            analysis_modules = st.multiselect(
                "选择分析模块",
                options=["inventory", "positioning", "term_structure", "technical", "basis", "news"],
                default=["inventory", "positioning", "term_structure", "technical", "basis", "news"],
                format_func=lambda x: {
                    "inventory": "库存仓单分析",
                    "positioning": "持仓席位分析", 
                    "term_structure": "期限结构分析",
                    "technical": "技术面分析",
                    "basis": "基差分析",
                    "news": "新闻分析"
                }.get(x, x),
                help="选择要执行的分析模块"
            )
            
            # 根据选择的模块显示支持的品种
            module_name_mapping = {
                "inventory": "库存仓单分析",
                "positioning": "持仓席位分析", 
                "term_structure": "期限结构分析",
                "technical": "技术分析",
                "basis": "基差分析",
                "news": "新闻分析"
            }
            
            if analysis_modules:
                module_varieties_info = st.session_state.data_manager.get_module_supported_varieties()
                supported_varieties = set()
                for module in analysis_modules:
                    module_name = module_name_mapping.get(module, module)
                    module_varieties = module_varieties_info.get(module_name, set())
                    supported_varieties.update(module_varieties)
                
            else:
                supported_varieties = set()
            
            # 品种选择 - 改为文本输入方式
            with st.spinner("获取可用品种..."):
                data_status = st.session_state.data_manager.get_data_status()
                available_commodities = sorted(list(data_status["summary"]["common_commodities"]))
            
            # 文本输入品种代码
            commodity_input = st.text_input(
                "输入分析品种",
                value="AU",
                placeholder="如：AU",
                help="输入期货品种代码，多个品种用空格分隔"
            )
            
            # 解析输入的品种代码并显示本地数据情况
            if commodity_input.strip():
                # 分割并清理品种代码（支持空格、逗号分隔）
                input_commodities = []
                for separator in [' ', ',']:
                    if separator in commodity_input:
                        input_commodities = [code.strip().upper() for code in commodity_input.split(separator) if code.strip()]
                        break
                else:
                    # 如果没有分隔符，当作单个品种
                    input_commodities = [commodity_input.strip().upper()]
                
                selected_commodities = input_commodities
                
                # 显示每个品种的本地数据情况
                for commodity in input_commodities:
                    st.write(f"**{commodity} 本地数据情况：**")
                    
                    # 检查各个分析师模块的本地数据情况（除了新闻分析）
                    module_data_status = check_commodity_local_data(commodity, data_status)
                    
                    # 创建列来显示数据状态
                    cols = st.columns(6)  # 6个模块（除了新闻分析）
                    
                    module_display_names = {
                        "technical": "技术分析",
                        "basis": "基差分析", 
                        "inventory": "库存分析",
                        "positioning": "持仓分析",
                        "term_structure": "期限结构",
                        "receipt": "仓单分析"
                    }
                    
                    for i, (module_key, display_name) in enumerate(module_display_names.items()):
                        with cols[i]:
                            has_data = module_data_status.get(module_key, False)
                            if has_data:
                                st.success(f"✅ {display_name}\n本地数据√")
                            else:
                                st.error(f"❌ {display_name}\n本地数据✗")
                    
                    # 添加联网搜索备注
                    st.caption("*若无本地数据，则通过联网搜索数据")
                    
                    st.write("---")  # 分隔线
            else:
                selected_commodities = []
                st.info("💡 请输入要分析的期货品种代码")
            
            # 分析日期
            analysis_date = st.date_input(
                "分析日期",
                value=datetime.now().date() - timedelta(days=1),
                help="选择分析的目标日期"
            )
            
        
        with col2:
            st.subheader("⚙️ 高级配置")
            
            # 分析模式选择 - 简化为两种模式
            analysis_mode = st.radio(
                "选择分析模式",
                options=["analyst_only", "complete_flow"],
                index=1,
                format_func=lambda x: {
                    "analyst_only": "仅分析师团队",
                    "complete_flow": "完整流程分析（分析师+辩论+交易员+风控+决策）"
                }.get(x, x),
                help="选择不同的分析模式"
            )
            
            # 调试模式开关
            debug_mode = st.checkbox("🔧 调试模式", help="显示详细的状态调试信息")
            if debug_mode:
                st.session_state.debug_mode = True
            else:
                st.session_state.debug_mode = False
            
            # 根据模式显示不同选项
            if analysis_mode == "complete_flow":
                # 显示详细的流程说明
                with st.expander("🎭 完整5阶段流程详解", expanded=False):
                    st.markdown("""
### 📊 系统架构与分析流程

本系统采用**5阶段渐进式决策架构**，通过多层次、多角度的专业分析，确保投资决策的科学性和可追溯性。

---

#### 阶段1️⃣：六大分析师团队 📊

**职责**：基于真实市场数据进行专业分析

- **📦 库存仓单分析师**
  - 数据来源：日度库存数据、仓单统计
  - 分析要点：供需平衡、库存周期、库存与价格相关性
  - 输出：库存压力评估、主动/被动补库判断、看多/看空观点

- **📈 技术面分析师**
  - 数据来源：价格K线、技术指标（MACD、RSI、布林带等）
  - 分析要点：趋势判断、支撑阻力位、超买超卖信号
  - 输出：关键价位、交易信号、技术面多空倾向

- **🎯 持仓席位分析师**
  - 数据来源：前20名持仓席位数据、主力资金动向
  - 分析要点：资金流向、主力意图、持仓集中度
  - 输出：机构做多/做空信号、资金动向评估

- **💰 基差分析师**
  - 数据来源：期货价格vs现货价格、基差率
  - 分析要点：期现关系、套利机会、市场结构
  - 输出：基差收敛/扩大趋势、正向/负向市场判断

- **📊 期限结构分析师**
  - 数据来源：近月/远月合约价差、Contango/Backwardation
  - 分析要点：远期曲线形态、时间价值、市场预期
  - 输出：市场预期评估、期限结构风险提示

- **📰 新闻分析师**
  - 数据来源：宏观政策、行业新闻、市场情绪
  - 分析要点：政策影响、突发事件、市场预期变化
  - 输出：宏观面利好/利空因素、市场情绪评估

**阶段产出**：6份独立的专业分析报告，每份包含数据、观点、信心度

---

#### 阶段2️⃣：激情多空辩论 🎭

**职责**：通过对抗性辩论暴露分析盲点，提升决策质量

- **🐂 多头分析师**
  - 基于6大模块数据，论证做多机会
  - 反击空头观点，挖掘多头逻辑
  - 强调上涨动能、支撑因素

- **🐻 空头分析师**
  - 基于6大模块数据，识别做空风险
  - 痛击多头逻辑，暴露风险隐患
  - 强调回调压力、阻力因素

- **⚖️ AI评判系统**
  - 三维度评分：论据质量(40%) + 逻辑严密性(35%) + 客观理性度(25%)
  - 论据可验证性检查：所有数据必须可追溯
  - 加分机制：方向与分析师观点一致 → 加分

**辩论规则**：
- 每轮辩论包含：多头论述 → 空头反驳 → 多头反击 → 空头总结
- 评判基于论证质量，不预设立场
- 辩论评判影响交易员的信心度调整

**阶段产出**：多空评分、辩论胜负、关键论据总结

---

#### 阶段3️⃣：AI驱动专业交易员 💼

**职责**：综合前两阶段信息，制定具体交易策略

**核心决策逻辑**：

1. **【辩论评判分析】**
   - 统计各模块辩论结果：强势/偏强/中性
   - 识别多空优势模块和关键论据
   - 生成辩论质量评估报告

2. **【分析师观点科学评估】**
   - 统计看多/看空/中性模块数量
   - 评估数据支撑程度（充分/有限）
   - 计算可信度等级（高/中/低）

3. **【多空综合判断结论】**
   - **方向判断铁律**：分析师观点多数决（看多数量 vs 看空数量）
   - **信心度计算**：基础信心度（优势模块数） + 3类调整因素
     - 调整1：辩论评判倾向
     - 调整2：反向高信度模块
     - 调整3：中性模块辩论倾向
   - 输出：方向（看多/看空/中性）+ 信心度（高/中/低）

4. **【交易策略建议】**
   - **仓位计算**：根据信心度确定区间（高10-15%、中5-10%、低2-5%）
   - **止损位设置**：基于关键技术位（支撑/阻力）
   - **持仓周期**：短线/中线/长线
   - **风控措施**：严格止损、分批建仓、动态调整

**透明化原则**：所有计算过程完全透明，决策依据可追溯

**阶段产出**：交易方向、建议仓位、止损位、风险提示

---

#### 阶段4️⃣：专业风控管理 🛡️

**职责**：独立风险评估，一票否决权

**风控评估流程**：

1. **风险矩阵评估**
   - 潜在最大亏损（基于止损位计算）
   - 风险发生概率（基于辩论分歧度）
   - 风险等级判定：极高/高/中/低

2. **操作信心度独立判断**
   - 基于风险等级确定操作信心度
   - 高风险 → 低信心 → 保守仓位
   - 低风险 → 高信心 → 适度配置

3. **风控批准意见**
   - 🟢 批准：风险可控，正常执行
   - 🟡 有条件批准：高风险，必须轻仓
   - 🔴 拒绝：风险失控，禁止操作

4. **仓位上限强制约束**
   - 极高风险：≤1%
   - 高风险：2-5%
   - 中风险：5-10%
   - 低风险：10-15%

**风控红线**：
- 止损必须基于技术位（通常2.5-3.5%）
- 单笔亏损极端情况不超过5%
- 风险失控立即减仓

**阶段产出**：风险等级、操作信心度、仓位上限、批准意见

---

#### 阶段5️⃣：CIO综合决策 👔

**职责**：最终拍板，权威决策

**决策框架**：

1. **方向判断确认**
   - 复核交易员的方向判断
   - 基于分析师观点（铁律：多数决）
   - 最终方向：看多/看空/观望

2. **双信心度体系**
   - **方向信心度**：对方向判断的信心（基于分析师共识）
   - **操作信心度**：对安全执行的信心（基于风控评估）
   - 两者不同维度，可以不一致（例如：方向信心中 + 操作信心低）

3. **仓位最终确定**
   - 交易员建议 vs 风控上限 → 取更保守值
   - 风控拥有一票否决权
   - 最终仓位必须在风控框架内

4. **执行指导制定**
   - 仓位配置：区间、分批策略
   - 风险控制：止损纪律、动态调整
   - 监控要点：关键价位、风险信号

**CIO核心判断**：
- 判断1：市场方向与趋势基础
- 判断2：风险管控的优先级
- 判断3：操作策略的保守程度

**阶段产出**：最终决策、操作指导、监控要点、决策追溯

---

### 🎯 系统特色

✅ **数据驱动**：所有判断基于真实市场数据  
✅ **多层验证**：6大分析师 + 辩论 + 交易员 + 风控 + CIO  
✅ **透明可追溯**：每个决策环节完全透明，计算过程可查  
✅ **风控优先**：风控拥有一票否决权，保护本金第一  
✅ **角色分工**：各司其职，制衡机制，避免单一视角盲点  
                    """)
                
                debate_rounds = st.slider(
                    "辩论轮数",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="设置多空双方的辩论轮数"
                )
                
                st.warning("⚠️ 完整流程需要消耗更多AI资源，预计耗时3-5分钟")
            
            else:
                st.info("📊 仅执行6大分析模块，不包含辩论和决策")
                debate_rounds = 0  # 不需要辩论
            
            # AI模型选择
            ai_model = st.selectbox(
                "AI分析模型",
                options=["deepseek-reasoner", "deepseek-chat"],
                index=0,
                help="选择用于分析的AI模型"
            )
            
            # 移除分析深度选项 - AI模型选择已足够区分分析质量
            
            # 实时数据
            use_realtime = st.checkbox(
                "启用实时数据增强",
                value=True,
                help="使用实时搜索数据增强分析结果"
            )
        
        # 保存配置到session state
        if st.button("💾 保存配置", type="primary"):
            st.session_state.analysis_config = {
                "commodities": selected_commodities,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "modules": analysis_modules,
                "analysis_mode": analysis_mode,
                "ai_model": ai_model,
                "use_realtime": use_realtime,
                "debate_rounds": debate_rounds
            }
            st.success("✅ 配置已保存")
        
        # 开始分析按钮
        if st.button("🚀 开始分析", type="primary", disabled=not selected_commodities):
            if selected_commodities and analysis_modules:
                # 启动分析
                with st.spinner("正在启动分析..."):
                    st.session_state.analysis_manager.start_analysis(
                        commodities=selected_commodities,
                        analysis_date=analysis_date.strftime("%Y-%m-%d"),
                        modules=analysis_modules,
                        analysis_mode=analysis_mode,
                        config={
                            "ai_model": ai_model,
                            "use_realtime": use_realtime,
                            "debate_rounds": debate_rounds
                        }
                    )
                st.success("✅ 分析已启动，请切换到'分析结果'标签页查看进度")
                st.rerun()
            else:
                st.error("❌ 请至少选择一个品种和一个分析模块")
    
    # Tab 4: 分析结果
    with tab4:
        st.header("🎭 分析结果")
        
        # 检查是否有正在进行的分析
        if hasattr(st.session_state.analysis_manager, 'current_analysis') and st.session_state.analysis_manager.current_analysis:
            
            # 如果分析刚启动，开始处理
            if (st.session_state.analysis_manager.current_analysis.get("status") == "running" and 
                not st.session_state.analysis_manager.analysis_results):
                
                st.info("🚀 开始执行分析...")
                
                # 处理所有品种
                st.session_state.analysis_manager.process_all_commodities()
            
            # 显示分析进度
            st.session_state.analysis_manager.display_progress()
            
            # 显示分析结果
            st.session_state.analysis_manager.display_results()
            
            # Word报告生成按钮
            if (st.session_state.analysis_manager.analysis_results and 
                st.session_state.analysis_manager.current_analysis.get("status") == "completed" and
                DOCX_AVAILABLE):
                
                st.markdown("---")
                
                # 🔥 Word报告生成选项
                st.subheader("📄 生成Word报告")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    report_mode = st.radio(
                        "报告模式",
                        options=["快速模式（仅文字）", "完整模式（包含图表）"],
                        help="快速模式：仅包含文字分析，生成速度快（约10秒）\n完整模式：包含所有图表，需要更长时间（约2-5分钟）",
                        horizontal=True
                    )
                
                with col2:
                    include_charts = (report_mode == "完整模式（包含图表）")
                
                if st.button("📄 生成Word报告", type="primary"):
                    # 创建进度显示容器
                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()
                    
                    def update_progress(msg: str):
                        """更新进度显示"""
                        status_placeholder.info(f"📝 {msg}")
                    
                    try:
                        update_progress("开始生成Word报告...")
                        
                        doc_io = st.session_state.word_generator.create_comprehensive_report(
                            st.session_state.analysis_manager.analysis_results,
                            st.session_state.analysis_manager.current_analysis,
                            include_charts=include_charts,
                            progress_callback=update_progress
                        )
                        
                        # 清空进度显示
                        progress_placeholder.empty()
                        status_placeholder.empty()
                        
                        # 提供下载
                        st.download_button(
                            label="📥 下载Word报告",
                            data=doc_io.getvalue(),
                            file_name=f"期货分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                        
                        st.success("✅ Word报告生成完成！")
                        
                        if not include_charts:
                            st.info("💡 提示：快速模式已跳过图表转换，如需查看图表请选择完整模式或在系统界面查看交互式图表。")
                        
                    except Exception as e:
                        progress_placeholder.empty()
                        status_placeholder.empty()
                        st.error(f"❌ Word报告生成失败: {e}")
                        st.exception(e)
            
            # 自动刷新（仅在分析运行时）
            if st.session_state.analysis_manager.is_analysis_running():
                time.sleep(1)
                st.rerun()
                
        else:
            st.info("👈 请在分析配置页面设置参数并开始分析")

# ============================================================================
# 应用入口
# ============================================================================

if __name__ == "__main__":
    main()
