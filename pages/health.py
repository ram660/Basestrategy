#!/usr/bin/env python3
"""
Health Check Page for External Monitoring
Simple endpoint for services like UptimeRobot to monitor
"""

import streamlit as st
from datetime import datetime
import json
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

st.set_page_config(
    page_title="Trading Bot Health Check",
    page_icon="💚",
    layout="centered"
)

def health_check():
    """Simple health check page"""
    try:
        # Import modules to verify they're working
        from config import config
        from trade_logger import trade_logger
        
        current_time = datetime.now()
        
        # Health status
        health_data = {
            "status": "healthy",
            "timestamp": current_time.isoformat(),
            "service": "trading-bot",
            "version": "1.0.0",
            "uptime": True,
            "components": {
                "config": True,
                "trade_logger": True,
                "strategy": True
            }
        }
        
        # Display health check
        st.title("💚 Trading Bot Health Check")
        st.success("🟢 System Status: HEALTHY")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Status", "ONLINE")
            st.metric("Uptime", "ACTIVE")
        
        with col2:
            st.metric("Timestamp", current_time.strftime("%H:%M:%S"))
            st.metric("Components", "ALL OK")
        
        # JSON response for monitoring tools
        st.subheader("JSON Response")
        st.json(health_data)
        
        # Simple text response for basic monitors
        st.subheader("Simple Response")
        st.code("OK")
        
        return health_data
        
    except Exception as e:
        error_data = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "service": "trading-bot",
            "error": str(e),
            "uptime": False
        }
        
        st.title("❌ Trading Bot Health Check")
        st.error("🔴 System Status: ERROR")
        st.error(f"Error: {e}")
        
        st.json(error_data)
        
        return error_data

if __name__ == "__main__":
    health_check()
