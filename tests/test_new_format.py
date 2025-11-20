"""Test the new signal format parsing."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.signal_parser import SignalParser

# Test message from the user's logs
test_message = """⚫️ XAUUSD    BUY
——————————————
🔘 Entry 🟰4057.749
—————————————— 
☑️ ( RR 0.8 —TP1 )🟰4069.117
☑️ ( RR 1 — TP2 )🟰4071.959
☑️ ( RR 1.3 — TP3 )🟰4076.222
——————————————
✖️SL 4043.540
————————————
🟡 توجه : 
رعایت اصول مدیریت سرمایه در بقا و موفقیت تریدر الزامی است 
👁️‍🗨️صرفا پیشنهاد
————————————"""

parser = SignalParser()
signal = parser.parse(test_message)

print("=" * 60, flush=True)
print("PARSED SIGNAL:", flush=True)
print("=" * 60, flush=True)
print(f"Symbol: {signal.symbol}", flush=True)
print(f"Side: {signal.side}", flush=True)
print(f"Market Price: {signal.market_price}", flush=True)
print(f"Buy Range: {signal.buy_range}", flush=True)
print(f"Sell Range: {signal.sell_range}", flush=True)
print(f"Take Profits: {signal.take_profits}", flush=True)
print(f"Stop Loss: {signal.stop_loss}", flush=True)
print(f"Pip Count: {signal.pip_count}", flush=True)
print(f"Is Valid: {signal.is_valid()}", flush=True)
print("=" * 60, flush=True)

