#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit期限结构数据更新适配器
将完善的期限结构数据更新器集成到streamlit系统中
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from 完善期限结构数据更新器 import PerfectedTermStructureUpdater

def show_term_structure_updater():
    """显示期限结构数据更新界面"""
    
    st.title("📊 期限结构数据更新系统")
    st.markdown("---")
    st.markdown("""
    ### 功能特点
    - ✅ **完全修复DCE Y品种错误** - 解决"list index out of range"问题
    - ✅ **修复CZCE日期异常** - 清理1970年异常日期
    - ✅ **智能增量更新** - 只获取缺失数据，提高效率
    - ✅ **健壮错误处理** - 多重备用策略，提高成功率
    - ✅ **科学计算逻辑** - 准确的roll yield计算
    """)
    
    # 初始化更新器
    if 'ts_updater' not in st.session_state:
        with st.spinner("初始化数据更新器..."):
            st.session_state.ts_updater = PerfectedTermStructureUpdater()
    
    updater = st.session_state.ts_updater
    
    # 获取现有品种
    all_varieties = updater.get_all_varieties()
    major_varieties = [v for v in updater.major_varieties if v in all_varieties]
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 更新配置")
        
        # 目标日期
        default_date = datetime.now().date()
        end_date = st.date_input(
            "📅 目标日期",
            value=default_date,
            min_value=datetime(2020, 1, 1).date(),
            max_value=default_date + timedelta(days=7),
            help="数据更新到的目标日期"
        )
        
        end_date_str = end_date.strftime('%Y%m%d')
        
        # 品种选择模式
        st.markdown("### 🎯 品种选择")
        update_mode = st.radio(
            "更新模式",
            ["🏆 主力品种", "📊 全部品种", "🎨 自定义选择"],
            help="选择要更新的品种范围"
        )
        
        if update_mode == "🏆 主力品种":
            selected_varieties = major_varieties
            st.info(f"将更新 {len(selected_varieties)} 个主力品种")
            
        elif update_mode == "📊 全部品种":
            selected_varieties = all_varieties
            st.info(f"将更新 {len(selected_varieties)} 个品种")
            
        else:  # 自定义选择
            # 按交易所分组显示
            dce_varieties = [v for v in all_varieties if updater.exchange_map.get(v) == 'DCE']
            shfe_varieties = [v for v in all_varieties if updater.exchange_map.get(v) == 'SHFE']
            czce_varieties = [v for v in all_varieties if updater.exchange_map.get(v) == 'CZCE']
            ine_varieties = [v for v in all_varieties if updater.exchange_map.get(v) == 'INE']
            gfex_varieties = [v for v in all_varieties if updater.exchange_map.get(v) == 'GFEX']
            
            selected_varieties = []
            
            with st.expander("🏢 大连商品交易所 (DCE)"):
                dce_selected = st.multiselect(
                    "DCE品种",
                    dce_varieties,
                    default=['Y', 'M', 'L', 'I', 'J'] if len(dce_varieties) >= 5 else dce_varieties[:3],
                    key="dce_select"
                )
                selected_varieties.extend(dce_selected)
            
            with st.expander("🏭 上海期货交易所 (SHFE)"):
                shfe_selected = st.multiselect(
                    "SHFE品种",
                    shfe_varieties,
                    default=['CU', 'AL', 'RB', 'AU', 'AG'] if len(shfe_varieties) >= 5 else shfe_varieties[:3],
                    key="shfe_select"
                )
                selected_varieties.extend(shfe_selected)
            
            with st.expander("🌾 郑州商品交易所 (CZCE)"):
                czce_selected = st.multiselect(
                    "CZCE品种",
                    czce_varieties,
                    default=['MA', 'TA', 'CF', 'SR', 'OI'] if len(czce_varieties) >= 5 else czce_varieties[:3],
                    key="czce_select"
                )
                selected_varieties.extend(czce_selected)
            
            if ine_varieties:
                with st.expander("⚡ 上海国际能源中心 (INE)"):
                    ine_selected = st.multiselect("INE品种", ine_varieties, key="ine_select")
                    selected_varieties.extend(ine_selected)
            
            if gfex_varieties:
                with st.expander("🌐 广州期货交易所 (GFEX)"):
                    gfex_selected = st.multiselect("GFEX品种", gfex_varieties, key="gfex_select")
                    selected_varieties.extend(gfex_selected)
            
            st.info(f"已选择 {len(selected_varieties)} 个品种")
        
        # 高级选项
        st.markdown("---")
        st.markdown("### ⚙️ 高级选项")
        
        clean_dates = st.checkbox(
            "🧹 清理无效日期",
            value=True,
            help="更新前先清理现有数据中的无效日期"
        )
        
        priority_update = st.checkbox(
            "⚡ 优先更新主力品种",
            value=True,
            help="优先更新主力品种，提高重要数据的更新成功率"
        )
    
    # 主界面
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.header("🚀 数据更新控制")
        
        # 更新按钮
        if st.button("🔄 开始更新数据", type="primary", use_container_width=True):
            if not selected_varieties:
                st.error("❌ 请先选择要更新的品种！")
                return
            
            # 显示更新计划
            st.info(f"📋 更新计划: {len(selected_varieties)} 个品种到 {end_date_str}")
            
            # 创建进度显示
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                current_variety = st.empty()
                
                # 结果统计容器
                results_container = st.container()
                
                def progress_callback(message):
                    status_text.text(message)
                
                # 数据清理阶段
                if clean_dates:
                    st.markdown("### 🧹 第一阶段：数据清理")
                    cleaned_varieties = []
                    
                    for i, variety in enumerate(selected_varieties):
                        progress_bar.progress((i + 1) / len(selected_varieties))
                        current_variety.text(f"🧹 清理 {variety} 的无效日期...")
                        
                        result = updater.clean_invalid_dates(variety)
                        if result['success'] and result.get('invalid_count', 0) > 0:
                            cleaned_varieties.append(f"{variety} ({result['invalid_count']}条)")
                    
                    if cleaned_varieties:
                        st.success(f"✅ 清理完成：{', '.join(cleaned_varieties)}")
                    else:
                        st.info("ℹ️ 未发现需要清理的无效日期")
                
                # 数据更新阶段
                st.markdown("### 🔄 第二阶段：数据更新")
                
                # 确定更新顺序
                if priority_update:
                    # 主力品种优先
                    priority_varieties = [v for v in selected_varieties if v in updater.major_varieties]
                    other_varieties = [v for v in selected_varieties if v not in updater.major_varieties]
                    update_order = priority_varieties + other_varieties
                else:
                    update_order = selected_varieties
                
                # 执行更新
                start_time = time.time()
                results = {
                    'success_varieties': [],
                    'failed_varieties': [],
                    'total_records_added': 0,
                    'details': []
                }
                
                for i, variety in enumerate(update_order):
                    progress_bar.progress((i + 1) / len(update_order))
                    current_variety.text(f"🔄 [{i+1}/{len(update_order)}] 更新 {variety}...")
                    
                    result = updater.update_variety_data(variety, end_date_str)
                    results['details'].append(result)
                    
                    if result['success']:
                        results['success_varieties'].append(variety)
                        results['total_records_added'] += result.get('records_added', 0)
                        current_variety.text(f"✅ {variety}: {result['message']}")
                    else:
                        results['failed_varieties'].append(variety)
                        current_variety.text(f"❌ {variety}: {result['message']}")
                    
                    time.sleep(0.5)  # 短暂停顿以显示状态
                
                # 完成统计
                end_time = time.time()
                total_time = end_time - start_time
                
                progress_bar.progress(1.0)
                status_text.text("🎉 更新完成！")
                current_variety.empty()
                
                # 显示结果汇总
                with results_container:
                    st.markdown("### 📊 更新结果汇总")
                    
                    col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                    
                    with col_metrics1:
                        st.metric(
                            "✅ 成功品种",
                            len(results['success_varieties']),
                            delta=f"{len(results['success_varieties'])/len(selected_varieties)*100:.1f}%"
                        )
                    
                    with col_metrics2:
                        st.metric(
                            "📈 新增记录",
                            results['total_records_added'],
                            delta=f"+{results['total_records_added']}"
                        )
                    
                    with col_metrics3:
                        st.metric(
                            "⏱️ 用时",
                            f"{total_time:.1f}秒",
                            delta=f"{total_time/len(selected_varieties):.1f}s/品种"
                        )
                    
                    # 成功品种详情
                    if results['success_varieties']:
                        with st.expander(f"✅ 成功更新品种 ({len(results['success_varieties'])}个)", expanded=True):
                            success_data = []
                            for detail in results['details']:
                                if detail['success']:
                                    success_data.append({
                                        '品种': detail['variety'],
                                        '交易所': detail['exchange'],
                                        '新增记录': detail.get('records_added', 0),
                                        '总记录数': detail.get('total_records', 'N/A'),
                                        '状态': detail['message']
                                    })
                            
                            if success_data:
                                st.dataframe(pd.DataFrame(success_data), use_container_width=True)
                    
                    # 失败品种详情
                    if results['failed_varieties']:
                        with st.expander(f"❌ 更新失败品种 ({len(results['failed_varieties'])}个)"):
                            failed_data = []
                            for detail in results['details']:
                                if not detail['success']:
                                    failed_data.append({
                                        '品种': detail['variety'],
                                        '交易所': detail['exchange'],
                                        '失败原因': detail['message']
                                    })
                            
                            if failed_data:
                                st.dataframe(pd.DataFrame(failed_data), use_container_width=True)
                                
                                st.markdown("#### 💡 失败原因分析")
                                st.markdown("""
                                - **未获取到新数据**: 可能是交易所接口问题或该品种无交易
                                - **数据处理失败**: 数据格式异常或缺少必要字段
                                - **未知交易所**: 品种交易所映射需要更新
                                - **网络问题**: 建议稍后重试
                                """)
    
    with col2:
        st.header("📊 数据状态监控")
        
        # 快速状态检查
        if st.button("🔍 检查数据状态", use_container_width=True):
            with st.spinner("检查数据状态..."):
                status_data = []
                
                check_varieties = selected_varieties[:15] if len(selected_varieties) > 15 else selected_varieties
                
                for variety in check_varieties:
                    latest_date = updater.get_variety_latest_date(variety)
                    csv_file = updater.data_dir / variety / "term_structure.csv"
                    
                    if csv_file.exists():
                        try:
                            df = pd.read_csv(csv_file)
                            record_count = len(df)
                            zero_count = (df['close'] == 0).sum() if 'close' in df.columns else 0
                            
                            status_icon = "✅" if latest_date and latest_date.strftime('%Y%m%d') == end_date_str else "⚠️"
                            
                            status_data.append({
                                '状态': status_icon,
                                '品种': variety,
                                '交易所': updater.exchange_map.get(variety, 'Unknown'),
                                '记录数': record_count,
                                '最新日期': latest_date.strftime('%Y%m%d') if latest_date else 'N/A',
                                '零值数': zero_count
                            })
                        except:
                            status_data.append({
                                '状态': '❌',
                                '品种': variety,
                                '交易所': updater.exchange_map.get(variety, 'Unknown'),
                                '记录数': 0,
                                '最新日期': '读取失败',
                                '零值数': 0
                            })
                    else:
                        status_data.append({
                            '状态': '⚪',
                            '品种': variety,
                            '交易所': updater.exchange_map.get(variety, 'Unknown'),
                            '记录数': 0,
                            '最新日期': '文件不存在',
                            '零值数': 0
                        })
                
                if status_data:
                    st.dataframe(pd.DataFrame(status_data), use_container_width=True, height=400)
                    
                    # 状态统计
                    up_to_date = sum(1 for item in status_data if item['状态'] == '✅')
                    total_checked = len(status_data)
                    
                    st.metric(
                        "📅 数据最新品种",
                        f"{up_to_date}/{total_checked}",
                        delta=f"{up_to_date/total_checked*100:.1f}%"
                    )
        
        # 数据质量分析
        st.markdown("---")
        st.markdown("### 📈 数据质量分析")
        
        if st.button("📊 质量分析", use_container_width=True):
            with st.spinner("分析数据质量..."):
                quality_stats = {
                    'excellent': 0,  # 无问题
                    'good': 0,       # 轻微问题
                    'poor': 0,       # 严重问题
                    'empty': 0       # 空文件
                }
                
                for variety in all_varieties:
                    csv_file = updater.data_dir / variety / "term_structure.csv"
                    
                    if not csv_file.exists():
                        quality_stats['empty'] += 1
                        continue
                    
                    try:
                        df = pd.read_csv(csv_file)
                        if df.empty:
                            quality_stats['empty'] += 1
                            continue
                        
                        zero_percentage = (df['close'] == 0).sum() / len(df) * 100
                        latest_date = updater.get_variety_latest_date(variety)
                        is_up_to_date = latest_date and latest_date.strftime('%Y%m%d') == end_date_str
                        
                        if zero_percentage == 0 and is_up_to_date:
                            quality_stats['excellent'] += 1
                        elif zero_percentage < 10:
                            quality_stats['good'] += 1
                        else:
                            quality_stats['poor'] += 1
                            
                    except:
                        quality_stats['poor'] += 1
                
                # 显示质量统计
                st.markdown("#### 数据质量分布")
                col_q1, col_q2 = st.columns(2)
                
                with col_q1:
                    st.metric("🟢 优秀", quality_stats['excellent'])
                    st.metric("🟡 良好", quality_stats['good'])
                
                with col_q2:
                    st.metric("🔴 问题", quality_stats['poor'])
                    st.metric("⚪ 空文件", quality_stats['empty'])
                
                total_quality = quality_stats['excellent'] + quality_stats['good']
                total_varieties = sum(quality_stats.values())
                
                if total_varieties > 0:
                    quality_percentage = total_quality / total_varieties * 100
                    st.progress(quality_percentage / 100)
                    st.caption(f"整体数据质量: {quality_percentage:.1f}%")
        
        # 系统信息
        st.markdown("---")
        st.markdown("### ℹ️ 系统信息")
        
        with st.expander("系统状态"):
            st.write(f"📁 数据目录: {updater.data_dir}")
            st.write(f"📊 总品种数: {len(all_varieties)}")
            st.write(f"🏆 主力品种数: {len(major_varieties)}")
            st.write(f"🏢 支持交易所: DCE, SHFE, CZCE, INE, GFEX")
            st.write(f"⚙️ 更新器版本: v2.0 (完善版)")

if __name__ == "__main__":
    show_term_structure_updater()
