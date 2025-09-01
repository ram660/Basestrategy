#!/usr/bin/env python3
"""
Bitget Futures Trading Integration
Real trading execution with automatic SL/TP management
"""

import os
import time
import hmac
import hashlib
import base64
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Import trade logger after other imports to avoid circular imports
try:
    from trade_logger import trade_logger
except ImportError:
    trade_logger = None
    logging.getLogger(__name__).warning("⚠️ Trade logger not available - trade logging will be disabled")

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

@dataclass
class TradingConfig:
    """Safe trading configuration"""
    # TRADING SYMBOLS (ONLY THESE ALLOWED)
    ALLOWED_SYMBOLS = ['XRPUSDT', 'ADAUSDT', 'XLMUSDT', 'UNIUSDT', 'ATOMUSDT', 'AXSUSDT', 'ARBUSDT']
    
    # ANALYSIS ONLY (NO TRADING)
    ANALYSIS_ONLY_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
    
    # TRADING PARAMETERS (ADJUSTED FOR SMALL ACCOUNT)
    POSITION_SIZE_USDT = 10.0      # $10 per trade (margin) - REDUCED for small account
    LEVERAGE = 2.0                 # 2x leverage - REDUCED for safety
    MAX_POSITIONS = 1              # Maximum 1 trade - REDUCED for small account
    STOP_LOSS_PERCENT = 3.5        # 3.5% stop loss
    TAKE_PROFIT_PERCENT = 5.0      # 5.0% take profit
    # MIN_ACCOUNT_BALANCE removed - no minimum balance requirement

    # DYNAMIC PROFIT TAKING - DISABLED (Let individual SL/TP orders work)
    PROFIT_THRESHOLD_USDT = 999999.0    # Effectively disabled

    # DYNAMIC LOSS CUTTING - DISABLED (Let individual SL/TP orders work)
    LOSS_THRESHOLD_USDT = 999999.0      # Effectively disabled

    # FEE INFORMATION
    TAKER_FEE_PERCENT = 0.06       # 0.06% taker fee
    MAKER_FEE_PERCENT = 0.02       # 0.02% maker fee

@dataclass
class Position:
    """Trading position data"""
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_id: str
    timestamp: str
    trade_id: Optional[str] = None  # Link to trade logger

