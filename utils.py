"""Utility functions for the trading bot."""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal


def format_price(price: Optional[float], decimals: int = 2) -> str:
    """Format price for display.

    Args:
        price: Price value
        decimals: Number of decimal places

    Returns:
        Formatted price string
    """
    if price is None:
        return "N/A"
    return f"{price:.{decimals}f}"


def format_volume(volume: float) -> str:
    """Format volume for display.

    Args:
        volume: Volume in lots

    Returns:
        Formatted volume string
    """
    return f"{volume:.2f} lots"


def safe_decimal(value: Any) -> Optional[Decimal]:
    """Safely convert value to Decimal.

    Args:
        value: Value to convert

    Returns:
        Decimal value or None if conversion fails
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, Exception):
        return None


def calculate_pip_distance(price1: float, price2: float, pip_size: float = 0.01) -> float:
    """Calculate distance in pips between two prices.

    Args:
        price1: First price
        price2: Second price
        pip_size: Size of one pip

    Returns:
        Distance in pips
    """
    return abs(price1 - price2) / pip_size


def validate_signal_completeness(parsed: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate if parsed signal has minimum required fields.

    Args:
        parsed: Parsed signal dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if 'symbol' not in parsed:
        return False, "Missing symbol"

    if 'side' not in parsed:
        return False, "Missing trade direction (buy/sell)"

    # Should have either entry price or range
    has_entry = any([
        parsed.get('market_price'),
        parsed.get('buy_range'),
        parsed.get('sell_range')
    ])

    if not has_entry:
        return False, "Missing entry price or range"

    # Should have at least one TP
    has_tp = any([parsed.get(f'tp{i}') for i in range(1, 5)])

    if not has_tp:
        logging.warning("Signal has no take profit levels")

    if not parsed.get('sl'):
        logging.warning("Signal has no stop loss")

    return True, None


def summarize_signal(parsed: Dict[str, Any]) -> str:
    """Create human-readable summary of parsed signal.

    Args:
        parsed: Parsed signal dictionary

    Returns:
        Summary string
    """
    symbol = parsed.get('symbol', 'Unknown')
    side = parsed.get('side', 'unknown').upper()

    # Entry info
    entry = ""
    if parsed.get('market_price'):
        entry = f"Market: {format_price(float(parsed['market_price']))}"
    elif parsed.get('buy_range'):
        low, high = parsed['buy_range']
        entry = f"Range: {format_price(float(low))}-{format_price(float(high))}"
    elif parsed.get('sell_range'):
        low, high = parsed['sell_range']
        entry = f"Range: {format_price(float(low))}-{format_price(float(high))}"

    # TPs
    tps = []
    for i in range(1, 5):
        tp = parsed.get(f'tp{i}')
        if tp:
            tps.append(f"TP{i}:{format_price(float(tp))}")
        elif tp is None and f'tp{i}' in parsed:
            tps.append(f"TP{i}:OPEN")

    tp_str = ", ".join(tps) if tps else "None"

    # SL
    sl = parsed.get('sl')
    sl_str = format_price(float(sl)) if sl else "None"

    # Pip count
    pips = parsed.get('pip_count', 'N/A')

    return f"{symbol} {side} | {entry} | TPs: {tp_str} | SL: {sl_str} | Pips: {pips}"


def summarize_order(order: Dict[str, Any]) -> str:
    """Create human-readable summary of order.

    Args:
        order: Order dictionary

    Returns:
        Summary string
    """
    symbol = order.get('symbol', 'Unknown')
    side = order.get('side', 'unknown').upper()
    order_type = order.get('type', 'market').upper()
    price = format_price(order.get('price'))
    volume = format_volume(order.get('volume', 0))
    sl = format_price(order.get('sl'))

    tps = order.get('tps', [])
    tp_str = ", ".join([format_price(tp) for tp in tps]) if tps else "None"

    return f"{symbol} {side} {order_type} @ {price} | Vol: {volume} | SL: {sl} | TPs: {tp_str}"

