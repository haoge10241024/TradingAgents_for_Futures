import argparse
import time
from datetime import datetime
from pathlib import Path

import pandas as pd


def fetch_dominant_contract(symbol: str, start: str, end: str) -> pd.DataFrame:
    import akshare as ak  # type: ignore
    df = ak.futures_spot_price_daily(start_day=start, end_day=end, vars_list=[symbol.upper()])
    # 仅保留必要列并规范
    keep = [
        "date",
        "symbol",
        "dominant_contract",
    ]
    for c in keep:
        if c not in df.columns:
            df[c] = pd.NA
    out = df[keep].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out


def fetch_top20_for_contract(contract: str, date_str_compact: str) -> tuple[int, int]:
    """返回 (long_top20, short_top20)。date_str_compact: YYYYMMDD
    使用 ak.futures_hold_pos_sina。
    """
    import akshare as ak  # type: ignore
    total_long = 0
    total_short = 0
    try:
        dfl = ak.futures_hold_pos_sina(symbol="多单持仓", contract=contract, date=date_str_compact)
        dfs = ak.futures_hold_pos_sina(symbol="空单持仓", contract=contract, date=date_str_compact)
    except Exception:
        return 0, 0
    try:
        if dfl is not None and len(dfl) > 0:
            total_long = pd.to_numeric(dfl.iloc[:20][dfl.columns[2]], errors="coerce").fillna(0).astype(int).sum()
        if dfs is not None and len(dfs) > 0:
            total_short = pd.to_numeric(dfs.iloc[:20][dfs.columns[2]], errors="coerce").fillna(0).astype(int).sum()
    except Exception:
        pass
    return int(total_long), int(total_short)


def build_positioning(symbol: str, start: str, end: str, cache_dir: Path, sleep_sec: float = 0.6) -> Path:
    dom_df = fetch_dominant_contract(symbol, start, end)
    rows = []
    for _, r in dom_df.iterrows():
        dt = r["date"]
        dstr = dt.strftime("%Y%m%d")
        contract = str(r.get("dominant_contract") or "").strip()
        if not contract:
            continue
        # 调用席位接口
        l20, s20 = fetch_top20_for_contract(contract=contract, date_str_compact=dstr)
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "long_top20": l20,
            "short_top20": s20,
        })
        time.sleep(sleep_sec)

    df = pd.DataFrame(rows)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"positioning_{symbol.upper()}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"保存: {path}")
    print(df.tail().to_string())
    return path


def main() -> None:
    p = argparse.ArgumentParser(description="从AkShare构建席位/拥挤度缓存（基于主力合约Top20席位）")
    p.add_argument("--symbol", required=True, help="品种，如 RB/TA/CU")
    p.add_argument("--start", required=True, help="YYYYMMDD")
    p.add_argument("--end", required=True, help="YYYYMMDD")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    p.add_argument("--sleep", type=float, default=0.6, help="每日请求间隔(秒)，避免限流")
    args = p.parse_args()

    build_positioning(args.symbol, args.start, args.end, Path(args.cache), sleep_sec=args.sleep)


if __name__ == "__main__":
    main()


