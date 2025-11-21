"""Main bot application orchestrator."""
import asyncio
import json
from pathlib import Path

from src.core.config import get_config
from src.core.logging import setup_logging, get_logger
from src.core.symbol_cache import get_symbol_cache
from src.infrastructure.telegram.client import SignalTelegramClient
from src.services.signal_parser import SignalParser
from src.services.risk_manager import RiskManager
from src.services.order_service import OrderService
from src.services.trading_service import TradingService
from src.services.position_manager import PositionManager


class SignalBot:
    """
    Main bot application that orchestrates all components.

    Follows the dependency injection pattern for better testability.
    """

    def __init__(self):
        """Initialize the signal bot."""
        # Load configuration
        self.config = get_config()

        # Setup logging
        setup_logging(self.config.logging)
        self.logger = get_logger(__name__)

        self.logger.info("=" * 60)
        self.logger.info("Signal Bot Starting...")
        self.logger.info("=" * 60)

        # Load symbol cache for MT5 symbol details
        self._load_symbol_cache()

        # Initialize services
        self.telegram_client = SignalTelegramClient(self.config.telegram)
        self.signal_parser = SignalParser()
        self.risk_manager = RiskManager(self.config.trading)
        self.order_service = OrderService(self.config.trading, self.risk_manager)
        self.trading_service = TradingService(self.config)
        self.position_manager = PositionManager()

        # Register message handler
        self.telegram_client.on_message(self.handle_signal_message)

        self.logger.info("All services initialized successfully")
        self._update_health_status("starting")

    def _load_symbol_cache(self) -> None:
        """Load symbol details cache for trading operations."""
        symbol_cache = get_symbol_cache()
        
        config_file = Path("config/mt5_symbols_details.json")
        if config_file.exists():
            if symbol_cache.load():
                self.logger.info("Symbol cache loaded successfully")
            else:
                self.logger.warning("Failed to load symbol cache, using defaults")
        else:
            self.logger.warning(
                "Symbol details file not found. "
                "Run export_symbols_details.py to generate it."
            )

    async def start(self) -> None:
        """Start the bot."""
        try:
            # Start Telegram client
            await self.telegram_client.start()

            # Get channels to monitor
            channels = self.telegram_client.parse_channels_config()

            if not channels:
                self.logger.error("No channels configured. Please set CHANNEL_USERNAME, CHANNEL_ID, or CHANNELS in .env")
                return

            # Validate channels against generated channels.json if available
            self._validate_channels(channels)

            # Listen to channels
            await self.telegram_client.listen_to_channels(channels)

            # Update health status
            self._update_health_status("running")

            self.logger.info("Bot is now running and monitoring channels...")

            # Run forever
            await self.telegram_client.run_forever()

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self._update_health_status("error")
            raise
        finally:
            await self.shutdown()

    def _validate_channels(self, channels: list) -> None:
        """
        Validate configured channels against generated channels.json.
        
        Args:
            channels: List of channel identifiers
        """
        channels_file = Path("config/channels.json")
        if not channels_file.exists():
            self.logger.warning("channels.json not found. Skipping validation.")
            return
        
        try:
            with open(channels_file, 'r', encoding='utf-8') as f:
                available_channels = json.load(f)
            
            self.logger.info(f"Loaded {len(available_channels)} available channels from channels.json")
            
            # Build lookup for validation
            channel_lookup = {
                str(ch['id']): ch for ch in available_channels
            }
            username_lookup = {
                ch['username']: ch for ch in available_channels 
                if ch.get('username')
            }
            
            # Validate each configured channel
            for channel in channels:
                channel_str = str(channel)
                
                # Check if it's a username
                if isinstance(channel, str) and not channel.isdigit():
                    if channel.replace('@', '') in username_lookup:
                        ch_info = username_lookup[channel.replace('@', '')]
                        self.logger.info(
                            f"✓ Channel validated: {ch_info['name']} (@{ch_info['username']})"
                        )
                    else:
                        self.logger.warning(
                            f"⚠ Channel username '{channel}' not found in channels.json"
                        )
                # Check if it's an ID
                elif str(channel).lstrip('-').isdigit():
                    if channel_str in channel_lookup:
                        ch_info = channel_lookup[channel_str]
                        self.logger.info(
                            f"✓ Channel validated: {ch_info['name']} (ID: {ch_info['id']})"
                        )
                    else:
                        self.logger.warning(
                            f"⚠ Channel ID '{channel}' not found in channels.json"
                        )
                        
        except Exception as e:
            self.logger.warning(f"Failed to validate channels: {e}")

    async def handle_signal_message(self, message_text: str, channel) -> None:
        """
        Handle incoming signal message from Telegram.

        Args:
            message_text: The message text content
            channel: The channel entity the message came from
        """
        try:
            self.logger.info(f"Processing message from {channel.title}...")

            # Parse signal
            signal = self.signal_parser.parse(message_text)

            if not signal.is_valid():
                self.logger.warning("Parsed signal is incomplete or invalid")
                self.logger.debug(f"Signal data: {signal}")
                return

            self.logger.info(
                f"Valid signal detected: {signal.symbol} {signal.side.value} "
                f"@ {signal.get_entry_price()}"
            )

            # Create order from signal
            order = self.order_service.create_order_from_signal(signal)

            if not order:
                self.logger.warning("Failed to create order from signal")
                return

            # Check if we should execute
            if not self.order_service.should_execute_order(order):
                self.logger.info("Order execution skipped (dry run or conditions not met)")
                return

            # Check if backend is available
            if not self.trading_service.is_backend_available():
                self.logger.warning(
                    "Trading backend not available. Order not executed. "
                    f"Backend: {self.config.trading.backend}, "
                    f"Dry Run: {self.config.trading.dry_run}"
                )
                return

            # Execute order
            try:
                result = self.trading_service.execute_order(order)
                self.logger.info(f"Order executed successfully: {result}")

                # Track position if order has multiple TPs
                if order.take_profits and len(order.take_profits) > 1:
                    position_id = str(result.get('order_id') or result.get('deal_id'))
                    actual_entry = result.get('price', order.price)
                    
                    self.position_manager.add_position(
                        position_id=position_id,
                        order=order,
                        actual_entry_price=actual_entry
                    )
                    
                    self.logger.info(
                        f"Position {position_id} tracked with {len(order.take_profits)} TP levels"
                    )
                    
                    # Start monitoring this position
                    asyncio.create_task(self.monitor_position(position_id))

                # Update account info for risk management
                account_info = self.trading_service.get_account_info()
                if account_info:
                    self.risk_manager.update_account_balance(account_info.balance)

            except Exception as e:
                self.logger.error(f"Failed to execute order: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error handling signal message: {e}", exc_info=True)

    async def monitor_position(self, position_id: str) -> None:
        """
        Monitor a position and manage partial closes at TP levels.
        
        Args:
            position_id: Position identifier
        """
        try:
            managed_pos = self.position_manager.get_position(position_id)
            if not managed_pos:
                return
            
            self.logger.info(f"Started monitoring position {position_id}")
            
            # Check price every 5 seconds
            while managed_pos:
                await asyncio.sleep(5)
                
                # Re-fetch in case position was closed
                managed_pos = self.position_manager.get_position(position_id)
                if not managed_pos:
                    self.logger.info(f"Position {position_id} no longer tracked")
                    break
                
                # Get current price
                current_price = self.trading_service.get_current_price(managed_pos.symbol)
                if current_price is None:
                    continue
                
                # Check if any TP levels hit
                actions = self.position_manager.check_tp_hits(position_id, current_price)
                
                for tp_level, tp_price, volume_to_close, new_sl in actions:
                    self.logger.info(
                        f"🎯 TP{tp_level + 1} hit at {tp_price:.5f} for {position_id}"
                    )
                    
                    # Close partial position
                    success = self.trading_service.close_position_partial(
                        position_id, 
                        volume_to_close
                    )
                    
                    if success:
                        self.logger.info(
                            f"✅ Closed {volume_to_close:.2f} lots at TP{tp_level + 1}"
                        )
                        
                        # Update stop loss if specified
                        if new_sl is not None:
                            sl_success = self.trading_service.modify_position_sl(
                                position_id,
                                new_sl
                            )
                            if sl_success:
                                action_desc = "break-even" if tp_level == 0 else f"TP{tp_level}"
                                self.logger.info(
                                    f"✅ Moved SL to {action_desc} ({new_sl:.5f})"
                                )
                        
                        # Update position manager
                        self.position_manager.update_after_partial_close(
                            position_id,
                            tp_level,
                            volume_to_close,
                            new_sl
                        )
                    else:
                        self.logger.error(
                            f"❌ Failed to close {volume_to_close:.2f} lots at TP{tp_level + 1}"
                        )
                
        except Exception as e:
            self.logger.error(f"Error monitoring position {position_id}: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error handling signal message: {e}", exc_info=True)

    async def shutdown(self) -> None:
        """Shutdown the bot gracefully."""
        self.logger.info("Shutting down bot...")

        try:
            # Stop Telegram client
            await self.telegram_client.stop()

            # Shutdown trading service
            self.trading_service.shutdown()

            self._update_health_status("stopped")
            self.logger.info("Bot shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)

    async def list_channels(self) -> None:
        """List all available Telegram dialogs and exit."""
        try:
            await self.telegram_client.start()

            self.logger.info("Fetching dialog list...")

            # Save to config directory
            output_file = Path("config/channels.json")
            await self.telegram_client.list_dialogs(str(output_file))

            self.logger.info(f"Channel list saved to {output_file}")

            await self.telegram_client.stop()

        except Exception as e:
            self.logger.error(f"Error listing channels: {e}", exc_info=True)
            raise

    def _update_health_status(self, status: str) -> None:
        """
        Update health status file.

        Args:
            status: Current status (starting, running, stopped, error)
        """
        try:
            health_file = Path(self.config.health_file)
            health_file.parent.mkdir(parents=True, exist_ok=True)

            import datetime
            timestamp = datetime.datetime.now().isoformat()

            with health_file.open('w') as f:
                f.write(f"{status}|{timestamp}\n")

        except Exception as e:
            self.logger.warning(f"Failed to update health status: {e}")


async def main():
    """Main entry point."""
    bot = SignalBot()
    await bot.start()


async def list_channels_main():
    """Entry point for listing channels."""
    bot = SignalBot()
    await bot.list_channels()


if __name__ == "__main__":
    import sys

    if "--list-channels" in sys.argv:
        asyncio.run(list_channels_main())
    else:
        asyncio.run(main())

