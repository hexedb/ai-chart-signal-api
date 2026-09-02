import unittest

from chart_signal.domain import Direction
from chart_signal.provider import DemoVisionProvider, features_from_mapping


class ProviderTests(unittest.TestCase):
    def test_demo_provider_is_repeatable(self) -> None:
        provider = DemoVisionProvider()
        first = provider.extract(b"image-bytes" * 20, symbol="XAUUSD", timeframe="H1")
        second = provider.extract(b"image-bytes" * 20, symbol="XAUUSD", timeframe="H1")
        self.assertEqual(first, second)

    def test_mapping_validation(self) -> None:
        item = features_from_mapping(
            {
                "direction": "SELL",
                "scores": {
                    "trend": 0.8,
                    "market_structure": 0.8,
                    "support_resistance": 0.7,
                    "momentum": 0.75,
                    "price_action": 0.9,
                },
                "entry": 100,
                "stop_loss": 102,
                "take_profit": 96,
                "notes": ["clear rejection"],
            }
        )
        self.assertEqual(item.direction, Direction.SELL)
        self.assertEqual(item.notes, ("clear rejection",))

    def test_score_outside_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            features_from_mapping(
                {
                    "direction": "BUY",
                    "scores": {
                        "trend": 1.2,
                        "market_structure": 0.8,
                        "support_resistance": 0.7,
                        "momentum": 0.75,
                        "price_action": 0.9,
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()

