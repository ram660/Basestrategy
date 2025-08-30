#!/usr/bin/env python3
"""
Simplified Telegram Bot for RSI-MA Trading
Integrates with Streamlit Dashboard
"""

import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import pandas as pd

# Import our core modules
from rsi_ma_strategy import OptimizedRSIMAStrategy
from bitget_futures_trader import BitgetFuturesTrader
from data_fetcher import get_current_price, get_historical_data
from telegram_notifier import telegram_notifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingTelegramBot:
    """Simplified Telegram Bot for Trading Operations"""
    
    def __init__(self):
        self.strategy = OptimizedRSIMAStrategy()
        self.trader = BitgetFuturesTrader()
        self.symbols = ['XRPUSDT', 'ADAUSDT', 'XLMUSDT', 'UNIUSDT', 'ATOMUSDT', 'AXSUSDT', 'ARBUSDT']
        
        # Get bot token from environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 **RSI-MA Trading Bot**

Welcome to your personal trading assistant!

**Available Commands:**
• /status - Get trading system status
• /balance - Check account balance
• /positions - View active positions
• /market - Get market overview
• /signals - Get current trading signals
• /enable - Enable live trading
• /disable - Disable live trading

**Quick Actions:**
Use the buttons below for common tasks.
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💰 Balance", callback_data="balance")
            ],
            [
                InlineKeyboardButton("📈 Market", callback_data="market"),
                InlineKeyboardButton("📍 Positions", callback_data="positions")
            ],
            [
                InlineKeyboardButton("🚀 Enable Trading", callback_data="enable"),
                InlineKeyboardButton("🛑 Disable Trading", callback_data="disable")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            safety_ok, safety_msg = self.trader.check_account_safety()
            positions = self.trader.get_active_positions()
            
            status_msg = f"""
📊 **Trading System Status**

**API Connection:** {'🟢 Connected' if safety_ok else '🔴 Error'}
**Account:** {safety_msg}
**Active Positions:** {len(positions)}/1
**Trading Mode:** {'🟢 ENABLED' if self.trader.trading_enabled else '🔴 DISABLED'}
**Strategy:** RSI-MA Optimized

**Last Update:** {datetime.now().strftime('%H:%M:%S')}
            """
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {str(e)}")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        try:
            safety_ok, safety_msg = self.trader.check_account_safety()
            
            # Extract balance from message
            balance = 0.0
            if "Balance:" in safety_msg:
                balance_str = safety_msg.split("Balance: $")[1].split(",")[0]
                balance = float(balance_str)
            
            balance_msg = f"""
💰 **Account Balance**

**Available Balance:** ${balance:.2f}
**Status:** {'✅ Healthy' if safety_ok else '⚠️ Check Required'}

**Trading Configuration:**
• Position Size: ${self.trader.config.POSITION_SIZE_USDT} USDT
• Leverage: {self.trader.config.LEVERAGE}x
• Max Risk per Trade: ~${self.trader.config.POSITION_SIZE_USDT * self.trader.config.STOP_LOSS_PERCENT / 100:.2f}
            """
            
            await update.message.reply_text(balance_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting balance: {str(e)}")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            positions = self.trader.get_active_positions()
            
            if not positions:
                await update.message.reply_text("📍 **No Active Positions**\n\nAll positions are closed.")
                return
            
            positions_msg = "📍 **Active Positions**\n\n"
            
            for i, pos in enumerate(positions, 1):
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                size = float(pos.get('size', 0))
                unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                
                side_emoji = '🟢' if side == 'long' else '🔴'
                pnl_emoji = '📈' if unrealized_pnl > 0 else '📉' if unrealized_pnl < 0 else '➖'
                
                positions_msg += f"""
**Position {i}:**
{side_emoji} {symbol} {side.upper()}
Size: {size:.4f}
PnL: {pnl_emoji} ${unrealized_pnl:.2f}
                """
            
            await update.message.reply_text(positions_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting positions: {str(e)}")
    
    async def market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /market command"""
        try:
            market_msg = "📈 **Market Overview**\n\n"
            
            for symbol in self.symbols:
                try:
                    price = get_current_price(symbol)
                    df = get_historical_data(symbol, '5m', 100)
                    
                    if df is not None and len(df) > 53:
                        df_with_indicators = self.strategy.update_indicators(df)
                        current_row = df_with_indicators.iloc[-1]
                        
                        rsi = current_row['rsi']
                        
                        # Determine signal
                        if self.strategy.generate_long_signal(df_with_indicators):
                            signal = "🟢 LONG"
                        elif self.strategy.generate_short_signal(df_with_indicators):
                            signal = "🔴 SHORT"
                        else:
                            signal = "🟡 HOLD"
                        
                        market_msg += f"""
**{symbol}**
Price: ${price:.4f}
RSI: {rsi:.1f}
Signal: {signal}
                        """
                    else:
                        market_msg += f"""
**{symbol}**
Price: ${price:.4f}
RSI: No data
Signal: 🟡 HOLD
                        """
                
                except Exception as e:
                    logger.error(f"Error getting data for {symbol}: {e}")
                    continue
            
            await update.message.reply_text(market_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting market data: {str(e)}")
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signals command"""
        try:
            signals_msg = "🎯 **Current Trading Signals**\n\n"
            
            has_signals = False
            
            for symbol in self.symbols:
                try:
                    df = get_historical_data(symbol, '5m', 100)
                    
                    if df is not None and len(df) > 53:
                        df_with_indicators = self.strategy.update_indicators(df)
                        current_row = df_with_indicators.iloc[-1]
                        
                        rsi = current_row['rsi']
                        price = current_row['close']
                        
                        # Check for signals
                        if self.strategy.generate_long_signal(df_with_indicators):
                            signals_msg += f"""
🟢 **LONG SIGNAL - {symbol}**
Price: ${price:.4f}
RSI: {rsi:.1f} (≥{self.strategy.rsi_buy_threshold})
Condition: RSI ≥ 60 AND Price > MA53 ✅

                            """
                            has_signals = True
                        
                        elif self.strategy.generate_short_signal(df_with_indicators):
                            signals_msg += f"""
🔴 **SHORT SIGNAL - {symbol}**
Price: ${price:.4f}
RSI: {rsi:.1f} (≤{self.strategy.rsi_sell_threshold})
Condition: RSI ≤ 40 AND Price < MA53 ✅

                            """
                            has_signals = True
                
                except Exception as e:
                    logger.error(f"Error checking signals for {symbol}: {e}")
                    continue
            
            if not has_signals:
                signals_msg += "🟡 **No Active Signals**\n\nWaiting for RSI-MA conditions to align."
            
            await update.message.reply_text(signals_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting signals: {str(e)}")
    
    async def enable_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /enable command"""
        try:
            if not self.trader.trading_enabled:
                self.trader.enable_trading()
                await update.message.reply_text("🚀 **Trading ENABLED**\n\nReal trades will now be executed when signals are detected!")
            else:
                await update.message.reply_text("✅ Trading is already enabled.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error enabling trading: {str(e)}")
    
    async def disable_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disable command"""
        try:
            if self.trader.trading_enabled:
                self.trader.disable_trading()
                await update.message.reply_text("🛑 **Trading DISABLED**\n\nMonitoring mode only. No new trades will be executed.")
            else:
                await update.message.reply_text("✅ Trading is already disabled.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error disabling trading: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        callback_map = {
            'status': self.status_command,
            'balance': self.balance_command,
            'market': self.market_command,
            'positions': self.positions_command,
            'enable': self.enable_trading_command,
            'disable': self.disable_trading_command
        }
        
        # Create a fake update for the command handlers
        class FakeUpdate:
            def __init__(self, original_update):
                self.message = original_update.callback_query.message
                self.callback_query = original_update.callback_query
        
        fake_update = FakeUpdate(update)
        
        if query.data in callback_map:
            await callback_map[query.data](fake_update, context)
    
    def run(self):
        """Run the Telegram bot"""
        try:
            # Create application
            application = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("status", self.status_command))
            application.add_handler(CommandHandler("balance", self.balance_command))
            application.add_handler(CommandHandler("positions", self.positions_command))
            application.add_handler(CommandHandler("market", self.market_command))
            application.add_handler(CommandHandler("signals", self.signals_command))
            application.add_handler(CommandHandler("enable", self.enable_trading_command))
            application.add_handler(CommandHandler("disable", self.disable_trading_command))
            application.add_handler(CallbackQueryHandler(self.button_callback))
            
            logger.info("🤖 Telegram bot starting...")
            
            # Run the bot
            application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")

def main():
    """Main function"""
    try:
        bot = TradingTelegramBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")

if __name__ == "__main__":
    main()
