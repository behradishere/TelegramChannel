# main.py
import logging
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel
import time
from logging.handlers import RotatingFileHandler
from signal_parser import parse_signal
from order_manager import decide_order, place_order, backend_available, TRADING_BACKEND

# Validate API credentials
load_dotenv()
# Validate API credentials
SESSION_NAME = os.getenv("SESSION_NAME", "signals_session")
api_id_raw = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHANNEL = os.getenv("CHANNEL_USERNAME")

if not api_id_raw or not API_HASH:
    raise SystemExit("API_ID and API_HASH must be set in environment or .env")

try:
    API_ID = int(api_id_raw)
except ValueError:
    raise SystemExit(f"API_ID must be an integer, got: {api_id_raw!r}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
# Add rotating file handler for persistent logs
LOG_FILE = os.path.join(os.path.dirname(__file__), 'bot.log')
rot_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
rot_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logging.getLogger().addHandler(rot_handler)

HEALTH_FILE = os.path.join(os.path.dirname(__file__), 'health.txt')

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def handle_new_message(event):
    text = event.message.message or ""
    # Use event.chat_id or CHANNEL for logging clarity
    chat_ident = getattr(event.chat, 'id', None) if getattr(event, 'chat', None) else None
    logging.info("📨 New message from %s (chat id=%s): %s", CHANNEL or 'unknown', chat_ident, text[:120].replace("\n", " "))
    try:
        parsed = parse_signal(text)
        logging.info("✅ Parsed Signal: %s", parsed)
        if 'symbol' not in parsed:
            logging.info("No recognizable symbol — skipping")
            return
        order = decide_order(parsed)
        result = place_order(order)
        logging.info("🚀 Order sent: %s", result)
        # update health file on successful processing
        try:
            with open(HEALTH_FILE, 'w', encoding='utf-8') as hf:
                hf.write(f"last_message={int(time.time())}\nsymbol={parsed.get('symbol')}\n")
        except Exception:
            pass
    except Exception as e:
        logging.exception("Error while handling message: %s", e)

def main():
    logging.info("Listening to Telegram channel %s", CHANNEL)
    # Check backend availability early and warn/exit if necessary
    backend = TRADING_BACKEND
    if backend == 'mt5' and not backend_available():
        logging.error("TRADING_BACKEND=mt5 but MetaTrader5 package is not available. Either install MetaTrader5 or set TRADING_BACKEND=ctrader.")
        return
    if backend == 'ctrader' and not backend_available():
        logging.warning("TRADING_BACKEND=ctrader but CTRADER credentials (BROKER_REST_URL/CTRADER_TOKEN) are missing. The bot will run in DRY_RUN mode or fail on order placement.")

    client.start()

    # Resolve CHANNEL to an entity before registering the handler so Telethon
    # doesn't try to resolve invalid strings at event dispatch time.
    resolved = None
    # First try explicit CHANNEL_ID + CHANNEL_ACCESS_HASH (recommended for private channels)
    chan_id_raw = os.getenv("CHANNEL_ID")
    chan_hash_raw = os.getenv("CHANNEL_ACCESS_HASH")
    if chan_id_raw and chan_hash_raw:
        try:
            cid = int(chan_id_raw)
            chash = int(chan_hash_raw)
            resolved = InputPeerChannel(channel_id=cid, access_hash=chash)
            logging.info("Using CHANNEL_ID/CHANNEL_ACCESS_HASH -> %s", resolved)
        except Exception as e:
            logging.error("Invalid CHANNEL_ID/CHANNEL_ACCESS_HASH: %s", e)
            return

    # Next, try to parse a CHANNEL environment variable containing either a numeric id,
    # a username, or a compound "access#id" or "id#access" form.
    if not resolved and CHANNEL:
        ch = CHANNEL
        # numeric id
        if isinstance(ch, str) and ch.isdigit():
            try:
                resolved = client.loop.run_until_complete(client.get_entity(int(ch)))
                logging.info("Resolved numeric CHANNEL to entity: %s", resolved)
            except Exception:
                # maybe it's provided as access#id or id#access
                pass

        # try parse a#b form
        if not resolved and isinstance(ch, str) and '#' in ch:
            left, right = ch.split('#', 1)
            tried = False
            # try left as access_hash, right as channel_id
            try:
                cid = int(right)
                chash = int(left)
                resolved = InputPeerChannel(channel_id=cid, access_hash=chash)
                logging.info("Using parsed access_hash#id -> %s", resolved)
                tried = True
            except Exception:
                pass
            # try left as channel_id, right as access_hash
            if not tried:
                try:
                    cid = int(left)
                    chash = int(right)
                    resolved = InputPeerChannel(channel_id=cid, access_hash=chash)
                    logging.info("Using parsed id#access_hash -> %s", resolved)
                except Exception:
                    resolved = None

        # finally, try resolving as username string
        if not resolved:
            try:
                resolved = client.loop.run_until_complete(client.get_entity(ch))
                logging.info("Resolved channel entity: %s", resolved)
            except Exception as e:
                logging.error("Failed to resolve CHANNEL=%r: %s", CHANNEL, e)
                logging.error("Make sure the session has access to the channel and that CHANNEL is a username or numeric id, or set CHANNEL_ID and CHANNEL_ACCESS_HASH.")
                return

    # Register the handler with the resolved entity (or listen to all messages if None)
    if resolved:
        client.add_event_handler(handle_new_message, events.NewMessage(chats=resolved))
    else:
        client.add_event_handler(handle_new_message, events.NewMessage)

    # Run with a reconnect loop and exponential backoff so transient network
    # issues don't leave the bot down permanently.
    backoff = 5
    max_backoff = 300
    while True:
        try:
            logging.info("Starting client (backoff=%s)", backoff)
            client.run_until_disconnected()
            # clean exit (disconnected by user)
            logging.info("Client disconnected cleanly; exiting main loop")
            break
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received; shutting down")
            try:
                client.disconnect()
            finally:
                raise
        except Exception as e:
            logging.exception("Uncaught exception in run loop: %s", e)
            try:
                client.disconnect()
            except Exception:
                pass
            # update health file with error timestamp and backoff
            try:
                with open(HEALTH_FILE, 'w', encoding='utf-8') as hf:
                    hf.write(f"last_error={int(time.time())}\nbackoff={backoff}\n")
            except Exception:
                pass

            logging.info("Reconnecting after %s seconds...", backoff)
            time.sleep(backoff)
            backoff = min(max_backoff, backoff * 2)

if __name__ == "__main__":
    main()