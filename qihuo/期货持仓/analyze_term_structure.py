import akshare as ak
import pandas as pd
import os
import numpy as np
from datetime import datetime

def get_futures_data(start_date, end_date):
    """
    获取期货行情数据
    返回: 保存的文件路径列表
    """
    print("\n开始获取期货行情数据...")
    
    # 交易所列表
    exchanges = [
        {"market": "DCE", "name": "大商所"},
        {"market": "CFFEX", "name": "中金所"},
        {"market": "INE", "name": "上海国际能源交易中心"},
        {"market": "CZCE", "name": "郑商所"},
        {"market": "SHFE", "name": "上期所"},
        {"market": "GFEX", "name": "广期所"}
    ]
    
    # 创建保存目录
    save_dir = "."
    os.makedirs(save_dir, exist_ok=True)
    
    saved_files = []
    # 遍历每个交易所
    for exchange in exchanges:
        market = exchange["market"]
        name = exchange["name"]
        
        print(f"\n正在获取{name}数据...")
        try:
            # 获取数据
            df = ak.get_futures_daily(start_date=start_date, end_date=end_date, market=market)
            
            # 保存到 Excel 文件
            save_path = os.path.join(save_dir, f"{name}_{start_date}_{end_date}.xlsx")
            
            # 按品种分组并保存到不同 sheet
            with pd.ExcelWriter(save_path) as writer:
                grouped = df.groupby("variety")
                for variety, group in grouped:
                    # 处理 sheet 名称（移除非法字符）
                    clean_variety = str(variety).replace("/", "-").replace("*", "")
                    group.to_excel(writer, sheet_name=clean_variety, index=False)
            
            print(f"{name}的数据已保存至：{save_path}")
            saved_files.append(save_path)
            
        except Exception as e:
            print(f"获取{name}数据时出错: {str(e)}")
            continue
    
    print("\n所有交易所的数据获取完成！")
    return saved_files

def analyze_term_structure(file_path):
    """
    分析期货品种的期限结构
    返回: [(品种名称, 期限结构类型, 合约列表, 收盘价列表), ...]
    """
    try:
        print(f"\n正在处理文件: {file_path}")
        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 获取交易所名称（从文件名中提取）
        exchange_name = os.path.basename(file_path).split('_')[0]
        print(f"交易所名称: {exchange_name}")
        
        # 确保数据框包含必要的列
        required_columns = ['symbol', 'close', 'variety']
        if not all(col in df.columns for col in required_columns):
            print(f"警告: {file_path} 缺少必要的列: {required_columns}")
            print(f"实际列名: {df.columns.tolist()}")
            return []
            
        results = []
        # 按品种分组分析
        for variety in df['variety'].unique():
            print(f"\n分析品种: {variety}")
            # 获取该品种的数据
            variety_data = df[df['variety'] == variety].copy()
            
            # 按合约代码排序
            variety_data = variety_data.sort_values('symbol')
            
            # 获取合约列表和对应的收盘价
            contracts = variety_data['symbol'].tolist()
            closes = variety_data['close'].tolist()
            
            # 检查是否有足够的数据进行分析
            if len(contracts) < 2:
                print(f"警告: {variety} 合约数量不足，无法分析期限结构")
                continue
                
            # 分析期限结构
            # 修正：判断是否严格递减或递增
            is_decreasing = all(closes[i] > closes[i+1] for i in range(len(closes)-1))
            is_increasing = all(closes[i] < closes[i+1] for i in range(len(closes)-1))

            if is_decreasing:
                structure = "back"
            elif is_increasing:
                structure = "contango"
            else:
                structure = "flat"
                
            print(f"分析结果: {variety} 为 {structure} 结构")
            results.append((variety, structure, contracts, closes))
            
        return results
        
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def generate_report(all_results, start_date, end_date):
    """
    生成分析报告
    """
    output_file = f"term_structure_analysis_{start_date}_{end_date}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("期货品种期限结构分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"分析日期：{start_date} 至 {end_date}\n\n")
        
        # 按期限结构类型分类
        back_results = [r for r in all_results if r[1] == "back"]
        contango_results = [r for r in all_results if r[1] == "contango"]
        flat_results = [r for r in all_results if r[1] == "flat"]
        
        # 输出Back结构品种
        f.write("一、Back结构品种（近强远弱）\n")
        f.write("-" * 30 + "\n")
        if back_results:
            for variety, structure, contracts, closes in back_results:
                f.write(f"\n品种: {variety}\n")
                f.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    f.write(f"  {contract}: {close}\n")
                f.write("\n")
        else:
            f.write("无\n")
        
        # 输出Contango结构品种
        f.write("\n二、Contango结构品种（近弱远强）\n")
        f.write("-" * 30 + "\n")
        if contango_results:
            for variety, structure, contracts, closes in contango_results:
                f.write(f"\n品种: {variety}\n")
                f.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    f.write(f"  {contract}: {close}\n")
                f.write("\n")
        else:
            f.write("无\n")
            
        # 输出Flat结构品种
        f.write("\n三、Flat结构品种（近远月价格相近）\n")
        f.write("-" * 30 + "\n")
        if flat_results:
            for variety, structure, contracts, closes in flat_results:
                f.write(f"\n品种: {variety}\n")
                f.write("合约价格详情:\n")
                for contract, close in zip(contracts, closes):
                    f.write(f"  {contract}: {close}\n")
                f.write("\n")
        else:
            f.write("无\n")
            
        # 添加统计信息
        f.write("\n四、统计信息\n")
        f.write("-" * 30 + "\n")
        f.write(f"Back结构品种数量: {len(back_results)}\n")
        f.write(f"Contango结构品种数量: {len(contango_results)}\n")
        f.write(f"Flat结构品种数量: {len(flat_results)}\n")
        f.write(f"总品种数量: {len(all_results)}\n")
    
    print(f"\n分析报告已保存至：{output_file}")
    return output_file

def main():
    print("期货品种期限结构分析程序")
    print("=" * 50)
    
    # 获取用户输入的日期
    start_date = input("\n请输入开始日期（格式：YYYYMMDD）：")
    end_date = input("请输入结束日期（格式：YYYYMMDD）：")
    
    # 获取期货行情数据
    saved_files = get_futures_data(start_date, end_date)
    
    if not saved_files:
        print("未获取到任何数据，程序终止")
        return
    
    # 分析期限结构
    print("\n开始分析期限结构...")
    all_results = []
    for file in saved_files:
        results = analyze_term_structure(file)
        all_results.extend(results)
    
    # 生成分析报告
    report_file = generate_report(all_results, start_date, end_date)
    
    print("\n分析流程已完成！")
    print(f"分析报告保存在：{report_file}")

if __name__ == "__main__":
    main() 