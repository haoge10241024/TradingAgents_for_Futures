import akshare as ak
import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class Strategy:
    """策略基类"""
    def __init__(self, name):
        self.name = name
    
    def analyze(self, data):
        """分析数据并返回结果"""
        raise NotImplementedError("子类必须实现analyze方法")

class PowerChangeStrategy(Strategy):
    """多空力量变化策略"""
    def __init__(self):
        super().__init__("多空力量变化策略")
    
    def analyze(self, data):
        """分析持仓变化并生成交易信号"""
        try:
            long_chg = float(data['total_long_chg'])
            short_chg = float(data['total_short_chg'])
            
            if long_chg > 0 and short_chg < 0:
                return "看多", f"多单增加{long_chg:.0f}手，空单减少{abs(short_chg):.0f}手", abs(long_chg)
            elif long_chg < 0 and short_chg > 0:
                return "看空", f"多单减少{abs(long_chg):.0f}手，空单增加{short_chg:.0f}手", abs(short_chg)
            else:
                return "中性", f"多单变化{long_chg:.0f}手，空单变化{short_chg:.0f}手", 0
        except Exception as e:
            print(f"分析持仓变化时出错：{str(e)}")
            return "错误", f"数据处理错误：{str(e)}", 0

class SpiderWebStrategy(Strategy):
    """蜘蛛网策略"""
    def __init__(self):
        super().__init__("蜘蛛网策略")
    
    def analyze(self, data):
        """分析蜘蛛网指标并生成交易信号"""
        try:
            df = data['raw_data']
            
            # 1. 找出同时存在于成交量、做多持仓、做空持仓的席位
            valid_seats = df[
                (df['vol'].notna()) &
                (df['long_open_interest'].notna()) & 
                (df['short_open_interest'].notna())
            ]
            
            if len(valid_seats) == 0:
                return "中性", "无有效席位数据", 0
            
            # 2. 计算知情度指标stat
            valid_seats['stat'] = (valid_seats['long_open_interest'] + valid_seats['short_open_interest']) / valid_seats['vol']
            
            # 3. 划分知情者和非知情者
            sorted_seats = valid_seats.sort_values('stat', ascending=False)
            cutoff_index = int(len(sorted_seats) * 0.4)
            its = sorted_seats.iloc[:cutoff_index]
            uts = sorted_seats.iloc[cutoff_index:]
            
            # 4. 计算ITS和UTS
            its['its'] = (its['long_open_interest'] - its['short_open_interest']) / (its['long_open_interest'] + its['short_open_interest'])
            uts['uts'] = (uts['long_open_interest'] - uts['short_open_interest']) / (uts['long_open_interest'] + uts['short_open_interest'])
            
            # 5. 计算MSD
            msd = its['its'].mean() - uts['uts'].mean()
            
            # 6. 生成信号
            if msd > 0:
                return "看多", f"MSD={msd:.4f}，知情者看多", abs(msd)
            elif msd < 0:
                return "看空", f"MSD={msd:.4f}，知情者看空", abs(msd)
            else:
                return "中性", f"MSD={msd:.4f}，无明显信号", 0
                
        except Exception as e:
            print(f"分析蜘蛛网指标时出错：{str(e)}")
            return "错误", f"数据处理错误：{str(e)}", 0

