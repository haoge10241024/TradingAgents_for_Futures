import argparse
from pathlib import Path
from typing import List

import pandas as pd


def symbol_to_cn(symbol: str) -> str:
    mapping = {
        "RB": "螺纹钢主连",
        "HC": "热卷主连",
        "CU": "沪铜主连",
        "AL": "沪铝主连",
        "ZN": "沪锌主连",
        "NI": "沪镍主连",
        "SN": "沪锡主连",
        "AG": "沪银主连",
        "AU": "沪金主连",
        "IF": "沪深300主连",
        "IH": "上证50主连",
        "IC": "中证500主连",
        "IM": "中证1000主连",
        "SS": "不锈钢主连",
        "I": "铁矿主连",
        "JM": "焦煤主连",
        "J": "焦炭主连",
        "TA": "PTA主连",
        "MA": "甲醇主连",
        "RU": "橡胶主连",
        "FG": "玻璃主连",
        "LH": "生猪主连",
        "SC": "原油主连",
    }
    return mapping.get(symbol.upper(), symbol)


def try_fetch_and_save(symbol: str, cache_csv: Path) -> bool:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return False
    try:
        cn = symbol_to_cn(symbol)
        df = ak.futures_hist_em(symbol=cn, period="daily")
        if df is None or len(df) == 0:
            return False
        need = ["时间", "开盘", "最高", "最低", "收盘", "成交量", "持仓量"]
        for col in need:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[need].copy()
        df["时间"] = pd.to_datetime(df["时间"])  # YYYY-MM-DD
        df = df.sort_values("时间").reset_index(drop=True)
        cache_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_csv, index=False, encoding="utf-8-sig")
        return True
    except Exception:
        return False


def diagnose_one(symbol: str, cache_dir: Path, min_days: int, auto_fetch: bool) -> None:
    csv_path = cache_dir / f"ohlcv_{symbol.upper()}.csv"
    status = {
        "symbol": symbol.upper(),
        "cache": str(csv_path),
        "exists": csv_path.exists(),
        "rows": 0,
        "first_date": None,
        "last_date": None,
        "ok": False,
        "action": None,
    }
    if not csv_path.exists() and auto_fetch:
        fetched = try_fetch_and_save(symbol, csv_path)
        status["exists"] = csv_path.exists()
        status["action"] = f"fetched={fetched}"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            status["rows"] = int(len(df))
            if "时间" in df.columns and len(df) > 0:
                status["first_date"] = str(pd.to_datetime(df["时间"]).min().date())
                status["last_date"] = str(pd.to_datetime(df["时间"]).max().date())
            status["ok"] = status["rows"] >= min_days
        except Exception as e:
            status["action"] = f"read_error: {e}"

    # 简洁打印
    ok_flag = "OK" if status["ok"] else "MISSING"
    print(f"[{symbol.upper()}] {ok_flag} rows={status['rows']} first={status['first_date']} last={status['last_date']} cache={csv_path}")
    if not status["ok"]:
        print("  建议: 运行导出脚本 → python qihuo/scripts/export_ohlcv.py --symbols", symbol.upper(), "--period daily --cache", str(cache_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="数据连通性自检：检查/拉取主连K线缓存")
    parser.add_argument("--symbols", nargs="+", required=True, help="品种代码列表，如 RB TA CU")
    parser.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    parser.add_argument("--min-days", type=int, default=180, help="最少需要的交易日数量")
    parser.add_argument("--auto-fetch", action="store_true", help="若无缓存则尝试在线拉取")
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    for sym in args.symbols:
        diagnose_one(sym, cache_dir, args.min_days, args.auto_fetch)


if __name__ == "__main__":
    main()


