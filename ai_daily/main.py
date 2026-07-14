from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ROOT, load_settings, load_sources
from .article_content import fetch_article_contents
from .digest import build_html, build_text
from .feeds import fetch_articles, select_articles
from .mailer import send_email
from .summarizer import enrich_with_llm
from .translation import translate_articles


def run(preview: bool = False) -> Path | None:
    settings = load_settings()
    articles, warnings = fetch_articles(
        load_sources(), settings.lookback_hours, settings.request_timeout
    )
    articles = select_articles(articles, settings.max_articles, settings.max_per_source)
    print(f"抓取完成：{len(articles)} 条资讯，{len(warnings)} 条提示")
    for warning in warnings:
        print(f"  - {warning}")

    if settings.full_article_brief and articles:
        content_warnings = fetch_article_contents(
            articles, settings.request_timeout, settings.brief_max_chars
        )
        print(f"正文简报素材提取完成：{len(articles)} 条，{len(content_warnings)} 条回退")
        for warning in content_warnings:
            print(f"  - {warning}")

    overview = "今日 AI 资讯已按来源优先级和发布时间自动整理。"
    use_llm = settings.translation_mode in {"auto", "llm"} and settings.llm_enabled
    use_free_translation = settings.translation_mode in {"auto", "free"}
    if use_llm:
        try:
            overview = enrich_with_llm(articles, settings)
        except Exception as exc:
            print(f"模型摘要失败：{exc}", file=sys.stderr)
            if settings.translation_mode == "auto":
                use_free_translation = True
    elif settings.translation_mode == "llm":
        print("TRANSLATION_MODE=llm，但未配置 LLM_API_KEY/LLM_MODEL，将保留原文。", file=sys.stderr)

    if use_free_translation and not any(article.title_zh for article in articles):
        translation_warnings = translate_articles(articles)
        print(f"免费中文翻译完成：{len(articles)} 条，{len(translation_warnings)} 条提示")
        for warning in translation_warnings:
            print(f"  - {warning}")

    if articles and not settings.llm_enabled:
        focus_titles = "；".join(article.display_title for article in articles[:4])
        overview = f"今日共整理 {len(articles)} 条 AI 动态。重点包括：{focus_titles}。"

    html_body = build_html(articles, overview, settings.timezone)
    text_body = build_text(articles, overview)
    now = datetime.now(ZoneInfo(settings.timezone))
    subject = f"【AI 每日资讯】{now:%Y-%m-%d} · {len(articles)} 条值得关注的动态"

    if preview:
        output_dir = ROOT / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"ai-daily-{now:%Y-%m-%d}.html"
        output_path.write_text(html_body, encoding="utf-8")
        print(f"预览已生成：{output_path}")
        return output_path

    send_email(settings, subject, text_body, html_body)
    print(f"邮件已发送至：{', '.join(settings.mail_to)}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取 AI 资讯并生成每日邮件")
    parser.add_argument("--preview", action="store_true", help="只生成 HTML 预览，不发邮件")
    args = parser.parse_args()
    run(preview=args.preview)


if __name__ == "__main__":
    main()
