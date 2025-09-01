# 🤖 RSI-MA Trading Bot for Streamlit Cloud

Professional 24/7 cryptocurrency trading bot built for Streamlit Cloud deployment.

## 🚀 Features
- **Continuous Signal Monitoring**: Real-time RSI + Moving Average signal detection
- **Automated Trading**: Execute trades automatically when signals are detected
- **Telegram Integration**: Real-time notifications and status updates
- **Professional Dashboard**: Multi-tab interface with live controls
- **Cloud-Ready**: Optimized for Streamlit Cloud 24/7 operation

## 📋 Quick Deploy to Streamlit Cloud

### 1. Deploy App
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select this repository
4. Set main file: `streamlit_app.py`
5. Click "Deploy"

### 2. Configure Secrets
Add these secrets in your Streamlit Cloud app settings:

```toml
# Bitget API Configuration
BITGET_API_KEY = "your_api_key_here"
BITGET_SECRET_KEY = "your_secret_key_here"
BITGET_PASSPHRASE = "your_passphrase_here"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "your_bot_token_here"
TELEGRAM_CHAT_ID = "your_chat_id_here"

# Environment Configuration
ENVIRONMENT = "production"
```

### 3. Start Trading
- Your bot will automatically start monitoring signals in the cloud
- Use the dashboard to enable trading and auto-execution
- Monitor performance through Telegram notifications

## 📖 Detailed Setup Guide
See `STREAMLIT_CLOUD_24_7_GUIDE.md` for complete deployment instructions.

## 🔐 Security Setup
See `STREAMLIT_CLOUD_SECRETS.md` for detailed secrets configuration.

## ⚙️ Core Files
- `streamlit_app.py` - Main dashboard application
- `rsi_ma_strategy.py` - Trading strategy logic
- `bitget_futures_trader.py` - Exchange integration
- `config.py` - Configuration management
- `error_handler.py` - Error handling system
- `trade_logger.py` - Trade tracking and analytics

## 🎯 Ready for Production
This bot includes enterprise-grade features:
- ✅ Robust error handling and recovery
- ✅ Comprehensive trade logging
- ✅ Cloud environment detection
- ✅ Automated monitoring and trading
- ✅ Real-time performance tracking

Your 24/7 trading bot is ready to deploy! 🚀
