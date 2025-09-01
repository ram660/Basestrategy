#!/usr/bin/env python3
"""
Unified Configuration Management System
Centralized configuration for all trading bot components
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class RiskLevel(Enum):
    """Risk level settings"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

@dataclass
class TradingConfig:
    """Enhanced Trading configuration with improved risk management"""
    # Position Management - SAFER DEFAULTS
    position_size_usdt: float = 10.0  # Keep small position size
    leverage: float = 2.0  # Reduced from 10x to 2x for safety
    max_positions: int = 1
    
    # Enhanced Risk Management
    stop_loss_percent: float = 2.0  # Tighter stop loss (was 3.5%)
    take_profit_percent: float = 3.0  # Conservative take profit (was 5.0%)
    max_daily_loss_usdt: float = 30.0  # Reduced daily loss limit
    max_drawdown_percent: float = 15.0  # Stricter drawdown limit
    max_risk_per_trade_percent: float = 1.0  # Max 1% account risk per trade
    
    # Strategy Parameters - ENHANCED
    rsi_period: int = 14
    ma53_period: int = 53
    ma50_period: int = 50
    rsi_buy_threshold: float = 35.0  # More conservative (was 60.0)
    rsi_sell_threshold: float = 65.0  # More conservative (was 40.0)
    
    # NEW: Market Condition Filters
    trend_strength_threshold: float = 25.0  # ADX threshold for trend strength
    volume_multiplier_threshold: float = 1.3  # Volume must be 30% above average
    volatility_filter_enabled: bool = True
    max_volatility_threshold: float = 0.05  # 5% max volatility filter
    
    # NEW: Multi-timeframe Analysis
    primary_timeframe: str = "5m"
    confirmation_timeframe: str = "1h"
    require_trend_alignment: bool = True
    
    # NEW: Session Filters
    trading_sessions_enabled: bool = True
    allowed_trading_hours: List[int] = None  # Will be set in __post_init__
    avoid_news_times: bool = True
    
    # Paper Trading Mode
    paper_trading_mode: bool = True  # START IN PAPER TRADING
    
    # Fees
    taker_fee_percent: float = 0.06
    maker_fee_percent: float = 0.02
    
    def __post_init__(self):
        """Initialize default values that need to be lists"""
        if self.allowed_trading_hours is None:
            # Only trade during active market hours (UTC)
            # Avoid early Asian session and late US session
            self.allowed_trading_hours = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

@dataclass
class APIConfig:
    """API configuration settings"""
    # Bitget API
    bitget_api_key: str = ""
    bitget_secret_key: str = ""
    bitget_passphrase: str = ""
    bitget_base_url: str = "https://api.bitget.com"
    
    # Telegram API
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # API Limits
    max_requests_per_minute: int = 600
    request_timeout_seconds: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0

@dataclass
class SystemConfig:
    """System configuration settings"""
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug_mode: bool = False
    log_level: str = "INFO"
    
    # Data Management
    data_cache_ttl_minutes: int = 5
    trade_history_days: int = 30
    backup_interval_hours: int = 24
    
    # Monitoring
    health_check_interval_seconds: int = 60
    performance_update_interval_seconds: int = 300
    
    # Security
    enable_ip_whitelist: bool = False
    allowed_ips: List[str] = None
    encrypt_sensitive_data: bool = True

