"""Trading service - manages trading backend and order execution."""
from typing import Optional

from src.api.trading_backend import TradingBackend
from src.infrastructure.trading.backends.ctrader_backend import CTraderBackend
from src.infrastructure.trading.backends.mt5_backend import MT5Backend
from src.domain.models import Order, AccountInfo
from src.core.config import AppConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class TradingService:
    """
    High-level trading service that manages backend selection and order execution.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize trading service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.backend: Optional[TradingBackend] = None
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the appropriate trading backend based on configuration."""
        backend_name = self.config.trading.backend

        if backend_name == "ctrader":
            self.backend = CTraderBackend(
                self.config.ctrader,
                self.config.trading
            )
        elif backend_name == "mt5":
            self.backend = MT5Backend(
                self.config.mt5,
                self.config.trading
            )
        else:
            raise ValueError(f"Unknown trading backend: {backend_name}")

        # Check availability
        if not self.backend.is_available():
            logger.warning(
                f"{backend_name} backend is not properly configured or available"
            )
            if not self.config.trading.dry_run:
                raise RuntimeError(
                    f"{backend_name} backend not available but dry_run is disabled"
                )
        else:
            # Initialize backend
            if self.backend.initialize():
                logger.info(f"{backend_name} backend initialized successfully")
            else:
                logger.error(f"Failed to initialize {backend_name} backend")

    def execute_order(self, order: Order) -> dict:
        """
        Execute an order through the configured trading backend.

        Args:
            order: Order to execute

        Returns:
            Execution result dictionary
        """
        if self.backend is None:
            raise RuntimeError("No trading backend available")

        try:
            logger.info(
                f"Executing order: {order.symbol} {order.side.value} "
                f"{order.volume:.2f} lots @ {order.price}"
            )

            result = self.backend.place_order(order)

            logger.info(f"Order execution result: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to execute order: {e}", exc_info=True)
            raise

    def get_account_info(self) -> Optional[AccountInfo]:
        """
        Get current account information.

        Returns:
            AccountInfo object or None if unavailable
        """
        if self.backend is None:
            logger.warning("No trading backend available")
            return None

        return self.backend.get_account_info()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current price or None if unavailable
        """
        if self.backend is None:
            logger.warning("No trading backend available")
            return None

        return self.backend.get_current_price(symbol)

    def close_position_partial(self, position_id: str, volume: float) -> bool:
        """
        Close part of a position.
        
        Args:
            position_id: Position identifier
            volume: Volume to close
            
        Returns:
            True if successful, False otherwise
        """
        if self.backend is None:
            logger.warning("No trading backend available")
            return False
        
        if hasattr(self.backend, 'close_position_partial'):
            return self.backend.close_position_partial(position_id, volume)
        else:
            logger.warning("Backend does not support partial close")
            return False
    
    def modify_position_sl(self, position_id: str, new_sl: float) -> bool:
        """
        Modify the stop loss of a position.
        
        Args:
            position_id: Position identifier
            new_sl: New stop loss price
            
        Returns:
            True if successful, False otherwise
        """
        if self.backend is None:
            logger.warning("No trading backend available")
            return False
        
        if hasattr(self.backend, 'modify_position_sl'):
            return self.backend.modify_position_sl(position_id, new_sl)
        else:
            logger.warning("Backend does not support SL modification")
            return False

    def is_backend_available(self) -> bool:
        """Check if trading backend is available and ready."""
        return self.backend is not None and self.backend.is_available()

    def shutdown(self) -> None:
        """Shutdown trading backend connection."""
        if self.backend:
            self.backend.shutdown()
            logger.info("Trading backend shut down")

