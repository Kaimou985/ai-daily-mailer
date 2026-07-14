from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import Settings
from .models import Article


JSON_RE = re.compile(r"\{.*\}", re.S)
VALID_CATEGORIES = {
    "官方动态",
    "模型产品",
    "开源项目",
    "研究论文",
    "行业资讯",
}


def _parse_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = JSON_RE.search(content)
        if not match:
            raise ValueError("模型未返回有效 JSON")
        return json.loads(match.group(0))


def _chat_json(
    settings: Settings,
    system_prompt: str,
    user_payload: dict,
    max_tokens: int,
) -> dict:
    response = requests.post(
        f"{settings.llm_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.llm_model,
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
        },
        timeout=max(120, settings.request_timeout),
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    if not content:
        raise ValueError("模型返回了空内容")
    return _parse_json(content)


def _summarize_one(article: Article, settings: Settings) -> Article:
    system_prompt = (
        "你是严谨的 AI 行业编辑。请阅读给定文章正文，用中文重写为一篇可独立阅读的短简报。"
        "必须忠于原文，不得补充原文没有的数字、结论或背景。"
        "保留公司、模型、产品、论文的英文专有名称。"
        "输出严格 JSON，不要 Markdown。"
    )
    payload = {
        "task": "总结整篇文章",
        "requirements": [
            "title_zh 为准确简洁的中文标题",
            "summary_zh 为 180-320 个中文字的完整小短文，说清事件、关键细节、结果与影响",
            "why_it_matters 用 1 句话说明对 AI 行业或开发者的意义",
            "category 只能是官方动态、模型产品、开源项目、研究论文、行业资讯之一",
        ],
        "json_schema": {
            "title_zh": "string",
            "summary_zh": "string",
            "why_it_matters": "string",
            "category": "string",
        },
        "article": {
            "title": article.title,
            "source": article.source,
            "published_category": article.category,
            "body": (article.content or article.summary)[: settings.llm_content_chars],
        },
    }
    result = _chat_json(settings, system_prompt, payload, max_tokens=1200)
    article.title_zh = str(result.get("title_zh", "")).strip() or article.title
    article.summary_zh = str(result.get("summary_zh", "")).strip()
    article.why_it_matters = str(result.get("why_it_matters", "")).strip()
    category = str(result.get("category", "")).strip()
    if category in VALID_CATEGORIES:
        article.category = category
    if not article.summary_zh:
        raise ValueError("模型未生成简报正文")
    return article


def _build_overview(articles: list[Article], settings: Settings) -> str:
    system_prompt = (
        "你是 AI 行业日报主编。根据多条已核对的简报，写出今日 AI 动态总览。"
        "只综合给定内容，不得添加外部信息。输出严格 JSON。"
    )
    payload = {
        "task": "用 120-220 个中文字写成一段连贯的今日总览，归纳 2-4 条主线，避免简单罗列标题",
        "json_schema": {"overview": "string"},
        "briefs": [
            {
                "title": article.display_title,
                "source": article.source,
                "summary": article.display_summary,
            }
            for article in articles
            if article.summary_zh
        ],
    }
    result = _chat_json(settings, system_prompt, payload, max_tokens=600)
    return str(result.get("overview", "")).strip()


def enrich_with_llm(
    articles: list[Article], settings: Settings
) -> tuple[str, list[Article], list[str]]:
    if not articles:
        return "今日暂无可总结的 AI 资讯。", [], []
    if not settings.llm_enabled:
        return "", articles, ["未配置模型 API"]

    failed: list[Article] = []
    warnings: list[str] = []
    with ThreadPoolExecutor(
        max_workers=min(settings.llm_max_workers, len(articles))
    ) as executor:
        futures = {
            executor.submit(_summarize_one, article, settings): article
            for article in articles
        }
        for future in as_completed(futures):
            article = futures[future]
            try:
                future.result()
            except Exception as exc:
                failed.append(article)
                warnings.append(
                    f"{article.source} 模型总结失败：{type(exc).__name__} - {exc}"
                )

    successful = [article for article in articles if article not in failed]
    if not successful:
        raise RuntimeError("所有文章的模型总结均失败")
    try:
        overview = _build_overview(successful, settings)
    except Exception as exc:
        warnings.append(f"今日总览生成失败：{type(exc).__name__} - {exc}")
        overview = "今日 AI 资讯已由 DeepSeek 逐篇阅读并整理。"
    return overview, failed, warnings
