@echo off
echo ============================================================
echo RSI-MA Trading Bot - Streamlit Dashboard
echo ============================================================
echo.
echo Starting Streamlit dashboard...
echo Dashboard will open at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard
echo ============================================================
echo.

cd /d "%~dp0"
streamlit run streamlit_app.py --server.port 8501

pause
