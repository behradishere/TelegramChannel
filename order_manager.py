# order_manager.py
import os
import logging
import requests
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()
BROKER_REST_URL = os.getenv("BROKER_REST_URL")      # e.g. https://api.spotware.com/v1/trading
CTRADER_TOKEN = os.getenv("CTRADER_TOKEN")           # OAuth2 token
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
TRADING_BACKEND = os.getenv("TRADING_BACKEND", "ctrader").lower()  # 'ctrader' or 'mt5'


def backend_available() -> bool:
    """Check whether the configured trading backend appears available.

    - For 'ctrader' we check that BROKER_REST_URL and CTRADER_TOKEN are set.
    - For 'mt5' we try to import the MetaTrader5 package (actual terminal availability
      cannot be fully checked here).
    Returns True if backend looks usable, False otherwise.
    """
    backend = TRADING_BACKEND
    if backend == 'ctrader':
        return bool(BROKER_REST_URL and CTRADER_TOKEN)
    if backend == 'mt5':
        try:
            import MetaTrader5  # type: ignore
            return True
        except Exception:
            return False
    return False

def decide_order(parsed: dict) -> dict:
    """Convert parsed data into executable order details."""
    if not parsed.get('symbol'):
        raise ValueError("No symbol detected")
    
    symbol = parsed['symbol']
    market = parsed.get('market_price')
    buy_range = parsed.get('buy_range')
    sl = parsed.get('sl')
    tps = [parsed.get(f'tp{i}') for i in range(1,5) if parsed.get(f'tp{i}')]

    if buy_range:
        low, high = buy_range
        if market and low <= market <= high:
            order_type = 'market'
            price = market
        else:
            order_type = 'limit'
            price = (low + high) / 2
    else:
        order_type = 'market'
        price = market

    volume = 0.01  # Example fixed lot size
    side = parsed.get('side', 'buy').lower()
    
    return {
        'symbol': symbol,
        'type': order_type,
        'price': float(price) if price else None,
        'volume': volume,
        'sl': float(sl) if sl else None,
        'tps': [float(x) for x in tps],
        'side': side,
    }

def place_order_ctrader(order: dict):
    """Send order to cTrader REST API."""
    if DRY_RUN:
        logging.info("[DRY_RUN] Order prepared: %s", order)
        return {'status': 'dry_run', 'order': order}
    
    if not BROKER_REST_URL or not CTRADER_TOKEN:
        raise ValueError("cTrader credentials missing")
    
    headers = {
        'Authorization': f'Bearer {CTRADER_TOKEN}',
        'Content-Type': 'application/json',
    }
    resp = requests.post(f"{BROKER_REST_URL}/orders", json=order, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def place_order_mt5(order: dict):
    """Send order using MetaTrader5 (desktop) API. This will only work on platforms
    where MetaTrader5 Python package and terminal are available (typically Windows).
    The function tries to initialize MT5, build a trade request and send it.
    """
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        raise RuntimeError("MetaTrader5 package is not available. Install it or switch TRADING_BACKEND to 'ctrader'.") from e

    if DRY_RUN:
        logging.info("[DRY_RUN][MT5] Order prepared: %s", order)
        return {'status': 'dry_run', 'order': order}

    # Initialize
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    symbol = order['symbol']
    volume = float(order.get('volume', 0.01))
    side = order.get('side', 'buy').lower()
    order_type = order.get('type', 'market')

    # Ensure symbol exists
    sym_info = mt5.symbol_info(symbol)
    if sym_info is None:
        mt5.shutdown()
        raise ValueError(f"Symbol {symbol} not found in MT5 terminal")

    tick = mt5.symbol_info_tick(symbol)
    price = order.get('price')
    if order_type == 'market' or price is None:
        price = tick.ask if side == 'buy' else tick.bid

    mt5_type = mt5.ORDER_TYPE_BUY if side == 'buy' else mt5.ORDER_TYPE_SELL

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": mt5_type,
        "price": float(price),
        "sl": float(order.get('sl')) if order.get('sl') else None,
        "tp": float(order.get('tps')[0]) if order.get('tps') else None,
        "deviation": 20,
        "magic": 234000,
        "comment": "signal-exec",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Remove None values because MT5 expects floats for price/sl/tp
    for k in ['sl', 'tp']:
        if req.get(k) is None:
            req.pop(k, None)

    result = mt5.order_send(req)
    # Do not shutdown here; keep MT5 initialized for subsequent orders may be fine
    if result is None:
        raise RuntimeError(f"MT5 order_send returned None; last_error={mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Order failed, retcode={result.retcode}, result={result}")
    return result._asdict() if hasattr(result, '_asdict') else result


def place_order(order: dict):
    """Dispatch order to the selected trading backend."""
    backend = TRADING_BACKEND
    if backend == 'mt5':
        return place_order_mt5(order)
    elif backend == 'ctrader':
        return place_order_ctrader(order)
    else:
        raise ValueError(f"Unknown TRADING_BACKEND: {backend}. Use 'ctrader' or 'mt5'.")
        raise ValueError(f"Unknown TRADING_BACKEND: {backend}")