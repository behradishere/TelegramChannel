"""Signal parsing service - extracts trading signals from Telegram messages."""
import re
from decimal import Decimal
from typing import Optional

from src.domain.models import Signal, TradeSide
from src.core.logging import get_logger

logger = get_logger(__name__)


class SignalParser:
    """
    Parser for extracting trading signals from text messages.

    Supports multiple languages (English, Persian, Arabic) and various signal formats.
    """

    # Persian/Arabic digit translation table
    _digit_map = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')

    # Symbol mappings
    _symbol_map = {
        'GOLD': 'XAUUSD',
        'XAU': 'XAUUSD',
    }

    def __init__(self):
        """Initialize the parser."""
        pass

    def normalize_digits(self, text: str) -> str:
        """Convert Persian/Arabic digits to Western digits."""
        return text.translate(self._digit_map)

    def normalize_text(self, text: str) -> str:
        """
        Normalize text by converting digits and Persian keywords to English.

        Args:
            text: Raw text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        text = self.normalize_digits(text)

        # Normalize Persian/Arabic trading terms
        text = text.replace('اسکلپ', 'scalp')
        text = text.replace('خرید', 'Buy')
        text = text.replace('فروش', 'Sell')

        return text

    def parse(self, text: str) -> Signal:
        """
        Parse a signal from text message.

        Args:
            text: Raw message text

        Returns:
            Signal object with extracted information
        """
        normalized_text = self.normalize_text(text)

        signal = Signal(raw_message=text)

        # Extract symbol
        signal.symbol = self._extract_symbol(normalized_text)

        # Extract market price
        signal.market_price = self._extract_market_price(normalized_text)

        # Extract buy/sell ranges
        signal.buy_range = self._extract_buy_range(normalized_text)
        signal.sell_range = self._extract_sell_range(normalized_text)

        # Extract take profit levels
        signal.take_profits = self._extract_take_profits(normalized_text)

        # Extract stop loss
        signal.stop_loss = self._extract_stop_loss(normalized_text)

        # Extract pip count
        signal.pip_count = self._extract_pip_count(normalized_text)

        # Determine trade side
        signal.side = self._determine_side(normalized_text, signal)

        if signal.is_valid():
            logger.info(f"Successfully parsed signal: {signal.symbol} {signal.side}")
        else:
            logger.warning(f"Parsed incomplete signal: {signal}")

        return signal

    def _extract_symbol(self, text: str) -> Optional[str]:
        """Extract trading symbol from text."""
        # Support multiple common symbols
        pattern = r'\b(XAUUSD|GOLD|XAU|EURUSD|GBPUSD|USDJPY|BTCUSD|ETHUSD)\b'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            symbol = match.group(1).upper()
            return self._symbol_map.get(symbol, symbol)

        return None

    def _extract_market_price(self, text: str) -> Optional[Decimal]:
        """Extract market price from text."""
        pattern = r'Market\s*price\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return Decimal(match.group(1))

        return None

    def _extract_buy_range(self, text: str) -> Optional[tuple]:
        """Extract buy range from text."""
        pattern = r'Buy\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            a = Decimal(match.group(1))
            b = Decimal(match.group(2))
            return (min(a, b), max(a, b))

        return None

    def _extract_sell_range(self, text: str) -> Optional[tuple]:
        """Extract sell range from text."""
        pattern = r'Sell\s*(?:now)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            a = Decimal(match.group(1))
            b = Decimal(match.group(2))
            return (min(a, b), max(a, b))

        return None

    def _extract_take_profits(self, text: str) -> list:
        """Extract take profit levels from text."""
        take_profits = []

        for i in range(1, 5):
            pattern = rf'Tp{i}[\s:\-]*([0-9]+(?:\.[0-9]+)?|open)'
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                val = match.group(1).lower()
                if val == 'open':
                    take_profits.append(None)
                else:
                    take_profits.append(Decimal(val))
            else:
                take_profits.append(None)

        return take_profits

    def _extract_stop_loss(self, text: str) -> Optional[Decimal]:
        """Extract stop loss from text."""
        # Accept SL, SI, or S[I|L]
        pattern = r'\bS[LI]\b\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return Decimal(match.group(1))

        return None

    def _extract_pip_count(self, text: str) -> Optional[int]:
        """Extract pip count from text."""
        pattern = r'(\d+)\s*pip'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return int(match.group(1))

        return None

    def _determine_side(self, text: str, signal: Signal) -> Optional[TradeSide]:
        """Determine trade side (buy/sell) from signal data."""
        # Prioritize range indicators
        if signal.sell_range:
            return TradeSide.SELL
        elif signal.buy_range:
            return TradeSide.BUY

        # Fall back to keyword detection
        match = re.search(r'\b(Buy|Sell)\b', text, re.IGNORECASE)
        if match:
            return TradeSide(match.group(1).lower())

        return None

