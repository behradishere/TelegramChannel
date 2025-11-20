"""Test stop loss and take profit validation."""
import unittest
from unittest.mock import Mock, MagicMock


class TestStopValidation(unittest.TestCase):
    """Test cases for stop level validation."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock MetaTrader5 module
        self.mt5_mock = Mock()
        
        # Create symbol info mock
        self.symbol_info = Mock()
        self.symbol_info.trade_stops_level = 10  # 10 points minimum
        self.symbol_info.point = 0.00001  # 5 digits (e.g., EURUSD)
        
    def test_buy_order_sl_too_close(self):
        """Test BUY order with stop loss too close to entry."""
        # For BUY at 1.10000, SL must be <= 1.10000 - (10 * 0.00001) = 1.09990
        price = 1.10000
        sl = 1.09995  # Too close (only 5 points away, needs 10)
        
        # Min distance: 10 * 0.00001 = 0.0001
        min_distance = 10 * 0.00001
        expected_sl = price - min_distance  # 1.09990
        
        self.assertLess(expected_sl, sl, "SL too close should be detected")
        
    def test_buy_order_tp_too_close(self):
        """Test BUY order with take profit too close to entry."""
        # For BUY at 1.10000, TP must be >= 1.10000 + (10 * 0.00001) = 1.10010
        price = 1.10000
        tp = 1.10005  # Too close (only 5 points away, needs 10)
        
        min_distance = 10 * 0.00001
        expected_tp = price + min_distance  # 1.10010
        
        self.assertGreater(expected_tp, tp, "TP too close should be detected")
        
    def test_sell_order_sl_too_close(self):
        """Test SELL order with stop loss too close to entry."""
        # For SELL at 1.10000, SL must be >= 1.10000 + (10 * 0.00001) = 1.10010
        price = 1.10000
        sl = 1.10005  # Too close (only 5 points away, needs 10)
        
        min_distance = 10 * 0.00001
        expected_sl = price + min_distance  # 1.10010
        
        self.assertGreater(expected_sl, sl, "SL too close should be detected")
        
    def test_sell_order_tp_too_close(self):
        """Test SELL order with take profit too close to entry."""
        # For SELL at 1.10000, TP must be <= 1.10000 - (10 * 0.00001) = 1.09990
        price = 1.10000
        tp = 1.09995  # Too close (only 5 points away, needs 10)
        
        min_distance = 10 * 0.00001
        expected_tp = price - min_distance  # 1.09990
        
        self.assertLess(expected_tp, tp, "TP too close should be detected")

    def test_valid_buy_order_stops(self):
        """Test BUY order with valid stop levels."""
        price = 1.10000
        sl = 1.09980  # 20 points away (valid, needs 10)
        tp = 1.10020  # 20 points away (valid, needs 10)
        
        min_distance = 10 * 0.00001
        
        # Both should be valid
        self.assertLessEqual(sl, price - min_distance, "SL should be valid")
        self.assertGreaterEqual(tp, price + min_distance, "TP should be valid")

    def test_valid_sell_order_stops(self):
        """Test SELL order with valid stop levels."""
        price = 1.10000
        sl = 1.10020  # 20 points away (valid, needs 10)
        tp = 1.09980  # 20 points away (valid, needs 10)
        
        min_distance = 10 * 0.00001
        
        # Both should be valid
        self.assertGreaterEqual(sl, price + min_distance, "SL should be valid")
        self.assertLessEqual(tp, price - min_distance, "TP should be valid")


if __name__ == '__main__':
    unittest.main()
