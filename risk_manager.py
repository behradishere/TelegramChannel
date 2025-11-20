# risk_manager.py
"""Risk management and position sizing for trading signals."""
import logging
from decimal import Decimal
from typing import Optional, Dict


class RiskManager:
    """Calculate position sizes based on risk parameters."""

    def __init__(self,
                 account_balance: float = 10000.0,
                 risk_percent: float = 1.0,
                 min_volume: float = 0.01,
                 max_volume: float = 1.0,
                 default_volume: float = 0.01):
        """
        Initialize risk manager.

        Args:
            account_balance: Account balance in base currency
            risk_percent: Percentage of account to risk per trade
            min_volume: Minimum position size
            max_volume: Maximum position size
            default_volume: Default volume when risk calculation not possible
        """
        self.account_balance = account_balance
        self.risk_percent = risk_percent
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.default_volume = default_volume

    def calculate_position_size(self,
                                entry_price: Optional[float],
                                stop_loss: Optional[float],
                                pip_value: float = 0.01) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            pip_value: Value of one pip

        Returns:
            Position size in lots
        """
        if not entry_price or not stop_loss or entry_price == stop_loss:
            logging.warning("Cannot calculate position size: missing/invalid prices. Using default volume.")
            return self.default_volume

        # Calculate risk amount in account currency
        risk_amount = self.account_balance * (self.risk_percent / 100)

        # Calculate stop loss distance in pips
        sl_distance = abs(entry_price - stop_loss)

        # Prevent division by zero
        if sl_distance < 0.0001:
            logging.warning("Stop loss too close to entry. Using default volume.")
            return self.default_volume

        # Calculate position size
        # For simplified calculation: volume = risk_amount / (sl_distance / pip_value)
        pip_distance = sl_distance / pip_value

        # Assuming 1 lot = $10/pip for gold (simplified)
        # Adjust this multiplier based on your broker's contract specifications
        value_per_pip = 10.0  # This should be configurable per symbol

        position_size = risk_amount / (pip_distance * value_per_pip)

        # Apply min/max constraints
        position_size = max(self.min_volume, min(self.max_volume, position_size))

        # Round to 2 decimal places (standard lot precision)
        position_size = round(position_size, 2)

        logging.info(f"Position size calculated: {position_size} lots "
                    f"(Risk: ${risk_amount:.2f}, SL distance: {pip_distance:.1f} pips)")

        return position_size

    def validate_trade(self, order: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate if trade meets risk management criteria.

        Args:
            order: Order dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        volume = order.get('volume', 0)

        if volume < self.min_volume:
            return False, f"Volume {volume} below minimum {self.min_volume}"

        if volume > self.max_volume:
            return False, f"Volume {volume} exceeds maximum {self.max_volume}"

        price = order.get('price')
        sl = order.get('sl')

        if price and sl:
            sl_distance = abs(price - sl)
            if sl_distance < 0.01:  # Too tight stop loss
                return False, f"Stop loss too tight: {sl_distance}"

        return True, None

