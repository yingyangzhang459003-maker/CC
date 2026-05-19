from __future__ import annotations

from src.market_scanner import PolymarketMarketScanner


class PolymarketSource:
    def __init__(self, config):
        self.scanner = PolymarketMarketScanner(config)

    def scan(self, session):
        return self.scanner.scan_and_store(session)
