import argparse
from pathlib import Path

import pandas as pd


def export_news(symbol_cn: str, cache_dir: Path) -> Path:
    import akshare as ak  # type: ignore
    df = ak.futures_news_shmet(symbol=symbol_cn)
    df = df.rename(columns={"发布时间": "time", "内容": "content"})
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"news_{symbol_cn}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(df.head().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="导出新闻到缓存，来源SHMET")
    p.add_argument("--symbol-cn", required=True, help="中文品种，如 铜/铝/锌/镍/锡/贵金属 等")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = p.parse_args()

    export_news(args.symbol_cn, Path(args.cache))


if __name__ == "__main__":
    main()


