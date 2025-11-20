# signal_parser.py
import re
from decimal import Decimal
from typing import Dict, Optional, Tuple

# Persian/Arabic digit translation
_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def normalize_digits(s: str) -> str:
    """Convert Persian/Arabic digits to Western digits."""
    return s.translate(_map)

def normalize_text(s: str) -> str:
    """Normalize text by converting digits and Persian keywords to English."""
    if not s:
        return ""
    s = normalize_digits(s)
    s = s.replace('اسکلپ', 'scalp').replace('خرید', 'Buy').replace('فروش', 'Sell')
    return s

def parse_signal(text: str) -> Dict[str, any]:
    """Extract key trade info from raw signal message.

    Args:
        text: Raw signal message text

    Returns:
        Dictionary containing parsed signal data with keys:
        - symbol: Trading symbol (e.g., 'XAUUSD')
        - market_price: Current market price
        - buy_range: Tuple of (low, high) buy range
        - sell_range: Tuple of (low, high) sell range
        - tp1-tp4: Take profit levels
        - sl: Stop loss level
        - pip_count: Number of pips
        - side: 'buy' or 'sell'
    """
    t = normalize_text(text)
    res = {}
    
    # Symbol detection - support multiple symbols
    m = re.search(r'\b(XAUUSD|GOLD|XAU|EURUSD|GBPUSD|USDJPY|BTCUSD|ETHUSD)\b', t, re.I)
    if m:
        symbol_map = {
            'GOLD': 'XAUUSD',
            'XAU': 'XAUUSD',
        }
        res['symbol'] = symbol_map.get(m.group(1).upper(), m.group(1).upper())

    # Market price
    m = re.search(r'Market\s*price\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        res['market_price'] = Decimal(m.group(1))

    # Buy range
    m = re.search(r'Buy\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        a, b = Decimal(m.group(1)), Decimal(m.group(2))
        res['buy_range'] = (min(a,b), max(a,b))
    
    # Sell range
    m = re.search(r'Sell\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        a, b = Decimal(m.group(1)), Decimal(m.group(2))
        res['sell_range'] = (min(a,b), max(a,b))

    # Take profit levels
    for i in range(1, 5):
        m = re.search(fr'Tp{i}[\s:\-]*([0-9]+(?:\.[0-9]+)?|open)', t, re.I)
        if m:
            val = m.group(1).lower()
            res[f'tp{i}'] = None if val == 'open' else Decimal(val)
    
    # Stop loss (accept SL, SI, or S[I|L])
    m = re.search(r'\bS[LI]\b\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        res['sl'] = Decimal(m.group(1))

    # Pip count
    m = re.search(r'(\d+)\s*pip', t, re.I)
    if m:
        res['pip_count'] = int(m.group(1))

    # Detect side (Buy/Sell) - prioritize buy_range/sell_range over keyword
    if 'sell_range' in res:
        res['side'] = 'sell'
    elif 'buy_range' in res:
        res['side'] = 'buy'
    else:
        m = re.search(r'\b(Buy|Sell)\b', t, re.I)
        if m:
            res['side'] = m.group(1).lower()

    return res

    return res
