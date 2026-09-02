from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from statistics import fmean
from typing import Any


class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


@dataclass(frozen=True, slots=True)
class MarketFeatures:
    direction: Direction
    trend: float
    market_structure: float
    support_resistance: float
    momentum: float
    price_action: float
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    notes: tuple[str, ...] = ()

    def scores(self) -> dict[str, float]:
        return {
            "trend": self.trend,
            "market_structure": self.market_structure,
            "support_resistance": self.support_resistance,
            "momentum": self.momentum,
            "price_action": self.price_action,
        }


@dataclass(frozen=True, slots=True)
class SignalDecision:
    symbol: str
    timeframe: str
    direction: Direction
    confidence: float
    confirmations: tuple[str, ...]
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_reward: float | None
    explanation: str
    disclaimer: str = "Research demo only. Not financial advice or a promise of performance."

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["direction"] = self.direction.value
        return result


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    min_confidence: float = 0.72
    confirmation_threshold: float = 0.68
    min_confirmations: int = 3
    max_risk_reward: float = 10.0

    def decide(self, symbol: str, timeframe: str, features: MarketFeatures) -> SignalDecision:
        scores = features.scores()
        confidence = round(fmean(scores.values()), 4)
        confirmations = tuple(name for name, score in scores.items() if score >= self.confirmation_threshold)
        invalid_levels = not _valid_levels(features)
        forced_no_trade = (
            features.direction is Direction.NO_TRADE
            or confidence < self.min_confidence
            or len(confirmations) < self.min_confirmations
            or invalid_levels
        )
        if forced_no_trade:
            reasons: list[str] = []
            if confidence < self.min_confidence:
                reasons.append(f"confidence {confidence:.0%} is below {self.min_confidence:.0%}")
            if len(confirmations) < self.min_confirmations:
                reasons.append(f"only {len(confirmations)} confirmations passed")
            if invalid_levels:
                reasons.append("entry/stop/target levels are missing or inconsistent")
            if not reasons:
                reasons.append("the provider found no valid setup")
            return SignalDecision(
                symbol=symbol,
                timeframe=timeframe,
                direction=Direction.NO_TRADE,
                confidence=confidence,
                confirmations=confirmations,
                entry=None,
                stop_loss=None,
                take_profit=None,
                risk_reward=None,
                explanation="NO_TRADE: " + "; ".join(reasons) + ".",
            )
        risk = abs(features.entry - features.stop_loss)  # type: ignore[operator]
        reward = abs(features.take_profit - features.entry)  # type: ignore[operator]
        risk_reward = round(reward / risk, 2)
        if risk_reward > self.max_risk_reward:
            return SignalDecision(
                symbol=symbol,
                timeframe=timeframe,
                direction=Direction.NO_TRADE,
                confidence=confidence,
                confirmations=confirmations,
                entry=None,
                stop_loss=None,
                take_profit=None,
                risk_reward=None,
                explanation="NO_TRADE: proposed levels exceed the configured risk/reward sanity limit.",
            )
        return SignalDecision(
            symbol=symbol,
            timeframe=timeframe,
            direction=features.direction,
            confidence=confidence,
            confirmations=confirmations,
            entry=features.entry,
            stop_loss=features.stop_loss,
            take_profit=features.take_profit,
            risk_reward=risk_reward,
            explanation=(
                f"{features.direction.value} setup passed {len(confirmations)} confirmations: "
                + ", ".join(confirmations)
                + "."
            ),
        )


def _valid_levels(features: MarketFeatures) -> bool:
    if features.direction is Direction.NO_TRADE:
        return True
    if None in (features.entry, features.stop_loss, features.take_profit):
        return False
    assert features.entry is not None and features.stop_loss is not None and features.take_profit is not None
    if features.direction is Direction.BUY:
        return features.stop_loss < features.entry < features.take_profit
    return features.take_profit < features.entry < features.stop_loss

