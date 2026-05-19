from __future__ import annotations

import hashlib

import feedparser
import requests

from src.sources.base_source import BaseSource, SourceMessage
from src.utils import matched_keywords, utc_now_iso


class RSSSource(BaseSource):
    def __init__(self, name: str, account: str, url: str, keywords: list[str], source_quality: str = "reliable_media"):
        self.name = name
        self.account = account
        self.url = url
        self.keywords = keywords
        self.source_quality = source_quality

    def fetch(self) -> list[SourceMessage]:
        response = requests.get(self.url, timeout=15, headers={"User-Agent": "PolymarketNvidiaEventRadar/0.1"})
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        messages: list[SourceMessage] = []
        for entry in feed.entries[:20]:
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")
            text = f"{title}\n{summary}"
            hits = matched_keywords(text, self.keywords)
            if hits:
                published = getattr(entry, "published", None) or getattr(entry, "updated", None) or utc_now_iso()
                messages.append(SourceMessage(
                    source=self.name,
                    source_account=self.account,
                    title=title,
                    content=summary,
                    url=link,
                    published_at=published,
                    entities=["NVIDIA"],
                    keywords=hits,
                    metadata={"source_quality": self.source_quality, "entry_hash": hashlib.sha256((title + link).encode()).hexdigest()},
                ))
        return messages
