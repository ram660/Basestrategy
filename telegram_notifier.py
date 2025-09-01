#!/usr/bin/env python3
"""
Telegram Notifications for Live Trading System
Sends real-time trading alerts and updates via Telegram
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.constants import ParseMode

# Load environment variables
def load_environment():
    """Load environment variables from Streamlit secrets or .env"""
    try:
        # Try Streamlit secrets first (for cloud deployment)
        import streamlit as st
        if hasattr(st, 'secrets'):
            for key in st.secrets:
                os.environ[key] = str(st.secrets[key])
        else:
            raise ImportError("Streamlit not available")
    except:
        # Fallback to .env file (for local development)
        from dotenv import load_dotenv
        load_dotenv()

load_environment()
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification system for trading alerts with reduced frequency"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')  # Load chat ID from environment
        self.bot = None
        self.last_status_update = None  # Track last status update
        self.status_update_interval = 3 * 60 * 60  # 3 hours in seconds
        
        if self.token:
            self.bot = Bot(token=self.token)
            if self.chat_id:
                logger.info(f"✅ Telegram notifier initialized with chat ID: {self.chat_id}")
            else:
                logger.info("✅ Telegram notifier initialized (no chat ID yet)")
        else:
            logger.warning("⚠️ No Telegram token found - notifications disabled")
    
    def set_chat_id(self, chat_id: str):
        """Set the chat ID for notifications"""
        self.chat_id = chat_id
        logger.info(f"Telegram chat ID set: {chat_id}")
    
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot and self.chat_id)
    
    async def send_message(self, message: str, parse_mode: str = ParseMode.MARKDOWN):
        """Send a message to Telegram"""
        if not self.bot or not self.chat_id:
            logger.debug("Telegram not configured, skipping notification")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info("📱 Telegram message sent successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False

    def should_send_status_update(self) -> bool:
        """Check if enough time has passed for a status update"""
        from datetime import datetime
        
        now = datetime.now()
        if self.last_status_update is None:
            return True
        
        time_since_last = (now - self.last_status_update).total_seconds()
        return time_since_last >= self.status_update_interval

    async def send_periodic_status(self, stats: Dict[str, Any] = None):
        """Send periodic status update (every 3 hours)"""
        if not self.should_send_status_update():
            return False
        
        from datetime import datetime
        
        message = f"""
🤖 **Bot Status Update**

✅ System Running
📊 Paper Trading: {'ON' if hasattr(self, '_paper_mode') and self._paper_mode else 'Check Dashboard'}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if stats:
            total_trades = stats.get('total_trades', 0)
            total_pnl = stats.get('total_pnl', 0)
            pnl_emoji = "💚" if total_pnl > 0 else "❤️" if total_pnl < 0 else "💙"
            
            message += f"""
� Session Stats:
• Trades: {total_trades}
• P&L: {pnl_emoji} ${total_pnl:.2f}
"""
        
        logger.info("📱 Sending 3-hour status update")
        result = await self.send_message(message)
        if result:
            self.last_status_update = datetime.now()
            logger.info("✅ Status update sent successfully")
        else:
            logger.warning("❌ Failed to send status update")
        
        return result
    
    async def notify_trade_entry(self, symbol: str, side: str, entry_price: float, 
                                stop_loss: float, take_profit: float, 
                                position_size: float, confidence: float = 0.0):
        """Send trade entry notification"""
        side_emoji = "🟢" if side.upper() == "LONG" else "🔴"
        
        message = f"""
🚀 **TRADE OPENED**

{side_emoji} **{symbol} {side.upper()}**
💰 Entry: ${entry_price:.4f}
🛡️ Stop Loss: ${stop_loss:.4f}
🎯 Take Profit: ${take_profit:.4f}
📊 Size: {position_size:.2f} units
📈 Confidence: {confidence:.1%}

⏰ {datetime.now().strftime('%H:%M:%S')}
💡 RSI-MA Strategy Signal
        """
        
        await self.send_message(message)
    
    async def notify_trade_exit(self, symbol: str, side: str, exit_price: float,
                               pnl: float, exit_reason: str):
        """Send trade exit notification"""
        pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💛"
        side_emoji = "🟢" if side.upper() == "LONG" else "🔴"
        
        message = f"""
🏁 **TRADE CLOSED**

{side_emoji} **{symbol} {side.upper()}**
💰 Exit: ${exit_price:.4f}
{pnl_emoji} P&L: ${pnl:.2f}
📋 Reason: {exit_reason}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self.send_message(message)
    
    async def notify_signal(self, symbol: str, action: str, price: float, 
                           rsi: float, confidence: float):
        """Send trading signal notification - DISABLED to reduce spam"""
        # Only log signals, don't send notifications
        logger.info(f"📡 Signal detected: {symbol} {action} at ${price:.4f} (RSI: {rsi:.1f}, Confidence: {confidence:.1%})")
        return True  # Return True to maintain compatibility
    
    async def notify_system_status(self, status: str, message: str = ""):
        """Send system status notification - ONLY for critical events"""
        if status.upper() not in ["STARTED", "STOPPED", "ERROR"]:
            # Only send notifications for critical status changes
            logger.info(f"System status: {status} - {message}")
            return True
        
        status_emoji = "✅" if status == "STARTED" else "🛑" if status == "STOPPED" else "⚠️"
        
        notification = f"""
{status_emoji} **SYSTEM {status}**

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self.send_message(notification)
    
    async def notify_performance_update(self, stats: Dict[str, Any]):
        """Send performance update - DISABLED, use periodic status instead"""
        # Performance updates are now handled by send_periodic_status
        logger.debug(f"Performance update: {stats}")
        return True  # Return True to maintain compatibility
    
    async def notify_error(self, error_type: str, error_message: str):
        """Send error notification"""
        message = f"""
🚨 **SYSTEM ERROR**

⚠️ Type: {error_type}
📝 Message: {error_message}
⏰ {datetime.now().strftime('%H:%M:%S')}

Please check the system!
        """
        
        await self.send_message(message)

# Global notifier instance
telegram_notifier = TelegramNotifier()

def run_async(coro):
    """Helper to run async functions from sync code"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)
