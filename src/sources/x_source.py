from __future__ import annotations

from src.sources.base_source import BaseSource, SourceMessage
from src.utils import utc_now_iso


class MockXSource(BaseSource):
    def fetch(self) -> list[SourceMessage]:
        return [SourceMessage(
            source="mock_x",
            source_account="Mock Semiconductor Reporter",
            title="Mock: NVIDIA Blackwell supply commentary gains attention",
            content="A mock social signal says hyperscaler demand for NVIDIA Blackwell systems remains strong. Treat as unconfirmed until official or reliable media confirmation.",
            url="https://example.com/mock-x-nvidia-blackwell",
            published_at=utc_now_iso(),
            entities=["NVIDIA", "Blackwell"],
            keywords=["NVIDIA", "Blackwell", "AI chip"],
            metadata={"source_quality": "social"},
        )]
