from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from qihuo.data_providers.news_provider import NewsProvider
from qihuo.data_providers.news_web_search import search_sina_finance, search_google_news_rss


@dataclass
class NewsAggConfig:
    days: int = 14
    max_items: int = 200
    cache_dir: str = "qihuo/.data/cache"


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = d.rename(columns={"发布时间": "time", "内容": "content"})
    if "time" not in d.columns:
        d["time"] = pd.NaT
    if "content" not in d.columns:
        d["content"] = ""
    d["time"] = pd.to_datetime(d["time"], errors="coerce")
    d = d.dropna(subset=["time"]).drop_duplicates(subset=["time", "content"]).sort_values("time")
    return d.reset_index(drop=True)


def _default_keywords_for_symbol(symbol: str) -> List[str]:
    s = symbol.upper()
    # 黑色系
    if s == "RB":
        return ["螺纹钢", "螺纹", "钢筋", "钢铁", "建材", "钢坯", "废钢", "成材", "钢厂", "钢价", "钢材", "钢贸", "钢市", "唐山钢坯", "HRB400"]
    if s == "HC":
        return ["热轧卷板", "热卷", "热轧", "钢铁", "黑色系"]
    if s == "I":
        return ["铁矿石", "铁矿", "矿石", "黑色系", "唐山港口", "普氏指数"]
    if s == "J":
        return ["焦炭", "黑色系", "钢厂", "独立焦化", "焦企"]
    if s == "JM":
        return ["焦煤", "炼焦煤", "主焦煤", "黑色系", "钢厂", "煤矿"]
    if s == "ZC":
        return ["动力煤", "煤炭", "电厂日耗", "煤价"]

    # 有色
    if s == "CU":
        return ["铜", "电解铜", "阴极铜", "废铜", "铜精矿"]
    if s == "AL":
        return ["铝", "电解铝", "氧化铝", "再生铝"]
    if s == "ZN":
        return ["锌", "电解锌", "锌锭"]
    if s == "NI":
        return ["镍", "电解镍", "镍铁", "不锈钢"]
    if s == "SN":
        return ["锡", "电解锡"]
    if s == "PB":
        return ["铅", "电解铅"]
    if s == "SS":
        return ["不锈钢", "不锈钢卷", "300系"]
    if s == "AU":
        return ["黄金", "金价", "金市", "金饰"]
    if s == "AG":
        return ["白银", "银价"]

    # 能化
    if s == "SC":
        return ["原油", "国际油价", "布伦特", "WTI", "OPEC"]
    if s == "FU":
        return ["燃料油", "船燃", "油品"]
    if s == "BU":
        return ["沥青", "重交沥青", "炼厂"]
    if s == "LU":
        return ["低硫燃料油", "船燃"]
    if s == "RU":
        return ["天然橡胶", "橡胶", "轮胎", "胶价", "泰国橡胶"]
    if s == "NR":
        return ["20号胶", "橡胶", "轮胎"]
    if s == "MA":
        return ["甲醇", "煤制甲醇", "港口库存"]
    if s == "EG":
        return ["乙二醇", "MEG", "涤纶"]
    if s == "EB":
        return ["苯乙烯", "SM", "化工"]
    if s == "L":
        return ["LLDPE", "PE", "塑料", "线性低密度聚乙烯"]
    if s == "PP":
        return ["聚丙烯", "PP", "塑料"]
    if s == "V":
        return ["PVC", "聚氯乙烯", "电石法"]
    if s == "TA":
        return ["PTA", "精对苯二甲酸", "涤纶", "聚酯"]
    if s == "PF":
        return ["短纤", "涤纶短纤", "聚酯"]
    if s == "FG":
        return ["玻璃", "浮法玻璃", "白玻", "建材"]
    if s == "SA":
        return ["纯碱", "碳酸钠", "光伏玻璃"]
    if s == "SP":
        return ["纸浆", "浆价", "阔叶浆", "针叶浆"]
    if s == "SF":
        return ["硅铁", "铁合金", "金属硅"]
    if s == "SM":
        return ["锰硅", "铁合金"]

    # 农产品
    if s == "SR":
        return ["白糖", "食糖", "糖价", "产销数据"]
    if s == "CF":
        return ["棉花", "棉价", "纺织"]
    if s == "CJ":
        return ["红枣", "枣价"]
    if s == "AP":
        return ["苹果", "水果"]
    if s == "RM":
        return ["菜粕", "水产饲料", "压榨"]
    if s == "M":
        return ["豆粕", "大豆压榨", "生猪饲料"]
    if s == "Y":
        return ["豆油", "油脂", "棕榈油"]
    if s == "P":
        return ["棕榈油", "油脂"]
    if s == "C":
        return ["玉米", "饲料", "淀粉"]
    if s == "CS":
        return ["玉米淀粉", "淀粉"]
    if s == "JD":
        return ["鸡蛋", "蛋价", "蛋鸡存栏"]
    return []


