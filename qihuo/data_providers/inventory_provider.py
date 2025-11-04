from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class InventoryProvider:
    """库存/仓单提供器：优先读取本地数据库，无则回空。

    数据文件位置：qihuo/database/inventory/{SERIES}/inventory.csv
    """

    def __init__(self, database_dir: str = "qihuo/database/inventory") -> None:
        self.database_dir = Path(database_dir)

    def get_inventory_series(self, series: str, try_online: bool = False) -> pd.DataFrame:
        # 优先从数据库读取（按品种代码）
        path = self.database_dir / series.upper() / "inventory.csv"
        if path.exists():
            return pd.read_csv(path)
        
        # 兼容旧的cache路径（向后兼容）
        cache_path = Path("qihuo/.data/cache") / f"inventory_{series}.csv"
        if cache_path.exists():
            return pd.read_csv(cache_path)
            
        if try_online:
            try:
                import akshare as ak  # type: ignore
                df = ak.futures_inventory_em(symbol=series)
                return df
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


