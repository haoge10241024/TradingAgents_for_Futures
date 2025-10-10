#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 应用启动入口
这是streamlit_app.py的简化入口文件
作者：7haoge
邮箱：953534947@qq.com
"""

# 直接导入并运行主应用
from streamlit_app import StreamlitApp

if __name__ == "__main__":
    app = StreamlitApp()
    app.run() 