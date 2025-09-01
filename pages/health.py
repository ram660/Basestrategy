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

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

st.set_page_config(
    page_title="Trading Bot Health Check",
    page_icon="💚",
    layout="centered"
)

def health_check():
    """Simple health check page"""
    try:
        # Setup environment for Streamlit Cloud
        if hasattr(st, 'secrets') and st.secrets:
            for key in st.secrets:
                os.environ[key] = str(st.secrets[key])
        
        # Import modules to verify they're working
        from config import config
        from trade_logger import trade_logger
        
        current_time = datetime.now()
        
        # Check component health
        components = {}
        
        # Test config module
        try:
            components["config"] = config.is_production() is not None
        except:
            components["config"] = False
            
        # Test trade logger
        try:
            components["trade_logger"] = hasattr(trade_logger, 'log_trade')
        except:
            components["trade_logger"] = False
            
        # Test strategy module
        try:
            from rsi_ma_strategy import OptimizedRSIMAStrategy
            components["strategy"] = True
        except:
            components["strategy"] = False
            
        # Test trader module
        try:
            from bitget_futures_trader import BitgetFuturesTrader
            components["trader"] = True
        except:
            components["trader"] = False
        
        # Overall health status
        all_healthy = all(components.values())
        status = "healthy" if all_healthy else "degraded"
        
        # Health status
        health_data = {
            "status": status,
            "timestamp": current_time.isoformat(),
            "service": "trading-bot",
            "version": "1.0.0",
            "uptime": True,
            "environment": config.system.environment.value if 'config' in locals() else "unknown",
            "components": components
        }
        
        # Display health check
        st.title("💚 Trading Bot Health Check")
        
        if all_healthy:
            st.success("🟢 System Status: HEALTHY")
        else:
            st.warning("🟡 System Status: DEGRADED")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Status", "ONLINE" if all_healthy else "DEGRADED")
            st.metric("Environment", health_data.get("environment", "unknown").upper())
        
        with col2:
            st.metric("Timestamp", current_time.strftime("%H:%M:%S"))
            working_components = sum(components.values())
            total_components = len(components)
            st.metric("Components", f"{working_components}/{total_components} OK")
        
        # Component details
        st.subheader("Component Status")
        for component, status in components.items():
            if status:
                st.success(f"✅ {component.title()}: OK")
            else:
                st.error(f"❌ {component.title()}: FAILED")
        
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
