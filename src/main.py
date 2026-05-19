from __future__ import annotations

import argparse
import logging
import time

from src.ai_signal import AISignalAnalyzer
from src.config_loader import load_config
from src.database import init_db, session_scope
from src.market_scanner import PolymarketMarketScanner
from src.news_monitor import NewsMonitor
from src.paper_trader import PaperTrader
from src.price_tracker import PriceTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("nvidia_event_radar")


def run_once(config_path: str | None = None) -> dict[str, int]:
    config = load_config(config_path)
    init_db(config.database_url)
    results = {"markets": 0, "messages": 0, "signals": 0, "paper_trades": 0, "trade_updates": 0}
    with session_scope(config.database_url) as session:
        markets = PolymarketMarketScanner(config).scan_and_store(session)
        results["markets"] = len(markets)
        messages = NewsMonitor(config).collect_and_store(session)
        results["messages"] = len(messages)
        signals = AISignalAnalyzer(config).analyze_unprocessed(session)
        results["signals"] = len(signals)
        trades = PaperTrader(config).create_for_signals(session)
        results["paper_trades"] = len(trades)
        updates = PriceTracker(config).update_trade_windows(session)
        results["trade_updates"] = updates
    logger.info("run_once results: %s", results)
    return results


def main():
    parser = argparse.ArgumentParser(description="Polymarket NVIDIA Event Radar")
    parser.add_argument("command", choices=["init-db", "run-once", "scan-markets", "monitor-news", "analyze", "paper-trades", "loop"])
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
            interval = int(config.get("scan_interval_seconds", 300))
            while True:
                run_once(args.config)
                time.sleep(interval)


if __name__ == "__main__":
    main()
