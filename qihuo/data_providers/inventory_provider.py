from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class InventoryProvider:
    """库存/仓单提供器：优先读缓存，无则回空。

    约定：
      - 库存/系列：inventory_{SERIES}.csv （列含 [date, value] 或 [日期, 库存]）
      - 仓单（示意，后续可扩展）：warehouse_{EXCHANGE}_{VAR}.csv
    """

    def __init__(self, cache_dir: str = "qihuo/.data/cache") -> None:
        self.cache_dir = Path(cache_dir)

    def get_inventory_series(self, series: str, try_online: bool = False) -> pd.DataFrame:
        path = self.cache_dir / f"inventory_{series}.csv"
        if path.exists():
            return pd.read_csv(path)
        if try_online:
            try:
                import akshare as ak  # type: ignore
                df = ak.futures_inventory_em(symbol=series)
                return df
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


