#!/usr/bin/env python
"""Simple test for new signal format."""

import sys
sys.path.insert(0, '/')

from src.services.signal_parser import SignalParser

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

if __name__ == "__main__":
    parser = SignalParser()
    signal = parser.parse(test_message)

    print("\n" + "="*60)
    print("PARSING RESULTS:")
    print("="*60)
    print(f"Symbol........: {signal.symbol}")
    print(f"Side..........: {signal.side}")
    print(f"Market Price..: {signal.market_price}")
    print(f"Buy Range.....: {signal.buy_range}")
    print(f"Sell Range....: {signal.sell_range}")
    print(f"Take Profits..: {signal.take_profits}")
    print(f"Stop Loss.....: {signal.stop_loss}")
    print(f"Pip Count.....: {signal.pip_count}")
    print(f"Is Valid......: {signal.is_valid()}")
    print("="*60 + "\n")

