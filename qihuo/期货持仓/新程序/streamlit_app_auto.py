#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 自动跳过版本
智能处理广期所超时问题，无需手动选择
作者：7haoge
邮箱：953534947@qq.com
"""

# 直接运行主应用
if __name__ == "__main__":
    import streamlit as st
    import sys
    import os
    
    # 确保当前目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # 导入并运行主应用
    from streamlit_app import StreamlitApp
    
    # 设置页面标题
    st.set_page_config(
        page_title="期货持仓分析系统 - 自动跳过版",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 在页面顶部显示版本信息
    st.markdown("""
    <div style="background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin: 0; color: #1f77b4;">🚀 期货持仓分析系统 - 自动跳过版</h4>
        <p style="margin: 5px 0 0 0; color: #666;">智能处理广期所超时问题，自动跳过卡顿交易所，确保分析流畅进行</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 运行应用
    app = StreamlitApp()
    app.run() 