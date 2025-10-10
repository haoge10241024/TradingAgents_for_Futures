from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class TermStructureProvider:
    """期限结构/展期 数据提供器：优先读取缓存，无则回空。

    缓存文件约定：roll_{VAR}.csv
    内容建议为 get_roll_yield_bar(type_method="date", var=VAR, start_day, end_day) 的汇总表。
    """

    def __init__(self, cache_dir: str = "qihuo/.data/cache") -> None:
        self.cache_dir = Path(cache_dir)

    def get_roll_by_date(self, var: str, start: str | None = None, end: str | None = None, try_online: bool = False) -> pd.DataFrame:
        path = self.cache_dir / f"roll_{var.upper()}.csv"
        if path.exists():
            df = pd.read_csv(path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return df
        if try_online:
            try:
                import akshare as ak  # type: ignore
                df = ak.get_roll_yield_bar(type_method="date", var=var.upper(), start_day=start, end_day=end)
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                return df
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


