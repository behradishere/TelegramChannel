#!/usr/bin/env python3
"""
Main entry point for the Telegram Signal Bot.

This script serves as the primary entry point for running the bot.
"""
import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import main, list_channels_main

if __name__ == "__main__":
    if "--list-channels" in sys.argv or "--list" in sys.argv:
        # List available channels and exit
        asyncio.run(list_channels_main())
    else:
        # Run the bot
        asyncio.run(main())

