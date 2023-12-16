
import unittest
from unittest.mock import patch
from portfolio_manager import PortfolioManager


class TestPortfolioManager(unittest.TestCase):

    def setUp(self):
        self.base_data = {
            "EXPIRY": "2023-12-31",
            "LOT_SIZE": 100,
            "COVER_FOR_PROFIT": 200,
            "MAX_SOLD_LTP": 150,
        }
        self.manager = PortfolioManager([], self.base_data)

    def test_update(self):
        positions = [
            {"symbol": "AAPL", "value": 1000, "last_price": 150, "quantity": 10},
            {"symbol": "GOOGL", "value": 2000, "last_price": 200, "quantity": -5},
        ]

        updated_portfolio = self.manager.update(positions, sort_key="value")
        expected_portfolio = [
            {"symbol": "GOOGL", "value": 2000, "last_price": 200, "quantity": -5},
            {"symbol": "AAPL", "value": 1000, "last_price": 150, "quantity": 10},
        ]

        self.assertEqual(updated_portfolio, expected_portfolio)

    def test_close_positions(self):
        # Mocking portfolio for testing
        self.manager.portfolio = [
            {"symbol": "AAPL", "value": 1000, "last_price": 150, "quantity": 10},
            {"symbol": "GOOGL", "value": 2000, "last_price": 200, "quantity": -5},
        ]

        positions_to_close = list(self.manager.close_positions())
        expected_positions = [
            {"symbol": "GOOGL", "side": "B", "quantity": 5},
            {"symbol": "AAPL", "side": "S", "quantity": 10},
        ]

        self.assertEqual(positions_to_close, expected_positions)

    @patch('portfolio_manager.logging.debug')
    def test_reduce_value(self, mock_logging_debug):
        # Mocking portfolio for testing
        self.manager.portfolio = [
            {"symbol": "AAPL", "value": 1000, "last_price": 150, "quantity": -10},
            {"symbol": "GOOGL", "value": 2000, "last_price": 200, "quantity": -5},
        ]

        current_value, positions = self.manager.reduce_value(
            15000, contains="P")
        expected_value = 1000  # Reduced value from the first position
        expected_positions = [
            {"symbol": "AAPL", "quantity": 1000, "side": "B"},
            {"symbol": "GOOGL", "quantity": 500, "side": "B"},
        ]

        self.assertEqual(current_value, expected_value)
        self.assertEqual(positions, expected_positions)

        # Assert that logging.debug was called with the expected arguments
        mock_logging_debug.assert_called_with(
            f"{current_value} before reducing")

    # Add more test cases for other methods as needed


if __name__ == "__main__":
    unittest.main()
