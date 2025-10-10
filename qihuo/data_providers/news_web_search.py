from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
from typing import List

import pandas as pd
import requests


def _parse_sina_search_html(html: str) -> pd.DataFrame:
    # 粗略解析：按结果块拆分并抓取时间与标题/摘要
    items: List[dict] = []
    # 结果块以 box-result 或 result-mod 开头
    blocks = re.split(r'<div[^>]+class="[^"]*(?:box-result|result-mod)[^"]*"[^>]*>', html)[1:]
    for block in blocks:
        # 时间
        m_time = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}[日\s]\s*\d{1,2}:\d{2})', block)
        ts = None
        if m_time:
            ts_raw = m_time.group(1)
            ts_norm = (
                ts_raw.replace('年', '-').replace('月', '-').replace('日', ' ').replace('/', '-')
            )
            try:
                ts = datetime.strptime(ts_norm.strip(), '%Y-%m-%d %H:%M')
            except Exception:
                try:
                    ts = datetime.strptime(ts_norm.strip(), '%Y-%m-%d')
                except Exception:
                    ts = None
        # 标题与链接
        m_title = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        url = m_title.group(1).strip() if m_title else ''
        title = re.sub(r'<[^>]+>', '', (m_title.group(2) if m_title else '')).strip()
        # 来源（域名）
        source = ''
        if url:
            m_dom = re.search(r'https?://([^/]+)/', url + '/')
            source = (m_dom.group(1) if m_dom else '').lower()
        # 摘要
        m_sum = re.search(r'<p[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</p>', block, flags=re.S)
        summary = re.sub(r'<[^>]+>', '', m_sum.group(1)).strip() if m_sum else ''
        content = title if summary == '' else f'{title} | {summary}'
        if content:
            items.append({'time': ts or pd.NaT, 'title': title, 'content': content, 'url': url, 'source': source})
    if not items:
        return pd.DataFrame(columns=['time', 'content'])
    df = pd.DataFrame(items)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    return df.dropna(subset=['content']).reset_index(drop=True)


def search_sina_finance(keyword: str, max_pages: int = 2) -> pd.DataFrame:
    """按关键词抓取新浪财经新闻搜索结果，返回列 time, content。
    """
    all_df = pd.DataFrame(columns=['time', 'title', 'content', 'url', 'source'])
    for page in range(1, max_pages + 1):
        url = (
            f'https://search.sina.com.cn/?q={keyword}&c=news&from=channel&col=finance'
            f'&range=all&source=all&dedup=1&sort=time&page={page}'
        )
        try:
            r = requests.get(url, timeout=12)
            r.encoding = r.apparent_encoding or 'utf-8'
            df = _parse_sina_search_html(r.text)
            if df is not None and len(df) > 0:
                all_df = pd.concat([all_df, df], ignore_index=True)
        except Exception:
            continue
    if len(all_df) == 0:
        return all_df
    all_df = (
        all_df.drop_duplicates(subset=['time', 'content']).sort_values('time').reset_index(drop=True)
    )
    return all_df


def search_google_news_rss(query: str, max_pages: int = 1) -> pd.DataFrame:
    """Google News RSS 简易抓取与解析。返回列 time,title,content,url,source
    注：部分环境可能不可达，失败时返回空表。
    """
    rows: list[dict] = []
    for page in range(max_pages):
        # Google News RSS 不严格分页，这里仅单页或尝试不同参数可扩展
        url = (
            f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        )
        try:
            r = requests.get(url, timeout=12)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.text)
            for item in root.findall('.//item'):
                title_el = item.find('title')
                link_el = item.find('link')
                pub_el = item.find('pubDate')
                title = (title_el.text or '').strip() if title_el is not None else ''
                link = (link_el.text or '').strip() if link_el is not None else ''
                pub = (pub_el.text or '').strip() if pub_el is not None else ''
                # 源域名
                m_dom = re.search(r'https?://([^/]+)/', link + '/')
                source = (m_dom.group(1) if m_dom else '').lower()
                # 时间
                try:
                    ts = pd.to_datetime(pub, errors='coerce')
                except Exception:
                    ts = pd.NaT
                if title or link:
                    rows.append({
                        'time': ts,
                        'title': title,
                        'content': title,
                        'url': link,
                        'source': source,
                    })
        except Exception:
            continue
    if not rows:
        return pd.DataFrame(columns=['time','title','content','url','source'])
    df = pd.DataFrame(rows)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['title','url'], how='all')
    return df.drop_duplicates(subset=['time','title','url']).sort_values('time').reset_index(drop=True)


