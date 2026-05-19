from __future__ import annotations

from src.sources.base_source import BaseSource, SourceMessage
from src.utils import utc_now_iso


class MockYouTubeSource(BaseSource):
    def fetch(self) -> list[SourceMessage]:
        return [SourceMessage(
            source="mock_youtube",
            source_account="Mock NVIDIA YouTube Monitor",
            title="Mock: Jensen Huang keynote clip mentions next generation AI infrastructure",
            content="Mock YouTube transcript summary. This adapter is a placeholder for YouTube Data API plus transcript ingestion.",
            url="https://example.com/mock-youtube-nvidia-keynote",
            published_at=utc_now_iso(),
            entities=["NVIDIA", "Jensen Huang"],
            keywords=["NVIDIA", "Jensen Huang", "AI accelerator"],
            metadata={"source_quality": "social"},
        )]
