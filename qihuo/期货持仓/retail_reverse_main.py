import os
import akshare as ak
import pandas as pd
from datetime import datetime
from retail_reverse_strategy import analyze_all_positions, print_results

def fetch_futures_data(trade_date, save_dir):
    """
    按日期自动下载五大交易所持仓数据，保存为Excel文件
    """
    exchanges = {
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
    os.makedirs(save_dir, exist_ok=True)
    for exchange_name, config in exchanges.items():
        try:
            data_dict = config["func"](date=trade_date)
            if not data_dict:
                print(f"{exchange_name} 没有获取到数据")
                continue
            save_path = os.path.join(save_dir, config['filename'])
            with pd.ExcelWriter(save_path) as writer:
                for raw_sheet_name, df in data_dict.items():
                    clean_name = config["sheet_handler"](raw_sheet_name)
                    df.to_excel(writer, sheet_name=clean_name, index=False)
            print(f"{exchange_name} 数据已保存到 {save_path}")
        except Exception as e:
            print(f"{exchange_name} 数据获取失败: {e}")

def main():
    save_dir = r"D:\期货数据"
    while True:
        trade_date = input("请输入要分析的交易日期（格式：YYYYMMDD）：")
        if len(trade_date) == 8 and trade_date.isdigit():
            break
        print("日期格式错误，请重新输入！")
    print(f"开始下载{trade_date}的期货持仓数据...")
    fetch_futures_data(trade_date, save_dir)
    print("\n开始分析家人席位反向策略...")
    results = analyze_all_positions(save_dir)
    print_results(results)

if __name__ == "__main__":
    main() 