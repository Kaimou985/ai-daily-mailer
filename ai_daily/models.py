from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    published_at: datetime
    summary: str
    content: str = ""
    priority: int = 0
    title_zh: str = ""
    summary_zh: str = ""
    why_it_matters: str = ""

    @property
    def display_title(self) -> str:
        return self.title_zh or self.title

    @property
    def display_summary(self) -> str:
        return self.summary_zh or self.summary