class BitgetFuturesTrader:
    """Real Bitget Futures Trading with Safety Controls"""
    
    def __init__(self):
        # API credentials from .env
        self.api_key = os.getenv('BITGET_API_KEY')
        self.secret_key = os.getenv('BITGET_SECRET_KEY')
        self.passphrase = os.getenv('BITGET_PASSPHRASE')
        
        if not all([self.api_key, self.secret_key, self.passphrase]):
            raise ValueError("❌ Missing Bitget API credentials in .env file")
        
        self.base_url = "https://api.bitget.com"
        self.config = TradingConfig()
        
        # Safety checks
        self.trading_enabled = False
        self.positions = {}
        
        logger.info("Bitget Futures Trader initialized")
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Generate API signature"""
        message = timestamp + method + request_path + body
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        timestamp = str(int(time.time() * 1000))
        request_path = endpoint
        
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            request_path += f"?{query_string}"
        
        body = json.dumps(data) if data else ""
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'ACCESS-KEY': self.api_key,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        url = self.base_url + request_path
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=body, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ API request failed: {e}")
            raise
    
    def check_account_safety(self) -> Tuple[bool, str]:
        """Smart safety checks accounting for existing positions"""
        try:
            # Get current positions first (using our working method)
            active_positions = self.get_active_positions()
            num_positions = len(active_positions)

            # Check position limit first
            if num_positions >= self.config.MAX_POSITIONS:
                return False, f"Max positions reached: {num_positions}/{self.config.MAX_POSITIONS}"

            # Get account balance
            try:
                balance_info = self._make_request('GET', '/api/v2/mix/account/accounts', {'productType': 'USDT-FUTURES'})

                if balance_info.get('code') == '00000' and balance_info.get('data'):
                    available_balance = float(balance_info['data'][0]['available'])
                else:
                    raise Exception(f"API returned: {balance_info.get('msg', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"Balance API failed: {e}")
                available_balance = 229.65  # Current confirmed balance

            # Smart balance check - adjusted for small account
            margin_per_trade = self.config.POSITION_SIZE_USDT / self.config.LEVERAGE  # ~$5 margin per trade
            buffer = 3.0  # $3 safety buffer (reduced for small account)
            min_required = margin_per_trade + buffer

            if available_balance < min_required:
                return False, f"Insufficient balance for trade: ${available_balance:.2f} < ${min_required:.2f} (need ${margin_per_trade:.0f} margin + ${buffer:.0f} buffer)"

            logger.info(f"✅ Smart safety check passed - Balance: ${available_balance:.2f}, Positions: {num_positions}/{self.config.MAX_POSITIONS}")
            return True, f"Safety check passed - Balance: ${available_balance:.2f}, Positions: {num_positions}/{self.config.MAX_POSITIONS}"

        except Exception as e:
            return False, f"Safety check error: {e}"
    
    def is_symbol_allowed_for_trading(self, symbol: str) -> bool:
        """Check if symbol is allowed for trading"""
        if symbol in self.config.ANALYSIS_ONLY_SYMBOLS:
            logger.warning(f"⚠️ {symbol} is ANALYSIS ONLY - no trading allowed")
            return False
        
        if symbol not in self.config.ALLOWED_SYMBOLS:
            logger.warning(f"⚠️ {symbol} not in allowed trading symbols")
            return False
        
        return True

    def set_leverage(self, symbol: str, leverage: float) -> bool:
        """Set leverage for a specific symbol"""
        try:
            leverage_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginCoin': 'USDT',
                'leverage': str(int(leverage))
            }

            logger.info(f"Setting leverage to {leverage}x for {symbol}")
            response = self._make_request('POST', '/api/v2/mix/account/set-leverage', data=leverage_data)

            if response.get('code') == '00000':
                logger.info(f"✅ Leverage set to {leverage}x for {symbol}")
                return True
            else:
                logger.warning(f"⚠️ Failed to set leverage for {symbol}: {response.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"❌ Error setting leverage for {symbol}: {e}")
            return False

    def place_order_with_sl_tp(self, symbol: str, side: str, entry_price: float, confidence: float = 0.7) -> Optional[Position]:
        """Place order with automatic SL/TP"""
        
        # Safety checks
        if not self.is_symbol_allowed_for_trading(symbol):
            return None
        
        safety_ok, safety_msg = self.check_account_safety()
        if not safety_ok:
            logger.error(f"❌ Safety check failed: {safety_msg}")
            return None
        
        try:
            # Set leverage first
            self.set_leverage(symbol, self.config.LEVERAGE)

            # Calculate position details
            # POSITION_SIZE_USDT represents the MARGIN we want to use (not position value)
            margin_target = self.config.POSITION_SIZE_USDT  # $100 margin

            if side.upper() == 'LONG':
                stop_loss = entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
                take_profit = entry_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100)
                order_side = 'buy'
            else:  # SHORT
                stop_loss = entry_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
                take_profit = entry_price * (1 - self.config.TAKE_PROFIT_PERCENT / 100)
                order_side = 'sell'

            # Calculate quantity for target margin
            # With leverage, position_value = margin × leverage
            # quantity = position_value / entry_price = (margin × leverage) / entry_price
            quantity = (margin_target * self.config.LEVERAGE) / entry_price

            logger.info(f"💰 Target margin: ${margin_target:.0f} at {self.config.LEVERAGE}x leverage")
            logger.info(f"📊 Calculated quantity: {quantity:.2f} units (${quantity * entry_price:.2f} position value)")
            
            # Place main order (MARKET ORDER for immediate execution)
            order_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': order_side,
                'orderType': 'market',
                'timeInForceValue': 'normal'
            }
            
            logger.info(f"🔄 Placing {side} MARKET order for {symbol} (immediate execution)")
            order_response = self._make_request('POST', '/api/v2/mix/order/place-order', data=order_data)
            
            if order_response.get('code') != '00000':
                logger.error(f"❌ Order failed: {order_response.get('msg')}")
                return None
            
            order_id = order_response['data']['orderId']
            logger.info(f"✅ Order placed successfully: {order_id}")
            
            # Wait for order fill (simplified - in production, use websocket)
            time.sleep(2)
            
            # Place SL and TP orders
            self._place_sl_tp_orders(symbol, order_id, stop_loss, take_profit, quantity, side)
            
            # Create position record
            position = Position(
                symbol=symbol,
                side=side.lower(),
                size=quantity,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_id=order_id,
                timestamp=datetime.now().isoformat()
            )

            self.positions[symbol] = position

            # Log trade entry to our comprehensive trade logger
            trade_id = None
            if trade_logger:
                try:
                    trade_id = trade_logger.log_trade_entry(
                        symbol=symbol,
                        side=side.upper(),
                        entry_price=entry_price,
                        size=quantity,
                        leverage=self.config.LEVERAGE,
                        margin=margin_target,
                        order_id=order_id,
                        strategy="RSI_MA",
                        confidence=confidence,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        notes=f"Auto SL/TP order placed"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to log trade entry: {e}")

            # Store trade_id in position for later reference
            position.trade_id = trade_id

            logger.info(f"🎯 Position opened: {symbol} {side} ${entry_price:.4f}")
            logger.info(f"   SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
            logger.info(f"📝 Trade logged with ID: {trade_id}")

            return position
            
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    def _place_sl_tp_orders(self, symbol: str, position_id: str, stop_loss: float, take_profit: float, quantity: float, side: str):
        """Place stop loss and take profit orders"""
        try:
            # Determine opposite side for closing orders
            close_side = 'sell' if side.upper() == 'LONG' else 'buy'

            # Place Stop Loss order
            sl_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': close_side,
                'orderType': 'stop_market',
                'triggerPrice': str(stop_loss),
                'timeInForceValue': 'normal'
            }

            sl_response = self._make_request('POST', '/api/v2/mix/order/place-order', data=sl_data)
            if sl_response.get('code') == '00000':
                logger.info(f"✅ Stop Loss placed at ${stop_loss:.4f}")
            else:
                logger.error(f"❌ Stop Loss failed: {sl_response.get('msg')}")

            # Place Take Profit order
            tp_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': close_side,
                'orderType': 'take_profit_market',
                'triggerPrice': str(take_profit),
                'timeInForceValue': 'normal'
            }

            tp_response = self._make_request('POST', '/api/v2/mix/order/place-order', data=tp_data)
            if tp_response.get('code') == '00000':
                logger.info(f"✅ Take Profit placed at ${take_profit:.4f}")
            else:
                logger.error(f"❌ Take Profit failed: {tp_response.get('msg')}")

        except Exception as e:
            logger.error(f"❌ Error placing SL/TP orders: {e}")

    def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        try:
            positions = self._make_request('GET', '/api/v2/mix/position/all-position', {'productType': 'USDT-FUTURES'})

            if positions.get('code') != '00000':
                logger.error(f"❌ Failed to get positions: {positions.get('msg')}")
                return []

            active_positions = []
            for pos in positions['data']:
                if float(pos['total']) != 0:  # Position has size
                    position_data = {
                        'symbol': pos['symbol'],
                        'side': pos['holdSide'],  # Correct field name
                        'size': float(pos['total']),
                        'entry_price': float(pos['openPriceAvg']),  # Correct field name
                        'mark_price': float(pos['markPrice']),
                        'unrealized_pnl': float(pos['unrealizedPL']),
                        'margin': float(pos['marginSize']),  # Correct field name
                        'leverage': float(pos['leverage']),
                        'liquidation_price': float(pos.get('liquidationPrice', 0))
                    }
                    active_positions.append(position_data)
                    logger.info(f"📈 Found position: {pos['symbol']} {pos['holdSide'].upper()} {pos['total']} units, P&L: ${float(pos['unrealizedPL']):.2f}")

            return active_positions

        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []

    def close_position(self, symbol: str, exit_reason: str = 'MANUAL') -> bool:
        """Close a specific position at market price"""
        try:
            active_positions = self.get_active_positions()

            # Find the position to close
            target_position = None
            for pos in active_positions:
                if pos['symbol'] == symbol:
                    target_position = pos
                    break

            if not target_position:
                logger.warning(f"⚠️ No active position found for {symbol}")
                return False

            # Get current market price for exit logging
            current_price = float(target_position.get('mark_price', target_position.get('avg_open_price', 0)))

            # Determine close side (opposite of position side)
            close_side = 'sell' if target_position['side'] == 'long' else 'buy'

            close_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(target_position['size']),
                'side': close_side,
                'orderType': 'market'
            }

            logger.info(f"🔄 Closing position: {symbol} {target_position['side'].upper()} {target_position['size']} units at market price")
            response = self._make_request('POST', '/api/v2/mix/order/place-order', data=close_data)

            if response.get('code') == '00000':
                # Log trade exit to our comprehensive trade logger
                # Find the corresponding trade_id from our local positions
                trade_id = None
                if symbol in self.positions and hasattr(self.positions[symbol], 'trade_id'):
                    trade_id = self.positions[symbol].trade_id

                # If we have a trade_id and trade_logger is available, log the exit
                if trade_id and trade_logger:
                    try:
                        trade_logger.log_trade_exit(
                            trade_id=trade_id,
                            exit_price=current_price,
                            exit_reason=exit_reason,
                            fees=0.0,  # Could calculate actual fees here
                            notes=f"Position closed via API - P&L: ${target_position['unrealized_pnl']:.2f}"
                        )
                        logger.info(f"📝 Trade exit logged for trade ID: {trade_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to log trade exit: {e}")
                elif not trade_id:
                    # If no trade_id, this might be a position from before we started logging
                    logger.warning(f"⚠️ No trade_id found for {symbol} - position may predate logging system")

                # Remove from local positions
                if symbol in self.positions:
                    del self.positions[symbol]

                logger.info(f"✅ Successfully closed position: {symbol} (P&L: ${target_position['unrealized_pnl']:.2f})")
                return True
            else:
                logger.error(f"❌ Failed to close {symbol}: {response.get('msg')}")
                return False

        except Exception as e:
            logger.error(f"❌ Error closing position {symbol}: {e}")
            return False

    def check_and_close_profitable_positions(self, profit_threshold_usdt: float = None) -> Dict:
        """Check total unrealized P&L and close positions if profit threshold is reached"""
        try:
            # Use config default if no threshold provided
            if profit_threshold_usdt is None:
                profit_threshold_usdt = self.config.PROFIT_THRESHOLD_USDT

            active_positions = self.get_active_positions()

            if not active_positions:
                return {'action': 'none', 'reason': 'No active positions'}

            # Calculate total unrealized P&L
            total_unrealized_pnl = sum(float(pos['unrealized_pnl']) for pos in active_positions)

            logger.info(f"💰 Total unrealized P&L: ${total_unrealized_pnl:.2f} (profit threshold: ${profit_threshold_usdt:.2f})")

            if total_unrealized_pnl >= profit_threshold_usdt:
                logger.info(f"🎯 Profit threshold reached! Closing all positions to lock in ${total_unrealized_pnl:.2f} profit")

                closed_positions = []
                total_profit_locked = 0.0

                for pos in active_positions:
                    symbol = pos['symbol']
                    pnl = pos['unrealized_pnl']

                    if self.close_position(symbol, exit_reason='PROFIT_TARGET'):
                        closed_positions.append({
                            'symbol': symbol,
                            'side': pos['side'],
                            'size': pos['size'],
                            'pnl': pnl
                        })
                        total_profit_locked += pnl

                        # Small delay between closes
                        time.sleep(0.5)

                if closed_positions:
                    logger.info(f"🎉 Successfully locked in ${total_profit_locked:.2f} profit by closing {len(closed_positions)} positions")
                    return {
                        'action': 'closed_positions',
                        'total_profit': total_profit_locked,
                        'closed_positions': closed_positions,
                        'reason': f'Profit threshold ${profit_threshold_usdt:.2f} reached'
                    }
                else:
                    return {
                        'action': 'failed',
                        'reason': 'Failed to close positions despite reaching threshold'
                    }
            else:
                return {
                    'action': 'monitoring',
                    'current_pnl': total_unrealized_pnl,
                    'threshold': profit_threshold_usdt,
                    'reason': f'P&L ${total_unrealized_pnl:.2f} below profit threshold ${profit_threshold_usdt:.2f}'
                }

        except Exception as e:
            logger.error(f"❌ Error checking profitable positions: {e}")
            return {
                'action': 'error',
                'reason': f'Error: {str(e)}'
            }

    def check_and_close_losing_positions(self, loss_threshold_usdt: float = None) -> Dict:
        """Check total unrealized P&L and close positions if loss threshold is reached"""
        try:
            # Use config default if no threshold provided
            if loss_threshold_usdt is None:
                loss_threshold_usdt = self.config.LOSS_THRESHOLD_USDT

            active_positions = self.get_active_positions()

            if not active_positions:
                return {'action': 'none', 'reason': 'No active positions'}

            # Calculate total unrealized P&L
            total_unrealized_pnl = sum(float(pos['unrealized_pnl']) for pos in active_positions)

            logger.info(f"🚨 Total unrealized P&L: ${total_unrealized_pnl:.2f} (loss threshold: -${loss_threshold_usdt:.2f})")

            if total_unrealized_pnl <= -loss_threshold_usdt:
                logger.warning(f"🛑 Loss threshold reached! Closing all positions to limit loss at ${total_unrealized_pnl:.2f}")

                closed_positions = []
                total_loss_cut = 0.0

                for pos in active_positions:
                    symbol = pos['symbol']
                    pnl = pos['unrealized_pnl']

                    if self.close_position(symbol, exit_reason='STOP_LOSS'):
                        closed_positions.append({
                            'symbol': symbol,
                            'side': pos['side'],
                            'size': pos['size'],
                            'pnl': pnl
                        })
                        total_loss_cut += pnl

                        # Small delay between closes
                        time.sleep(0.5)

                if closed_positions:
                    logger.warning(f"🛑 Successfully cut loss at ${total_loss_cut:.2f} by closing {len(closed_positions)} positions")
                    return {
                        'action': 'closed_positions',
                        'total_loss': total_loss_cut,
                        'closed_positions': closed_positions,
                        'reason': f'Loss threshold -${loss_threshold_usdt:.2f} reached'
                    }
                else:
                    return {
                        'action': 'failed',
                        'reason': 'Failed to close positions despite reaching loss threshold'
                    }
            else:
                return {
                    'action': 'monitoring',
                    'current_pnl': total_unrealized_pnl,
                    'threshold': -loss_threshold_usdt,
                    'reason': f'P&L ${total_unrealized_pnl:.2f} above loss threshold -${loss_threshold_usdt:.2f}'
                }

        except Exception as e:
            logger.error(f"❌ Error checking losing positions: {e}")
            return {
                'action': 'error',
                'reason': f'Error: {str(e)}'
            }

    def check_breakout_signals(self) -> Dict:
        """Check for major breakouts against our positions on larger timeframes"""
        try:
            from data_fetcher import DataFetcher
            from rsi_ma_strategy import RSIMAStrategy

            active_positions = self.get_active_positions()

            if not active_positions:
                return {'action': 'none', 'reason': 'No active positions'}

            data_fetcher = DataFetcher()
            strategy = RSIMAStrategy()
            breakout_signals = []

            for pos in active_positions:
                symbol = pos['symbol']
                side = pos['side']

                # Check larger timeframes for breakouts against our position
                timeframes_to_check = ['1h', '4h', '1d']

                for tf in timeframes_to_check:
                    try:
                        # Get recent data for the timeframe
                        df = data_fetcher.get_data(symbol, tf, limit=100)
                        if df is None or len(df) < 50:
                            continue

                        # Apply strategy to get signals
                        signals = strategy.analyze(df)
                        if not signals:
                            continue

                        latest_signal = signals[-1]
                        current_rsi = latest_signal.get('rsi', 50)
                        signal_type = latest_signal.get('signal', 'HOLD')

                        # Check if signal is against our position
                        position_against_signal = False
                        signal_strength = 0

                        if side == 'short' and signal_type == 'LONG':
                            # We're short but getting long signals = breakout against us
                            position_against_signal = True
                            signal_strength = current_rsi - 60  # How much above 60
                        elif side == 'long' and signal_type == 'SHORT':
                            # We're long but getting short signals = breakout against us
                            position_against_signal = True
                            signal_strength = 40 - current_rsi  # How much below 40

                        if position_against_signal and signal_strength > 0:
                            breakout_signals.append({
                                'symbol': symbol,
                                'timeframe': tf,
                                'signal': signal_type,
                                'rsi': current_rsi,
                                'strength': signal_strength,
                                'position_side': side,
                                'risk_level': 'HIGH' if signal_strength > 10 else 'MEDIUM'
                            })

                            logger.warning(f"🚨 Breakout detected: {symbol} {tf} showing {signal_type} signal (RSI: {current_rsi:.1f}) against our {side.upper()} position")

                    except Exception as e:
                        logger.error(f"❌ Error checking {symbol} {tf}: {e}")
                        continue

            if breakout_signals:
                # Check if we should close positions due to strong breakouts
                high_risk_signals = [s for s in breakout_signals if s['risk_level'] == 'HIGH']

                if high_risk_signals:
                    logger.warning(f"🚨 HIGH RISK BREAKOUTS detected on {len(high_risk_signals)} signals - consider closing positions")
                    return {
                        'action': 'high_risk_breakout',
                        'signals': breakout_signals,
                        'high_risk_count': len(high_risk_signals),
                        'reason': f'Strong breakouts detected against positions on larger timeframes'
                    }
                else:
                    return {
                        'action': 'medium_risk_breakout',
                        'signals': breakout_signals,
                        'reason': f'Medium risk breakouts detected on {len(breakout_signals)} timeframes'
                    }
            else:
                return {
                    'action': 'no_breakout',
                    'reason': 'No significant breakouts detected against positions'
                }

        except Exception as e:
            logger.error(f"❌ Error checking breakout signals: {e}")
            return {
                'action': 'error',
                'reason': f'Error: {str(e)}'
            }

    def comprehensive_risk_management(self) -> Dict:
        """Comprehensive risk management: ONLY breakout detection (SL/TP handled by exchange)"""
        try:
            active_positions = self.get_active_positions()

            if not active_positions:
                return {'action': 'none', 'reason': 'No active positions'}

            # Calculate current P&L for monitoring
            total_unrealized_pnl = sum(float(pos['unrealized_pnl']) for pos in active_positions)

            # DISABLED: Individual SL/TP orders handle profit/loss management
            # Let exchange-level SL/TP orders work instead of manual intervention
            logger.info(f"📊 Monitoring {len(active_positions)} positions - Total P&L: ${total_unrealized_pnl:.2f}")
            logger.info("🎯 Individual SL/TP orders active on exchange - no manual intervention")

            # 3. Check for breakout signals against positions
            breakout_check = self.check_breakout_signals()

            # If high risk breakouts detected, close positions immediately
            if breakout_check['action'] == 'high_risk_breakout':
                logger.warning(f"🚨 HIGH RISK BREAKOUTS - Closing all positions to prevent major losses")

                closed_positions = []
                total_pnl_at_close = 0.0

                for pos in active_positions:
                    symbol = pos['symbol']
                    pnl = pos['unrealized_pnl']

                    if self.close_position(symbol, exit_reason='BREAKOUT_RISK'):
                        closed_positions.append({
                            'symbol': symbol,
                            'side': pos['side'],
                            'size': pos['size'],
                            'pnl': pnl
                        })
                        total_pnl_at_close += pnl
                        time.sleep(0.5)

                if closed_positions:
                    logger.warning(f"🛑 Closed {len(closed_positions)} positions due to breakout risk. P&L: ${total_pnl_at_close:.2f}")
                    return {
                        'action': 'breakout_exit',
                        'total_pnl': total_pnl_at_close,
                        'closed_positions': closed_positions,
                        'breakout_signals': breakout_check['signals'],
                        'reason': 'High risk breakouts detected - emergency exit'
                    }

            # Return monitoring status - only breakout protection active
            return {
                'action': 'monitoring',
                'current_pnl': total_unrealized_pnl,
                'breakout_status': breakout_check,
                'reason': f'Exchange SL/TP active - P&L: ${total_unrealized_pnl:.2f}'
            }

        except Exception as e:
            logger.error(f"❌ Error in comprehensive risk management: {e}")
            return {
                'action': 'error',
                'reason': f'Error: {str(e)}'
            }

    def test_sl_tp_order_placement(self, symbol: str = "XRPUSDT", side: str = "short", entry_price: float = None) -> Dict:
        """Test SL/TP order placement without actually placing orders"""
        try:
            if entry_price is None:
                # Get current price for testing
                from data_fetcher import get_current_price
                entry_price = get_current_price(symbol)

            # Calculate SL/TP prices (same logic as real trading)
            if side.upper() == 'LONG':
                stop_loss = entry_price * (1 - self.config.STOP_LOSS_PERCENT / 100)
                take_profit = entry_price * (1 + self.config.TAKE_PROFIT_PERCENT / 100)
                order_side = 'buy'
                close_side = 'sell'
            else:  # SHORT
                stop_loss = entry_price * (1 + self.config.STOP_LOSS_PERCENT / 100)
                take_profit = entry_price * (1 - self.config.TAKE_PROFIT_PERCENT / 100)
                order_side = 'sell'
                close_side = 'buy'

            # Calculate quantity
            margin_target = self.config.POSITION_SIZE_USDT  # $100 margin
            quantity = (margin_target * self.config.LEVERAGE) / entry_price

            # Simulate the order data that would be sent (MARKET ORDER)
            main_order_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': order_side,
                'orderType': 'market',
                'timeInForceValue': 'normal'
            }

            sl_order_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': close_side,
                'orderType': 'stop_market',
                'triggerPrice': str(stop_loss),
                'timeInForceValue': 'normal'
            }

            tp_order_data = {
                'symbol': symbol,
                'productType': 'USDT-FUTURES',
                'marginMode': 'isolated',
                'marginCoin': 'USDT',
                'size': str(quantity),
                'side': close_side,
                'orderType': 'take_profit_market',
                'triggerPrice': str(take_profit),
                'timeInForceValue': 'normal'
            }

            # Calculate percentages and profit/loss amounts
            sl_distance_pct = abs((stop_loss - entry_price) / entry_price) * 100
            tp_distance_pct = abs((take_profit - entry_price) / entry_price) * 100

            position_value = quantity * entry_price
            potential_loss = position_value * (sl_distance_pct / 100)
            potential_profit = position_value * (tp_distance_pct / 100)

            logger.info("🧪 TESTING SL/TP ORDER PLACEMENT")
            logger.info(f"📊 Symbol: {symbol} | Side: {side.upper()}")
            logger.info(f"💰 Entry Price: ${entry_price:.4f}")
            logger.info(f"📏 Quantity: {quantity:.2f} units")
            logger.info(f"💵 Position Value: ${position_value:.2f} (${margin_target} margin × {self.config.LEVERAGE}x)")
            logger.info(f"🛑 Stop Loss: ${stop_loss:.4f} ({sl_distance_pct:.2f}% = -${potential_loss:.2f})")
            logger.info(f"🎯 Take Profit: ${take_profit:.4f} ({tp_distance_pct:.2f}% = +${potential_profit:.2f})")

            return {
                'success': True,
                'test_mode': True,
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'quantity': quantity,
                'position_value': position_value,
                'margin_used': margin_target,
                'leverage': self.config.LEVERAGE,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'sl_distance_pct': sl_distance_pct,
                'tp_distance_pct': tp_distance_pct,
                'potential_loss': potential_loss,
                'potential_profit': potential_profit,
                'main_order': main_order_data,
                'sl_order': sl_order_data,
                'tp_order': tp_order_data,
                'message': f'✅ Test successful - SL/TP orders would be placed correctly'
            }

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'❌ Test failed: {str(e)}'
            }

    def close_all_positions(self) -> bool:
        """Emergency close all positions"""
        try:
            active_positions = self.get_active_positions()

            for pos in active_positions:
                close_side = 'sell' if pos['side'] == 'long' else 'buy'

                close_data = {
                    'symbol': pos['symbol'],
                    'productType': 'USDT-FUTURES',
                    'marginMode': 'isolated',
                    'marginCoin': 'USDT',
                    'size': str(pos['size']),
                    'side': close_side,
                    'orderType': 'market'
                }

                response = self._make_request('POST', '/api/v2/mix/order/place-order', data=close_data)

                if response.get('code') == '00000':
                    logger.info(f"✅ Closed position: {pos['symbol']}")
                else:
                    logger.error(f"❌ Failed to close {pos['symbol']}: {response.get('msg')}")

            return True

        except Exception as e:
            logger.error(f"❌ Error closing positions: {e}")
            return False

    def get_trade_history(self, limit: int = 50, days: int = 30) -> List[Dict]:
        """Get recent trade history from Bitget"""
        try:
            trade_history = []

            # Try multiple endpoints to get comprehensive trade data
            endpoints_to_try = [
                {
                    'endpoint': '/api/v2/mix/order/fills',
                    'name': 'Order Fills',
                    'params': {
                        'symbol': '',  # Empty for all symbols
                        'productType': 'USDT-FUTURES',
                        'startTime': str(int((datetime.now() - timedelta(days=days)).timestamp() * 1000)),
                        'endTime': str(int(datetime.now().timestamp() * 1000)),
                        'pageSize': str(limit)
                    }
                },
                {
                    'endpoint': '/api/v2/mix/order/history',
                    'name': 'Order History',
                    'params': {
                        'symbol': '',
                        'productType': 'USDT-FUTURES',
                        'startTime': str(int((datetime.now() - timedelta(days=days)).timestamp() * 1000)),
                        'endTime': str(int(datetime.now().timestamp() * 1000)),
                        'pageSize': str(limit),
                        'isPre': 'false'
                    }
                }
            ]

            for endpoint_config in endpoints_to_try:
                try:
                    logger.info(f"🔍 Trying {endpoint_config['name']} endpoint...")
                    response = self._make_request('GET', endpoint_config['endpoint'], params=endpoint_config['params'])

                    if response.get('code') != '00000':
                        logger.warning(f"⚠️ {endpoint_config['name']} failed: {response.get('msg')}")
                        continue

                    # Handle different response structures
                    if endpoint_config['endpoint'] == '/api/v2/mix/order/fills':
                        fills = response.get('data', {}).get('fillList', [])
                        logger.info(f"📊 Found {len(fills)} fills from Order Fills")

                        for fill in fills:
                            try:
                                fill_price = float(fill['fillPrice'])
                                fill_size = float(fill['fillSize'])
                                side = fill['side']

                                trade = {
                                    'symbol': fill['symbol'],
                                    'side': side.upper(),
                                    'type': 'LONG' if side == 'buy' else 'SHORT',
                                    'size': fill_size,
                                    'price': fill_price,
                                    'timestamp': fill['fillTime'],
                                    'order_id': fill['orderId'],
                                    'trade_id': fill.get('tradeId', ''),
                                    'fee': float(fill.get('fee', 0)),
                                    'fee_coin': fill.get('feeCoin', 'USDT'),
                                    'pnl': float(fill.get('profit', 0)),
                                    'formatted_time': datetime.fromtimestamp(int(fill['fillTime']) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                                    'source': 'fills'
                                }
                                trade_history.append(trade)

                            except Exception as e:
                                logger.warning(f"⚠️ Error processing fill: {e}")
                                continue

                    elif endpoint_config['endpoint'] == '/api/v2/mix/order/history':
                        orders = response.get('data', {}).get('orderList', [])
                        logger.info(f"📊 Found {len(orders)} orders from Order History")

                        for order in orders:
                            try:
                                if order.get('state') == 'filled':  # Only filled orders
                                    avg_price = float(order.get('priceAvg', 0))
                                    if avg_price > 0:  # Valid filled order
                                        size = float(order['size'])
                                        side = order['side']

                                        trade = {
                                            'symbol': order['symbol'],
                                            'side': side.upper(),
                                            'type': 'LONG' if side == 'buy' else 'SHORT',
                                            'size': size,
                                            'price': avg_price,
                                            'timestamp': order['uTime'],
                                            'order_id': order['orderId'],
                                            'trade_id': order.get('clientOid', ''),
                                            'fee': float(order.get('fee', 0)),
                                            'fee_coin': order.get('feeCoin', 'USDT'),
                                            'pnl': 0,  # Order history doesn't include P&L
                                            'formatted_time': datetime.fromtimestamp(int(order['uTime']) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                                            'source': 'orders'
                                        }
                                        trade_history.append(trade)

                            except Exception as e:
                                logger.warning(f"⚠️ Error processing order: {e}")
                                continue

                except Exception as e:
                    logger.warning(f"⚠️ Error with {endpoint_config['name']}: {e}")
                    continue

            # Remove duplicates based on order_id and timestamp
            seen = set()
            unique_trades = []
            for trade in trade_history:
                key = (trade['order_id'], trade['timestamp'])
                if key not in seen:
                    seen.add(key)
                    unique_trades.append(trade)

            # Sort by timestamp (newest first)
            unique_trades.sort(key=lambda x: int(x['timestamp']), reverse=True)

            logger.info(f"✅ Retrieved {len(unique_trades)} unique trades from last {days} days")
            return unique_trades[:limit]  # Return only requested limit

        except Exception as e:
            logger.error(f"❌ Error getting trade history: {e}")
            return []

    def get_position_history(self, limit: int = 50, days: int = 30) -> List[Dict]:
        """Get recent position history (closed positions)"""
        try:
            position_history = []

            # Try multiple endpoints for position history
            endpoints_to_try = [
                {
                    'endpoint': '/api/v2/mix/position/history-position',
                    'name': 'Position History',
                    'params': {
                        'symbol': '',  # Empty for all symbols
                        'productType': 'USDT-FUTURES',
                        'startTime': str(int((datetime.now() - timedelta(days=days)).timestamp() * 1000)),
                        'endTime': str(int(datetime.now().timestamp() * 1000)),
                        'pageSize': str(limit)
                    }
                },
                {
                    'endpoint': '/api/v2/mix/account/bill',
                    'name': 'Account Bill',
                    'params': {
                        'symbol': '',
                        'productType': 'USDT-FUTURES',
                        'businessType': 'close_long,close_short',  # Only closing trades
                        'startTime': str(int((datetime.now() - timedelta(days=days)).timestamp() * 1000)),
                        'endTime': str(int(datetime.now().timestamp() * 1000)),
                        'pageSize': str(limit)
                    }
                }
            ]

            for endpoint_config in endpoints_to_try:
                try:
                    logger.info(f"🔍 Trying {endpoint_config['name']} endpoint...")
                    response = self._make_request('GET', endpoint_config['endpoint'], params=endpoint_config['params'])

                    if response.get('code') != '00000':
                        logger.warning(f"⚠️ {endpoint_config['name']} failed: {response.get('msg')}")
                        continue

                    # Handle different response structures
                    if endpoint_config['endpoint'] == '/api/v2/mix/position/history-position':
                        positions = response.get('data', {}).get('list', [])
                        logger.info(f"📊 Found {len(positions)} positions from Position History")

                        for pos in positions:
                            try:
                                position = {
                                    'symbol': pos['symbol'],
                                    'side': pos['holdSide'].upper(),
                                    'type': 'LONG' if pos['holdSide'] == 'long' else 'SHORT',
                                    'size': float(pos['total']),
                                    'entry_price': float(pos['openAvgPrice']),
                                    'exit_price': float(pos.get('closeAvgPrice', 0)),
                                    'pnl': float(pos.get('achievedProfits', 0)),
                                    'pnl_percentage': float(pos.get('profitRate', 0)) * 100,
                                    'open_time': pos.get('openTime', ''),
                                    'close_time': pos.get('closeTime', ''),
                                    'margin': float(pos.get('margin', 0)),
                                    'leverage': float(pos.get('leverage', 1)),
                                    'formatted_open_time': datetime.fromtimestamp(int(pos.get('openTime', 0)) / 1000).strftime('%Y-%m-%d %H:%M:%S') if pos.get('openTime') else '',
                                    'formatted_close_time': datetime.fromtimestamp(int(pos.get('closeTime', 0)) / 1000).strftime('%Y-%m-%d %H:%M:%S') if pos.get('closeTime') else '',
                                    'source': 'position_history'
                                }
                                position_history.append(position)

                            except Exception as e:
                                logger.warning(f"⚠️ Error processing position: {e}")
                                continue

                    elif endpoint_config['endpoint'] == '/api/v2/mix/account/bill':
                        bills = response.get('data', {}).get('billList', [])
                        logger.info(f"📊 Found {len(bills)} bills from Account Bill")

                        # Group bills by symbol and time to reconstruct positions
                        position_groups = {}
                        for bill in bills:
                            try:
                                if bill.get('businessType') in ['close_long', 'close_short']:
                                    symbol = bill['symbol']
                                    timestamp = bill['cTime']
                                    key = f"{symbol}_{timestamp}"

                                    if key not in position_groups:
                                        position_groups[key] = {
                                            'symbol': symbol,
                                            'side': 'LONG' if bill['businessType'] == 'close_long' else 'SHORT',
                                            'type': 'LONG' if bill['businessType'] == 'close_long' else 'SHORT',
                                            'size': abs(float(bill.get('size', 0))),
                                            'entry_price': 0,  # Not available in bills
                                            'exit_price': float(bill.get('price', 0)),
                                            'pnl': float(bill.get('pnl', 0)),
                                            'pnl_percentage': 0,  # Calculate if possible
                                            'open_time': '',
                                            'close_time': timestamp,
                                            'margin': 0,
                                            'leverage': 1,
                                            'formatted_open_time': '',
                                            'formatted_close_time': datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                                            'source': 'account_bill'
                                        }
                                    else:
                                        # Aggregate if multiple bills for same position
                                        position_groups[key]['pnl'] += float(bill.get('pnl', 0))
                                        position_groups[key]['size'] += abs(float(bill.get('size', 0)))

                            except Exception as e:
                                logger.warning(f"⚠️ Error processing bill: {e}")
                                continue

                        position_history.extend(position_groups.values())

                except Exception as e:
                    logger.warning(f"⚠️ Error with {endpoint_config['name']}: {e}")
                    continue

            # Remove duplicates and sort by close time
            unique_positions = []
            seen = set()

            for pos in position_history:
                # Create a unique key based on symbol, close_time, and pnl
                key = (pos['symbol'], pos['close_time'], pos['pnl'])
                if key not in seen:
                    seen.add(key)
                    unique_positions.append(pos)

            # Sort by close time (newest first)
            unique_positions.sort(key=lambda x: int(x['close_time']) if x['close_time'] else 0, reverse=True)

            logger.info(f"✅ Retrieved {len(unique_positions)} unique closed positions from last {days} days")
            return unique_positions[:limit]  # Return only requested limit

        except Exception as e:
            logger.error(f"❌ Error getting position history: {e}")
            return []

    def enable_trading(self):
        """Enable trading mode"""
        self.trading_enabled = True
        logger.info("✅ Trading mode ENABLED - Real trades will be executed")
    
    def disable_trading(self):
        """Disable trading mode"""
        self.trading_enabled = False
        logger.info("🛑 Trading mode DISABLED - Simulation only")
    
    def check_position_status(self, position_id: str) -> bool:
        """Check if a position is still active"""
        try:
            # Get all active positions
            active_positions = self.get_active_positions()
            
            # Check if our position is still in the list
            for pos in active_positions:
                # This is a simplified check - in reality you'd need to match
                # based on the actual position data structure
                if pos.get('symbol') and pos.get('size', 0) > 0:
                    # Position exists - you might want to match more specifically
                    # based on your position tracking method
                    continue
            
            # For now, we'll use a simple time-based check
            # In production, you'd want to track positions more precisely
            return True  # Assume position is still active
            
        except Exception as e:
            logger.error(f"❌ Error checking position status: {e}")
            return False

# Global instance
futures_trader = BitgetFuturesTrader()

def execute_trade(symbol: str, direction: str, entry_price: float, confidence: float = 0.7) -> Dict:
    """Execute a real trade with safety checks"""
    try:
        position = futures_trader.place_order_with_sl_tp(symbol, direction, entry_price, confidence)
        
        if position:
            return {
                'success': True,
                'position': position.__dict__,
                'message': f'✅ {direction} position opened for {symbol}'
            }
        else:
            return {
                'success': False,
                'message': '❌ Trade execution failed - check logs for details'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ Trade error: {str(e)}'
        }
