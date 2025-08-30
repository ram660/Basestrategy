#!/usr/bin/env python3
"""
Configuration file for RSI MA Trading Bot

Contains all configurable parameters for the trading strategy and bot behavior
"""

from typing import List, Dict
from datetime import timedelta

class TradingConfig:
    """Trading strategy configuration"""

    # Strategy Parameters (Proven optimized values)
    RSI_PERIOD = 14
    MA53_PERIOD = 53
    MA50_PERIOD = 50
    RSI_BUY_THRESHOLD = 62.0    # Proven threshold for long entries
    RSI_SELL_THRESHOLD = 39.0   # Proven threshold for short entries

    # Risk Management
    STOP_LOSS_PCT = 0.03        # 3% stop loss
    TAKE_PROFIT_PCT = 0.025     # 2.5% take profit (optimized)
    POSITION_SIZE_PCT = 0.10    # 10% of account per trade

    # Bot Configuration
    MAX_CONCURRENT_TRADES = 3
    CYCLE_INTERVAL_SECONDS = 300  # 5 minutes between cycles
    DATA_INTERVAL = '5m'          # 5-minute candles
    DATA_PERIODS = 100            # Number of historical periods to fetch

    # Default symbols to trade
    DEFAULT_SYMBOLS = [
        'BTCUSDT',   # Bitcoin
        'XRPUSDT',   # XRP (strategy optimized for this)
        'ETHUSDT',   # Ethereum
        'ADAUSDT',   # Cardano
        'SOLUSDT',   # Solana
        'POLUSDT',   # Polygon (POL) - New token after migration
    ]

    # Account settings
    INITIAL_BALANCE = 10000.0     # Starting balance in USDT
    MIN_BALANCE_WARNING = 1000.0  # Warn when balance drops below this

class APIConfig:
    """API configuration for data fetching"""

    # Binance API (public endpoints, no auth required)
    BINANCE_BASE_URL = "https://api.binance.com"
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    # Rate limiting
    REQUESTS_PER_MINUTE = 1200  # Binance limit
    REQUEST_DELAY = 0.1  # Small delay between requests

class LoggingConfig:
    """Logging configuration"""

    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = "trading_bot.log"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5

class AlertConfig:
    """Alert and notification configuration"""

    # Console alerts
    ENABLE_CONSOLE_ALERTS = True

    # Position alerts
    ALERT_ON_POSITION_OPEN = True
    ALERT_ON_POSITION_CLOSE = True
    ALERT_ON_STOP_LOSS = True
    ALERT_ON_TAKE_PROFIT = True

    # Performance alerts
    ALERT_ON_DRAWDOWN_PCT = 10.0  # Alert if drawdown exceeds 10%
    ALERT_ON_WIN_STREAK = 5       # Alert on 5 consecutive wins
    ALERT_ON_LOSS_STREAK = 3      # Alert on 3 consecutive losses

class BacktestConfig:
    """Backtesting configuration"""

    # Historical data range
    BACKTEST_DAYS = 30
    BACKTEST_INTERVAL = '5m'

    # Backtesting parameters
    INITIAL_CAPITAL = 10000.0
    COMMISSION_PCT = 0.001  # 0.1% commission per trade
    SLIPPAGE_PCT = 0.0005   # 0.05% slippage

# Utility functions
def get_trading_config() -> Dict:
    """Get trading configuration as dictionary"""
    return {
        'rsi_period': TradingConfig.RSI_PERIOD,
        'ma53_period': TradingConfig.MA53_PERIOD,
        'ma50_period': TradingConfig.MA50_PERIOD,
        'rsi_buy_threshold': TradingConfig.RSI_BUY_THRESHOLD,
        'rsi_sell_threshold': TradingConfig.RSI_SELL_THRESHOLD,
        'stop_loss_pct': TradingConfig.STOP_LOSS_PCT,
        'take_profit_pct': TradingConfig.TAKE_PROFIT_PCT,
        'position_size_pct': TradingConfig.POSITION_SIZE_PCT,
        'max_concurrent_trades': TradingConfig.MAX_CONCURRENT_TRADES,
        'cycle_interval': TradingConfig.CYCLE_INTERVAL_SECONDS,
        'data_interval': TradingConfig.DATA_INTERVAL,
        'data_periods': TradingConfig.DATA_PERIODS,
        'symbols': TradingConfig.DEFAULT_SYMBOLS,
        'initial_balance': TradingConfig.INITIAL_BALANCE
    }

def validate_config() -> bool:
    """Validate configuration parameters"""
    try:
        # Check required parameters
        assert TradingConfig.RSI_PERIOD > 0, "RSI period must be positive"
        assert TradingConfig.MA53_PERIOD > 0, "MA53 period must be positive"
        assert TradingConfig.MA50_PERIOD > 0, "MA50 period must be positive"
        assert 0 < TradingConfig.STOP_LOSS_PCT < 1, "Stop loss must be between 0 and 1"
        assert 0 < TradingConfig.TAKE_PROFIT_PCT < 1, "Take profit must be between 0 and 1"
        assert 0 < TradingConfig.POSITION_SIZE_PCT <= 1, "Position size must be between 0 and 1"
        assert TradingConfig.MAX_CONCURRENT_TRADES > 0, "Max concurrent trades must be positive"
        assert TradingConfig.INITIAL_BALANCE > 0, "Initial balance must be positive"
        assert len(TradingConfig.DEFAULT_SYMBOLS) > 0, "Must have at least one symbol"

        return True

    except AssertionError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

# Export configuration classes
__all__ = [
    'TradingConfig',
    'APIConfig',
    'LoggingConfig',
    'AlertConfig',
    'BacktestConfig',
    'get_trading_config',
    'validate_config'
]