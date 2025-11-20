# MT5 Symbol Mapping

## Overview

Different MT5 brokers use different symbol naming conventions. This bot automatically maps standard symbol names (like `XAUUSD`) to your broker's specific format (like `XAUUSD_o`).

## How It Works

When a signal is received with a symbol like `XAUUSD`, the bot will:

1. **Try exact match** - Check if `XAUUSD` exists as-is
2. **Try case-insensitive match** - Check all symbols with different cases
3. **Try prefix match** - Check if any symbol starts with `XAUUSD`
4. **Try common variations**:
   - `XAUUSD_o` (common broker suffix)
   - `XAUUSDm` (mini lots)
   - `XAUUSD.a`, `XAUUSD.b`, `XAUUSD.c` (various suffixes)
   - `#XAUUSD` (stock symbols)
   - `XAUUSDi` (another common suffix)

## Checking Available Symbols

To see all symbols available in your MT5 account:

```bash
python scripts/list_mt5_symbols.py
```

This will:
- List all 331+ symbols available
- Group them by prefix for easier reading
- Test common symbol mappings (XAUUSD, EURUSD, etc.)

## Testing Symbol Mapping

To test that symbol mapping works correctly:

```bash
python scripts/test_mt5_symbols.py
```

This will:
- Test mapping for common trading symbols
- Show the actual MT5 symbol name
- Display current prices
- Confirm the mapping is working

## Common Symbol Mappings

Based on your MT5 broker, here are common mappings:

| Signal Symbol | MT5 Symbol | Description |
|--------------|------------|-------------|
| XAUUSD       | XAUUSD_o   | Gold        |
| XAGUSD       | XAGUSD_o   | Silver      |
| EURUSD       | EURUSD_o   | EUR/USD     |
| GBPUSD       | GBPUSD_o   | GBP/USD     |
| USDJPY       | USDJPY_o   | USD/JPY     |
| BTCUSD       | BTCUSD     | Bitcoin     |

## Troubleshooting

### Symbol Not Found Error

If you get an error like:
```
ValueError: Symbol XAUUSD not found in MT5
```

**Solution**: The bot now automatically handles this! Just make sure:

1. **MT5 is running and logged in**
2. **The symbol is available** in your broker's Market Watch
3. **Check available symbols** using the script above

### Adding Symbols to Market Watch

If a symbol exists but isn't in Market Watch:

1. Right-click in Market Watch window
2. Select "Symbols"
3. Find your symbol (e.g., `XAUUSD_o`)
4. Click "Show"
5. Click "OK"

The bot will automatically enable symbols that are available but not visible.

## Technical Details

### Code Location

Symbol mapping is implemented in:
- `src/infrastructure/trading/backends/mt5_backend.py`
- Methods: `find_symbol()`, `get_available_symbols()`

### Automatic Symbol Resolution

When placing an order, the bot automatically:
1. Calls `find_symbol(order.symbol)`
2. Gets the actual MT5 symbol name
3. Uses that for all subsequent operations

### Logging

Symbol mapping is logged at INFO level:
```
Found symbol with prefix: XAUUSD -> XAUUSD_o
```

If not found, similar symbols are suggested:
```
Symbol 'GOLD' not found. Similar symbols available: XAUUSD_o, XAGUSD_o
```

## Example Usage

```python
from src.core.config import get_config
from src.infrastructure.trading.backends.mt5_backend import MT5Backend

# Initialize
config = get_config()
backend = MT5Backend(config.mt5, config.trading)
backend.initialize()

# Find symbol - automatically maps XAUUSD to XAUUSD_o
actual_symbol = backend.find_symbol("XAUUSD")
print(f"XAUUSD maps to: {actual_symbol}")

# Get price - automatically uses correct symbol
price = backend.get_current_price("XAUUSD")
print(f"Current price: {price}")
```

## Notes

- Symbol mapping is done **automatically** - no manual configuration needed
- The mapping is cached in memory during the session
- If MT5 is restarted, symbols are re-detected on next initialization
- The bot supports 331+ symbols across Forex, Crypto, Commodities, and Stocks
