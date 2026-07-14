from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .feeds import clean_text
from .models import Article


SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+")
NOISE_RE = re.compile(
    r"cookie|privacy policy|sign up|subscribe|newsletter|advertisement|all rights reserved",
    re.I,
)
USER_AGENT = "Mozilla/5.0 (compatible; AI-Daily-Brief/0.2; personal digest)"


def extract_article_text(page_html: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")
    for node in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        node.decompose()

    # 部分新闻站会在 JSON-LD 中提供干净的正文。
    raw_soup = BeautifulSoup(page_html, "html.parser")
    for script in raw_soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            candidates = data if isinstance(data, list) else [data]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("articleBody"):
                    body = clean_text(str(candidate["articleBody"]), 12000)
                    if len(body) >= 300:
                        return body
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    container = soup.find("article") or soup.find("main") or soup
    paragraphs: list[str] = []
    seen: set[str] = set()
    for node in container.find_all("p"):
        text = clean_text(node.get_text(" ", strip=True), 3000)
        key = text.lower()
        if len(text) < 55 or NOISE_RE.search(text) or key in seen:
            continue
        seen.add(key)
        paragraphs.append(text)
    return "\n".join(paragraphs)[:12000]


def make_extractive_brief(text: str, max_chars: int) -> str:
    if not text:
        return ""
    sentences = [item.strip() for item in SENTENCE_RE.split(text.replace("\n", " ")) if len(item.strip()) >= 35]
    if not sentences:
        return text[:max_chars]

    chosen: list[str] = []
    length = 0
    for sentence in sentences:
        if length + len(sentence) > max_chars and len(chosen) >= 3:
            break
        chosen.append(sentence)
        length += len(sentence)
        if len(chosen) >= 8:
            break
    return " ".join(chosen)[:max_chars]


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _fetch_one(article: Article, timeout: int, max_chars: int) -> tuple[Article, str | None]:
    # arXiv 的 Feed 本身已包含完整摘要，无需再请求页面。
    if article.category == "论文" or "arxiv.org" in article.url.lower():
        article.content = make_extractive_brief(article.summary, max_chars)
        return article, None
    try:
        session = _session()
        response = session.get(article.url, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        extracted = extract_article_text(response.text)
        source_text = extracted if len(extracted) >= 250 else article.summary
        article.content = make_extractive_brief(source_text, max_chars)
        return article, None
    except Exception as exc:
        article.content = make_extractive_brief(article.summary, max_chars)
        return article, f"{article.source} 正文提取失败，已使用 RSS 摘要：{type(exc).__name__}"


def fetch_article_contents(
    articles: list[Article], timeout: int, max_chars: int, workers: int = 6
) -> list[str]:
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, max(1, len(articles)))) as executor:
        futures = [executor.submit(_fetch_one, article, timeout, max_chars) for article in articles]
        for future in as_completed(futures):
            _, warning = future.result()
            if warning:
                warnings.append(warning)
    return warnings