class RetailReverseStrategy(Strategy):
    """家人席位反向操作策略"""
    def __init__(self):
        super().__init__("家人席位反向操作策略")
        self.retail_seats = ["东方财富", "平安期货", "徽商期货"]
    
    def analyze(self, data):
        """分析家人席位持仓变化并生成反向交易信号"""
        try:
            df = data['raw_data']
            
            # 统计家人席位的多空变化（合并同一席位）
            seat_stats = {name: {'long_chg': 0, 'short_chg': 0} for name in self.retail_seats}
            for _, row in df.iterrows():
                if row['long_party_name'] in self.retail_seats:
                    seat_stats[row['long_party_name']]['long_chg'] += row['long_open_interest_chg'] if pd.notna(row['long_open_interest_chg']) else 0
                if row['short_party_name'] in self.retail_seats:
                    seat_stats[row['short_party_name']]['short_chg'] += row['short_open_interest_chg'] if pd.notna(row['short_open_interest_chg']) else 0

            # 只保留有变化的席位
            seat_details = []
            for seat, chg in seat_stats.items():
                if chg['long_chg'] != 0 or chg['short_chg'] != 0:
                    seat_details.append({'seat_name': seat, 'long_chg': chg['long_chg'], 'short_chg': chg['short_chg']})

            if not seat_details:
                return "中性", "未发现家人席位持仓变化", 0

            # 判断信号 - 家人席位多单增加时看空，空单增加时看多
            all_long_increase = all(seat['long_chg'] > 0 for seat in seat_details)
            all_short_increase = all(seat['short_chg'] > 0 for seat in seat_details)
            
            # 计算家人席位持仓占比
            retail_long_position = 0
            retail_short_position = 0
            
            for _, row in df.iterrows():
                if row['long_party_name'] in self.retail_seats:
                    retail_long_position += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
                if row['short_party_name'] in self.retail_seats:
                    retail_short_position += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0
            
            total_long = df['long_open_interest'].sum()
            total_short = df['short_open_interest'].sum()

            if all_long_increase:
                # 家人席位多单增加，看空
                retail_ratio = retail_long_position / total_long if total_long > 0 else 0
                return "看空", f"家人席位多单增加，持仓占比{retail_ratio:.2%}", retail_ratio
            elif all_short_increase:
                # 家人席位空单增加，看多
                retail_ratio = retail_short_position / total_short if total_short > 0 else 0
                return "看多", f"家人席位空单增加，持仓占比{retail_ratio:.2%}", retail_ratio
            else:
                return "中性", "家人席位持仓变化不符合策略要求", 0
                
        except Exception as e:
            print(f"分析家人席位时出错：{str(e)}")
            return "错误", f"数据处理错误：{str(e)}", 0

class FuturesDataFetcher:
    """期货数据获取类"""
    def __init__(self, save_dir):
        self.save_dir = save_dir
        self.exchange_config = {
            "郑商所": {
                "func": ak.get_czce_rank_table,
                "filename": "郑商所持仓.xlsx",
                "sheet_handler": lambda x: x
            },
            "中金所": {
                "func": ak.get_cffex_rank_table,
                "filename": "中金所持仓.xlsx",
                "sheet_handler": lambda x: x
            },
            "大商所": {
                "func": ak.futures_dce_position_rank,
                "filename": "大商所持仓.xlsx",
                "sheet_handler": lambda x: x
            },
            "上期所": {
                "func": ak.get_shfe_rank_table,
                "filename": "上期所持仓.xlsx",
                "sheet_handler": lambda x: x[:31].replace("/", "-").replace("*", "")
            },
            "广期所": {
                "func": ak.futures_gfex_position_rank,
                "filename": "广期所持仓.xlsx",
                "sheet_handler": lambda x: x[:31].replace("/", "-").replace("*", "")
            }
        }
        
        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)
    
    def fetch_data(self, trade_date):
        """
        获取指定日期的所有交易所持仓数据
        :param trade_date: 交易日期，格式：YYYYMMDD
        :return: 是否成功获取所有数据
        """
        success = True
        for exchange_name, config in self.exchange_config.items():
            try:
                # 获取数据
                data_dict = config["func"](date=trade_date)
                
                # 检查数据是否为空
                if not data_dict:
                    success = False
                    continue

                # 保存到Excel
                save_path = os.path.join(self.save_dir, config['filename'])
                with pd.ExcelWriter(save_path) as writer:
                    for raw_sheet_name, df in data_dict.items():
                        clean_name = config["sheet_handler"](raw_sheet_name)
                        df.to_excel(writer, sheet_name=clean_name, index=False)
                
            except Exception as e:
                success = False
        
        return success

