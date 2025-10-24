# main.py
import logging
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel
import time
import argparse
import sys
from logging.handlers import RotatingFileHandler
from signal_parser import parse_signal
from order_manager import decide_order, place_order, backend_available, TRADING_BACKEND

# Validate API credentials
# Validate API credentials
load_dotenv()
# Validate API credentials
SESSION_NAME = os.getenv("SESSION_NAME", "signals_session")
api_id_raw = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
# Single-channel fallback for backward-compatibility
CHANNEL = os.getenv("CHANNEL_USERNAME")
# New: support multiple channels via comma-separated env var. Each entry can be:
# - a public username (without @)
# - a numeric channel id
# - access_hash#channel_id or channel_id#access_hash
CHANNELS = os.getenv("CHANNELS")

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

# Parse CLI args (simple): --list-channels to resolve and print channels then exit
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--list-channels', action='store_true', help='Resolve and list configured channels then exit')
ARGS, _ = parser.parse_known_args()

async def handle_new_message(event):
    text = event.message.message or ""
    # Build a clearer channel identity for logs
    chat_obj = getattr(event, 'chat', None)
    chat_id = getattr(chat_obj, 'id', None) or getattr(event, 'chat_id', None) or getattr(event.message, 'chat_id', None)
    chat_name = None
    if chat_obj:
        chat_name = getattr(chat_obj, 'title', None) or getattr(chat_obj, 'username', None)
    # Fallback to configured CHANNEL or CHANNELS for clarity
    configured = CHANNELS or CHANNEL or 'unknown'
    logging.info("📨 New message from configured=%s | channel_id=%s | name=%s : %s", configured, chat_id, chat_name, text[:120].replace("\n", " "))
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

    # Resolve one or more channels to entities before registering the handler.
    # We support:
    # - CHANNELS (comma-separated list)
    # - fallback to single CHANNEL
    to_resolve = []
    if CHANNELS:
        to_resolve = [c.strip() for c in CHANNELS.split(',') if c.strip()]
    elif CHANNEL:
        to_resolve = [CHANNEL]

    resolved_entities = []
    failed_entries = []
    # If explicit CHANNEL_ID + CHANNEL_ACCESS_HASH given, use that first (single)
    chan_id_raw = os.getenv("CHANNEL_ID")
    chan_hash_raw = os.getenv("CHANNEL_ACCESS_HASH")
    if chan_id_raw and chan_hash_raw:
        try:
            cid = int(chan_id_raw)
            chash = int(chan_hash_raw)
            resolved_entities.append(InputPeerChannel(channel_id=cid, access_hash=chash))
            logging.info("Using CHANNEL_ID/CHANNEL_ACCESS_HASH -> %s", resolved_entities[-1])
        except Exception as e:
            logging.error("Invalid CHANNEL_ID/CHANNEL_ACCESS_HASH: %s", e)
            return

    # Resolve each requested channel entry
    for ch in to_resolve:
        if not ch:
            continue
        # numeric id
        resolved = None
        if ch.isdigit():
            try:
                resolved = client.loop.run_until_complete(client.get_entity(int(ch)))
                logging.info("Resolved numeric CHANNEL to entity: %s", resolved)
            except Exception:
                # maybe it's provided as access#id or id#access; we'll try below
                resolved = None

        # try parse a#b form (access#id or id#access)
        if not resolved and '#' in ch:
            left, right = ch.split('#', 1)
            tried = False
            try:
                cid = int(right)
                chash = int(left)
                resolved = InputPeerChannel(channel_id=cid, access_hash=chash)
                logging.info("Using parsed access_hash#id -> %s", resolved)
                tried = True
            except Exception:
                pass
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
                logging.error("Failed to resolve channel entry %r: %s", ch, e)
                logging.error("Make sure the session has access to the channel or provide CHANNEL_ID and CHANNEL_ACCESS_HASH.")
                # skip this entry but continue resolving others
                resolved = None

        if resolved:
            resolved_entities.append(resolved)
        else:
            failed_entries.append(ch)

    # If user configured explicit channels (via CHANNELS or CHANNEL), treat failures as fatal
    if (to_resolve) and failed_entries:
        logging.error("Failed to resolve the following configured channel entries: %s", failed_entries)
        logging.error("Make sure the session has access to these channels or provide their CHANNEL_ID and CHANNEL_ACCESS_HASH.")
        # strict failure: exit with non-zero status
        sys.exit(2)

    if not resolved_entities:
        logging.warning("No channel entities resolved. The handler will listen to all incoming messages.")

    # Register the handler with the resolved entities (or listen to all messages if none)
    if resolved_entities:
        client.add_event_handler(handle_new_message, events.NewMessage(chats=resolved_entities))
    else:
        client.add_event_handler(handle_new_message, events.NewMessage)

    # If user requested to list resolved channels, print and exit now
    if ARGS.list_channels:
        print("Resolved channels:")
        for ent in resolved_entities:
            # Some entities are InputPeerChannel (no easy title) — print repr and ids
            try:
                cid = getattr(ent, 'channel_id', None) or getattr(ent, 'id', None)
            except Exception:
                cid = None
            print(f" - {ent!r} (id={cid})")
        # disconnect and exit
        try:
            client.disconnect()
        except Exception:
            pass
        sys.exit(0)

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