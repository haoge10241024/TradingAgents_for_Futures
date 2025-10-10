from __future__ import annotations

from pathlib import Path
from typing import Dict

from qihuo.data_providers.basis_provider import BasisProvider
from qihuo.features.basis import compute_basis_metrics
from qihuo.data_providers.term_structure_provider import TermStructureProvider
from qihuo.features.term_structure import compute_term_structure_metrics
from qihuo.data_providers.inventory_provider import InventoryProvider
from qihuo.features.inventory import compute_inventory_metrics


def aggregate_fundamentals(symbol: str, cache_dir: str, try_online: bool = False, start: str | None = None, end: str | None = None) -> Dict:
    """汇总四类基本面（基差/期限结构/库存/席位）。不涉及LLM。

    返回结构：{
      symbol, fundamentals: {basis, term_structure, inventory, positioning}, audit
    }
    """
    cache = Path(cache_dir)

    # 基差
    try:
        basis_provider = BasisProvider(cache_dir=str(cache))
        basis_df = basis_provider.get_spot_price_daily(symbol, start=start, end=end, try_online=try_online)
        basis_report = (
            compute_basis_metrics(basis_df, symbol)
            if basis_df is not None and len(basis_df) > 0
            else {"notes": ["无基差缓存"]}
        )
    except Exception:
        basis_report = {"notes": ["基差计算异常"]}

    # 期限结构
    try:
        ts_provider = TermStructureProvider(cache_dir=str(cache))
        roll_df = ts_provider.get_roll_by_date(symbol, start=start, end=end, try_online=try_online)
        term_report = (
            compute_term_structure_metrics(roll_df, symbol)
            if roll_df is not None and len(roll_df) > 0
            else {"notes": ["无期限结构缓存"]}
        )
    except Exception:
        term_report = {"notes": ["期限结构计算异常"]}

    # 库存（示例映射，可外置到配置）
    try:
        inv_provider = InventoryProvider(cache_dir=str(cache))
        sym2series = {
            "RB": "螺纹钢",
            "TA": "PTA",
            "CU": "沪铜",
        }
        series = sym2series.get(symbol.upper())
        inv_df = inv_provider.get_inventory_series(series, try_online=try_online) if series else None
        inv_report = (
            compute_inventory_metrics(inv_df, series)
            if inv_df is not None and len(inv_df) > 0
            else {"notes": ["无库存缓存"]}
        )
    except Exception:
        inv_report = {"notes": ["库存计算异常"]}

    fundamentals = {
        "symbol": symbol.upper(),
        "fundamentals": {
            "basis": basis_report,
            "term_structure": term_report,
            "inventory": inv_report,
        },
        "audit": {
            "cache_dir": str(cache),
            "modules": ["basis", "term_structure", "inventory"],
        },
    }

    # 构造给LLM的精简输入（仅结构化数值，不含rule文本signals）
    def _safe(d: dict, keys: list[str]) -> dict:
        out: dict = {}
        for k in keys:
            v = d.get(k)
            if isinstance(v, (int, float)) or v is None:
                out[k] = v
            else:
                # 跳过非数值/非None
                pass
        return out

    basis_llm = {}
    if isinstance(basis_report, dict):
        latest = basis_report.get("latest", {}) if isinstance(basis_report.get("latest"), dict) else {}
        z180 = basis_report.get("zscore_180d", {}) if isinstance(basis_report.get("zscore_180d"), dict) else {}
        slope = basis_report.get("slope_20d", {}) if isinstance(basis_report.get("slope_20d"), dict) else {}
        basis_llm = {
            "latest": _safe(latest, [
                "spot_price","near_contract_price","dominant_contract_price",
                "near_basis","dom_basis","near_basis_rate","dom_basis_rate",
            ]),
            "zscore_180d": _safe(z180, ["near_basis_rate_pctl","dom_basis_rate_pctl"]),
            "slope_20d": _safe(slope, ["near_basis_rate_slope","dom_basis_rate_slope"]),
        }

    term_llm = {}
    if isinstance(term_report, dict):
        latest = term_report.get("latest", {}) if isinstance(term_report.get("latest"), dict) else {}
        z180 = term_report.get("zscore_180d", {}) if isinstance(term_report.get("zscore_180d"), dict) else {}
        slope = term_report.get("slope_20d", {}) if isinstance(term_report.get("slope_20d"), dict) else {}
        term_llm = {
            "latest": _safe(latest, ["roll_yield", "spread"]),
            "zscore_180d": {k: v for k, v in z180.items() if isinstance(v, (int, float)) or v is None},
            "slope_20d": {k: v for k, v in slope.items() if isinstance(v, (int, float)) or v is None},
        }

    inv_llm = {}
    if isinstance(inv_report, dict):
        latest = inv_report.get("latest", {}) if isinstance(inv_report.get("latest"), dict) else {}
        inv_llm = {
            "latest": _safe(latest, ["value"]),
            "wow_change": inv_report.get("wow_change") if isinstance(inv_report.get("wow_change"), (int, float)) else None,
            "mom_change": inv_report.get("mom_change") if isinstance(inv_report.get("mom_change"), (int, float)) else None,
            "zscore_180d": inv_report.get("zscore_180d") if isinstance(inv_report.get("zscore_180d"), (int, float)) else None,
        }

    fundamentals["llm_input"] = {
        "symbol": symbol.upper(),
        "basis": basis_llm,
        "term_structure": term_llm,
        "inventory": inv_llm,
    }

    # 仅输出给LLM的必要信息（去除任何rule判定/文字signals）
    return {
        "symbol": fundamentals["symbol"],
        "llm_input": fundamentals["llm_input"],
        "audit": fundamentals["audit"],
    }


