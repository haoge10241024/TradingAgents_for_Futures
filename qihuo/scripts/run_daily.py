import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# 保障可直接运行：将项目根目录加入 sys.path
import sys
_CURR = Path(__file__).resolve()
_ROOT = _CURR.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qihuo.data_providers import get_provider
from qihuo.agents import TechnicalAnalyst
from qihuo.llm.deepseek_client import DeepSeekClient
from qihuo.data_providers.basis_provider import BasisProvider
from qihuo.features.basis import compute_basis_metrics
from qihuo.data_providers.term_structure_provider import TermStructureProvider
from qihuo.features.term_structure import compute_term_structure_metrics
from qihuo.data_providers.inventory_provider import InventoryProvider
from qihuo.features.inventory import compute_inventory_metrics
from qihuo.data_providers.positioning_provider import PositioningProvider
from qihuo.features.positioning import compute_positioning_metrics
from qihuo.data_providers.news_provider import NewsProvider
from qihuo.features.news import compute_news_metrics

def load_config() -> dict:
    """尝试加载 qihuo/config/core.yaml；若不可用则使用内置默认。"""
    default_cfg = {
        "project": {
            "name": "qihuo-ai-trader",
            "timezone": "Asia/Shanghai",
            "output_dir": "qihuo/output",
        }
    }
    cfg_path = Path("qihuo/config/core.yaml")
    if cfg_path.exists():
        try:
            import yaml  # type: ignore

            with cfg_path.open("r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            # 浅合并
            # 深合并（简单实现）
            def _merge(a, b):
                for k, v in b.items():
                    if isinstance(v, dict) and isinstance(a.get(k), dict):
                        _merge(a[k], v)
                    else:
                        a[k] = v
                return a
            default_cfg = _merge(default_cfg, user_cfg)
        except Exception:
            pass
    return default_cfg


def build_report_skeleton(symbol: str, date_str: str, cfg: dict) -> dict:
    now_iso = datetime.now().isoformat(timespec="seconds")
    return {
        "symbol": symbol,
        "as_of": date_str,
        "signals": {
            "direction": "neutral",
            "conviction": 0.0,
            "timeframe": "swing",
            "rationale_bullets": [
                "占位：待接入技术/期限结构/新闻三线分析",
            ],
        },
        "entry_plan": {
            "triggers": [],
            "position_sizing": {"method": "vol_target", "target_vol": 0.15, "max_margin_ratio": 0.30},
            "execution": {"participation_rate": 0.1, "algo": "TWAP"},
        },
        "risk": {
            "stop_loss": {"method": "ATR", "multiplier": 2.5},
            "take_profit": {"rr": 2.0},
            "overnight_limits": {"allow": True, "notes": "占位"},
            "stress_flags": [],
        },
        "roll_strategy": {"rule": "主力切换前N天展期", "spread_guard": ">"},
        "audit": {
            "generated_at": now_iso,
            "project": cfg.get("project", {}).get("name", "qihuo-ai-trader"),
            "tools_called": [],
            "llm_models": [],
            "confidence": 0.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily AI futures analysis (skeleton)")
    parser.add_argument("--symbol", required=True, help="品种代码，例如 RB/CU/LH")
    parser.add_argument("--date", required=True, help="交易日，格式 YYYY-MM-DD 或 YYYYMMDD")
    args = parser.parse_args()

    # 规范化日期
    date_in = args.date.replace("/", "-")
    if len(date_in) == 8 and date_in.isdigit():
        date_in = f"{date_in[0:4]}-{date_in[4:6]}-{date_in[6:8]}"

    cfg = load_config()
    out_dir = Path(cfg.get("project", {}).get("output_dir", "qihuo/output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    report = build_report_skeleton(args.symbol.upper(), date_in, cfg)

    # 技术分析师（占位运行：provider 未实现将返回占位报告）
    provider = get_provider()
    tech = TechnicalAnalyst(provider=provider)
    tech_res = tech.analyze(symbol=report["symbol"], as_of=report["as_of"])
    report.update(tech_res)

    # 基差与期现（基础版）：若缓存存在则计算，否则跳过
    try:
        basis_provider = BasisProvider(cache_dir=cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache"))
        basis_df = basis_provider.get_spot_price_daily(report["symbol"])
        basis_res = compute_basis_metrics(basis_df, report["symbol"]) if basis_df is not None and len(basis_df) > 0 else {"notes": ["无基差缓存"]}
        report["basis_report"] = basis_res
    except Exception:
        pass

    # 期限结构/展期（基础版）：读取 roll_{VAR}.csv（需用变量，如RB/TA），与 symbol 大多数一致，此处直接用 symbol 传入
    try:
        ts_provider = TermStructureProvider(cache_dir=cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache"))
        roll_df = ts_provider.get_roll_by_date(report["symbol"])
        ts_res = compute_term_structure_metrics(roll_df, report["symbol"]) if roll_df is not None and len(roll_df) > 0 else {"notes": ["无期限结构缓存"]}
        report["term_structure_report"] = ts_res
    except Exception:
        pass

    # 席位与拥挤度（缓存 positioning_{SYMBOL}.csv）
    try:
        pos_provider = PositioningProvider(cache_dir=cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache"))
        pos_df = pos_provider.get_positioning(report["symbol"])
        pos_res = compute_positioning_metrics(pos_df, report["symbol"]) if pos_df is not None and len(pos_df) > 0 else {"notes": ["无席位缓存"]}
        report["positioning_report"] = pos_res
    except Exception:
        pass

    # 新闻/事件（缓存 news_{key}.csv；示例用中文品种映射）
    try:
        news_provider = NewsProvider(cache_dir=cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache"))
        sym2news = {"RB": "钢铁", "TA": "化工", "CU": "铜"}
        key = sym2news.get(report["symbol"].upper(), report["symbol"].upper())
        news_df = news_provider.get_news(key)
        news_res = compute_news_metrics(news_df, key) if news_df is not None and len(news_df) > 0 else {"notes": ["无新闻缓存"]}
        report["news_report"] = news_res
    except Exception:
        pass

    # 交易成本与约束：按你的要求，暂不纳入本流程

    # 库存/仓单（示例：用户可指定series；此处默认尝试 inventory_{SYMBOL} 与手工指定映射）
    try:
        inv_provider = InventoryProvider(cache_dir=cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache"))
        # 简易映射：RB -> "螺纹钢"（若无则跳过）。实际中应配置在config里
        sym2series = {
            "RB": "螺纹钢",
            "TA": "PTA",
            "CU": "沪铜",
        }
        series = sym2series.get(report["symbol"].upper())
        inv_df = inv_provider.get_inventory_series(series) if series else None
        inv_res = compute_inventory_metrics(inv_df, series) if inv_df is not None and len(inv_df) > 0 else {"notes": ["无库存缓存"]}
        report["inventory_report"] = inv_res
    except Exception:
        pass

    # 基于技术面生成顶层 signals
    try:
        tr = tech_res.get("technical_report", {})
        # 兼容旧schema（无daily/weekly时）
        if "daily" not in tr and ("direction" in tr or "triggers" in tr):
            # 将单层结构包装为daily，weekly给空
            daily = {
                "direction": tr.get("direction", "neutral"),
                "strength": tr.get("strength", 0.0),
                "triggers": tr.get("triggers", []),
                "volatility": tr.get("volatility", {"atr": None, "regime": "low"}),
                "oi_divergence": tr.get("oi_divergence", "neutral"),
                "notes": tr.get("notes", []),
            }
            weekly = {"direction": "neutral", "strength": 0.0, "triggers": [], "volatility": {"atr": None, "regime": "low"}, "oi_divergence": "neutral", "notes": ["无周线数据"]}
            tech_res["technical_report"] = {"timeframes": ["D"], "daily": daily, "weekly": weekly}
            tr = tech_res["technical_report"]
        daily = tr.get("daily", {})
        weekly = tr.get("weekly", {})

        def _dir_score(d: str) -> float:
            return 1.0 if d == "long" else (-1.0 if d == "short" else 0.0)

        score = 0.6 * _dir_score(daily.get("direction")) + 0.4 * _dir_score(weekly.get("direction"))
        direction = "neutral"
        if score > 0.1:
            direction = "long"
        elif score < -0.1:
            direction = "short"

        # 置信度：由强度 + 触发点 + 背离修正
        sd = float(daily.get("strength", 0.0) or 0.0)
        sw = float(weekly.get("strength", 0.0) or 0.0)
        base_conv = max(0.0, min(1.0, 0.6 * sd + 0.4 * sw))

        triggers_d = list(daily.get("triggers", []) or [])
        triggers_w = list(weekly.get("triggers", []) or [])
        trig_bonus = min(0.2, 0.05 * min(4, len(triggers_d) + len(triggers_w)))

        oi_adj = 0.0
        if (daily.get("oi_divergence") == "confirm") or (weekly.get("oi_divergence") == "confirm"):
            oi_adj += 0.1
        if (daily.get("oi_divergence") == "conflict") or (weekly.get("oi_divergence") == "conflict"):
            oi_adj -= 0.05

        conviction = max(0.0, min(1.0, base_conv + trig_bonus + oi_adj))
        if direction == "neutral":
            conviction = 0.0

        # 组装要点（取前3个触发）
        bullets = []
        for t in triggers_d[:2]:
            bullets.append(f"[D] {t}")
        for t in triggers_w[:1]:
            bullets.append(f"[W] {t}")
        if daily.get("oi_divergence"):
            bullets.append(f"[D] OI背离: {daily.get('oi_divergence')}")
        if weekly.get("oi_divergence"):
            bullets.append(f"[W] OI背离: {weekly.get('oi_divergence')}")

        report["signals"] = {
            "direction": direction,
            "conviction": round(float(conviction), 3),
            "timeframe": "swing",
            "rationale_bullets": bullets or ["技术面信号有限"],
        }
        report["signals_source"] = "rule"
    except Exception:
        # 出现异常时保持骨架
        pass

    # 技术面文字/判定（LLM 可选）
    try:
        tr = report.get("technical_report", {})
        daily = tr.get("daily", {})
        weekly = tr.get("weekly", {})
        analysis_mode = cfg.get("llm", {}).get("analysis_mode", "rule")
        if analysis_mode == "llm":
            # 将最终判定交给 LLM，严格JSON输出并回填顶层signals
            ds = DeepSeekClient()
            llm_input = {
                "symbol": report["symbol"],
                "as_of": report["as_of"],
                "daily": daily,
                "weekly": weekly,
                "rule_signals": report.get("signals", {}),
            }
            obj, raw, err = ds.analyze_technical_json_with_raw(llm_input)
            if obj and isinstance(obj, dict):
                dir_map = {"long": "long", "short": "short", "neutral": "neutral"}
                direction = dir_map.get(str(obj.get("direction", "neutral")).lower(), "neutral")
                try:
                    conv = float(obj.get("conviction", 0.0))
                except Exception:
                    conv = 0.0
                bullets = obj.get("bullets", [])
                if not isinstance(bullets, list):
                    bullets = []
                report["signals"] = {
                    "direction": direction,
                    "conviction": max(0.0, min(1.0, conv)),
                    "timeframe": "swing",
                    "rationale_bullets": bullets[:5] or ["(LLM未给出要点)"],
                }
                report["signals_source"] = "llm"
                report["technical_llm_decision"] = {
                    "direction": direction,
                    "conviction": max(0.0, min(1.0, conv)),
                    "bullets": bullets[:5] if isinstance(bullets, list) else [],
                    "raw_present": True,
                    "error": None,
                }
                # 可选：将原始响应以文件落盘，便于离线核查（避免JSON过大塞入报告）
                try:
                    raw_dir = Path(cfg.get("project", {}).get("output_dir", "qihuo/output")) / "llm_raw"
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    raw_file = raw_dir / f"tech_decision_{report['symbol']}_{report['as_of']}.txt"
                    with raw_file.open("w", encoding="utf-8") as f:
                        f.write(raw or "")
                except Exception:
                    pass
                # 同时生成文字总结
                text = ds.summarize_technical(symbol=report["symbol"], as_of=report["as_of"], daily=daily, weekly=weekly)
                report["technical_summary"] = text or "(LLM未返回文字总结)"
            else:
                # 回退到仅文字总结
                text = DeepSeekClient().summarize_technical(symbol=report["symbol"], as_of=report["as_of"], daily=daily, weekly=weekly)
                report["technical_summary"] = text or "(LLM未返回，保留规则结论)"
                report["technical_llm_decision"] = {
                    "status": "failed",
                    "raw_present": bool(raw),
                    "error": err or "unknown",
                }
        else:
            # 仅文字化总结
            ds = DeepSeekClient()
            summary = ds.summarize_technical(symbol=report["symbol"], as_of=report["as_of"], daily=daily, weekly=weekly)
            if not summary:
                bullets = report.get("signals", {}).get("rationale_bullets", [])
                direction = report.get("signals", {}).get("direction", "neutral")
                conv = report.get("signals", {}).get("conviction", 0.0)
                summary = f"技术面结论：方向={direction}，置信度={conv}。要点：" + "; ".join(bullets[:3])
            report["technical_summary"] = summary
    except Exception:
        pass

    out_path = out_dir / f"report_{report['symbol']}_{report['as_of']}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(str(out_path))


if __name__ == "__main__":
    main()


