from __future__ import annotations

from sqlalchemy import func, select

from src.database import AiSignal, Market, PaperTrade
from src.risk_rules import stop_loss_price, take_profit_price
from src.utils import make_id, utc_now_iso


class PaperTrader:
    def __init__(self, config):
        self.config = config
        self.initial_balance = float(config.get("paper_trading.initial_balance", 1000))
        self.position_size_percent = float(config.get("paper_trading.position_size_percent", 2))
        self.stop_loss_percent = float(config.get("paper_trading.stop_loss_percent", 20))
        self.take_profit_percent = float(config.get("paper_trading.take_profit_percent", 30))
        self.max_open_trades_per_market = int(config.get("paper_trading.max_open_trades_per_market", 3))

    def create_for_signals(self, session) -> list[PaperTrade]:
        signals = list(session.execute(select(AiSignal).where(AiSignal.suggested_action == "paper_trade")).scalars())
        created: list[PaperTrade] = []
        for signal in signals:
            if not signal.market_id or signal.direction not in {"YES", "NO"}:
                continue
            exists = session.execute(select(PaperTrade).where(PaperTrade.signal_id == signal.signal_id)).scalar_one_or_none()
            if exists:
                continue
            open_count = session.execute(select(func.count(PaperTrade.id)).where(PaperTrade.market_id == signal.market_id, PaperTrade.status == "open")).scalar_one()
            if open_count >= self.max_open_trades_per_market:
                continue
            market = session.execute(select(Market).where(Market.market_id == signal.market_id)).scalar_one_or_none()
            if not market:
                continue
            entry_price = market.yes_price if signal.direction == "YES" else market.no_price
            if entry_price <= 0:
                continue
            position_size = self.initial_balance * self.position_size_percent / 100.0
            now = utc_now_iso()
            trade = PaperTrade(
                paper_trade_id=make_id("pt"),
                signal_id=signal.signal_id,
                market_id=signal.market_id,
                direction=signal.direction,
                entry_price=entry_price,
                entry_time=now,
                position_size=position_size,
                stop_loss=stop_loss_price(entry_price, signal.direction, self.stop_loss_percent),
                take_profit=take_profit_price(entry_price, signal.direction, self.take_profit_percent),
                status="open",
                review_note="自动纸面交易记录；不涉及真实资金、钱包或私钥。",
                created_at=now,
                updated_at=now,
            )
            session.add(trade)
            created.append(trade)
        return created
