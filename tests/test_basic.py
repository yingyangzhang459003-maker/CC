from __future__ import annotations

from src.ai_signal import AISignalAnalyzer
from src.config_loader import Config
from src.database import Message, init_db, session_scope
from src.market_scanner import PolymarketMarketScanner
from src.news_monitor import NewsMonitor


def test_mock_pipeline(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    config = Config({
        "database_url": db_url,
        "nvidia_keywords": ["NVIDIA", "NVDA", "Blackwell", "AI chip", "data center"],
        "mock_sources": {"enabled": True},
        "rss_sources": [],
        "sec": {"cik": "0001045810", "watched_forms": ["10-K", "10-Q", "8-K", "4", "DEF 14A"]},
        "polymarket": {"gamma_api_base": "https://gamma-api.polymarket.com", "request_timeout_seconds": 1, "page_limit": 2, "max_pages": 0},
        "ai": {"use_llm": False, "min_confidence": 0.65, "min_impact_score": 6},
        "paper_trading": {"initial_balance": 1000, "position_size_percent": 2, "stop_loss_percent": 20, "take_profit_percent": 30, "max_open_trades_per_market": 3},
    })
    init_db(db_url)
    with session_scope(db_url) as session:
        markets = PolymarketMarketScanner(config).scan_and_store(session)
        assert len(markets) >= 1
        monitor = NewsMonitor(config)
        monitor.sources = []
        session.add(Message(
            message_id="test_msg_1",
            source="nvidia_newsroom",
            source_account="NVIDIA Newsroom",
            title="NVIDIA announces stronger Blackwell demand",
            content="Official NVIDIA update says Blackwell and data center demand is strong.",
            summary="Official NVIDIA update.",
            url="https://example.com",
            published_at="2026-05-19T00:00:00Z",
            captured_at="2026-05-19T00:00:01Z",
            entities='["NVIDIA"]',
            keywords='["NVIDIA", "Blackwell"]',
            processed=False,
            created_at="2026-05-19T00:00:01Z",
        ))
        signals = AISignalAnalyzer(config).analyze_unprocessed(session)
        assert len(signals) == 1
        assert signals[0].direction in {"YES", "WATCH", "SKIP", "NO"}
