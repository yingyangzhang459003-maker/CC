from __future__ import annotations

import logging
from typing import Any

import requests
from sqlalchemy import select

from src.database import Market, PriceSnapshot
from src.market_ranker import MarketRanker
from src.utils import dumps, matched_keywords, parse_yes_no_prices, safe_float, utc_now_iso

logger = logging.getLogger(__name__)


class PolymarketMarketScanner:
    """Discover, normalize, rank and persist NVIDIA/NVDA-related Polymarket markets."""

    def __init__(self, config):
        self.config = config
        self.api_base = config.get("polymarket.gamma_api_base", "https://gamma-api.polymarket.com").rstrip("/")
        self.timeout = config.get("polymarket.request_timeout_seconds", 20)
        self.keywords = config.get("nvidia_keywords", [])
        self.page_limit = int(config.get("polymarket.page_limit", 200))
        self.max_pages = int(config.get("polymarket.max_pages", 5))
        self.min_volume = float(config.get("market_filters.min_volume", 0) or 0)
        self.min_liquidity = float(config.get("market_filters.min_liquidity", 0) or 0)
        self.max_spread = float(config.get("market_filters.max_spread", 1) or 1)
        self.ranker = MarketRanker()

    def fetch_active_markets(self) -> list[dict[str, Any]]:
        all_markets: list[dict[str, Any]] = []
        for page in range(self.max_pages):
            params = {
                "active": "true",
                "closed": "false",
                "limit": self.page_limit,
                "offset": page * self.page_limit,
            }
            url = f"{self.api_base}/markets"
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                break
            all_markets.extend(payload)
            if len(payload) < self.page_limit:
                break
        return all_markets

    def find_related_markets(self, markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        related: list[dict[str, Any]] = []
        for market in markets:
            text = " ".join(str(market.get(k, "")) for k in ["question", "title", "description", "slug", "category"])
            tags = market.get("tags") or []
            text += " " + dumps(tags)
            hits = matched_keywords(text, self.keywords)
            if hits:
                market["_nvidia_keywords"] = hits
                related.append(market)
        return related

    def normalize_market(self, raw: dict[str, Any]) -> dict[str, Any]:
        yes_price, no_price = parse_yes_no_prices(raw.get("outcomes"), raw.get("outcomePrices"))
        volume = safe_float(raw.get("volume") or raw.get("volumeNum"))
        volume_24h = safe_float(raw.get("volume24hr") or raw.get("volume24h"))
        liquidity = safe_float(raw.get("liquidity") or raw.get("liquidityNum"))
        spread = abs(1.0 - (yes_price + no_price)) if yes_price and no_price else safe_float(raw.get("spread"))
        slug = raw.get("slug") or raw.get("marketSlug") or raw.get("id")
        market_id = str(raw.get("id") or raw.get("conditionId") or raw.get("questionID") or slug)
        return {
            "market_id": market_id,
            "event_id": str(raw.get("eventId") or raw.get("event_id") or ""),
            "title": raw.get("question") or raw.get("title") or "",
            "url": f"https://polymarket.com/market/{slug}" if slug else None,
            "category": raw.get("category") or raw.get("categorySlug"),
            "tags": dumps(raw.get("tags") or []),
            "yes_price": yes_price,
            "no_price": no_price,
            "volume": volume,
            "volume_24h": volume_24h,
            "liquidity": liquidity,
            "spread": spread,
            "end_time": raw.get("endDate") or raw.get("end_date"),
            "resolution_rules": raw.get("description") or raw.get("resolutionSource") or "",
            "is_nvidia_related": True,
            "nvidia_keywords": dumps(raw.get("_nvidia_keywords") or []),
            "active": bool(raw.get("active", True)),
            "closed": bool(raw.get("closed", False)),
            "created_at": raw.get("createdAt") or utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

    def passes_filters(self, data: dict[str, Any]) -> bool:
        """Apply configurable liquidity, volume and spread filters after normalization."""
        if data["volume"] < self.min_volume:
            return False
        if data["liquidity"] < self.min_liquidity:
            return False
        if data["spread"] and data["spread"] > self.max_spread:
            return False
        return True

    def sort_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prefer liquid and recently active markets when multiple NVIDIA candidates exist."""
        return sorted(
            candidates,
            key=lambda item: (
                safe_float(item.get("volume24hr") or item.get("volume24h")),
                safe_float(item.get("liquidity") or item.get("liquidityNum")),
                safe_float(item.get("volume") or item.get("volumeNum")),
            ),
            reverse=True,
        )

    def mock_markets(self) -> list[dict[str, Any]]:
        samples = [
            {
                "id": "mock_nvda_close_above_200",
                "question": "Will NVDA close above $200 this Friday?",
                "slug": "will-nvda-close-above-200-this-friday",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.42","0.58"]',
                "volume": 18250,
                "volume24hr": 3210,
                "liquidity": 8400,
                "description": "Market resolves according to the official NVDA closing price.",
                "active": True,
                "closed": False,
                "_nvidia_keywords": ["NVDA", "NVIDIA"],
            },
            {
                "id": "mock_blackwell_shipping",
                "question": "Will NVIDIA announce expanded Blackwell shipments before month end?",
                "slug": "nvidia-blackwell-shipments-before-month-end",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.31","0.69"]',
                "volume": 7400,
                "volume24hr": 900,
                "liquidity": 5100,
                "description": "Resolves based on official NVIDIA announcement or reliable media confirmation.",
                "active": True,
                "closed": False,
                "_nvidia_keywords": ["NVIDIA", "Blackwell", "AI chip"],
            },
        ]
        return samples

    def scan_candidates(self) -> list[dict[str, Any]]:
        """Fetch, filter and sort raw market candidates, using mock fallback only when configured."""
        try:
            markets = self.fetch_active_markets()
            related_raw = self.find_related_markets(markets)
            if not related_raw and self.config.get("mock_sources.enabled", True):
                logger.warning("No live NVIDIA markets found; using mock markets for validation.")
                related_raw = self.mock_markets()
        except Exception as exc:
            logger.exception("Polymarket scan failed; falling back to mock data: %s", exc)
            related_raw = self.mock_markets() if self.config.get("mock_sources.enabled", True) else []
        return self.sort_candidates(related_raw)

    def scan_and_store(self, session) -> list[Market]:
        stored: list[Market] = []
        for raw in self.scan_candidates():
            data = self.normalize_market(raw)
            if not self.passes_filters(data):
                logger.info("Skipping market by filters: %s", data["title"])
                continue
            existing = session.execute(select(Market).where(Market.market_id == data["market_id"])).scalar_one_or_none()
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                market = existing
            else:
                market = Market(**data)
                session.add(market)
            session.flush()
            session.add(PriceSnapshot(
                market_id=market.market_id,
                yes_price=market.yes_price,
                no_price=market.no_price,
                volume=market.volume,
                liquidity=market.liquidity,
                spread=market.spread,
                captured_at=utc_now_iso(),
            ))
            self.ranker.persist_score(session, market)
            stored.append(market)
        return stored
