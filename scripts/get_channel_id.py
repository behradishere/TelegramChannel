#!/usr/bin/env python3
"""
Utility script to list all Telegram channels and save their IDs.

This helps users find the channel ID and access hash needed for configuration.
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.telegram.client import SignalTelegramClient
from src.core.config import get_config, TelegramConfig
from src.core.logging import setup_logging


async def main():
    """List all dialogs and save to file."""
    # Setup basic logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    print("=" * 60)
    print("Telegram Channel ID Finder")
    print("=" * 60)
    print()

    try:
        # Get Telegram config
        config = get_config()
        telegram_config = config.telegram

        # Create client
        client = SignalTelegramClient(telegram_config)

        # Start client
        await client.start()

        # List dialogs
        print("\nFetching your Telegram dialogs...")
        output_file = Path("config/channels.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        dialogs = await client.list_dialogs(str(output_file))

        # Print summary
        print("\n" + "=" * 60)
        print(f"Found {len(dialogs)} dialogs")
        print(f"Results saved to: {output_file}")
        print("=" * 60)
        print("\nChannel Configuration Examples:")
        print("-" * 60)

        for dialog in dialogs[:5]:  # Show first 5 as examples
            if dialog['type'] in ['Channel', 'Chat']:
                print(f"\nName: {dialog['name']}")
                print(f"  ID: {dialog['id']}")
                if dialog.get('username'):
                    print(f"  Username: @{dialog['username']}")
                    print(f"  Config (username): CHANNEL_USERNAME={dialog['username']}")
                if dialog.get('access_hash'):
                    print(f"  Access Hash: {dialog['access_hash']}")
                    print(f"  Config (explicit): CHANNEL_ID={dialog['id']}")
                    print(f"                     CHANNEL_ACCESS_HASH={dialog['access_hash']}")

        if len(dialogs) > 5:
            print(f"\n... and {len(dialogs) - 5} more. See {output_file} for full list.")

        # Stop client
        await client.stop()

        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

