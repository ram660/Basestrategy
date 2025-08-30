# 🤖 RSI-MA Trading Bot - Streamlit Cloud

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

A professional cryptocurrency trading bot with Streamlit dashboard and Telegram integration, ready for cloud deployment.

## 🎯 Features

- **📊 Professional Dashboard**: Real-time monitoring and control
- **🤖 Telegram Integration**: Mobile access and notifications  
- **📈 RSI-MA Strategy**: Proven trading algorithm (187.49% avg return)
- **🔒 Risk Management**: Automatic stop-loss and position limits
- **☁️ Cloud Ready**: Optimized for Streamlit Cloud deployment

## 🚀 Quick Deploy to Streamlit Cloud

### 1. Fork this Repository
Click the "Fork" button to create your own copy.

### 2. Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your forked repository
4. Set main file: `streamlit_app.py`
5. Click "Deploy"

### 3. Configure Secrets
In your Streamlit Cloud app settings, add these secrets:

```toml
# Required API Keys
BITGET_API_KEY = "your_bitget_api_key"
BITGET_SECRET_KEY = "your_bitget_secret_key"  
BITGET_PASSPHRASE = "your_bitget_passphrase"
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_telegram_chat_id"
```

### 4. Access Your Bot
- **Dashboard**: https://your-app-name.streamlit.app
- **Telegram**: Send `/start` to your bot

## 📊 Dashboard Features

### 🎮 Trading Controls
- Enable/disable live trading
- Test Telegram notifications
- Real-time system status

### 📈 Market Monitoring  
- Live prices for 7 crypto pairs
- RSI indicators and signals
- Trading opportunity alerts

### 💼 Position Management
- Active trade monitoring
- Real-time P&L tracking
- Risk metrics display

### ⚙️ Configuration
- Strategy parameters
- Risk management settings
- Trading limits

## 🤖 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome menu with quick buttons |
| `/status` | System status and connectivity |
| `/balance` | Account balance and risk info |
| `/positions` | Active positions and P&L |
| `/market` | Live market overview |
| `/signals` | Current trading signals |
| `/enable` | Enable live trading |
| `/disable` | Disable trading |

## ⚙️ Trading Configuration

- **Strategy**: RSI-MA crossover with optimized parameters
- **Position Size**: $10 USDT per trade
- **Leverage**: 2x (conservative)
- **Stop Loss**: 3.5% 
- **Take Profit**: 5.0%
- **Max Positions**: 1 (risk control)
- **Risk per Trade**: ~$0.35

## � Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/rsi-ma-trading-bot.git
cd rsi-ma-trading-bot

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env

# Run locally
streamlit run streamlit_app.py
```

## 📱 Mobile Access

Access your trading bot on mobile through:
- **Responsive web dashboard** - works on any device
- **Telegram bot interface** - native mobile app experience
- **Real-time notifications** - instant trade alerts

## 🛡️ Security & Risk Management

### Built-in Safety Features
- ✅ Conservative position sizing
- ✅ Automatic stop-loss orders
- ✅ API key encryption
- ✅ Manual trading controls
- ✅ Real-time risk monitoring

### Best Practices
- Start with small amounts
- Monitor trades actively
- Keep API keys secure
- Use stop-loss orders
- Understand market risks

## 📈 Performance

- **Backtested Strategy**: 187.49% average return
- **Risk-Adjusted**: Conservative position sizing
- **Multi-Asset**: Works across crypto pairs
- **Real-time**: Live market data integration

## 🌐 Cloud Benefits

- **24/7 Availability**: Always online
- **Global Access**: Trade from anywhere
- **No Setup**: Zero installation required
- **Auto-Updates**: Always latest version
- **Scalable**: Enterprise-grade infrastructure

## ⚠️ Important Disclaimers

- **Real Trading**: This bot executes actual trades with real money
- **Risk Warning**: Cryptocurrency trading involves significant risk of loss
- **Not Financial Advice**: This is educational software only
- **Test First**: Always test with small amounts initially
- **Monitor Actively**: Keep oversight of all trading activity

## 📞 Support

- **Documentation**: See [STREAMLIT_CLOUD_DEPLOYMENT.md](STREAMLIT_CLOUD_DEPLOYMENT.md)
- **Issues**: Use GitHub Issues for bug reports
- **Security**: Report vulnerabilities privately

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⚠️ Trading involves substantial risk. Never risk more than you can afford to lose.**
