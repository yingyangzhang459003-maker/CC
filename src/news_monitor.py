from __future__ import annotations

import hashlib
import logging
import os
from typing import Iterable

from sqlalchemy import select

from src.database import Message
from src.sources.mock_source import MockNewsSource
from src.sources.rss_source import RSSSource
from src.sources.sec_source import SECSource
from src.sources.x_source import MockXSource
from src.sources.youtube_source import MockYouTubeSource
from src.utils import dumps, matched_keywords, utc_now_iso

logger = logging.getLogger(__name__)


class NewsMonitor:
    def __init__(self, config):
        self.config = config
        self.keywords = config.get("nvidia_keywords", [])
        self.sources = self._build_sources()

    def _build_sources(self):
        sources = []
        for item in self.config.get("rss_sources", []):
            sources.append(RSSSource(
                name=item.get("name", "rss"),
                account=item.get("account", item.get("name", "RSS")),
                url=item["url"],
                keywords=self.keywords,
                source_quality=item.get("source_quality", "reliable_media"),
            ))
        sec_user_agent = os.getenv("SEC_USER_AGENT") or self.config.get("sec.user_agent") or "PolymarketNvidiaEventRadar/0.1 contact@example.com"
        sources.append(SECSource(
            cik=self.config.get("sec.cik", "0001045810"),
            watched_forms=self.config.get("sec.watched_forms", ["10-K", "10-Q", "8-K", "4", "DEF 14A"]),
            user_agent=sec_user_agent,
        ))
        if self.config.get("mock_sources.enabled", True):
            sources.extend([MockXSource(), MockYouTubeSource(), MockNewsSource()])
        return sources

    def collect(self) -> list:
        collected = []
        for source in self.sources:
            try:
                collected.extend(source.fetch())
            except Exception as exc:
                logger.warning("Source fetch failed for %s: %s", source.__class__.__name__, exc)
        return collected

    def _message_id(self, source_message) -> str:
        raw = f"{source_message.source}|{source_message.title}|{source_message.url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def collect_and_store(self, session) -> list[Message]:
        stored: list[Message] = []
        for item in self.collect():
            text = f"{item.title}\n{item.content}"
            hits = item.keywords or matched_keywords(text, self.keywords)
            if not hits:
                continue
            message_id = self._message_id(item)
            exists = session.execute(select(Message).where(Message.message_id == message_id)).scalar_one_or_none()
            if exists:
                continue
            msg = Message(
                message_id=message_id,
                source=item.source,
                source_account=item.source_account,
                title=item.title,
                content=item.content,
                summary=(item.content or "")[:500],
                url=item.url,
                published_at=item.published_at,
                captured_at=utc_now_iso(),
                entities=dumps(item.entities),
                keywords=dumps(hits),
                processed=False,
                created_at=utc_now_iso(),
            )
            session.add(msg)
            stored.append(msg)
        return stored
