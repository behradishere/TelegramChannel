"""Position manager for handling multiple take profit levels and stop loss adjustments."""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.models import Order, Position, TradeSide
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ManagedPosition:
    """A position with multiple TP levels and tracking."""
    position_id: str
    symbol: str
    side: TradeSide
    entry_price: float
    initial_volume: float
    remaining_volume: float
    stop_loss: float
    take_profits: List[float]
    tp_hit_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    # Volume percentages for each TP level
    TP_PERCENTAGES = [0.40, 0.30, 0.30]  # 40%, 30%, 30%
    
    def get_volume_for_tp_level(self, level: int) -> float:
        """
        Get the volume to close at a specific TP level.
        
        Args:
            level: TP level (0-based index)
            
        Returns:
            Volume to close
        """
        if level >= len(self.TP_PERCENTAGES):
            return self.remaining_volume
        
        return self.initial_volume * self.TP_PERCENTAGES[level]
    
    def get_next_stop_loss(self, tp_level: int) -> Optional[float]:
        """
        Get the new stop loss level after hitting a TP.
        
        Rules:
        - TP1 hit: Move SL to Entry (break-even)
        - TP2 hit: Move SL to TP1
        - TP3 hit: Position closed
        
        Args:
            tp_level: TP level that was just hit (0-based)
            
        Returns:
            New stop loss price or None if position should be closed
        """
        if tp_level == 0:
            # TP1 hit: Move SL to break-even
            return self.entry_price
        elif tp_level == 1:
            # TP2 hit: Move SL to TP1
            return self.take_profits[0] if len(self.take_profits) > 0 else self.entry_price
        else:
            # TP3 hit: Close everything
            return None
    
    def mark_tp_hit(self, tp_level: int) -> None:
        """Mark a TP level as hit."""
        self.tp_hit_count = max(self.tp_hit_count, tp_level + 1)


class PositionManager:
    """Manager for tracking and managing positions with multiple TP levels."""
    
    def __init__(self):
        """Initialize position manager."""
        self._positions: Dict[str, ManagedPosition] = {}
    
    def add_position(
        self, 
        position_id: str, 
        order: Order,
        actual_entry_price: float
    ) -> ManagedPosition:
        """
        Add a new position to track.
        
        Args:
            position_id: Unique position identifier
            order: The original order
            actual_entry_price: Actual filled entry price
            
        Returns:
            ManagedPosition object
        """
        managed_pos = ManagedPosition(
            position_id=position_id,
            symbol=order.symbol,
            side=order.side,
            entry_price=actual_entry_price,
            initial_volume=order.volume,
            remaining_volume=order.volume,
            stop_loss=order.stop_loss or 0.0,
            take_profits=order.take_profits[:],  # Copy the list
            metadata=order.metadata.copy()
        )
        
        self._positions[position_id] = managed_pos
        
        logger.info(
            f"Added managed position {position_id}: {order.symbol} "
            f"{order.side.value.upper()} {order.volume} lots @ {actual_entry_price}"
        )
        
        if managed_pos.take_profits:
            logger.info(
                f"  TP levels: {', '.join([f'TP{i+1}={tp:.5f}' for i, tp in enumerate(managed_pos.take_profits)])}"
            )
        
        return managed_pos
    
    def get_position(self, position_id: str) -> Optional[ManagedPosition]:
        """Get a managed position by ID."""
        return self._positions.get(position_id)
    
    def remove_position(self, position_id: str) -> None:
        """Remove a position from tracking."""
        if position_id in self._positions:
            del self._positions[position_id]
            logger.info(f"Removed managed position {position_id}")
    
    def check_tp_hits(
        self, 
        position_id: str, 
        current_price: float
    ) -> List[tuple]:
        """
        Check if any TP levels have been hit.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            
        Returns:
            List of (tp_level, tp_price, volume_to_close, new_sl) tuples
        """
        managed_pos = self._positions.get(position_id)
        if not managed_pos:
            return []
        
        actions = []
        
        for tp_level, tp_price in enumerate(managed_pos.take_profits):
            # Skip if already hit
            if tp_level < managed_pos.tp_hit_count:
                continue
            
            # Check if TP is hit
            is_hit = False
            if managed_pos.side == TradeSide.BUY:
                is_hit = current_price >= tp_price
            else:  # SELL
                is_hit = current_price <= tp_price
            
            if is_hit:
                volume_to_close = managed_pos.get_volume_for_tp_level(tp_level)
                new_sl = managed_pos.get_next_stop_loss(tp_level)
                
                actions.append((tp_level, tp_price, volume_to_close, new_sl))
                
                logger.info(
                    f"TP{tp_level + 1} hit for {position_id}: "
                    f"Price {current_price:.5f} {'>=' if managed_pos.side == TradeSide.BUY else '<='} {tp_price:.5f}"
                )
        
        return actions
    
    def update_after_partial_close(
        self, 
        position_id: str, 
        tp_level: int,
        closed_volume: float,
        new_sl: Optional[float]
    ) -> None:
        """
        Update position tracking after partial close.
        
        Args:
            position_id: Position identifier
            tp_level: TP level that was hit
            closed_volume: Volume that was closed
            new_sl: New stop loss level
        """
        managed_pos = self._positions.get(position_id)
        if not managed_pos:
            return
        
        # Update tracking
        managed_pos.mark_tp_hit(tp_level)
        managed_pos.remaining_volume -= closed_volume
        
        if new_sl is not None:
            managed_pos.stop_loss = new_sl
            logger.info(
                f"Updated {position_id}: TP{tp_level + 1} closed {closed_volume:.2f} lots, "
                f"remaining {managed_pos.remaining_volume:.2f}, new SL: {new_sl:.5f}"
            )
        else:
            logger.info(
                f"Updated {position_id}: TP{tp_level + 1} closed {closed_volume:.2f} lots (final)"
            )
        
        # Remove if fully closed
        if managed_pos.remaining_volume <= 0.001:  # Small tolerance
            self.remove_position(position_id)
    
    def get_all_positions(self) -> List[ManagedPosition]:
        """Get all tracked positions."""
        return list(self._positions.values())
    
    def get_positions_for_symbol(self, symbol: str) -> List[ManagedPosition]:
        """Get all positions for a specific symbol."""
        return [pos for pos in self._positions.values() if pos.symbol == symbol]
