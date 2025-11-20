"""
Unit tests for backend switching functionality.
Tests the ability to switch between cTrader and MT5 backends.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestBackendSwitching:
    """Test backend switching between cTrader and MT5."""

    @patch.dict(os.environ, {'TRADING_BACKEND': 'ctrader', 'BROKER_REST_URL': 'https://test.com', 'CTRADER_TOKEN': 'token123'})
    def test_ctrader_backend_available(self):
        """Test that cTrader backend is detected as available when credentials are set."""
        # Need to reload module to pick up new env vars
        import importlib
        import order_manager
        importlib.reload(order_manager)

        assert order_manager.TRADING_BACKEND == 'ctrader'
        assert order_manager.backend_available() is True

    @patch.dict(os.environ, {'TRADING_BACKEND': 'ctrader', 'BROKER_REST_URL': '', 'CTRADER_TOKEN': ''})
    def test_ctrader_backend_unavailable(self):
        """Test that cTrader backend is detected as unavailable when credentials are missing."""
        import importlib
        import order_manager
        importlib.reload(order_manager)

        assert order_manager.TRADING_BACKEND == 'ctrader'
        assert order_manager.backend_available() is False

    @patch.dict(os.environ, {'TRADING_BACKEND': 'mt5'})
    def test_mt5_backend_detection(self):
        """Test MT5 backend detection."""
        import importlib
        import order_manager
        importlib.reload(order_manager)

        assert order_manager.TRADING_BACKEND == 'mt5'
        # backend_available() will return False on systems without MetaTrader5 package
        # This is expected on macOS/Linux without Wine

    @patch.dict(os.environ, {'TRADING_BACKEND': 'ctrader', 'DRY_RUN': 'true'})
    def test_decide_order_generic(self):
        """Test that decide_order works regardless of backend."""
        from order_manager import decide_order

        parsed = {
            'symbol': 'XAUUSD',
            'side': 'buy',
            'market_price': 2000.0,
            'buy_range': (1995.0, 2005.0),
            'sl': 1990.0,
            'tp1': 2010.0,
        }

        order = decide_order(parsed)

        assert order['symbol'] == 'XAUUSD'
        assert order['side'] == 'buy'
        assert order['sl'] == 1990.0
        assert 2010.0 in order['tps']

    @patch.dict(os.environ, {'TRADING_BACKEND': 'ctrader', 'DRY_RUN': 'true'})
    def test_place_order_ctrader_dry_run(self):
        """Test placing order with cTrader backend in DRY_RUN mode."""
        from order_manager import place_order

        order = {
            'symbol': 'XAUUSD',
            'type': 'market',
            'price': 2000.0,
            'volume': 0.01,
            'sl': 1990.0,
            'tps': [2010.0],
            'side': 'buy',
        }

        result = place_order(order)

        assert result['status'] == 'dry_run'
        assert result['order']['symbol'] == 'XAUUSD'

    @patch.dict(os.environ, {'TRADING_BACKEND': 'mt5', 'DRY_RUN': 'true'})
    def test_place_order_mt5_dry_run(self):
        """Test placing order with MT5 backend in DRY_RUN mode."""
        from order_manager import place_order

        order = {
            'symbol': 'XAUUSD',
            'type': 'market',
            'price': 2000.0,
            'volume': 0.01,
            'sl': 1990.0,
            'tps': [2010.0],
            'side': 'buy',
        }

        result = place_order(order)

        assert result['status'] == 'dry_run'
        assert result['order']['symbol'] == 'XAUUSD'

    def test_invalid_backend(self):
        """Test that invalid backend raises error."""
        with patch.dict(os.environ, {'TRADING_BACKEND': 'invalid'}):
            import importlib
            import order_manager
            importlib.reload(order_manager)

            order = {
                'symbol': 'XAUUSD',
                'type': 'market',
                'price': 2000.0,
                'volume': 0.01,
                'side': 'buy',
            }

            with pytest.raises(ValueError, match="Unknown TRADING_BACKEND"):
                order_manager.place_order(order)


class TestMT5Backend:
    """Test MT5 backend specific functionality."""

    def test_mt5_availability_check(self):
        """Test MT5 availability detection."""
        try:
            from mt5_backend import is_mt5_available
            # Should return True on Windows with MT5 installed, False otherwise
            available = is_mt5_available()
            assert isinstance(available, bool)
        except ImportError:
            pytest.skip("mt5_backend module not available")

    @patch.dict(os.environ, {'DRY_RUN': 'true', 'MT5_LOGIN': '', 'MT5_PASSWORD': '', 'MT5_SERVER': ''})
    def test_mt5_place_order_dry_run(self):
        """Test MT5 order placement in DRY_RUN mode."""
        try:
            from mt5_backend import place_mt5_order

            order = {
                'symbol': 'XAUUSD',
                'type': 'market',
                'price': 2000.0,
                'volume': 0.01,
                'sl': 1990.0,
                'tps': [2010.0],
                'side': 'buy',
            }

            result = place_mt5_order(order)

            assert result['status'] == 'dry_run'
            assert result['order']['symbol'] == 'XAUUSD'
        except ImportError:
            pytest.skip("mt5_backend module not available")


class TestConfigValidation:
    """Test configuration validation for different backends."""

    @patch.dict(os.environ, {
        'API_ID': '123456',
        'API_HASH': 'test_hash',
        'TRADING_BACKEND': 'mt5',
    })
    def test_mt5_config_valid(self):
        """Test that MT5 configuration is valid."""
        import importlib
        import config
        importlib.reload(config)

        cfg = config.Config()
        assert cfg.TRADING_BACKEND == 'mt5'

        issues = cfg.validate()
        # Should not have issues about backend type
        backend_issues = [i for i in issues if 'TRADING_BACKEND' in i]
        assert len(backend_issues) == 0

    @patch.dict(os.environ, {
        'API_ID': '123456',
        'API_HASH': 'test_hash',
        'TRADING_BACKEND': 'ctrader',
        'DRY_RUN': 'false',
        'BROKER_REST_URL': '',
        'CTRADER_TOKEN': '',
    }, clear=False)
    def test_ctrader_config_missing_credentials(self):
        """Test that cTrader without credentials shows warnings."""
        import importlib
        import config
        importlib.reload(config)

        cfg = config.Config()
        assert cfg.TRADING_BACKEND == 'ctrader'
        assert cfg.DRY_RUN is False

        issues = cfg.validate()
        # Should have issues about missing credentials
        assert any('BROKER_REST_URL' in i for i in issues) or any('CTRADER_TOKEN' in i for i in issues), f"Expected credential issues, got: {issues}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

