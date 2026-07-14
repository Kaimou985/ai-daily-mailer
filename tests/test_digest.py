import unittest
from datetime import datetime, timezone

from ai_daily.digest import build_html, build_markdown, build_text
from ai_daily.feeds import clean_text, select_articles
from ai_daily.models import Article
from ai_daily.translation import looks_chinese
from ai_daily.article_content import extract_article_text, make_extractive_brief


def sample_article() -> Article:
    return Article(
        title="A new AI model",
        title_zh="某公司发布新 AI 模型",
        url="https://example.com/article",
        source="Example AI",
        category="模型产品",
        published_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        summary="Original summary",
        summary_zh="这是一段中文摘要。",
        why_it_matters="这项更新会影响 AI 应用开发。",
    )


class DigestTests(unittest.TestCase):
    def test_clean_text_removes_html(self):
        self.assertEqual(clean_text("<p>Hello&nbsp; <b>AI</b></p>"), "Hello AI")

    def test_html_digest_contains_article_and_escapes(self):
        result = build_html([sample_article()], "今日 <AI> 总览", "Asia/Shanghai")
        self.assertIn("某公司发布新 AI 模型", result)
        self.assertIn("https://example.com/article", result)
        self.assertIn("今日 &lt;AI&gt; 总览", result)

    def test_text_digest_contains_source(self):
        result = build_text([sample_article()], "今日总览")
        self.assertIn("Example AI", result)
        self.assertIn("值得关注", result)

    def test_markdown_digest_contains_article(self):
        result = build_markdown([sample_article()], "今日总览", "Asia/Shanghai")
        self.assertIn("# AI 每日资讯简报", result)
        self.assertIn("某公司发布新 AI 模型", result)
        self.assertIn("[\u67e5看来源](https://example.com/article)", result)

    def test_html_has_markdown_download_link(self):
        url = "https://example.github.io/repo/download.html"
        result = build_html([sample_article()], "今日总览", "Asia/Shanghai", url)
        self.assertIn("下载 Markdown 简报", result)
        self.assertIn(url, result)

    def test_selection_caps_a_single_source(self):
        articles = [sample_article() for _ in range(6)]
        selected = select_articles(articles, maximum=6, per_source=2)
        self.assertEqual(len(selected), 2)

    def test_chinese_detection(self):
        self.assertTrue(looks_chinese("这是一条 AI 新闻"))
        self.assertFalse(looks_chinese("A new AI model is available"))

    def test_extracts_article_paragraphs(self):
        page = """<html><body><nav>menu</nav><article>
        <p>This is the first substantial paragraph about a new artificial intelligence model and its release details.</p>
        <p>This is the second substantial paragraph explaining performance, availability, pricing, and intended users.</p>
        </article></body></html>"""
        text = extract_article_text(page)
        self.assertIn("first substantial paragraph", text)
        self.assertNotIn("menu", text)

    def test_extractive_brief_has_multiple_sentences(self):
        text = "First sentence contains useful release context and enough detail to retain. Second sentence explains the product capability and availability clearly. Third sentence describes why the change matters to developers and users."
        brief = make_extractive_brief(text, 500)
        self.assertIn("First sentence", brief)
        self.assertIn("Third sentence", brief)


if __name__ == "__main__":
    unittest.main()
