from __future__ import annotations

from pathlib import Path
import pandas as pd


class PositioningProvider:
    """席位/拥挤度数据提供器：读取缓存 positioning_{SYMBOL}.csv。

    文件应为日度聚合的指标表，至少含 date 与 long_top20/short_top20/total_oi 之一。
    """

    def __init__(self, cache_dir: str = "qihuo/.data/cache") -> None:
        self.cache_dir = Path(cache_dir)

    def get_positioning(self, symbol: str, start: str | None = None, end: str | None = None, try_online: bool = False) -> pd.DataFrame:
        path = self.cache_dir / f"positioning_{symbol.upper()}.csv"
        if path.exists():
            return pd.read_csv(path)
        # 在线构建入口：复用构建脚本逻辑较复杂，这里保持空，由脚本负责落盘（避免长耗时阻塞主流程）
        return pd.DataFrame()


