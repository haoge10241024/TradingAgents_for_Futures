from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from qihuo.features.technical import summarize_multi_timeframes
from qihuo.analysis.technical_engine import TechnicalEngine, TechnicalEngineConfig


@dataclass
class TechnicalAnalystConfig:
    lookback_days: int = 365
    freq: str = "1d"


class TechnicalAnalyst:
    """技术面分析师（MVP）。

    仅依赖历史K线与OI，计算基础指标并给出结构化技术面报告。
    """

    def __init__(self, provider, config: Optional[TechnicalAnalystConfig] = None) -> None:
        self.provider = provider
        self.config = config or TechnicalAnalystConfig()

    def analyze(self, symbol: str, as_of: str) -> Dict:
        # 计算起止日期
        import datetime as _dt

        end_dt = _dt.datetime.strptime(as_of, "%Y-%m-%d")
        start_dt = end_dt - _dt.timedelta(days=int(self.config.lookback_days))
        start = start_dt.strftime("%Y-%m-%d")
        end = end_dt.strftime("%Y-%m-%d")

        # 获取K线数据（后续将用 provider 实现，这里先抛错由上层捕获或在接入前注入DataFrame）
        try:
            df = self.provider.get_ohlcv(symbol=symbol, start=start, end=end, freq=self.config.freq, continuous=True)
        except NotImplementedError:
            # 占位：返回统一schema的空报告（daily/weekly），避免下游解析不一致
            return {
                "technical_report": {
                    "timeframes": ["D", "W"],
                    "daily": {
                        "direction": "neutral",
                        "strength": 0.0,
                        "triggers": [],
                        "volatility": {"atr": None, "regime": "low"},
                        "oi_divergence": "neutral",
                        "notes": ["数据提供器不可用/无数据"],
                    },
                    "weekly": {
                        "direction": "neutral",
                        "strength": 0.0,
                        "triggers": [],
                        "volatility": {"atr": None, "regime": "low"},
                        "oi_divergence": "neutral",
                        "notes": ["数据提供器不可用/无数据"],
                    },
                }
            }

        if not isinstance(df, pd.DataFrame) or df.empty:
            return {
                "technical_report": {
                    "timeframes": ["D", "W"],
                    "daily": {
                        "direction": "neutral",
                        "strength": 0.0,
                        "triggers": [],
                        "volatility": {"atr": None, "regime": "low"},
                        "oi_divergence": "neutral",
                        "notes": ["未获取到有效K线数据"],
                    },
                    "weekly": {
                        "direction": "neutral",
                        "strength": 0.0,
                        "triggers": [],
                        "volatility": {"atr": None, "regime": "low"},
                        "oi_divergence": "neutral",
                        "notes": ["未获取到有效K线数据"],
                    },
                }
            }

        # 多周期摘要（与引擎输出并列）
        summary = summarize_multi_timeframes(df)
        # 引擎生成更完整的日线专业摘要（scores/levels/quality）
        engine = TechnicalEngine(TechnicalEngineConfig())
        engine_daily = engine.summarize(df)
        return {
            "technical_report": {
                "timeframes": ["D", "W"],
                "daily": summary.get("daily", {}),
                "weekly": summary.get("weekly", {}),
                "engine_daily": engine_daily,
            }
        }


