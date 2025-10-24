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
    parsed = parse_signal(SAMPLE)
    assert parsed['symbol'] == 'XAUUSD'
    assert 'market_price' in parsed
    assert parsed['buy_range'][0] == 4112 or parsed['buy_range'][1] == 4112
    assert parsed['tp1'] == 4120
    assert parsed['tp2'] == 4128
    assert parsed['tp3'] == 4146
    assert parsed['tp4'] is None
    assert parsed['sl'] == 4101.50
    assert parsed['pip_count'] == 80
    assert parsed.get('side') == 'buy'
