@echo off
echo ============================================================
echo RSI-MA Trading Bot - Telegram Bot
echo ============================================================
echo.
echo Starting Telegram bot...
echo Bot will monitor for commands and send notifications
echo.
echo Press Ctrl+C to stop the bot
echo ============================================================
echo.

cd /d "%~dp0"
python telegram_bot.py

pause
