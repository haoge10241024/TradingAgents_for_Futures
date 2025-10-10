from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_positioning_metrics(df: pd.DataFrame, symbol: str) -> Dict:
    """席位与拥挤度指标计算（基于本地预聚合的CSV）。

    期望列（尽量兼容，缺失时尽力推断）：
      - date
      - long_top20: 前20多单持仓合计
      - short_top20: 前20空单持仓合计
      - total_oi: 全市场持仓量（可选）
      - net_long_top20: 前20净多（可选，若无则 long_top20 - short_top20）
    """
    result: Dict = {
        "symbol": symbol,
        "latest": {},
        "concentration": None,
        "crowding_pctl_180d": None,
        "net_long_change_5d": None,
        "signals": [],
        "notes": [],
    }

    if df is None or len(df) == 0:
        result["notes"].append("无席位缓存")
        return result

    data = df.copy()
    # 统一列名
    rename_map = {
        "日期": "date",
        "long_open_interest_top20": "long_top20",
        "short_open_interest_top20": "short_top20",
        "total_open_interest": "total_oi",
    }
    data = data.rename(columns=rename_map)
    if "date" not in data.columns:
        result["notes"].append("缺少date列")
        return result
    for c in ["long_top20", "short_top20", "total_oi", "net_long_top20"]:
        if c in data.columns:
            data[c] = pd.to_numeric(data[c], errors="coerce")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if len(data) < 5:
        result["notes"].append("样本不足")

    if "net_long_top20" not in data.columns and {"long_top20", "short_top20"}.issubset(set(data.columns)):
        data["net_long_top20"] = data["long_top20"] - data["short_top20"]

    # 计算集中度
    conc = None
    if "total_oi" in data.columns and "long_top20" in data.columns:
        denom = (2.0 * data["total_oi"]).replace(0, pd.NA)
        conc = (data.get("long_top20", 0).fillna(0) + data.get("short_top20", 0).fillna(0)) / denom
    elif "long_top20" in data.columns:
        # 以 long_top20 的180日分位近似集中度强弱
        conc = (data["long_top20"] - data["long_top20"].rolling(60, min_periods=10).mean()) / data["long_top20"].rolling(60, min_periods=10).std()
    if conc is not None is not False:
        data["conc_metric"] = conc

    last = data.iloc[-1]

    # 180日分位（对 conc_metric 或 net_long_top20）
    def _pctl(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) == 0:
            return float("nan")
        lastv = s.iloc[-1]
        return float((s <= lastv).mean())

    pctl = None
    if "conc_metric" in data.columns:
        pctl = _pctl(data.tail(180)["conc_metric"])

    # 5日净多变化
    nl_chg5 = None
    if "net_long_top20" in data.columns and len(data) >= 6:
        nl_chg5 = float(data["net_long_top20"].iloc[-1] - data["net_long_top20"].iloc[-6])

    # 最新值与信号
    result["latest"] = {
        "date": str(last.get("date")) if pd.notna(last.get("date")) else None,
        "long_top20": float(last.get("long_top20")) if "long_top20" in data.columns and pd.notna(last.get("long_top20")) else None,
        "short_top20": float(last.get("short_top20")) if "short_top20" in data.columns and pd.notna(last.get("short_top20")) else None,
        "total_oi": float(last.get("total_oi")) if "total_oi" in data.columns and pd.notna(last.get("total_oi")) else None,
        "net_long_top20": float(last.get("net_long_top20")) if "net_long_top20" in data.columns and pd.notna(last.get("net_long_top20")) else None,
    }
    result["concentration"] = float(last.get("conc_metric")) if "conc_metric" in data.columns and pd.notna(last.get("conc_metric")) else None
    result["crowding_pctl_180d"] = pctl
    result["net_long_change_5d"] = nl_chg5

    sigs = []
    if pctl is not None and pctl == pctl:  # 非NaN
        if pctl >= 0.8:
            sigs.append("拥挤度处高分位")
        elif pctl <= 0.2:
            sigs.append("拥挤度处低分位")
    if nl_chg5 is not None:
        if nl_chg5 >= 0:
            sigs.append("前20净多增加")
        else:
            sigs.append("前20净多减少")
    result["signals"] = sigs
    return result


