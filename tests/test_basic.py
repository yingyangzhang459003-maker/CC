from __future__ import annotations

from src.ai_signal import AISignalAnalyzer
from src.config_loader import Config
from src.database import AiSignal, Market, Message, init_db, session_scope
from src.main import summarize_status
from src.market_scanner import PolymarketMarketScanner
from src.news_monitor import NewsMonitor
from src.paper_trader import PaperTrader
from src.price_tracker import PriceTracker
from src.risk_rules import estimated_net_pnl, stop_loss_price, take_profit_price


def make_test_config(tmp_path) -> Config:
    db_url = f"sqlite:///{tmp_path}/test.db"
    return Config({
        "database_url": db_url,
        "nvidia_keywords": ["NVIDIA", "NVDA", "Blackwell", "AI chip", "data center"],
        "mock_sources": {"enabled": True},
        "rss_sources": [],
        "sec": {"cik": "0001045810", "watched_forms": ["10-K", "10-Q", "8-K", "4", "DEF 14A"]},
        "polymarket": {"gamma_api_base": "https://gamma-api.polymarket.com", "request_timeout_seconds": 1, "page_limit": 2, "max_pages": 0},
        "ai": {"use_llm": False, "min_confidence": 0.65, "min_impact_score": 6},
        "paper_trading": {
            "initial_balance": 1000,
            "position_size_percent": 2,
            "stop_loss_percent": 20,
            "take_profit_percent": 30,
            "estimated_fee_percent": 1,
            "estimated_slippage_percent": 1,
            "max_open_trades_per_market": 3,
            "max_total_open_trades": 10,
        },
    })


def test_mock_pipeline(tmp_path):
    config = make_test_config(tmp_path)
    init_db(config.database_url)
    with session_scope(config.database_url) as session:
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


def test_bought_outcome_risk_rules_are_symmetric():
    assert stop_loss_price(0.50, "YES", 20) == 0.40
    assert stop_loss_price(0.50, "NO", 20) == 0.40
    assert take_profit_price(0.50, "YES", 30) == 0.65
    assert take_profit_price(0.50, "NO", 30) == 0.65
    assert estimated_net_pnl(0.50, 0.65, "YES", 20, 1, 1) > 0
    assert estimated_net_pnl(0.50, 0.65, "NO", 20, 1, 1) > 0


def test_paper_trade_take_profit_for_no_token(tmp_path):
    config = make_test_config(tmp_path)
    init_db(config.database_url)
    with session_scope(config.database_url) as session:
        market = Market(
            market_id="m1",
            event_id="e1",
            title="Will NVIDIA guidance disappoint?",
            url="https://example.com/m1",
            category="finance",
            tags="[]",
            yes_price=0.42,
            no_price=0.58,
            volume=10000,
            volume_24h=2000,
            liquidity=5000,
            spread=0.0,
            end_time=None,
            resolution_rules="Official close.",
            is_nvidia_related=True,
            nvidia_keywords='["NVIDIA"]',
            active=True,
            closed=False,
            created_at="2026-05-19T00:00:00Z",
            updated_at="2026-05-19T00:00:00Z",
        )
        signal = AiSignal(
            signal_id="sig1",
            message_id="msg1",
            market_id="m1",
            direction="NO",
            confidence=0.90,
            impact_score=8,
            source_quality="official",
            need_confirmation=False,
            is_likely_rumor=False,
            market_reacted=False,
            suggested_action="paper_trade",
            reason="Regression test signal.",
            created_at="2026-05-19T00:00:01Z",
        )
        session.add_all([market, signal])
        session.flush()
        trades = PaperTrader(config).create_for_signals(session)
        assert len(trades) == 1
        trade = trades[0]
        assert trade.direction == "NO"
        assert trade.entry_price == 0.58
        market.no_price = trade.take_profit + 0.01
        updated = PriceTracker(config).update_trade_windows(session)
        assert updated == 1
        assert trade.status == "take_profit"
        assert trade.pnl is not None and trade.pnl > 0


def test_status_summary(tmp_path, monkeypatch):
    config = make_test_config(tmp_path)
    init_db(config.database_url)
    monkeypatch.setenv("DATABASE_URL", config.database_url)
    status = summarize_status(None)
    assert status["database_url"] == config.database_url
    assert status["markets"] == 0
    assert status["paper_trades_total_pnl"] == 0.0
