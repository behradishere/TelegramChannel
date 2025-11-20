"""Test suite for risk management functionality."""
import pytest
from risk_manager import RiskManager


class TestRiskManager:
    """Test cases for RiskManager class."""

    def test_initialization(self):
        """Test RiskManager initialization."""
        rm = RiskManager(
            account_balance=10000.0,
            risk_percent=2.0,
            min_volume=0.01,
            max_volume=1.0
        )
        assert rm.account_balance == 10000.0
        assert rm.risk_percent == 2.0
        assert rm.min_volume == 0.01
        assert rm.max_volume == 1.0

    def test_position_size_calculation(self):
        """Test position size calculation with valid parameters."""
        rm = RiskManager(account_balance=10000.0, risk_percent=1.0)

        # Entry at 2000, SL at 1990, 10 point difference
        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1990.0,
            pip_value=0.01
        )

        assert position_size > 0
        assert position_size >= rm.min_volume
        assert position_size <= rm.max_volume

    def test_position_size_with_missing_sl(self):
        """Test that default volume is used when SL is missing."""
        rm = RiskManager(account_balance=10000.0, default_volume=0.05)

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=None
        )

        assert position_size == 0.05

    def test_position_size_respects_max_volume(self):
        """Test that position size never exceeds max volume."""
        rm = RiskManager(
            account_balance=100000.0,
            risk_percent=10.0,  # Very high risk
            max_volume=0.5
        )

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1999.0  # Very tight SL
        )

        assert position_size <= 0.5

    def test_position_size_respects_min_volume(self):
        """Test that position size never goes below min volume."""
        rm = RiskManager(
            account_balance=100.0,  # Small account
            risk_percent=1.0,
            min_volume=0.01
        )

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1900.0  # Large SL
        )

        assert position_size >= 0.01

    def test_validate_trade_valid(self):
        """Test trade validation with valid order."""
        rm = RiskManager(min_volume=0.01, max_volume=1.0)

        order = {
            'volume': 0.1,
            'price': 2000.0,
            'sl': 1990.0
        }

        is_valid, error = rm.validate_trade(order)
        assert is_valid is True
        assert error is None

    def test_validate_trade_volume_too_low(self):
        """Test trade validation rejects volume below minimum."""
        rm = RiskManager(min_volume=0.01, max_volume=1.0)

        order = {
            'volume': 0.001,
            'price': 2000.0
        }

        is_valid, error = rm.validate_trade(order)
        assert is_valid is False
        assert 'minimum' in error.lower()

    def test_validate_trade_volume_too_high(self):
        """Test trade validation rejects volume above maximum."""
        rm = RiskManager(min_volume=0.01, max_volume=1.0)

        order = {
            'volume': 5.0,
            'price': 2000.0
        }

        is_valid, error = rm.validate_trade(order)
        assert is_valid is False
        assert 'maximum' in error.lower()

    def test_validate_trade_sl_too_tight(self):
        """Test trade validation rejects orders with too tight stop loss."""
        rm = RiskManager()

        order = {
            'volume': 0.1,
            'price': 2000.0,
            'sl': 2000.001  # Extremely tight SL
        }

        is_valid, error = rm.validate_trade(order)
        assert is_valid is False
        assert 'tight' in error.lower()

