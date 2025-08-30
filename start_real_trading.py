#!/usr/bin/env python3
"""
Real Trading System Startup
Complete setup for live trading with all safety checks
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def print_banner():
    """Print startup banner"""
    print("\n" + "="*70)
    print("🚀 REAL TRADING SYSTEM STARTUP")
    print("RSI-MA Strategy with Bitget Futures")
    print("="*70)

def check_requirements():
    """Check if all requirements are met"""
    print("\n🔍 Checking System Requirements...")
    
    # Check .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("   Please create .env file with your API credentials")
        return False
    
    # Check API credentials
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['BITGET_API_KEY', 'BITGET_SECRET_KEY', 'BITGET_PASSPHRASE']
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing {var} in .env file!")
            return False
    
    print("✅ API credentials found")
    
    # Check Python packages
    try:
        import requests
        import pandas
        import numpy
        print("✅ Required packages available")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def test_api_connection():
    """Test Bitget API connection"""
    print("\n🔗 Testing API Connection...")
    
    try:
        from bitget_futures_trader import BitgetFuturesTrader
        trader = BitgetFuturesTrader()
        
        safety_ok, safety_msg = trader.check_account_safety()
        if safety_ok:
            print(f"✅ API Connection: {safety_msg}")
            return True
        else:
            print(f"❌ API Safety Check Failed: {safety_msg}")
            return False
            
    except Exception as e:
        print(f"❌ API Connection Failed: {e}")
        return False

def show_trading_config():
    """Display trading configuration"""
    print("\n⚙️ TRADING CONFIGURATION:")
    
    from bitget_futures_trader import TradingConfig
    config = TradingConfig()
    
    print(f"   🎯 Trading Symbols: {config.ALLOWED_SYMBOLS}")
    print(f"   📊 Analysis Only: {config.ANALYSIS_ONLY_SYMBOLS}")
    print(f"   💰 Position Size: ${config.POSITION_SIZE_USDT} USDT margin")
    print(f"   📈 Leverage: {config.LEVERAGE}x")
    print(f"   🛡️ Stop Loss: {config.STOP_LOSS_PERCENT}%")
    print(f"   🎯 Take Profit: {config.TAKE_PROFIT_PERCENT}%")
    print(f"   🔢 Max Positions: {config.MAX_POSITIONS}")
    
    # Calculate risk
    risk_per_trade = config.POSITION_SIZE_USDT * config.STOP_LOSS_PERCENT / 100
    max_risk = risk_per_trade * config.MAX_POSITIONS
    
    print(f"\n💡 RISK ANALYSIS:")
    print(f"   Risk per trade: ~${risk_per_trade:.2f}")
    print(f"   Maximum total risk: ~${max_risk:.2f}")
    print(f"   Profit potential per trade: ~${config.POSITION_SIZE_USDT * config.TAKE_PROFIT_PERCENT / 100:.2f}")

def get_user_confirmation():
    """Get user confirmation for live trading"""
    print("\n" + "="*70)
    print("⚠️  IMPORTANT WARNINGS:")
    print("   • This will execute REAL trades with REAL money")
    print("   • You could lose money if markets move against you")
    print("   • Always monitor your positions")
    print("   • Start with small position sizes")
    print("="*70)
    
    print("\n📋 CHECKLIST:")
    print("   ✓ I understand this uses real money")
    print("   ✓ I have tested my strategy")
    print("   ✓ I am comfortable with the risk levels")
    print("   ✓ I will monitor the system actively")
    
    while True:
        choice = input("\nDo you want to start REAL TRADING? (yes/no): ").lower().strip()
        if choice in ['yes', 'y']:
            return True
        elif choice in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")

def start_dashboard():
    """Start the dashboard in the background"""
    print("\n🌐 Starting Dashboard...")
    try:
        dashboard_process = subprocess.Popen([
            sys.executable, 'dashboard.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a moment for dashboard to start
        time.sleep(3)
        
        # Try to open in browser
        webbrowser.open('http://localhost:7000')
        print("✅ Dashboard started at http://localhost:7000")
        return dashboard_process
        
    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        return None

def start_live_trading():
    """Start the live trading system"""
    print("\n🤖 Starting Live Trading System...")
    try:
        trading_process = subprocess.Popen([
            sys.executable, 'live_trading_system.py'
        ])
        print("✅ Live trading system started")
        return trading_process
        
    except Exception as e:
        print(f"❌ Failed to start trading system: {e}")
        return None

def main():
    """Main startup function"""
    print_banner()
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements check failed!")
        input("Press Enter to exit...")
        return
    
    # Test API connection
    if not test_api_connection():
        print("\n❌ API connection test failed!")
        input("Press Enter to exit...")
        return
    
    # Show configuration
    show_trading_config()
    
    # Get user confirmation
    if not get_user_confirmation():
        print("\n🛑 Real trading cancelled by user")
        input("Press Enter to exit...")
        return
    
    print("\n🚀 Starting Real Trading System...")
    
    # Start dashboard
    dashboard_process = start_dashboard()
    
    # Start live trading
    trading_process = start_live_trading()
    
    if trading_process:
        print("\n" + "="*70)
        print("✅ REAL TRADING SYSTEM IS NOW RUNNING!")
        print("="*70)
        print("📊 Dashboard: http://localhost:7000")
        print("📋 Logs: live_trading.log")
        print("📁 Trade Data: trade_logs/ folder")
        print("⚠️  Press Ctrl+C to stop safely")
        print("="*70)
        
        try:
            # Keep script running
            trading_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down systems...")
            if trading_process:
                trading_process.terminate()
            if dashboard_process:
                dashboard_process.terminate()
            print("✅ Systems stopped safely")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
