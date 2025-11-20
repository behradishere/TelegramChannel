"""Additional test cases for signal_parser module."""
import pytest
from signal_parser import parse_signal, normalize_digits, normalize_text
from decimal import Decimal


class TestNormalization:
    """Test text normalization functions."""

    def test_normalize_persian_digits(self):
        """Test Persian digit normalization."""
        assert normalize_digits('۱۲۳۴۵') == '12345'
        assert normalize_digits('۰۹۸۷۶') == '09876'

    def test_normalize_arabic_digits(self):
        """Test Arabic digit normalization."""
        assert normalize_digits('٠١٢٣٤٥٦٧٨٩') == '0123456789'

    def test_normalize_persian_keywords(self):
        """Test Persian keyword normalization."""
        assert 'scalp' in normalize_text('اسکلپ').lower()
        assert 'buy' in normalize_text('خرید').lower()
        assert 'sell' in normalize_text('فروش').lower()


class TestSignalParser:
    """Test signal parsing functionality."""

    def test_parse_gold_symbol_variants(self):
        """Test parsing of different gold symbol variations."""
        for symbol in ['XAUUSD', 'GOLD', 'XAU']:
            result = parse_signal(f'{symbol} Market price: 2000')
            assert result['symbol'] == 'XAUUSD'

    def test_parse_sell_signal(self):
        """Test parsing of sell signals."""
        text = '''
        XAUUSD
        Sell now: 2050 - 2055
        TP1: 2040
        TP2: 2030
        SL: 2060
        '''
        result = parse_signal(text)
        assert result['side'] == 'sell'
        assert result['sell_range'] == (Decimal('2050'), Decimal('2055'))

    def test_parse_multiple_symbols(self):
        """Test parsing different forex symbols."""
        symbols_map = {
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'USDJPY': 'USDJPY'
        }

        for symbol, expected in symbols_map.items():
            result = parse_signal(f'{symbol} Buy: 1.1000')
            assert result.get('symbol') == expected

    def test_parse_no_symbol(self):
        """Test parsing when no symbol is present."""
        result = parse_signal('Just some random text')
        assert 'symbol' not in result

    def test_parse_open_tp(self):
        """Test parsing of 'open' take profit levels."""
        text = 'XAUUSD TP1: 2000 TP2: open TP3: 2020'
        result = parse_signal(text)
        assert result['tp1'] == Decimal('2000')
        assert result['tp2'] is None
        assert result['tp3'] == Decimal('2020')

    def test_parse_with_persian_numbers(self):
        """Test parsing signal with Persian numbers."""
        text = '''
        XAUUSD
        Market price : ۴۱۱۲
        Buy now : ۴۱۱۲ - ۴۱۰۷
        Tp1 : ۴۱۲۰
        SL : ۴۱۰۱.۵۰
        '''
        result = parse_signal(text)
        assert result['market_price'] == Decimal('4112')
        assert result['tp1'] == Decimal('4120')

    def test_parse_sl_variations(self):
        """Test parsing different SL variations (SL, SI)."""
        for sl_text in ['SL: 2000', 'SI: 2000', 'Sl: 2000']:
            result = parse_signal(f'XAUUSD {sl_text}')
            assert result.get('sl') == Decimal('2000')

    def test_parse_pip_count(self):
        """Test parsing pip count from signal."""
        result = parse_signal('XAUUSD (50 pip)')
        assert result['pip_count'] == 50

    def test_side_detection_priority(self):
        """Test that sell_range/buy_range takes priority over keywords."""
        # Signal with both Buy keyword and sell range
        text = '''
        Don't Buy now!
        XAUUSD
        Sell now: 2050 - 2055
        '''
        result = parse_signal(text)
        assert result['side'] == 'sell'  # Should prioritize sell_range


class TestComplexSignals:
    """Test parsing of complex real-world signal formats."""

    def test_parse_complete_buy_signal(self):
        """Test parsing a complete buy signal with all fields."""
        signal = '''
        🟢 XAUUSD (Scalp)
        
        Market price: 2685.50
        
        Buy now: 2685 - 2680
        
        🎯 Targets:
        TP1: 2690
        TP2: 2695
        TP3: 2700
        TP4: open
        
        🛑 SL: 2675 (100 pip)
        '''

        result = parse_signal(signal)

        assert result['symbol'] == 'XAUUSD'
        assert result['market_price'] == Decimal('2685.50')
        assert result['buy_range'] == (Decimal('2680'), Decimal('2685'))
        assert result['tp1'] == Decimal('2690')
        assert result['tp2'] == Decimal('2695')
        assert result['tp3'] == Decimal('2700')
        assert result['tp4'] is None
        assert result['sl'] == Decimal('2675')
        assert result['pip_count'] == 100
        assert result['side'] == 'buy'

    def test_parse_minimal_signal(self):
        """Test parsing a minimal signal with only essential info."""
        signal = 'XAUUSD Buy: 2680'

        result = parse_signal(signal)

        assert result['symbol'] == 'XAUUSD'
        assert result['side'] == 'buy'
        # Other fields should be missing
        assert 'market_price' not in result
        assert 'sl' not in result

