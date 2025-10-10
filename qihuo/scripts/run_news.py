import argparse
import json
from pathlib import Path

# 保障可直接运行：将项目根目录加入 sys.path
import sys
_CURR = Path(__file__).resolve()
_ROOT = _CURR.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qihuo.analysis.news_aggregator import aggregate_news, NewsAggConfig
from qihuo.scripts.run_daily import load_config


def main() -> None:
    p = argparse.ArgumentParser(description="新闻分析师：汇集近N天新闻列表，供LLM分析")
    p.add_argument("--symbol", required=True, help="品种代码，如 RB/TA/CU")
    p.add_argument("--symbol-cn", default=None, help="中文品种/专题，如 钢铁/铜 等")
    p.add_argument("--days", type=int, default=14, help="时间窗口天数")
    p.add_argument("--as-of", default=None, help="基准日期（YYYY-MM-DD），围绕该日期做时间窗过滤")
    p.add_argument("--max-items", type=int, default=200, help="最多条目数")
    p.add_argument("--try-online", action="store_true", help="缓存为空时尝试在线拉取")
    p.add_argument("--keywords", default=None, help="以逗号分隔的关键词列表，用于过滤相关新闻")
    p.add_argument("--llm-online", action="store_true", help="启用LLM生成检索查询并辅助在线抓取")
    p.add_argument("--out", default=None, help="输出文件（默认 qihuo/output/news_{symbol}.json）")
    args = p.parse_args()

    cfg = load_config()
    cache_dir = cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache")
    out_dir = Path(cfg.get("project", {}).get("output_dir", "qihuo/output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    news_cfg = NewsAggConfig(days=args.days, max_items=args.max_items, cache_dir=cache_dir)
    kw_list = [s.strip() for s in (args.keywords.split(",") if args.keywords else []) if s.strip()]
    agg = aggregate_news(args.symbol.upper(), args.symbol_cn, try_online=args.try_online, config=news_cfg, keywords=kw_list, as_of=args.as_of)

    # 可选：调用LLM生成查询，再进行补充抓取（当前用新浪检索执行）
    if args.llm_online:
        try:
            from qihuo.llm.deepseek_client import DeepSeekClient
            from qihuo.analysis.news_aggregator import _default_keywords_for_symbol
            from qihuo.data_providers.news_web_search import search_sina_finance
            ds = DeepSeekClient()
            seed_kws = kw_list or _default_keywords_for_symbol(args.symbol.upper())
            obj, raw, err = ds.propose_news_queries_with_raw(args.symbol.upper(), seed_kws, days=args.days)
            queries = []
            if obj and isinstance(obj, dict):
                queries = list(obj.get("queries", []))[:6]
            merged = None
            for q in queries:
                df = search_sina_finance(q, max_pages=2)
                merged = df if merged is None else (merged.append(df, ignore_index=True))
            if merged is not None and len(merged) > 0:
                # 合并到 agg.items
                from datetime import timedelta
                import pandas as pd
                items = agg.get("items", [])
                extra = [
                    {
                        "time": str(pd.to_datetime(r["time"], errors="coerce")),
                        "title": str(r.get("title", ""))[:500],
                        "content": str(r.get("content", ""))[:2000],
                        "url": str(r.get("url", ""))[:1000],
                        "source": str(r.get("source", ""))[:200],
                    }
                    for _, r in merged.iterrows()
                ]
                items.extend(extra)
                # 去重
                seen = set()
                uniq = []
                for it in items:
                    key = (it.get("time"), it.get("title"), it.get("url"))
                    if key in seen:
                        continue
                    seen.add(key)
                    uniq.append(it)
                agg["items"] = uniq[: news_cfg.max_items]
                agg["counts"] = len(agg["items"])
                agg.setdefault("audit", {})["tools_called"] = ["llm_query+sina"]
        except Exception:
            pass

    out_path = Path(args.out) if args.out else (out_dir / f"news_{args.symbol.upper()}.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    print(str(out_path))


if __name__ == "__main__":
    main()


