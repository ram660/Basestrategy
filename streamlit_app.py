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
    """Main Streamlit Trading Dashboard"""
    
    def __init__(self):
        self.strategy = OptimizedRSIMAStrategy()
        self.trader = BitgetFuturesTrader()
        self.symbols = ['XRPUSDT', 'ADAUSDT', 'XLMUSDT', 'UNIUSDT', 'ATOMUSDT', 'AXSUSDT', 'ARBUSDT']
        self.trading_active = False
        
        # Initialize session state
        if 'trading_enabled' not in st.session_state:
            st.session_state.trading_enabled = False
        if 'positions' not in st.session_state:
            st.session_state.positions = []
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
    
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
                        asyncio.run(telegram_notifier.send_notification("🚀 Trading enabled via dashboard!"))
        
        with col2:
            if st.button("🛑 Disable Trading", type="secondary" if not st.session_state.trading_enabled else "primary"):
                if st.session_state.trading_enabled:
                    self.trader.disable_trading()
                    st.session_state.trading_enabled = False
                    st.warning("Trading disabled. No new trades will be executed.")
                    if telegram_notifier.is_configured():
                        asyncio.run(telegram_notifier.send_notification("🛑 Trading disabled via dashboard."))
        
        with col3:
            if st.button("📱 Test Telegram"):
                if telegram_notifier.is_configured():
                    asyncio.run(telegram_notifier.send_notification("📊 Dashboard test message - All systems operational!"))
                    st.success("Telegram test message sent!")
                else:
                    st.error("Telegram not configured. Check .env file.")
        
        # Trading status
        if st.session_state.trading_enabled:
            st.markdown('<p class="status-green">✅ Trading is ENABLED - Real trades will be executed</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-yellow">⚠️ Trading is DISABLED - Monitoring only</p>', unsafe_allow_html=True)
    
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
    
    def run(self):
        """Main dashboard runner"""
        self.render_header()
        
        st.divider()
        
        # Main content in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["🎮 Controls", "📈 Market", "💼 Positions", "⚙️ Config"])
        
        with tab1:
            self.render_trading_controls()
        
        with tab2:
            self.render_market_overview()
        
        with tab3:
            self.render_positions()
        
        with tab4:
            self.render_strategy_config()
        
        # Auto-refresh
        if st.checkbox("🔄 Auto-refresh (30s)", value=True):
            time.sleep(30)
            st.rerun()

# Main application
def main():
    """Main function"""
    try:
        st.write("🚀 Initializing RSI-MA Trading Dashboard...")
        dashboard = StreamlitTradingDashboard()
        st.write("✅ Dashboard initialized successfully")
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
