import argparse
from pathlib import Path

import pandas as pd


def export_roll_by_date(var: str, start: str, end: str, cache_dir: Path) -> Path:
    import akshare as ak  # type: ignore
    df = ak.get_roll_yield_bar(type_method="date", var=var.upper(), start_day=start, end_day=end)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"roll_{var.upper()}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(df.head().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="导出期限结构/展期-按日期数据")
    p.add_argument("--var", required=True, help="品种变量，如 RB/TA/CU（注意是变量，不是合约symbol）")
    p.add_argument("--start", required=True, help="起始日期YYYYMMDD")
    p.add_argument("--end", required=True, help="结束日期YYYYMMDD")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_roll_by_date(args.var, args.start, args.end, Path(args.cache))


if __name__ == "__main__":
    main()