class ConfigManager:
    """Centralized configuration manager"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        # Production-ready: no testing_mode flag; always validate required settings
        self.trading = TradingConfig()
        self.api = APIConfig()
        self.system = SystemConfig()
        
        # Load configuration (env vars should be set in production)
        self._load_from_env()
        self._load_from_file()
        
        # Validate configuration strictly for production readiness
        self._validate_config()

    def _load_from_env(self):
        """Load configuration from environment variables"""
        try:
            # API Configuration
            self.api.bitget_api_key = os.getenv('BITGET_API_KEY', '')
            self.api.bitget_secret_key = os.getenv('BITGET_SECRET_KEY', '')
            self.api.bitget_passphrase = os.getenv('BITGET_PASSPHRASE', '')
            self.api.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
            self.api.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            
            # Trading Configuration
            if os.getenv('POSITION_SIZE_USDT'):
                self.trading.position_size_usdt = float(os.getenv('POSITION_SIZE_USDT'))
            if os.getenv('LEVERAGE'):
                self.trading.leverage = float(os.getenv('LEVERAGE'))
            if os.getenv('MAX_POSITIONS'):
                self.trading.max_positions = int(os.getenv('MAX_POSITIONS'))
            
            # System Configuration
            if os.getenv('ENVIRONMENT'):
                self.system.environment = Environment(os.getenv('ENVIRONMENT'))
            elif self._is_cloud_environment():
                # Auto-detect cloud environment as production
                self.system.environment = Environment.PRODUCTION
                logger.info("🌐 Auto-detected cloud environment, setting to PRODUCTION mode")
            
            if os.getenv('DEBUG_MODE'):
                self.system.debug_mode = os.getenv('DEBUG_MODE').lower() == 'true'
            if os.getenv('LOG_LEVEL'):
                self.system.log_level = os.getenv('LOG_LEVEL')
                
            logger.info("✅ Configuration loaded from environment variables")
            
        except Exception as e:
            logger.error(f"❌ Error loading environment configuration: {e}")

    def _load_from_file(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Update trading config
                if 'trading' in config_data:
                    for key, value in config_data['trading'].items():
                        if hasattr(self.trading, key):
                            setattr(self.trading, key, value)
                
                # Update system config
                if 'system' in config_data:
                    for key, value in config_data['system'].items():
                        if hasattr(self.system, key):
                            if key == 'environment':
                                setattr(self.system, key, Environment(value))
                            else:
                                setattr(self.system, key, value)
                
                logger.info(f"✅ Configuration loaded from {self.config_file}")
            else:
                logger.info(f"📝 Config file {self.config_file} not found, using defaults")
                
        except Exception as e:
            logger.error(f"❌ Error loading configuration file: {e}")

    def _validate_config(self, skip_api_validation: bool = False):
        """Validate configuration settings"""
        try:
            errors = []
            
            # Validate API credentials (skip in testing mode)
            if not skip_api_validation:
                if not self.api.bitget_api_key:
                    errors.append("Missing BITGET_API_KEY")
                if not self.api.bitget_secret_key:
                    errors.append("Missing BITGET_SECRET_KEY")
                if not self.api.bitget_passphrase:
                    errors.append("Missing BITGET_PASSPHRASE")
            
            # Validate trading parameters
            if self.trading.position_size_usdt <= 0:
                errors.append("Position size must be positive")
            if self.trading.leverage <= 0:
                errors.append("Leverage must be positive")
            if self.trading.max_positions <= 0:
                errors.append("Max positions must be positive")
            if not (0 < self.trading.stop_loss_percent < 100):
                errors.append("Stop loss must be between 0 and 100%")
            if not (0 < self.trading.take_profit_percent < 100):
                errors.append("Take profit must be between 0 and 100%")
            
            # Validate risk parameters
            if self.trading.max_daily_loss_usdt <= 0:
                errors.append("Max daily loss must be positive")
            if not (0 < self.trading.max_drawdown_percent < 100):
                errors.append("Max drawdown must be between 0 and 100%")
            
            if errors:
                raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
            
            logger.info("✅ Configuration validation passed")
            
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            raise

    def save_to_file(self):
        """Save current configuration to file"""
        try:
            config_data = {
                'trading': asdict(self.trading),
                'system': asdict(self.system)
            }
            
            # Convert enum to string
            config_data['system']['environment'] = self.system.environment.value
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"✅ Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving configuration: {e}")

    def update_trading_config(self, **kwargs):
        """Update trading configuration"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.trading, key):
                    setattr(self.trading, key, value)
                    logger.info(f"📝 Updated trading.{key} = {value}")
            
            self._validate_config()
            
        except Exception as e:
            logger.error(f"❌ Error updating trading config: {e}")
            raise

    def get_symbols_config(self) -> Dict[str, List[str]]:
        """Get trading symbols configuration"""
        return {
            'trading_symbols': [
                'XRPUSDT', 'ADAUSDT', 'XLMUSDT', 'UNIUSDT', 
                'ATOMUSDT', 'AXSUSDT', 'ARBUSDT'
            ],
            'analysis_only': [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'
            ]
        }

    def get_risk_profile(self) -> Dict[str, Any]:
        """Get current risk profile"""
        if self.trading.leverage <= 2 and self.trading.max_positions <= 1:
            risk_level = RiskLevel.CONSERVATIVE
        elif self.trading.leverage <= 5 and self.trading.max_positions <= 3:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.AGGRESSIVE
        
        return {
            'risk_level': risk_level.value,
            'position_size': self.trading.position_size_usdt,
            'leverage': self.trading.leverage,
            'max_positions': self.trading.max_positions,
            'stop_loss': self.trading.stop_loss_percent,
            'take_profit': self.trading.take_profit_percent,
            'max_daily_loss': self.trading.max_daily_loss_usdt
        }

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.system.environment == Environment.PRODUCTION

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self.system.debug_mode

    def _is_cloud_environment(self) -> bool:
        """Detect if running in a cloud environment like Streamlit Cloud"""
        cloud_indicators = [
            'STREAMLIT_CLOUD' in os.environ,
            'STREAMLIT_SHARING' in os.environ,
            os.environ.get('USER') == 'appuser',  # Common cloud user
            'streamlit.io' in os.environ.get('HOME', ''),
            'HOSTNAME' in os.environ and 'streamlit' in os.environ.get('HOSTNAME', '').lower()
        ]
        return any(cloud_indicators)

# Global configuration instance
config = ConfigManager()

def validate_config() -> bool:
    """Validate the global configuration"""
    try:
        config._validate_config()
        return True
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False
