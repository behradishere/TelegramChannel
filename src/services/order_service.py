"""Order management service - converts signals to orders and manages execution."""
from typing import Optional
from decimal import Decimal

from src.domain.models import Signal, Order, TradeSide, OrderType
from src.services.risk_manager import RiskManager
from src.core.config import TradingConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


class OrderService:
    """
    Service for converting signals to executable orders and managing order lifecycle.
    """

    def __init__(self, config: TradingConfig, risk_manager: RiskManager):
        """
        Initialize order service.

        Args:
            config: Trading configuration
            risk_manager: Risk manager for position sizing
        """
        self.config = config
        self.risk_manager = risk_manager

    def create_order_from_signal(self, signal: Signal) -> Optional[Order]:
        """
        Convert a signal into an executable order.

        Args:
            signal: Parsed trading signal

        Returns:
            Order object ready for execution, or None if signal is invalid
        """
        if not signal.is_valid():
            logger.warning("Cannot create order from invalid signal")
            return None

        # Determine order type and price
        order_type, price = self._determine_order_type_and_price(signal)

        # Calculate position size
        entry_price_float = float(price) if price else None
        stop_loss_float = float(signal.stop_loss) if signal.stop_loss else None

        volume = self.risk_manager.calculate_position_size(
            entry_price=entry_price_float,
            stop_loss=stop_loss_float,
            pip_value=self.config.pip_size
        )

        # Extract take profit levels
        take_profits = [
            float(tp) for tp in signal.take_profits if tp is not None
        ]

        # Create order
        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            order_type=order_type,
            volume=volume,
            price=entry_price_float,
            stop_loss=stop_loss_float,
            take_profits=take_profits,
            metadata={
                'signal_timestamp': signal.timestamp.isoformat(),
                'pip_count': signal.pip_count,
                'raw_message': signal.raw_message[:100]  # First 100 chars
            }
        )

        # Validate order
        is_valid, error = self.risk_manager.validate_order(order)
        if not is_valid:
            logger.error(f"Order validation failed: {error}")
            return None

        logger.info(
            f"Created order: {order.symbol} {order.side.value} "
            f"{order.volume:.2f} lots @ {order.price:.2f}"
        )

        return order

    def _determine_order_type_and_price(
        self,
        signal: Signal
    ) -> tuple[OrderType, Optional[Decimal]]:
        """
        Determine order type and price based on signal data.

        Args:
            signal: Trading signal

        Returns:
            Tuple of (order_type, price)
        """
        market_price = signal.market_price

        # Get the appropriate range based on trade side
        if signal.side == TradeSide.BUY:
            trade_range = signal.buy_range
        elif signal.side == TradeSide.SELL:
            trade_range = signal.sell_range
        else:
            trade_range = None

        # If we have a range
        if trade_range:
            low, high = trade_range

            # If market price is within range, execute at market
            if market_price and low <= market_price <= high:
                return OrderType.MARKET, market_price

            # Otherwise, use limit order at midpoint of range
            midpoint = (low + high) / 2
            return OrderType.LIMIT, midpoint

        # If we only have market price, execute at market
        if market_price:
            return OrderType.MARKET, market_price

        # Fallback: get entry price from signal
        entry_price = signal.get_entry_price()
        if entry_price:
            return OrderType.LIMIT, entry_price

        # Last resort
        logger.warning("Could not determine entry price, defaulting to market order")
        return OrderType.MARKET, None

    def should_execute_order(self, order: Order) -> bool:
        """
        Determine if an order should be executed based on current conditions.

        Args:
            order: Order to evaluate

        Returns:
            True if order should be executed, False otherwise
        """
        # In dry run mode, log but don't actually execute
        if self.config.dry_run:
            logger.info(f"[DRY RUN] Would execute order: {order.to_dict()}")
            return False

        # Additional checks could be added here:
        # - Market hours
        # - Current market conditions
        # - Maximum daily trades
        # - Existing positions in the same symbol

        return True

    def enrich_order_with_calculated_levels(self, order: Order) -> Order:
        """
        Enrich order with calculated SL/TP levels if missing.

        Args:
            order: Order to enrich

        Returns:
            Enriched order
        """
        if not order.price:
            return order

        # If no stop loss, suggest one (e.g., 1% away)
        if not order.stop_loss:
            sl_distance = order.price * 0.01  # 1% stop loss
            if order.side == TradeSide.BUY:
                order.stop_loss = order.price - sl_distance
            else:
                order.stop_loss = order.price + sl_distance

            logger.info(f"Auto-calculated stop loss: {order.stop_loss:.2f}")

        # If no take profits, suggest based on risk-reward ratios
        if not order.take_profits and order.stop_loss:
            order.take_profits = self.risk_manager.suggest_take_profit_levels(
                entry_price=order.price,
                stop_loss=order.stop_loss,
                side=order.side.value
            )
            logger.info(f"Auto-calculated take profits: {order.take_profits}")

        return order