class FuturesPositionAnalyzer:
    def __init__(self, data_dir):
        """
        初始化分析器
        :param data_dir: 数据文件所在目录
        """
        self.data_dir = data_dir
        self.data_fetcher = FuturesDataFetcher(data_dir)
        self.exchanges = {
            '郑商所': '郑商所持仓.xlsx',
            '中金所': '中金所持仓.xlsx',
            '大商所': '大商所持仓.xlsx',
            '上期所': '上期所持仓.xlsx',
            '广期所': '广期所持仓.xlsx'
        }
        self.strategies = [
            PowerChangeStrategy(),
            SpiderWebStrategy(),
            RetailReverseStrategy()
        ]
    
    def read_exchange_data(self, exchange_name):
        """
        读取指定交易所的持仓数据
        :param exchange_name: 交易所名称
        :return: 包含所有品种数据的字典
        """
        file_path = os.path.join(self.data_dir, self.exchanges[exchange_name])
        if not os.path.exists(file_path):
            return {}
            
        try:
            # 读取Excel文件中的所有sheet
            data_dict = pd.read_excel(file_path, sheet_name=None)
            return data_dict
        except Exception as e:
            return {}
    
    def process_position_data(self, df):
        """
        处理单个品种的持仓数据
        :param df: 单个品种的持仓数据DataFrame
        :return: 处理后的数据
        """
        try:
            # 自动适配郑商所的实际列名
            if 'g_party_n' in df.columns and 't_party_n' in df.columns:
                df = df.rename(columns={
                    'g_party_n': 'long_party_name',
                    'open_inten': 'long_open_interest',
                    'inten_intert': 'long_open_interest_chg',
                    't_party_n': 'short_party_name',
                    'open_inten.1': 'short_open_interest',
                    'inten_intert.1': 'short_open_interest_chg',
                    'vol': 'vol'
                })

            required_columns = ['long_party_name', 'long_open_interest', 'long_open_interest_chg',
                              'short_party_name', 'short_open_interest', 'short_open_interest_chg',
                              'vol']
            
            if not all(col in df.columns for col in required_columns):
                return None
                
            # 只保留前20名会员的数据
            df = df.head(20)
            
            # 确保数值列为数值类型
            numeric_columns = ['long_open_interest', 'long_open_interest_chg',
                             'short_open_interest', 'short_open_interest_chg',
                             'vol']
            for col in numeric_columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace(' ', '').replace({'nan': None})
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 计算多空单总量和变化量
            total_long = df['long_open_interest'].sum()
            total_short = df['short_open_interest'].sum()
            total_long_chg = df['long_open_interest_chg'].sum()
            total_short_chg = df['short_open_interest_chg'].sum()
            
            return {
                'total_long': total_long,
                'total_short': total_short,
                'total_long_chg': total_long_chg,
                'total_short_chg': total_short_chg,
                'raw_data': df
            }
        except Exception as e:
            return None
    
    def analyze_all_positions(self):
        """
        分析所有交易所的持仓数据
        :return: 分析结果字典
        """
        results = {}
        
        for exchange_name in self.exchanges.keys():
            exchange_data = self.read_exchange_data(exchange_name)
            
            if not exchange_data:
                continue
                
            for contract_name, df in exchange_data.items():
                processed_data = self.process_position_data(df)
                if processed_data:
                    # 对每个策略进行分析
                    strategy_results = {}
                    for strategy in self.strategies:
                        signal, reason, strength = strategy.analyze(processed_data)
                        strategy_results[strategy.name] = {
                            'signal': signal,
                            'reason': reason,
                            'strength': strength
                        }
                    # 存储结果时包含原始数据
                    results[f"{exchange_name}_{contract_name}"] = {
                        'strategies': strategy_results,
                        'raw_data': processed_data['raw_data']
                    }
        
        return results

    def fetch_and_analyze(self, trade_date):
        """
        获取数据并进行分析
        :param trade_date: 交易日期，格式：YYYYMMDD
        :return: 分析结果
        """
        # 获取数据
        if not self.data_fetcher.fetch_data(trade_date):
            return None
        
        # 分析数据
        results = self.analyze_all_positions()
        
        return results

def print_strategy_results(results, strategy_name):
    """打印特定策略的分析结果"""
    print(f"\n{strategy_name}分析结果：")
    print("="*80)
    
    # 分类整理数据
    long_signals = []
    short_signals = []
    
    for contract, data in results.items():
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
    
    # 按强度排序
    long_signals.sort(key=lambda x: x['strength'], reverse=True)
    short_signals.sort(key=lambda x: x['strength'], reverse=True)
    
    # 打印看多信号汇总
    print("\n看多信号品种：")
    print("-"*80)
    print(f"{'品种':<20} {'信号强度':>10} {'信号原因':<40}")
    print("-"*80)
    for signal in long_signals:
        print(f"{signal['contract']:<20} {signal['strength']:>10.2f} {signal['reason']:<40}")
    
    # 打印看空信号汇总
    print("\n看空信号品种：")
    print("-"*80)
    print(f"{'品种':<20} {'信号强度':>10} {'信号原因':<40}")
    print("-"*80)
    for signal in short_signals:
        print(f"{signal['contract']:<20} {signal['strength']:>10.2f} {signal['reason']:<40}")
    
    # 打印统计信息
    print("\n统计信息：")
    print(f"看多信号品种数量：{len(long_signals)}")
    print(f"看空信号品种数量：{len(short_signals)}")
    print(f"中性信号品种数量：{len(results) - len(long_signals) - len(short_signals)}")

