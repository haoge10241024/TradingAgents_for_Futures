from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from qihuo.features.technical import add_basic_indicators, add_extended_indicators


@dataclass
class TechnicalEngineConfig:
    atr_stop_multiplier: float = 2.5
    min_rows_required: int = 60
    adx_trend_threshold: float = 25.0
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    bw_expand_ratio: float = 1.05
    bw_contract_ratio: float = 0.95


class TechnicalEngine:
    def __init__(self, config: Optional[TechnicalEngineConfig] = None) -> None:
        self.config = config or TechnicalEngineConfig()

    def _compute_scores(self, last: pd.Series) -> Dict[str, float]:
        scores: Dict[str, float] = {}

        # 基础趋势（EMA20 vs MA60）
        ema20 = last.get("EMA20")
        ma60 = last.get("MA60")
        if pd.notna(ema20) and pd.notna(ma60):
            scores["trend"] = float((ema20 - ma60) / max(abs(ma60), 1e-9))
        else:
            scores["trend"] = 0.0

        # MACD
        macd = last.get("MACD")
        macd_sig = last.get("MACD_SIGNAL")
        if pd.notna(macd) and pd.notna(macd_sig):
            scores["macd"] = float((macd - macd_sig) / max(abs(macd_sig) + 1e-9, 1.0))
        else:
            scores["macd"] = 0.0

        # DMI
        pdi = last.get("PLUS_DI14")
        mdi = last.get("MINUS_DI14")
        if pd.notna(pdi) and pd.notna(mdi):
            scores["dmi"] = float((pdi - mdi) / max(pdi + mdi, 1e-9))
        else:
            scores["dmi"] = 0.0

        # VWAP20 相对位置
        close = last.get("收盘")
        vwap20 = last.get("VWAP20")
        if pd.notna(close) and pd.notna(vwap20):
            scores["vwap"] = float((close - vwap20) / max(abs(vwap20), 1e-9))
        else:
            scores["vwap"] = 0.0

        # 归一化方向强度（粗略 0-1）
        raw = 0.4 * scores["trend"] + 0.3 * scores["macd"] + 0.2 * scores["dmi"] + 0.1 * scores["vwap"]
        strength = max(0.0, min(1.0, abs(raw)))
        direction = "long" if raw > 0.02 else ("short" if raw < -0.02 else "neutral")
        scores["raw"] = raw
        scores["strength"] = strength
        scores["direction_sign"] = 1.0 if direction == "long" else (-1.0 if direction == "short" else 0.0)
        return scores

    def _levels(self, last: pd.Series) -> Dict[str, Optional[float]]:
        atr = float(last.get("ATR14")) if pd.notna(last.get("ATR14")) else None
        close = float(last.get("收盘")) if pd.notna(last.get("收盘")) else None
        ma20 = float(last.get("MA20")) if pd.notna(last.get("MA20")) else None
        ma60 = float(last.get("MA60")) if pd.notna(last.get("MA60")) else None
        vwap20 = float(last.get("VWAP20")) if pd.notna(last.get("VWAP20")) else None
        s1 = float(last.get("PIVOT_S1")) if pd.notna(last.get("PIVOT_S1")) else None
        r1 = float(last.get("PIVOT_R1")) if pd.notna(last.get("PIVOT_R1")) else None
        hh = float(last.get("HHV20")) if pd.notna(last.get("HHV20")) else None
        ll = float(last.get("LLV20")) if pd.notna(last.get("LLV20")) else None

        stop_atr = None
        if atr is not None and close is not None:
            stop_atr = round(self.config.atr_stop_multiplier * atr, 4)

        return {
            "close": close,
            "MA20": ma20,
            "MA60": ma60,
            "VWAP20": vwap20,
            "HHV20": hh,
            "LLV20": ll,
            "PIVOT_R1": r1,
            "PIVOT_S1": s1,
            "ATR14": atr,
            "ATRx": stop_atr,
        }

    def summarize(self, df: pd.DataFrame) -> Dict:
        result = {
            "direction": "neutral",
            "strength": 0.0,
            "triggers": [],
            "volatility": {"atr": None, "regime": "low"},
            "oi_divergence": "neutral",
            "notes": [],
            "snapshot": {},
            "levels": {},
            "scores": {},
            "quality": {},
        }

        if not isinstance(df, pd.DataFrame) or len(df) < 5:
            result["notes"].append("样本不足")
            result["quality"] = {"rows": int(len(df) if isinstance(df, pd.DataFrame) else 0), "ok": False}
            return result

        feat = add_basic_indicators(df)
        feat = add_extended_indicators(feat)
        last = feat.iloc[-1]

        # 方向/强度评分
        scores = self._compute_scores(last)
        direction = "long" if scores["raw"] > 0.02 else ("short" if scores["raw"] < -0.02 else "neutral")
        strength = scores["strength"]

        # 触发规则（与 features 保持一致，列表化即可）
        triggers: List[str] = []
        if pd.notna(last.get("MA20")) and pd.notna(last.get("MA60")):
            if last["收盘"] > last["MA20"] > last["MA60"]:
                triggers.append("价在MA20/MA60上方，趋势延续条件")
            if last["收盘"] < last["MA20"] < last["MA60"]:
                triggers.append("价在MA20/MA60下方，空头延续条件")
        if pd.notna(last.get("MACD")) and pd.notna(last.get("MACD_SIGNAL")):
            if last["MACD"] > last["MACD_SIGNAL"]:
                triggers.append("MACD金叉")
            elif last["MACD"] < last["MACD_SIGNAL"]:
                triggers.append("MACD死叉")
        if int(last.get("BREAKOUT_LONG20", 0)) == 1:
            triggers.append("突破20日新高")
        if int(last.get("BREAKOUT_SHORT20", 0)) == 1:
            triggers.append("跌破20日新低")

        # 波动与背离
        atr_val = float(last.get("ATR14")) if pd.notna(last.get("ATR14")) else None
        vol_regime = "low"
        if atr_val is not None and pd.notna(last.get("收盘")):
            atr_ratio = atr_val / max(float(last["收盘"]), 1e-9)
            vol_regime = "high" if atr_ratio > 0.02 else "low"

        oi_div = "neutral"
        if "持仓量" in feat.columns:
            window = 5
            price_chg = feat["收盘"].astype(float).diff(window).iloc[-1]
            oi_chg = feat["持仓量"].astype(float).diff(window).iloc[-1]
            if pd.notna(price_chg) and pd.notna(oi_chg):
                if price_chg > 0 and oi_chg > 0:
                    oi_div = "confirm"
                elif (price_chg > 0 and oi_chg < 0) or (price_chg < 0 and oi_chg > 0):
                    oi_div = "conflict"

        # 快照/水平/质量
        snapshot_keys = [
            "收盘","MA20","MA60","EMA20","ATR14","RSI14","MACD","MACD_SIGNAL","MACD_HIST",
            "BOLL_UP","BOLL_MID","BOLL_LOW","BOLL_BW","PLUS_DI14","MINUS_DI14","ADX14",
            "KDJ_K","KDJ_D","KDJ_J","VOL_Z20","OI_Z20","VWAP20","ATR_RATIO_PCTL180","BOX20",
        ]
        snapshot = {k: (float(last.get(k)) if pd.notna(last.get(k)) else None) for k in snapshot_keys}
        levels = self._levels(last)
        quality = {
            "rows": int(len(feat)),
            "ok": bool(len(feat) >= self.config.min_rows_required),
            "has_oi": bool("持仓量" in feat.columns),
        }

        result.update({
            "direction": direction,
            "strength": round(float(strength), 3),
            "triggers": triggers,
            "volatility": {"atr": atr_val, "regime": vol_regime},
            "oi_divergence": oi_div,
            "snapshot": snapshot,
            "levels": levels,
            "scores": scores,
            "quality": quality,
        })
        return result


