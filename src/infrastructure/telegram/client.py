"""Telegram client for receiving and processing signals."""
from typing import List, Callable, Optional
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel

from src.core.config import TelegramConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class SignalTelegramClient:
    """
    Wrapper around Telethon client for signal monitoring.
    """

    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram client.

        Args:
            config: Telegram configuration
        """
        self.config = config
        self.client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash
        )
        self._message_handlers: List[Callable] = []

    async def start(self) -> None:
        """Start Telegram client."""
        await self.client.start()
        logger.info("Telegram client started")

        # Get and log account info
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (ID: {me.id})")

    async def stop(self) -> None:
        """Stop Telegram client."""
        await self.client.disconnect()
        logger.info("Telegram client stopped")

    def on_message(self, handler: Callable) -> None:
        """
        Register a message handler.

        Args:
            handler: Async function to handle new messages
        """
        self._message_handlers.append(handler)

    async def listen_to_channels(self, channel_inputs: List) -> None:
        """
        Start listening to configured channels for new messages.

        Args:
            channel_inputs: List of channel identifiers (username, ID, or InputPeerChannel)
        """
        if not channel_inputs:
            logger.warning("No channels configured for monitoring")
            return

        # Resolve channels
        channels = []
        for channel_input in channel_inputs:
            try:
                channel = await self._resolve_channel(channel_input)
                if channel:
                    channels.append(channel)
                    logger.info(f"Monitoring channel: {channel_input}")
            except Exception as e:
                logger.error(f"Failed to resolve channel {channel_input}: {e}")

        if not channels:
            raise RuntimeError("No valid channels to monitor")

        # Register event handler for new messages
        @self.client.on(events.NewMessage(chats=channels))
        async def handle_new_message(event):
            """Handle incoming messages from monitored channels."""
            try:
                message = event.message
                channel = await event.get_chat()

                logger.info(
                    f"New message from {channel.title} (ID: {channel.id}): "
                    f"{message.message[:100]}"
                )

                # Call registered handlers
                for handler in self._message_handlers:
                    try:
                        await handler(message.message, channel)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

        logger.info(f"Listening to {len(channels)} channel(s) for signals...")

    async def _resolve_channel(self, channel_input) -> Optional[InputPeerChannel]:
        """
        Resolve a channel identifier to InputPeerChannel.

        Args:
            channel_input: Channel username, ID, or InputPeerChannel

        Returns:
            Resolved channel entity
        """
        # If already an entity, return as is
        if isinstance(channel_input, InputPeerChannel):
            return channel_input

        # Try to resolve by username or ID
        try:
            entity = await self.client.get_entity(channel_input)
            return entity
        except Exception as e:
            logger.error(f"Failed to resolve channel {channel_input}: {e}")
            return None

    async def list_dialogs(self, save_to_file: Optional[str] = None) -> List[dict]:
        """
        List all available dialogs (chats, channels, groups).

        Args:
            save_to_file: Optional file path to save results

        Returns:
            List of dialog information dictionaries
        """
        dialogs = []

        async for dialog in self.client.iter_dialogs():
            info = {
                'name': dialog.name,
                'id': dialog.id,
                'username': getattr(dialog.entity, 'username', None),
                'type': type(dialog.entity).__name__
            }

            # Try to get access hash for channels
            if hasattr(dialog.entity, 'access_hash'):
                info['access_hash'] = dialog.entity.access_hash

            dialogs.append(info)

            logger.info(
                f"Dialog: {info['name']} | ID: {info['id']} | "
                f"Username: {info.get('username', 'N/A')} | "
                f"Type: {info['type']}"
            )

        # Save to file if requested
        if save_to_file:
            import json
            from pathlib import Path

            output_path = Path(save_to_file)
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(dialogs, f, indent=2, ensure_ascii=False)

            logger.info(f"Dialog list saved to {save_to_file}")

        return dialogs

    def parse_channels_config(self) -> List:
        """
        Parse channel configuration and return list of channel identifiers.

        Returns:
            List of channel identifiers to monitor
        """
        channels = []

        # Priority 1: Explicit CHANNEL_ID + CHANNEL_ACCESS_HASH
        if self.config.channel_id and self.config.channel_access_hash:
            channels.append(
                InputPeerChannel(
                    self.config.channel_id,
                    self.config.channel_access_hash
                )
            )
            logger.info("Using explicit CHANNEL_ID + CHANNEL_ACCESS_HASH")
            return channels

        # Priority 2: CHANNELS (comma-separated list)
        if self.config.channels:
            for entry in self.config.channels.split(','):
                entry = entry.strip()

                # Try parsing as access_hash#channel_id or channel_id#access_hash
                if '#' in entry:
                    parts = entry.split('#')
                    try:
                        a, b = int(parts[0]), int(parts[1])
                        # Assume larger number is access_hash
                        if a > b:
                            channels.append(InputPeerChannel(b, a))
                        else:
                            channels.append(InputPeerChannel(a, b))
                    except ValueError:
                        logger.warning(f"Invalid channel format: {entry}")
                # Try as numeric channel ID
                elif entry.isdigit() or (entry.startswith('-') and entry[1:].isdigit()):
                    try:
                        channels.append(int(entry))
                    except ValueError:
                        logger.warning(f"Invalid channel ID: {entry}")
                # Otherwise, treat as username
                else:
                    channels.append(entry)

            logger.info(f"Using CHANNELS config with {len(channels)} channel(s)")
            return channels

        # Priority 3: CHANNEL_USERNAME (legacy single channel)
        if self.config.channel_username:
            channels.append(self.config.channel_username)
            logger.info(f"Using CHANNEL_USERNAME: {self.config.channel_username}")
            return channels

        logger.warning("No channels configured")
        return channels

    async def run_forever(self) -> None:
        """Run the client until disconnected."""
        await self.client.run_until_disconnected()

