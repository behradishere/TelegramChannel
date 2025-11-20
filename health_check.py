#!/usr/bin/env python3
"""Health check script for monitoring bot status."""
import os
import sys
import time
from pathlib import Path


def main():
    """Check bot health status and exit with appropriate code."""
    health_file = Path("health.txt")

    if not health_file.exists():
        print("❌ Health file not found. Bot may not be running.")
        sys.exit(1)

    try:
        content = health_file.read_text().strip()
        lines = dict(line.split('=', 1) for line in content.split('\n') if '=' in line)

        last_message = int(lines.get('last_message', 0))
        last_error = int(lines.get('last_error', 0))
        symbol = lines.get('symbol', 'unknown')
        backoff = int(lines.get('backoff', 0))

        current_time = int(time.time())
        time_since_message = current_time - last_message if last_message else None
        time_since_error = current_time - last_error if last_error else None

        print("🏥 Bot Health Status")
        print("=" * 40)

        if last_message:
            print(f"✅ Last message: {time_since_message}s ago")
            print(f"   Symbol: {symbol}")
        else:
            print("⚠️  No messages processed yet")

        if last_error:
            print(f"⚠️  Last error: {time_since_error}s ago")
            print(f"   Backoff: {backoff}s")

            if time_since_error < 300:  # Less than 5 minutes
                print("❌ Recent errors detected!")
                sys.exit(2)

        # Check if bot seems stale (no messages in 1 hour)
        if time_since_message and time_since_message > 3600:
            print("⚠️  No messages in over 1 hour - bot may be stuck")
            sys.exit(1)

        print("✅ Bot appears healthy")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Error reading health file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

