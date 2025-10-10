#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 配置文件
作者：7haoge
邮箱：953534947@qq.com
"""

# 系统配置
SYSTEM_CONFIG = {
    "app_name": "期货持仓分析系统",
    "version": "2.1",
    "author": "7haoge",
    "email": "953534947@qq.com",
    "description": "基于期货持仓数据的多策略分析系统 - 智能自动跳过版"
}

# 数据配置
DATA_CONFIG = {
    "data_dir": "data",
    "cache_ttl": 3600,  # 缓存时间（秒）
    "max_retries": 3,   # 最大重试次数
    "timeout": 30,      # 网络超时时间（秒）
}

# 交易所配置
EXCHANGE_CONFIG = {
    "大商所": {
        "code": "DCE",
        "name": "大连商品交易所",
        "priority": 1,
        "enabled": True
    },
    "中金所": {
        "code": "CFFEX", 
        "name": "中国金融期货交易所",
        "priority": 2,
        "enabled": True
    },
    "郑商所": {
        "code": "CZCE",
        "name": "郑州商品交易所", 
        "priority": 3,
        "enabled": True
    },
    "上期所": {
        "code": "SHFE",
        "name": "上海期货交易所",
        "priority": 4,
        "enabled": True
    },
    "广期所": {
        "code": "GFEX",
        "name": "广州期货交易所",
        "priority": 5,
        "enabled": False  # 默认关闭，可选开启
    }
}

# 策略配置
STRATEGY_CONFIG = {
    "多空力量变化策略": {
        "enabled": True,
        "min_change_threshold": 50,  # 最小变化阈值
        "description": "分析席位持仓增减变化判断市场趋势"
    },
    "蜘蛛网策略": {
        "enabled": True,
        "msd_threshold": 0.05,  # MSD阈值
        "min_seats": 5,         # 最小席位数
        "its_ratio": 0.4,       # 知情者比例
        "description": "基于持仓分布分化程度判断机构资金参与情况"
    },
    "家人席位反向操作策略": {
        "enabled": True,
        "default_retail_seats": [
            "东方财富", "平安期货", "徽商期货"
        ],
        "description": "基于散户投资者行为特点的反向操作策略。看多信号：所有家人席位空单增加且多单减少或不变；看空信号：所有家人席位多单增加且空单减少或不变"
    }
}

# 显示配置
DISPLAY_CONFIG = {
    "max_signals_per_strategy": 10,  # 每个策略最大显示信号数
    "max_contracts_in_chart": 10,    # 图表中最大合约数
    "show_progress": True,           # 显示进度条
    "auto_refresh": False,           # 自动刷新
    "include_term_structure": True,  # 总是包含期限结构分析
}

# UI配置
UI_CONFIG = {
    "theme": "light",
    "sidebar_width": 300,
    "chart_height": 500,
    "colors": {
        "long_signal": "#ff4444",
        "short_signal": "#44ff44", 
        "resonance_signal": "#ffc107",
        "primary": "#1f77b4"
    }
}

# 网络配置
NETWORK_CONFIG = {
    "test_urls": [
        "https://www.baidu.com",
        "https://akshare.akfamily.xyz",
        "https://www.sina.com.cn"
    ],
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "futures_analysis.log",
    "max_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
} 