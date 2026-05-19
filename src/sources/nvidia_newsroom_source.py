from __future__ import annotations

from src.sources.rss_source import RSSSource


class NvidiaNewsroomSource(RSSSource):
    def __init__(self, url: str, keywords: list[str]):
        super().__init__(
            name="nvidia_newsroom",
            account="NVIDIA Newsroom",
            url=url,
            keywords=keywords,
            source_quality="official",
        )
