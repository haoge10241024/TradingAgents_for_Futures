from __future__ import annotations

from pathlib import Path
import pandas as pd


class PositioningProvider:
    """席位/拥挤度数据提供器：读取本地数据库。
    
    数据文件位置：qihuo/database/positioning/{SYMBOL}/positioning_data.csv
    """

    def __init__(self, database_dir: str = "qihuo/database/positioning") -> None:
        self.database_dir = Path(database_dir)

    def get_positioning(self, symbol: str, start: str | None = None, end: str | None = None, try_online: bool = False) -> pd.DataFrame:
        # 优先从数据库读取
        path = self.database_dir / symbol.upper() / "positioning_data.csv"
        if path.exists():
            df = pd.read_csv(path)
            # 过滤日期范围
            if "date" in df.columns and (start or end):
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                if start:
                    df = df[df["date"] >= pd.to_datetime(start)]
                if end:
                    df = df[df["date"] <= pd.to_datetime(end)]
            return df
        
        # 兼容旧的cache路径（向后兼容）
        cache_path = Path("qihuo/.data/cache") / f"positioning_{symbol.upper()}.csv"
        if cache_path.exists():
            return pd.read_csv(cache_path)
            
        # 在线构建入口：复用构建脚本逻辑较复杂，这里保持空，由脚本负责落盘（避免长耗时阻塞主流程）
        return pd.DataFrame()


