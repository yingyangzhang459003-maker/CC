from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.database import Market, PaperTrade, PriceSnapshot
from src.risk_rules import estimated_net_pnl
from src.utils import utc_now_iso


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PriceTracker:
    def __init__(self, config):
        self.config = config
        self.fee_percent = float(config.get("paper_trading.estimated_fee_percent", 1))
        self.slippage_percent = float(config.get("paper_trading.estimated_slippage_percent", 1))

    def record_snapshot(self, session, market: Market) -> PriceSnapshot:
        snap = PriceSnapshot(
            market_id=market.market_id,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume=market.volume,
            liquidity=market.liquidity,
            spread=market.spread,
            captured_at=utc_now_iso(),
        )
        session.add(snap)
        return snap

    def update_trade_windows(self, session) -> int:
        now = datetime.now(timezone.utc)
        updated = 0
        trades = list(session.execute(select(PaperTrade).where(PaperTrade.status == "open")).scalars())
        for trade in trades:
            market = session.execute(select(Market).where(Market.market_id == trade.market_id)).scalar_one_or_none()
            if not market:
                continue
            current_price = market.yes_price if trade.direction == "YES" else market.no_price
            age_seconds = (now - _parse_iso(trade.entry_time)).total_seconds()
            if age_seconds >= 5 * 60 and trade.price_after_5m is None:
                trade.price_after_5m = current_price
                updated += 1
            if age_seconds >= 30 * 60 and trade.price_after_30m is None:
                trade.price_after_30m = current_price
                updated += 1
            if age_seconds >= 2 * 60 * 60 and trade.price_after_2h is None:
                trade.price_after_2h = current_price
                trade.final_price = current_price
                trade.pnl = estimated_net_pnl(trade.entry_price, current_price, trade.direction, trade.position_size, self.fee_percent, self.slippage_percent)
                trade.status = "review_ready"
                updated += 1
            trade.updated_at = utc_now_iso()
        return updated
