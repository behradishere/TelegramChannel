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
    
    return {
        'symbol': symbol,
        'type': order_type,
        'price': float(price) if price else None,
        'volume': volume,
        'sl': float(sl) if sl else None,
        'tps': [float(x) for x in tps],
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