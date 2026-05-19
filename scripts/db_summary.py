from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "radar.db"


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    tables = [
        "markets",
        "market_scores",
        "messages",
        "ai_signals",
        "price_snapshots",
        "paper_trades",
    ]
    for table in tables:
        count = con.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"{table}={count}")

    print("latest_messages")
    for row in con.execute("select source, title, processed from messages order by id desc limit 5"):
        print(row)

    print("latest_signals")
    for row in con.execute("select direction, confidence, impact_score, suggested_action, market_id from ai_signals order by id desc limit 5"):
        print(row)

    print("latest_trades")
    for row in con.execute("select direction, entry_price, position_size, status, market_id from paper_trades order by id desc limit 5"):
        print(row)


if __name__ == "__main__":
    main()
