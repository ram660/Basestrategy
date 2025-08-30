#!/usr/bin/env python3
"""
Cloud Deployment Verification Script
Tests if the app is ready for Streamlit Cloud deployment
"""

import os
import sys
import importlib
from pathlib import Path

def check_file_exists(filepath):
    """Check if a required file exists"""
    if Path(filepath).exists():
        print(f"✅ {filepath}")
        return True
    else:
        print(f"❌ {filepath} - MISSING")
        return False

def check_imports():
    """Check if all required modules can be imported"""
    required_modules = [
        'streamlit',
        'pandas', 
        'plotly',
        'requests',
        'telegram',
        'ccxt',
        'aiohttp'
    ]
    
    print("\n📦 Checking Python Dependencies:")
    all_good = True
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - NOT INSTALLED")
            all_good = False
    
    return all_good

def check_streamlit_secrets():
    """Check if Streamlit secrets template exists"""
    secrets_file = ".streamlit/secrets.toml"
    if Path(secrets_file).exists():
        print(f"✅ {secrets_file}")
        with open(secrets_file, 'r') as f:
            content = f.read()
            required_keys = [
                'BITGET_API_KEY',
                'BITGET_SECRET_KEY', 
                'BITGET_PASSPHRASE',
                'TELEGRAM_BOT_TOKEN',
                'TELEGRAM_CHAT_ID'
            ]
            
            missing_keys = []
            for key in required_keys:
                if key not in content:
                    missing_keys.append(key)
            
            if missing_keys:
                print(f"⚠️  Missing keys in secrets.toml: {', '.join(missing_keys)}")
                return False
            else:
                print("✅ All required secrets keys present")
                return True
    else:
        print(f"❌ {secrets_file} - MISSING")
        return False

def check_app_imports():
    """Check if the main app can import without errors"""
    print("\n🔍 Testing App Imports:")
    try:
        # Set a dummy Streamlit secrets for testing
        import streamlit as st
        if not hasattr(st, 'secrets'):
            st.secrets = {
                'BITGET_API_KEY': 'test',
                'BITGET_SECRET_KEY': 'test',
                'BITGET_PASSPHRASE': 'test',
                'TELEGRAM_BOT_TOKEN': 'test',
                'TELEGRAM_CHAT_ID': 'test'
            }
        
        from streamlit_app import StreamlitTradingDashboard
        print("✅ streamlit_app.py imports successfully")
        return True
    except Exception as e:
        print(f"❌ streamlit_app.py import failed: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 STREAMLIT CLOUD DEPLOYMENT VERIFICATION")
    print("=" * 50)
    
    # Check required files
    print("\n📁 Checking Required Files:")
    required_files = [
        "streamlit_app.py",
        "requirements.txt",
        ".streamlit/config.toml",
        ".streamlit/secrets.toml",
        ".gitignore",
        "README.md",
        "rsi_ma_strategy.py",
        "bitget_futures_trader.py",
        "data_fetcher.py",
        "telegram_notifier.py",
        "config.py"
    ]
    
    files_ok = all(check_file_exists(f) for f in required_files)
    
    # Check dependencies
    deps_ok = check_imports()
    
    # Check secrets configuration
    secrets_ok = check_streamlit_secrets()
    
    # Check app imports
    app_ok = check_app_imports()
    
    # Final verdict
    print("\n" + "=" * 50)
    if all([files_ok, deps_ok, secrets_ok, app_ok]):
        print("🎉 READY FOR STREAMLIT CLOUD DEPLOYMENT!")
        print("\nNext steps:")
        print("1. Push to GitHub (ensure .env is in .gitignore)")
        print("2. Deploy on share.streamlit.io")
        print("3. Configure secrets in Streamlit Cloud dashboard")
        print("4. Test your deployed app")
        return True
    else:
        print("❌ NOT READY FOR DEPLOYMENT")
        print("\nPlease fix the issues above before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
