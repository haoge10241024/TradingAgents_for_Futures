from __future__ import annotations

"""
一次性构建库存数据库到 `qihuo/database/inventory/{SYMBOL}/inventory.csv`。

特性：
- 并发抓取、自动重试、按起止日期过滤（若接口不支持日期过滤则本地截取）
- 自动标准化为两列格式：date, value（UTF-8-SIG 保存）
- 与已存在文件自动合并去重（以 date 唯一）

用法示例：
  python qihuo/scripts/build_inventory_database.py --symbols all --start 20160101 --end 20250813 --workers 6
  python qihuo/scripts/build_inventory_database.py --symbols RB,HC,CU --workers 4

说明：
- AkShare 接口：ak.futures_inventory_em(symbol=系列中文名)
- 符号到库存系列中文名的映射需在 SYMBOL_TO_INVENTORY_SERIES 中维护
"""

import argparse
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


DEFAULT_DATABASE_DIR = Path("qihuo/database")
INVENTORY_DIRNAME = "inventory"


# 默认品种池（可根据需要扩充/调整顺序）
DEFAULT_SYMBOLS: List[str] = [
    "RB", "HC", "I", "J", "JM", "ZC",
    "CU", "AL", "ZN", "NI", "SN", "PB", "SS",
    "AU", "AG",
    "RU", "NR",
    "MA", "EG", "EB",
    "L", "PP", "V",
    "FG", "SA", "SP",
    "SR", "CF", "AP", "RM",
    "M", "Y", "P", "C", "CS", "JD", "LH",
]


# 品种 -> 库存系列中文名 映射
# 注：并非所有品种在 Eastmoney/AK 有一致的库存口径；缺失的可以后续再补
SYMBOL_TO_INVENTORY_SERIES: Dict[str, str] = {
    # 黑色系
    "RB": "螺纹钢",
    "HC": "热轧卷板",
    # 有色系
    "CU": "电解铜",
    "AL": "电解铝",
    "ZN": "锌锭",
    "NI": "电解镍",
    "SN": "锡锭",
    # 化工/能化部分品种可能无权威库存系列，这里暂不强配
    # 橡胶
    "RU": "天然橡胶",
    # 其他缺失者将被跳过
}


def _import_akshare():
    try:
        import akshare as ak  # type: ignore
        return ak
    except Exception as exc:  # pragma: no cover
        print("[ERROR] 未能导入 akshare，请先安装: pip install akshare", file=sys.stderr)
        raise


def _parse_yyyymmdd(s: Optional[str]) -> Optional[pd.Timestamp]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    except Exception:
        return pd.to_datetime(s, errors="coerce")


def _normalize_inventory_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "value"])  # 空框架

    # 统一列名
    cols = {c: str(c).lower() for c in df.columns}
    df = df.rename(columns=cols)

    # 常见列名映射
    date_col_candidates = [
        "date", "日期", "时间", "trade_date",
    ]
    value_col_candidates = [
        "value", "库存", "数量", "数值", "inventory",
    ]

    date_col = next((c for c in date_col_candidates if c.lower() in df.columns), None)
    value_col = next((c for c in value_col_candidates if c.lower() in df.columns), None)

    if date_col is None:
        # 猜第一列为日期
        date_col = df.columns[0]
    if value_col is None:
        # 猜最后一列为值
        value_col = df.columns[-1]

    out = df[[date_col, value_col]].copy()
    out.columns = ["date", "value"]

    # 规范化日期
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"])  # 丢弃无效日期

    # 数值清洗
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["value"])  # 丢弃无效数值

    # 去重排序
    out = out.drop_duplicates(subset=["date"]).sort_values("date")

    # 输出字符串化日期
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def _filter_by_date(df: pd.DataFrame, start: Optional[pd.Timestamp], end: Optional[pd.Timestamp]) -> pd.DataFrame:
    if df.empty:
        return df
    tmp = df.copy()
    dt = pd.to_datetime(tmp["date"], errors="coerce")
    mask = pd.Series(True, index=tmp.index)
    if start is not None:
        mask &= dt >= start
    if end is not None:
        mask &= dt <= end
    return tmp.loc[mask].reset_index(drop=True)


