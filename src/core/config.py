"""Configuration management for the Telegram Signal Bot.

This module provides a centralized configuration management system using
environment variables and .env files. It follows the 12-factor app methodology.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram API configuration."""

    api_id: int
    api_hash: str
    session_name: str = "signals_session"
    channel_username: Optional[str] = None
    channel_id: Optional[int] = None
    channel_access_hash: Optional[int] = None
    channels: Optional[str] = None

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        """Create configuration from environment variables."""
        api_id_raw = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")

        if not api_id_raw or not api_hash:
            raise ValueError("API_ID and API_HASH must be set in environment or .env")

        try:
            api_id = int(api_id_raw)
        except ValueError:
            raise ValueError(f"API_ID must be an integer, got: {api_id_raw!r}")

        channel_id_raw = os.getenv("CHANNEL_ID")
        channel_id = int(channel_id_raw) if channel_id_raw else None

        channel_access_hash_raw = os.getenv("CHANNEL_ACCESS_HASH")
        channel_access_hash = int(channel_access_hash_raw) if channel_access_hash_raw else None

        return cls(
            api_id=api_id,
            api_hash=api_hash,
            session_name=os.getenv("SESSION_NAME", "signals_session"),
            channel_username=os.getenv("CHANNEL_USERNAME"),
            channel_id=channel_id,
            channel_access_hash=channel_access_hash,
            channels=os.getenv("CHANNELS")
        )


@dataclass
class CTraderConfig:
    """cTrader broker configuration."""

    rest_url: Optional[str] = None
    token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "CTraderConfig":
        """Create configuration from environment variables."""
        return cls(
            rest_url=os.getenv("BROKER_REST_URL"),
            token=os.getenv("CTRADER_TOKEN")
        )

    def is_configured(self) -> bool:
        """Check if cTrader is properly configured."""
        return bool(self.rest_url and self.token)


@dataclass
class MT5Config:
    """MetaTrader5 configuration."""

    login: Optional[str] = None
    password: Optional[str] = None
    server: Optional[str] = None

    @classmethod
    def from_env(cls) -> "MT5Config":
        """Create configuration from environment variables."""
        return cls(
            login=os.getenv("MT5_LOGIN"),
            password=os.getenv("MT5_PASSWORD"),
            server=os.getenv("MT5_SERVER")
        )

    def is_configured(self) -> bool:
        """Check if MT5 is properly configured."""
        return bool(self.login and self.password and self.server)


@dataclass
class TradingConfig:
    """Trading parameters configuration."""

    backend: str = "ctrader"
    dry_run: bool = True
    symbol_xau: str = "XAUUSD"
    pip_size: float = 0.01
    default_volume: float = 0.01
    risk_percent: float = 1.0
    max_volume: float = 1.0
    min_volume: float = 0.01
    account_balance: float = 10000.0

    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Create configuration from environment variables."""
        dry_run_str = os.getenv("DRY_RUN", "true").lower()
        dry_run = dry_run_str in ("1", "true", "yes")

        return cls(
            backend=os.getenv("TRADING_BACKEND", "ctrader").lower(),
            dry_run=dry_run,
            symbol_xau=os.getenv("SYMBOL_XAU", "XAUUSD"),
            pip_size=float(os.getenv("PIP_SIZE", "0.01")),
            default_volume=float(os.getenv("DEFAULT_VOLUME", "0.01")),
            risk_percent=float(os.getenv("RISK_PERCENT", "1.0")),
            max_volume=float(os.getenv("MAX_VOLUME", "1.0")),
            min_volume=float(os.getenv("MIN_VOLUME", "0.01")),
            account_balance=float(os.getenv("ACCOUNT_BALANCE", "10000.0"))
        )


@dataclass
class LoggingConfig:
    """Logging configuration."""

    log_file: str = "bot.log"
    log_level: str = "INFO"
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables."""
        return cls(
            log_file=os.getenv("LOG_FILE", "logs/bot.log"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_max_bytes=int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024))),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "3"))
        )


@dataclass
class AppConfig:
    """Main application configuration container."""

    telegram: TelegramConfig
    trading: TradingConfig
    ctrader: CTraderConfig
    mt5: MT5Config
    logging: LoggingConfig

    health_file: str = "health.txt"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create full application configuration from environment."""
        return cls(
            telegram=TelegramConfig.from_env(),
            trading=TradingConfig.from_env(),
            ctrader=CTraderConfig.from_env(),
            mt5=MT5Config.from_env(),
            logging=LoggingConfig.from_env(),
            health_file=os.getenv("HEALTH_FILE", "logs/health.txt")
        )

    def validate(self) -> None:
        """Validate configuration consistency."""
        # Validate trading backend is properly configured
        if self.trading.backend == "ctrader" and not self.ctrader.is_configured():
            if not self.trading.dry_run:
                raise ValueError(
                    "cTrader backend selected but BROKER_REST_URL and CTRADER_TOKEN are not configured"
                )

        elif self.trading.backend == "mt5":
            # MT5 can work without credentials if terminal is logged in
            # So we don't enforce configuration here
            pass

        elif self.trading.backend not in ["ctrader", "mt5"]:
            raise ValueError(
                f"Invalid TRADING_BACKEND: {self.trading.backend}. Must be 'ctrader' or 'mt5'"
            )


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        _config.validate()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment."""
    global _config
    load_dotenv(override=True)
    _config = AppConfig.from_env()
    _config.validate()
    return _config

