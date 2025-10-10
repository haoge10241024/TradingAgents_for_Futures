from __future__ import annotations

import argparse
import sys
import time
import random
import warnings
from pathlib import Path
from typing import List, Dict

import pandas as pd


def _to_yyyymmdd(s: str) -> str:
    return pd.to_datetime(s).strftime("%Y%m%d")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    # 标准 ak.futures_spot_price_daily 字段直接映射
    cols = [
        "date",
        "symbol",
        "spot_price",
        "near_contract",
        "near_contract_price",
        "dominant_contract",
        "dominant_contract_price",
        "near_basis",
        "dom_basis",
        "near_basis_rate",
        "dom_basis_rate",
    ]

    # 容错：统一小写比对
    lower_map: Dict[str, str] = {c.lower(): c for c in df.columns}
    need = {c: lower_map.get(c.lower()) for c in cols}

    # 必须字段
    must = ["date", "symbol"]
    for m in must:
        if need.get(m) is None:
            return pd.DataFrame()

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[need["date"]], errors="coerce")
    out["symbol"] = df[need["symbol"]].astype(str).str.upper()

    def to_num(s):
        return pd.to_numeric(
            pd.Series(s)
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", "", regex=False),
            errors="coerce",
        )

    def fill_col(dst: str, src: str | None, numeric: bool = True, default=""):
        if src is None:
            out[dst] = pd.NA if numeric else default
        else:
            out[dst] = to_num(df[src]) if numeric else df[src]

    fill_col("spot_price", need.get("spot_price"), numeric=True)
    fill_col("near_contract", need.get("near_contract"), numeric=False, default="")
    fill_col("near_contract_price", need.get("near_contract_price"), numeric=True)
    fill_col("dominant_contract", need.get("dominant_contract"), numeric=False, default="")
    fill_col("dominant_contract_price", need.get("dominant_contract_price"), numeric=True)
    fill_col("near_basis", need.get("near_basis"), numeric=True)
    fill_col("dom_basis", need.get("dom_basis"), numeric=True)
    fill_col("near_basis_rate", need.get("near_basis_rate"), numeric=True)
    fill_col("dom_basis_rate", need.get("dom_basis_rate"), numeric=True)

    out = out.dropna(subset=["date"]).copy()

    # 仅保留至少一个数值列非空的行
    num_cols = [
        "spot_price",
        "near_contract_price",
        "dominant_contract_price",
        "near_basis",
        "dom_basis",
        "near_basis_rate",
        "dom_basis_rate",
    ]
    if not out.empty:
        non_empty_mask = (~pd.isna(out[num_cols])).any(axis=1)
        out = out.loc[non_empty_mask].copy()

    if out.empty:
        return out

    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out = out[
        [
            "date",
            "symbol",
            "spot_price",
            "near_contract",
            "near_contract_price",
            "dominant_contract",
            "dominant_contract_price",
            "near_basis",
            "dom_basis",
            "near_basis_rate",
            "dom_basis_rate",
        ]
    ].reset_index(drop=True)
    return out


def _is_valid_basis_csv(path: Path) -> bool:
    try:
        if not path.exists():
            return False
        d = pd.read_csv(path)
        d.columns = [c.strip().lower() for c in d.columns]
        need = {
            "date",
            "spot_price",
            "near_contract",
            "near_contract_price",
            "dominant_contract",
            "dominant_contract_price",
            "near_basis",
            "dom_basis",
            "near_basis_rate",
            "dom_basis_rate",
        }
        if not need.issubset(set(d.columns)):
            return False
        if d.empty:
            return False
        # 至少一行存在任一数值列非空
        num_cols = [
            "spot_price",
            "near_contract_price",
            "dominant_contract_price",
            "near_basis",
            "dom_basis",
            "near_basis_rate",
            "dom_basis_rate",
        ]
        return (~pd.isna(d[num_cols])).any(axis=1).any()
    except Exception:
        return False


