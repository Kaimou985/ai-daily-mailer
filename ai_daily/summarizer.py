from __future__ import annotations

import json
import re

import requests

from .config import Settings
from .models import Article


JSON_RE = re.compile(r"\{.*\}", re.S)


def _article_payload(articles: list[Article]) -> list[dict]:
    return [
        {
            "id": index,
            "title": item.title,
            "source": item.source,
            "category": item.category,
            "summary": (item.content or item.summary)[:2200],
        }
        for index, item in enumerate(articles)
    ]


def enrich_with_llm(articles: list[Article], settings: Settings) -> str:
    if not articles:
        return "今日暂未抓取到符合时间范围的 AI 资讯。"
    if not settings.llm_enabled:
        return "今日 AI 资讯已按官方来源优先级和发布时间整理。"

    system_prompt = (
        "你是一名严谨的 AI 行业编辑。仅根据输入内容编写中文简报，不得虚构。"
        "保留产品、模型、公司和论文的英文专有名称。"
        "返回严格 JSON，不要 Markdown。"
    )
    user_prompt = {
        "task": "生成中文 AI 每日简报",
        "output_schema": {
            "overview": "80-150 字的今日总览",
            "items": [
                {
                    "id": "对应输入 id",
                    "title_zh": "准确简洁的中文标题",
                    "summary_zh": "3-6 句可独立阅读的中文简报，包含事件、关键细节和影响",
                    "why_it_matters": "1 句说明为什么值得关注",
                    "category": "官方动态/模型产品/开源项目/研究论文/行业资讯之一",
                }
            ],
        },
        "articles": _article_payload(articles),
    }
    response = requests.post(
        f"{settings.llm_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
        },
        timeout=max(60, settings.request_timeout),
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    match = JSON_RE.search(content)
    if not match:
        raise ValueError("模型未返回有效 JSON")
    result = json.loads(match.group(0))
    for item in result.get("items", []):
        index = item.get("id")
        if not isinstance(index, int) or not 0 <= index < len(articles):
            continue
        article = articles[index]
        article.title_zh = str(item.get("title_zh", "")).strip()
        article.summary_zh = str(item.get("summary_zh", "")).strip()
        article.why_it_matters = str(item.get("why_it_matters", "")).strip()
        article.category = str(item.get("category", article.category)).strip() or article.category
    return str(result.get("overview", "")).strip() or "今日 AI 重要动态已整理完毕。"
