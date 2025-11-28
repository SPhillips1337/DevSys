"""
Centralized logging configuration for DevSys agents.
Provides structured logging with proper formatting and levels.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'agent_type'):
            log_entry['agent_type'] = record.agent_type
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
            
        return json.dumps(log_entry)


def setup_logging(service_name: str, log_level: str = None) -> logging.Logger:
    """
    Set up structured logging for a DevSys service.
    
    Args:
        service_name: Name of the service (e.g., 'manager', 'coding-agent')
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment or use default
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler if workspace is available and writable
    workspace = os.environ.get('WORKSPACE', '/workspace')
    if workspace and os.path.exists(workspace) and os.access(workspace, os.W_OK):
        try:
            log_dir = os.path.join(workspace, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f'{service_name}.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except (OSError, PermissionError):
            # If we can't create file handler, just use console
            pass
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance with the service name."""
    service_name = name or os.environ.get('SERVICE_NAME', 'devsys')
    return logging.getLogger(service_name)


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter to add contextual information to log records."""
    
    def process(self, msg, kwargs):
        # Add extra context to the log record
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_task_logger(task_id: str, agent_type: str = None) -> LoggerAdapter:
    """
    Get a logger adapter with task context.
    
    Args:
        task_id: ID of the task being processed
        agent_type: Type of agent (coding, deployment, testing, monitoring)
        
    Returns:
        Logger adapter with task context
    """
    logger = get_logger()
    extra = {'task_id': task_id}
    if agent_type:
        extra['agent_type'] = agent_type
    return LoggerAdapter(logger, extra)


def log_operation(operation: str):
    """Decorator to log function entry/exit and execution time."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = datetime.utcnow()
            
            logger.info(
                f"Starting operation: {operation}",
                extra={'operation': operation, 'function': func.__name__}
            )
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"Completed operation: {operation}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'status': 'success'
                    }
                )
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"Failed operation: {operation}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'duration_seconds': duration,
                        'status': 'error',
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise
        return wrapper
    return decorator