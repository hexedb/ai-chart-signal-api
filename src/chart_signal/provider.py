from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.request
from typing import Protocol

from .domain import Direction, MarketFeatures


class VisionProvider(Protocol):
    def extract(self, image: bytes, *, symbol: str, timeframe: str) -> MarketFeatures: ...


def features_from_mapping(data: dict[str, object]) -> MarketFeatures:
    direction = Direction(str(data.get("direction", "NO_TRADE")).upper())
    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise TypeError("provider response must include a scores object")

    def score(name: str) -> float:
        value = float(scores[name])
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
        return value

    def optional_number(name: str) -> float | None:
        value = data.get(name)
        return None if value is None else float(value)

    return MarketFeatures(
        direction=direction,
        trend=score("trend"),
        market_structure=score("market_structure"),
        support_resistance=score("support_resistance"),
        momentum=score("momentum"),
        price_action=score("price_action"),
        entry=optional_number("entry"),
        stop_loss=optional_number("stop_loss"),
        take_profit=optional_number("take_profit"),
        notes=tuple(str(note) for note in data.get("notes", []) if isinstance(note, str)),
    )


class DemoVisionProvider:
    """Deterministic offline provider for UI demos and repeatable tests.

    It intentionally does not pretend to analyze markets. Production mode should use a
    reviewed provider and evaluation dataset.
    """

    def extract(self, image: bytes, *, symbol: str, timeframe: str) -> MarketFeatures:
        digest = hashlib.sha256(image + symbol.encode() + timeframe.encode()).digest()
        values = [0.55 + (byte / 255) * 0.35 for byte in digest[:5]]
        direction = Direction.BUY if digest[5] % 2 == 0 else Direction.SELL
        entry = 100 + digest[6] / 10
        if direction is Direction.BUY:
            stop, target = entry - 1.2, entry + 2.4
        else:
            stop, target = entry + 1.2, entry - 2.4
        return MarketFeatures(
            direction=direction,
            trend=values[0],
            market_structure=values[1],
            support_resistance=values[2],
            momentum=values[3],
            price_action=values[4],
            entry=round(entry, 2),
            stop_loss=round(stop, 2),
            take_profit=round(target, 2),
            notes=("deterministic demo provider",),
        )


class OpenAICompatibleVisionProvider:
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai provider")
        self.api_key = api_key
        self.model = model

    def extract(self, image: bytes, *, symbol: str, timeframe: str) -> MarketFeatures:
        image_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
        schema_instruction = (
            "Return JSON only with direction BUY, SELL or NO_TRADE; scores object containing "
            "trend, market_structure, support_resistance, momentum and price_action from 0 to 1; "
            "entry, stop_loss, take_profit as numbers or null; and notes as a list. Never invent "
            "unreadable price levels. Use NO_TRADE when the screenshot is unclear."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": schema_instruction},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze {symbol} on {timeframe}."},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        return features_from_mapping(json.loads(content))


def provider_from_env() -> VisionProvider:
    if os.getenv("VISION_PROVIDER", "demo").lower() == "openai":
        return OpenAICompatibleVisionProvider(
            os.getenv("OPENAI_API_KEY", ""), os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        )
    return DemoVisionProvider()
