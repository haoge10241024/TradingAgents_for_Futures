from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class TermStructureProvider:
    """期限结构/展期 数据提供器：优先读取本地数据库，无则回空。

    数据文件位置：qihuo/database/term_structure/{VAR}/term_structure.csv
    """

    def __init__(self, database_dir: str = "qihuo/database/term_structure") -> None:
        self.database_dir = Path(database_dir)

    def get_roll_by_date(self, var: str, start: str | None = None, end: str | None = None, try_online: bool = False) -> pd.DataFrame:
        # 优先从数据库读取
        path = self.database_dir / var.upper() / "term_structure.csv"
        if path.exists():
            df = pd.read_csv(path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            # 过滤日期范围
            if start:
                df = df[df["date"] >= pd.to_datetime(start)]
            if end:
                df = df[df["date"] <= pd.to_datetime(end)]
            return df
        
        # 兼容旧的cache路径（向后兼容）
        cache_path = Path("qihuo/.data/cache") / f"roll_{var.upper()}.csv"
        if cache_path.exists():
            df = pd.read_csv(cache_path)
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