def _merge_existing(target_csv: Path, new_df: pd.DataFrame) -> pd.DataFrame:
    if target_csv.exists():
        try:
            old = pd.read_csv(target_csv)
            # 统一规范
            if not old.empty:
                if "date" not in old.columns or "value" not in old.columns:
                    old = _normalize_inventory_df(old)
                old["date"] = pd.to_datetime(old["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            merged = pd.concat([old, new_df], ignore_index=True)
            merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
            return merged
        except Exception:
            # 若旧文件异常，直接以新数据覆盖
            return new_df
    return new_df


def _save_inventory(symbol: str, db_dir: Path, df: pd.DataFrame) -> Path:
    out_dir = db_dir / INVENTORY_DIRNAME / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "inventory.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def _fetch_single(symbol: str, series_cn: str, retries: int, jitter_range: Tuple[float, float]) -> pd.DataFrame:
    ak = _import_akshare()
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            df = ak.futures_inventory_em(symbol=series_cn)
            return df
        except Exception as exc:
            last_err = exc
            # 轻度随机退避
            time.sleep(random.uniform(*jitter_range))
    if last_err:
        raise last_err
    return pd.DataFrame()


def _load_external_mapping(path: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not path:
        return mapping
    p = Path(path)
    if not p.exists():
        return mapping
    try:
        if p.suffix.lower() in {".csv"}:
            df = pd.read_csv(p)
        else:
            df = pd.read_excel(p)
        cols = {c: str(c).lower() for c in df.columns}
        df = df.rename(columns=cols)
        if "symbol" in df.columns and "series_cn" in df.columns:
            for _, row in df.iterrows():
                sym = str(row["symbol"]).strip().upper()
                ser = str(row["series_cn"]).strip()
                if sym and ser and ser.lower() != "nan":
                    mapping[sym] = ser
    except Exception as exc:
        print(f"[WARN] 外部映射文件解析失败: {exc}")
    return mapping


def _process_symbol(symbol: str, db_dir: Path, start: Optional[pd.Timestamp], end: Optional[pd.Timestamp], retries: int, jitter_range: Tuple[float, float]) -> Tuple[str, str, Optional[str]]:
    series_cn = SYMBOL_TO_INVENTORY_SERIES.get(symbol)
    if not series_cn:
        return symbol, "skip", f"未配置库存系列中文名，已跳过"
    try:
        raw = _fetch_single(symbol, series_cn, retries=retries, jitter_range=jitter_range)
        norm = _normalize_inventory_df(raw)
        if start is not None or end is not None:
            norm = _filter_by_date(norm, start, end)
        target_csv = db_dir / INVENTORY_DIRNAME / symbol / "inventory.csv"
        merged = _merge_existing(target_csv, norm)
        _save_inventory(symbol, db_dir, merged)
        return symbol, "ok", f"{len(merged)} rows"
    except Exception as exc:
        return symbol, "fail", str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="构建库存数据库（一次性或增量）")
    parser.add_argument("--symbols", type=str, default="all", help="all 或 逗号分隔品种，如 RB,HC,CU")
    parser.add_argument("--database-dir", type=str, default=str(DEFAULT_DATABASE_DIR), help="数据库根目录，默认 qihuo/database")
    parser.add_argument("--workers", type=int, default=4, help="并发线程数")
    parser.add_argument("--start", type=str, default=None, help="起始日期 YYYYMMDD，可选")
    parser.add_argument("--end", type=str, default=None, help="结束日期 YYYYMMDD，可选")
    parser.add_argument("--retries", type=int, default=3, help="失败重试次数")
    parser.add_argument("--sleep-min", type=float, default=0.4, help="重试最小等待秒")
    parser.add_argument("--sleep-max", type=float, default=1.2, help="重试最大等待秒")
    parser.add_argument("--mapping-file", type=str, default="qihuo/config/inventory_series_map.csv", help="外部映射文件 CSV/Excel，列需包含 symbol, series_cn")

    args = parser.parse_args()

    database_dir = Path(args.database_dir)
    database_dir.mkdir(parents=True, exist_ok=True)

    # 解析品种集合
    if args.symbols.strip().lower() == "all":
        symbols = list(dict.fromkeys(DEFAULT_SYMBOLS))
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        symbols = list(dict.fromkeys(symbols))

    # 载入外部映射，合并到默认映射
    external_map = _load_external_mapping(args.mapping_file)
    if external_map:
        SYMBOL_TO_INVENTORY_SERIES.update(external_map)
        print(f"[INFO] 已从 {args.mapping_file} 载入映射 {len(external_map)} 条")

    start_ts = _parse_yyyymmdd(args.start)
    end_ts = _parse_yyyymmdd(args.end)

    print(f"[INFO] 目标数据库目录: {database_dir}")
    print(f"[INFO] 品种数: {len(symbols)} => {symbols}")
    if start_ts is not None or end_ts is not None:
        print(f"[INFO] 日期过滤: start={args.start}, end={args.end}")

    results: List[Tuple[str, str, Optional[str]]] = []
    jitter = (min(args.sleep_min, args.sleep_max), max(args.sleep_min, args.sleep_max))

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_to_symbol = {
            executor.submit(
                _process_symbol,
                symbol,
                database_dir,
                start_ts,
                end_ts,
                args.retries,
                jitter,
            ): symbol for symbol in symbols
        }
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                sym, status, msg = future.result()
            except Exception as exc:  # pragma: no cover
                sym, status, msg = symbol, "fail", str(exc)
            print(f"[{status.upper()}] {sym}: {msg}")
            results.append((sym, status, msg))

    ok = sum(1 for _, s, _ in results if s == "ok")
    skip = sum(1 for _, s, _ in results if s == "skip")
    fail = sum(1 for _, s, _ in results if s == "fail")
    print(f"[SUMMARY] ok={ok}, skip={skip}, fail={fail}")

    if fail > 0:
        print("[HINT] 可提高 --retries 或降低 --workers，或补充 SYMBOL_TO_INVENTORY_SERIES 映射。")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


