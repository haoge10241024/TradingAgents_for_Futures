from __future__ import annotations

import json
from typing import Optional

import httpx

from qihuo.utils.secrets import get_env


class DeepSeekClient:
    """最小DeepSeek客户端：仅用于生成技术面文字总结。

    说明：不做数值计算，只基于我们产出的结构化字段生成中文要点与建议。
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat") -> None:
        self.api_key = api_key or get_env("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    def summarize_technical(self, symbol: str, as_of: str, daily: dict, weekly: dict) -> Optional[str]:
        if not self.api_key:
            return None

        system = "你是资深量化交易研究员。请基于给定的结构化技术面信息，输出简洁中文结论与建议。不要编造数值。"
        user = {
            "symbol": symbol,
            "as_of": as_of,
            "daily": daily,
            "weekly": weekly,
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "max_tokens": 400,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(self.base_url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                return content
        except Exception:
            return None

    def analyze_technical_json(self, payload: dict) -> Optional[dict]:
        """请求LLM返回严格JSON: {direction, conviction, bullets[]}。

        direction: long|short|neutral
        conviction: 0~1
        bullets: 中文要点数组
        """
        if not self.api_key:
            return None

        system = (
            "你是资深量化交易研究员。仅基于提供的结构化技术指标（日/周）进行判断，不要编造数值。"
            "请输出严格JSON，不要附加任何文字。JSON键包括: direction(仅 long|short|neutral),"
            " conviction(0到1的小数), bullets(中文要点字符串数组)。"
        )
        user = payload

        req = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(self.base_url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                # 尝试直接解析
                try:
                    obj = json.loads(content)
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    # 简单提取花括号内容
                    import re
                    m = re.search(r"\{[\s\S]*\}", content)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            return None
                    return None
        except Exception:
            return None

    def analyze_technical_json_with_raw(self, payload: dict):
        """与 analyze_technical_json 类似，但返回 (obj, raw, error)。

        obj: 解析后的JSON(dict)或None
        raw: 原始模型输出字符串（可能含非JSON文本）
        error: 错误描述字符串或None
        """
        if not self.api_key:
            return None, None, "missing_api_key"

        system = (
            "你是资深量化交易研究员。仅基于提供的结构化技术指标（日/周）进行判断，不要编造数值。"
            "请输出严格JSON，不要附加任何文字。JSON键包括: direction(仅 long|short|neutral),"
            " conviction(0到1的小数), bullets(中文要点字符串数组)。"
        )
        req = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        raw = None
        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(self.base_url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                # 解析
                try:
                    obj = json.loads(raw)
                    return (obj if isinstance(obj, dict) else None), raw, None
                except Exception:
                    import re
                    m = re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        try:
                            obj = json.loads(m.group(0))
                            return (obj if isinstance(obj, dict) else None), raw, None
                        except Exception as e:
                            return None, raw, f"json_parse_error: {e}"
                    return None, raw, "no_json_found"
        except Exception as e:
            return None, raw, f"http_error: {e}"

    def analyze_news_json_with_raw(self, items: list[dict], symbol: str) -> tuple[Optional[dict], Optional[str], Optional[str]]:
        """将新闻列表交给LLM，返回严格JSON：
        {
          "events": [ {"time": str, "impact": "bullish|bearish|neutral", "confidence": 0..1, "summary": str}... ],
          "summary": str
        }
        返回 (obj, raw, error)
        """
        if not self.api_key:
            return None, None, "missing_api_key"

        system = (
            "你是资深商品/期货研究员。基于给定新闻列表（time/content），抽取关键事件并评估方向(\"bullish|bearish|neutral\")与置信度(0~1)。"
            "输出严格JSON，不要附加任何文字：{events:[{time, impact, confidence, summary}], summary}。不要编造时间。"
        )
        user = {"symbol": symbol, "items": items[:200]}

        req = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        raw = None
        try:
            with httpx.Client(timeout=25) as client:
                r = client.post(self.base_url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                try:
                    obj = json.loads(raw)
                    return (obj if isinstance(obj, dict) else None), raw, None
                except Exception:
                    import re
                    m = re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        try:
                            return json.loads(m.group(0)), raw, None
                        except Exception as e:
                            return None, raw, f"json_parse_error: {e}"
                    return None, raw, "no_json_found"
        except Exception as e:
            return None, raw, f"http_error: {e}"


    def propose_news_queries_with_raw(self, symbol: str, keywords: list[str], days: int = 7):
        """让LLM产出联网检索的查询语句，返回 (obj, raw, error)。
        期望严格JSON：{"queries": ["...", ...], "must_keywords": ["..."]}
        """
        if not self.api_key:
            return None, None, "missing_api_key"

        system = (
            "你是资深资讯研究员。请基于提供的期货品种与关键词，产出适合中文互联网检索的查询语句，"
            "用于获取过去N天的高相关市场资讯。输出严格JSON且不要附加文字，键包括："
            "queries(字符串数组，长度3~6，按相关度排序)，must_keywords(用于过滤的必含关键词，1~5个)。"
        )
        user = {"symbol": symbol, "keywords": keywords[:10], "days": days}

        req = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        raw = None
        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(self.base_url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                try:
                    obj = json.loads(raw)
                    return (obj if isinstance(obj, dict) else None), raw, None
                except Exception:
                    import re
                    m = re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        try:
                            return json.loads(m.group(0)), raw, None
                        except Exception as e:
                            return None, raw, f"json_parse_error: {e}"
                    return None, raw, "no_json_found"
        except Exception as e:
            return None, raw, f"http_error: {e}"


