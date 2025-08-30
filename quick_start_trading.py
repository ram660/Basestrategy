#!/usr/bin/env python3
"""
Quick Start Real Trading
Simple script to start live trading with current balance
"""

import os
import sys

def main():
    print("\n" + "="*60)
    print("🚀 STARTING REAL TRADING SYSTEM")
    print("="*60)
    
    # Show current configuration
    from bitget_futures_trader import TradingConfig
    config = TradingConfig()
    
    print(f"\n📊 CURRENT SETTINGS (Adjusted for your balance):")
    print(f"   💰 Position Size: ${config.POSITION_SIZE_USDT} USDT margin")
    print(f"   📈 Leverage: {config.LEVERAGE}x")
    print(f"   🛡️ Stop Loss: {config.STOP_LOSS_PERCENT}%")
    print(f"   🎯 Take Profit: {config.TAKE_PROFIT_PERCENT}%")
    print(f"   🔢 Max Positions: {config.MAX_POSITIONS}")
    
    # Calculate risk
    risk_per_trade = config.POSITION_SIZE_USDT * config.STOP_LOSS_PERCENT / 100
    profit_per_trade = config.POSITION_SIZE_USDT * config.TAKE_PROFIT_PERCENT / 100
    
    print(f"\n💡 RISK/REWARD ANALYSIS:")
    print(f"   💸 Risk per trade: ~${risk_per_trade:.2f}")
    print(f"   💰 Profit potential: ~${profit_per_trade:.2f}")
    print(f"   📊 Risk/Reward Ratio: 1:{profit_per_trade/risk_per_trade:.2f}")
    
    # Test API
    print(f"\n🔗 Testing API Connection...")
    try:
        from bitget_futures_trader import BitgetFuturesTrader
        trader = BitgetFuturesTrader()
        safety_ok, safety_msg = trader.check_account_safety()
        
        if safety_ok:
            print(f"✅ {safety_msg}")
        else:
            print(f"❌ {safety_msg}")
            input("Press Enter to exit...")
            return
    except Exception as e:
        print(f"❌ API Error: {e}")
        input("Press Enter to exit...")
        return
    
    print(f"\n⚠️ WARNING: This will execute REAL trades!")
    confirm = input("Type 'START' to begin real trading: ")
    
    if confirm != 'START':
        print("❌ Cancelled")
        return
    
    print(f"\n🚀 Starting live trading system...")
    
    # Start the live trading system
    try:
        os.system('python live_trading_system.py')
    except KeyboardInterrupt:
        print(f"\n🛑 Trading stopped by user")

if __name__ == "__main__":
    main()
