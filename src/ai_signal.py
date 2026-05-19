from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy import select

from src.database import AiSignal, Market, Message
from src.utils import make_id, matched_keywords, safe_float, utc_now_iso

PROMPT_TEMPLATE = """
你是一个专注于 Polymarket NVIDIA / NVDA 盘口的事件分析助手。

你的任务不是预测未来，也不是给投资建议，而是判断一条公开消息是否可能影响某个 Polymarket 上与 NVIDIA / NVDA 相关的 Yes/No 盘口。

请根据以下信息判断：

1. 这条消息是否与 NVIDIA / NVDA 相关
2. 消息来源是否可靠
3. 消息是否与某个具体盘口存在因果关系
4. 它利好 YES 还是利好 NO
5. 影响强度是多少
6. 是否需要多源确认
7. 当前盘口是否可能已经反应
8. 是否适合进入纸面交易

请只输出 JSON，不要输出多余解释。
""".strip()


class AISignalAnalyzer:
    def __init__(self, config):
        self.config = config
        self.keywords = config.get("nvidia_keywords", [])
        self.use_llm = bool(config.get("ai.use_llm", False)) and bool(os.getenv("OPENAI_API_KEY"))
        self.model = config.get("ai.model", "gpt-4.1-mini")
        self.min_confidence = safe_float(config.get("ai.min_confidence", 0.65))
        self.min_impact_score = int(config.get("ai.min_impact_score", 6))

    def _market_context(self, markets: list[Market]) -> str:
        return "\n".join([
            f"market_id={m.market_id}; title={m.title}; yes_price={m.yes_price}; no_price={m.no_price}; liquidity={m.liquidity}; spread={m.spread}; rules={m.resolution_rules[:300] if m.resolution_rules else ''}"
            for m in markets[:20]
        ])

    def _llm_analyze(self, message: Message, markets: list[Market]) -> dict[str, Any]:
        from openai import OpenAI
        client = OpenAI()
        user_payload = {
            "message": {
                "message_id": message.message_id,
                "source": message.source,
                "source_account": message.source_account,
                "title": message.title,
                "content": message.content,
                "url": message.url,
                "published_at": message.published_at,
            },
            "markets": self._market_context(markets),
            "output_schema": {
                "related_market_id": "",
                "direction": "YES/NO/SKIP/WATCH",
                "confidence": 0.0,
                "impact_score": 0,
                "source_quality": "official/reliable_media/social/rumor",
                "need_confirmation": True,
                "is_likely_rumor": False,
                "market_reacted": False,
                "suggested_action": "paper_trade/watch/skip",
                "reason": "",
            },
        }
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": PROMPT_TEMPLATE}, {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")

    def _heuristic_analyze(self, message: Message, markets: list[Market]) -> dict[str, Any]:
        text = f"{message.title}\n{message.content or ''}"
        hits = matched_keywords(text, self.keywords)
        source = (message.source or "").lower()
        source_quality = "official" if any(s in source for s in ["nvidia", "sec"]) else "reliable_media" if "rss" in source or "news" in source else "social"
        likely_positive = any(k in text.lower() for k in ["strong", "beat", "raise", "expand", "growth", "demand", "shipments", "partnership", "approval"])
        likely_negative = any(k in text.lower() for k in ["ban", "restriction", "miss", "delay", "investigation", "cut", "weak", "export control"])
        target_market = None
        best_overlap = 0
        for market in markets:
            overlap = len(matched_keywords(f"{market.title}\n{market.resolution_rules or ''}", hits or self.keywords))
            if overlap > best_overlap:
                target_market = market
                best_overlap = overlap
        if not hits or not target_market:
            direction = "SKIP"
            confidence = 0.25
            impact_score = 2
            action = "skip"
            reason = "消息未能与当前 NVIDIA 相关盘口建立足够明确的因果关系。"
        else:
            direction = "NO" if likely_negative and not likely_positive else "YES" if likely_positive else "WATCH"
            impact_score = 8 if source_quality == "official" else 7 if source_quality == "reliable_media" else 5
            confidence = 0.72 if source_quality == "official" else 0.66 if source_quality == "reliable_media" else 0.48
            action = "paper_trade" if direction in {"YES", "NO"} and confidence >= self.min_confidence and impact_score >= self.min_impact_score else "watch"
            reason = f"消息关键词 {hits} 与盘口 '{target_market.title}' 存在匹配；来源可信度为 {source_quality}，方向为 {direction}。"
        return {
            "related_market_id": target_market.market_id if target_market else "",
            "direction": direction,
            "confidence": confidence,
            "impact_score": impact_score,
            "source_quality": source_quality,
            "need_confirmation": source_quality == "social",
            "is_likely_rumor": source_quality == "social",
            "market_reacted": False,
            "suggested_action": action,
            "reason": reason,
        }

    def analyze_message(self, message: Message, markets: list[Market]) -> dict[str, Any]:
        if self.use_llm:
            try:
                return self._llm_analyze(message, markets)
            except Exception as exc:
                return {**self._heuristic_analyze(message, markets), "reason": f"LLM 调用失败，已回退启发式分析：{exc}"}
        return self._heuristic_analyze(message, markets)

    def analyze_unprocessed(self, session) -> list[AiSignal]:
        session.flush()
        markets = list(session.execute(select(Market).where(Market.is_nvidia_related == True, Market.closed == False)).scalars())
        messages = list(session.execute(select(Message).where(Message.processed == False)).scalars())
        signals: list[AiSignal] = []
        for message in messages:
            result = self.analyze_message(message, markets)
            signal = AiSignal(
                signal_id=make_id("sig"),
                message_id=message.message_id,
                market_id=result.get("related_market_id") or None,
                direction=result.get("direction", "SKIP"),
                confidence=safe_float(result.get("confidence", 0.0)),
                impact_score=int(result.get("impact_score", 0) or 0),
                source_quality=result.get("source_quality", "unknown"),
                need_confirmation=bool(result.get("need_confirmation", False)),
                is_likely_rumor=bool(result.get("is_likely_rumor", False)),
                market_reacted=bool(result.get("market_reacted", False)),
                suggested_action=result.get("suggested_action", "skip"),
                reason=result.get("reason", ""),
                created_at=utc_now_iso(),
            )
            session.add(signal)
            message.processed = True
            signals.append(signal)
        return signals
