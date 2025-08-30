#!/usr/bin/env python3
"""
RSI-MA Trading Bot - Deployment Manager
Streamlit Dashboard + Telegram Bot Integration
"""

import subprocess
import sys
import os
import threading
import time
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please create a .env file with the following variables:")
        print("""
# Bitget API Configuration
BITGET_API_KEY=your_api_key_here
BITGET_SECRET_KEY=your_secret_key_here
BITGET_PASSPHRASE=your_passphrase_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
        """)
        return False
    
    # Check required variables
    required_vars = [
        'BITGET_API_KEY',
        'BITGET_SECRET_KEY', 
        'BITGET_PASSPHRASE',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your_" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or incomplete environment variables: {', '.join(missing_vars)}")
        print("Please update your .env file with actual values")
        return False
    
    print("✅ Environment variables configured")
    return True

def run_streamlit_dashboard():
    """Run Streamlit dashboard"""
    print("🚀 Starting Streamlit dashboard...")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
    except KeyboardInterrupt:
        print("🛑 Streamlit dashboard stopped")

def run_telegram_bot():
    """Run Telegram bot"""
    print("🤖 Starting Telegram bot...")
    try:
        subprocess.run([sys.executable, "telegram_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Telegram bot: {e}")
    except KeyboardInterrupt:
        print("🛑 Telegram bot stopped")

def run_both():
    """Run both dashboard and telegram bot"""
    print("🚀 Starting complete trading system...")
    print("📊 Dashboard: http://localhost:8501")
    print("🤖 Telegram: Will start monitoring for messages")
    print("⚠️  Press Ctrl+C to stop all services")
    
    # Start Telegram bot in background thread
    telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    telegram_thread.start()
    
    # Give Telegram bot time to start
    time.sleep(3)
    
    # Start Streamlit dashboard (blocking)
    run_streamlit_dashboard()

def main():
    """Main deployment function"""
    print("=" * 60)
    print("🤖 RSI-MA Trading Bot - Streamlit Deployment")
    print("=" * 60)
    
    # Check environment
    if not check_env_file():
        return
    
    print("\nChoose deployment option:")
    print("1. 📊 Streamlit Dashboard only")
    print("2. 🤖 Telegram Bot only") 
    print("3. 🚀 Both Dashboard + Telegram Bot")
    print("4. 📦 Install requirements only")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        if install_requirements():
            run_streamlit_dashboard()
    
    elif choice == "2":
        if install_requirements():
            run_telegram_bot()
    
    elif choice == "3":
        if install_requirements():
            run_both()
    
    elif choice == "4":
        install_requirements()
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
