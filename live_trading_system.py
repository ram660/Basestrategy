#!/usr/bin/env python3
"""
Live Trading System Controller
Integrates RSI-MA Strategy with Bitget Futures Trading
"""

import os
import sys
import time
import json
import logging
import signal
from datetime import datetime, timedelta
from threading import Thread, Event
from typing import Dict, List, Optional

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rsi_ma_strategy import OptimizedRSIMAStrategy
from bitget_futures_trader import BitgetFuturesTrader, TradingConfig
from data_fetcher import get_current_price, get_historical_data
from config import validate_config
from telegram_notifier import telegram_notifier, run_async

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveTradingController:
    """Main controller for live trading operations"""
    
    def __init__(self):
        self.running = False
        self.stop_event = Event()
        
        # Initialize components
        self.strategy = OptimizedRSIMAStrategy()
        self.trader = BitgetFuturesTrader()
        self.config = TradingConfig()
        
        # Trading state
        self.active_positions = {}
        self.trade_history = []
        self.last_signals = {}
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'start_balance': 0.0,
            'current_balance': 0.0
        }
        
        logger.info("Live Trading Controller initialized")
        
        # Setup Telegram notifications
        self._setup_telegram()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def validate_setup(self) -> bool:
        """Validate trading setup before starting"""
        try:
            # Check configuration
            if not validate_config():
                logger.error("❌ Configuration validation failed")
                return False
            
            # Check trader connectivity
            safety_ok, safety_msg = self.trader.check_account_safety()
            if not safety_ok:
                logger.error(f"❌ Safety check failed: {safety_msg}")
                return False
            
            # Test data fetching
            test_price = get_current_price('XRPUSDT')
            if not test_price:
                logger.error("❌ Cannot fetch market data")
                return False
            
            logger.info("Setup validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Setup validation error: {e}")
            return False
    
    def start(self):
        """Start the live trading system"""
        if self.running:
            logger.warning("⚠️ Trading system already running")
            return
        
        logger.info("Starting Live Trading System...")
        
        # Validate setup
        if not self.validate_setup():
            logger.error("Setup validation failed, cannot start trading")
            return False
        
        # Enable trading
        self.trader.enable_trading()
        self.running = True
        
        # Send startup notification
        run_async(telegram_notifier.notify_system_status("STARTED", f"Live trading enabled with {len(self.config.ALLOWED_SYMBOLS)} symbols"))
        
        # Start main trading loop
        self.trading_thread = Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        
        # Start performance tracking
        self.performance_thread = Thread(target=self._performance_loop, daemon=True)
        self.performance_thread.start()
        
        logger.info("Live Trading System started successfully")
        return True
    
    def stop(self):
        """Stop the trading system gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping Live Trading System...")
        
        self.running = False
        self.stop_event.set()
        
        # Send shutdown notification
        run_async(telegram_notifier.notify_system_status("STOPPED", "Live trading system stopped safely"))
        
        # Close all positions (optional - you might want to keep them)
        # self._close_all_positions()
        
        # Save final performance data
        self._save_performance_data()
        
        logger.info("Live Trading System stopped")
    
    def _trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Check each trading symbol
                for symbol in self.config.ALLOWED_SYMBOLS:
                    if self.stop_event.is_set():
                        break
                    
                    self._process_symbol(symbol)
                
                # Update performance stats
                self._update_performance_stats()
                
                # Wait for next cycle
                self.stop_event.wait(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _process_symbol(self, symbol: str):
        """Process trading signals for a specific symbol"""
        try:
            # Get current price
            current_price = get_current_price(symbol)
            if not current_price:
                logger.warning(f"⚠️ Cannot get price for {symbol}")
                return
            
            # Get historical data for analysis
            historical_data = get_historical_data(symbol, '5m', 100)
            if historical_data is None or historical_data.empty:
                logger.warning(f"⚠️ Cannot get historical data for {symbol}")
                return
            
            # Analyze with strategy
            signal = self.strategy.analyze(symbol, historical_data, current_price)
            
            # Store signal
            self.last_signals[symbol] = {
                'signal': signal,
                'price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
            # Check if we should trade
            self._check_trading_signal(symbol, signal, current_price)
            
        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {e}")
    
    def _check_trading_signal(self, symbol: str, signal: Dict, current_price: float):
        """Check if we should execute a trade based on the signal"""
        try:
            action = signal.get('action', 'hold')
            
            # Skip if already have position for this symbol
            if symbol in self.active_positions:
                logger.debug(f"📊 {symbol}: Already have position, skipping")
                return
            
            # Check max positions limit
            if len(self.active_positions) >= self.config.MAX_POSITIONS:
                logger.debug(f"📊 {symbol}: Max positions reached ({self.config.MAX_POSITIONS})")
                return
            
            # Execute trade based on signal
            if action == 'buy':
                logger.info(f"🔵 {symbol}: BUY signal at ${current_price:.4f}")
                
                # Send signal notification
                rsi_value = signal.get('rsi', 0)
                confidence = signal.get('confidence', 0.5)
                run_async(telegram_notifier.notify_signal(symbol, 'BUY', current_price, rsi_value, confidence))
                
                position = self.trader.place_order_with_sl_tp(symbol, 'LONG', current_price)
                if position:
                    self.active_positions[symbol] = position
                    self._log_trade_entry(position)
                    
                    # Send trade entry notification
                    run_async(telegram_notifier.notify_trade_entry(
                        symbol, 'LONG', position.entry_price, position.stop_loss, 
                        position.take_profit, position.size, confidence
                    ))
                    
                    logger.info(f"✅ {symbol}: LONG position opened")
                
            elif action == 'sell':
                logger.info(f"🔴 {symbol}: SELL signal at ${current_price:.4f}")
                
                # Send signal notification
                rsi_value = signal.get('rsi', 0)
                confidence = signal.get('confidence', 0.5)
                run_async(telegram_notifier.notify_signal(symbol, 'SELL', current_price, rsi_value, confidence))
                
                position = self.trader.place_order_with_sl_tp(symbol, 'SHORT', current_price)
                if position:
                    self.active_positions[symbol] = position
                    self._log_trade_entry(position)
                    
                    # Send trade entry notification
                    run_async(telegram_notifier.notify_trade_entry(
                        symbol, 'SHORT', position.entry_price, position.stop_loss, 
                        position.take_profit, position.size, confidence
                    ))
                    
                    logger.info(f"✅ {symbol}: SHORT position opened")
            
        except Exception as e:
            logger.error(f"❌ Error checking trading signal for {symbol}: {e}")
    
    def _log_trade_entry(self, position):
        """Log trade entry"""
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'entry',
            'symbol': position.symbol,
            'side': position.side,
            'size': position.size,
            'entry_price': position.entry_price,
            'stop_loss': position.stop_loss,
            'take_profit': position.take_profit,
            'position_id': position.position_id
        }
        
        self.trade_history.append(trade_data)
        
        # Save to file
        self._save_trade_log(trade_data)
    
    def _performance_loop(self):
        """Performance monitoring loop"""
        while self.running and not self.stop_event.is_set():
            try:
                # Check position status
                self._check_position_status()
                
                # Update performance metrics
                self._update_performance_stats()
                
                # Save performance data
                self._save_performance_data()
                
                # Wait 1 minute
                self.stop_event.wait(60)
                
            except Exception as e:
                logger.error(f"❌ Performance loop error: {e}")
                time.sleep(60)
    
    def _check_position_status(self):
        """Check status of active positions"""
        for symbol in list(self.active_positions.keys()):
            try:
                position = self.active_positions[symbol]
                
                # Check if position is still active
                is_active = self.trader.check_position_status(position.position_id)
                
                if not is_active:
                    # Position was closed (SL/TP hit)
                    logger.info(f"📊 {symbol}: Position closed")
                    
                    # Send exit notification (simplified - real implementation would get actual exit price and P&L)
                    run_async(telegram_notifier.notify_trade_exit(
                        symbol, position.side, position.entry_price, 0.0, "SL/TP Hit"
                    ))
                    
                    self._log_trade_exit(position)
                    del self.active_positions[symbol]
                
            except Exception as e:
                logger.error(f"❌ Error checking position status for {symbol}: {e}")
    
    def _log_trade_exit(self, position):
        """Log trade exit"""
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'exit',
            'symbol': position.symbol,
            'side': position.side,
            'position_id': position.position_id,
            'reason': 'sl_tp_hit'  # Assume SL/TP hit for now
        }
        
        self.trade_history.append(trade_data)
        self._save_trade_log(trade_data)
    
    def _update_performance_stats(self):
        """Update performance statistics"""
        try:
            # Calculate basic stats from trade history
            entries = [t for t in self.trade_history if t['type'] == 'entry']
            exits = [t for t in self.trade_history if t['type'] == 'exit']
            
            self.performance_stats['total_trades'] = len(entries)
            
            # This is simplified - in a real implementation you'd calculate actual P&L
            # based on entry/exit prices and position sizes
            
        except Exception as e:
            logger.error(f"❌ Error updating performance stats: {e}")
    
    def _save_performance_data(self):
        """Save performance data to file"""
        try:
            with open('performance_data.json', 'w') as f:
                json.dump(self.performance_stats, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving performance data: {e}")
    
    def _save_trade_log(self, trade_data):
        """Save individual trade to log file"""
        try:
            os.makedirs('trade_logs', exist_ok=True)
            
            log_file = f"trade_logs/trades_{datetime.now().strftime('%Y%m%d')}.json"
            
            # Load existing data
            trades = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    trades = json.load(f)
            
            # Add new trade
            trades.append(trade_data)
            
            # Save updated data
            with open(log_file, 'w') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error saving trade log: {e}")
    
    def get_status(self) -> Dict:
        """Get current trading status"""
        return {
            'running': self.running,
            'active_positions': len(self.active_positions),
            'total_trades': self.performance_stats['total_trades'],
            'last_update': datetime.now().isoformat(),
            'symbols': list(self.last_signals.keys()),
            'performance': self.performance_stats
        }
    
    def _setup_telegram(self):
        """Setup Telegram notifications"""
        try:
            # For now, we'll use a default chat ID or get it from environment
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if chat_id:
                telegram_notifier.set_chat_id(chat_id)
                run_async(telegram_notifier.notify_system_status("INITIALIZING", "Live trading system starting up"))
                logger.info("Telegram notifications enabled")
            else:
                logger.info("Telegram notifications available (need chat ID)")
        except Exception as e:
            logger.warning(f"Telegram setup failed: {e}")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("🤖 LIVE RSI-MA TRADING SYSTEM")
    print("Real Trading with Bitget Futures")
    print("="*60)
    
    # Create controller
    controller = LiveTradingController()
    controller.setup_signal_handlers()
    
    # Configuration info
    print(f"\n📊 TRADING CONFIGURATION:")
    print(f"   Symbols: {controller.config.ALLOWED_SYMBOLS}")
    print(f"   Position Size: ${controller.config.POSITION_SIZE_USDT} USDT")
    print(f"   Leverage: {controller.config.LEVERAGE}x")
    print(f"   Max Positions: {controller.config.MAX_POSITIONS}")
    print(f"   Stop Loss: {controller.config.STOP_LOSS_PERCENT}%")
    print(f"   Take Profit: {controller.config.TAKE_PROFIT_PERCENT}%")
    
    print(f"\n⚠️ WARNING: THIS WILL EXECUTE REAL TRADES!")
    print(f"   Risk per trade: ~${controller.config.POSITION_SIZE_USDT * controller.config.STOP_LOSS_PERCENT / 100:.2f}")
    print(f"   Max total risk: ~${controller.config.POSITION_SIZE_USDT * controller.config.STOP_LOSS_PERCENT / 100 * controller.config.MAX_POSITIONS:.2f}")
    
    # Confirmation
    print("\n" + "="*60)
    confirm = input("Type 'START' to begin live trading: ")
    if confirm != 'START':
        print("❌ Live trading cancelled")
        return
    
    # Start trading
    if controller.start():
        print("\n✅ Live trading system started!")
        print("📊 Monitor progress in the dashboard at http://localhost:7000")
        print("📋 Press Ctrl+C to stop gracefully")
        
        try:
            # Keep main thread alive
            while controller.running:
                time.sleep(10)
                
                # Print status every 5 minutes
                if int(time.time()) % 300 == 0:
                    status = controller.get_status()
                    print(f"\n📊 Status: {status['active_positions']} positions, {status['total_trades']} total trades")
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            controller.stop()
    else:
        print("❌ Failed to start live trading system")

if __name__ == "__main__":
    main()
