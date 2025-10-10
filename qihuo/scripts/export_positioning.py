import argparse
from pathlib import Path

import pandas as pd


def export_positioning(symbol: str, cache_dir: Path) -> Path:
    """示意脚本：用户可将交易所席位明细（多/空/成交）聚合成长表后落盘。
    由于各交易所接口字段不一，这里仅提供落盘格式要求：
      必须列：date, long_top20, short_top20
      可选列：total_oi, net_long_top20
    你可以先从 ak.get_*_rank_table / futures_hold_pos_sina 等接口整理后再写入。
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"positioning_{symbol.upper()}.csv"
    # 示例空表头，便于你粘贴数据
    df = pd.DataFrame(columns=["date", "long_top20", "short_top20", "total_oi", "net_long_top20"]) 
    if not path.exists():
        df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"请在 {path} 中填充或替换为你的聚合结果（CSV列: date,long_top20,short_top20,total_oi,net_long_top20）")
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="初始化席位/拥挤度缓存CSV文件，供用户粘贴聚合结果")
    p.add_argument("--symbol", required=True, help="品种，如 RB/TA/CU")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_positioning(args.symbol, Path(args.cache))


if __name__ == "__main__":
    main()


