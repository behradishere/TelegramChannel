import pytest
from src.services.signal_parser import SignalParser
from decimal import Decimal

parser = SignalParser()

SAMPLE = '''
XAUUSD ( اسکلپ )

Market price : 4112

Buy  now : 4112 - 4107

Tp1 : 4120

Tp2 : 4128

Tp3 :4146

Tp4 : open

Sl : 4101.50        ( 80 pip )
'''


def test_parse_sample():
    signal = parser.parse(SAMPLE)
    assert signal.symbol == 'XAUUSD'
    assert signal.market_price == Decimal('4112')
    assert signal.buy_range[0] == Decimal('4107')
    assert signal.buy_range[1] == Decimal('4112')
    assert signal.take_profits[0] == Decimal('4120')
    assert signal.take_profits[1] == Decimal('4128')
    assert signal.take_profits[2] == Decimal('4146')
    assert signal.take_profits[3] is None
    assert signal.stop_loss == Decimal('4101.50')
    assert signal.pip_count == 80
    assert signal.side.value == 'buy'

