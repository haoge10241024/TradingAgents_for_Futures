from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd


def audit_one(symbol_dir: Path) -> Dict[str, object]:
    symbol = symbol_dir.name
    csv_path = symbol_dir / "roll.csv"
    status: Dict[str, object] = {
        "symbol": symbol,
        "exists": csv_path.exists(),
        "rows": 0,
        "start": None,
        "end": None,
        "sorted": False,
        "unique_dates": False,
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
        status["note"] = "empty"
        return status

    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols
    if "date" not in df.columns:
        status["note"] = "no date col"
        return status

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    if df.empty:
        status["note"] = "all dates invalid"
        return status

    status["rows"] = int(len(df))
    status["start"] = df["date"].min().date().isoformat()
    status["end"] = df["date"].max().date().isoformat()
    status["sorted"] = df["date"].is_monotonic_increasing
    status["unique_dates"] = (df["date"].nunique() == len(df))

    return status


def main() -> None:
    p = argparse.ArgumentParser(description="审计期限结构数据库")
    p.add_argument("--root", default="qihuo/database/term_structure")
    p.add_argument("--out", default="qihuo/output/roll_audit.csv")
    args = p.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    symbols = [d for d in root.iterdir() if d.is_dir()]
    rows: List[Dict[str, object]] = []
    for d in sorted(symbols, key=lambda x: x.name):
        rows.append(audit_one(d))

    out_df = pd.DataFrame(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] 审计输出: {out_path}")
    problems = out_df[(out_df["rows"] == 0) | (~out_df["sorted"]) | (~out_df["unique_dates"])]
    if len(problems) == 0:
        print("[INFO] 全部通过")
    else:
        print("[WARN] 存在问题条目:\n" + problems.sort_values(["symbol"]).to_string(index=False))


if __name__ == "__main__":
    main()


