from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path("config/config.example.yaml")


def deep_get(mapping: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = mapping
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


class Config:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    def get(self, path: str, default: Any = None) -> Any:
        return deep_get(self.data, path, default)

    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL") or self.get("database_url") or "sqlite:///data/radar.db"


def load_config(path: str | Path | None = None) -> Config:
    load_dotenv()
    config_path = Path(path or os.getenv("RADAR_CONFIG") or DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("database_url", os.getenv("DATABASE_URL", "sqlite:///data/radar.db"))
    return Config(data)
