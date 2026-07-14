from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import Article


def _escape(value: str) -> str:
    return html.escape(value or "")


def _brief_html(value: str) -> str:
    paragraphs = [part.strip() for part in (value or "").split("\n\n") if part.strip()]
    return "".join(f'<p class="brief">{_escape(part)}</p>' for part in paragraphs)


def build_html(
    articles: list[Article],
    overview: str,
    timezone_name: str,
    markdown_download_url: str = "",
) -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    cards = []
    for index, article in enumerate(articles, 1):
        published = article.published_at.astimezone(ZoneInfo(timezone_name)).strftime("%m-%d %H:%M")
        why = (
            f'<div class="why"><strong>值得关注：</strong>{_escape(article.why_it_matters)}</div>'
            if article.why_it_matters
            else ""
        )
        cards.append(
            f"""
            <article class="card">
              <div class="meta"><span class="index">{index:02d}</span><span>{_escape(article.category)}</span><span>{_escape(article.source)}</span><span>{published}</span></div>
              <h2>{_escape(article.display_title)}</h2>
              <div class="label">简报内容</div>
              {_brief_html(article.display_summary)}
              {why}
              <a class="source-link" href="{_escape(article.url)}">来源链接（供核验）</a>
            </article>"""
        )
    empty = '<div class="empty">今日暂无新资讯，可尝试调大 LOOKBACK_HOURS。</div>' if not cards else ""
    download = (
        f'<div class="download"><a href="{_escape(markdown_download_url)}">↓ 下载 Markdown 简报</a></div>'
        if markdown_download_url
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{margin:0;background:#f3f5f4;color:#17201c;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}}
.wrap{{max-width:760px;margin:auto;padding:30px 16px 46px}}.hero{{background:#102a22;color:#fff;padding:32px;border-radius:18px}}
.eyebrow{{color:#8ee0b8;font-size:12px;letter-spacing:2px;font-weight:700}}h1{{font-size:30px;margin:10px 0 8px}}.date{{color:#bdd0c8;font-size:14px}}
.overview{{background:#fff;border-left:4px solid #21a66b;margin:18px 0;padding:18px 20px;border-radius:10px;line-height:1.75}}
.card{{background:#fff;margin:14px 0;padding:22px;border-radius:14px;border:1px solid #e1e8e4}}.meta{{display:flex;gap:9px;flex-wrap:wrap;color:#67756f;font-size:12px}}
.index{{background:#102a22;color:#fff;border-radius:5px;padding:2px 6px}}h2{{font-size:19px;line-height:1.45;margin:13px 0 10px}}h2 a{{color:#17201c;text-decoration:none}}
p{{color:#43514b;line-height:1.72;margin:0 0 12px}}.label{{font-size:12px;color:#117847;font-weight:700;letter-spacing:1px;margin:14px 0 8px}}.brief{{font-size:15px;line-height:1.85}}
.why{{background:#eff9f3;padding:11px 13px;border-radius:8px;color:#2b5d45;font-size:13px;line-height:1.6}}.source-link{{display:inline-block;margin-top:12px;color:#87938e;text-decoration:none;font-size:11px;border-bottom:1px dotted #aab4b0}}
.download{{text-align:center;margin:26px 0 8px}}.download a{{display:inline-block;background:#102a22;color:#fff;text-decoration:none;padding:12px 20px;border-radius:9px;font-weight:700;font-size:14px}}
.footer{{text-align:center;color:#87938e;font-size:12px;margin-top:18px}}.empty{{padding:30px;text-align:center}}
@media(max-width:520px){{.hero{{padding:24px}}h1{{font-size:25px}}.card{{padding:18px}}}}
</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">AI DAILY SIGNAL</div><h1>AI 每日资讯</h1><div class="date">{now:%Y 年 %m 月 %d 日} · 精选 {len(articles)} 条</div></header>
<section class="overview">{_escape(overview)}</section>{''.join(cards)}{empty}{download}
<footer class="footer">由 AI Daily Mailer 自动整理 · 请以原文为准</footer>
</div></body></html>"""


def build_text(articles: list[Article], overview: str, markdown_download_url: str = "") -> str:
    lines = ["AI 每日资讯", "", overview, ""]
    for index, article in enumerate(articles, 1):
        lines.extend(
            [
                f"{index}. {article.display_title}",
                f"来源：{article.source} | {article.category}",
                article.display_summary,
                f"值得关注：{article.why_it_matters}" if article.why_it_matters else "",
                article.url,
                "",
            ]
        )
    if markdown_download_url:
        lines.extend(["下载 Markdown 简报：", markdown_download_url, ""])
    return "\n".join(line for line in lines if line is not None)


def build_markdown(
    articles: list[Article], overview: str, timezone_name: str
) -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    lines = [
        f"# AI 每日资讯简报｜{now:%Y-%m-%d}",
        "",
        f"> 生成时间：{now:%Y-%m-%d %H:%M} ({timezone_name})",
        "",
        "## 今日总览",
        "",
        overview,
        "",
    ]
    for index, article in enumerate(articles, 1):
        published = article.published_at.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")
        lines.extend(
            [
                f"## {index}. {article.display_title}",
                "",
                f"- **分类**：{article.category}",
                f"- **来源**：{article.source}",
                f"- **发布时间**：{published}",
                "",
                article.display_summary,
                "",
            ]
        )
        if article.why_it_matters:
            lines.extend([f"> **值得关注**：{article.why_it_matters}", ""])
        lines.extend([f"[查看来源]({article.url})", "", "---", ""])
    lines.extend(["*AI Daily Mailer 自动整理，重要信息请以原始来源为准。*", ""])
    return "\n".join(lines)


def build_download_page() -> str:
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>下载 AI 简报</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f3f5f4;color:#17201c;display:grid;place-items:center;min-height:100vh;margin:0}.box{background:#fff;padding:32px;border-radius:16px;text-align:center;box-shadow:0 10px 40px #102a2218}a{display:inline-block;background:#102a22;color:#fff;padding:12px 20px;border-radius:9px;text-decoration:none;font-weight:700}</style></head>
<body><div class="box"><h1>AI 每日资讯简报</h1><p id="status">正在准备 Markdown 文件……</p><a id="manual" href="latest.md" download="AI-daily-brief.md">手动下载</a></div>
<script>fetch('latest.md?ts='+Date.now()).then(r=>{if(!r.ok)throw Error();return r.blob()}).then(b=>{const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='AI-daily-brief.md';a.click();document.getElementById('status').textContent='下载已开始，如未下载请点击下方按钮。'}).catch(()=>document.getElementById('status').textContent='自动下载失败，请点击下方按钮。')</script></body></html>"""


def build_pages_index() -> str:
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI 每日简报</title></head><body><h1>AI 每日资讯简报</h1><p><a href="download.html">下载最新 Markdown 简报</a></p><p><a href="latest.md">在线查看 Markdown</a></p></body></html>"""
