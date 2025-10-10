from __future__ import annotations

import argparse
import time
import random
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict

import pandas as pd


DEFAULT_SYMBOLS: List[str] = [
    # 黑色、有色、化工、农产品等（期限结构分析：包含所有品种，不剔除）
    "RB","HC","I","J","JM","SS",
    "CU","AL","ZN","NI","SN","PB","AO",
    "AU","AG",
    "RU","NR","BU","FU","LU","PG","EB","EG","MA","TA","PX","PL",
    "PF","CY","PR",
    "SR","CF","AP","CJ","SP","P","Y","M","RM","OI","RS","PK","A","B",
    "C","CS","JD","LH",
    "FG","SA",
    "L","PP","V","UR",
    "SF","SM",
]


def _to_yyyymmdd(s: str) -> str:
    return pd.to_datetime(s).strftime("%Y%m%d")


def _fetch_roll(var: str, start: str, end: str, retries: int = 3, verbose: bool = True) -> pd.DataFrame:
    import akshare as ak  # type: ignore
    last_e: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            if verbose:
                print(f"[REQ] {var} {start}~{end}")
            df = ak.get_roll_yield_bar(type_method="date", var=var.upper(), start_day=start, end_day=end)
            return df
        except Exception as e:
            last_e = e
            time.sleep(random.uniform(0.4, 0.9))
    if verbose and last_e:
        print(f"[FAIL] {var}: {last_e}")
    return pd.DataFrame()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    # 标准化列名
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # 统一日期
    if "date" not in df.columns:
        # 常见备选名
        for c in ["日期", "trade_date", "datetime"]:
            if c in df.columns:
                df.rename(columns={c: "date"}, inplace=True)
                break
    if "date" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if df.empty:
        return pd.DataFrame()

    # 将可能包含百分号/逗号的数值列转成数值
    for c in list(df.columns):
        if c == "date":
            continue
        if df[c].dtype == object:
            s = pd.Series(df[c])
            s = s.astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False)
            df[c] = pd.to_numeric(s, errors="ignore")

    # 排序、去重
    df = df.sort_values("date").drop_duplicates().reset_index(drop=True)

    # 将 date 格式化为 YYYY-MM-DD
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def _save_csv(root: Path, sym: str, df_norm: pd.DataFrame) -> None:
    out_dir = root / sym
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "roll.csv"
    # 合并写入（按 date 去重）
    if out_csv.exists():
        try:
            old = pd.read_csv(out_csv)
        except Exception:
            old = pd.DataFrame()
        merged = pd.concat([old, df_norm], ignore_index=True)
    else:
        merged = df_norm
    if "date" in merged.columns:
        merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
    merged.to_csv(out_csv, index=False, encoding="utf-8-sig")


def build(root: Path, symbols: List[str], start_day: str, end_day: str, workers: int = 4) -> Dict[str, List[str]]:
    ok: List[str] = []
    fail: List[str] = []

    def task(sym: str) -> tuple[str, bool]:
        raw = _fetch_roll(sym, start_day, end_day, retries=3, verbose=True)
        norm = _normalize(raw)
        if norm is None or norm.empty:
            return sym, False
        _save_csv(root, sym, norm)
        return sym, True

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(task, s): s for s in symbols}
        for fut in as_completed(futures):
            sym, ok_flag = fut.result()
            if ok_flag:
                ok.append(sym)
            else:
                fail.append(sym)

    return {"ok": sorted(ok), "fail": sorted(fail)}


def main() -> None:
    warnings.filterwarnings("ignore", message=".*非交易日.*")

    p = argparse.ArgumentParser(description="构建期限结构/展期数据库 → qihuo/database/term_structure/{symbol}/roll.csv")
    p.add_argument("--symbols", default="all", help="逗号分隔品种或 all(默认)")
    p.add_argument("--start", required=False, help="起始 YYYYMMDD；不填按 --lookback-days 推算")
    p.add_argument("--end", required=False, help="结束 YYYYMMDD；缺省为今日")
    p.add_argument("--lookback-days", type=int, default=183, help="回溯天数，默认半年")
    p.add_argument("--workers", type=int, default=4, help="并发抓取数")
    args = p.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    db_root = base_dir / "database" / "term_structure"
    db_root.mkdir(parents=True, exist_ok=True)

    if args.end:
        end_day = _to_yyyymmdd(args.end)
    else:
        end_day = pd.Timestamp.today().strftime("%Y%m%d")
    if args.start:
        start_day = _to_yyyymmdd(args.start)
    else:
        start_day = (pd.to_datetime(end_day) - pd.Timedelta(days=int(args.lookback_days))).strftime("%Y%m%d")

    if args.symbols.lower() == "all":
        symbols = DEFAULT_SYMBOLS
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    print(f"[INFO] 期限结构 构建区间: {start_day} ~ {end_day}")
    print(f"[INFO] 品种数: {len(symbols)}")

    res = build(db_root, symbols, start_day, end_day, workers=args.workers)
    print(f"[SUMMARY] ok={len(res['ok'])}, fail={len(res['fail'])}")
    if res["fail"]:
        print("[FAIL]", res["fail"])


if __name__ == "__main__":
    main()


