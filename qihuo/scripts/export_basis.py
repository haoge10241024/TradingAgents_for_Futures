import argparse
from pathlib import Path

import pandas as pd


def export_basis(symbol: str, start: str, end: str, cache_dir: Path) -> Path:
    import akshare as ak  # type: ignore
    df = ak.futures_spot_price_daily(start_day=start, end_day=end, vars_list=[symbol.upper()])
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"basis_{symbol.upper()}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(df.head().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="导出基差日度数据到本地缓存")
    p.add_argument("--symbol", required=True, help="品种符号，例如 RB/TA/CU")
    p.add_argument("--start", required=True, help="起始日期YYYYMMDD")
    p.add_argument("--end", required=True, help="结束日期YYYYMMDD")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_basis(args.symbol, args.start, args.end, Path(args.cache))


if __name__ == "__main__":
    main()


