"""Script to export all MT5 symbols with their details to JSON."""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.infrastructure.trading.backends.mt5_backend import MT5Backend


def get_filling_mode_name(filling_mode):
    """Convert MT5 filling mode constant to readable name."""
    try:
        import MetaTrader5 as mt5
        filling_modes = {
            mt5.ORDER_FILLING_FOK: "FOK (Fill or Kill)",
            mt5.ORDER_FILLING_IOC: "IOC (Immediate or Cancel)",
            mt5.ORDER_FILLING_RETURN: "RETURN (Return)",
            mt5.ORDER_FILLING_BOC: "BOC (Book or Cancel)"
        }
        return filling_modes.get(filling_mode, f"Unknown ({filling_mode})")
    except:
        return f"Unknown ({filling_mode})"


def get_symbol_details(mt5_backend):
    """Get detailed information for all MT5 symbols."""
    import MetaTrader5 as mt5
    
    symbols = mt5.symbols_get()
    if symbols is None:
        print("❌ Failed to get symbols from MT5")
        return None
    
    symbols_data = []
    
    for symbol in symbols:
        # Get detailed symbol information
        # Use getattr with defaults to handle attributes that may not exist
        symbol_dict = {
            "name": symbol.name,
            "description": getattr(symbol, 'description', ''),
            "path": symbol.path,
            "currency_base": symbol.currency_base,
            "currency_profit": symbol.currency_profit,
            "currency_margin": symbol.currency_margin,
            "digits": symbol.digits,
            "point": symbol.point,
            "trade_contract_size": symbol.trade_contract_size,
            "trade_tick_size": symbol.trade_tick_size,
            "trade_tick_value": symbol.trade_tick_value,
            "trade_tick_value_profit": symbol.trade_tick_value_profit,
            "trade_tick_value_loss": symbol.trade_tick_value_loss,
            "volume_min": symbol.volume_min,
            "volume_max": symbol.volume_max,
            "volume_step": symbol.volume_step,
            "volume_limit": symbol.volume_limit,
            "swap_long": symbol.swap_long,
            "swap_short": symbol.swap_short,
            "margin_initial": symbol.margin_initial,
            "margin_maintenance": symbol.margin_maintenance,
            "session_deals": symbol.session_deals,
            "session_buy_orders": symbol.session_buy_orders,
            "session_sell_orders": symbol.session_sell_orders,
            "session_volume": symbol.session_volume,
            "session_turnover": symbol.session_turnover,
            "session_interest": symbol.session_interest,
            "session_buy_orders_volume": symbol.session_buy_orders_volume,
            "session_sell_orders_volume": symbol.session_sell_orders_volume,
            "session_open": symbol.session_open,
            "session_close": symbol.session_close,
            "session_aw": symbol.session_aw,
            "session_price_settlement": symbol.session_price_settlement,
            "session_price_limit_min": symbol.session_price_limit_min,
            "session_price_limit_max": symbol.session_price_limit_max,
            "margin_hedged": symbol.margin_hedged,
            "price_change": getattr(symbol, 'price_change', 0),
            "price_volatility": getattr(symbol, 'price_volatility', 0),
            "price_theoretical": getattr(symbol, 'price_theoretical', 0),
            "price_greeks_delta": getattr(symbol, 'price_greeks_delta', 0),
            "price_greeks_theta": getattr(symbol, 'price_greeks_theta', 0),
            "price_greeks_gamma": getattr(symbol, 'price_greeks_gamma', 0),
            "price_greeks_vega": getattr(symbol, 'price_greeks_vega', 0),
            "price_greeks_rho": getattr(symbol, 'price_greeks_rho', 0),
            "price_greeks_omega": getattr(symbol, 'price_greeks_omega', 0),
            "price_sensitivity": getattr(symbol, 'price_sensitivity', 0),
            "basis": getattr(symbol, 'basis', ''),
            "category": getattr(symbol, 'category', ''),
            "exchange": getattr(symbol, 'exchange', ''),
            "formula": getattr(symbol, 'formula', ''),
            "isin": getattr(symbol, 'isin', ''),
            "page": getattr(symbol, 'page', ''),
            "spread": symbol.spread,
            "spread_float": getattr(symbol, 'spread_float', False),
            "ticks_bookdepth": getattr(symbol, 'ticks_bookdepth', 0),
            "chart_mode": symbol.chart_mode,
            "trade_mode": symbol.trade_mode,
            "trade_exemode": symbol.trade_exemode,
            "trade_calc_mode": symbol.trade_calc_mode,
            "trade_stops_level": symbol.trade_stops_level,
            "trade_freeze_level": symbol.trade_freeze_level,
            "trade_gtc_mode": getattr(symbol, 'trade_gtc_mode', 0),
            "time": symbol.time,
            "time_msc": getattr(symbol, 'time_msc', 0),
            "visible": symbol.visible,
            "select": symbol.select,
            "custom": symbol.custom,
            "background_color": getattr(symbol, 'background_color', 0),
            
            # Filling mode information
            "filling_mode": symbol.filling_mode,
            "filling_mode_name": get_filling_mode_name(symbol.filling_mode),
            
            # Additional trade execution modes
            "order_mode": getattr(symbol, 'order_mode', 0),
            "order_gtc_mode": getattr(symbol, 'order_gtc_mode', 0),
            "option_mode": getattr(symbol, 'option_mode', 0),
            "option_right": getattr(symbol, 'option_right', 0),
            
            # Expiration modes
            "expiration_mode": symbol.expiration_mode,
        }
        
        symbols_data.append(symbol_dict)
    
    return symbols_data


def main():
    """Export all MT5 symbols with details to JSON."""
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
    
    print("📊 Fetching symbol details...")
    symbols_data = get_symbol_details(mt5_backend)
    
    if not symbols_data:
        print("⚠️ No symbols found")
        mt5_backend.shutdown()
        return
    
    # Prepare output
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_symbols": len(symbols_data),
        "symbols": symbols_data
    }
    
    # Save to config folder
    config_dir = project_root / "config"
    config_dir.mkdir(exist_ok=True)
    
    output_file = config_dir / "mt5_symbols_details.json"
    
    print(f"💾 Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully exported {len(symbols_data)} symbols with details!")
    print(f"📁 File saved: {output_file}")
    
    # Print summary statistics
    print("\n📈 Summary:")
    print(f"   Total symbols: {len(symbols_data)}")
    
    # Count by filling mode
    filling_modes = {}
    for symbol in symbols_data:
        mode = symbol['filling_mode_name']
        filling_modes[mode] = filling_modes.get(mode, 0) + 1
    
    print(f"\n   Filling modes:")
    for mode, count in sorted(filling_modes.items()):
        print(f"      {mode}: {count}")
    
    # Count by category
    categories = {}
    for symbol in symbols_data:
        cat = symbol.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    if categories:
        print(f"\n   Top categories:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      {cat}: {count}")
    
    # Shutdown MT5
    mt5_backend.shutdown()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
