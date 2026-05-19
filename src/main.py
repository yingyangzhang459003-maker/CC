from __future__ import annotations

import argparse
import logging
import time
from typing import Any

from sqlalchemy import func, select

from src.ai_signal import AISignalAnalyzer
from src.config_loader import load_config
from src.database import AiSignal, Market, Message, PaperTrade, PriceSnapshot, init_db, session_scope
from src.market_scanner import PolymarketMarketScanner
from src.news_monitor import NewsMonitor
from src.paper_trader import PaperTrader
from src.price_tracker import PriceTracker
from src.runtime_monitor import record_runtime_run, runtime_health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("nvidia_event_radar")


def run_once(config_path: str | None = None) -> dict[str, int]:
    config = load_config(config_path)
    init_db(config.database_url)
    results = {
        "markets": 0,
        "messages": 0,
        "signals": 0,
        "paper_trades": 0,
        "trade_updates": 0,
        "snapshots": 0,
    }
    with session_scope(config.database_url) as session:
        markets = PolymarketMarketScanner(config).scan_and_store(session)
        results["markets"] = len(markets)
        messages = NewsMonitor(config).collect_and_store(session)
        results["messages"] = len(messages)
        signals = AISignalAnalyzer(config).analyze_unprocessed(session)
        results["signals"] = len(signals)
        trades = PaperTrader(config).create_for_signals(session)
        results["paper_trades"] = len(trades)
        tracker = PriceTracker(config)
        results["snapshots"] = tracker.record_all_market_snapshots(session)
        results["trade_updates"] = tracker.update_trade_windows(session)
    logger.info("run_once results: %s", results)
    return results


def summarize_status(config_path: str | None = None) -> dict[str, Any]:
    """Return a compact operational summary suitable for CLI checks and dashboards."""
    config = load_config(config_path)
    init_db(config.database_url)
    with session_scope(config.database_url) as session:
        latest_snapshot = session.execute(select(func.max(PriceSnapshot.captured_at))).scalar_one()
        latest_message = session.execute(select(func.max(Message.captured_at))).scalar_one()
        latest_signal = session.execute(select(func.max(AiSignal.created_at))).scalar_one()
        open_trades = session.execute(select(func.count(PaperTrade.id)).where(PaperTrade.status == "open")).scalar_one()
        closed_trades = session.execute(select(func.count(PaperTrade.id)).where(PaperTrade.status != "open")).scalar_one()
        total_pnl = session.execute(select(func.coalesce(func.sum(PaperTrade.pnl), 0.0))).scalar_one()
        summary = {
            "database_url": config.database_url,
            "markets": session.execute(select(func.count(Market.id))).scalar_one(),
            "messages": session.execute(select(func.count(Message.id))).scalar_one(),
            "signals": session.execute(select(func.count(AiSignal.id))).scalar_one(),
            "paper_trades_open": open_trades,
            "paper_trades_closed": closed_trades,
            "paper_trades_total_pnl": round(float(total_pnl or 0.0), 4),
            "price_snapshots": session.execute(select(func.count(PriceSnapshot.id))).scalar_one(),
            "latest_snapshot_at": latest_snapshot,
            "latest_message_at": latest_message,
            "latest_signal_at": latest_signal,
        }
        summary.update(runtime_health(session))
        return summary


def refresh_prices(config_path: str | None = None) -> dict[str, int]:
    """Refresh markets, record snapshots, and update open paper trades."""
    config = load_config(config_path)
    init_db(config.database_url)
    with session_scope(config.database_url) as session:
        markets = PolymarketMarketScanner(config).scan_and_store(session)
        tracker = PriceTracker(config)
        snapshots = tracker.record_all_market_snapshots(session)
        trade_updates = tracker.update_trade_windows(session)
        return {"markets": len(markets), "snapshots": snapshots, "trade_updates": trade_updates}


def main():
    parser = argparse.ArgumentParser(description="Polymarket NVIDIA Event Radar")
    parser.add_argument(
        "command",
        choices=[
            "init-db",
            "run-once",
            "scan-markets",
            "monitor-news",
            "analyze",
            "paper-trades",
            "refresh-prices",
            "status",
            "loop",
        ],
    )
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "init-db":
        init_db(config.database_url)
        print(f"Initialized database: {config.database_url}")
        return

    if args.command == "run-once":
        print(run_once(args.config))
        return

    if args.command == "refresh-prices":
        print(refresh_prices(args.config))
        return

    if args.command == "status":
        print(summarize_status(args.config))
        return

    with session_scope(config.database_url) as session:
        if args.command == "scan-markets":
            print(f"stored_markets={len(PolymarketMarketScanner(config).scan_and_store(session))}")
        elif args.command == "monitor-news":
            print(f"stored_messages={len(NewsMonitor(config).collect_and_store(session))}")
        elif args.command == "analyze":
            print(f"signals={len(AISignalAnalyzer(config).analyze_unprocessed(session))}")
        elif args.command == "paper-trades":
            print(f"paper_trades={len(PaperTrader(config).create_for_signals(session))}")
        elif args.command == "loop":
            interval = int(config.get("runtime.loop_interval_seconds", config.get("scan_interval_seconds", 300)))
            max_backoff = int(config.get("runtime.max_backoff_seconds", 900))
            failure_count = 0
            while True:
                try:
                    with session_scope(config.database_url) as runtime_session:
                        record_runtime_run(runtime_session, "run_once", lambda: run_once(args.config))
                    failure_count = 0
                    sleep_seconds = interval
                except Exception as exc:  # noqa: BLE001 - worker loop should survive transient API/network failures.
                    failure_count += 1
                    sleep_seconds = min(max_backoff, interval * (2 ** min(failure_count, 4)))
                    logger.exception("loop iteration failed; backing off for %ss: %s", sleep_seconds, exc)
                time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
