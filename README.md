# Telegram Signal Bot

Automated trading assistant that listens to configured Telegram channels, parses structured trade signals, applies risk controls, and routes the resulting orders to cTrader or MetaTrader 5 backends.

## Table of Contents
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Trading Backends](#trading-backends)
- [Testing](#testing)
- [Monitoring & Operations](#monitoring--operations)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

## Architecture

```
run.py ──▶ src/bot.py ──▶ SignalBot orchestrator
             │
             ├─ core/config.py ........ load & validate env (.env / CI vars)
             ├─ core/logging.py ...... structured logging to logs/bot.log
             ├─ infrastructure/telegram/client.py ──▶ Telethon client wrapper
             ├─ services/signal_parser.py .......... interpret channel text
             ├─ services/risk_manager.py ........... manage exposure, balance
             ├─ services/order_service.py .......... build executable orders
             └─ services/trading_service.py ........ select cTrader/MT5 backend
```

Signals that pass parsing and risk filters are converted to `Order` objects (see `src/domain/models.py`) and delivered to the configured backend (`src/api/trading_backend.py`). Health and log information is persisted under `logs/` and `health.txt` for easy operational checks.

## Features
- Monitors any mix of public or private Telegram channels using Telethon sessions
- Supports multiple trading backends (`ctrader` REST or local `mt5`) with dry-run safety mode
- Pluggable signal parsing with extensive tests (`tests/test_signal_parser*.py`)
- Risk-aware order sizing and balance tracking (`src/services/risk_manager.py`)
- Docker and Make targets for consistent local or containerized operation
- `--list-channels` helper to capture channel metadata into `config/channels.json`

## Prerequisites
- Python 3.11+
- Telegram API credentials from https://my.telegram.org/apps
- Access to a cTrader REST account or an MT5 terminal (optional when using dry-run)
- (Optional) Docker 24+ and docker-compose 1.29+ if running via containers

## Quick Start

### 1. Clone & install
```sh
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
Alternatively, run `make install` to automate the steps above plus `.env` scaffolding.

### 2. Configure environment
1. Copy `.env.example` to `.env` (automatically done by `make install`).
2. Fill in `API_ID` and `API_HASH` plus your preferred channel configuration (see [Configuration](#configuration)).
3. Choose a trading backend with `TRADING_BACKEND=ctrader|mt5` and decide whether to keep `DRY_RUN=true` while testing.

### 3. Start the bot
```sh
python run.py
```
Use `python run.py --list-channels` once to fetch channel IDs into `config/channels.json` for reference.

## Configuration

The bot reads settings via `src/core/config.py`, prioritizing `.env` variables but compatible with any environment injection (CI/CD, container). Key groups:

### Telegram
- `API_ID`, `API_HASH`: required; retrieved from Telegram developer portal.
- `SESSION_NAME`: filename for the Telethon session (default `signals_session`).
- Channel targeting options (pick one):
  - `CHANNEL_USERNAME`: public username
  - `CHANNEL_ID` + `CHANNEL_ACCESS_HASH`: private channel
  - `CHANNELS`: comma separated entries; each can be `@username` or `id,access_hash`

### Trading & Risk
- `TRADING_BACKEND`: `ctrader` (default) or `mt5`.
- `DRY_RUN`: `true` keeps execution offline while still parsing signals.
- `SYMBOL_XAU`, `PIP_SIZE`, `DEFAULT_VOLUME`: parsing defaults.
- `RISK_PERCENT`, `MAX_VOLUME`, `MIN_VOLUME`, `ACCOUNT_BALANCE`: inputs for `RiskManager` sizing rules.
- cTrader-specific: `BROKER_REST_URL`, `CTRADER_TOKEN`.
- MT5-specific: `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` (optional when MT5 terminal already logged in).

### Logging & Health
- `LOG_FILE`: default `logs/bot.log`; rotated via `src/core/logging.py`.
- `LOG_LEVEL`: `INFO`, `DEBUG`, etc.
- `HEALTH_FILE`: default `logs/health.txt`, updated with `status|timestamp` markers.

## Running the Bot

### Local (Python)
```sh
python run.py                  # start processing channels
python run.py --list-channels  # dump dialogs to config/channels.json
```

### Make targets
```sh
make run        # python main.py (legacy entry point)
make run-dry    # ensures DRY_RUN=true
make list-channels
make test
```
`run.py` is the current entry point; `main.py` is kept for backward compatibility with Make targets.

### Docker
```sh
docker-compose up --build
```
- Mounts `./data` for logs/health/session persistence.
- Reuses host `.env` values via `env_file`.
- Health check executes `health_check.py` inside the container.

To run manually without compose:
```sh
docker build -t telegram-signal-bot .
docker run --env-file .env -v $(pwd)/data:/data telegram-signal-bot
```

## Trading Backends

| Backend  | Availability check                         | Notes |
|----------|--------------------------------------------|-------|
| `ctrader`| Requires `BROKER_REST_URL` + `CTRADER_TOKEN`| Uses REST OpenAPI; fails fast if creds missing (unless `DRY_RUN=true`).
| `mt5`    | Works with local MT5 terminal sessions      | Credentials optional when terminal already authenticated.

`TradingService` (`src/services/trading_service.py`) auto-selects the backend, initializes it, and exposes `execute_order`, `get_account_info`, and `get_current_price` APIs.

## Testing

The suite covers parsing logic, backend selection, and risk sizing:
```sh
pytest tests -v
```
Focus areas:
- `tests/test_signal_parser*.py`: validates extended formats and edge cases.
- `tests/test_risk_manager.py`: enforces sizing constraints.
- `tests/test_backend_switching.py`: ensures runtime respects backend availability.

Run `make test-coverage` for reports in `htmlcov/`.

## Monitoring & Operations
- Logs: default at `logs/bot.log`; stream via `make logs` or `tail -f logs/bot.log`.
- Health: `health.txt` (or configured path) records `starting/running/stopped/error` transitions with timestamps. `make health` prints the latest state.
- Channel discovery: `python run.py --list-channels` populates `config/channels.json` for manual channel management.
- Channel ID helper: `python scripts/get_channel_id.py` prompts for a username and outputs its numeric ID.

## Troubleshooting
- **`ValueError: API_ID and API_HASH must be set`**: ensure `.env` contains valid Telegram credentials.
- **No channels configured**: verify at least one of `CHANNEL_USERNAME`, `CHANNEL_ID`/`CHANNEL_ACCESS_HASH`, or `CHANNELS` is filled.
- **Backend unavailable**: check that credentials for the selected backend are present. When experimenting, set `DRY_RUN=true` to bypass live execution.
- **Session issues**: delete `signals_session.session` (after backing it up) to force a fresh Telegram login.
- **Docker health check failing**: inspect `/data/health.txt` inside the container and container logs via `docker logs telegram-signal-bot`.

## Project Structure

```
├── run.py                 # Primary CLI entry (list channels / run bot)
├── src/
│   ├── bot.py             # SignalBot orchestrator
│   ├── core/              # config + logging utilities
│   ├── services/          # parser, risk manager, trading orchestrator
│   ├── infrastructure/    # Telegram & backend integrations
│   └── domain/            # dataclasses for signals/orders
├── tests/                 # Pytest suites (unit & integration)
├── scripts/get_channel_id.py
├── docker-compose.yml     # Containerized deployment
├── Dockerfile             # Image definition
└── docs/README.md         # You are here
```

For further enhancements—metrics exporters, alternative parsers, or CI hooks—extend the service classes under `src/services/` and keep counterparts covered by the existing tests for confidence.