def save_strategy_results_to_excel(results, strategy_name, data_dir):
    """
    将策略分析结果保存到Excel文件
    :param results: 分析结果
    :param strategy_name: 策略名称
    :param data_dir: 数据保存目录
    """
    try:
        # 创建Excel写入器
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy_name}_{timestamp}.xlsx"
        filepath = os.path.join(data_dir, filename)
        
        print(f"\n正在生成{strategy_name}的Excel报告...")
        print(f"文件将保存到：{filepath}")
        
        writer = pd.ExcelWriter(filepath, engine='openpyxl')
        
        # 准备汇总数据
        summary_data = []
        for contract, data in results.items():
            strategy_data = data['strategies'][strategy_name]
            summary_data.append({
                '合约': contract,
                '信号': strategy_data['signal'],
                '信号强度': strategy_data['strength'],
                '信号原因': strategy_data['reason']
            })
        
        # 创建汇总DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        # 按信号类型和强度排序
        summary_df = summary_df.sort_values(['信号', '信号强度'], ascending=[True, False])
        
        # 保存汇总表
        summary_df.to_excel(writer, sheet_name='策略汇总', index=False)
        print("已生成策略汇总页")
        
        # 为每个合约创建详细分析页
        for contract, data in results.items():
            print(f"正在处理{contract}的详细分析...")
            strategy_data = data['strategies'][strategy_name]
            df = data['raw_data']
            
            if strategy_name == "多空力量变化策略":
                # 多空力量变化策略的详细分析
                detail_data = {
                    '会员名称': df['long_party_name'],
                    '多单持仓': df['long_open_interest'],
                    '多单变化': df['long_open_interest_chg'],
                    '空单持仓': df['short_open_interest'],
                    '空单变化': df['short_open_interest_chg'],
                    '成交量': df['vol']
                }
                detail_df = pd.DataFrame(detail_data)
                
                # 添加汇总行
                summary_row = pd.DataFrame([{
                    '会员名称': '合计',
                    '多单持仓': df['long_open_interest'].sum(),
                    '多单变化': df['long_open_interest_chg'].sum(),
                    '空单持仓': df['short_open_interest'].sum(),
                    '空单变化': df['short_open_interest_chg'].sum(),
                    '成交量': df['vol'].sum()
                }])
                detail_df = pd.concat([detail_df, summary_row], ignore_index=True)
                
            else:  # 蜘蛛网策略
                # 计算知情度指标
                valid_seats = df[
                    (df['vol'].notna()) & 
                    (df['long_open_interest'].notna()) & 
                    (df['short_open_interest'].notna())
                ]
                valid_seats['stat'] = (valid_seats['long_open_interest'] + valid_seats['short_open_interest']) / valid_seats['vol']
                
                # 划分知情者和非知情者
                sorted_seats = valid_seats.sort_values('stat', ascending=False)
                cutoff_index = int(len(sorted_seats) * 0.4)
                its = sorted_seats.iloc[:cutoff_index]
                uts = sorted_seats.iloc[cutoff_index:]
                
                # 计算ITS和UTS
                its['its'] = (its['long_open_interest'] - its['short_open_interest']) / (its['long_open_interest'] + its['short_open_interest'])
                uts['uts'] = (uts['long_open_interest'] - uts['short_open_interest']) / (uts['long_open_interest'] + uts['short_open_interest'])
                
                # 合并知情者和非知情者数据
                its['类型'] = '知情者'
                uts['类型'] = '非知情者'
                detail_df = pd.concat([its, uts])
                
                # 添加MSD计算
                msd = its['its'].mean() - uts['uts'].mean()
                detail_df = detail_df[['类型', 'long_party_name', 'long_open_interest', 'short_open_interest', 'vol', 'stat', 'its', 'uts']]
                detail_df.columns = ['类型', '会员名称', '多单持仓', '空单持仓', '成交量', '知情度指标', 'ITS', 'UTS']
                
                # 添加MSD汇总行
                summary_row = pd.DataFrame([{
                    '类型': 'MSD',
                    '会员名称': f'MSD = {msd:.4f}',
                    '多单持仓': '',
                    '空单持仓': '',
                    '成交量': '',
                    '知情度指标': '',
                    'ITS': f'ITS均值 = {its["its"].mean():.4f}',
                    'UTS': f'UTS均值 = {uts["uts"].mean():.4f}'
                }])
                detail_df = pd.concat([detail_df, summary_row], ignore_index=True)
            
            # 保存详细分析页
            sheet_name = contract.replace('/', '_')[:31]  # Excel sheet名称长度限制
            detail_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"已生成{contract}的详细分析页")
        
        # 保存Excel文件
        writer.close()
        print(f"\n{strategy_name}分析结果已保存到：{filepath}")
        
    except Exception as e:
        print(f"保存Excel文件时出错：{str(e)}")
        raise

