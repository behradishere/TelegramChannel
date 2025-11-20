"""Quick test to verify MT5 symbol mapping works correctly."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.infrastructure.trading.backends.mt5_backend import MT5Backend
from src.domain.models import Order, TradeSide, OrderType


def test_symbol_mapping():
    """Test that symbol mapping works for common symbols."""
    print("🧪 Testing MT5 Symbol Mapping\n")
    
    # Load configuration
    config = get_config()
    
    # Initialize MT5 backend
    mt5_backend = MT5Backend(config.mt5, config.trading)
    
    if not mt5_backend.is_available():
        print("❌ MT5 is not available")
        return False
    
    print("🔄 Initializing MT5...")
    if not mt5_backend.initialize():
        print("❌ Failed to initialize MT5")
        return False
    
    print("✅ MT5 initialized\n")
    
    # Test common symbols
    test_symbols = {
        "XAUUSD": "Gold",
        "EURUSD": "Euro/USD",
        "GBPUSD": "Pound/USD",
        "USDJPY": "USD/Yen",
        "BTCUSD": "Bitcoin",
        "XAGUSD": "Silver",
    }
    
    print("=" * 60)
    print("Testing Symbol Lookups:")
    print("=" * 60 + "\n")
    
    success_count = 0
    total_count = len(test_symbols)
    
    for symbol, name in test_symbols.items():
        found = mt5_backend.find_symbol(symbol)
        if found:
            print(f"✅ {symbol:10s} ({name:15s}) -> {found}")
            success_count += 1
            
            # Try to get current price
            price = mt5_backend.get_current_price(symbol)
            if price:
                print(f"   💰 Current price: {price}")
        else:
            print(f"❌ {symbol:10s} ({name:15s}) -> Not found")
        print()
    
    # Summary
    print("=" * 60)
    print(f"\n📊 Results: {success_count}/{total_count} symbols found")
    
    if success_count == total_count:
        print("✅ All symbols mapped successfully!")
    elif success_count > 0:
        print(f"⚠️  {total_count - success_count} symbols not available in your MT5")
    else:
        print("❌ No symbols found - check your MT5 setup")
    
    # Cleanup
    mt5_backend.shutdown()
    print("\n✅ Test complete!")
    
    return success_count > 0


if __name__ == "__main__":
    success = test_symbol_mapping()
    sys.exit(0 if success else 1)
