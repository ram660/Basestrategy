#!/usr/bin/env python3
"""
Data Fetcher for RSI MA Trading Strategy

Simple data fetching utilities for cryptocurrency price data
Supports both Binance and Bitget APIs
"""

import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str

class BitgetDataFetcher:
    """Simple Bitget data fetcher for public market data"""

    def __init__(self):
        self.base_url = "https://api.bitget.com"

    def fetch_kline_data(self, symbol: str, interval: str = '5m', limit: int = 200) -> pd.DataFrame:
        """
        Fetch kline data from Bitget API

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Time interval ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            limit: Number of data points to fetch (max 1000)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert interval format for Bitget API v2
            interval_map = {
                '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
                '1h': '1h', '4h': '4h', '1d': '1day'
            }

            bitget_interval = interval_map.get(interval, '5min')

            # Bitget spot API v2 endpoint for klines
            url = f"{self.base_url}/api/v2/spot/market/candles"
            params = {
                'symbol': symbol,
                'granularity': bitget_interval,
                'limit': limit
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != '00000' or not result.get('data'):
                logger.warning(f"⚠️ No data received for {symbol}: {result.get('msg', 'Unknown error')}")
                return pd.DataFrame()

            data = result['data']

            # Convert to DataFrame - Bitget format: [timestamp, open, high, low, close, volume, quoteVolume, usdtVolume]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'usdt_volume'
            ])

            # Convert data types
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp'], errors='coerce'), unit='ms')
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].astype(float)

            # Keep only OHLCV columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            logger.info(f"✅ Fetched {len(df)} candles for {symbol} {interval}")
            return df

        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            url = f"{self.base_url}/api/v2/spot/market/tickers"
            params = {'symbol': symbol}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != '00000' or not result.get('data'):
                logger.warning(f"⚠️ No price data received for {symbol}")
                return None

            # Bitget returns an array of tickers, get the first one
            ticker_data = result['data'][0] if result['data'] else None
            if not ticker_data:
                logger.warning(f"⚠️ No ticker data for {symbol}")
                return None

            return float(ticker_data['lastPr'])

        except Exception as e:
            logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return None

class DataProcessor:
    """Data processing utilities for trading strategy"""

    def __init__(self):
        self.data_cache = {}

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate OHLCV data"""
        if df.empty:
            return False

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logger.error("Missing required OHLCV columns")
            return False

        # Check for null values
        if df[required_columns].isnull().any().any():
            logger.warning("Found null values in OHLCV data")

        # Basic price validation
        invalid_prices = (df['high'] < df['low']) | (df['close'] < 0) | (df['volume'] < 0)
        if invalid_prices.any():
            logger.warning(f"Found {invalid_prices.sum()} invalid price records")

        return True

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for analysis"""
        df_clean = df.copy()

        # Remove null values
        df_clean = df_clean.dropna()

        # Remove invalid prices
        df_clean = df_clean[
            (df_clean['high'] >= df_clean['low']) &
            (df_clean['close'] > 0) &
            (df_clean['volume'] >= 0)
        ]

        # Sort by timestamp
        df_clean = df_clean.sort_index()

        # Add technical indicators (RSI, MA53, MA50)
        from rsi_ma_strategy import OptimizedRSIMAStrategy
        strategy = OptimizedRSIMAStrategy()
        df_clean = strategy.update_indicators(df_clean)

        return df_clean

    def get_latest_data(self, symbol: str, interval: str = '5m', periods: int = 200) -> pd.DataFrame:
        """Get latest cleaned and processed data for a symbol"""
        fetcher = BitgetDataFetcher()

        # Fetch raw data
        raw_data = fetcher.fetch_kline_data(symbol=symbol, interval=interval, limit=periods)

        if raw_data.empty:
            logger.error(f"No data fetched for {symbol}")
            return pd.DataFrame()

        # Validate and clean data
        if not self.validate_data(raw_data):
            logger.error(f"Data validation failed for {symbol}")
            return pd.DataFrame()

        cleaned_data = self.clean_data(raw_data)

        # Cache the data
        self.data_cache[symbol] = {
            'data': cleaned_data,
            'last_update': datetime.now()
        }

        logger.info(f"✅ Processed {len(cleaned_data)} data points for {symbol}")
        return cleaned_data

    def get_cached_data(self, symbol: str, max_age_minutes: int = 5) -> Optional[pd.DataFrame]:
        """Get cached data if available and not too old"""
        if symbol not in self.data_cache:
            return None

        cache_entry = self.data_cache[symbol]
        age = datetime.now() - cache_entry['last_update']

        if age.total_seconds() / 60 > max_age_minutes:
            return None

        return cache_entry['data']

# Utility functions for easy access
def get_crypto_data(symbol: str, interval: str = '5m', periods: int = 200) -> pd.DataFrame:
    """
    Simple function to get cryptocurrency data

    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        interval: Time interval ('1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d')
        periods: Number of data points to fetch

    Returns:
        DataFrame with OHLCV data
    """
    processor = DataProcessor()
    return processor.get_latest_data(symbol, interval, periods)

def get_current_price(symbol: str) -> Optional[float]:
    """
    Simple function to get current price

    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')

    Returns:
        Current price as float
    """
    fetcher = BitgetDataFetcher()
    return fetcher.get_current_price(symbol)

def get_historical_data(symbol: str, interval: str = '5m', periods: int = 100) -> Optional[pd.DataFrame]:
    """
    Get historical data for strategy analysis
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        interval: Time interval ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
        periods: Number of periods to fetch
    
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        return get_crypto_data(symbol, interval, periods)
    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {e}")
        return None

# Export for easy access
__all__ = ['BinanceDataFetcher', 'DataProcessor', 'PriceData', 'get_crypto_data', 'get_current_price', 'get_historical_data']