def generate_analysis_report_txt(results, data_dir):
    """
    生成分析结果txt报告，包括：
    1. 各策略做多/做空信号品种总结
    2. 大盘整体预测（基于蜘蛛网策略看多信号比例）
    3. 交易机会（两策略前10看多/看空信号交集）
    """
    power_name = "多空力量变化策略"
    spider_name = "蜘蛛网策略"
    txt_lines = []
    txt_lines.append("期货持仓分析自动报告\n")
    txt_lines.append("一、各策略信号总结\n")

    def get_signals(strategy_name):
        long_list, short_list = [], []
        for contract, data in results.items():
            s = data['strategies'][strategy_name]
            if s['signal'] == '看多':
                long_list.append((contract, s['strength'], s['reason']))
            elif s['signal'] == '看空':
                short_list.append((contract, s['strength'], s['reason']))
        long_list.sort(key=lambda x: x[1], reverse=True)
        short_list.sort(key=lambda x: x[1], reverse=True)
        return long_list, short_list

    # 1. 各策略做多/做空信号
    for strat in [power_name, spider_name]:
        txt_lines.append(f"【{strat}】\n")
        long_list, short_list = get_signals(strat)
        txt_lines.append(f"  做多信号品种（按强度排序，前10）：")
        for c, s, r in long_list[:10]:
            txt_lines.append(f"    {c}（强度{s}）：{r}")
        txt_lines.append(f"  做空信号品种（按强度排序，前10）：")
        for c, s, r in short_list[:10]:
            txt_lines.append(f"    {c}（强度{s}）：{r}")
        txt_lines.append("")

    # 2. 大盘整体预测（蜘蛛网策略看多信号比例）
    spider_long, spider_short = get_signals(spider_name)
    total = len(results)
    long_ratio = len(spider_long) / total if total else 0
    if long_ratio > 0.7:
        market_pred = "看多"
    elif long_ratio > 0.5:
        market_pred = "谨慎看多"
    elif long_ratio > 0.3:
        market_pred = "谨慎看空"
    else:
        market_pred = "看空"
    txt_lines.append("二、大盘整体预测\n")
    txt_lines.append(f"  蜘蛛网策略看多信号品种数：{len(spider_long)}，总品种数：{total}，比例：{long_ratio:.2%}")
    txt_lines.append(f"  预测结论：{market_pred}\n")

    # 3. 交易机会（两策略前10看多/看空信号交集）
    power_long, power_short = get_signals(power_name)
    spider_long, spider_short = get_signals(spider_name)
    set_power_long = set([c for c,_,_ in power_long[:10]])
    set_spider_long = set([c for c,_,_ in spider_long[:10]])
    set_power_short = set([c for c,_,_ in power_short[:10]])
    set_spider_short = set([c for c,_,_ in spider_short[:10]])
    long_opps = set_power_long & set_spider_long
    short_opps = set_power_short & set_spider_short
    txt_lines.append("三、交易机会\n")
    txt_lines.append("  做多机会（两策略前10交集）：")
    for c in long_opps:
        txt_lines.append(f"    {c}")
    txt_lines.append("  做空机会（两策略前10交集）：")
    for c in short_opps:
        txt_lines.append(f"    {c}")
    txt_lines.append("")

    # 写入txt文件
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = os.path.join(data_dir, f"分析报告_{ts}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_lines))
    print(f"分析报告已生成：{txt_path}")

def main():
    # 设置数据目录
    data_dir = r"D:\期货数据"
    
    # 创建分析器实例
    analyzer = FuturesPositionAnalyzer(data_dir)
    
    # 获取用户输入的日期
    while True:
        trade_date = input("\n请输入要分析的交易日期（格式：YYYYMMDD）：")
        if len(trade_date) == 8 and trade_date.isdigit():
            break
        print("日期格式错误，请重新输入！")
    
    # 获取数据并分析
    results = analyzer.fetch_and_analyze(trade_date)
    
    if not results:
        print("\n错误：没有获取到任何分析结果")
        return
    
    # 打印每个策略的结果
    for strategy in analyzer.strategies:
        print_strategy_results(results, strategy.name)

    # 保存每个策略的分析结果到Excel文件
    for strategy in analyzer.strategies:
        save_strategy_results_to_excel(results, strategy.name, data_dir)
    
    # 生成txt报告
    generate_analysis_report_txt(results, data_dir)

if __name__ == "__main__":
    main() 