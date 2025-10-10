#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货价格数据获取器
从本地数据库获取真实的期货价格
"""

import pandas as pd
import os
from typing import Optional, Dict

class FuturesPriceProvider:
    """期货价格数据提供器"""
    
    def __init__(self, data_root_dir: str = "qihuo/database"):
        self.data_root_dir = data_root_dir
        
    def get_current_price(self, commodity: str) -> Optional[float]:
        """获取期货品种的当前价格（最新收盘价）"""
        try:
            ohlc_file = os.path.join(self.data_root_dir, "technical_analysis", commodity, "ohlc_data.csv")
            
            if not os.path.exists(ohlc_file):
                print(f"警告：找不到{commodity}的价格数据文件")
                return None
                
            df = pd.read_csv(ohlc_file)
            
            if df.empty:
                print(f"警告：{commodity}的价格数据为空")
                return None
                
            # 获取最新收盘价
            current_price = float(df.iloc[-1]['收盘'])
            print(f"✅ 获取{commodity}当前价格: {current_price:.0f}元/吨")
            
            return current_price
            
        except Exception as e:
            print(f"错误：获取{commodity}价格失败 - {e}")
            return None
    
    def get_price_range(self, commodity: str, days: int = 30) -> Dict[str, float]:
        """获取指定天数内的价格范围"""
        try:
            ohlc_file = os.path.join(self.data_root_dir, "technical_analysis", commodity, "ohlc_data.csv")
            
            if not os.path.exists(ohlc_file):
                return {}
                
            df = pd.read_csv(ohlc_file)
            
            if df.empty:
                return {}
                
            # 获取最近N天的数据
            recent_data = df.tail(days)
            
            return {
                'current_price': float(df.iloc[-1]['收盘']),
                'high': float(recent_data['最高'].max()),
                'low': float(recent_data['最低'].min()),
                'avg': float(recent_data['收盘'].mean())
            }
            
        except Exception as e:
            print(f"错误：获取{commodity}价格范围失败 - {e}")
            return {}
    
    def get_support_resistance_levels(self, commodity: str) -> Dict[str, list]:
        """从历史价格中提取支撑阻力位"""
        try:
            ohlc_file = os.path.join(self.data_root_dir, "technical_analysis", commodity, "ohlc_data.csv")
            
            if not os.path.exists(ohlc_file):
                return {'support': [], 'resistance': []}
                
            df = pd.read_csv(ohlc_file)
            
            if df.empty or len(df) < 20:
                return {'support': [], 'resistance': []}
                
            # 获取最近60天的数据
            recent_data = df.tail(60)
            
            # 简单的支撑阻力位计算
            high_prices = recent_data['最高']
            low_prices = recent_data['最低']
            
            # 找出局部高点和低点
            resistance_levels = []
            support_levels = []
            
            # 使用简单的局部极值方法
            for i in range(2, len(recent_data) - 2):
                # 局部高点（阻力位）
                if (high_prices.iloc[i] > high_prices.iloc[i-1] and 
                    high_prices.iloc[i] > high_prices.iloc[i+1] and
                    high_prices.iloc[i] > high_prices.iloc[i-2] and 
                    high_prices.iloc[i] > high_prices.iloc[i+2]):
                    resistance_levels.append(float(high_prices.iloc[i]))
                
                # 局部低点（支撑位）
                if (low_prices.iloc[i] < low_prices.iloc[i-1] and 
                    low_prices.iloc[i] < low_prices.iloc[i+1] and
                    low_prices.iloc[i] < low_prices.iloc[i-2] and 
                    low_prices.iloc[i] < low_prices.iloc[i+2]):
                    support_levels.append(float(low_prices.iloc[i]))
            
            # 去重并排序
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)[:3]
            support_levels = sorted(list(set(support_levels)), reverse=True)[:3]
            
            return {
                'support': support_levels,
                'resistance': resistance_levels
            }
            
        except Exception as e:
            print(f"错误：获取{commodity}支撑阻力位失败 - {e}")
            return {'support': [], 'resistance': []}

# 创建全局实例
futures_price_provider = FuturesPriceProvider()

def get_commodity_current_price(commodity: str) -> float:
    """获取商品当前价格的便捷函数"""
    price = futures_price_provider.get_current_price(commodity)
    
    if price is None:
        # 回退到估算价格
        fallback_prices = {
            "RB": 3500, "CU": 79620, "AU": 450, "AG": 5000,
            "I": 800, "J": 2000, "M": 3000, "Y": 8000,
            "AL": 20000, "ZN": 25000, "NI": 130000, "SN": 220000
        }
        price = fallback_prices.get(commodity, 3000)
        print(f"⚠️ 使用回退价格 {commodity}: {price:.0f}元/吨")
    
    return price

if __name__ == "__main__":
    # 测试价格获取
    provider = FuturesPriceProvider()
    
    # 测试铜期货
    cu_price = provider.get_current_price("CU")
    print(f"铜期货当前价格: {cu_price}")
    
    # 测试价格范围
    cu_range = provider.get_price_range("CU", 30)
    print(f"铜期货30天价格范围: {cu_range}")
    
    # 测试支撑阻力位
    cu_levels = provider.get_support_resistance_levels("CU")
    print(f"铜期货支撑阻力位: {cu_levels}")
