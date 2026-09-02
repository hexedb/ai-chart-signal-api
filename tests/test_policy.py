import unittest

from chart_signal.domain import DecisionPolicy, Direction, MarketFeatures


def features(direction: Direction = Direction.BUY, **overrides: object) -> MarketFeatures:
    values: dict[str, object] = {
        "direction": direction,
        "trend": 0.9,
        "market_structure": 0.82,
        "support_resistance": 0.8,
        "momentum": 0.75,
        "price_action": 0.78,
        "entry": 100.0,
        "stop_loss": 98.0,
        "take_profit": 104.0,
    }
    values.update(overrides)
    return MarketFeatures(**values)  # type: ignore[arg-type]


class DecisionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = DecisionPolicy()

    def test_valid_buy_signal(self) -> None:
        result = self.policy.decide("XAUUSD", "H1", features())
        self.assertEqual(result.direction, Direction.BUY)
        self.assertEqual(result.risk_reward, 2.0)
        self.assertGreaterEqual(len(result.confirmations), 3)

    def test_low_confidence_forces_no_trade(self) -> None:
        result = self.policy.decide(
            "XAUUSD", "H1", features(trend=0.5, market_structure=0.5, momentum=0.5)
        )
        self.assertEqual(result.direction, Direction.NO_TRADE)
        self.assertIsNone(result.entry)

    def test_inverted_buy_levels_are_rejected(self) -> None:
        result = self.policy.decide("EURUSD", "M15", features(stop_loss=101.0))
        self.assertEqual(result.direction, Direction.NO_TRADE)
        self.assertIn("inconsistent", result.explanation)

    def test_valid_sell_signal(self) -> None:
        result = self.policy.decide(
            "EURUSD",
            "M15",
            features(Direction.SELL, entry=100.0, stop_loss=102.0, take_profit=96.0),
        )
        self.assertEqual(result.direction, Direction.SELL)
        self.assertEqual(result.risk_reward, 2.0)


if __name__ == "__main__":
    unittest.main()

