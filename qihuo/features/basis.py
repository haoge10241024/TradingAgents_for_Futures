from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_basis_metrics(df: pd.DataFrame, symbol: str) -> Dict:
    """基差与期现关系指标计算。

    输入 df: 期望来自 ak.futures_spot_price_daily，包含列：
      date, symbol, spot_price, near_contract, near_contract_price,
      dominant_contract, dominant_contract_price,
      near_basis, dom_basis, near_basis_rate, dom_basis_rate

    返回: 结构化指标与信号。
    """
    result: Dict = {
        "symbol": symbol,
        "latest": {},
        "zscore_180d": {},
        "slope_20d": {},
        "signals": [],
        "notes": [],
    }
    if df is None or len(df) == 0:
        result["notes"].append("无基差数据")
        return result

    # 仅保留指定品种
    data = df.copy()
    if "symbol" in data.columns:
        data = data[data["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    if len(data) == 0:
        result["notes"].append("目标品种无数据")
        return result

    # 规范类型与排序
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # 选取核心列
    cols = [
        "date","spot_price","near_contract","near_contract_price",
        "dominant_contract","dominant_contract_price",
        "near_basis","dom_basis","near_basis_rate","dom_basis_rate",
    ]
    for c in cols:
        if c not in data.columns:
            data[c] = pd.NA

    for c in ["spot_price","near_contract_price","dominant_contract_price","near_basis","dom_basis","near_basis_rate","dom_basis_rate"]:
        data[c] = pd.to_numeric(data[c], errors="coerce")

    if len(data) < 5:
        result["notes"].append("样本不足")

    last = data.iloc[-1]
    result["latest"] = {
        "date": str(last.get("date")) if pd.notna(last.get("date")) else None,
        "spot_price": float(last.get("spot_price")) if pd.notna(last.get("spot_price")) else None,
        "near_contract": last.get("near_contract"),
        "near_contract_price": float(last.get("near_contract_price")) if pd.notna(last.get("near_contract_price")) else None,
        "dominant_contract": last.get("dominant_contract"),
        "dominant_contract_price": float(last.get("dominant_contract_price")) if pd.notna(last.get("dominant_contract_price")) else None,
        "near_basis": float(last.get("near_basis")) if pd.notna(last.get("near_basis")) else None,
        "dom_basis": float(last.get("dom_basis")) if pd.notna(last.get("dom_basis")) else None,
        "near_basis_rate": float(last.get("near_basis_rate")) if pd.notna(last.get("near_basis_rate")) else None,
        "dom_basis_rate": float(last.get("dom_basis_rate")) if pd.notna(last.get("dom_basis_rate")) else None,
    }

    # 180日 Z 分位
    def _pctl(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) == 0:
            return float("nan")
        last = s.iloc[-1]
        return float((s <= last).mean())

    last_180 = data.tail(180)
    result["zscore_180d"] = {
        "near_basis_rate_pctl": _pctl(last_180["near_basis_rate"] if "near_basis_rate" in last_180.columns else pd.Series(dtype=float)),
        "dom_basis_rate_pctl": _pctl(last_180["dom_basis_rate"] if "dom_basis_rate" in last_180.columns else pd.Series(dtype=float)),
    }

    # 20日斜率（简单线性近似：最后值-前值）
    def _slope_20(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) < 2:
            return float("nan")
        return float(s.iloc[-1] - s.iloc[max(0, len(s)-20)])

    result["slope_20d"] = {
        "near_basis_rate_slope": _slope_20(data["near_basis_rate"] if "near_basis_rate" in data.columns else pd.Series(dtype=float)),
        "dom_basis_rate_slope": _slope_20(data["dom_basis_rate"] if "dom_basis_rate" in data.columns else pd.Series(dtype=float)),
    }

    # 信号（示例）：近月贴水扩大→可能反弹；主力溢价极端→回归
    signals: List[str] = []
    nbr = result["latest"].get("near_basis_rate")
    dbr = result["latest"].get("dom_basis_rate")
    p_near = result["zscore_180d"].get("near_basis_rate_pctl")
    p_dom = result["zscore_180d"].get("dom_basis_rate_pctl")
    if nbr is not None:
        if nbr < 0 and (p_near is not None and p_near <= 0.2):
            signals.append("近月贴水处低分位，存在反弹概率")
        if nbr > 0 and (p_near is not None and p_near >= 0.8):
            signals.append("近月升水处高分位，回归风险上升")
    if dbr is not None:
        if dbr < 0 and (p_dom is not None and p_dom <= 0.2):
            signals.append("主力贴水处低分位")
        if dbr > 0 and (p_dom is not None and p_dom >= 0.8):
            signals.append("主力升水处高分位")

    result["signals"] = signals
    return result


