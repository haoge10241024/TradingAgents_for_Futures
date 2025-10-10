from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


EXPECTED_COLS = [
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

NUMERIC_COLS = [
    "spot_price",
    "near_contract_price",
    "dominant_contract_price",
    "near_basis",
    "dom_basis",
    "near_basis_rate",
    "dom_basis_rate",
]


def audit_one(symbol_dir: Path) -> Dict[str, object]:
    symbol = symbol_dir.name
    csv_path = symbol_dir / "basis.csv"
    status: Dict[str, object] = {
        "symbol": symbol,
        "exists": csv_path.exists(),
        "rows": 0,
        "start": None,
        "end": None,
        "schema_ok": False,
        "sorted": False,
        "unique_dates": False,
        "nonempty_ratio": 0.0,
        "empty_rows": 0,
        "note": "",
    }

    if not csv_path.exists():
        status["note"] = "missing file"
        return status

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        status["note"] = f"read_error: {e}"
        return status

    if df is None or df.empty:
        status["rows"] = 0
        status["note"] = "empty file"
        return status

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    status["schema_ok"] = set(EXPECTED_COLS).issubset(set(df.columns))
    status["rows"] = int(len(df))

    if "date" not in df.columns:
        status["note"] = "no date column"
        return status

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if df.empty:
        status["note"] = "all dates invalid"
        return status

    # metrics
    status["start"] = df["date"].min().date().isoformat()
    status["end"] = df["date"].max().date().isoformat()
    status["sorted"] = df["date"].is_monotonic_increasing
    status["unique_dates"] = (df["date"].nunique() == len(df))

    if set(NUMERIC_COLS).issubset(set(df.columns)):
        nonempty_mask = (~pd.isna(df[NUMERIC_COLS])).any(axis=1)
        status["nonempty_ratio"] = float(nonempty_mask.mean())
        status["empty_rows"] = int((~nonempty_mask).sum())
    else:
        status["note"] = (status.get("note", "") + " missing numeric cols").strip()

    return status


def main() -> None:
    p = argparse.ArgumentParser(description="审计基差数据库完整性")
    p.add_argument("--root", default="qihuo/database/basis", help="基差数据库根目录")
    p.add_argument("--out", default="qihuo/output/basis_audit.csv", help="输出汇总CSV")
    args = p.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] 目录不存在: {root}")
        return

    symbols = [d for d in root.iterdir() if d.is_dir()]
    rows: List[Dict[str, object]] = []
    for d in sorted(symbols, key=lambda x: x.name):
        rows.append(audit_one(d))

    out_df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    # 简要打印异常项
    problems = out_df[(~out_df["schema_ok"]) | (out_df["rows"] == 0) | (~out_df["sorted"]) | (~out_df["unique_dates"]) | (out_df["nonempty_ratio"] < 1.0)]
    print(f"[INFO] 审计已输出: {out_path}")
    if len(problems) == 0:
        print("[INFO] 全部通过基础校验")
    else:
        print("[WARN] 发现问题条目: ")
        print(problems.sort_values(["symbol"]).to_string(index=False))


if __name__ == "__main__":
    main()


