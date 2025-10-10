import argparse
from pathlib import Path

import pandas as pd


def export_inventory(series: str, cache_dir: Path) -> Path:
    """示意：使用 ak.futures_inventory_em(symbol=中文名称) 导出库存序列。
    注意：series应与 ak 接口中文名称匹配，如 "苯乙烯"。
    """
    import akshare as ak  # type: ignore
    df = ak.futures_inventory_em(symbol=series)
    # 统一列名
    df = df.rename(columns={"日期": "date", "库存": "value"})
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"inventory_{series}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(df.head().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="导出库存序列到缓存")
    p.add_argument("--series", required=True, help="系列中文名称，如 苯乙烯")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_inventory(args.series, Path(args.cache))


if __name__ == "__main__":
    main()


