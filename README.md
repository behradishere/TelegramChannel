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

Channel configuration (private channels)
--------------------------------------
If the channel is private or the username can't be resolved, prefer using the numeric
channel id and its access hash. You can obtain both by running `GetChannelId.py`.

Example `.env` entries:

CHANNEL_ID=1144215308
CHANNEL_ACCESS_HASH=7450773130669315489

Alternatively you can still set `CHANNEL_USERNAME` to a public username (without the @).
The client now supports three ways (priority order):
1. `CHANNEL_ID` + `CHANNEL_ACCESS_HASH` (recommended for private channels)
2. `CHANNEL_USERNAME` as a numeric id (e.g. `1144215308`) or username (e.g. `mychannel`)
3. `CHANNEL_USERNAME` in `access_hash#id` or `id#access_hash` format (not recommended — prefer explicit env vars)

How to get the id & access hash
------------------------------
Run the dialog lister we included:

```bash
python3 GetChannelId.py
```

Look for your channel by name and copy the `ID` and `Access Hash` fields. Put them in
`CHANNEL_ID` and `CHANNEL_ACCESS_HASH` respectively.

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
