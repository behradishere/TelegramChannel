"""Domain models representing core business entities."""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Tuple
from datetime import datetime


class TradeSide(Enum):
    """Trade direction."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order execution type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Signal:
    """
    Trading signal extracted from Telegram message.

    Represents the raw signal data before being converted to an executable order.
    """
    symbol: Optional[str] = None
    market_price: Optional[Decimal] = None
    buy_range: Optional[Tuple[Decimal, Decimal]] = None
    sell_range: Optional[Tuple[Decimal, Decimal]] = None
    take_profits: List[Optional[Decimal]] = field(default_factory=list)
    stop_loss: Optional[Decimal] = None
    pip_count: Optional[int] = None
    side: Optional[TradeSide] = None
    raw_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate and normalize signal data."""
        # Convert side to enum if string
        if isinstance(self.side, str):
            self.side = TradeSide(self.side.lower())

        # Ensure take_profits is a list
        if not isinstance(self.take_profits, list):
            self.take_profits = [self.take_profits] if self.take_profits else []

    def is_valid(self) -> bool:
        """Check if signal has minimum required information."""
        return (
            self.symbol is not None and
            self.side is not None and
            (self.market_price is not None or
             self.buy_range is not None or
             self.sell_range is not None)
        )

    def get_entry_price(self) -> Optional[Decimal]:
        """Get the entry price for the signal."""
        if self.market_price:
            return self.market_price

        if self.side == TradeSide.BUY and self.buy_range:
            # Use midpoint of buy range
            return (self.buy_range[0] + self.buy_range[1]) / 2

        if self.side == TradeSide.SELL and self.sell_range:
            # Use midpoint of sell range
            return (self.sell_range[0] + self.sell_range[1]) / 2

        return None

    def get_first_take_profit(self) -> Optional[Decimal]:
        """Get the first non-None take profit level."""
        for tp in self.take_profits:
            if tp is not None:
                return tp
        return None


@dataclass
class Order:
    """
    Executable trading order.

    Represents an order ready to be sent to a trading platform.
    """
    symbol: str
    side: TradeSide
    order_type: OrderType
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None
    filled_volume: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize order data."""
        # Convert side to enum if string
        if isinstance(self.side, str):
            self.side = TradeSide(self.side.lower())

        # Convert order_type to enum if string
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type.lower())

        # Convert status to enum if string
        if isinstance(self.status, str):
            self.status = OrderStatus(self.status.lower())

    def to_dict(self) -> dict:
        """Convert order to dictionary for API submission."""
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'type': self.order_type.value,
            'volume': self.volume,
            'price': self.price,
            'sl': self.stop_loss,
            'tps': self.take_profits,
            'order_id': self.order_id,
            'timestamp': self.timestamp.isoformat(),
            **self.metadata
        }


@dataclass
class Position:
    """
    Active trading position.
    """
    symbol: str
    side: TradeSide
    volume: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_id: Optional[str] = None
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def calculate_pnl(self, current_price: Optional[float] = None) -> float:
        """Calculate profit/loss for the position."""
        price = current_price or self.current_price

        if self.side == TradeSide.BUY:
            pnl = (price - self.entry_price) * self.volume
        else:  # SELL
            pnl = (self.entry_price - price) * self.volume

        return pnl


@dataclass
class AccountInfo:
    """Trading account information."""
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    currency: str = "USD"
    leverage: int = 100
    timestamp: datetime = field(default_factory=datetime.now)

