"""
Custom exceptions and error handling utilities for DevSys.
Provides structured error handling with proper categorization.
"""
import time
import functools
from typing import Any, Callable, Optional, Type, Union
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for better handling and monitoring."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    EXTERNAL_SERVICE = "external_service"
    TASK_PROCESSING = "task_processing"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    MONITORING = "monitoring"


class DevSysError(Exception):
    """Base exception for all DevSys errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.TASK_PROCESSING,
        details: Optional[dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/API responses."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'category': self.category.value,
            'details': self.details,
            'cause': str(self.cause) if self.cause else None
        }


class ConfigurationError(DevSysError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            details=details,
            **kwargs
        )


class NetworkError(DevSysError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if url:
            details['url'] = url
        if status_code:
            details['status_code'] = status_code
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            details=details,
            **kwargs
        )


class FilesystemError(DevSysError):
    """Raised when filesystem operations fail."""
    
    def __init__(self, message: str, path: Optional[str] = None, operation: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if path:
            details['path'] = path
        if operation:
            details['operation'] = operation
        super().__init__(
            message,
            category=ErrorCategory.FILESYSTEM,
            details=details,
            **kwargs
        )


class AuthenticationError(DevSysError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            **kwargs
        )


class ValidationError(DevSysError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            details=details,
            **kwargs
        )


class ExternalServiceError(DevSysError):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if service:
            details['service'] = service
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            details=details,
            **kwargs
        )


class TaskProcessingError(DevSysError):
    """Raised when task processing fails."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, stage: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if task_id:
            details['task_id'] = task_id
        if stage:
            details['stage'] = stage
        super().__init__(
            message,
            category=ErrorCategory.TASK_PROCESSING,
            details=details,
            **kwargs
        )


class DeploymentError(DevSysError):
    """Raised when deployment operations fail."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, target: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if task_id:
            details['task_id'] = task_id
        if target:
            details['target'] = target
        super().__init__(
            message,
            category=ErrorCategory.DEPLOYMENT,
            details=details,
            **kwargs
        )


class TestingError(DevSysError):
    """Raised when testing operations fail."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, test_type: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if task_id:
            details['task_id'] = task_id
        if test_type:
            details['test_type'] = test_type
        super().__init__(
            message,
            category=ErrorCategory.TESTING,
            details=details,
            **kwargs
        )


class MonitoringError(DevSysError):
    """Raised when monitoring operations fail."""
    
    def __init__(self, message: str, check_name: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if check_name:
            details['check_name'] = check_name
        super().__init__(
            message,
            category=ErrorCategory.MONITORING,
            details=details,
            **kwargs
        )


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], tuple] = Exception,
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Exception types to catch and retry
        on_retry: Callback function called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        raise
                    
                    if on_retry:
                        on_retry(attempt + 1, e, current_delay)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False
) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        default_return: Value to return if function fails
        log_errors: Whether to log errors
        reraise: Whether to re-raise exceptions after logging
        
    Returns:
        Function result or default_return if function fails
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in safe_execute: {e}", exc_info=True)
        
        if reraise:
            raise
        
        return default_return


class ErrorHandler:
    """Context manager for structured error handling."""
    
    def __init__(
        self,
        operation: str,
        task_id: Optional[str] = None,
        reraise: bool = True,
        default_return: Any = None
    ):
        self.operation = operation
        self.task_id = task_id
        self.reraise = reraise
        self.default_return = default_return
        self.logger = None
    
    def __enter__(self):
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Starting operation: {self.operation}", extra={
            'operation': self.operation,
            'task_id': self.task_id
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"Completed operation: {self.operation}", extra={
                'operation': self.operation,
                'task_id': self.task_id,
                'status': 'success'
            })
            return False
        
        # Log the error
        error_info = {
            'operation': self.operation,
            'task_id': self.task_id,
            'status': 'error',
            'error_type': exc_type.__name__,
            'error_message': str(exc_val)
        }
        
        if isinstance(exc_val, DevSysError):
            error_info.update(exc_val.to_dict())
        
        self.logger.error(f"Failed operation: {self.operation}", extra=error_info, exc_info=True)
        
        # Return True to suppress the exception if reraise is False
        return not self.reraise


def handle_errors(operation: str, task_id: Optional[str] = None):
    """Decorator for error handling with logging."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorHandler(operation, task_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator