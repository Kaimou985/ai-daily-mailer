from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_from: str
    mail_to: tuple[str, ...]
    smtp_use_ssl: bool
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    translation_mode: str
    full_article_brief: bool
    brief_max_chars: int
    lookback_hours: int
    max_articles: int
    max_per_source: int
    request_timeout: int
    timezone: str

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)

    def validate_mail(self) -> None:
        missing = [
            name
            for name, value in {
                "SMTP_HOST": self.smtp_host,
                "SMTP_USER": self.smtp_user,
                "SMTP_PASSWORD": self.smtp_password,
                "MAIL_FROM": self.mail_from,
                "MAIL_TO": self.mail_to,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError("缺少邮件配置：" + ", ".join(missing))


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    recipients = tuple(
        address.strip()
        for address in os.getenv("MAIL_TO", "").split(",")
        if address.strip()
    )
    smtp_user = os.getenv("SMTP_USER", "").strip()
    translation_mode = os.getenv("TRANSLATION_MODE", "auto").strip().lower()
    if translation_mode not in {"auto", "free", "llm", "off"}:
        raise ValueError("TRANSLATION_MODE 必须是 auto、free、llm 或 off")
    return Settings(
        smtp_host=os.getenv("SMTP_HOST", "smtp.qq.com").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_user=smtp_user,
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        mail_from=os.getenv("MAIL_FROM", smtp_user).strip(),
        mail_to=recipients,
        smtp_use_ssl=_as_bool(os.getenv("SMTP_USE_SSL"), True),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        translation_mode=translation_mode,
        full_article_brief=_as_bool(os.getenv("FULL_ARTICLE_BRIEF"), True),
        brief_max_chars=max(600, min(4500, int(os.getenv("BRIEF_MAX_CHARS", "2200")))),
        lookback_hours=max(1, int(os.getenv("LOOKBACK_HOURS", "36"))),
        max_articles=max(1, int(os.getenv("MAX_ARTICLES", "18"))),
        max_per_source=max(1, int(os.getenv("MAX_PER_SOURCE", "5"))),
        request_timeout=max(5, int(os.getenv("REQUEST_TIMEOUT", "20"))),
        timezone=os.getenv("TIMEZONE", "Asia/Shanghai").strip(),
    )


def load_sources() -> list[dict]:
    with (ROOT / "config" / "sources.json").open(encoding="utf-8") as handle:
        return json.load(handle)
