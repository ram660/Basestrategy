#!/usr/bin/env python3
"""
Enhanced Error Handling and Logging System
Provides structured error handling, recovery mechanisms, and comprehensive logging
"""

import os
import sys
import logging
import traceback
import functools
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better classification"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    DATA_ERROR = "data_error"
    TRADING_ERROR = "trading_error"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"

class TradingError(Exception):
    """Custom trading error with enhanced context"""
    
    def __init__(self, message: str, category: ErrorCategory, severity: ErrorSeverity, 
                 context: Dict = None, recoverable: bool = True):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now().isoformat()

class ErrorHandler:
    """Enhanced error handler with recovery mechanisms"""
    
    def __init__(self):
        self.error_log_file = "logs/error_log.json"
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'last_error_time': None
        }
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup enhanced logging configuration"""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # File handler for all logs
        file_handler = logging.FileHandler('logs/trading_bot.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Error file handler
        error_handler = logging.FileHandler('logs/error.log')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)

    def handle_error(self, error: Exception, context: Dict = None, 
                    category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recoverable: bool = True) -> bool:
        """Handle an error with enhanced logging and recovery"""
        try:
            # Create TradingError if not already one
            if not isinstance(error, TradingError):
                error = TradingError(
                    str(error), category, severity, context, recoverable
                )
            
            # Log error
            self._log_error(error)
            
            # Update statistics
            self._update_error_stats(error)
            
            # Attempt recovery if applicable
            if error.recoverable:
                return self._attempt_recovery(error)
            
            return False
            
        except Exception as e:
            logging.getLogger(__name__).critical(f"Error in error handler: {e}")
            return False

    def _log_error(self, error: TradingError):
        """Log error to file and console"""
        logger = logging.getLogger(__name__)
        
        # Create error record
        error_record = {
            'timestamp': error.timestamp,
            'message': str(error),
            'category': error.category.value,
            'severity': error.severity.value,
            'recoverable': error.recoverable,
            'context': error.context,
            'traceback': traceback.format_exc()
        }
        
        # Log to file
        try:
            error_logs = []
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, 'r') as f:
                    error_logs = json.load(f)
            
            error_logs.append(error_record)
            
            # Keep only last 1000 errors
            if len(error_logs) > 1000:
                error_logs = error_logs[-1000:]
            
            with open(self.error_log_file, 'w') as f:
                json.dump(error_logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
        
        # Log to console based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"🚨 CRITICAL: {error.message}")
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"❌ HIGH: {error.message}")
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"⚠️ MEDIUM: {error.message}")
        else:
            logger.info(f"ℹ️ LOW: {error.message}")

    def _update_error_stats(self, error: TradingError):
        """Update error statistics"""
        self.error_stats['total_errors'] += 1
        self.error_stats['last_error_time'] = error.timestamp
        
        # Update category stats
        category = error.category.value
        if category not in self.error_stats['errors_by_category']:
            self.error_stats['errors_by_category'][category] = 0
        self.error_stats['errors_by_category'][category] += 1
        
        # Update severity stats
        severity = error.severity.value
        if severity not in self.error_stats['errors_by_severity']:
            self.error_stats['errors_by_severity'][severity] = 0
        self.error_stats['errors_by_severity'][severity] += 1

    def _attempt_recovery(self, error: TradingError) -> bool:
        """Attempt to recover from error based on category"""
        logger = logging.getLogger(__name__)
        
        try:
            if error.category == ErrorCategory.API_ERROR:
                return self._recover_api_error(error)
            elif error.category == ErrorCategory.NETWORK_ERROR:
                return self._recover_network_error(error)
            elif error.category == ErrorCategory.DATA_ERROR:
                return self._recover_data_error(error)
            elif error.category == ErrorCategory.TRADING_ERROR:
                return self._recover_trading_error(error)
            else:
                logger.info(f"🔄 No specific recovery mechanism for {error.category.value}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Recovery attempt failed: {e}")
            return False

    def _recover_api_error(self, error: TradingError) -> bool:
        """Recover from API errors"""
        logger = logging.getLogger(__name__)
        logger.info("🔄 Attempting API error recovery...")
        
        # Wait and retry logic would go here
        # For now, just log the attempt
        return True

    def _recover_network_error(self, error: TradingError) -> bool:
        """Recover from network errors"""
        logger = logging.getLogger(__name__)
        logger.info("🔄 Attempting network error recovery...")
        
        # Network retry logic would go here
        return True

    def _recover_data_error(self, error: TradingError) -> bool:
        """Recover from data errors"""
        logger = logging.getLogger(__name__)
        logger.info("🔄 Attempting data error recovery...")
        
        # Data refresh logic would go here
        return True

    def _recover_trading_error(self, error: TradingError) -> bool:
        """Recover from trading errors"""
        logger = logging.getLogger(__name__)
        logger.info("🔄 Attempting trading error recovery...")
        
        # Trading error recovery logic would go here
        return True

    def get_error_stats(self) -> Dict:
        """Get current error statistics"""
        return self.error_stats.copy()

# Global error handler instance
error_handler = ErrorHandler()

def safe_execute(category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                recoverable: bool = True):
    """Decorator for safe function execution with error handling"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                
                error_handler.handle_error(
                    e, context, category, severity, recoverable
                )
                
                # Return None or appropriate default value
                return None
        return wrapper
    return decorator

def retry_on_error(max_retries: int = 3, delay: float = 1.0, 
                  backoff_factor: float = 2.0):
    """Decorator for retrying function calls on error"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff_factor ** attempt)
                        logging.getLogger(__name__).warning(
                            f"⏳ Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s: {e}"
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        logging.getLogger(__name__).error(
                            f"❌ All {max_retries + 1} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        return wrapper
    return decorator

def log_performance(func: Callable) -> Callable:
    """Decorator to log function performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        logger = logging.getLogger(__name__)
        
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"⚡ {func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper
