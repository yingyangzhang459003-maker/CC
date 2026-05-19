from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def dumps(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def normalize_text(text: str | None) -> str:
    return (text or "").lower()


def matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    haystack = normalize_text(text)
    hits: list[str] = []
    for keyword in keywords:
        k = normalize_text(keyword)
        if not k:
            continue
        if re.search(r"\b" + re.escape(k) + r"\b", haystack) or k in haystack:
            hits.append(keyword)
    return sorted(set(hits), key=lambda x: x.lower())


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "null"):
            return default
        return float(value)
    except Exception:
        return default


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def parse_yes_no_prices(outcomes: Any, outcome_prices: Any) -> tuple[float, float]:
    outs = parse_json_array(outcomes)
    prices = parse_json_array(outcome_prices)
    yes_price = 0.0
    no_price = 0.0
    for outcome, price in zip(outs, prices):
        lower = str(outcome).strip().lower()
        if lower == "yes":
            yes_price = safe_float(price)
        elif lower == "no":
            no_price = safe_float(price)
    if yes_price == 0.0 and no_price == 0.0 and len(prices) >= 2:
        yes_price = safe_float(prices[0])
        no_price = safe_float(prices[1])
    return yes_price, no_price
