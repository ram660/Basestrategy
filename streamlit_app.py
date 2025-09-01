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

# Global position cache and poller controls (updated by background thread)
GLOBAL_POSITION_CACHE = {
    'positions': [],
    'last_poll': None,
}
_position_poller_thread = None
_position_poller_lock = threading.Lock()

# Import our core modules
from rsi_ma_strategy import EnhancedRSIMAStrategy
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
        self.strategy = EnhancedRSIMAStrategy()
        self.trader = BitgetFuturesTrader()
        self.symbols = config.get_symbols_config()['trading_symbols']
        self.trading_active = False
        
        # Detect cloud environment
        self.is_cloud = self._detect_cloud_environment()
        
        # Initialize session state
        if 'trading_enabled' not in st.session_state:
            # Default to running the bot on start (user requested)
            st.session_state.trading_enabled = True
        if 'positions' not in st.session_state:
            st.session_state.positions = []
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
        if 'last_signal_check' not in st.session_state:
            st.session_state.last_signal_check = datetime.now()
        if 'signal_monitoring_active' not in st.session_state:
            # Start monitoring by default
            st.session_state.signal_monitoring_active = True
        if 'auto_trading_active' not in st.session_state:
            st.session_state.auto_trading_active = True
        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = datetime.now()
        
        # Auto-start monitoring for cloud environment
        if self.is_cloud and config.is_production():
            if not st.session_state.signal_monitoring_active:
                st.session_state.signal_monitoring_active = True
                logger.info("🚀 Auto-started signal monitoring for cloud environment")
        
        # Ensure background position poller is running when monitoring is active
        try:
            if st.session_state.signal_monitoring_active:
                # start_position_poller is safe to call if already running
                self.start_position_poller()
        except Exception:
            pass
    
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
        """Render enhanced main header with improved features"""
        st.markdown('<div class="main-header">📊 Enhanced RSI-MA Trading Bot Dashboard</div>', unsafe_allow_html=True)
        
        # Enhanced status display
        st.markdown("### 🔧 **Enhanced Features Active:**")
        
        # Feature status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            paper_mode = self.strategy.paper_trading_mode
            if paper_mode:
                st.markdown('<p class="status-green">📝 Paper Trading Mode</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="status-red">💰 Live Trading Mode</p>', unsafe_allow_html=True)
        
        with col2:
            trend_filter = f"📈 Trend Filter: ADX ≥ {self.strategy.trend_strength_threshold}"
            st.markdown(f'<p class="status-green">{trend_filter}</p>', unsafe_allow_html=True)
        
        with col3:
            volume_filter = f"📊 Volume Filter: {self.strategy.volume_multiplier_threshold}x"
            st.markdown(f'<p class="status-green">{volume_filter}</p>', unsafe_allow_html=True)
        
        with col4:
            risk_mgmt = f"⚠️ Max Risk: {self.strategy.max_risk_per_trade*100:.1f}%"
            st.markdown(f'<p class="status-green">{risk_mgmt}</p>', unsafe_allow_html=True)
        
        # API and Account Status
        st.markdown("---")
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
        
        # Enhanced Strategy Parameters
        st.markdown("---")
        st.markdown("### 📋 **Enhanced Strategy Parameters:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            **Signal Thresholds:**
            - RSI Buy: ≤ {self.strategy.rsi_buy_threshold} (Oversold)
            - RSI Sell: ≥ {self.strategy.rsi_sell_threshold} (Overbought)
            - MA Period: {self.strategy.ma53_period}
            """)
        
        with col2:
            st.markdown(f"""
            **Risk Management:**
            - Stop Loss: {self.strategy.stop_loss_pct*100:.1f}%
            - Take Profit: {self.strategy.take_profit_pct*100:.1f}%
            - Leverage: {config.trading.leverage}x
            """)
        
        with col3:
            st.markdown(f"""
            **Market Filters:**
            - Session Filter: {'✅' if self.strategy.trading_sessions_enabled else '❌'}
            - Volatility Filter: {'✅' if self.strategy.volatility_filter_enabled else '❌'}
            - Max Daily Loss: ${config.trading.max_daily_loss_usdt}
            """)
    
    def render_trading_controls(self):
        """Render enhanced trading control panel"""
        st.subheader("🎮 Enhanced Trading Controls")
        
        # Paper Trading Mode Toggle
        st.markdown("### 📝 Trading Mode")
        col1, col2 = st.columns(2)
        
        with col1:
            current_paper_mode = self.strategy.paper_trading_mode
            if st.checkbox("📝 Paper Trading Mode", value=current_paper_mode, 
                          help="Enable paper trading to test strategies without real money"):
                if not current_paper_mode:
                    self.strategy.paper_trading_mode = True
                    st.success("✅ Switched to Paper Trading Mode - No real trades will be executed!")
            else:
                if current_paper_mode:
                    if st.button("⚠️ Confirm Switch to LIVE TRADING", type="secondary"):
                        self.strategy.paper_trading_mode = False
                        st.error("🚨 LIVE TRADING MODE ENABLED - Real money at risk!")
        
        with col2:
            if self.strategy.paper_trading_mode:
                st.info("📝 **Paper Trading Active** - All trades are simulated")
            else:
                st.error("💰 **LIVE TRADING** - Real money at risk!")
        
        st.markdown("---")
        
        # Main execution controls
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.session_state.trading_enabled:
                if st.button("⏸️ Stop Execution", key="stop_execution", type="primary"):
                    # Stop everything
                    try:
                        self.trader.disable_trading()
                    except Exception:
                        pass
                    st.session_state.trading_enabled = False
                    st.session_state.auto_trading_active = False
                    st.session_state.signal_monitoring_active = False
                    # stop poller
                    try:
                        self.stop_position_poller()
                    except Exception:
                        pass
                    st.warning("Execution stopped. Monitoring and auto-trading disabled.")
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_message("⏸️ Execution stopped via dashboard"))
            else:
                if st.button("▶️ Start Execution", key="start_execution", type="primary"):
                    try:
                        self.trader.enable_trading()
                    except Exception:
                        pass
                    st.session_state.trading_enabled = True
                    st.session_state.auto_trading_active = True
                    st.session_state.signal_monitoring_active = True
                    # start poller
                    try:
                        self.start_position_poller()
                    except Exception:
                        pass
                    st.success("Execution started. Monitoring and auto-trading enabled.")
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_message("▶️ Execution started via dashboard"))
        
        with col2:
            if st.button("📱 Test Telegram"):
                if telegram_notifier.is_configured():
                    asyncio.run(telegram_notifier.send_message("📊 Dashboard test message - All systems operational!"))
                    st.success("Telegram test message sent!")
                else:
                    st.error("Telegram not configured. Check secrets.")
        
        # Trading status
        if st.session_state.trading_enabled:
            st.markdown('<p class="status-green">✅ Execution: RUNNING</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-red">⏸️ Execution: STOPPED</p>', unsafe_allow_html=True)
        
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
        
        # Use GLOBAL_POSITION_CACHE if available to avoid blocking API calls
        with _position_poller_lock:
            cached = GLOBAL_POSITION_CACHE.get('positions', [])
            last_poll = GLOBAL_POSITION_CACHE.get('last_poll')

        positions = cached if cached else self.get_current_positions()
        
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
                    unrealized_pnl = float(pos.get('unrealized_pnl', pos.get('unrealizedPnl', 0)))
                    pnl_color = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
                    st.metric("PnL", f"{pnl_color} ${unrealized_pnl:.2f}")
        else:
            st.info("No active positions")

        # Show last poll time
        if last_poll:
            st.caption(f"Last polled: {last_poll.strftime('%Y-%m-%d %H:%M:%S')}")
        
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
            
            # Reconcile positions first
            try:
                self.monitor_positions_reconciliation()
            except Exception:
                pass

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
        st.subheader("☁️ Cloud Monitoring")
        # Minimal controls: show status and single Start/Stop execution button (managed above)
        col1, col2 = st.columns(2)
        with col1:
            status = "🟢 ACTIVE" if st.session_state.signal_monitoring_active else "🔴 INACTIVE"
            st.markdown(f"**Signal Monitoring:** {status}")
            status2 = "🟢 ENABLED" if st.session_state.auto_trading_active else "🔴 DISABLED"
            st.markdown(f"**Auto-Trading:** {status2}")
        with col2:
            last_check = st.session_state.last_signal_check
            time_ago = (datetime.now() - last_check).total_seconds()
            st.markdown(f"**Last Check:** {int(time_ago)}s ago")
            uptime = datetime.now() - st.session_state.get('app_start_time', datetime.now())
            st.markdown(f"**Uptime:** {int(uptime.total_seconds()/3600)}h")

    def render_signals_panel(self):
        """Render real-time signals panel with execute controls"""
        st.sidebar.header("Signals & Execution")

        # Select symbol
        selected_symbol = st.sidebar.selectbox("Symbol", self.symbols, index=0)

        # Fetch market data and signal
        market_data = self.get_market_data(selected_symbol)
        signal = market_data.get('signal', 'HOLD')

        st.sidebar.markdown("---")
        st.sidebar.subheader(f"Latest Signal: {signal}")
        st.sidebar.metric("Price", f"{market_data.get('price', 0):.4f}")
        st.sidebar.metric("RSI", f"{market_data.get('rsi', 0):.2f}")
        st.sidebar.metric("MA53", f"{market_data.get('ma53', 0):.4f}")
        st.sidebar.write("Confidence: N/A")
        st.sidebar.write(market_data.get('signal'))

        st.sidebar.markdown("---")
        # Safety summary
        safety_ok, safety_msg = self.trader.check_account_safety()
        st.sidebar.write("**Safety Check**")
        if safety_ok:
            st.sidebar.success(safety_msg)
        else:
            st.sidebar.error(safety_msg)

        # Manual execution
        if signal in ['LONG', 'SHORT']:
            exec_label = f"Execute {signal} on {selected_symbol}"
            if st.sidebar.button(exec_label):
                # Confirmation
                if st.sidebar.checkbox("Confirm execution"):
                    # Execute - do not block UI; run safely
                    with st.spinner("Placing order..."):
                        try:
                            side = 'LONG' if signal == 'LONG' else 'SHORT'
                            position = self.trader.place_order_with_sl_tp(selected_symbol, side, market_data.get('price', 0))
                            if position:
                                st.sidebar.success(f"Order placed: {position.position_id}")
                                # log to session
                                st.session_state.positions.append({
                                    'symbol': selected_symbol,
                                    'side': side,
                                    'entry_price': position.entry_price,
                                    'size': position.size,
                                    'sl': position.stop_loss,
                                    'tp': position.take_profit,
                                    'timestamp': position.timestamp
                                })
                                # Optional telegram notify
                                try:
                                    from telegram_notifier import telegram_notifier
                                    telegram_notifier.send_message(f"Executed {side} {selected_symbol} @ {position.entry_price:.4f}")
                                except Exception:
                                    pass
                            else:
                                st.sidebar.error("Failed to place order. Check logs.")
                        except Exception as e:
                            st.sidebar.error(f"Execution error: {e}")
        else:
            st.sidebar.info("No actionable signal")

        st.sidebar.markdown("---")
        st.sidebar.write("Last checked:", st.session_state.last_signal_check.strftime('%Y-%m-%d %H:%M:%S'))

    def render_dashboard(self):
        """Top-level renderer"""
        self.render_header()

        # Left column: signals & positions
        col1, col2 = st.columns([1, 2])

        with col1:
            st.header("Signals & Controls")
            self.render_signals_panel()

        with col2:
            st.header("Positions & Trade History")
            # Positions table
            if st.session_state.positions:
                st.table(st.session_state.positions[-10:])
            else:
                st.info("No active positions recorded in session")

            st.markdown("---")
            st.subheader("Recent Trades (session)")
            if st.session_state.trade_history:
                st.table(st.session_state.trade_history[-20:])
            else:
                st.info("No trades recorded this session")

    def monitor_positions_reconciliation(self, poll_interval: int = 10):
        """Fetch positions from exchange, detect closed positions and reconcile logs.

        This is a single-run reconciliation pass — call periodically from the main loop.
        """
        try:
            # Fetch current positions from exchange
            current_positions = self.trader.get_active_positions() or []
            current_symbols = {p['symbol']: p for p in current_positions}

            # Build previous positions map from session state
            prev_positions_list = st.session_state.get('positions', [])
            prev_by_symbol = {p['symbol']: p for p in prev_positions_list}

            # Detect closed positions: present previously but not in current_symbols
            closed_symbols = [s for s in prev_by_symbol.keys() if s not in current_symbols]

            for symbol in closed_symbols:
                prev = prev_by_symbol[symbol]
                # Attempt to determine exit price and PnL
                exit_price = get_current_price(symbol) or prev.get('entry_price')
                size = float(prev.get('size', 0))
                side = prev.get('side', 'LONG')
                entry_price = float(prev.get('entry_price', exit_price))

                # Compute approximate pnl: long -> (exit-entry)*size, short -> (entry-exit)*size
                try:
                    if side.upper() in ['LONG', 'long']:
                        pnl = (exit_price - entry_price) * size
                    else:
                        pnl = (entry_price - exit_price) * size
                except Exception:
                    pnl = 0.0

                exit_time = datetime.now()
                exit_reason = 'CLOSED (exchange)'

                # Try to find trade_id from trader.positions if available
                trade_id = None
                try:
                    tp = self.trader.positions.get(symbol)
                    if tp and hasattr(tp, 'trade_id'):
                        trade_id = tp.trade_id
                except Exception:
                    trade_id = None

                # Log exit to trade_logger if possible
                if trade_id and trade_logger:
                    try:
                        trade_logger.log_trade_exit(
                            trade_id=trade_id,
                            exit_price=exit_price,
                            exit_reason=exit_reason,
                            fees=0.0,
                            notes=f"Reconciled exit detected via polling"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log trade exit for {symbol}: {e}")

                # Append to session trade history
                st.session_state.trade_history.append({
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S')
                })

                # Remove from local session positions
                st.session_state.positions = [p for p in st.session_state.positions if p.get('symbol') != symbol]

                logger.info(f"Reconciled closed position: {symbol} side={side} pnl=${pnl:.2f}")

            # Update session positions to reflect current exchange state
            new_session_positions = []
            for p in current_positions:
                # Normalize fields to session format
                new_session_positions.append({
                    'symbol': p.get('symbol'),
                    'side': p.get('side'),
                    'entry_price': p.get('entry_price'),
                    'size': p.get('size'),
                    'sl': p.get('stop_loss', None) if isinstance(p, dict) else None,
                    'tp': p.get('take_profit', None) if isinstance(p, dict) else None,
                    'unrealized_pnl': p.get('unrealized_pnl', p.get('unrealizedPnl', 0)),
                    'mark_price': p.get('mark_price', p.get('markPrice', 0)),
                })

            st.session_state.positions = new_session_positions

            return True

        except Exception as e:
            logger.error(f"Error in position reconciliation: {e}")
            return False

    def _position_poller(self, interval: int = 10):
        """Background thread that polls exchange positions and updates GLOBAL_POSITION_CACHE."""
        global GLOBAL_POSITION_CACHE
        while st.session_state.get('signal_monitoring_active', False):
            try:
                positions = self.trader.get_active_positions() or []
                with _position_poller_lock:
                    GLOBAL_POSITION_CACHE['positions'] = positions
                    GLOBAL_POSITION_CACHE['last_poll'] = datetime.now()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Position poller error: {e}")
                time.sleep(interval)

    def start_position_poller(self, interval: int = 10):
        """Start background poller thread if not running"""
        global _position_poller_thread
        if _position_poller_thread and _position_poller_thread.is_alive():
            return
        _position_poller_thread = threading.Thread(target=self._position_poller, args=(interval,), daemon=True)
        _position_poller_thread.start()
        logger.info("Started position poller thread")

    def stop_position_poller(self):
        """Stop background poller by toggling session flag; thread will exit gracefully."""
        st.session_state.signal_monitoring_active = False
        logger.info("Stopped position poller thread")

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
        if config.is_production() and not st.session_state.get('auto_monitor_started', False):
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
