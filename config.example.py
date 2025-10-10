#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件模板
使用前请复制为 config.py 并填入真实的API密钥
"""

# ============================================================================
# API配置
# ============================================================================

# DeepSeek API配置（必需）
# 获取地址: https://platform.deepseek.com/
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY_HERE"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Serper API配置（可选，用于新闻搜索）
# 获取地址: https://serper.dev/
SERPER_API_KEY = "YOUR_SERPER_API_KEY_HERE"

# ============================================================================
# 系统配置
# ============================================================================

# 分析配置
DEFAULT_DAYS_BACK = 3  # 默认回溯天数
MAX_NEWS_PER_CATEGORY = 50  # 每个类别最大新闻数量
REQUEST_DELAY = 1  # API请求间隔（秒）

# 数据路径
DATA_ROOT_DIR = "./qihuo/database"
RESULTS_DIR = "./qihuo/trading_agents_results"
LOGS_DIR = "./qihuo/logs"
CACHE_DIR = "./qihuo/cache"

# ============================================================================
# 支持的品种列表
# ============================================================================

SUPPORTED_COMMODITIES = {
    # 有色金属
    "铜": {
        "symbol": "CU",
        "exchange": "SHFE",
        "category": "有色金属"
    },
    "铝": {
        "symbol": "AL",
        "exchange": "SHFE",
        "category": "有色金属"
    },
    "锌": {
        "symbol": "ZN",
        "exchange": "SHFE",
        "category": "有色金属"
    },
    
    # 贵金属
    "黄金": {
        "symbol": "AU",
        "exchange": "SHFE",
        "category": "贵金属"
    },
    "白银": {
        "symbol": "AG",
        "exchange": "SHFE",
        "category": "贵金属"
    },
    
    # 黑色系
    "螺纹钢": {
        "symbol": "RB",
        "exchange": "SHFE",
        "category": "黑色系"
    },
    "热卷": {
        "symbol": "HC",
        "exchange": "SHFE",
        "category": "黑色系"
    },
    "铁矿石": {
        "symbol": "I",
        "exchange": "DCE",
        "category": "黑色系"
    },
    
    # 能化
    "原油": {
        "symbol": "SC",
        "exchange": "INE",
        "category": "能源化工"
    },
    "橡胶": {
        "symbol": "RU",
        "exchange": "SHFE",
        "category": "能源化工"
    },
    
    # 农产品
    "大豆": {
        "symbol": "A",
        "exchange": "DCE",
        "category": "农产品"
    },
    "玉米": {
        "symbol": "C",
        "exchange": "DCE",
        "category": "农产品"
    },
    "棉花": {
        "symbol": "CF",
        "exchange": "CZCE",
        "category": "农产品"
    }
}

# ============================================================================
# 品种代码映射
# ============================================================================

# 交易所代码
EXCHANGE_CODES = {
    "SHFE": "上海期货交易所",
    "DCE": "大连商品交易所",
    "CZCE": "郑州商品交易所",
    "INE": "上海国际能源交易中心",
    "CFFEX": "中国金融期货交易所",
    "GFEX": "广州期货交易所"
}

# 品种分类
COMMODITY_CATEGORIES = {
    "黑色系": ["RB", "HC", "I", "J", "JM", "SS"],
    "有色金属": ["CU", "AL", "ZN", "NI", "SN", "PB"],
    "贵金属": ["AU", "AG"],
    "能化系": ["RU", "NR", "BU", "FU", "LU", "EB", "EG", "MA", "TA", "PX"],
    "农产品": ["SR", "CF", "AP", "CJ", "SP", "P", "Y", "M", "RM", "OI"],
    "建材轻工": ["FG", "SA", "L", "PP", "V", "UR"],
    "新兴品种": ["SF", "SM", "LC", "SI", "PS"]
}

