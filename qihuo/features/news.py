from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_news_metrics(df: pd.DataFrame, symbol: str) -> Dict:
    """新闻/事件基础指标（不使用LLM，仅基于统计特征）。

    期望列：
      - 发布时间 或 time
      - 内容 或 content
    输出：近7/14/30天新闻条数、近3天热度、简单情绪计数（基于关键词，粗略）、重要性近似（标题包含关键词）。
    """
    result: Dict = {
        "symbol": symbol,
        "counts": {},
        "recent_top": [],
        "sentiment_counts": {},
        "signals": [],
        "notes": [],
    }

    if df is None or len(df) == 0:
        result["notes"].append("无新闻缓存")
        return result

    data = df.copy()
    data = data.rename(columns={"发布时间": "time", "内容": "content"})
    if "time" not in data.columns or "content" not in data.columns:
        result["notes"].append("缺少time/content列")
        return result
    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    data = data.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    now = data["time"].max()
    def _cnt(days: int) -> int:
        since = now - pd.Timedelta(days=days)
        return int((data["time"] >= since).sum())
    result["counts"] = {
        "n7": _cnt(7),
        "n14": _cnt(14),
        "n30": _cnt(30),
    }

    # 近3天热度Top5（按时间倒序）
    since3 = now - pd.Timedelta(days=3)
    recent = data[data["time"] >= since3].sort_values("time", ascending=False).head(5)
    result["recent_top"] = [
        {
            "time": str(r["time"]),
            "content": str(r["content"])[:120],
        }
        for _, r in recent.iterrows()
    ]

    # 简单情绪（关键词计数，示意）
    bullish_kw = ["上调", "涨", "扩大", "改善", "提振", "好转", "超预期"]
    bearish_kw = ["下调", "跌", "收缩", "恶化", "承压", "不及预期"]
    bpos = 0
    bneg = 0
    for txt in data["content"].astype(str).tail(200):
        if any(kw in txt for kw in bullish_kw):
            bpos += 1
        if any(kw in txt for kw in bearish_kw):
            bneg += 1
    result["sentiment_counts"] = {"bullish": bpos, "bearish": bneg}

    # 简单信号
    sigs = []
    if result["counts"].get("n7", 0) >= 50:
        sigs.append("近一周新闻热度高")
    if bpos >= bneg * 1.5 and bpos >= 10:
        sigs.append("新闻情绪偏多")
    if bneg >= bpos * 1.5 and bneg >= 10:
        sigs.append("新闻情绪偏空")
    result["signals"] = sigs
    return result


