# config.py
"""Configuration management for the Telegram Signal Bot."""
import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centralized configuration class."""

    # Telegram API credentials
    API_ID: int
    API_HASH: str
    SESSION_NAME: str

    # Channel configuration
    CHANNEL_USERNAME: Optional[str]
    CHANNEL_ID: Optional[int]
    CHANNEL_ACCESS_HASH: Optional[int]
    CHANNELS: Optional[str]

    # Trading backend
    TRADING_BACKEND: str
    DRY_RUN: bool

    # cTrader configuration
    BROKER_REST_URL: Optional[str]
    CTRADER_TOKEN: Optional[str]

    # Trading parameters
    SYMBOL_XAU: str
    PIP_SIZE: float
    DEFAULT_VOLUME: float
    RISK_PERCENT: float
    MAX_VOLUME: float
    MIN_VOLUME: float

    # Logging
    LOG_FILE: str
    LOG_LEVEL: str
    LOG_MAX_BYTES: int
    LOG_BACKUP_COUNT: int

    # Health monitoring
    HEALTH_FILE: str

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Telegram API
        api_id_raw = os.getenv("API_ID")
        if not api_id_raw:
            raise ValueError("API_ID must be set in environment")
        try:
            self.API_ID = int(api_id_raw)
        except ValueError:
            raise ValueError(f"API_ID must be an integer, got: {api_id_raw!r}")

        self.API_HASH = os.getenv("API_HASH")
        if not self.API_HASH:
            raise ValueError("API_HASH must be set in environment")

        self.SESSION_NAME = os.getenv("SESSION_NAME", "signals_session")

        # Channels
        self.CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
        self.CHANNELS = os.getenv("CHANNELS")

        chan_id = os.getenv("CHANNEL_ID")
        self.CHANNEL_ID = int(chan_id) if chan_id else None

        chan_hash = os.getenv("CHANNEL_ACCESS_HASH")
        self.CHANNEL_ACCESS_HASH = int(chan_hash) if chan_hash else None

        # Trading
        self.TRADING_BACKEND = os.getenv("TRADING_BACKEND", "ctrader").lower()
        self.DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")

        # cTrader
        self.BROKER_REST_URL = os.getenv("BROKER_REST_URL")
        self.CTRADER_TOKEN = os.getenv("CTRADER_TOKEN")

        # Trading parameters
        self.SYMBOL_XAU = os.getenv("SYMBOL_XAU", "XAUUSD")
        self.PIP_SIZE = float(os.getenv("PIP_SIZE", "0.01"))
        self.DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.01"))
        self.RISK_PERCENT = float(os.getenv("RISK_PERCENT", "1.0"))
        self.MAX_VOLUME = float(os.getenv("MAX_VOLUME", "1.0"))
        self.MIN_VOLUME = float(os.getenv("MIN_VOLUME", "0.01"))

        # Logging
        self.LOG_FILE = os.getenv("LOG_FILE", "bot.log")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
        self.LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

        # Health
        self.HEALTH_FILE = os.getenv("HEALTH_FILE", "health.txt")

    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings/errors."""
        issues = []

        if self.TRADING_BACKEND not in ("ctrader", "mt5"):
            issues.append(f"Invalid TRADING_BACKEND: {self.TRADING_BACKEND}")

        if self.TRADING_BACKEND == "ctrader" and not self.DRY_RUN:
            if not self.BROKER_REST_URL:
                issues.append("BROKER_REST_URL required for cTrader backend")
            if not self.CTRADER_TOKEN:
                issues.append("CTRADER_TOKEN required for cTrader backend")

        if not any([self.CHANNEL_USERNAME, self.CHANNELS,
                   (self.CHANNEL_ID and self.CHANNEL_ACCESS_HASH)]):
            issues.append("No channel configured. Set CHANNEL_USERNAME, CHANNELS, or CHANNEL_ID+CHANNEL_ACCESS_HASH")

        if self.DEFAULT_VOLUME < self.MIN_VOLUME:
            issues.append(f"DEFAULT_VOLUME ({self.DEFAULT_VOLUME}) less than MIN_VOLUME ({self.MIN_VOLUME})")

        if self.DEFAULT_VOLUME > self.MAX_VOLUME:
            issues.append(f"DEFAULT_VOLUME ({self.DEFAULT_VOLUME}) exceeds MAX_VOLUME ({self.MAX_VOLUME})")

        return issues

    def __repr__(self) -> str:
        """String representation (hide sensitive data)."""
        return (
            f"Config(API_ID={self.API_ID}, "
            f"SESSION_NAME={self.SESSION_NAME}, "
            f"TRADING_BACKEND={self.TRADING_BACKEND}, "
            f"DRY_RUN={self.DRY_RUN})"
        )


# Global config instance
config = Config()

