from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_inventory_metrics(df: pd.DataFrame, series_name: str) -> Dict:
    """库存时序指标计算。

    期望列名之一：
      - [date, value]
      - [日期, 库存]
      - 允许包含 增减 列（可用于参考）
    """
    result: Dict = {
        "series": series_name,
        "latest": {},
        "wow_change": None,
        "mom_change": None,
        "zscore_180d": None,
        "jump_flag": False,
        "signals": [],
        "notes": [],
    }

    if df is None or len(df) == 0:
        result["notes"].append("无库存数据")
        return result

    data = df.copy()
    # 统一列名
    data = data.rename(columns={
        "日期": "date",
        "库存": "value",
        "数量": "value",
    })
    if "date" not in data.columns:
        result["notes"].append("缺少日期列")
        return result
    if "value" not in data.columns:
        # 若没有 value，尝试第一数值列
        num_cols = [c for c in data.columns if c != "date" and pd.api.types.is_numeric_dtype(data[c])]
        if num_cols:
            data["value"] = data[num_cols[0]]
        else:
            result["notes"].append("缺少库存数值列")
            return result

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(subset=["value"])  # 仅保留有效值
    if len(data) < 5:
        result["notes"].append("样本不足")

    last = data.iloc[-1]
    result["latest"] = {
        "date": str(last.get("date")) if pd.notna(last.get("date")) else None,
        "value": float(last.get("value")) if pd.notna(last.get("value")) else None,
    }

    # 简化 WoW / MoM（按行索引近似）
    try:
        prev_5 = data.iloc[-6]["value"] if len(data) >= 6 else None
        prev_20 = data.iloc[-21]["value"] if len(data) >= 21 else None
        v = float(last["value"]) if pd.notna(last["value"]) else None
        if v is not None and prev_5 is not None:
            result["wow_change"] = round(v - float(prev_5), 4)
        if v is not None and prev_20 is not None:
            result["mom_change"] = round(v - float(prev_20), 4)
    except Exception:
        pass

    # 180日分位
    tail = data.tail(180)
    def _pctl(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) == 0:
            return float("nan")
        lastv = s.iloc[-1]
        return float((s <= lastv).mean())
    try:
        result["zscore_180d"] = _pctl(tail["value"])
    except Exception:
        result["zscore_180d"] = None

    # 跳变标志（近20日变化相对20日std）
    try:
        d = data["value"].diff()
        z = (d - d.rolling(20, min_periods=5).mean()) / d.rolling(20, min_periods=5).std()
        jump = abs(float(z.iloc[-1])) if pd.notna(z.iloc[-1]) else 0.0
        result["jump_flag"] = bool(jump >= 3)
    except Exception:
        result["jump_flag"] = False

    # 简单信号
    sigs = []
    if result["wow_change"] is not None:
        if result["wow_change"] > 0:
            sigs.append("库存环比上升")
        elif result["wow_change"] < 0:
            sigs.append("库存环比下降")
    if result["zscore_180d"] is not None:
        p = result["zscore_180d"]
        if p >= 0.8:
            sigs.append("库存处高分位")
        elif p <= 0.2:
            sigs.append("库存处低分位")
    if result["jump_flag"]:
        sigs.append("库存变化异常（跳变）")

    result["signals"] = sigs
    return result


