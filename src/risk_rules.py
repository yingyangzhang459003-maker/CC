from __future__ import annotations


def clamp_price(value: float) -> float:
    return max(0.0, min(1.0, value))


def stop_loss_price(entry_price: float, direction: str, stop_loss_percent: float) -> float:
    factor = stop_loss_percent / 100.0
    return clamp_price(entry_price * (1 - factor)) if direction == "YES" else clamp_price(entry_price * (1 + factor))


def take_profit_price(entry_price: float, direction: str, take_profit_percent: float) -> float:
    factor = take_profit_percent / 100.0
    return clamp_price(entry_price * (1 + factor)) if direction == "YES" else clamp_price(entry_price * (1 - factor))


def estimated_net_pnl(entry_price: float, exit_price: float, direction: str, position_size: float, fee_percent: float, slippage_percent: float) -> float:
    if entry_price <= 0:
        return 0.0
    shares = position_size / entry_price
    gross = (exit_price - entry_price) * shares if direction == "YES" else (entry_price - exit_price) * shares
    costs = position_size * ((fee_percent + slippage_percent) / 100.0)
    return gross - costs
