#!/usr/bin/env python3
"""
Comprehensive Trade Logging System
Tracks all trading activities with detailed entry/exit information
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TradeEntry:
    """Trade entry data structure"""
    trade_id: str
    timestamp: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    size: float
    leverage: float
    margin: float
    order_id: str
    strategy: str
    confidence: float
    stop_loss: float
    take_profit: float
    notes: str = ""

@dataclass
class TradeExit:
    """Trade exit data structure"""
    trade_id: str
    exit_timestamp: str
    exit_price: float
    exit_reason: str
    fees: float
    pnl: float
    notes: str = ""

class TradeLogger:
    """Comprehensive trade logging system"""
    
    def __init__(self):
        self.log_dir = "trade_logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.trades = {}  # Active trades
        self.completed_trades = []  # Completed trades
        
        # Load existing trades
        self._load_trades()

    def log_trade_entry(self, symbol: str, side: str, entry_price: float, size: float,
                       leverage: float, margin: float, order_id: str, strategy: str,
                       confidence: float, stop_loss: float, take_profit: float,
                       notes: str = "") -> str:
        """Log a trade entry and return trade ID"""
        try:
            trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_id[-6:]}"
            
            trade_entry = TradeEntry(
                trade_id=trade_id,
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                size=size,
                leverage=leverage,
                margin=margin,
                order_id=order_id,
                strategy=strategy,
                confidence=confidence,
                stop_loss=stop_loss,
                take_profit=take_profit,
                notes=notes
            )
            
            self.trades[trade_id] = trade_entry
            self._save_trade_entry(trade_entry)
            
            logger.info(f"📝 Trade entry logged: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"❌ Error logging trade entry: {e}")
            return ""

    def log_trade_exit(self, trade_id: str, exit_price: float, exit_reason: str,
                      fees: float = 0.0, notes: str = ""):
        """Log a trade exit"""
        try:
            if trade_id not in self.trades:
                logger.error(f"❌ Trade ID {trade_id} not found")
                return
            
            trade_entry = self.trades[trade_id]
            
            # Calculate P&L
            pnl = self._calculate_pnl(trade_entry, exit_price, fees)
            
            trade_exit = TradeExit(
                trade_id=trade_id,
                exit_timestamp=datetime.now().isoformat(),
                exit_price=exit_price,
                exit_reason=exit_reason,
                fees=fees,
                pnl=pnl,
                notes=notes
            )
            
            # Create completed trade record
            completed_trade = {
                'entry': asdict(trade_entry),
                'exit': asdict(trade_exit)
            }
            
            self.completed_trades.append(completed_trade)
            del self.trades[trade_id]
            
            self._save_completed_trade(completed_trade)
            
            logger.info(f"📝 Trade exit logged: {trade_id}, P&L: ${pnl:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error logging trade exit: {e}")

    def _calculate_pnl(self, entry: TradeEntry, exit_price: float, fees: float) -> float:
        """Calculate P&L for a trade"""
        try:
            if entry.side.lower() == 'long':
                pnl = (exit_price - entry.entry_price) * entry.size
            else:  # short
                pnl = (entry.entry_price - exit_price) * entry.size
            
            # Subtract fees
            pnl -= fees
            
            return pnl
            
        except Exception as e:
            logger.error(f"❌ Error calculating P&L: {e}")
            return 0.0

    def _save_trade_entry(self, trade_entry: TradeEntry):
        """Save trade entry to file"""
        try:
            filename = os.path.join(self.log_dir, f"entries_{datetime.now().strftime('%Y%m%d')}.json")
            
            entries = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    entries = json.load(f)
            
            entries.append(asdict(trade_entry))
            
            with open(filename, 'w') as f:
                json.dump(entries, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error saving trade entry: {e}")

    def _save_completed_trade(self, completed_trade: Dict):
        """Save completed trade to file"""
        try:
            filename = os.path.join(self.log_dir, f"completed_{datetime.now().strftime('%Y%m%d')}.json")
            
            trades = []
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    trades = json.load(f)
            
            trades.append(completed_trade)
            
            with open(filename, 'w') as f:
                json.dump(trades, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Error saving completed trade: {e}")
    
    def _load_trades(self):
        """Load existing trades from files"""
        try:
            # Load active trades (entries without exits)
            # This is simplified - in production you'd want better persistence
            pass
        except Exception as e:
            logger.error(f"❌ Error loading trades: {e}")

    def get_performance_stats(self) -> Dict:
        """Calculate performance statistics"""
        try:
            if not self.completed_trades:
                return {}
            
            winning_trades = [t for t in self.completed_trades if t['exit']['pnl'] > 0]
            losing_trades = [t for t in self.completed_trades if t['exit']['pnl'] <= 0]
            
            total_pnl = sum(t['exit']['pnl'] for t in self.completed_trades)
            win_rate = (len(winning_trades) / len(self.completed_trades)) * 100 if self.completed_trades else 0
            
            avg_profit = sum(t['exit']['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t['exit']['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            return {
                'total_trades': len(self.completed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance stats: {e}")
            return {}

# Create global instance
trade_logger = TradeLogger()
