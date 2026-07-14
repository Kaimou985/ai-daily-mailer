from __future__ import annotations

import re

from deep_translator import GoogleTranslator

from .models import Article


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def looks_chinese(text: str) -> bool:
    compact = "".join(text.split())
    if not compact:
        return True
    chinese_count = len(CJK_RE.findall(compact))
    return chinese_count >= 2 and chinese_count / len(compact) >= 0.2


def _translate(translator: GoogleTranslator, text: str, limit: int) -> str:
    if not text or looks_chinese(text):
        return text
    # 免费翻译服务对单次文本有长度限制。邮件摘要无需传入整篇原文。
    translated = translator.translate(text[:limit])
    return translated.strip() if translated else text


def _paragraphize(text: str) -> str:
    if len(text) < 220:
        return text
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]
    if len(sentences) < 3:
        return text
    paragraphs = ["".join(sentences[index : index + 2]) for index in range(0, len(sentences), 2)]
    return "\n\n".join(paragraphs)


def translate_articles(articles: list[Article]) -> list[str]:
    """使用免费翻译生成中文标题和摘要；单条失败时保留原文。"""
    translator = GoogleTranslator(source="auto", target="zh-CN")
    warnings: list[str] = []
    for article in articles:
        try:
            article.title_zh = _translate(translator, article.title, 500)
        except Exception as exc:
            warnings.append(f"{article.source} 标题翻译失败：{type(exc).__name__}")
        try:
            source_text = article.content or article.summary
            article.summary_zh = _paragraphize(_translate(translator, source_text, 4500))
        except Exception as exc:
            warnings.append(f"{article.source} 摘要翻译失败：{type(exc).__name__}")
    return warnings
