import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from futures_position_analysis import FuturesPositionAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import io
import akshare as ak
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置页面配置
st.set_page_config(
    page_title="期货持仓分析系统",
    page_icon="📊",
    layout="wide"
)

# 创建data目录
@st.cache_data
def ensure_data_directory():
    """确保data目录存在"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

# 优化的数据获取函数
@st.cache_data(ttl=3600, show_spinner=False)
def get_analysis_results_optimized(trade_date):
    """优化的分析结果获取函数"""
    try:
        data_dir = ensure_data_directory()
        analyzer = FuturesPositionAnalyzer(data_dir)
        
        # 显示进度
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("正在获取数据...")
        progress_bar.progress(20)
        
        # 获取数据
        results = analyzer.fetch_and_analyze(trade_date)
        progress_bar.progress(80)
        
        status_text.text("数据分析完成")
        progress_bar.progress(100)
        
        # 清除进度显示
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return results
    except Exception as e:
        st.error(f"数据获取失败: {str(e)}")
        return None

# 优化的期货行情数据获取
@st.cache_data(ttl=1800, show_spinner=False)
def get_futures_price_data_optimized(date_str):
    """优化的期货行情数据获取函数"""
    try:
        exchanges = [
            {"market": "DCE", "name": "大商所"},
            {"market": "CFFEX", "name": "中金所"},
            {"market": "CZCE", "name": "郑商所"},
            {"market": "SHFE", "name": "上期所"},
        ]
        
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, exchange in enumerate(exchanges):
            try:
                status_text.text(f"正在获取{exchange['name']}数据...")
                progress_bar.progress((i + 1) / len(exchanges))
                
                df = ak.get_futures_daily(start_date=date_str, end_date=date_str, market=exchange["market"])
                if not df.empty:
                    df['exchange'] = exchange["name"]
                    all_data.append(df)
                    
            except Exception as e:
                st.warning(f"获取{exchange['name']}数据失败: {str(e)}")
                continue
        
        # 清除进度显示
        progress_bar.empty()
        status_text.empty()
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"获取期货行情数据失败: {str(e)}")
        return pd.DataFrame()

# 简化的图表生成函数
@st.cache_data(ttl=3600)
def generate_charts_simple(results):
    """简化的图表生成函数"""
    charts = {}
    try:
        for contract_name, data in list(results.items())[:5]:  # 只生成前5个合约的图表
            if 'raw_data' in data:
                df = data['raw_data']
                fig = go.Figure()
                
                # 简化的持仓分布图
                fig.add_trace(go.Bar(
                    x=df['long_party_name'][:10],  # 只显示前10名
                    y=df['long_open_interest'][:10],
                    name='多单持仓',
                    marker_color='red'
                ))
                
                fig.add_trace(go.Bar(
                    x=df['short_party_name'][:10],
                    y=df['short_open_interest'][:10],
                    name='空单持仓',
                    marker_color='green'
                ))
                
                fig.update_layout(
                    title=f'{contract_name} 持仓分布',
                    height=400,
                    showlegend=True
                )
                charts[contract_name] = fig
    except Exception as e:
        st.warning(f"图表生成失败: {str(e)}")
    
    return charts

def analyze_term_structure_simple(df):
    """简化的期限结构分析"""
    try:
        if df.empty:
            return []
            
        required_columns = ['symbol', 'close', 'variety']
        if not all(col in df.columns for col in required_columns):
            return []
            
        results = []
        # 只分析前10个品种
        varieties = df['variety'].unique()[:10]
        
        for variety in varieties:
            variety_data = df[df['variety'] == variety].copy()
            variety_data = variety_data.sort_values('symbol')
            variety_data = variety_data[
                (variety_data['close'] > 0) & 
                (variety_data['close'].notna())
            ]
            
            if len(variety_data) < 2:
                continue
                
            contracts = variety_data['symbol'].tolist()
            closes = variety_data['close'].tolist()
            
            # 简化的期限结构判断
            if closes[0] > closes[-1]:
                structure = "back"
            elif closes[0] < closes[-1]:
                structure = "contango"
            else:
                structure = "flat"
                
            results.append((variety, structure, contracts, closes))
            
        return results
        
    except Exception as e:
        st.error(f"期限结构分析出错: {str(e)}")
        return []

def analyze_retail_reverse_strategy(df):
    """家人席位反向操作策略分析"""
    retail_seats = ["东方财富", "平安期货", "徽商期货"]
    
    try:
        seat_stats = {name: {'long_chg': 0, 'short_chg': 0, 'long_pos': 0, 'short_pos': 0} for name in retail_seats}
        
        for _, row in df.iterrows():
            if row['long_party_name'] in retail_seats:
                seat_stats[row['long_party_name']]['long_chg'] += row['long_open_interest_chg'] if pd.notna(row['long_open_interest_chg']) else 0
                seat_stats[row['long_party_name']]['long_pos'] += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
            if row['short_party_name'] in retail_seats:
                seat_stats[row['short_party_name']]['short_chg'] += row['short_open_interest_chg'] if pd.notna(row['short_open_interest_chg']) else 0
                seat_stats[row['short_party_name']]['short_pos'] += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0

        seat_details = []
        for seat, stats in seat_stats.items():
            if stats['long_chg'] != 0 or stats['short_chg'] != 0:
                seat_details.append({
                    'seat_name': seat, 
                    'long_chg': stats['long_chg'], 
                    'short_chg': stats['short_chg'],
                    'long_pos': stats['long_pos'],
                    'short_pos': stats['short_pos']
                })

        if not seat_details:
            return "中性", "未发现家人席位持仓变化", 0, []

        total_long_chg = sum([seat['long_chg'] for seat in seat_details])
        total_short_chg = sum([seat['short_chg'] for seat in seat_details])
        total_long_pos = sum([seat['long_pos'] for seat in seat_details])
        total_short_pos = sum([seat['short_pos'] for seat in seat_details])
        
        df_total_long = df['long_open_interest'].sum()
        df_total_short = df['short_open_interest'].sum()

        if total_long_chg > 0 and total_short_chg <= 0:
            retail_ratio = total_long_pos / df_total_long if df_total_long > 0 else 0
            return "看空", f"家人席位多单增加{total_long_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        elif total_short_chg > 0 and total_long_chg <= 0:
            retail_ratio = total_short_pos / df_total_short if df_total_short > 0 else 0
            return "看多", f"家人席位空单增加{total_short_chg}手，持仓占比{retail_ratio:.2%}", retail_ratio, seat_details
        else:
            return "中性", "家人席位持仓变化不符合策略要求", 0, seat_details
            
    except Exception as e:
        return "错误", f"数据处理错误：{str(e)}", 0, []

def main():
    st.title("期货持仓分析系统 (优化版)")
    
    # 添加系统状态检查
    with st.sidebar:
        st.header("系统状态")
        data_dir = ensure_data_directory()
        st.success(f"数据目录: {data_dir}")
        
        # 网络连接测试
        if st.button("测试网络连接"):
            try:
                import requests
                response = requests.get("https://www.baidu.com", timeout=5)
                if response.status_code == 200:
                    st.success("网络连接正常")
                else:
                    st.warning("网络连接异常")
            except:
                st.error("网络连接失败")
    
    # 日期选择
    today = datetime.now()
    default_date = today - timedelta(days=1)
    trade_date = st.date_input(
        "选择交易日期",
        value=default_date,
        max_value=today
    )
    
    trade_date_str = trade_date.strftime("%Y%m%d")
    
    # 添加快速模式选项
    quick_mode = st.checkbox("快速模式 (跳过期限结构分析)", value=True)
    
    # 创建分析按钮
    if st.button("开始分析", type="primary"):
        # 清除缓存
        st.cache_data.clear()
        
        # 显示分析进度
        with st.spinner("正在分析数据，请稍候..."):
            # 获取分析结果
            results = get_analysis_results_optimized(trade_date_str)
            
            if not results:
                st.error("获取数据失败，请检查网络连接或稍后重试")
                st.info("可能的原因：1. 网络连接问题 2. 选择的日期非交易日 3. 数据源暂时不可用")
                return
            
            st.success(f"成功获取 {len(results)} 个合约的数据")
            
            # 创建标签页
            if quick_mode:
                tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "家人席位反向操作策略", "策略总结"])
            else:
                tabs = st.tabs(["多空力量变化策略", "蜘蛛网策略", "家人席位反向操作策略", "期限结构分析", "策略总结"])
            
            all_strategy_signals = {}
            
            # 多空力量变化策略
            with tabs[0]:
                st.header("多空力量变化策略")
                st.info("策略原理：通过分析席位持仓的增减变化来判断市场趋势")
                
                strategy_name = "多空力量变化策略"
                long_signals = []
                short_signals = []
                
                for contract, data in results.items():
                    if strategy_name in data['strategies']:
                        strategy_data = data['strategies'][strategy_name]
                        if strategy_data['signal'] == '看多':
                            long_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                        elif strategy_data['signal'] == '看空':
                            short_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                
                all_strategy_signals[strategy_name] = {
                    'long': long_signals,
                    'short': short_signals
                }
                
                long_signals.sort(key=lambda x: x['strength'], reverse=True)
                short_signals.sort(key=lambda x: x['strength'], reverse=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("看多信号")
                    for signal in long_signals[:10]:  # 只显示前10个
                        st.markdown(f"""
                        <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                            <strong>{signal['contract']}</strong><br>
                            强度: {signal['strength']:.2f}<br>
                            {signal['reason']}
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    st.subheader("看空信号")
                    for signal in short_signals[:10]:  # 只显示前10个
                        st.markdown(f"""
                        <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                            <strong>{signal['contract']}</strong><br>
                            强度: {signal['strength']:.2f}<br>
                            {signal['reason']}
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown(f"""
                ### 统计信息
                - 看多信号品种数量：{len(long_signals)}
                - 看空信号品种数量：{len(short_signals)}
                - 中性信号品种数量：{len(results) - len(long_signals) - len(short_signals)}
                """)
            
            # 蜘蛛网策略
            with tabs[1]:
                st.header("蜘蛛网策略")
                st.info("策略原理：基于持仓分布的分化程度判断机构资金的参与情况")
                
                strategy_name = "蜘蛛网策略"
                long_signals = []
                short_signals = []
                
                for contract, data in results.items():
                    if strategy_name in data['strategies']:
                        strategy_data = data['strategies'][strategy_name]
                        if strategy_data['signal'] == '看多':
                            long_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                        elif strategy_data['signal'] == '看空':
                            short_signals.append({
                                'contract': contract,
                                'strength': strategy_data['strength'],
                                'reason': strategy_data['reason']
                            })
                
                all_strategy_signals[strategy_name] = {
                    'long': long_signals,
                    'short': short_signals
                }
                
                long_signals.sort(key=lambda x: x['strength'], reverse=True)
                short_signals.sort(key=lambda x: x['strength'], reverse=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("看多信号")
                    for signal in long_signals[:10]:
                        st.markdown(f"""
                        <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                            <strong>{signal['contract']}</strong><br>
                            强度: {signal['strength']:.2f}<br>
                            {signal['reason']}
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    st.subheader("看空信号")
                    for signal in short_signals[:10]:
                        st.markdown(f"""
                        <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                            <strong>{signal['contract']}</strong><br>
                            强度: {signal['strength']:.2f}<br>
                            {signal['reason']}
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown(f"""
                ### 统计信息
                - 看多信号品种数量：{len(long_signals)}
                - 看空信号品种数量：{len(short_signals)}
                - 中性信号品种数量：{len(results) - len(long_signals) - len(short_signals)}
                """)
            
            # 家人席位反向操作策略
            with tabs[2]:
                st.header("家人席位反向操作策略")
                st.info("策略原理：基于散户投资者往往在市场顶部做多、底部做空的特点，采用反向操作思路")
                
                retail_long_signals = []
                retail_short_signals = []
                
                for contract, data in results.items():
                    if 'raw_data' in data:
                        df = data['raw_data']
                        signal, reason, strength, seat_details = analyze_retail_reverse_strategy(df)
                        
                        if signal == '看多':
                            retail_long_signals.append({
                                'contract': contract,
                                'strength': strength,
                                'reason': reason,
                                'seat_details': seat_details
                            })
                        elif signal == '看空':
                            retail_short_signals.append({
                                'contract': contract,
                                'strength': strength,
                                'reason': reason,
                                'seat_details': seat_details
                            })
                
                retail_long_signals = sorted(retail_long_signals, key=lambda x: float(x.get('strength', 0)), reverse=True)
                retail_short_signals = sorted(retail_short_signals, key=lambda x: float(x.get('strength', 0)), reverse=True)
                
                all_strategy_signals['家人席位反向操作策略'] = {
                    'long': retail_long_signals,
                    'short': retail_short_signals
                }
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("看多信号")
                    if retail_long_signals:
                        for idx, signal in enumerate(retail_long_signals[:10], 1):
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{idx}. {signal['contract']}</strong><br>
                                强度: {signal['strength']:.4f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("无看多信号")
                
                with col2:
                    st.subheader("看空信号")
                    if retail_short_signals:
                        for idx, signal in enumerate(retail_short_signals[:10], 1):
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{idx}. {signal['contract']}</strong><br>
                                强度: {signal['strength']:.4f}<br>
                                {signal['reason']}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("无看空信号")
                
                st.markdown(f"""
                ### 统计信息
                - 看多信号品种数量：{len(retail_long_signals)}
                - 看空信号品种数量：{len(retail_short_signals)}
                - 总分析品种数量：{len(results)}
                """)
            
            # 期限结构分析（仅在非快速模式下显示）
            if not quick_mode:
                with tabs[3]:
                    st.header("期限结构分析")
                    st.info("策略原理：通过比较同一品种不同交割月份合约的价格关系，判断市场对该品种未来供需的预期")
                    
                    try:
                        with st.spinner("正在获取期货行情数据..."):
                            price_data = get_futures_price_data_optimized(trade_date_str)
                        
                        if not price_data.empty:
                            structure_results = analyze_term_structure_simple(price_data)
                            
                            if structure_results:
                                back_results = [r for r in structure_results if r[1] == "back"]
                                contango_results = [r for r in structure_results if r[1] == "contango"]
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.subheader("Back结构（近强远弱）")
                                    if back_results:
                                        for variety, structure, contracts, closes in back_results:
                                            st.markdown(f"**{variety}**")
                                            price_df = pd.DataFrame({
                                                '合约': contracts,
                                                '收盘价': closes
                                            })
                                            st.dataframe(price_df, use_container_width=True)
                                    else:
                                        st.info("无Back结构品种")
                                
                                with col2:
                                    st.subheader("Contango结构（近弱远强）")
                                    if contango_results:
                                        for variety, structure, contracts, closes in contango_results:
                                            st.markdown(f"**{variety}**")
                                            price_df = pd.DataFrame({
                                                '合约': contracts,
                                                '收盘价': closes
                                            })
                                            st.dataframe(price_df, use_container_width=True)
                                    else:
                                        st.info("无Contango结构品种")
                                
                                st.markdown(f"""
                                ### 统计信息
                                - Back结构品种数量: {len(back_results)}
                                - Contango结构品种数量: {len(contango_results)}
                                - 总品种数量: {len(structure_results)}
                                """)
                            else:
                                st.warning("没有找到可分析的期限结构数据")
                        else:
                            st.warning("无法获取期货行情数据")
                            
                    except Exception as e:
                        st.error(f"期限结构分析出错: {str(e)}")
            
            # 策略总结
            with tabs[-1]:
                st.header("策略总结")
                
                def extract_symbol(contract):
                    """从合约名称中提取品种代码"""
                    try:
                        if '_' in contract:
                            symbol_part = contract.split('_')[-1]
                        else:
                            symbol_part = contract
                        
                        symbol = ''.join(c for c in symbol_part if c.isalpha()).upper()
                        return symbol if symbol else None
                    except:
                        return None
                
                # 统计信号共振
                long_symbol_count = {}
                short_symbol_count = {}
                
                for strategy_name, signals in all_strategy_signals.items():
                    for signal in signals['long'][:10]:
                        symbol = extract_symbol(signal['contract'])
                        if symbol:
                            if symbol not in long_symbol_count:
                                long_symbol_count[symbol] = {'count': 0, 'strategies': []}
                            long_symbol_count[symbol]['count'] += 1
                            long_symbol_count[symbol]['strategies'].append(strategy_name)
                    
                    for signal in signals['short'][:10]:
                        symbol = extract_symbol(signal['contract'])
                        if symbol:
                            if symbol not in short_symbol_count:
                                short_symbol_count[symbol] = {'count': 0, 'strategies': []}
                            short_symbol_count[symbol]['count'] += 1
                            short_symbol_count[symbol]['strategies'].append(strategy_name)
                
                common_long_symbols = {symbol: info for symbol, info in long_symbol_count.items() if info['count'] >= 2}
                common_short_symbols = {symbol: info for symbol, info in short_symbol_count.items() if info['count'] >= 2}
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("信号共振看多品种")
                    if common_long_symbols:
                        sorted_long = sorted(common_long_symbols.items(), key=lambda x: x[1]['count'], reverse=True)
                        for symbol, info in sorted_long:
                            strategies_text = "、".join(info['strategies'])
                            st.markdown(f"""
                            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong> 
                                <span style='color: #666; font-size: 0.9em;'>({info['count']}个策略)</span><br>
                                <span style='font-size: 0.8em; color: #888;'>策略: {strategies_text}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有信号共振的看多品种")
                
                with col2:
                    st.subheader("信号共振看空品种")
                    if common_short_symbols:
                        sorted_short = sorted(common_short_symbols.items(), key=lambda x: x[1]['count'], reverse=True)
                        for symbol, info in sorted_short:
                            strategies_text = "、".join(info['strategies'])
                            st.markdown(f"""
                            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <strong>{symbol}</strong> 
                                <span style='color: #666; font-size: 0.9em;'>({info['count']}个策略)</span><br>
                                <span style='font-size: 0.8em; color: #888;'>策略: {strategies_text}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("没有信号共振的看空品种")
                
                st.markdown(f"""
                ### 信号共振统计
                - 看多信号共振品种数量：{len(common_long_symbols)}
                - 看空信号共振品种数量：{len(common_short_symbols)}
                - 总参与策略数量：{len(all_strategy_signals)}
                """)
            
            # 下载功能
            st.markdown("---")
            st.subheader("下载分析结果")
            
            # 准备下载数据
            summary_data = []
            for strategy_name, signals in all_strategy_signals.items():
                for signal in signals['long'][:10]:
                    summary_data.append({
                        '策略': strategy_name,
                        '信号类型': '看多',
                        '合约': signal['contract'],
                        '强度': signal['strength'],
                        '原因': signal['reason']
                    })
                for signal in signals['short'][:10]:
                    summary_data.append({
                        '策略': strategy_name,
                        '信号类型': '看空',
                        '合约': signal['contract'],
                        '强度': signal['strength'],
                        '原因': signal['reason']
                    })
            
            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='策略总结', index=False)
                
                # 共同信号
                common_signals = []
                for symbol in common_long_symbols:
                    common_signals.append({'品种': symbol, '信号类型': '共同看多'})
                for symbol in common_short_symbols:
                    common_signals.append({'品种': symbol, '信号类型': '共同看空'})
                pd.DataFrame(common_signals).to_excel(writer, sheet_name='共同信号', index=False)
            
            st.download_button(
                label="下载分析结果(Excel)",
                data=output.getvalue(),
                file_name=f"futures_analysis_{trade_date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main() 