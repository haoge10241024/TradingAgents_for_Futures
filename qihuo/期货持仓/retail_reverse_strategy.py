import pandas as pd
import os

class RetailReverseStrategy:
    """散户反向操作策略"""
    def __init__(self):
        self.retail_seats = ["东方财富", "平安期货", "徽商期货"]

    def analyze(self, df):
        try:
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
                return "中性", "未发现家人席位持仓变化", 0, None

            # 判断信号
            all_long_increase = all(seat['long_chg'] > 0 for seat in seat_details)
            all_short_increase = all(seat['short_chg'] > 0 for seat in seat_details)
            total_position = df['long_open_interest'].sum() + df['short_open_interest'].sum()
            retail_position = sum([abs(seat['long_chg']) + abs(seat['short_chg']) for seat in seat_details])
            position_ratio = retail_position / total_position if total_position > 0 else 0

            if all_long_increase:
                return "看空", f"家人席位多单增加，持仓占比{position_ratio:.2%}", position_ratio, seat_details
            elif all_short_increase:
                return "看多", f"家人席位空单增加，持仓占比{position_ratio:.2%}", position_ratio, seat_details
            return "中性", "家人席位持仓变化不符合策略要求", 0, seat_details
        except Exception as e:
            return "错误", f"数据处理错误：{str(e)}", 0, None

def process_position_data(df):
    # 适配郑商所格式
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
    # 不再限制前20名，遍历所有数据
    df = df.copy()
    numeric_columns = ['long_open_interest', 'long_open_interest_chg',
                     'short_open_interest', 'short_open_interest_chg',
                     'vol']
    for col in numeric_columns:
        df[col] = df[col].astype(str).str.replace(',', '').str.replace(' ', '').replace({'nan': None})
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def analyze_all_positions(data_dir):
    exchanges = {
        '郑商所': '郑商所持仓.xlsx',
        '中金所': '中金所持仓.xlsx',
        '大商所': '大商所持仓.xlsx',
        '上期所': '上期所持仓.xlsx',
        '广期所': '广期所持仓.xlsx'
    }
    strategy = RetailReverseStrategy()
    results = {}
    for exchange_name, file_name in exchanges.items():
        file_path = os.path.join(data_dir, file_name)
        if not os.path.exists(file_path):
            continue
        data_dict = pd.read_excel(file_path, sheet_name=None)
        for contract_name, df in data_dict.items():
            processed_df = process_position_data(df)
            if processed_df is not None:
                signal, reason, strength, seat_details = strategy.analyze(processed_df)
                # 计算家人席位持仓占比
                retail_long_position = 0
                retail_short_position = 0
                
                # 计算家人席位的实际持仓量
                for _, row in processed_df.iterrows():
                    if row['long_party_name'] in ["东方财富", "平安期货", "徽商期货"]:
                        retail_long_position += row['long_open_interest'] if pd.notna(row['long_open_interest']) else 0
                    if row['short_party_name'] in ["东方财富", "平安期货", "徽商期货"]:
                        retail_short_position += row['short_open_interest'] if pd.notna(row['short_open_interest']) else 0
                
                total_long = processed_df['long_open_interest'].sum()
                total_short = processed_df['short_open_interest'].sum()
                
                # 根据信号类型计算占比
                if signal == '看多':
                    # 看多信号是因为家人空单增加，显示家人空单占比
                    retail_ratio = retail_short_position / total_short if total_short > 0 else 0
                elif signal == '看空':
                    # 看空信号是因为家人多单增加，显示家人多单占比
                    retail_ratio = retail_long_position / total_long if total_long > 0 else 0
                else:
                    retail_ratio = 0
                results[f"{exchange_name}_{contract_name}"] = {
                    'signal': signal,
                    'reason': reason,
                    'strength': strength,
                    'seat_details': seat_details,
                    'raw_df': processed_df,
                    'retail_ratio': retail_ratio
                }
    return results

def print_results(results):
    print("\n散户反向操作策略分析结果：")
    print("="*80)
    long_signals = []
    short_signals = []
    for contract, data in results.items():
        if data['signal'] == '看多':
            long_signals.append({'contract': contract, 'strength': data['strength'], 'reason': data['reason'], 'seat_details': data['seat_details']})
        elif data['signal'] == '看空':
            short_signals.append({'contract': contract, 'strength': data['strength'], 'reason': data['reason'], 'seat_details': data['seat_details']})
    long_signals.sort(key=lambda x: x['strength'], reverse=True)
    short_signals.sort(key=lambda x: x['strength'], reverse=True)
    print("\n看多信号品种：")
    print("-"*80)
    print(f"{'品种':<20} {'信号强度':>10} {'信号原因':<40}")
    print("-"*80)
    for signal in long_signals:
        print(f"{signal['contract']:<20} {signal['strength']:>10.2f} {signal['reason']:<40}")
        if signal['seat_details']:
            print("家人席位持仓变化情况：")
            for seat in signal['seat_details']:
                print(f"  {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
        # 新增：输出原始席位明细
        raw_df = results[signal['contract']]['raw_df']
        print("席位明细：")
        print(raw_df[['long_party_name', 'long_open_interest', 'long_open_interest_chg',
                      'short_party_name', 'short_open_interest', 'short_open_interest_chg', 'vol']].to_string(index=False))
    print("\n看空信号品种：")
    print("-"*80)
    print(f"{'品种':<20} {'信号强度':>10} {'信号原因':<40}")
    print("-"*80)
    for signal in short_signals:
        print(f"{signal['contract']:<20} {signal['strength']:>10.2f} {signal['reason']:<40}")
        if signal['seat_details']:
            print("家人席位持仓变化情况：")
            for seat in signal['seat_details']:
                print(f"  {seat['seat_name']}: 多单变化{seat['long_chg']}手, 空单变化{seat['short_chg']}手")
        # 新增：输出原始席位明细
        raw_df = results[signal['contract']]['raw_df']
        print("席位明细：")
        print(raw_df[['long_party_name', 'long_open_interest', 'long_open_interest_chg',
                      'short_party_name', 'short_open_interest', 'short_open_interest_chg', 'vol']].to_string(index=False))
    print("\n统计信息：")
    print(f"看多信号品种数量：{len(long_signals)}")
    print(f"看空信号品种数量：{len(short_signals)}")
    print(f"中性/无信号品种数量：{len(results) - len(long_signals) - len(short_signals)}")

if __name__ == "__main__":
    data_dir = r"D:\期货数据"  # 修改为你的数据目录
    results = analyze_all_positions(data_dir)
    print_results(results) 