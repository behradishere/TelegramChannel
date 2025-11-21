"""MetaTrader5 trading backend implementation."""
from typing import Optional, List

from src.api.trading_backend import TradingBackend
from src.domain.models import Order, Position, AccountInfo, TradeSide, OrderType
from src.core.config import MT5Config, TradingConfig
from src.core.logging import get_logger
from src.core.symbol_cache import get_symbol_cache

logger = get_logger(__name__)


class MT5Backend(TradingBackend):
    """MetaTrader5 API implementation."""

    def __init__(self, config: MT5Config, trading_config: TradingConfig):
        """
        Initialize MT5 backend.

        Args:
            config: MT5 specific configuration
            trading_config: General trading configuration
        """
        self.config = config
        self.trading_config = trading_config
        self._initialized = False
        self._mt5 = None

    def is_available(self) -> bool:
        """Check if MetaTrader5 package is available."""
        try:
            import MetaTrader5
            return True
        except ImportError:
            return False

    def initialize(self) -> bool:
        """Initialize MT5 terminal connection."""
        if self._initialized:
            logger.debug("MT5 already initialized")
            return True

        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
        except ImportError as e:
            logger.error(
                "MetaTrader5 package not available. "
                "Install with 'pip install MetaTrader5' or switch to cTrader backend."
            )
            return False

        # Initialize with credentials if provided
        if self.config.is_configured():
            try:
                login = int(self.config.login)
            except ValueError:
                logger.error(f"MT5_LOGIN must be numeric, got: {self.config.login}")
                return False

            if not mt5.initialize(
                login=login,
                password=self.config.password,
                server=self.config.server
            ):
                error = mt5.last_error()
                logger.error(
                    f"MT5 initialization failed: {error}. "
                    f"Account: {login}, Server: {self.config.server}"
                )
                return False

            logger.info(f"MT5 initialized with credentials (account: {login})")
        else:
            # Initialize without credentials (use existing terminal session)
            if not mt5.initialize():
                error = mt5.last_error()
                logger.error(
                    f"MT5 initialization failed: {error}. "
                    "Ensure MT5 terminal is running and logged in."
                )
                return False

            logger.info("MT5 initialized using existing terminal session")

        self._initialized = True
        return True

    def shutdown(self) -> None:
        """Shutdown MT5 connection."""
        if not self._initialized or not self._mt5:
            return

        try:
            self._mt5.shutdown()
            self._initialized = False
            logger.info("MT5 connection closed")
        except Exception as e:
            logger.warning(f"Error shutting down MT5: {e}")

    def _validate_stops(
        self, 
        symbol: str, 
        order_type: int,
        price: float, 
        stop_loss: Optional[float], 
        take_profit: Optional[float]
    ) -> bool:
        """
        Validate stop loss and take profit levels without adjusting them.
        Logs errors if stops are invalid but returns the original values.
        
        Args:
            symbol: Symbol name
            order_type: MT5 order type (BUY or SELL)
            price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if valid, False if invalid (but doesn't modify values)
        """
        mt5 = self._mt5
        sym_info = mt5.symbol_info(symbol)
        
        if sym_info is None:
            logger.warning(f"Could not get symbol info for {symbol}")
            return True  # Can't validate, assume OK
        
        is_buy = order_type == mt5.ORDER_TYPE_BUY
        is_valid = True
        
        # Validate that stops are on the correct side of price
        if stop_loss is not None:
            if is_buy and stop_loss >= price:
                logger.error(
                    f"❌ Invalid SL for BUY: SL={stop_loss:.5f} must be BELOW entry={price:.5f}"
                )
                is_valid = False
            elif not is_buy and stop_loss <= price:
                logger.error(
                    f"❌ Invalid SL for SELL: SL={stop_loss:.5f} must be ABOVE entry={price:.5f}"
                )
                is_valid = False
        
        if take_profit is not None:
            if is_buy and take_profit <= price:
                logger.error(
                    f"❌ Invalid TP for BUY: TP={take_profit:.5f} must be ABOVE entry={price:.5f}"
                )
                is_valid = False
            elif not is_buy and take_profit >= price:
                logger.error(
                    f"❌ Invalid TP for SELL: TP={take_profit:.5f} must be BELOW entry={price:.5f}"
                )
                is_valid = False
        
        # Check minimum distance if broker enforces it
        stops_level = sym_info.trade_stops_level
        point = sym_info.point
        min_distance = stops_level * point
        
        if stops_level > 0:
            if stop_loss is not None:
                actual_distance = abs(price - stop_loss)
                if actual_distance < min_distance:
                    logger.warning(
                        f"⚠️  SL too close: distance={actual_distance:.5f}, "
                        f"minimum={min_distance:.5f} ({stops_level} points)"
                    )
            
            if take_profit is not None:
                actual_distance = abs(price - take_profit)
                if actual_distance < min_distance:
                    logger.warning(
                        f"⚠️  TP too close: distance={actual_distance:.5f}, "
                        f"minimum={min_distance:.5f} ({stops_level} points)"
                    )
        
        return is_valid

    def place_order(self, order: Order) -> dict:
        """
        Place order via MT5 API.

        Args:
            order: Order to execute

        Returns:
            Order execution result
        """
        if self.trading_config.dry_run:
            logger.info(f"[DRY RUN][MT5] Would place order: {order.to_dict()}")
            return {
                'status': 'dry_run',
                'order': order.to_dict()
            }

        if not self._initialized:
            raise RuntimeError("MT5 backend not initialized")

        mt5 = self._mt5
        
        # Find the actual symbol name in MT5
        actual_symbol = self.find_symbol(order.symbol)
        if actual_symbol is None:
            available = self.get_available_symbols()
            raise ValueError(
                f"Symbol {order.symbol} not found in MT5. "
                f"Available symbols: {len(available)} total. "
                f"Use get_available_symbols() to see all."
            )
        
        symbol = actual_symbol
        volume = order.volume

        # Ensure symbol is available
        sym_info = mt5.symbol_info(symbol)
        if sym_info is None:
            raise ValueError(f"Symbol {symbol} not found in MT5")

        if not sym_info.visible:
            if not mt5.symbol_select(symbol, True):
                raise ValueError(f"Failed to enable symbol {symbol}")

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f"Failed to get tick data for {symbol}")

        # Determine price
        if order.order_type == OrderType.MARKET or not order.price:
            price = tick.ask if order.side == TradeSide.BUY else tick.bid
        else:
            price = order.price

        # Determine MT5 order type
        if order.side == TradeSide.BUY:
            mt5_type = mt5.ORDER_TYPE_BUY
        else:
            mt5_type = mt5.ORDER_TYPE_SELL

        # Get best filling mode for this symbol from cache
        symbol_cache = get_symbol_cache()
        filling_mode = symbol_cache.get_best_filling_mode(
            symbol, 
            preferred_mode=mt5.ORDER_FILLING_IOC
        )
        
        # Fallback to IOC if cache is not loaded or symbol not found
        if filling_mode is None:
            filling_mode = mt5.ORDER_FILLING_IOC
            logger.warning(
                f"Using default filling mode (IOC) for {symbol}. "
                "Consider running export_symbols_details.py to cache symbol info."
            )
        else:
            logger.debug(f"Using filling mode {filling_mode} for {symbol}")

        # Validate stops - use only first TP for initial order
        # We'll manage multiple TPs through position manager
        sl = order.stop_loss
        tp = order.take_profits[0] if order.take_profits else None
        
        logger.info(
            f"Order details - Entry: {price:.5f}, SL: {sl}, "
            f"All TPs: {order.take_profits}, Side: {order.side.value.upper()}"
        )
        
        # Validate without adjusting
        if sl is not None or tp is not None:
            is_valid = self._validate_stops(symbol, mt5_type, price, sl, tp)
            if not is_valid:
                logger.error(
                    "❌ Stop levels are invalid. Order will NOT be placed. "
                    "Please fix the signal format."
                )
                raise ValueError(
                    "Invalid stop levels: stops must be on correct side of entry price. "
                    f"For {order.side.value.upper()}: "
                    f"SL={'below' if order.side == TradeSide.BUY else 'above'} entry, "
                    f"TP={'above' if order.side == TradeSide.BUY else 'below'} entry"
                )

        # Build trade request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_type,
            "price": float(price),
            "deviation": 20,
            "magic": 234000,
            "comment": "Signal Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        # Add stop loss if valid
        if sl is not None:
            request["sl"] = float(sl)

        # Add take profit if valid (only first one)
        if tp is not None:
            request["tp"] = float(tp)

        # Send order
        result = mt5.order_send(request)

        if result is None:
            error = mt5.last_error()
            logger.error(f"Order send failed: {error}")
            logger.error(f"Request details: {request}")
            raise RuntimeError(f"MT5 order_send failed: {error}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_details = (
                f"Order failed: {result.comment} (retcode: {result.retcode})\n"
                f"Symbol: {symbol}, Price: {price}, Volume: {volume}\n"
                f"SL: {request.get('sl', 'None')}, TP: {request.get('tp', 'None')}\n"
                f"Stops Level: {sym_info.trade_stops_level} points, Point: {sym_info.point}"
            )
            logger.error(error_details)
            raise RuntimeError(error_details)

        logger.info(
            f"Order executed successfully: "
            f"Order={result.order}, Deal={result.deal}, Volume={result.volume}"
        )

        return {
            'status': 'success',
            'order_id': result.order,
            'deal_id': result.deal,
            'volume': result.volume,
            'price': result.price,
            'comment': result.comment,
            'retcode': result.retcode
        }

    def get_account_info(self) -> Optional[AccountInfo]:
        """Get MT5 account information."""
        if not self._initialized or not self._mt5:
            logger.warning("MT5 backend not initialized")
            return None

        try:
            account_info = self._mt5.account_info()
            if account_info is None:
                error = self._mt5.last_error()
                logger.error(f"Failed to get account info: {error}")
                return None

            return AccountInfo(
                balance=account_info.balance,
                equity=account_info.equity,
                margin=account_info.margin,
                free_margin=account_info.margin_free,
                margin_level=account_info.margin_level,
                currency=account_info.currency,
                leverage=account_info.leverage
            )

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_positions(self) -> List[Position]:
        """Get all open positions from MT5."""
        if not self._initialized or not self._mt5:
            logger.warning("MT5 backend not initialized")
            return []

        try:
            positions = self._mt5.positions_get()
            if positions is None:
                error = self._mt5.last_error()
                logger.error(f"Failed to get positions: {error}")
                return []

            result = []
            for pos in positions:
                position = Position(
                    symbol=pos.symbol,
                    side=TradeSide.BUY if pos.type == 0 else TradeSide.SELL,
                    volume=pos.volume,
                    entry_price=pos.price_open,
                    current_price=pos.price_current,
                    stop_loss=pos.sl if pos.sl > 0 else None,
                    take_profit=pos.tp if pos.tp > 0 else None,
                    position_id=str(pos.ticket),
                    unrealized_pnl=pos.profit
                )
                result.append(position)

            return result

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def close_position(self, position_id: str) -> bool:
        """Close a position in MT5."""
        if not self._initialized or not self._mt5:
            logger.error("MT5 backend not initialized")
            return False

        try:
            ticket = int(position_id)
            mt5 = self._mt5

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Position {position_id} not found")
                return False

            pos = position[0]

            # Determine closing type (opposite of opening)
            close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY

            # Get current price
            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {pos.symbol}")
                return False

            close_price = tick.bid if pos.type == 0 else tick.ask

            # Get best filling mode for this symbol from cache
            symbol_cache = get_symbol_cache()
            filling_mode = symbol_cache.get_best_filling_mode(
                pos.symbol,
                preferred_mode=mt5.ORDER_FILLING_IOC
            )
            
            # Fallback to IOC if cache is not loaded or symbol not found
            if filling_mode is None:
                filling_mode = mt5.ORDER_FILLING_IOC
                logger.warning(
                    f"Using default filling mode (IOC) for {pos.symbol}. "
                    "Consider running export_symbols_details.py to cache symbol info."
                )

            # Close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close by bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)

            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error = result.comment if result else mt5.last_error()
                logger.error(f"Failed to close position {position_id}: {error}")
                return False

            logger.info(f"Position {position_id} closed successfully")
            return True

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return False

    def close_position_partial(
        self, 
        position_id: str, 
        volume: float
    ) -> bool:
        """
        Close part of a position in MT5.
        
        Args:
            position_id: Position ticket number
            volume: Volume to close (partial)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self._mt5:
            logger.error("MT5 backend not initialized")
            return False

        try:
            ticket = int(position_id)
            mt5 = self._mt5

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Position {position_id} not found")
                return False

            pos = position[0]

            # Validate volume
            if volume > pos.volume:
                logger.error(
                    f"Cannot close {volume} lots, position only has {pos.volume} lots"
                )
                return False

            # Determine closing type (opposite of opening)
            close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY

            # Get current price
            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {pos.symbol}")
                return False

            close_price = tick.bid if pos.type == 0 else tick.ask

            # Get filling mode
            symbol_cache = get_symbol_cache()
            filling_mode = symbol_cache.get_best_filling_mode(
                pos.symbol,
                preferred_mode=mt5.ORDER_FILLING_IOC
            )
            
            if filling_mode is None:
                filling_mode = mt5.ORDER_FILLING_IOC

            # Partial close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": volume,  # Partial volume
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"Partial close ({volume} lots)",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)

            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error = result.comment if result else mt5.last_error()
                logger.error(f"Failed to partially close position {position_id}: {error}")
                return False

            logger.info(
                f"Partially closed {volume} lots of position {position_id} "
                f"(remaining: {pos.volume - volume})"
            )
            return True

        except Exception as e:
            logger.error(f"Error partially closing position {position_id}: {e}")
            return False

    def modify_position_sl(
        self, 
        position_id: str, 
        new_sl: float
    ) -> bool:
        """
        Modify the stop loss of an existing position.
        
        Args:
            position_id: Position ticket number
            new_sl: New stop loss price
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self._mt5:
            logger.error("MT5 backend not initialized")
            return False

        try:
            ticket = int(position_id)
            mt5 = self._mt5

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Position {position_id} not found")
                return False

            pos = position[0]

            # Modification request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": pos.symbol,
                "sl": float(new_sl),
                "tp": pos.tp,  # Keep existing TP
            }

            result = mt5.order_send(request)

            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error = result.comment if result else mt5.last_error()
                logger.error(f"Failed to modify SL for position {position_id}: {error}")
                return False

            logger.info(f"Modified SL for position {position_id} to {new_sl:.5f}")
            return True

        except Exception as e:
            logger.error(f"Error modifying SL for position {position_id}: {e}")
            return False

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        if not self._initialized or not self._mt5:
            logger.warning("MT5 backend not initialized")
            return None

        try:
            # Find the actual symbol name
            actual_symbol = self.find_symbol(symbol)
            if actual_symbol is None:
                logger.error(f"Symbol {symbol} not found in MT5")
                return None
            
            tick = self._mt5.symbol_info_tick(actual_symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {actual_symbol}")
                return None

            return tick.bid

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def get_available_symbols(self) -> List[str]:
        """
        Get list of all available symbols in MT5.
        
        Returns:
            List of symbol names
        """
        if not self._initialized or not self._mt5:
            logger.warning("MT5 backend not initialized")
            return []

        try:
            symbols = self._mt5.symbols_get()
            if symbols is None:
                logger.error("Failed to get symbols from MT5")
                return []

            symbol_names = [sym.name for sym in symbols]
            logger.info(f"Found {len(symbol_names)} symbols in MT5")
            return symbol_names

        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []

    def find_symbol(self, symbol: str) -> Optional[str]:
        """
        Find a symbol in MT5, trying various formats.
        
        Args:
            symbol: Symbol to search for (e.g., 'XAUUSD', 'GOLD')
            
        Returns:
            The actual symbol name in MT5, or None if not found
        """
        if not self._initialized or not self._mt5:
            logger.warning("MT5 backend not initialized")
            return None

        try:
            # First, try exact match
            sym_info = self._mt5.symbol_info(symbol)
            if sym_info is not None:
                return symbol

            # Get all available symbols
            all_symbols = self.get_available_symbols()
            
            # Try case-insensitive match
            symbol_upper = symbol.upper()
            for sym in all_symbols:
                if sym.upper() == symbol_upper:
                    logger.info(f"Found symbol match: {symbol} -> {sym}")
                    return sym
            
            # Try partial match (e.g., XAUUSD might be XAUUSD_o or XAUUSDm)
            for sym in all_symbols:
                if sym.upper().startswith(symbol_upper):
                    logger.info(f"Found symbol with prefix: {symbol} -> {sym}")
                    return sym
            
            # Try common broker-specific variations
            variations = [
                f"{symbol}_o",  # Common suffix for some brokers
                f"{symbol}m",   # Mini lot
                f"{symbol}.a",  # Suffix
                f"{symbol}.b",
                f"{symbol}.c",
                f"#{symbol}",   # Some brokers use # for stocks
                f"{symbol}i",   # Another common suffix
            ]
            
            for variation in variations:
                sym_info = self._mt5.symbol_info(variation)
                if sym_info is not None:
                    logger.info(f"Found symbol variation: {symbol} -> {variation}")
                    return variation
            
            # Log available symbols that might be related
            related = [s for s in all_symbols if symbol[:3].upper() in s.upper()]
            if related:
                logger.warning(
                    f"Symbol '{symbol}' not found. Similar symbols available: {', '.join(related[:10])}"
                )
            else:
                logger.error(f"Symbol '{symbol}' not found in MT5. No similar symbols found.")
            
            return None

        except Exception as e:
            logger.error(f"Error finding symbol {symbol}: {e}")
            return None

