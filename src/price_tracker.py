from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.database import Market, PaperTrade, PriceSnapshot
from src.risk_rules import estimated_net_pnl
from src.utils import utc_now_iso


REVIEW_WINDOWS_SECONDS = {
    "price_after_5m": 5 * 60,
    "price_after_30m": 30 * 60,
    "price_after_2h": 2 * 60 * 60,
}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PriceTracker:
    """Record price snapshots and keep paper trades synchronized with market prices."""

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

    def record_all_market_snapshots(self, session) -> int:
        """Persist one snapshot for every active NVIDIA-related market currently in DB."""
        count = 0
        markets = list(session.execute(select(Market).where(Market.is_nvidia_related == True)).scalars())  # noqa: E712
        for market in markets:
            self.record_snapshot(session, market)
            count += 1
        return count

    def current_trade_price(self, trade: PaperTrade, market: Market) -> float:
        return market.yes_price if trade.direction == "YES" else market.no_price

    def mark_closed(self, trade: PaperTrade, exit_price: float, status: str, note: str) -> None:
        trade.final_price = exit_price
        trade.pnl = estimated_net_pnl(
            trade.entry_price,
            exit_price,
            trade.direction,
            trade.position_size,
            self.fee_percent,
            self.slippage_percent,
        )
        trade.status = status
        trade.review_note = note
        trade.updated_at = utc_now_iso()

    def apply_risk_exit(self, trade: PaperTrade, current_price: float) -> bool:
        """Close an open paper trade immediately when stop-loss or take-profit is hit."""
        if current_price <= trade.stop_loss:
            self.mark_closed(trade, current_price, "stopped_out", "触发纸面止损；不涉及真实资金。")
            return True
        if current_price >= trade.take_profit:
            self.mark_closed(trade, current_price, "take_profit", "触发纸面止盈；不涉及真实资金。")
            return True
        return False

    def update_review_windows(self, trade: PaperTrade, age_seconds: float, current_price: float) -> int:
        updated = 0
        for field, threshold in REVIEW_WINDOWS_SECONDS.items():
            if age_seconds >= threshold and getattr(trade, field) is None:
                setattr(trade, field, current_price)
                updated += 1
        if age_seconds >= REVIEW_WINDOWS_SECONDS["price_after_2h"] and trade.status == "open":
            self.mark_closed(trade, current_price, "review_ready", "达到 2 小时复盘窗口，等待人工复核。")
            updated += 1
        return updated

    def update_trade_windows(self, session) -> int:
        now = datetime.now(timezone.utc)
        updated = 0
        trades = list(session.execute(select(PaperTrade).where(PaperTrade.status == "open")).scalars())
        for trade in trades:
            market = session.execute(select(Market).where(Market.market_id == trade.market_id)).scalar_one_or_none()
            if not market:
                continue
            current_price = self.current_trade_price(trade, market)
            if current_price <= 0:
                continue
            age_seconds = (now - _parse_iso(trade.entry_time)).total_seconds()
            if self.apply_risk_exit(trade, current_price):
                updated += 1
                continue
            updated += self.update_review_windows(trade, age_seconds, current_price)
            trade.updated_at = utc_now_iso()
        return updated

    def unrealized_pnl(self, trade: PaperTrade, market: Market) -> float:
        return estimated_net_pnl(
            trade.entry_price,
            self.current_trade_price(trade, market),
            trade.direction,
            trade.position_size,
            self.fee_percent,
            self.slippage_percent,
        )
