from __future__ import annotations

from src.sources.base_source import BaseSource, SourceMessage
from src.utils import utc_now_iso


class MockNewsSource(BaseSource):
    def fetch(self) -> list[SourceMessage]:
        return [SourceMessage(
            source="mock_news",
            source_account="Mock Reliable Media",
            title="Mock: NVIDIA revenue guidance reportedly lifted by stronger data center demand",
            content="Mock reliable-media item for local testing. It is not real news and should only be used for pipeline validation.",
            url="https://example.com/mock-nvidia-guidance",
            published_at=utc_now_iso(),
            entities=["NVIDIA", "data center"],
            keywords=["NVIDIA", "Nvidia guidance", "data center"],
            metadata={"source_quality": "reliable_media"},
        )]
