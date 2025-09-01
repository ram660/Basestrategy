# 🚀 Streamlit Cloud Deployment Guide - 24/7 Trading Bot

This guide will help you deploy your RSI-MA Trading Bot on Streamlit Cloud for continuous operation.

## 📋 Prerequisites

1. **GitHub Account**: Your code must be in a GitHub repository
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
3. **Trading API Keys**: Bitget API credentials
4. **Telegram Bot**: For notifications

## 🔧 Step 1: Prepare Your Repository

### 1.1 Ensure these files are in your repository:
- `streamlit_app.py` (main dashboard - ✅ updated)
- `requirements.txt` (dependencies - ✅ updated)
- `config.py` (configuration management - ✅ created)
- `error_handler.py` (error handling - ✅ created)
- `trade_logger.py` (trade logging - ✅ created)
- All your existing strategy files

### 1.2 Update your .gitignore:
```
# Don't commit sensitive data
.env
.streamlit/secrets.toml
config.json
logs/
trade_logs/
```

## 🚀 Step 2: Deploy to Streamlit Cloud

### 2.1 Create New App
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub account
4. Select your repository: `ram660/Basestrategy`
5. Set main file path: `streamlit_app.py`
6. Click "Deploy"

### 2.2 Configure Secrets
In your Streamlit Cloud app settings, add these secrets:

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
LOG_LEVEL = "INFO"

# Trading Configuration (optional - uses defaults if not set)
POSITION_SIZE_USDT = "10.0"
LEVERAGE = "2.0"
MAX_POSITIONS = "1"
```

## ⚙️ Step 3: Configure for 24/7 Operation

### 3.1 Auto-Start Features
The app automatically:
- ✅ Starts signal monitoring in production environment
- ✅ Uses configuration-based settings
- ✅ Enables comprehensive error handling
- ✅ Logs all trading activities

### 3.2 Dashboard Controls
Use the dashboard to:
- 🎮 **Controls Tab**: Enable/disable trading and auto-trading
- 📈 **Market Tab**: Monitor real-time signals
- 💼 **Positions Tab**: Track active positions
- ⚙️ **Config Tab**: View current settings
- 📊 **Logs Tab**: Monitor performance and trades

### 3.3 Signal Monitoring
- Click "🔍 Start Signal Monitoring" to begin 24/7 monitoring
- Enable "🤖 Auto-Trading" to automatically execute signals
- Monitor status in the Cloud Status section

## 📱 Step 4: Telegram Integration

### 4.1 Create Telegram Bot
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow instructions to get your bot token
4. Add token to Streamlit secrets

### 4.2 Get Chat ID
1. Start conversation with your bot
2. Send a message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your chat ID in the response
5. Add chat ID to Streamlit secrets

### 4.3 Test Integration
- Use "📱 Test Telegram" button in the dashboard
- Bot will send notifications for:
  - 🔍 Signal detection
  - 🚀 Trade execution
  - ⚠️ Errors and system status

## 🔧 Step 5: Monitoring & Maintenance

### 5.1 Dashboard Monitoring
- **Auto-refresh**: Enabled by default (10s when monitoring, 30s otherwise)
- **Signal Status**: Green = active monitoring, Red = inactive
- **Uptime Tracking**: Shows how long the app has been running
- **Last Check**: Time since last signal check

### 5.2 Performance Tracking
- **Trade Logs**: View recent trades and performance
- **P&L Tracking**: Monitor profits and losses
- **Win Rate**: Track strategy success rate
- **Error Monitoring**: Comprehensive error tracking

### 5.3 Keep-Alive Strategies
Streamlit Cloud apps can sleep after inactivity. To prevent this:

1. **Enable Auto-refresh**: Keeps the app active
2. **Telegram Monitoring**: Regular API calls
3. **Signal Checking**: Continuous market monitoring
4. **External Monitoring**: Use UptimeRobot or similar (optional)

## 🚨 Troubleshooting

### Common Issues:

1. **App Sleeping**
   - ✅ Auto-refresh is enabled by default
   - ✅ Signal monitoring provides continuous activity
   - Consider external monitoring service

2. **API Errors**
   - Check secrets configuration
   - Verify API key permissions
   - Monitor error logs in dashboard

3. **Telegram Not Working**
   - Verify bot token and chat ID
   - Test with "📱 Test Telegram" button
   - Check bot permissions

4. **No Signals Detected**
   - Market conditions may not meet criteria
   - Check RSI thresholds (60 for long, 40 for short)
   - Verify data fetching is working

### 5.4 Emergency Controls
- **🛑 Disable Trading**: Stops all new trades immediately
- **Close Positions**: Manual position management in Positions tab
- **Telegram Alerts**: Immediate notifications for critical events

## 📊 App Features for Cloud Operation

### Enhanced for 24/7 Operation:
- ✅ **Continuous Signal Monitoring**: Scans all symbols every 10-30 seconds
- ✅ **Auto-Trading**: Executes trades automatically when signals are found
- ✅ **Error Recovery**: Automatic error handling and recovery
- ✅ **Trade Logging**: Comprehensive trade tracking and performance analytics
- ✅ **Telegram Integration**: Real-time notifications and status updates
- ✅ **Configuration Management**: Centralized settings with validation
- ✅ **Cloud Optimization**: Designed for Streamlit Cloud deployment

### Safety Features:
- 🛡️ **Position Limits**: Maximum 1 position to limit risk
- 🛡️ **Account Safety Checks**: Balance and safety validations
- 🛡️ **Error Handling**: Graceful error recovery
- 🛡️ **Stop Loss/Take Profit**: Automatic risk management
- 🛡️ **Manual Override**: Emergency stop controls

## 🎯 Next Steps

1. **Deploy** your app to Streamlit Cloud
2. **Configure** all secrets properly
3. **Test** Telegram integration
4. **Enable** signal monitoring
5. **Monitor** performance through dashboard
6. **Optimize** settings based on performance

Your trading bot is now ready for 24/7 cloud operation! 🚀

## 📞 Support

- Monitor the **📊 Logs** tab for any issues
- Use **Telegram integration** for real-time status
- Check **error logs** in the dashboard for troubleshooting
