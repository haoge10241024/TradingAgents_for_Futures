from __future__ import annotations

from pathlib import Path
import pandas as pd


class ExecutionCostsProvider:
    """交易成本/约束提供器：读取缓存 comminfo_{SYMBOL}.csv

    该缓存可由 ak.futures_comm_info(symbol="所有") 导出后，筛选出目标品种行写入。
    """

    def __init__(self, cache_dir: str = "qihuo/.data/cache") -> None:
        self.cache_dir = Path(cache_dir)

    def get_costs(self, symbol: str) -> pd.DataFrame:
        path = self.cache_dir / f"comminfo_{symbol.upper()}.csv"
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()


