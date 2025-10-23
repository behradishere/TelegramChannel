# signal_bot.py
import os
import re
import json
import logging
from decimal import Decimal
from dotenv import load_dotenv
from telethon import TelegramClient, events
import requests

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "signals_session")
CHANNEL = os.getenv("CHANNEL_USERNAME")  # e.g. '@mychannel' or numeric id like -100XXXX
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1","true","yes")

BROKER_REST_URL = os.getenv("BROKER_REST_URL")
BROKER_API_KEY = os.getenv("BROKER_API_KEY")
SYMBOL_XAU = os.getenv("SYMBOL_XAU", "XAUUSD")
PIP_SIZE = Decimal(os.getenv("PIP_SIZE", "0.01"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Persian/Arabic digit translation table
_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
def normalize_digits(s: str) -> str:
    return s.translate(_map)

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = normalize_digits(s)
    # unify some persian tokens
    s = s.replace('اسکلپ','scalp').replace('خرید','Buy').replace('فروش','Sell')
    return s

def parse_signal(text: str) -> dict:
    """Return dict with keys: symbol, market_price, buy_range (low,high), tp1..tp4, sl, pip_count"""
    t = normalize_text(text)
    res = {}
    # Symbol
    m = re.search(r'\b(XAUUSD|GOLD|XAU)\b', t, re.I)
    if m:
        res['symbol'] = 'XAUUSD'
    # Market price
    m = re.search(r'Market\s*price\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        res['market_price'] = Decimal(m.group(1))
    # Buy range (allow either order)
    m = re.search(r'Buy\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        a, b = Decimal(m.group(1)), Decimal(m.group(2))
        res['buy_range'] = (min(a,b), max(a,b))
    # TPs
    for i in range(1,5):
        m = re.search(r'Tp{}[\s:\-]*([0-9]+(?:\.[0-9]+)?|open)'.format(i), t, re.I)
        if m:
            val = m.group(1).lower()
            res[f'tp{i}'] = None if val == 'open' else Decimal(val)
    # SL (accept Sl or SI or S[I|L])
    m = re.search(r'\bS[LI]\b\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
    if m:
        res['sl'] = Decimal(m.group(1))
    else:
        m = re.search(r'Sl\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)', t, re.I)
        if m:
            res['sl'] = Decimal(m.group(1))
    # pip count
    m = re.search(r'(\d+)\s*pip', t, re.I)
    if m:
        res['pip_count'] = int(m.group(1))
    return res

def decide_order(parsed: dict) -> dict:
    """Make simple trade decision. Returns order dict with type, price, volume, sl, tps etc."""
    if not parsed.get('symbol'):
        raise ValueError("No symbol")
    symbol = parsed['symbol']
    market = parsed.get('market_price')
    buy_range = parsed.get('buy_range')
    sl = parsed.get('sl')
    tps = [parsed.get(f'tp{i}') for i in range(1,5) if parsed.get(f'tp{i}') is not None]

    # Decide: if market inside buy_range or buy_range absent -> MARKET order.
    # If market is outside buy_range but buy_range exists: place LIMIT at midpoint of buy_range.
    if buy_range:
        low, high = buy_range
        if market is not None and low <= market <= high:
            order_type = 'market'
            price = market
        else:
            order_type = 'limit'
            price = (low + high) / 2
    else:
        order_type = 'market'
        price = market

    # Volume sizing: simple fixed lot example - you will implement proper risk management
    volume = 0.01  # example lot: change per your broker & account
    return {
        'symbol': symbol,
        'order_type': order_type,
        'price': float(price) if price is not None else None,
        'volume': volume,
        'sl': float(sl) if sl is not None else None,
        'tps': [float(x) for x in tps],
    }

def place_order_rest(order: dict) -> dict:
    """Example REST broker order. Replace with your broker's API call.
       Returns broker response JSON on success.
    """
    if DRY_RUN:
        logging.info("DRY_RUN enabled — not sending to broker. Order prepared: %s", order)
        return {'status': 'dry_run', 'order': order}
    if not BROKER_REST_URL or not BROKER_API_KEY:
        raise ValueError("Broker config missing")

    payload = {
        "symbol": order['symbol'],
        "type": order['order_type'],
        "price": order['price'],
        "volume": order['volume'],
        "sl": order['sl'],
        "tps": order['tps'],
    }
    headers = {'Authorization': f'Bearer {BROKER_API_KEY}', 'Content-Type': 'application/json'}
    resp = requests.post(BROKER_REST_URL, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

# Telethon client & event loop
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL))
async def on_new_message(event):
    try:
        text = event.message.message or ""
        logging.info("New message from %s: %s", CHANNEL, text[:120].replace("\n"," "))
        parsed = parse_signal(text)
        logging.info("Parsed: %s", parsed)
        if 'symbol' not in parsed:
            logging.info("No recognizable symbol — skipping")
            return
        order = decide_order(parsed)
        # optional: here you can implement a confirmation step (e.g., send yourself a message)
        res = place_order_rest(order)
        logging.info("Order result: %s", res)
    except Exception as e:
        logging.exception("Error processing message: %s", e)

def main():
    logging.info("Starting client, listening to %s", CHANNEL)
    client.start()
    client.run_until_disconnected()

if __name__ == "__main__":
    main()