"""Risk management service for position sizing and trade validation."""
from typing import Optional, Tuple

from src.domain.models import Order, Signal
from src.core.config import TradingConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class RiskManager:
    """
    Manages risk and calculates position sizes based on account parameters.

    Follows proper risk management principles to protect capital.
    """

    def __init__(self, config: TradingConfig):
        """
        Initialize risk manager.

        Args:
            config: Trading configuration with risk parameters
        """
        self.config = config
        self.account_balance = config.account_balance
        self.risk_percent = config.risk_percent
        self.min_volume = config.min_volume
        self.max_volume = config.max_volume
        self.default_volume = config.default_volume

    def calculate_position_size(
        self,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        pip_value: float = 0.01
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            pip_value: Value of one pip for the symbol

        Returns:
            Position size in lots
        """
        if not entry_price or not stop_loss or entry_price == stop_loss:
            logger.warning(
                "Cannot calculate position size: missing or invalid prices. "
                f"Using default volume: {self.default_volume}"
            )
            return self.default_volume

        # Calculate risk amount in account currency
        risk_amount = self.account_balance * (self.risk_percent / 100)

        # Calculate stop loss distance
        sl_distance = abs(entry_price - stop_loss)

        # Prevent division by zero
        if sl_distance < 0.0001:
            logger.warning(
                f"Stop loss too close to entry ({sl_distance:.5f}). "
                f"Using default volume: {self.default_volume}"
            )
            return self.default_volume

        # Calculate pip distance
        pip_distance = sl_distance / pip_value

        # Calculate position size
        # For XAUUSD: typically $10/pip per lot (varies by broker)
        # This should be configurable per symbol
        value_per_pip = self._get_pip_value_per_lot(symbol="XAUUSD")

        if value_per_pip <= 0:
            logger.warning("Invalid pip value. Using default volume.")
            return self.default_volume

        # Position size = Risk amount / (Pip distance * Value per pip)
        position_size = risk_amount / (pip_distance * value_per_pip)

        # Apply min/max constraints
        position_size = max(self.min_volume, min(self.max_volume, position_size))

        # Round to 2 decimal places (standard lot precision)
        position_size = round(position_size, 2)

        logger.info(
            f"Position size calculated: {position_size:.2f} lots | "
            f"Risk: ${risk_amount:.2f} | "
            f"SL distance: {pip_distance:.1f} pips | "
            f"Entry: {entry_price:.2f} | SL: {stop_loss:.2f}"
        )

        return position_size

    def validate_order(self, order: Order) -> Tuple[bool, Optional[str]]:
        """
        Validate if order meets risk management criteria.

        Args:
            order: Order to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check volume constraints
        if order.volume < self.min_volume:
            error = f"Volume {order.volume:.2f} below minimum {self.min_volume:.2f}"
            logger.warning(error)
            return False, error

        if order.volume > self.max_volume:
            error = f"Volume {order.volume:.2f} exceeds maximum {self.max_volume:.2f}"
            logger.warning(error)
            return False, error

        # Check if stop loss is set (recommended but not required)
        if not order.stop_loss:
            logger.warning("Order has no stop loss - high risk!")

        # Check if stop loss is reasonable
        if order.price and order.stop_loss:
            sl_distance_percent = abs(order.price - order.stop_loss) / order.price * 100
            if sl_distance_percent > 10:  # More than 10% away
                logger.warning(
                    f"Stop loss is {sl_distance_percent:.1f}% away from entry - "
                    "unusually large risk!"
                )

        logger.info(f"Order validation passed: {order.symbol} {order.side.value}")
        return True, None

    def calculate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> Optional[float]:
        """
        Calculate risk-reward ratio for a trade.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Risk-reward ratio (e.g., 2.0 means 2:1 reward:risk)
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return None

        return reward / risk

    def suggest_take_profit_levels(
        self,
        entry_price: float,
        stop_loss: float,
        side: str,
        ratios: list = None
    ) -> list:
        """
        Suggest take profit levels based on risk-reward ratios.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: Trade side ('buy' or 'sell')
            ratios: List of risk-reward ratios to use (default: [1, 2, 3, 4])

        Returns:
            List of suggested take profit prices
        """
        if ratios is None:
            ratios = [1.0, 2.0, 3.0, 4.0]

        risk = abs(entry_price - stop_loss)
        take_profits = []

        for ratio in ratios:
            reward = risk * ratio

            if side.lower() == 'buy':
                tp = entry_price + reward
            else:  # sell
                tp = entry_price - reward

            take_profits.append(round(tp, 2))

        return take_profits

    def _get_pip_value_per_lot(self, symbol: str) -> float:
        """
        Get pip value per lot for a given symbol.

        This should ideally be fetched from the broker or configured per symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Pip value per lot in account currency
        """
        # Standard values for common symbols
        # These are approximate and should be configured per broker
        pip_values = {
            'XAUUSD': 10.0,   # Gold: $10/pip per lot
            'EURUSD': 10.0,   # EUR/USD: $10/pip per lot
            'GBPUSD': 10.0,   # GBP/USD: $10/pip per lot
            'USDJPY': 9.09,   # USD/JPY: ~$9.09/pip per lot (varies with rate)
        }

        return pip_values.get(symbol, 10.0)

    def update_account_balance(self, new_balance: float) -> None:
        """
        Update account balance for position sizing calculations.

        Args:
            new_balance: New account balance
        """
        old_balance = self.account_balance
        self.account_balance = new_balance
        logger.info(f"Account balance updated: ${old_balance:.2f} -> ${new_balance:.2f}")

