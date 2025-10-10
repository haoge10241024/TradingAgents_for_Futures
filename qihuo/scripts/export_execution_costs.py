import argparse
from pathlib import Path

import pandas as pd


def export_comminfo(symbol: str, cache_dir: Path) -> Path:
    import akshare as ak  # type: ignore
    df = ak.futures_comm_info(symbol="所有")
    # 简单筛选包含 symbol 的行以落盘
    m = pd.Series([True] * len(df))
    if "合约代码" in df.columns:
        m = m & df["合约代码"].astype(str).str.contains(symbol, case=False, na=False)
    if "合约名称" in df.columns:
        m = m | df["合约名称"].astype(str).str.contains(symbol, case=False, na=False)
    sub = df[m].copy()
    if len(sub) == 0:
        sub = df.copy().head(20)  # 兜底，避免空
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"comminfo_{symbol.upper()}.csv"
    sub.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(sub.head().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="导出交易成本/约束到缓存")
    p.add_argument("--symbol", required=True, help="品种，如 RB/TA/CU")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_comminfo(args.symbol, Path(args.cache))


if __name__ == "__main__":
    main()


