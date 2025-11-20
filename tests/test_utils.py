"""Test suite for utility functions."""
import pytest
from utils import (
    format_price,
    format_volume,
    calculate_pip_distance,
    validate_signal_completeness,
    summarize_signal,
    summarize_order,
    safe_decimal
)
from decimal import Decimal


class TestFormatters:
    """Test formatting functions."""

    def test_format_price(self):
        """Test price formatting."""
        assert format_price(2000.50) == "2000.50"
        assert format_price(2000.5, decimals=1) == "2000.5"
        assert format_price(None) == "N/A"

    def test_format_volume(self):
        """Test volume formatting."""
        assert format_volume(0.01) == "0.01 lots"
        assert format_volume(1.5) == "1.50 lots"


class TestCalculations:
    """Test calculation functions."""

    def test_calculate_pip_distance(self):
        """Test pip distance calculation."""
        assert calculate_pip_distance(2000.0, 2010.0, 0.01) == 1000.0
        assert calculate_pip_distance(2010.0, 2000.0, 0.01) == 1000.0
        assert calculate_pip_distance(2000.0, 2005.0, 0.01) == 500.0

    def test_safe_decimal(self):
        """Test safe decimal conversion."""
        assert safe_decimal(100) == Decimal('100')
        assert safe_decimal("100.5") == Decimal('100.5')
        assert safe_decimal(None) is None
        assert safe_decimal("invalid") is None


class TestValidation:
    """Test validation functions."""

    def test_validate_complete_signal(self):
        """Test validation of complete signal."""
        signal = {
            'symbol': 'XAUUSD',
            'side': 'buy',
            'market_price': Decimal('2000'),
            'tp1': Decimal('2010'),
            'sl': Decimal('1990')
        }

        is_valid, error = validate_signal_completeness(signal)
        assert is_valid is True
        assert error is None

    def test_validate_missing_symbol(self):
        """Test validation fails without symbol."""
        signal = {
            'side': 'buy',
            'market_price': Decimal('2000')
        }

        is_valid, error = validate_signal_completeness(signal)
        assert is_valid is False
        assert 'symbol' in error.lower()

    def test_validate_missing_side(self):
        """Test validation fails without side."""
        signal = {
            'symbol': 'XAUUSD',
            'market_price': Decimal('2000')
        }

        is_valid, error = validate_signal_completeness(signal)
        assert is_valid is False
        assert 'direction' in error.lower() or 'side' in error.lower()

    def test_validate_missing_entry(self):
        """Test validation fails without entry price."""
        signal = {
            'symbol': 'XAUUSD',
            'side': 'buy'
        }

        is_valid, error = validate_signal_completeness(signal)
        assert is_valid is False
        assert 'entry' in error.lower() or 'price' in error.lower()


class TestSummarizers:
    """Test summary functions."""

    def test_summarize_signal(self):
        """Test signal summarization."""
        signal = {
            'symbol': 'XAUUSD',
            'side': 'buy',
            'market_price': Decimal('2000.00'),
            'tp1': Decimal('2010.00'),
            'tp2': Decimal('2020.00'),
            'sl': Decimal('1990.00'),
            'pip_count': 100
        }

        summary = summarize_signal(signal)
        assert 'XAUUSD' in summary
        assert 'BUY' in summary
        assert '2000.00' in summary
        assert 'TP1' in summary
        assert 'SL' in summary

    def test_summarize_order(self):
        """Test order summarization."""
        order = {
            'symbol': 'XAUUSD',
            'side': 'buy',
            'type': 'market',
            'price': 2000.00,
            'volume': 0.1,
            'sl': 1990.00,
            'tps': [2010.00, 2020.00]
        }

        summary = summarize_order(order)
        assert 'XAUUSD' in summary
        assert 'BUY' in summary
        assert 'MARKET' in summary
        assert '0.10 lots' in summary

