from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceMessage:
    source: str
    source_account: str
    title: str
    content: str
    url: str
    published_at: str | None = None
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSource(ABC):
    @abstractmethod
    def fetch(self) -> list[SourceMessage]:
        raise NotImplementedError