def _save_symbol(out_dir: Path, sym: str, df_sym: pd.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / sym / "basis.csv"
    (out_dir / sym).mkdir(parents=True, exist_ok=True)

    keep = [
        "date",
        "spot_price",
        "near_contract",
        "near_contract_price",
        "dominant_contract",
        "dominant_contract_price",
        "near_basis",
        "dom_basis",
        "near_basis_rate",
        "dom_basis_rate",
    ]

    if out_csv.exists():
        try:
            old = pd.read_csv(out_csv)
            old.columns = [c.strip().lower() for c in old.columns]
        except Exception:
            old = pd.DataFrame(columns=keep)
        merged = pd.concat([old[old.columns.intersection(keep)], df_sym[keep]], ignore_index=True)
    else:
        merged = df_sym[keep]

    num_cols = [
        "spot_price",
        "near_contract_price",
        "dominant_contract_price",
        "near_basis",
        "dom_basis",
        "near_basis_rate",
        "dom_basis_rate",
    ]
    non_empty_mask = (~pd.isna(merged[num_cols])).any(axis=1)
    merged = merged.loc[non_empty_mask].copy()

    merged = merged.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
    out_csv.write_text("")  # 防止编码冲突，先清空
    merged.to_csv(out_csv, index=False, encoding="utf-8-sig")


def _fetch_one(symbol: str, start: str, end: str, retries: int = 3, verbose: bool = True) -> pd.DataFrame:
    import akshare as ak  # type: ignore
    last_err: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            if verbose:
                print(f"[REQ] {symbol} {start}~{end}")
            df = ak.futures_spot_price_daily(start_day=start, end_day=end, vars_list=[symbol])
            return df
        except Exception as e:
            last_err = e
            time.sleep(random.uniform(0.4, 0.9))
    if verbose and last_err:
        print(f"[FAIL] {symbol}: {last_err}")
    return pd.DataFrame()


def main() -> None:
    warnings.filterwarnings("ignore", message=".*非交易日.*")

    parser = argparse.ArgumentParser(description="仅补齐缺失/无效品种的基差数据")
    parser.add_argument("--start", required=False, help="起始日期 YYYYMMDD，例如 20250615")
    parser.add_argument("--end", required=False, help="结束日期 YYYYMMDD，例如 20250814")
    parser.add_argument(
        "--symbols",
        required=False,
        help="逗号分隔的品种列表，仅对这些品种进行补齐；缺省将自动扫描目录发现无效/缺失品种",
    )
    parser.add_argument("--lookback-days", type=int, default=183, help="若未给 start，则从 end 往前回溯的天数，默认半年(183)")
    args = parser.parse_args()

    # 根目录：qihuo/scripts → qihuo
    qihuo_dir = Path(__file__).resolve().parents[1]
    basis_root = qihuo_dir / "database" / "basis"
    basis_root.mkdir(parents=True, exist_ok=True)

    # 时间区间
    if args.end:
        end_day = _to_yyyymmdd(args.end)
    else:
        end_day = pd.Timestamp.today().strftime("%Y%m%d")

    if args.start:
        start_day = _to_yyyymmdd(args.start)
    else:
        start_day = (pd.to_datetime(end_day) - pd.Timedelta(days=int(args.lookback_days))).strftime("%Y%m%d")

    # 确定目标品种集合
    target_symbols: List[str] = []
    if args.symbols:
        target_symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        # 自动扫描：文件缺失或文件无效
        existed_syms = [p.name for p in basis_root.iterdir() if p.is_dir()]
        for sym in existed_syms:
            if not _is_valid_basis_csv(basis_root / sym / "basis.csv"):
                target_symbols.append(sym)
        # 额外纳入这次用户反馈失败的列表（若目录根本不存在）
        reported_failed = ["J", "AO", "NR", "LU", "PL", "AP", "CJ", "RS", "PK", "B", "CS"]
        for s in reported_failed:
            if s not in existed_syms:
                target_symbols.append(s)
        target_symbols = sorted(list(dict.fromkeys(target_symbols)))

    if not target_symbols:
        print("[INFO] 无需补齐，未发现缺失或无效文件")
        return

    print(f"[INFO] 补齐目标: {target_symbols}")
    print(f"[INFO] 区间: {start_day} ~ {end_day}")

    ok, fail = [], []
    for sym in target_symbols:
        raw = _fetch_one(sym, start_day, end_day, retries=3, verbose=True)
        norm = _normalize(raw)
        if norm is None or norm.empty:
            fail.append(sym)
            continue
        # 仅保留该品种
        norm = norm[(norm["symbol"].str.upper() == sym)].copy()
        if norm.empty:
            fail.append(sym)
            continue
        _save_symbol(basis_root, sym, norm.drop(columns=["symbol"]))
        ok.append(sym)
        time.sleep(random.uniform(0.3, 0.7))

    print(f"[SUMMARY] 成功={len(ok)}, 失败={len(fail)}")
    if fail:
        print("[FAIL]", fail)


if __name__ == "__main__":
    main()


