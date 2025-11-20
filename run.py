#!/usr/bin/env python3
"""
Main entry point for the Telegram Signal Bot.

This script serves as the primary entry point for running the bot.
"""
import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import main, list_channels_main


def run_setup_scripts():
    """Run setup scripts to generate configuration files."""
    project_root = Path(__file__).parent
    config_dir = project_root / "config"
    
    print("=" * 60)
    print("Running Setup Scripts")
    print("=" * 60)
    
    # Check if channels.json exists
    channels_file = config_dir / "channels.json"
    if not channels_file.exists():
        print("\n📋 Generating channels list...")
        print("   Running get_channel_id.py...")
        
        script_path = project_root / "scripts" / "get_channel_id.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=False
        )
        
        if result.returncode != 0:
            print("⚠️  Warning: Failed to generate channels.json")
            print("   You may need to run it manually later.")
        else:
            print("✅ Channels list generated successfully")
    else:
        print("\n✓ channels.json already exists")
    
    # Check if mt5_symbols_details.json exists
    symbols_file = config_dir / "mt5_symbols_details.json"
    if not symbols_file.exists():
        print("\n📊 Generating MT5 symbols details...")
        print("   Running export_symbols_details.py...")
        
        script_path = project_root / "scripts" / "export_symbols_details.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=False
        )
        
        if result.returncode != 0:
            print("⚠️  Warning: Failed to generate mt5_symbols_details.json")
            print("   MT5 may not be running or configured.")
            print("   The bot will use default filling modes.")
        else:
            print("✅ MT5 symbols details generated successfully")
    else:
        print("\n✓ mt5_symbols_details.json already exists")
    
    print("\n" + "=" * 60)
    print("Setup Complete")
    print("=" * 60)
    print()


if __name__ == "__main__":
    if "--list-channels" in sys.argv or "--list" in sys.argv:
        # List available channels and exit
        asyncio.run(list_channels_main())
    elif "--skip-setup" in sys.argv:
        # Skip setup and run directly
        asyncio.run(main())
    else:
        # Run setup scripts first
        run_setup_scripts()
        
        # Then run the bot
        asyncio.run(main())

