import argparse
from pathlib import Path

# 保障可直接运行：将项目根目录加入 sys.path
import sys
_CURR = Path(__file__).resolve()
_ROOT = _CURR.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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


def export_one(symbol: str, cache_dir: Path, period: str = "daily") -> Path:
    import akshare as ak  # type: ignore

    cn = symbol_to_cn(symbol)
    df = ak.futures_hist_em(symbol=cn, period=period)
    if df is None or len(df) == 0:
        raise RuntimeError(f"未获取到数据: {symbol} ({cn})")

    # 选择常用列并转类型
    need = ["时间", "开盘", "最高", "最低", "收盘", "成交量", "持仓量"]
    for col in need:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[need].copy()
    for col in ["开盘", "最高", "最低", "收盘", "成交量", "持仓量"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["时间"] = pd.to_datetime(df["时间"])  # YYYY-MM-DD
    df = df.sort_values("时间").reset_index(drop=True)

    cache_dir.mkdir(parents=True, exist_ok=True)
    csv_path = cache_dir / f"ohlcv_{symbol.upper()}.csv"
    # 仅写 CSV，避免依赖 pyarrow
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    saved = csv_path

    # 输出前5行供校验
    print(f"保存: {saved}")
    print(df.head().to_string())
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="导出主连K线至本地缓存")
    parser.add_argument("--symbols", nargs="+", default=["RB", "CU", "LH"], help="品种代码列表，如 RB CU LH")
    parser.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"], help="周期")
    parser.add_argument("--cache", default="qihuo/.data/cache", help="缓存目录")
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    for sym in args.symbols:
        try:
            export_one(sym, cache_dir=cache_dir, period=args.period)
        except Exception as e:
            print(f"[{sym}] 导出失败: {e}")


if __name__ == "__main__":
    main()


