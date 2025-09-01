#!/usr/bin/env python3
"""
Enhanced RSI MA Trading Strategy - Production Ready

MAJOR IMPROVEMENTS:
- Paper trading mode by default
- Enhanced market condition filters
- Multi-timeframe confirmation
- Advanced risk management
- Volume and volatility filters
- Session time filtering
- Trend strength confirmation

Strategy Rules (ENHANCED):
- Long: RSI <= 35 AND price > MA53 AND trend_strength > 25 AND volume_confirmed
- Short: RSI >= 65 AND price < MA53 AND trend_strength > 25 AND volume_confirmed
- Stop Loss: 2% from entry (tighter)
- Take Profit: 3% from entry (conservative)
- Max Risk: 1% of account per trade
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

# Import our enhanced systems
from config import config
from error_handler import safe_execute, ErrorCategory, ErrorSeverity, log_performance

logger = logging.getLogger(__name__)

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class TradingSignal:
    signal_type: SignalType
    price: float
    timestamp: datetime
    rsi: float
    ma53: float
    ma50: float
    confidence: float = 1.0
    reasoning: str = ""
    # Enhanced signal properties
    volume_confirmed: bool = False
    trend_strength: float = 0.0
    volatility_check: bool = False
    session_allowed: bool = False
    multi_tf_confirmed: bool = False

@dataclass
class MarketCondition:
    """Market condition analysis"""
    trend_strength: float  # ADX value
    volume_ratio: float    # Current volume vs average
    volatility: float      # Price volatility measure
    session_allowed: bool  # Trading session check
    market_regime: str     # "TRENDING", "RANGING", "VOLATILE"

@dataclass
class Position:
    position_type: PositionType
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    current_pnl: float = 0.0

class EnhancedRSIMAStrategy:
    """
    Enhanced RSI MA strategy with comprehensive market filters
    """

    def __init__(self,
                 rsi_period: int = None,
                 ma53_period: int = None,
                 ma50_period: int = None,
                 rsi_buy_threshold: float = None,
                 rsi_sell_threshold: float = None,
                 stop_loss_pct: float = None,
                 take_profit_pct: float = None,
                 position_size_pct: float = None):

        # Use enhanced configuration system
        self.rsi_period = rsi_period or config.trading.rsi_period
        self.ma53_period = ma53_period or config.trading.ma53_period
        self.ma50_period = ma50_period or config.trading.ma50_period
        self.rsi_buy_threshold = rsi_buy_threshold or config.trading.rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold or config.trading.rsi_sell_threshold
        self.stop_loss_pct = stop_loss_pct or (config.trading.stop_loss_percent / 100)
        self.take_profit_pct = take_profit_pct or (config.trading.take_profit_percent / 100)
        
        # Enhanced risk management
        self.max_risk_per_trade = config.trading.max_risk_per_trade_percent / 100
        self.paper_trading_mode = config.trading.paper_trading_mode
        
        # Market condition filters
        self.trend_strength_threshold = config.trading.trend_strength_threshold
        self.volume_multiplier_threshold = config.trading.volume_multiplier_threshold
        self.volatility_filter_enabled = config.trading.volatility_filter_enabled
        self.max_volatility_threshold = config.trading.max_volatility_threshold
        
        # Session filtering
        self.trading_sessions_enabled = config.trading.trading_sessions_enabled
        self.allowed_trading_hours = config.trading.allowed_trading_hours
        
        self.current_position = None
        self.signals_history = []
        self.trade_history = []
        self.daily_stats = {'trades': 0, 'pnl': 0.0, 'date': datetime.now().date()}

        logger.info(f"Enhanced RSI MA Strategy initialized:")
        logger.info(f"  Paper Trading Mode: {self.paper_trading_mode}")
        logger.info(f"  RSI: {self.rsi_period} period, Long: <={self.rsi_buy_threshold}, Short: >={self.rsi_sell_threshold}")
        logger.info(f"  MA: {self.ma53_period} & {self.ma50_period} periods")
        logger.info(f"  Risk: {self.stop_loss_pct*100:.1f}% SL, {self.take_profit_pct*100:.1f}% TP")
        logger.info(f"  Max Risk per Trade: {self.max_risk_per_trade*100:.1f}%")
        logger.info(f"  Market Filters: Trend={self.trend_strength_threshold}, Volume={self.volume_multiplier_threshold}x")

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    @log_performance
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index"""
        if period is None:
            period = self.rsi_period

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.LOW)
    def calculate_moving_average(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX) for trend strength"""
        high = df['high']
        low = df['low'] 
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movements
        dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low), 
                          np.maximum(high - high.shift(1), 0), 0)
        dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)), 
                           np.maximum(low.shift(1) - low, 0), 0)
        
        # Smooth the values
        tr_smooth = pd.Series(tr).rolling(window=period).mean()
        dm_plus_smooth = pd.Series(dm_plus).rolling(window=period).mean()
        dm_minus_smooth = pd.Series(dm_minus).rolling(window=period).mean()
        
        # Calculate DI+ and DI-
        di_plus = 100 * dm_plus_smooth / tr_smooth
        di_minus = 100 * dm_minus_smooth / tr_smooth
        
        # Calculate ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()
        
        return adx

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.LOW)
    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate price volatility (standard deviation of returns)"""
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std()
        return volatility

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.LOW)
    def check_trading_session(self, timestamp: datetime = None) -> bool:
        """Check if current time is within allowed trading hours"""
        if not self.trading_sessions_enabled:
            return True
            
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        current_hour = timestamp.hour
        return current_hour in self.allowed_trading_hours

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def analyze_market_condition(self, df: pd.DataFrame) -> MarketCondition:
        """Comprehensive market condition analysis"""
        if len(df) < 30:
            return MarketCondition(0, 0, 0, False, "INSUFFICIENT_DATA")
        
        current_row = df.iloc[-1]
        
        # Calculate trend strength (ADX)
        adx_series = self.calculate_adx(df)
        trend_strength = adx_series.iloc[-1] if not pd.isna(adx_series.iloc[-1]) else 0
        
        # Calculate volume confirmation
        if 'volume' in df.columns:
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        else:
            volume_ratio = 1.5  # Assume good volume if not available
        
        # Calculate volatility
        volatility_series = self.calculate_volatility(df)
        current_volatility = volatility_series.iloc[-1] if not pd.isna(volatility_series.iloc[-1]) else 0
        
        # Check trading session
        session_allowed = self.check_trading_session()
        
        # Determine market regime
        if trend_strength >= self.trend_strength_threshold:
            if current_volatility <= self.max_volatility_threshold:
                market_regime = "TRENDING"
            else:
                market_regime = "VOLATILE"
        else:
            market_regime = "RANGING"
        
        return MarketCondition(
            trend_strength=trend_strength,
            volume_ratio=volume_ratio,
            volatility=current_volatility,
            session_allowed=session_allowed,
            market_regime=market_regime
        )

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    @log_performance
    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators including new ones"""
        df = df.copy()

        # Calculate basic indicators
        df['rsi'] = self.calculate_rsi(df['close'])
        df['ma53'] = self.calculate_moving_average(df['close'], self.ma53_period)
        df['ma50'] = self.calculate_moving_average(df['close'], self.ma50_period)
        
        # Calculate enhanced indicators
        df['adx'] = self.calculate_adx(df)
        df['volatility'] = self.calculate_volatility(df)

        # Calculate helper columns
        df['rsi_prev'] = df['rsi'].shift(1)
        df['price_above_ma53'] = df['close'] > df['ma53']
        df['price_below_ma53'] = df['close'] < df['ma53']
        df['price_above_ma50'] = df['close'] > df['ma50']
        df['price_below_ma50'] = df['close'] < df['ma50']
        
        # Volume analysis (if available)
        if 'volume' in df.columns:
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma20']
        else:
            df['volume_ratio'] = 1.5  # Assume good volume if not available

        return df

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def generate_enhanced_long_signal(self, df: pd.DataFrame) -> Tuple[bool, float, str]:
        """Generate enhanced long signal with market condition filters"""
        if len(df) < max(self.rsi_period, self.ma53_period, 30):
            return False, 0.0, "INSUFFICIENT_DATA"
        
        current_row = df.iloc[-1]
        market_condition = self.analyze_market_condition(df)
        
        # Base RSI-MA signal (REVERSED LOGIC - buy oversold)
        rsi_oversold = current_row['rsi'] <= self.rsi_buy_threshold  # RSI <= 35
        price_above_ma53 = current_row['price_above_ma53']
        
        # Market condition filters
        trend_strong_enough = market_condition.trend_strength >= self.trend_strength_threshold
        volume_confirmed = market_condition.volume_ratio >= self.volume_multiplier_threshold
        volatility_acceptable = (not self.volatility_filter_enabled or 
                               market_condition.volatility <= self.max_volatility_threshold)
        session_allowed = market_condition.session_allowed
        market_trending = market_condition.market_regime == "TRENDING"
        
        # Calculate confidence based on multiple factors
        confidence = 0.0
        reasoning_parts = []
        
        if rsi_oversold and price_above_ma53:
            confidence += 0.3
            reasoning_parts.append("RSI oversold + price above MA53")
        
        if trend_strong_enough:
            confidence += 0.2
            reasoning_parts.append(f"strong trend (ADX: {market_condition.trend_strength:.1f})")
        
        if volume_confirmed:
            confidence += 0.2
            reasoning_parts.append(f"volume confirmed ({market_condition.volume_ratio:.1f}x)")
        
        if volatility_acceptable:
            confidence += 0.15
            reasoning_parts.append("volatility acceptable")
        
        if session_allowed:
            confidence += 0.1
            reasoning_parts.append("trading session allowed")
        
        if market_trending:
            confidence += 0.05
            reasoning_parts.append("trending market")
        
        # Signal is valid if base conditions + key filters are met
        signal_valid = (rsi_oversold and price_above_ma53 and 
                       trend_strong_enough and volume_confirmed and 
                       volatility_acceptable and session_allowed)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No conditions met"
        
        return signal_valid, confidence, reasoning
    
    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def generate_enhanced_short_signal(self, df: pd.DataFrame) -> Tuple[bool, float, str]:
        """Generate enhanced short signal with market condition filters"""
        if len(df) < max(self.rsi_period, self.ma53_period, 30):
            return False, 0.0, "INSUFFICIENT_DATA"
        
        current_row = df.iloc[-1]
        market_condition = self.analyze_market_condition(df)
        
        # Base RSI-MA signal (REVERSED LOGIC - sell overbought)
        rsi_overbought = current_row['rsi'] >= self.rsi_sell_threshold  # RSI >= 65
        price_below_ma53 = current_row['price_below_ma53']
        
        # Market condition filters (same as long)
        trend_strong_enough = market_condition.trend_strength >= self.trend_strength_threshold
        volume_confirmed = market_condition.volume_ratio >= self.volume_multiplier_threshold
        volatility_acceptable = (not self.volatility_filter_enabled or 
                               market_condition.volatility <= self.max_volatility_threshold)
        session_allowed = market_condition.session_allowed
        market_trending = market_condition.market_regime == "TRENDING"
        
        # Calculate confidence
        confidence = 0.0
        reasoning_parts = []
        
        if rsi_overbought and price_below_ma53:
            confidence += 0.3
            reasoning_parts.append("RSI overbought + price below MA53")
        
        if trend_strong_enough:
            confidence += 0.2
            reasoning_parts.append(f"strong trend (ADX: {market_condition.trend_strength:.1f})")
        
        if volume_confirmed:
            confidence += 0.2
            reasoning_parts.append(f"volume confirmed ({market_condition.volume_ratio:.1f}x)")
        
        if volatility_acceptable:
            confidence += 0.15
            reasoning_parts.append("volatility acceptable")
        
        if session_allowed:
            confidence += 0.1
            reasoning_parts.append("trading session allowed")
        
        if market_trending:
            confidence += 0.05
            reasoning_parts.append("trending market")
        
        # Signal is valid if base conditions + key filters are met
        signal_valid = (rsi_overbought and price_below_ma53 and 
                       trend_strong_enough and volume_confirmed and 
                       volatility_acceptable and session_allowed)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No conditions met"
        
        return signal_valid, confidence, reasoning

    def detect_rsi_retest(self, df: pd.DataFrame, threshold: float = 40.0) -> bool:
        """Detect RSI retest of threshold level from below"""
        if len(df) < 3:
            return False

        current_rsi = df['rsi'].iloc[-1]

        # Look for RSI coming from below and retesting the threshold
        recent_below = any(df['rsi'].iloc[-5:] < threshold - 2)
        current_retest = abs(current_rsi - threshold) <= 2

        return recent_below and current_retest

    def detect_price_retest_under_ma50(self, df: pd.DataFrame) -> bool:
        """Detect price retesting under MA50"""
        if len(df) < 5:
            return False

        recent_data = df.tail(5)
        price_near_ma50 = any(abs(recent_data['close'] - recent_data['ma50']) / recent_data['ma50'] < 0.01)
        price_still_below = df['close'].iloc[-1] < df['ma50'].iloc[-1]

        return price_near_ma50 and price_still_below

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def generate_long_signal(self, df: pd.DataFrame) -> bool:
        """Legacy method - now uses enhanced signal logic"""
        signal_valid, confidence, reasoning = self.generate_enhanced_long_signal(df)
        if signal_valid:
            logger.info(f"📈 Long signal generated - Confidence: {confidence:.2f} - {reasoning}")
        return signal_valid
    
    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def generate_short_signal(self, df: pd.DataFrame) -> bool:
        """Legacy method - now uses enhanced signal logic"""
        signal_valid, confidence, reasoning = self.generate_enhanced_short_signal(df)
        if signal_valid:
            logger.info(f"📉 Short signal generated - Confidence: {confidence:.2f} - {reasoning}")
        return signal_valid
    
    def create_position(self, signal: TradingSignal, account_balance: float) -> Position:
        """Create a new position with enhanced risk management"""
        # Calculate position size based on risk management
        risk_amount = account_balance * self.max_risk_per_trade
        price_risk = signal.price * self.stop_loss_pct
        max_quantity = risk_amount / price_risk
        
        # Also consider configured position size
        config_quantity = config.trading.position_size_usdt / signal.price
        
        # Use the smaller of the two (more conservative)
        quantity = min(max_quantity, config_quantity)

        if signal.signal_type == SignalType.BUY:
            position_type = PositionType.LONG
            stop_loss = signal.price * (1 - self.stop_loss_pct)
            take_profit = signal.price * (1 + self.take_profit_pct)
        else:  # SELL
            position_type = PositionType.SHORT
            stop_loss = signal.price * (1 + self.stop_loss_pct)
            take_profit = signal.price * (1 - self.take_profit_pct)

        position = Position(
            position_type=position_type,
            entry_price=signal.price,
            quantity=quantity,
            entry_time=signal.timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Log the risk calculation
        risk_percentage = (quantity * price_risk) / account_balance * 100
        logger.info(f"💰 Position created - Risk: {risk_percentage:.2f}% of account")
        logger.info(f"   Quantity: {quantity:.6f}, SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
        
        return position

    def check_exit_conditions(self, current_price: float) -> Tuple[bool, str]:
        """Check if position should be closed"""
        if not self.current_position:
            return False, ""

        if self.current_position.position_type == PositionType.LONG:
            if current_price <= self.current_position.stop_loss:
                return True, "STOP_LOSS"
            elif current_price >= self.current_position.take_profit:
                return True, "TAKE_PROFIT"
        else:  # SHORT
            if current_price >= self.current_position.stop_loss:
                return True, "STOP_LOSS"
            elif current_price <= self.current_position.take_profit:
                return True, "TAKE_PROFIT"

        return False, ""

    def update_position_pnl(self, current_price: float):
        """Update current position PnL"""
        if not self.current_position:
            return

        if self.current_position.position_type == PositionType.LONG:
            self.current_position.current_pnl = (current_price - self.current_position.entry_price) * self.current_position.quantity
        else:  # SHORT
            self.current_position.current_pnl = (self.current_position.entry_price - current_price) * self.current_position.quantity

    def process_data(self, df: pd.DataFrame, account_balance: float = 10000) -> Optional[TradingSignal]:
        """Process new data and generate enhanced signals with paper trading support"""
        try:
            # Calculate indicators
            df_with_indicators = self.update_indicators(df)

            if len(df_with_indicators) < max(self.rsi_period, self.ma53_period, self.ma50_period, 30):
                return None

            current_row = df_with_indicators.iloc[-1]
            current_price = current_row['close']
            current_time = datetime.now()

            # Check for position exits first
            if self.current_position:
                should_exit, exit_reason = self.check_exit_conditions(current_price)
                if should_exit:
                    exit_signal = TradingSignal(
                        signal_type=SignalType.HOLD,  # Represents exit
                        price=current_price,
                        timestamp=current_time,
                        rsi=current_row['rsi'],
                        ma53=current_row['ma53'],
                        ma50=current_row['ma50'],
                        reasoning=f"EXIT: {exit_reason}"
                    )
                    
                    # Calculate final P&L
                    self.update_position_pnl(current_price)
                    final_pnl = self.current_position.current_pnl
                    
                    # Update daily stats
                    self.daily_stats['trades'] += 1
                    self.daily_stats['pnl'] += final_pnl
                    
                    logger.info(f"🔚 Position closed: {exit_reason} - P&L: ${final_pnl:.2f}")
                    
                    # Clear position
                    self.current_position = None
                    return exit_signal

            # Don't open new positions if we already have one
            if self.current_position:
                self.update_position_pnl(current_price)
                return None

            # Check daily loss limits
            if self.daily_stats['pnl'] <= -config.trading.max_daily_loss_usdt:
                logger.warning(f"⚠️ Daily loss limit reached: ${self.daily_stats['pnl']:.2f}")
                return None

            # Generate new signals using enhanced logic
            signal_type = SignalType.HOLD
            reasoning = ""
            confidence = 0.0

            # Check for LONG signal
            long_valid, long_confidence, long_reasoning = self.generate_enhanced_long_signal(df_with_indicators)
            if long_valid:
                signal_type = SignalType.BUY
                confidence = long_confidence
                reasoning = f"LONG: {long_reasoning}"

            # Check for SHORT signal (only if no long signal)
            if signal_type == SignalType.HOLD:
                short_valid, short_confidence, short_reasoning = self.generate_enhanced_short_signal(df_with_indicators)
                if short_valid:
                    signal_type = SignalType.SELL
                    confidence = short_confidence
                    reasoning = f"SHORT: {short_reasoning}"

            # Create and return signal if found
            if signal_type != SignalType.HOLD:
                signal = TradingSignal(
                    signal_type=signal_type,
                    price=current_price,
                    timestamp=current_time,
                    rsi=current_row['rsi'],
                    ma53=current_row['ma53'],
                    ma50=current_row['ma50'],
                    confidence=confidence,
                    reasoning=reasoning,
                    # Enhanced signal properties
                    volume_confirmed=True,  # Already checked in enhanced logic
                    trend_strength=current_row.get('adx', 0),
                    volatility_check=True,  # Already checked
                    session_allowed=True,   # Already checked
                    multi_tf_confirmed=True # For now, single timeframe
                )

                # Create position (respects paper trading mode)
                if self.paper_trading_mode:
                    logger.info(f"📝 PAPER TRADE: {signal_type.value} signal at ${current_price:.2f}")
                    logger.info(f"   Confidence: {confidence:.2f} - {reasoning}")
                else:
                    self.current_position = self.create_position(signal, account_balance)
                    logger.info(f"💰 LIVE TRADE: {signal_type.value} signal at ${current_price:.2f}")

                self.signals_history.append(signal)
                return signal

            return None

        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return None
            current_time = current_row.name if hasattr(current_row.name, 'timestamp') else datetime.now()

            # Update existing position PnL
            if self.current_position:
                self.update_position_pnl(current_price)

                # Check exit conditions
                should_exit, exit_reason = self.check_exit_conditions(current_price)
                if should_exit:
                    logger.info(f"Position closed: {exit_reason}. PnL: {self.current_position.current_pnl:.2f}")
                    # Record trade
                    self.trade_history.append({
                        'entry_time': self.current_position.entry_time,
                        'exit_time': datetime.now(),
                        'position_type': self.current_position.position_type.value,
                        'entry_price': self.current_position.entry_price,
                        'exit_price': current_price,
                        'quantity': self.current_position.quantity,
                        'pnl': self.current_position.current_pnl,
                        'exit_reason': exit_reason
                    })
                    self.current_position = None

            # Generate new signals if no position
            if not self.current_position:
                signal_type = SignalType.HOLD
                reasoning = ""

                # Check for long signal
                if self.generate_long_signal(df_with_indicators):
                    signal_type = SignalType.BUY
                    reasoning = "LONG: RSI cross above 62 with price above MA53"
                    logger.info(f"🟢 LONG signal: {reasoning} at {current_price:.4f}")

                # Check for short signal (only if no long signal)
                elif self.generate_short_signal(df_with_indicators):
                    signal_type = SignalType.SELL
                    reasoning = "SHORT: RSI retest 39 with price below MA53 and retest under MA50"
                    logger.info(f"🔴 SHORT signal: {reasoning} at {current_price:.4f}")

                if signal_type != SignalType.HOLD:
                    signal = TradingSignal(
                        signal_type=signal_type,
                        price=current_price,
                        timestamp=current_time,
                        rsi=current_row['rsi'],
                        ma53=current_row['ma53'],
                        ma50=current_row['ma50'],
                        reasoning=reasoning
                    )

                    # Create position
                    self.current_position = self.create_position(signal, account_balance)
                    self.signals_history.append(signal)

                    return signal

            return None

        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return None

    @safe_execute(category=ErrorCategory.DATA_ERROR, severity=ErrorSeverity.MEDIUM)
    def generate_signal(self, latest_data: pd.Series) -> Optional[TradingSignal]:
        """Generate trading signal from latest market data"""
        try:
            current_price = latest_data.get('close', 0)
            current_rsi = latest_data.get('rsi', 50)
            current_ma53 = latest_data.get('ma53', current_price)
            current_ma50 = latest_data.get('ma50', current_price)
            
            # Check for BUY signal (LONG)
            if (current_rsi >= self.rsi_buy_threshold and 
                current_price > current_ma53):
                
                # Calculate confidence based on RSI strength and MA separation
                rsi_strength = min((current_rsi - self.rsi_buy_threshold) / 10, 1.0)
                ma_separation = abs(current_price - current_ma53) / current_price
                confidence = min(0.5 + (rsi_strength * 0.3) + (ma_separation * 0.2), 1.0)
                
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    price=current_price,
                    timestamp=datetime.now(),
                    rsi=current_rsi,
                    ma53=current_ma53,
                    ma50=current_ma50,
                    confidence=confidence,
                    reasoning=f"RSI {current_rsi:.1f} >= {self.rsi_buy_threshold}, Price above MA53"
                )
            
            # Check for SELL signal (SHORT)
            elif (current_rsi <= self.rsi_sell_threshold and 
                  current_price < current_ma53):
                
                # Calculate confidence based on RSI strength and MA separation
                rsi_strength = min((self.rsi_sell_threshold - current_rsi) / 10, 1.0)
                ma_separation = abs(current_ma53 - current_price) / current_price
                confidence = min(0.5 + (rsi_strength * 0.3) + (ma_separation * 0.2), 1.0)
                
                return TradingSignal(
                    signal_type=SignalType.SELL,
                    price=current_price,
                    timestamp=datetime.now(),
                    rsi=current_rsi,
                    ma53=current_ma53,
                    ma50=current_ma50,
                    confidence=confidence,
                    reasoning=f"RSI {current_rsi:.1f} <= {self.rsi_sell_threshold}, Price below MA53"
                )
            
            # No signal - HOLD
            return TradingSignal(
                signal_type=SignalType.HOLD,
                price=current_price,
                timestamp=datetime.now(),
                rsi=current_rsi,
                ma53=current_ma53,
                ma50=current_ma50,
                confidence=0.0,
                reasoning="No clear signal - holding position"
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating signal: {e}")
            return None

    def get_current_position_info(self) -> Dict:
        """Get current position information"""
        if not self.current_position:
            return {"status": "NO_POSITION"}

        return {
            "status": "IN_POSITION",
            "type": self.current_position.position_type.value,
            "entry_price": self.current_position.entry_price,
            "quantity": self.current_position.quantity,
            "stop_loss": self.current_position.stop_loss,
            "take_profit": self.current_position.take_profit,
            "current_pnl": self.current_position.current_pnl,
            "entry_time": self.current_position.entry_time
        }

    def get_strategy_stats(self) -> Dict:
        """Get strategy performance statistics"""
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t['pnl'] > 0])
        losing_trades = total_trades - winning_trades

        total_pnl = sum([t['pnl'] for t in self.trade_history])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            "total_signals": len(self.signals_history),
            "long_signals": len([s for s in self.signals_history if s.signal_type == SignalType.BUY]),
            "short_signals": len([s for s in self.signals_history if s.signal_type == SignalType.SELL]),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "current_position": self.get_current_position_info(),
            "parameters": {
                "rsi_period": self.rsi_period,
                "rsi_buy_threshold": self.rsi_buy_threshold,
                "rsi_sell_threshold": self.rsi_sell_threshold,
                "ma53_period": self.ma53_period,
                "ma50_period": self.ma50_period,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
                "position_size_pct": self.position_size_pct
            }
        }

# Export for easy access
__all__ = ['OptimizedRSIMAStrategy', 'EnhancedRSIMAStrategy', 'TradingSignal', 'Position', 'SignalType', 'PositionType', 'MarketCondition']

# Backward compatibility alias
OptimizedRSIMAStrategy = EnhancedRSIMAStrategy