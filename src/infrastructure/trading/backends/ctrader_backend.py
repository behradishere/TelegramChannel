"""cTrader trading backend implementation."""
import requests
from typing import Optional, List

from src.api.trading_backend import TradingBackend
from src.domain.models import Order, Position, AccountInfo, TradeSide
from src.core.config import CTraderConfig, TradingConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class CTraderBackend(TradingBackend):
    """cTrader REST API implementation."""

    def __init__(self, config: CTraderConfig, trading_config: TradingConfig):
        """
        Initialize cTrader backend.

        Args:
            config: cTrader specific configuration
            trading_config: General trading configuration
        """
        self.config = config
        self.trading_config = trading_config
        self._initialized = False

    def is_available(self) -> bool:
        """Check if cTrader backend is properly configured."""
        return self.config.is_configured()

    def initialize(self) -> bool:
        """Initialize cTrader connection."""
        if not self.is_available():
            logger.error("cTrader backend not properly configured")
            return False

        # Test connection
        try:
            response = requests.get(
                f"{self.config.rest_url}/account",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            self._initialized = True
            logger.info("cTrader backend initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize cTrader backend: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown cTrader connection."""
        self._initialized = False
        logger.info("cTrader backend connection closed")

    def place_order(self, order: Order) -> dict:
        """
        Place order via cTrader REST API.

        Args:
            order: Order to execute

        Returns:
            Order execution result
        """
        if self.trading_config.dry_run:
            logger.info(f"[DRY RUN] Would place order: {order.to_dict()}")
            return {
                'status': 'dry_run',
                'order': order.to_dict()
            }

        if not self._initialized:
            raise RuntimeError("cTrader backend not initialized")

        try:
            # Prepare order payload for cTrader API
            payload = self._prepare_order_payload(order)

            # Send order
            response = requests.post(
                f"{self.config.rest_url}/orders",
                json=payload,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Order placed successfully: {result}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to place order: {e}")
            raise

    def get_account_info(self) -> Optional[AccountInfo]:
        """Get cTrader account information."""
        if not self._initialized:
            logger.warning("cTrader backend not initialized")
            return None

        try:
            response = requests.get(
                f"{self.config.rest_url}/account",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            return AccountInfo(
                balance=data.get('balance', 0.0),
                equity=data.get('equity', 0.0),
                margin=data.get('margin', 0.0),
                free_margin=data.get('freeMargin', 0.0),
                margin_level=data.get('marginLevel', 0.0),
                currency=data.get('currency', 'USD'),
                leverage=data.get('leverage', 100)
            )

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None

    def get_positions(self) -> List[Position]:
        """Get all open positions from cTrader."""
        if not self._initialized:
            logger.warning("cTrader backend not initialized")
            return []

        try:
            response = requests.get(
                f"{self.config.rest_url}/positions",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            positions = []

            for pos_data in data.get('positions', []):
                position = Position(
                    symbol=pos_data['symbol'],
                    side=TradeSide(pos_data['side'].lower()),
                    volume=pos_data['volume'],
                    entry_price=pos_data['entryPrice'],
                    current_price=pos_data['currentPrice'],
                    stop_loss=pos_data.get('stopLoss'),
                    take_profit=pos_data.get('takeProfit'),
                    position_id=str(pos_data['id']),
                    unrealized_pnl=pos_data.get('unrealizedPnl', 0.0)
                )
                positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def close_position(self, position_id: str) -> bool:
        """Close a position in cTrader."""
        if not self._initialized:
            logger.error("cTrader backend not initialized")
            return False

        try:
            response = requests.delete(
                f"{self.config.rest_url}/positions/{position_id}",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Position {position_id} closed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            return False

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        if not self._initialized:
            logger.warning("cTrader backend not initialized")
            return None

        try:
            response = requests.get(
                f"{self.config.rest_url}/symbols/{symbol}/price",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return data.get('bid', 0.0)  # or 'ask' depending on use case

        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def _get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        return {
            'Authorization': f'Bearer {self.config.token}',
            'Content-Type': 'application/json'
        }

    def _prepare_order_payload(self, order: Order) -> dict:
        """
        Prepare order payload for cTrader API.

        Args:
            order: Order object

        Returns:
            API payload dictionary
        """
        payload = {
            'symbol': order.symbol,
            'side': order.side.value.upper(),
            'type': order.order_type.value.upper(),
            'volume': order.volume,
        }

        if order.price:
            payload['price'] = order.price

        if order.stop_loss:
            payload['stopLoss'] = order.stop_loss

        if order.take_profits:
            # cTrader typically supports one TP, use the first one
            payload['takeProfit'] = order.take_profits[0]

        return payload

