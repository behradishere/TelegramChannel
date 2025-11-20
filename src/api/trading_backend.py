"""Trading backend interface - abstract base for all trading platform integrations."""
from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.models import Order, Position, AccountInfo


class TradingBackend(ABC):
    """
    Abstract base class for trading backend implementations.

    All trading platform integrations must implement this interface.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the trading backend is available and properly configured.

        Returns:
            True if backend is ready to use, False otherwise
        """
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize connection to the trading platform.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Close connection to the trading platform."""
        pass

    @abstractmethod
    def place_order(self, order: Order) -> dict:
        """
        Place an order on the trading platform.

        Args:
            order: Order to execute

        Returns:
            Dictionary with order execution result
        """
        pass

    @abstractmethod
    def get_account_info(self) -> Optional[AccountInfo]:
        """
        Get current account information.

        Returns:
            AccountInfo object or None if unavailable
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of Position objects
        """
        pass

    @abstractmethod
    def close_position(self, position_id: str) -> bool:
        """
        Close a position.

        Args:
            position_id: ID of the position to close

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current price or None if unavailable
        """
        pass

