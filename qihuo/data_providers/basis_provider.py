from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class BasisProvider:
    """基差数据提供器：优先读取本地数据库，无则尝试在线获取。
    
    数据文件位置：qihuo/database/basis/{SYMBOL}/basis_data.csv
    """

    def __init__(self, database_dir: str = "qihuo/database/basis") -> None:
        self.database_dir = Path(database_dir)

    def get_spot_price_daily(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None, try_online: bool = False) -> pd.DataFrame:
        """读取或获取基差日度数据。
        数据文件：qihuo/database/basis/{SYMBOL}/basis_data.csv
        """
        # 优先从数据库读取
        path = self.database_dir / symbol.upper() / "basis_data.csv"
        if path.exists():
            df = pd.read_csv(path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            # 简单区间过滤
            if start:
                df = df[df["date"] >= pd.to_datetime(start)]
            if end:
                df = df[df["date"] <= pd.to_datetime(end)]
            return df
        
        # 兼容旧的cache路径（向后兼容）
        cache_path = Path("qihuo/.data/cache") / f"basis_{symbol.upper()}.csv"
        if cache_path.exists():
            df = pd.read_csv(cache_path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            if start:
                df = df[df["date"] >= pd.to_datetime(start)]
            if end:
                df = df[df["date"] <= pd.to_datetime(end)]
            return df
        
        # 在线获取（可选）
        if try_online:
            try:
                import akshare as ak  # type: ignore

                # 规范日期
                s = start.replace('-', '') if start else None
                e = end.replace('-', '') if end else None

                def _fetch_chunk(sday: str, eday: str) -> pd.DataFrame:
                    d = ak.futures_spot_price_daily(start_day=sday, end_day=eday, vars_list=[symbol.upper()])
                    if "date" in d.columns:
                        d["date"] = pd.to_datetime(d["date"], errors="coerce")
                    return d

                out = None
                if s and e:
                    # 分段按月获取，提升稳定性
                    s_dt = pd.to_datetime(s)
                    e_dt = pd.to_datetime(e)
                    months = pd.date_range(s_dt.normalize().replace(day=1), e_dt.normalize().replace(day=1), freq='MS')
                    for i, m in enumerate(months):
                        sday = m.strftime('%Y%m%d')
                        if i + 1 < len(months):
                            eday_dt = (months[i+1] - pd.Timedelta(days=1))
                        else:
                            eday_dt = e_dt
                        eday = eday_dt.strftime('%Y%m%d')
                        try:
                            d = _fetch_chunk(sday, eday)
                            if out is None:
                                out = d
                            else:
                                out = pd.concat([out, d], ignore_index=True)
                        except Exception:
                            continue
                    if out is None:
                        out = pd.DataFrame()
                else:
                    # 直接一次性获取
                    out = _fetch_chunk(s or '20000101', e or pd.Timestamp.today().strftime('%Y%m%d'))

                # 若按月仍为空，回退更细粒度（14天步长）
                if out is None or len(out) == 0:
                    out = pd.DataFrame()
                    s_dt = pd.to_datetime(s or '20000101')
                    e_dt = pd.to_datetime(e or pd.Timestamp.today().strftime('%Y%m%d'))
                    cur = s_dt
                    while cur <= e_dt:
                        chunk_start = cur
                        chunk_end = min(cur + pd.Timedelta(days=13), e_dt)
                        try:
                            d = _fetch_chunk(chunk_start.strftime('%Y%m%d'), chunk_end.strftime('%Y%m%d'))
                            if d is not None and len(d) > 0:
                                out = pd.concat([out, d], ignore_index=True) if len(out) > 0 else d
                        except Exception:
                            pass
                        cur = chunk_end + pd.Timedelta(days=1)
                    if out is None or len(out) == 0:
                        return pd.DataFrame()

                # 去重与排序
                out = out.drop_duplicates().sort_values('date').reset_index(drop=True)

                # 写入缓存到数据库目录
                try:
                    target_dir = self.database_dir / symbol.upper()
                    target_dir.mkdir(parents=True, exist_ok=True)
                    out.to_csv(target_dir / "basis_data.csv", index=False, encoding="utf-8-sig")
                except Exception:
                    pass
                return out
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


