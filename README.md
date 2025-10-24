GetChannelId.py

This small script lists your Telegram dialogs (users, channels, chats) and prints their names, usernames, IDs and access hashes. It also saves the output to `ChannelIds.txt` in the repository root.

Required environment variables (use a `.env` file or export them in your shell):

- API_ID (integer)
- API_HASH (string)
- SESSION_NAME (optional, defaults to `signals_session`)

Example `.env`:

API_ID=123456
API_HASH=your_api_hash_here
SESSION_NAME=signals_session

Channel configuration (private channels) and multi-channel support
----------------------------------------------------------------
If the channel is private or the username can't be resolved, prefer using the numeric
channel id and its access hash. You can obtain both by running `GetChannelId.py`.

Example `.env` entries (single private channel):

CHANNEL_ID=1144215308
CHANNEL_ACCESS_HASH=7450773130669315489

Multi-channel examples (configure multiple channels):

# Using public usernames (without the @):
CHANNELS=channelA,channelB,my_public_channel

# Using numeric IDs:
CHANNELS=1144215308,2237445566

# Mixed: public + numeric + private (access_hash#id)
CHANNELS=publicChannel,1144215308,3284937556#1144215308

Priority and formats supported by the app (checked in order):
1. `CHANNEL_ID` + `CHANNEL_ACCESS_HASH` (single explicit channel — highest priority)
2. `CHANNELS` — comma-separated list; each entry may be:
	- a username (e.g. `mychannel`)
	- a numeric id (e.g. `1144215308`)
	- `access_hash#channel_id` or `channel_id#access_hash` for private channels
3. `CHANNEL_USERNAME` (legacy single-channel fallback)

How to get the id & access hash
------------------------------
Run the dialog lister we included:

```bash
python3 GetChannelId.py
```

Look for your channel by name and copy the `ID` and `Access Hash` fields. Put them in
`CHANNEL_ID` and `CHANNEL_ACCESS_HASH` respectively, or add an `access_hash#id` entry to `CHANNELS`.

Trading backend selection
-------------------------
You can choose which trading backend to use with the `TRADING_BACKEND` env var. Supported values:

- `ctrader` (default) — uses the cTrader REST API configured with `BROKER_REST_URL` and `CTRADER_TOKEN`.
- `mt5` — uses the MetaTrader5 Python API. This requires the `MetaTrader5` Python package and a running MT5 terminal (usually Windows).

Example:

```
TRADING_BACKEND=ctrader
# or
TRADING_BACKEND=mt5
```

If you set `TRADING_BACKEND=mt5` on macOS, the MT5 package/terminal may not be available — in that case use `ctrader` or run the code on a Windows machine with MT5 installed.

Install dependencies (in a Python venv):

python -m pip install -r requirements.txt

Run:

python3 GetChannelId.py

The script will print dialogs and create/overwrite `ChannelIds.txt` with the same content (UTF-8).
