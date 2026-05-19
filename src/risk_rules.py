from __future__ import annotations


MIN_PRICE = 0.0
MAX_PRICE = 1.0


def clamp_price(value: float) -> float:
    return max(MIN_PRICE, min(MAX_PRICE, value))


def stop_loss_price(entry_price: float, direction: str, stop_loss_percent: float) -> float:
    """Return the stop-loss price for a bought outcome share.

    In Polymarket-style binary markets, a paper trade in direction YES means buying
    the YES outcome token, while direction NO means buying the NO outcome token.
    The tracked price is therefore the price of the outcome that was bought. For
    both directions, a lower tracked outcome price is adverse and a higher tracked
    outcome price is favorable.
    """
    factor = stop_loss_percent / 100.0
    return clamp_price(entry_price * (1 - factor))


def take_profit_price(entry_price: float, direction: str, take_profit_percent: float) -> float:
    """Return the take-profit price for a bought outcome share."""
    factor = take_profit_percent / 100.0
    return clamp_price(entry_price * (1 + factor))


def estimated_net_pnl(
    entry_price: float,
    exit_price: float,
    direction: str,
    position_size: float,
    fee_percent: float,
    slippage_percent: float,
) -> float:
    """Estimate net PnL for a bought YES or NO outcome token.

    The formula intentionally treats YES and NO symmetrically because the system
    stores the price of the purchased outcome token as `entry_price` and
    `exit_price`. If a NO token rises from 0.40 to 0.55, the paper trade should
    show profit in the same way a YES token rising from 0.40 to 0.55 does.
    """
    if entry_price <= 0:
        return 0.0
    shares = position_size / entry_price
    gross = (exit_price - entry_price) * shares
    costs = position_size * ((fee_percent + slippage_percent) / 100.0)
    return gross - costs
