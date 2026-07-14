from __future__ import annotations

import calendar
import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from time import struct_time

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Article


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
USER_AGENT = "AI-Daily-Mailer/0.1 (+personal RSS digest)"


def clean_text(value: str, limit: int = 900) -> str:
    text = html.unescape(TAG_RE.sub(" ", value or ""))
    text = SPACE_RE.sub(" ", text).strip()
    return text[:limit]


def _entry_datetime(entry: dict, now: datetime) -> datetime:
    parsed: struct_time | None = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return now
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _entry_url(entry: dict) -> str:
    link = entry.get("link") or entry.get("id") or ""
    if link.startswith("http"):
        return link
    for candidate in entry.get("links", []):
        href = candidate.get("href", "")
        if href.startswith("http"):
            return href
    return ""


def _entry_summary(entry: dict) -> str:
    value = entry.get("summary") or entry.get("description")
    if value:
        return value
    content = entry.get("content") or []
    return content[0].get("value", "") if content else ""


def _dedupe_key(article: Article) -> str:
    base = article.url.rstrip("/").lower() or article.title.lower()
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def fetch_articles(
    sources: list[dict],
    lookback_hours: int,
    timeout: int,
    now: datetime | None = None,
) -> tuple[list[Article], list[str]]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)
    articles: list[Article] = []
    warnings: list[str] = []
    seen: set[str] = set()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))

    for source in sources:
        try:
            response = session.get(source["url"], timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.bozo and not feed.entries:
                raise ValueError(str(feed.bozo_exception))

            added = 0
            for entry in feed.entries:
                published = _entry_datetime(entry, now)
                if published < cutoff or published > now + timedelta(hours=12):
                    continue
                url = _entry_url(entry)
                title = clean_text(entry.get("title", ""), 240)
                if not title or not url:
                    continue
                summary = clean_text(_entry_summary(entry))
                article = Article(
                    title=title,
                    url=url,
                    source=source["name"],
                    category=source.get("category", "AI 资讯"),
                    published_at=published,
                    summary=summary or "请点击原文查看详情。",
                    priority=int(source.get("priority", 0)),
                )
                key = _dedupe_key(article)
                if key not in seen:
                    seen.add(key)
                    articles.append(article)
                    added += 1
            if added == 0:
                warnings.append(f"{source['name']}: 最近 {lookback_hours} 小时无新内容")
        except Exception as exc:  # 单个源失败不影响整封邮件
            warnings.append(f"{source['name']}: {type(exc).__name__} - {exc}")

    articles.sort(key=lambda item: (item.priority, item.published_at), reverse=True)
    return articles, warnings


def select_articles(articles: list[Article], maximum: int, per_source: int) -> list[Article]:
    """限制单一来源占比，避免邮件被 arXiv 等高频源刷屏。"""
    selected: list[Article] = []
    counts: dict[str, int] = {}
    for article in articles:
        if counts.get(article.source, 0) >= per_source:
            continue
        selected.append(article)
        counts[article.source] = counts.get(article.source, 0) + 1
        if len(selected) >= maximum:
            break
    return selected
