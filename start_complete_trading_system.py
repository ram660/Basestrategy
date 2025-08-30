#!/usr/bin/env python3
"""
Complete Live Trading System with Telegram
Starts trading system, dashboard, and Telegram bot together
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
    print("🚀 COMPLETE LIVE TRADING SYSTEM")
    print("RSI-MA Strategy + Dashboard + Telegram Bot")
    print("="*70)

def check_telegram_setup():
    """Check Telegram bot setup"""
    print("\n📱 Checking Telegram Setup...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False
    
    print(f"✅ Telegram Bot Token: {token[:10]}...")
    print("💡 To get notifications:")
    print("   1. Start this system")
    print("   2. Open Telegram and search for your bot")
    print("   3. Send /start to your bot")
    print("   4. Notifications will be enabled automatically")
    
    return True

def start_all_systems():
    """Start all systems"""
    print("\n🚀 Starting All Systems...")
    
    processes = []
    
    # 1. Start Dashboard
    print("📊 Starting Dashboard...")
    try:
        dashboard_process = subprocess.Popen([
            sys.executable, 'dashboard.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(('Dashboard', dashboard_process))
        time.sleep(2)
        print("✅ Dashboard started at http://localhost:7000")
    except Exception as e:
        print(f"❌ Dashboard failed: {e}")
    
    # 2. Start Telegram Bot
    print("📱 Starting Telegram Bot...")
    try:
        telegram_process = subprocess.Popen([
            sys.executable, 'live_trading_telegram_bot.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(('Telegram Bot', telegram_process))
        time.sleep(2)
        print("✅ Telegram Bot started")
    except Exception as e:
        print(f"❌ Telegram Bot failed: {e}")
    
    # 3. Show system status before trading
    print("\n" + "="*70)
    print("✅ SYSTEMS READY!")
    print("="*70)
    print("📊 Dashboard: http://localhost:7000")
    print("📱 Telegram: Find your bot and send /start")
    print("🤖 Trading: Ready to start")
    print("="*70)
    
    # Open dashboard in browser
    try:
        webbrowser.open('http://localhost:7000')
    except:
        pass
    
    # Ask about starting trading
    print("\n🤖 TRADING SYSTEM:")
    print("   • Position Size: $10 USDT margin")
    print("   • Risk per trade: ~$0.35")
    print("   • Max positions: 1")
    print("   • Telegram notifications: Enabled")
    
    confirm = input("\nStart LIVE TRADING now? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y']:
        print("\n🚀 Starting Live Trading System...")
        try:
            trading_process = subprocess.Popen([
                sys.executable, 'live_trading_system.py'
            ])
            processes.append(('Live Trading', trading_process))
            
            print("✅ Live Trading System started!")
            print("\n" + "="*70)
            print("🎉 COMPLETE SYSTEM IS NOW RUNNING!")
            print("="*70)
            print("📊 Dashboard: http://localhost:7000")
            print("📱 Telegram: Send /start to your bot")
            print("🤖 Trading: Monitoring markets for signals")
            print("📋 Logs: live_trading.log")
            print("⚠️  Press Ctrl+C to stop all systems safely")
            print("="*70)
            
            # Keep main process alive and monitor
            try:
                while True:
                    time.sleep(10)
                    
                    # Check if processes are still running
                    for name, process in processes:
                        if process.poll() is not None:
                            print(f"⚠️ {name} stopped unexpectedly")
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutting down all systems...")
                for name, process in processes:
                    try:
                        process.terminate()
                        print(f"✅ {name} stopped")
                    except:
                        pass
                print("✅ All systems stopped safely")
        
        except Exception as e:
            print(f"❌ Failed to start trading: {e}")
    
    else:
        print("\n📊 Systems running without live trading")
        print("   • Dashboard: http://localhost:7000")
        print("   • Telegram Bot: Active")
        print("   • To start trading later, run: python live_trading_system.py")
        
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down systems...")
            for name, process in processes:
                try:
                    process.terminate()
                    print(f"✅ {name} stopped")
                except:
                    pass

def main():
    """Main function"""
    print_banner()
    
    # Check requirements
    print("\n🔍 Checking Requirements...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        input("Press Enter to exit...")
        return
    
    # Check Telegram setup
    if not check_telegram_setup():
        print("\n⚠️ Telegram setup incomplete, but you can still trade")
        choice = input("Continue anyway? (yes/no): ").lower().strip()
        if choice not in ['yes', 'y']:
            return
    
    # Test API connection
    print("\n🔗 Testing Trading API...")
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
        print(f"❌ API test failed: {e}")
        input("Press Enter to exit...")
        return
    
    # Start all systems
    start_all_systems()
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
