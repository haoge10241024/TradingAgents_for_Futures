#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓分析系统 - 快速版本
专门优化云端部署性能
作者：7haoge
邮箱：953534947@qq.com
"""

import streamlit as st
import os
import sys

# 确保导入路径正确
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统 - 快速版",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 显示性能提示
st.markdown("""
<div style="background-color: #e8f5e8; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 4px solid #28a745;">
    <h4 style="color: #155724; margin: 0;">🚀 快速版本已启用</h4>
    <p style="color: #155724; margin: 0.5rem 0 0 0;">
        • 智能缓存系统 • 并发数据获取 • 网络优化 • 首次运行后显著加速
    </p>
</div>
""", unsafe_allow_html=True)

# 导入并运行主应用
try:
    from streamlit_app import StreamlitApp
    
    # 创建应用实例
    app = StreamlitApp()
    
    # 渲染应用
    app.render_sidebar()
    app.render_main_content()
    
except ImportError as e:
    st.error(f"导入错误: {str(e)}")
    st.info("请确保所有依赖包已正确安装")
except Exception as e:
    st.error(f"应用启动失败: {str(e)}")
    st.info("请检查系统配置或联系技术支持") 