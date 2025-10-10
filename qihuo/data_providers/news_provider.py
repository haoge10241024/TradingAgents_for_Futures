from __future__ import annotations

from pathlib import Path
import pandas as pd


class NewsProvider:
    """新闻提供器：读取缓存 news_{SYMBOL}.csv，或按专题 news_{TOPIC}.csv。

    建议列：time, content
    可由 ak.futures_news_shmet(symbol=中文) 导出后重命名。
    """

    def __init__(self, cache_dir: str = "qihuo/.data/cache") -> None:
        self.cache_dir = Path(cache_dir)

    def get_news(self, key: str) -> pd.DataFrame:
        p = self.cache_dir / f"news_{key}.csv"
        if p.exists():
            return pd.read_csv(p)
        return pd.DataFrame()


