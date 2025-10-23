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

Install dependencies (in a Python venv):

python -m pip install -r requirements.txt

Run:

python3 GetChannelId.py

The script will print dialogs and create/overwrite `ChannelIds.txt` with the same content (UTF-8).
