GetChannelId.py

This small script lists your Telegram dialogs (users, channels, chats) and prints their names, usernames, IDs and access hashes. It also saves the output to `ChannelIds.txt` in the repository root.


### Setup

Required environment variables (use a `.env` file or export them in your shell):

- **API_ID** (integer) - Get from https://my.telegram.org/apps
- **API_HASH** (string) - Get from https://my.telegram.org/apps  
- **SESSION_NAME** (optional, defaults to `signals_session`)

Example `.env`:

```env
API_ID=123456
API_HASH=your_api_hash_here
SESSION_NAME=signals_session
```

### Usage

Run the dialog lister:

```bash
python GetChannelId.py
```

Look for your channel by name and copy the `ID` and `Access Hash` fields. Put them in `CHANNEL_ID` and `CHANNEL_ACCESS_HASH` respectively, or add an `access_hash#id` entry to `CHANNELS`.

---

## Channel Configuration

The bot supports multiple ways to configure which channels to monitor:

### Method 1: Single Public Channel

Use the channel username (without @):

```env
CHANNEL_USERNAME=mychannel
```

### Method 2: Single Private Channel  

Use channel ID and access hash (obtain from GetChannelId.py):

```env
CHANNEL_ID=1144215308
CHANNEL_ACCESS_HASH=7450773130669315489
```

### Method 3: Multiple Channels

Comma-separated list supporting mixed formats:

```env
# Public usernames, numeric IDs, or access_hash#id format
CHANNELS=publicChannel,1144215308,7450773130669315489#1144215308
```

### Priority Order

The bot checks configuration in this order:

1. `CHANNEL_ID` + `CHANNEL_ACCESS_HASH` (single explicit channel — highest priority)
2. `CHANNELS` (comma-separated list with mixed formats)
3. `CHANNEL_USERNAME` (legacy single-channel fallback)

---

## Trading Backend Configuration

Choose your trading platform with the `TRADING_BACKEND` environment variable:

### cTrader (Default)

Uses the cTrader REST API:

```env
TRADING_BACKEND=ctrader
BROKER_REST_URL=https://api.spotware.com/v1/trading
CTRADER_TOKEN=your_oauth_token
```

### MetaTrader5

Uses the MetaTrader5 Python API (requires MT5 terminal, usually Windows only):

```env
TRADING_BACKEND=mt5
```

⚠️ **Note**: MT5 backend requires the MetaTrader5 Python package and a running MT5 terminal. On macOS, this may not be available—use cTrader instead or run on Windows.

---

## Risk Management

Configure position sizing and risk parameters:

```env
# Account settings
ACCOUNT_BALANCE=10000.0
RISK_PERCENT=1.0

# Volume constraints
DEFAULT_VOLUME=0.01
MIN_VOLUME=0.01
MAX_VOLUME=1.0

# Symbol settings
SYMBOL_XAU=XAUUSD
PIP_SIZE=0.01
```

The bot will automatically calculate position sizes based on:
- Account balance
- Risk percentage
- Stop loss distance
- Min/max volume constraints

---

## Signal Format

The bot can parse various signal formats. Example:

```
XAUUSD ( اسکلپ )

Market price : 4112

Buy  now : 4112 - 4107

Tp1 : 4120
Tp2 : 4128
Tp3 : 4146
Tp4 : open

Sl : 4101.50        ( 80 pip )
```

### Supported Features

- ✅ Multiple symbols: XAUUSD, GOLD, XAU, EURUSD, GBPUSD, USDJPY, BTCUSD, ETHUSD
- ✅ Persian/Arabic digit conversion (۰۱۲۳۴۵۶۷۸۹)
- ✅ Persian keywords (اسکلپ, خرید, فروش)
- ✅ Buy and Sell signals
- ✅ Buy/Sell ranges
- ✅ Up to 4 take profit levels
- ✅ Stop loss (SL, SI, Sl variations)
- ✅ Pip count extraction

---

## Development

### Project Structure

```
TelegramChannel/
├── main.py              # Main bot entry point
├── signal_bot.py        # Legacy signal bot
├── signal_parser.py     # Signal parsing logic
├── order_manager.py     # Order execution & backend management
├── risk_manager.py      # Position sizing & risk management
├── config.py            # Centralized configuration
├── GetChannelId.py      # Channel ID utility
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment configuration
├── .gitignore          # Git ignore rules
└── tests/              # Test suite
    ├── test_signal_parser.py
    ├── test_signal_parser_extended.py
    └── test_risk_manager.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_signal_parser.py

# Run with verbose output
pytest -v
```

### Testing in Dry Run Mode

Always test with `DRY_RUN=true` first:

```env
DRY_RUN=true
```

This will parse signals and prepare orders without sending them to your broker.

---

## Logging & Monitoring

### Log Files

- **bot.log**: Main application log (rotating, max 5MB, 3 backups)
- **health.txt**: Health check file updated on each successful message

### Log Configuration

```env
LOG_FILE=bot.log
LOG_LEVEL=INFO
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=3
```

### Health Monitoring

The bot writes to `health.txt` after each processed message:

```
last_message=1700000000
symbol=XAUUSD
```

Use this for monitoring/alerting in production.

---

## Advanced Usage

### List Configured Channels

```bash
python main.py --list-channels
```

### Custom Trading Logic

Extend `order_manager.py` to implement custom trading logic:

```python
def decide_order(parsed: dict) -> dict:
    # Your custom logic here
    # Modify volume, add filters, etc.
    pass
```

### Custom Signal Formats

Extend `signal_parser.py` to support additional signal formats:

```python
def parse_signal(text: str) -> Dict[str, any]:
    # Add custom regex patterns
    # Support new keywords
    pass
```

---

## Safety & Best Practices

⚠️ **Important Security Notes**:

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use separate Telegram account** - Don't risk your personal account
3. **Start with DRY_RUN=true** - Test thoroughly before live trading
4. **Monitor logs** - Watch for errors and unexpected behavior
5. **Set reasonable limits** - Configure MAX_VOLUME and RISK_PERCENT conservatively
6. **Test with small amounts** - When going live, start with minimal position sizes

### Telegram ToS Compliance

Remember: This uses your **personal Telegram account**. Violations of Telegram's Terms of Service may result in an account ban. Best practices:

- Keep API request rates reasonable
- Don't spam channels or users  
- Only monitor channels you have legitimate access to
- Consider using a dedicated account for bot operations

---

## Troubleshooting

### Common Issues

**Q: "MetaTrader5 package is not available"**  
A: Install MetaTrader5 (`pip install MetaTrader5`) or switch to cTrader backend.

**Q: "Failed to resolve channel"**  
A: Run `GetChannelId.py` to get the correct channel ID and access hash. Make sure your session has access to the channel.

**Q: Bot stops after network error**  
A: The bot implements automatic reconnection with exponential backoff. Check logs for details.

**Q: Orders not being placed**  
A: Ensure `DRY_RUN=false` and broker credentials are configured correctly.

---

## License

[Add your license here]

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## Support

For issues and questions:
- Check the logs in `bot.log`
- Review the troubleshooting section
- Open an issue on GitHub

---

## Disclaimer

This software is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this software. Always test thoroughly and understand the risks of automated trading.
