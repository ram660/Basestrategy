#!/usr/bin/env python3
"""
RSI-MA Trading Bot - Streamlit Dashboard
Live Trading Dashboard with Telegram Integration
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os

# Import our core modules
from rsi_ma_strategy import OptimizedRSIMAStrategy
from bitget_futures_trader import BitgetFuturesTrader
from data_fetcher import get_current_price, get_historical_data
from telegram_notifier import telegram_notifier

# Import our enhanced systems
from config import config
from error_handler import safe_execute, ErrorCategory, ErrorSeverity
from trade_logger import trade_logger

# Configure environment variables for Streamlit Cloud
def setup_environment():
    """Setup environment variables from Streamlit secrets or .env"""
    try:
        # Try to use Streamlit secrets first (for cloud deployment)
        if hasattr(st, 'secrets') and st.secrets:
            st.write("🔧 Loading configuration from Streamlit Cloud secrets...")
            for key in st.secrets:
                os.environ[key] = str(st.secrets[key])
            st.write("✅ Secrets loaded successfully")
        else:
            st.write("🔧 Loading configuration from .env file...")
            # Fallback to .env file (for local development)
            from dotenv import load_dotenv
            load_dotenv()
            st.write("✅ .env file loaded successfully")
    except Exception as e:
        st.error(f"❌ Error loading configuration: {e}")
        st.write("Please check your Streamlit Cloud secrets or .env file configuration.")

# Setup environment
setup_environment()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="RSI-MA Trading Bot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .status-green { color: #28a745; font-weight: bold; }
    .status-red { color: #dc3545; font-weight: bold; }
    .status-yellow { color: #ffc107; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

class StreamlitTradingDashboard:
    """Main Streamlit Trading Dashboard - Cloud Ready for 24/7 Operation"""
    
    def __init__(self):
        self.strategy = OptimizedRSIMAStrategy()
        self.trader = BitgetFuturesTrader()
        self.symbols = config.get_symbols_config()['trading_symbols']
        self.trading_active = False
        
        # Detect cloud environment
        self.is_cloud = self._detect_cloud_environment()
        
        # Initialize session state
        if 'trading_enabled' not in st.session_state:
            st.session_state.trading_enabled = False
        if 'positions' not in st.session_state:
            st.session_state.positions = []
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
        if 'last_signal_check' not in st.session_state:
            st.session_state.last_signal_check = datetime.now()
        if 'signal_monitoring_active' not in st.session_state:
            st.session_state.signal_monitoring_active = False
        if 'auto_trading_active' not in st.session_state:
            st.session_state.auto_trading_active = False
        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = datetime.now()
        
        # Auto-start monitoring for cloud environment
        if self.is_cloud and config.get_trading_config()['environment'] == 'production':
            if not st.session_state.signal_monitoring_active:
                st.session_state.signal_monitoring_active = True
                logger.info("🚀 Auto-started signal monitoring for cloud environment")
    
    def _detect_cloud_environment(self) -> bool:
        """Detect if running on Streamlit Cloud"""
        # Common Streamlit Cloud environment indicators
        cloud_indicators = [
            'STREAMLIT_CLOUD' in os.environ,
            'STREAMLIT_SHARING' in os.environ,
            hasattr(st, 'secrets') and bool(st.secrets),
            os.environ.get('USER') == 'appuser',  # Common Streamlit Cloud user
            'streamlit' in os.environ.get('HOME', '').lower()
        ]
        return any(cloud_indicators)
    
    def check_api_status(self) -> Dict:
        """Check API connectivity and account status"""
        try:
            safety_ok, safety_msg = self.trader.check_account_safety()
            return {
                'status': 'connected' if safety_ok else 'error',
                'message': safety_msg,
                'balance': self.extract_balance_from_message(safety_msg)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"API Error: {str(e)}",
                'balance': 0.0
            }
    
    def extract_balance_from_message(self, message: str) -> float:
        """Extract balance from safety message"""
        try:
            if "Balance:" in message:
                balance_str = message.split("Balance: $")[1].split(",")[0]
                return float(balance_str)
        except:
            pass
        return 0.0
    
    def get_current_positions(self) -> List[Dict]:
        """Get current active positions"""
        try:
            return self.trader.get_active_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get current market data for a symbol"""
        try:
            price = get_current_price(symbol)
            df = get_historical_data(symbol, '5m', 100)
            
            if df is not None and len(df) > 53:
                df_with_indicators = self.strategy.update_indicators(df)
                current_row = df_with_indicators.iloc[-1]
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'rsi': current_row['rsi'],
                    'ma53': current_row['ma53'],
                    'ma50': current_row['ma50'],
                    'price_above_ma53': current_row['price_above_ma53'],
                    'signal': self.get_trading_signal(df_with_indicators)
                }
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
        
        return {
            'symbol': symbol,
            'price': 0.0,
            'rsi': 0.0,
            'ma53': 0.0,
            'ma50': 0.0,
            'price_above_ma53': False,
            'signal': 'NO_DATA'
        }
    
    def get_trading_signal(self, df: pd.DataFrame) -> str:
        """Get current trading signal"""
        try:
            if self.strategy.generate_long_signal(df):
                return 'LONG'
            elif self.strategy.generate_short_signal(df):
                return 'SHORT'
            else:
                return 'HOLD'
        except:
            return 'HOLD'
    
    def render_header(self):
        """Render main header"""
        st.markdown('<div class="main-header">📊 RSI-MA Trading Bot Dashboard</div>', unsafe_allow_html=True)
        
        # API Status
        api_status = self.check_api_status()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if api_status['status'] == 'connected':
                st.markdown('<p class="status-green">🟢 API Connected</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="status-red">🔴 API Error</p>', unsafe_allow_html=True)
        
        with col2:
            balance = api_status.get('balance', 0.0)
            st.metric("Account Balance", f"${balance:.2f}")
        
        with col3:
            positions = self.get_current_positions()
            st.metric("Active Positions", f"{len(positions)}/1")
        
        with col4:
            telegram_status = "🟢 Connected" if telegram_notifier.is_configured() else "🔴 Not Connected"
            st.markdown(f"**Telegram:** {telegram_status}")
    
    def render_trading_controls(self):
        """Render trading control panel"""
        st.subheader("🎮 Trading Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Enable Trading", type="primary" if not st.session_state.trading_enabled else "secondary"):
                if not st.session_state.trading_enabled:
                    self.trader.enable_trading()
                    st.session_state.trading_enabled = True
                    st.success("Trading enabled! Real trades will be executed.")
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_message("🚀 Trading enabled via dashboard!"))
        
        with col2:
            if st.button("🛑 Disable Trading", type="secondary" if not st.session_state.trading_enabled else "primary"):
                if st.session_state.trading_enabled:
                    self.trader.disable_trading()
                    st.session_state.trading_enabled = False
                    st.session_state.auto_trading_active = False  # Also disable auto-trading
                    st.warning("Trading disabled. No new trades will be executed.")
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_message("🛑 Trading disabled via dashboard."))
        
        with col3:
            if st.button("📱 Test Telegram"):
                if telegram_notifier.is_configured():
                    asyncio.run(telegram_notifier.send_message("📊 Dashboard test message - All systems operational!"))
                    st.success("Telegram test message sent!")
                else:
                    st.error("Telegram not configured. Check secrets.")
        
        # Trading status
        if st.session_state.trading_enabled:
            st.markdown('<p class="status-green">✅ Trading is ENABLED - Real trades will be executed</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-yellow">⚠️ Trading is DISABLED - Monitoring only</p>', unsafe_allow_html=True)
        
        # Add cloud monitoring controls
        st.divider()
        self.render_cloud_monitoring_controls()
    
    def render_market_overview(self):
        """Render market overview"""
        st.subheader("📈 Market Overview")
        
        market_data = []
        for symbol in self.symbols:
            data = self.get_market_data(symbol)
            market_data.append(data)
        
        if market_data:
            df = pd.DataFrame(market_data)
            
            # Create metrics display
            cols = st.columns(len(self.symbols))
            
            for i, (col, data) in enumerate(zip(cols, market_data)):
                with col:
                    signal_color = {
                        'LONG': '🟢',
                        'SHORT': '🔴', 
                        'HOLD': '🟡',
                        'NO_DATA': '⚪'
                    }.get(data['signal'], '⚪')
                    
                    st.metric(
                        label=f"{signal_color} {data['symbol']}",
                        value=f"${data['price']:.4f}",
                        delta=f"RSI: {data['rsi']:.1f}"
                    )
                    
                    if data['signal'] != 'NO_DATA':
                        st.caption(f"Signal: {data['signal']}")
            
            # Detailed table
            st.subheader("📊 Detailed Analysis")
            display_df = df[['symbol', 'price', 'rsi', 'ma53', 'ma50', 'signal']].copy()
            display_df['price'] = display_df['price'].apply(lambda x: f"${x:.4f}")
            display_df['rsi'] = display_df['rsi'].apply(lambda x: f"{x:.1f}")
            display_df['ma53'] = display_df['ma53'].apply(lambda x: f"${x:.4f}")
            display_df['ma50'] = display_df['ma50'].apply(lambda x: f"${x:.4f}")
            
            st.dataframe(display_df, use_container_width=True)
    
    def render_positions(self):
        """Render current positions"""
        st.subheader("💼 Current Positions")
        
        positions = self.get_current_positions()
        
        if positions:
            for pos in positions:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Symbol", pos.get('symbol', 'N/A'))
                
                with col2:
                    side = pos.get('side', 'N/A')
                    side_color = '🟢' if side == 'long' else '🔴' if side == 'short' else '⚪'
                    st.metric("Side", f"{side_color} {side.upper()}")
                
                with col3:
                    size = float(pos.get('size', 0))
                    st.metric("Size", f"{size:.4f}")
                
                with col4:
                    unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                    pnl_color = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
                    st.metric("PnL", f"{pnl_color} ${unrealized_pnl:.2f}")
        else:
            st.info("No active positions")
    
    def render_strategy_config(self):
        """Render strategy configuration"""
        st.subheader("⚙️ Strategy Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**RSI Parameters:**")
            st.info(f"• RSI Period: {self.strategy.rsi_period}")
            st.info(f"• Long Threshold: ≥{self.strategy.rsi_buy_threshold}")
            st.info(f"• Short Threshold: ≤{self.strategy.rsi_sell_threshold}")
        
        with col2:
            st.markdown("**Risk Management:**")
            st.info(f"• Position Size: ${self.trader.config.POSITION_SIZE_USDT} USDT")
            st.info(f"• Leverage: {self.trader.config.LEVERAGE}x")
            st.info(f"• Stop Loss: {self.trader.config.STOP_LOSS_PERCENT}%")
            st.info(f"• Take Profit: {self.trader.config.TAKE_PROFIT_PERCENT}%")
    
    @safe_execute(category=ErrorCategory.TRADING_ERROR, severity=ErrorSeverity.HIGH)
    def monitor_trading_signals(self):
        """Continuously monitor for trading signals - Cloud Ready"""
        try:
            if not st.session_state.signal_monitoring_active:
                return
            
            signals_found = []
            
            for symbol in self.symbols:
                try:
                    # Get market data
                    df = get_historical_data(symbol, '5m', 100)
                    if df is None or len(df) < 53:
                        continue
                    
                    # Update indicators
                    df_with_indicators = self.strategy.update_indicators(df)
                    
                    # Check for signals
                    long_signal = self.strategy.generate_long_signal(df_with_indicators)
                    short_signal = self.strategy.generate_short_signal(df_with_indicators)
                    
                    if long_signal or short_signal:
                        signal_type = 'LONG' if long_signal else 'SHORT'
                        current_price = get_current_price(symbol)
                        current_rsi = df_with_indicators['rsi'].iloc[-1]
                        
                        signal_data = {
                            'symbol': symbol,
                            'type': signal_type,
                            'price': current_price,
                            'rsi': current_rsi,
                            'timestamp': datetime.now(),
                            'confidence': self.calculate_signal_confidence(df_with_indicators)
                        }
                        
                        signals_found.append(signal_data)
                        
                        # Execute trade if auto-trading is enabled
                        if st.session_state.auto_trading_active and st.session_state.trading_enabled:
                            self.execute_signal(signal_data)
                        
                        # Send notification
                        if telegram_notifier.is_configured():
                            asyncio.run(self.send_signal_notification(signal_data))
                            
                except Exception as e:
                    logger.error(f"Error monitoring {symbol}: {e}")
                    continue
            
            # Update last check time
            st.session_state.last_signal_check = datetime.now()
            
            return signals_found
            
        except Exception as e:
            logger.error(f"Error in signal monitoring: {e}")
            return []
    
    def calculate_signal_confidence(self, df: pd.DataFrame) -> float:
        """Calculate signal confidence based on multiple factors"""
        try:
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            confidence = 0.5  # Base confidence
            
            # RSI trend confirmation
            if current_row['rsi'] > prev_row['rsi']:
                confidence += 0.1
            
            # Volume confirmation (if available)
            if 'volume' in df.columns:
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                if current_row['volume'] > avg_volume * 1.2:
                    confidence += 0.2
            
            # Price momentum
            price_change = (current_row['close'] - prev_row['close']) / prev_row['close']
            if abs(price_change) > 0.005:  # 0.5% price change
                confidence += 0.2
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    @safe_execute(category=ErrorCategory.TRADING_ERROR, severity=ErrorSeverity.CRITICAL)
    def execute_signal(self, signal_data: Dict):
        """Execute trading signal automatically"""
        try:
            if not self.trader.trading_enabled:
                return
            
            # Check if we already have a position for this symbol
            positions = self.get_current_positions()
            for pos in positions:
                if pos.get('symbol') == signal_data['symbol']:
                    logger.info(f"Position already exists for {signal_data['symbol']}, skipping")
                    return
            
            # Place order
            side = 'long' if signal_data['type'] == 'LONG' else 'short'
            position = self.trader.place_order_with_sl_tp(
                symbol=signal_data['symbol'],
                side=side,
                entry_price=signal_data['price'],
                confidence=signal_data['confidence']
            )
            
            if position:
                # Log the trade
                trade_id = trade_logger.log_trade_entry(
                    symbol=signal_data['symbol'],
                    side=side,
                    entry_price=signal_data['price'],
                    size=position.quantity,
                    leverage=config.trading.leverage,
                    margin=config.trading.position_size_usdt / config.trading.leverage,
                    order_id=position.position_id,
                    strategy="RSI_MA_AUTO",
                    confidence=signal_data['confidence'],
                    stop_loss=position.stop_loss,
                    take_profit=position.take_profit,
                    notes=f"Auto-executed signal at RSI {signal_data['rsi']:.1f}"
                )
                
                logger.info(f"✅ Auto-executed {side} signal for {signal_data['symbol']} at ${signal_data['price']:.4f}")
                
                # Send success notification
                if telegram_notifier.is_configured():
                    asyncio.run(telegram_notifier.notify_trade_entry(
                        signal_data['symbol'], side, signal_data['price'], signal_data['rsi']
                    ))
            else:
                logger.error(f"❌ Failed to execute signal for {signal_data['symbol']}")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def send_signal_notification(self, signal_data: Dict):
        """Send signal notification via Telegram"""
        try:
            message = f"""
🚨 **TRADING SIGNAL DETECTED**

📊 **Symbol:** {signal_data['symbol']}
{'🟢 **Signal:** LONG' if signal_data['type'] == 'LONG' else '🔴 **Signal:** SHORT'}
💰 **Price:** ${signal_data['price']:.4f}
📈 **RSI:** {signal_data['rsi']:.1f}
🎯 **Confidence:** {signal_data['confidence']*100:.1f}%
⏰ **Time:** {signal_data['timestamp'].strftime('%H:%M:%S')}

{'✅ Auto-trading: ENABLED' if st.session_state.auto_trading_active else '⚠️ Auto-trading: DISABLED'}
            """
            
            await telegram_notifier.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending signal notification: {e}")
    
    def render_cloud_monitoring_controls(self):
        """Render cloud monitoring controls for 24/7 operation"""
        st.subheader("☁️ Cloud Monitoring Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Start Signal Monitoring", type="primary" if not st.session_state.signal_monitoring_active else "secondary"):
                st.session_state.signal_monitoring_active = not st.session_state.signal_monitoring_active
                status = "started" if st.session_state.signal_monitoring_active else "stopped"
                st.success(f"Signal monitoring {status}!")
                
                if telegram_notifier.is_configured():
                    asyncio.run(telegram_notifier.send_message(f"🔍 Signal monitoring {status} via dashboard"))
        
        with col2:
            if st.button("🤖 Toggle Auto-Trading", type="primary" if not st.session_state.auto_trading_active else "secondary"):
                if st.session_state.trading_enabled:
                    st.session_state.auto_trading_active = not st.session_state.auto_trading_active
                    status = "enabled" if st.session_state.auto_trading_active else "disabled"
                    st.success(f"Auto-trading {status}!")
                    
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_message(f"🤖 Auto-trading {status} via dashboard"))
                else:
                    st.error("Enable trading first!")
        
        with col3:
            if st.button("📊 Check Signals Now"):
                with st.spinner("Checking for signals..."):
                    signals = self.monitor_trading_signals()
                    if signals:
                        st.success(f"Found {len(signals)} signals!")
                        for signal in signals:
                            st.write(f"• {signal['symbol']}: {signal['type']} at ${signal['price']:.4f}")
                    else:
                        st.info("No signals found at this time")
        
        # Status indicators
        st.markdown("### 📊 Cloud Status")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = "🟢 ACTIVE" if st.session_state.signal_monitoring_active else "🔴 INACTIVE"
            st.markdown(f"**Signal Monitoring:** {status}")
        
        with col2:
            status = "🟢 ENABLED" if st.session_state.auto_trading_active else "🔴 DISABLED"
            st.markdown(f"**Auto-Trading:** {status}")
        
        with col3:
            last_check = st.session_state.last_signal_check
            time_ago = (datetime.now() - last_check).total_seconds()
            st.markdown(f"**Last Check:** {int(time_ago)}s ago")
        
        with col4:
            uptime = datetime.now() - st.session_state.get('app_start_time', datetime.now())
            st.markdown(f"**Uptime:** {int(uptime.total_seconds()/3600)}h")

    def run(self):
        """Main dashboard runner - Enhanced for 24/7 cloud operation"""
        self.render_header()
        
        st.divider()
        
        # Main content in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎮 Controls", "📈 Market", "💼 Positions", "⚙️ Config", "📊 Logs"])
        
        with tab1:
            self.render_trading_controls()
        
        with tab2:
            self.render_market_overview()
            
            # Auto-monitor signals when monitoring is active
            if st.session_state.signal_monitoring_active:
                with st.container():
                    st.subheader("🔍 Live Signal Monitoring")
                    signals = self.monitor_trading_signals()
                    if signals:
                        st.success(f"🎯 {len(signals)} signals detected!")
                        for signal in signals:
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Symbol", signal['symbol'])
                            with col2:
                                signal_emoji = "🟢" if signal['type'] == 'LONG' else "🔴"
                                st.metric("Signal", f"{signal_emoji} {signal['type']}")
                            with col3:
                                st.metric("Price", f"${signal['price']:.4f}")
                            with col4:
                                st.metric("Confidence", f"{signal['confidence']*100:.1f}%")
                    else:
                        st.info("🔍 Monitoring active - No signals at this time")
        
        with tab3:
            self.render_positions()
        
        with tab4:
            self.render_strategy_config()
        
        with tab5:
            self.render_trade_logs()
        
        # Auto-refresh with different intervals based on monitoring status
        refresh_interval = 10 if st.session_state.signal_monitoring_active else 30
        if st.checkbox(f"🔄 Auto-refresh ({refresh_interval}s)", value=True):
            time.sleep(refresh_interval)
            st.rerun()
    
    def render_trade_logs(self):
        """Render trade logs and performance"""
        st.subheader("📊 Trade Logs & Performance")
        
        try:
            # Get performance stats
            stats = trade_logger.get_performance_stats()
            
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Trades", stats.get('total_trades', 0))
                
                with col2:
                    win_rate = stats.get('win_rate', 0)
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                
                with col3:
                    total_pnl = stats.get('total_pnl', 0)
                    pnl_color = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
                    st.metric("Total P&L", f"{pnl_color} ${total_pnl:.2f}")
                
                with col4:
                    avg_profit = stats.get('avg_profit', 0)
                    st.metric("Avg Profit", f"${avg_profit:.2f}")
                
                # Recent trades
                if hasattr(trade_logger, 'completed_trades') and trade_logger.completed_trades:
                    st.subheader("📈 Recent Trades")
                    recent_trades = trade_logger.completed_trades[-10:]  # Last 10 trades
                    
                    trade_data = []
                    for trade in recent_trades:
                        entry = trade['entry']
                        exit_data = trade['exit']
                        trade_data.append({
                            'Symbol': entry['symbol'],
                            'Side': entry['side'].upper(),
                            'Entry Price': f"${entry['entry_price']:.4f}",
                            'Exit Price': f"${exit_data['exit_price']:.4f}",
                            'P&L': f"${exit_data['pnl']:.2f}",
                            'Reason': exit_data['exit_reason'],
                            'Time': entry['timestamp'][:19].replace('T', ' ')
                        })
                    
                    if trade_data:
                        df = pd.DataFrame(trade_data)
                        st.dataframe(df, use_container_width=True)
            else:
                st.info("No trade data available yet")
                
        except Exception as e:
            st.error(f"Error loading trade logs: {e}")
            logger.error(f"Error in render_trade_logs: {e}")

# Main application
def main():
    """Main function - Enhanced for cloud deployment"""
    try:
        # Initialize app start time
        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = datetime.now()
        
        st.write("🚀 Initializing RSI-MA Trading Dashboard...")
        dashboard = StreamlitTradingDashboard()
        st.write("✅ Dashboard initialized successfully")
        
        # Auto-start signal monitoring in cloud environment
        if config.system.environment.value == 'production' and not st.session_state.get('auto_monitor_started', False):
            st.session_state.signal_monitoring_active = True
            st.session_state.auto_monitor_started = True
            st.info("🔍 Auto-started signal monitoring for cloud deployment")
        
        dashboard.run()
        
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        st.write("**Debug Information:**")
        st.write(f"- Error Type: {type(e).__name__}")
        st.write(f"- Error Details: {str(e)}")
        
        # Check environment variables
        st.write("**Environment Check:**")
        required_vars = ['BITGET_API_KEY', 'BITGET_SECRET_KEY', 'BITGET_PASSPHRASE', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                st.write(f"✅ {var}: Configured")
            else:
                st.write(f"❌ {var}: Missing")
        
        logger.error(f"Dashboard error: {e}")
        
        # Show traceback for debugging
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
