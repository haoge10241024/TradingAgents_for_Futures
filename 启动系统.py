#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货分析系统启动脚本
"""

import subprocess
import sys
import os

def check_dependencies():
    """检查依赖库"""
    try:
        import streamlit
        import pandas
        import plotly
        print("✅ 依赖库检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖库: {e}")
        print("正在安装依赖库...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def main():
    """主函数"""
    print("🚀 期货分析Streamlit系统启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 启动系统
    print("🎯 启动系统...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "期货TradingAgents系统_专业完整版界面.py"
        ])
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()
