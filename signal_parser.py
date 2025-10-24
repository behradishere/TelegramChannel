# signal_parser.py
import re
from decimal import Decimal

# Persian/Arabic digit translation
_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

def normalize_digits(s: str) -> str:
    return s.translate(_map)

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = normalize_digits(s)
    s = s.replace('اسکلپ', 'scalp').replace('خرید', 'Buy').replace('فروش', 'Sell')
    return s

def parse_signal(text: str) -> dict:
    """Extract key trade info from raw signal message."""
    t = normalize_text(text)
    res = {}
    
    m = re.search(r'\b(XAUUSD|GOLD|XAU)\b', t, re.I)
    if m: res['symbol'] = 'XAUUSD'
    
    m = re.search(r'Market\s*price\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m: res['market_price'] = Decimal(m.group(1))
    
    m = re.search(r'Buy\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        a, b = Decimal(m.group(1)), Decimal(m.group(2))
        res['buy_range'] = (min(a,b), max(a,b))
    
    for i in range(1,5):
        m = re.search(fr'Tp{i}[\s:\-]*([0-9]+(?:\.[0-9]+)?|open)', t, re.I)
        if m:
            val = m.group(1).lower()
            res[f'tp{i}'] = None if val == 'open' else Decimal(val)
    
    m = re.search(r'\bS[LI]\b\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m: res['sl'] = Decimal(m.group(1))
    
    m = re.search(r'(\d+)\s*pip', t, re.I)
    if m: res['pip_count'] = int(m.group(1))
    
    # detect side (Buy/Sell) if present in text
    m = re.search(r'\b(Buy|Sell)\b', t, re.I)
    if m:
        res['side'] = m.group(1).lower()

    return res