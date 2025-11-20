"""Test suite for risk management functionality."""
import pytest
from src.services.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.domain.models import Order, TradeSide, OrderType


class TestRiskManager:
    """Test cases for RiskManager class."""

    def test_initialization(self):
        """Test RiskManager initialization."""
        config = TradingConfig(
            account_balance=10000.0,
            risk_percent=2.0,
            min_volume=0.01,
            max_volume=1.0
        )
        rm = RiskManager(config)
        assert rm.account_balance == 10000.0
        assert rm.risk_percent == 2.0
        assert rm.min_volume == 0.01
        assert rm.max_volume == 1.0

    def test_position_size_calculation(self):
        """Test position size calculation with valid parameters."""
        config = TradingConfig(account_balance=10000.0, risk_percent=1.0)
        rm = RiskManager(config)

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
        config = TradingConfig(account_balance=10000.0, default_volume=0.05)
        rm = RiskManager(config)

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=None
        )

        assert position_size == 0.05

    def test_position_size_respects_max_volume(self):
        """Test that position size never exceeds max volume."""
        config = TradingConfig(
            account_balance=100000.0,
            risk_percent=10.0,
            max_volume=0.5
        )
        rm = RiskManager(config)

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1999.0
        )

        assert position_size <= 0.5

    def test_position_size_respects_min_volume(self):
        """Test that position size never goes below min volume."""
        config = TradingConfig(
            account_balance=100.0,
            risk_percent=1.0,
            min_volume=0.01
        )
        rm = RiskManager(config)

        position_size = rm.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1900.0
        )

        assert position_size >= 0.01

    def test_validate_trade_valid(self):
        """Test trade validation with valid order."""
        config = TradingConfig(min_volume=0.01, max_volume=1.0)
        rm = RiskManager(config)

        order = Order(
            symbol='XAUUSD',
            side=TradeSide.BUY,
            order_type=OrderType.MARKET,
            volume=0.1,
            price=2000.0,
            stop_loss=1990.0
        )

        is_valid, error = rm.validate_order(order)
        assert is_valid is True
        assert error is None

    def test_validate_trade_volume_too_low(self):
        """Test trade validation rejects volume below minimum."""
        config = TradingConfig(min_volume=0.01, max_volume=1.0)
        rm = RiskManager(config)

        order = Order(
            symbol='XAUUSD',
            side=TradeSide.BUY,
            order_type=OrderType.MARKET,
            volume=0.001,
            price=2000.0
        )

        is_valid, error = rm.validate_order(order)
        assert is_valid is False
        assert 'minimum' in error.lower()

    def test_validate_trade_volume_too_high(self):
        """Test trade validation rejects volume above maximum."""
        config = TradingConfig(min_volume=0.01, max_volume=1.0)
        rm = RiskManager(config)

        order = Order(
            symbol='XAUUSD',
            side=TradeSide.BUY,
            order_type=OrderType.MARKET,
            volume=5.0,
            price=2000.0
        )

        is_valid, error = rm.validate_order(order)
        assert is_valid is False
        assert 'maximum' in error.lower()

    def test_risk_reward_calculation(self):
        """Test risk-reward ratio calculation."""
        config = TradingConfig()
        rm = RiskManager(config)

        ratio = rm.calculate_risk_reward_ratio(
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0
        )

        assert ratio == 2.0  # 20 point reward / 10 point risk

