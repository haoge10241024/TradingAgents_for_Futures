from __future__ import annotations

from typing import Dict, Optional

import pandas as pd


def compute_term_structure_metrics(df: pd.DataFrame, var: str) -> Dict:
    """期限结构/展期收益分析（基于 get_roll_yield_bar 导出的按日期数据）。

    兼容不同版本列名，尽力从列中识别：spread/roll_yield/主次合约价格差。

    期望（可能包含的列示例，不强制）：
      date, main_symbol, second_symbol, main_price, second_price, spread, roll_yield
    """
    result: Dict = {
        "var": var,
        "latest": {},
        "zscore_180d": {},
        "slope_20d": {},
        "structure": None,  # contango/backwardation/unknown
        "carry_score": None,  # [-1,1] 越高越利多多头
        "signals": [],
        "notes": [],
    }

    if df is None or len(df) == 0:
        result["notes"].append("无期限结构数据")
        return result

    data = df.copy()
    # 统一日期
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # 猜测可用的度量列
    cand_cols = [
        "roll_yield", "rollYield", "roll", "yield",  # 展期收益率
        "spread", "price_spread", "main_minus_second",  # 价差
    ]
    metric_col: Optional[str] = None
    for c in cand_cols:
        if c in data.columns:
            metric_col = c
            break

    # 若都没有，尝试以价格推导
    if metric_col is None and {"main_price", "second_price"}.issubset(set(data.columns)):
        data["spread"] = pd.to_numeric(data["main_price"], errors="coerce") - pd.to_numeric(data["second_price"], errors="coerce")
        metric_col = "spread"

    if metric_col is None:
        result["notes"].append("未识别可用的展期/价差列")
        return result

    # 数值化
    data[metric_col] = pd.to_numeric(data[metric_col], errors="coerce")
    data = data.dropna(subset=[metric_col])
    if len(data) == 0:
        result["notes"].append("度量列全为空")
        return result

    last = data.iloc[-1]
    result["latest"] = {
        "date": str(last.get("date")) if pd.notna(last.get("date")) else None,
        metric_col: float(last.get(metric_col)) if pd.notna(last.get(metric_col)) else None,
    }

    # 结构判定
    val = float(last.get(metric_col)) if pd.notna(last.get(metric_col)) else None
    if val is not None:
        if val > 0:
            result["structure"] = "contango"  # 远月>近月，价差为正
        elif val < 0:
            result["structure"] = "backwardation"  # 近月>远月
        else:
            result["structure"] = "flat"

    # 180日分位
    tail = data.tail(180)
    def _pctl(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) == 0:
            return float("nan")
        lastv = s.iloc[-1]
        return float((s <= lastv).mean())
    p = _pctl(tail[metric_col])
    result["zscore_180d"] = {metric_col + "_pctl": p}

    # 20日斜率（近似）
    def _slope_20(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) < 2:
            return float("nan")
        return float(s.iloc[-1] - s.iloc[max(0, len(s)-20)])
    result["slope_20d"] = {metric_col + "_slope": _slope_20(data[metric_col])}

    # carry_score（-1,1）：以分位与结构综合
    carry = None
    if p == p:  # 非NaN
        carry = (p - 0.5) * 2.0
        if result["structure"] == "backwardation":
            carry += 0.2
        elif result["structure"] == "contango":
            carry -= 0.2
        carry = max(-1.0, min(1.0, carry))
    result["carry_score"] = carry

    # 信号
    sigs = []
    if result["structure"] == "backwardation":
        sigs.append("期限结构偏多（Backwardation）")
    elif result["structure"] == "contango":
        sigs.append("期限结构偏空（Contango）")
    if carry is not None:
        if carry >= 0.5:
            sigs.append("carry友好（多头）")
        elif carry <= -0.5:
            sigs.append("carry不友好（多头）")
    result["signals"] = sigs
    return result


