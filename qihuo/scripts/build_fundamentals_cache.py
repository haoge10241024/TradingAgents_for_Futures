import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


def month_chunks(start: str, end: str) -> List[Tuple[str, str]]:
    """Return list of [YYYYMMDD, YYYYMMDD] month chunks covering [start, end]."""
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    chunks: List[Tuple[str, str]] = []
    cur = datetime(s.year, s.month, 1)
    while cur <= e:
        # month end
        if cur.month == 12:
            nxt = datetime(cur.year + 1, 1, 1)
        else:
            nxt = datetime(cur.year, cur.month + 1, 1)
        chunk_start = max(cur, s)
        chunk_end = min(e, nxt - timedelta(days=1))
        chunks.append((chunk_start.strftime("%Y%m%d"), chunk_end.strftime("%Y%m%d")))
        cur = nxt
    return chunks


def safe_merge_cache(path: Path, df_new: pd.DataFrame, date_cols: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            df_old = pd.read_csv(path)
        except Exception:
            df_old = pd.DataFrame()
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    # try de-dup by date columns if present
    key_cols = [c for c in date_cols if c in df_all.columns]
    if key_cols:
        for c in key_cols:
            df_all[c] = pd.to_datetime(df_all[c], errors="coerce")
        df_all = df_all.drop_duplicates(subset=key_cols)
        df_all = df_all.sort_values(by=key_cols)
    else:
        df_all = df_all.drop_duplicates()
    df_all.to_csv(path, index=False, encoding="utf-8-sig")


def fetch_basis_symbol(symbol: str, start: str, end: str, cache_dir: Path, retries: int = 2) -> Optional[Path]:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        print(f"[basis] akshare 导入失败: {symbol}")
        return None
    out = cache_dir / f"basis_{symbol.upper()}.csv"
    all_parts: List[pd.DataFrame] = []
    for a, b in month_chunks(start, end):
        for k in range(retries + 1):
            try:
                df = ak.futures_spot_price_daily(start_day=a, end_day=b, vars_list=[symbol.upper()])
                if df is not None and len(df) > 0:
                    all_parts.append(df)
                break
            except Exception as e:
                if k >= retries:
                    print(f"[basis] {symbol} {a}-{b} 失败: {e}")
    if not all_parts:
        return None
    df_new = pd.concat(all_parts, ignore_index=True)
    safe_merge_cache(out, df_new, date_cols=["日期", "date", "时间"])  # 尽可能识别日期列
    print(f"[basis] 保存: {out}")
    return out


def fetch_roll_var(variety: str, start: str, end: str, cache_dir: Path, retries: int = 2) -> Optional[Path]:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        print(f"[roll] akshare 导入失败: {variety}")
        return None
    out = cache_dir / f"roll_{variety.upper()}.csv"
    all_parts: List[pd.DataFrame] = []
    for a, b in month_chunks(start, end):
        for k in range(retries + 1):
            try:
                df = ak.get_roll_yield_bar(type_method="date", var=variety.upper(), start_day=a, end_day=b)
                if df is not None and len(df) > 0:
                    all_parts.append(df)
                break
            except Exception as e:
                if k >= retries:
                    print(f"[roll] {variety} {a}-{b} 失败: {e}")
    if not all_parts:
        return None
    df_new = pd.concat(all_parts, ignore_index=True)
    safe_merge_cache(out, df_new, date_cols=["date", "日期", "时间"])  # 统一按日期去重
    print(f"[roll] 保存: {out}")
    return out


def fetch_inventory_series(series_cn: str, cache_dir: Path, retries: int = 1) -> Optional[Path]:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        print(f"[inventory] akshare 导入失败: {series_cn}")
        return None
    out = cache_dir / f"inventory_{series_cn}.csv"
    for k in range(retries + 1):
        try:
            df = ak.futures_inventory_em(symbol=series_cn)
            if df is None or len(df) == 0:
                return None
            df = df.rename(columns={"日期": "date", "库存": "value"})
            safe_merge_cache(out, df, date_cols=["date", "日期"])  # 按日期去重
            print(f"[inventory] 保存: {out}")
            return out
        except Exception as e:
            if k >= retries:
                print(f"[inventory] {series_cn} 失败: {e}")
    return None


DEFAULT_SYMBOLS: List[str] = [
    # 黑色
    "RB", "HC", "I", "J", "JM", "ZC",
    # 有色
    "CU", "AL", "ZN", "NI", "SN", "PB", "SS", "AU", "AG",
    # 能化
    "SC", "FU", "BU", "LU", "RU", "NR", "MA", "EG", "EB", "L", "PP", "V",
    # 玻璃纯碱纸浆
    "FG", "SA", "SP",
    # 农产品
    "SR", "CF", "AP", "RM", "M", "Y", "P", "C", "CS", "JD",
]


DEFAULT_INVENTORY_MAP: Dict[str, List[str]] = {
    # 示例映射（可按需扩充/修正为数据源实际可用名称）
    "RB": ["螺纹钢"],
    "HC": ["热轧卷板"],
    "CU": ["电解铜"],
    "AL": ["电解铝"],
    "ZN": ["锌锭"],
    "NI": ["电解镍"],
    "SN": ["锡锭"],
    "RU": ["天然橡胶"]
}


def parse_symbols(arg: str) -> List[str]:
    if arg.lower() == "all":
        return DEFAULT_SYMBOLS
    return [s.strip().upper() for s in arg.split(",") if s.strip()]


def main() -> None:
    p = argparse.ArgumentParser(description="一键构建/回补 基本面缓存：基差/期限结构/库存")
    p.add_argument("--symbols", default="all", help="品种列表，如 RB,HC 或 all")
    p.add_argument("--start", default="20100101", help="开始日期YYYYMMDD，用于基差/期限结构")
    p.add_argument("--end", default=datetime.now().strftime("%Y%m%d"), help="结束日期YYYYMMDD")
    p.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    p.add_argument("--include", default="basis,roll,inventory", help="包含模块，逗号分隔：basis,roll,inventory")
    p.add_argument("--workers", type=int, default=4, help="并发线程数")
    p.add_argument("--inventory-only", action="store_true", help="仅根据内置映射抓取库存")
    args = p.parse_args()

    symbols = parse_symbols(args.symbols)
    cache_dir = Path(args.cache)
    include = {t.strip() for t in args.include.split(",")}

    tasks: List[Tuple[str, str]] = []

    if not args.inventory_only and ("basis" in include):
        for s in symbols:
            tasks.append(("basis", s))

    if not args.inventory_only and ("roll" in include):
        for s in symbols:
            tasks.append(("roll", s))

    if "inventory" in include:
        for s in symbols:
            for series_cn in DEFAULT_INVENTORY_MAP.get(s, []):
                tasks.append(("inventory", series_cn))

    print(f"计划任务数: {len(tasks)} (symbols={len(symbols)})")

    def runner(job: Tuple[str, str]) -> Tuple[str, str, Optional[Path]]:
        kind, key = job
        try:
            if kind == "basis":
                return kind, key, fetch_basis_symbol(key, args.start, args.end, cache_dir)
            if kind == "roll":
                return kind, key, fetch_roll_var(key, args.start, args.end, cache_dir)
            if kind == "inventory":
                return kind, key, fetch_inventory_series(key, cache_dir)
        except Exception as e:
            print(f"[runner] {kind}:{key} 异常: {e}")
        return kind, key, None

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(runner, t) for t in tasks]
        for fu in as_completed(futs):
            kind, key, path = fu.result()
            if path is None:
                print(f"完成: {kind}:{key} -> 失败/无数据")
            else:
                print(f"完成: {kind}:{key} -> {path}")


if __name__ == "__main__":
    main()


