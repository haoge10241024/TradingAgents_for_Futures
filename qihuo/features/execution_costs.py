from __future__ import annotations

import re
from typing import Dict, Optional

import pandas as pd


def _to_float(x: object) -> Optional[float]:
    if x is None:
        return None
    try:
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x)
        if s.strip() == "" or s.strip().lower() == "nan":
            return None
        # 提取数字（含小数、负号）
        m = re.findall(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
        if not m:
            return None
        return float(m[0])
    except Exception:
        return None


def compute_execution_costs(df: pd.DataFrame, symbol: str) -> Dict:
    """交易成本与约束标准化。

    期望列示例（ak.futures_comm_info）：
      现价、涨停板、跌停板、保证金-买开、保证金-卖开、保证金-每手、手续费标准-开仓-万分之、...、手续费标准-开仓-元、手续费标准-平昨-元、手续费标准-平今-元、每跳毛利、手续费、每跳净利
    注：不同交易所列可能为 NaN，本函数尽力兼容。
    """
    result: Dict = {
        "symbol": symbol,
        "exchange": None,
        "contract_hint": None,
        "price": None,
        "limit_up": None,
        "limit_down": None,
        "margin_rate_buy": None,
        "margin_rate_sell": None,
        "margin_per_lot": None,
        "fee": {
            "open_per_lot": None,
            "close_yest_per_lot": None,
            "close_today_per_lot": None,
            "open_rate": None,
            "close_yest_rate": None,
            "close_today_rate": None,
        },
        "tick_gross": None,
        "tick_net": None,
        "notes": [],
    }

    if df is None or len(df) == 0:
        result["notes"].append("无交易成本数据")
        return result

    data = df.copy()
    # 简单依据 symbol 过滤（合约代码/合约名称包含品种代号，可能需要更精细规则，可后续增强）
    mask = pd.Series([True] * len(data))
    if "合约代码" in data.columns:
        mask = mask & data["合约代码"].astype(str).str.contains(symbol, case=False, na=False)
    if "合约名称" in data.columns:
        mask = mask | data["合约名称"].astype(str).str.contains(symbol, case=False, na=False)
    filtered = data[mask].copy()
    if len(filtered) == 0:
        # 回退：取整表中与 symbol 同交易所品种的第一行
        filtered = data.copy()

    row = filtered.iloc[0]

    # 基本域
    result["exchange"] = row.get("交易所名称") if pd.notna(row.get("交易所名称")) else None
    result["contract_hint"] = row.get("合约名称") if pd.notna(row.get("合约名称")) else None
    result["price"] = _to_float(row.get("现价"))
    result["limit_up"] = _to_float(row.get("涨停板"))
    result["limit_down"] = _to_float(row.get("跌停板"))

    # 保证金
    result["margin_rate_buy"] = _to_float(row.get("保证金-买开"))
    result["margin_rate_sell"] = _to_float(row.get("保证金-卖开"))
    result["margin_per_lot"] = _to_float(row.get("保证金-每手"))

    # 手续费（元/手 与 万分比并存）
    # 元/手
    result["fee"]["open_per_lot"] = _to_float(row.get("手续费标准-开仓-元")) or _to_float(row.get("手续费"))
    result["fee"]["close_yest_per_lot"] = _to_float(row.get("手续费标准-平昨-元"))
    result["fee"]["close_today_per_lot"] = _to_float(row.get("手续费标准-平今-元"))
    # 费率（万分之→小数）
    def _to_rate(val) -> Optional[float]:
        v = _to_float(val)
        return None if v is None else v / 10000.0
    result["fee"]["open_rate"] = _to_rate(row.get("手续费标准-开仓-万分之"))
    result["fee"]["close_yest_rate"] = _to_rate(row.get("手续费标准-平昨-万分之"))
    result["fee"]["close_today_rate"] = _to_rate(row.get("手续费标准-平今-万分之"))

    # Tick 信息
    result["tick_gross"] = _to_float(row.get("每跳毛利"))
    result["tick_net"] = _to_float(row.get("每跳净利"))

    return result


