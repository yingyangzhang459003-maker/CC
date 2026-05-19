from __future__ import annotations

from src.database import Market, MarketScore
from src.utils import utc_now_iso


def _scale(value: float, thresholds: tuple[float, float, float]) -> int:
    low, mid, high = thresholds
    if value >= high:
        return 10
    if value >= mid:
        return 8
    if value >= low:
        return 5
    return 2


class MarketRanker:
    def score(self, market: Market) -> dict:
        title = (market.title or "").lower()
        volume = market.volume or 0.0
        liquidity = market.liquidity or 0.0
        spread = market.spread or 0.0

        media_score = 9 if any(k in title for k in ["earnings", "stock", "market cap", "chip", "china", "nvidia", "nvda"]) else 6
        liquidity_score = max(_scale(volume, (500, 5000, 25000)), _scale(liquidity, (300, 3000, 15000)))
        spread_score = 10 if spread <= 0.05 else 8 if spread <= 0.10 else 5 if spread <= 0.20 else 2
        resolution_clarity_score = 9 if any(k in title for k in ["above", "below", "by", "before", "earnings", "close"]) else 6
        ai_judgement_score = 9 if any(k in title for k in ["earnings", "revenue", "stock", "chip", "market cap", "export"]) else 7
        time_sensitivity_score = 9 if any(k in title for k in ["today", "week", "friday", "earnings", "announcement"]) else 7
        competition_score = 5 if volume > 100000 else 7
        total = sum([media_score, liquidity_score, spread_score, resolution_clarity_score, ai_judgement_score, time_sensitivity_score, competition_score])
        grade = "A" if total >= 52 else "B" if total >= 42 else "C" if total >= 32 else "D"
        reason = f"该盘口与 NVIDIA/NVDA 关键词匹配，流动性评分 {liquidity_score}，价差评分 {spread_score}，综合评级 {grade}。"
        return {
            "market_id": market.market_id,
            "media_score": media_score,
            "liquidity_score": liquidity_score,
            "spread_score": spread_score,
            "resolution_clarity_score": resolution_clarity_score,
            "ai_judgement_score": ai_judgement_score,
            "time_sensitivity_score": time_sensitivity_score,
            "competition_score": competition_score,
            "total_score": total,
            "grade": grade,
            "reason": reason,
        }

    def persist_score(self, session, market: Market) -> MarketScore:
        data = self.score(market)
        score = MarketScore(**data, created_at=utc_now_iso())
        session.add(score)
        return score