def aggregate_news(symbol: str, symbol_cn: Optional[str], try_online: bool, config: Optional[NewsAggConfig] = None, keywords: Optional[List[str]] = None, as_of: Optional[str] = None) -> Dict:
    cfg = config or NewsAggConfig()
    provider = NewsProvider(cache_dir=cfg.cache_dir)

    # 读缓存（先按symbol_cn，否则按symbol）
    key_primary = symbol_cn or symbol.upper()
    df = provider.get_news(key_primary)

    # 在线(可选) + 多类别回退（SHMET仅部分品类，如RB无钢铁类别，回退到“要闻/全部”）
    merged = pd.DataFrame()
    if try_online:
        try:
            import akshare as ak  # type: ignore
            # 首选类别
            keys_to_try: List[str] = []
            metal_map = {"CU": "铜", "AL": "铝", "ZN": "锌", "NI": "镍", "SN": "锡", "AG": "贵金属", "AU": "贵金属"}
            if symbol.upper() in metal_map:
                keys_to_try.append(metal_map[symbol.upper()])
            if symbol_cn:
                keys_to_try.append(symbol_cn)
            keys_to_try.extend([symbol.upper(), "要闻", "全部"])  # 回退顺序

            seen: set[str] = set()
            for k in keys_to_try:
                if k in seen:
                    continue
                seen.add(k)
                try:
                    raw = ak.futures_news_shmet(symbol=k)
                    if raw is not None and len(raw) > 0:
                        merged = pd.concat([merged, raw], ignore_index=True) if len(merged) > 0 else raw
                except Exception:
                    continue
            # 若在线抓到内容则覆盖df，并统一缓存为 news_{symbol}.csv
            if merged is not None and len(merged) > 0:
                df = merged
                try:
                    Path(cfg.cache_dir).mkdir(parents=True, exist_ok=True)
                    (Path(cfg.cache_dir) / f"news_{symbol.upper()}.csv").write_text(
                        df.to_csv(index=False, encoding="utf-8-sig"), encoding="utf-8"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    d = _normalize(df) if df is not None and len(df) > 0 else pd.DataFrame(columns=["time", "content"])

    # 追加：新浪财经关键词搜索（提升RB/非金属类相关度）
    try:
        kw_join = " ".join(_default_keywords_for_symbol(symbol)[:3] or [symbol])
        sina_df = search_sina_finance(kw_join, max_pages=2)
        if len(sina_df) > 0:
            d = pd.concat([d, sina_df], ignore_index=True)
    except Exception:
        pass

    # 追加：Google News RSS 搜索
    try:
        kw_join = " ".join(_default_keywords_for_symbol(symbol)[:3] or [symbol])
        g_df = search_google_news_rss(kw_join, max_pages=1)
        if len(g_df) > 0:
            d = pd.concat([d, g_df], ignore_index=True)
    except Exception:
        pass

    # 统一时区到上海本地并去除tz，避免tz混合比较报错
    if len(d) > 0:
        try:
            d["time"] = pd.to_datetime(d["time"], errors="coerce", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
        except Exception:
            d["time"] = pd.to_datetime(d["time"], errors="coerce")

    # 时间窗口过滤（支持 as_of）
    if len(d) > 0:
        end = pd.to_datetime(as_of) if as_of else d["time"].max()
        start = end - timedelta(days=cfg.days)
        d = d[(d["time"] >= start) & (d["time"] <= end)].tail(cfg.max_items)

    # 关键词过滤（若提供keywords，否则对RB/HC等使用内置关键词）
    kws = [k for k in (keywords or []) if isinstance(k, str) and k.strip()]
    if not kws:
        kws = _default_keywords_for_symbol(symbol)
    if kws:
        mask = pd.Series([False] * len(d), index=d.index)
        for k in kws:
            mask = mask | d["content"].astype(str).str.contains(k, na=False)
        d = d[mask]

    # 规范输出结构（加入 title/url/source，若无则回退空串）
    items: List[Dict] = [
        {
            "time": str(r.get("time")),
            "title": ("" if str(r.get("title", "")).lower() == "nan" else str(r.get("title", "")))[:500],
            "content": ("" if str(r.get("content", "")).lower() == "nan" else str(r.get("content", "")).strip())[:2000],
            "url": ("" if str(r.get("url", "")).lower() == "nan" else str(r.get("url", "")))[:1000],
            "source": ("" if str(r.get("source", "")).lower() == "nan" else str(r.get("source", "")))[:200],
        }
        for _, r in d.iterrows()
    ]

    return {
        "symbol": symbol.upper(),
        "window_days": cfg.days,
        "items": items,
        "counts": len(items),
        "audit": {"cache_dir": cfg.cache_dir, "source": "shmet+cache+sina+google+keywords" if kws else "shmet+cache+sina+google"},
    }


