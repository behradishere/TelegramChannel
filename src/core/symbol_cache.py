"""Symbol cache for loading and accessing MT5 symbol details."""
import json
from pathlib import Path
from typing import Optional, Dict, Any
from src.core.logging import get_logger

logger = get_logger(__name__)


class SymbolCache:
    """Cache for MT5 symbol details loaded from JSON."""
    
    _instance = None
    _symbols: Dict[str, Dict[str, Any]] = {}
    _loaded = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one cache instance."""
        if cls._instance is None:
            cls._instance = super(SymbolCache, cls).__new__(cls)
        return cls._instance
    
    def load(self, file_path: Optional[Path] = None) -> bool:
        """
        Load symbol details from JSON file.
        
        Args:
            file_path: Path to the JSON file. If None, uses default location.
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if self._loaded:
            logger.debug("Symbol cache already loaded")
            return True
        
        if file_path is None:
            file_path = Path(__file__).parent.parent.parent / "config" / "mt5_symbols_details.json"
        
        if not file_path.exists():
            logger.warning(f"Symbol details file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            symbols_list = data.get('symbols', [])
            
            # Index by symbol name for fast lookup
            self._symbols = {symbol['name']: symbol for symbol in symbols_list}
            self._loaded = True
            
            logger.info(f"Loaded {len(self._symbols)} symbols from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load symbol details: {e}", exc_info=True)
            return False
    
    def get_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol details by name.
        
        Args:
            name: Symbol name (e.g., 'XAUUSD')
            
        Returns:
            Dictionary with symbol details or None if not found
        """
        if not self._loaded:
            logger.warning("Symbol cache not loaded. Call load() first.")
            return None
        
        return self._symbols.get(name)
    
    def get_filling_mode(self, name: str) -> Optional[int]:
        """
        Get filling mode for a symbol.
        
        Args:
            name: Symbol name
            
        Returns:
            Filling mode constant or None if not found
        """
        symbol = self.get_symbol(name)
        if symbol:
            return symbol.get('filling_mode')
        return None
    
    def get_supported_filling_modes(self, name: str) -> list:
        """
        Get list of supported filling modes for a symbol.
        
        Args:
            name: Symbol name
            
        Returns:
            List of filling mode constants
        """
        symbol = self.get_symbol(name)
        if not symbol:
            return []
        
        filling_mode = symbol.get('filling_mode', 0)
        
        # MT5 filling_mode is a bitmask
        # Bit 0: FOK (1), Bit 1: IOC (2), Bit 2: RETURN (4), Bit 3: BOC (8)
        try:
            import MetaTrader5 as mt5
            modes = []
            if filling_mode & 1:
                modes.append(mt5.ORDER_FILLING_FOK)
            if filling_mode & 2:
                modes.append(mt5.ORDER_FILLING_IOC)
            if filling_mode & 4:
                modes.append(mt5.ORDER_FILLING_RETURN)
            # BOC is not commonly available, checking anyway
            # if filling_mode & 8:
            #     modes.append(mt5.ORDER_FILLING_BOC)
            return modes
        except ImportError:
            return []
    
    def get_best_filling_mode(self, name: str, preferred_mode: Optional[int] = None) -> Optional[int]:
        """
        Get the best filling mode for a symbol.
        
        Args:
            name: Symbol name
            preferred_mode: Preferred filling mode constant (if supported)
            
        Returns:
            Best filling mode constant or None
        """
        modes = self.get_supported_filling_modes(name)
        
        if not modes:
            return None
        
        # If preferred mode is supported, use it
        if preferred_mode and preferred_mode in modes:
            return preferred_mode
        
        # Otherwise, return the first supported mode
        # Priority: IOC > FOK > RETURN
        try:
            import MetaTrader5 as mt5
            for mode in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]:
                if mode in modes:
                    return mode
        except ImportError:
            pass
        
        return modes[0] if modes else None
    
    def get_volume_limits(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get volume limits for a symbol.
        
        Args:
            name: Symbol name
            
        Returns:
            Dict with volume_min, volume_max, volume_step or None
        """
        symbol = self.get_symbol(name)
        if symbol:
            return {
                'volume_min': symbol.get('volume_min', 0.01),
                'volume_max': symbol.get('volume_max', 100.0),
                'volume_step': symbol.get('volume_step', 0.01)
            }
        return None
    
    def is_loaded(self) -> bool:
        """Check if cache is loaded."""
        return self._loaded
    
    def reload(self, file_path: Optional[Path] = None) -> bool:
        """
        Reload symbol details from file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            True if reloaded successfully
        """
        self._loaded = False
        self._symbols.clear()
        return self.load(file_path)


# Global instance
_symbol_cache = SymbolCache()


def get_symbol_cache() -> SymbolCache:
    """Get the global symbol cache instance."""
    return _symbol_cache
