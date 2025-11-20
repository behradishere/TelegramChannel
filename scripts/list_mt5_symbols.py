"""Script to list all available symbols in MT5."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.infrastructure.trading.backends.mt5_backend import MT5Backend


def main():
    """List all available MT5 symbols."""
    # Load configuration
    config = get_config()
    
    # Initialize MT5 backend
    mt5_backend = MT5Backend(config.mt5, config.trading)
    
    if not mt5_backend.is_available():
        print("❌ MT5 is not available. Install with: pip install MetaTrader5")
        return
    
    print("🔄 Initializing MT5...")
    if not mt5_backend.initialize():
        print("❌ Failed to initialize MT5. Make sure MT5 terminal is running and logged in.")
        return
    
    print("✅ MT5 initialized successfully!\n")
    
    # Get all symbols
    symbols = mt5_backend.get_available_symbols()
    
    if not symbols:
        print("⚠️ No symbols found")
        return
    
    print(f"📊 Found {len(symbols)} symbols:\n")
    print("=" * 60)
    
    # Group symbols by prefix for easier reading
    symbol_dict = {}
    for symbol in symbols:
        prefix = symbol[:3] if len(symbol) >= 3 else symbol
        if prefix not in symbol_dict:
            symbol_dict[prefix] = []
        symbol_dict[prefix].append(symbol)
    
    # Print grouped symbols
    for prefix in sorted(symbol_dict.keys()):
        syms = symbol_dict[prefix]
        print(f"\n{prefix}* symbols ({len(syms)}):")
        for sym in sorted(syms):
            print(f"  - {sym}")
    
    # Test finding specific symbols
    print("\n" + "=" * 60)
    print("\n🔍 Testing symbol search:\n")
    
    test_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "GOLD"]
    for test_sym in test_symbols:
        found = mt5_backend.find_symbol(test_sym)
        if found:
            print(f"✅ {test_sym:10s} -> {found}")
        else:
            print(f"❌ {test_sym:10s} -> Not found")
    
    # Cleanup
    mt5_backend.shutdown()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
