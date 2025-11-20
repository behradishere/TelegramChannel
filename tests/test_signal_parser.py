import pytest
from signal_parser import parse_signal

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
    assert signal.market_price is not None
    assert signal.buy_range[0] == 4107 or signal.buy_range[1] == 4112
    assert signal.take_profits[0] == 4120
    assert signal.take_profits[1] == 4128
    assert signal.take_profits[2] == 4146
    assert signal.take_profits[3] is None
    assert parsed['sl'] == 4101.50
    assert parsed['pip_count'] == 80
    assert parsed.get('side') == 'buy'
