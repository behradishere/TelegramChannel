"""
Integration tests for backend switching functionality.
Tests the ability to switch between cTrader and MT5 backends.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from src.services.trading_service import TradingService
from src.core.config import AppConfig, TradingConfig, CTraderConfig, MT5Config
from src.domain.models import Order, TradeSide, OrderType


class TestBackendSwitching:
    """Test backend switching between cTrader and MT5."""

    def test_ctrader_backend_initialization(self):
        """Test that cTrader backend initializes correctly."""
        config = AppConfig(
            telegram=MagicMock(),
            trading=TradingConfig(backend='ctrader', dry_run=True),
            ctrader=CTraderConfig(rest_url='https://test.com', token='test123'),
            mt5=MT5Config(),
            logging=MagicMock()
        )

        service = TradingService(config)
        assert service.backend is not None
        assert service.config.trading.backend == 'ctrader'

    def test_mt5_backend_initialization(self):
        """Test that MT5 backend initializes correctly."""
        config = AppConfig(
            telegram=MagicMock(),
            trading=TradingConfig(backend='mt5', dry_run=True),
            ctrader=CTraderConfig(),
            mt5=MT5Config(),
            logging=MagicMock()
        )

        service = TradingService(config)
        assert service.backend is not None
        assert service.config.trading.backend == 'mt5'

    def test_backend_availability_check(self):
        """Test backend availability checking."""
        config = AppConfig(
            telegram=MagicMock(),
            trading=TradingConfig(backend='ctrader', dry_run=True),
            ctrader=CTraderConfig(rest_url='https://test.com', token='test123'),
            mt5=MT5Config(),
            logging=MagicMock()
        )

        service = TradingService(config)
        # In dry run mode, backend should be available
        assert service.is_backend_available()

    @patch.dict(os.environ, {'DRY_RUN': 'true', 'TRADING_BACKEND': 'ctrader'})
    def test_order_execution_dry_run(self):
        """Test order execution in dry run mode."""
        config = AppConfig(
            telegram=MagicMock(),
            trading=TradingConfig(backend='ctrader', dry_run=True),
            ctrader=CTraderConfig(rest_url='https://test.com', token='test123'),
            mt5=MT5Config(),
            logging=MagicMock()
        )

        service = TradingService(config)

        order = Order(
            symbol='XAUUSD',
            side=TradeSide.BUY,
            order_type=OrderType.MARKET,
            volume=0.01,
            price=2000.0,
            stop_loss=1990.0,
            take_profits=[2010.0]
        )

        result = service.execute_order(order)
        assert result is not None
        assert result['status'] == 'dry_run'

