"""
Custom exceptions for TGsys services with proper error handling.
"""

import logging
from typing import Any, Dict, Optional


class TGSystemError(Exception):
    """Base exception for all TGsys errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.logger = logging.getLogger(__name__)
    
    def log_error(self, extra_context: Optional[Dict[str, Any]] = None):
        """Log the error with context information."""
        context = {**self.context, **(extra_context or {})}
        self.logger.error(
            f"{self.__class__.__name__}: {self}",
            extra={"error_code": self.error_code, "context": context},
            exc_info=True
        )


class DatabaseError(TGSystemError):
    """Database-related errors."""
    pass


class KafkaError(TGSystemError):
    """Kafka-related errors."""
    pass


class TelegramAPIError(TGSystemError):
    """Telegram API errors."""
    pass


class ConfigurationError(TGSystemError):
    """Configuration validation errors."""
    pass


class SessionError(TGSystemError):
    """Session management errors."""
    pass


class ProxyError(TGSystemError):
    """Proxy-related errors."""
    pass


class WorkerError(TGSystemError):
    """Worker management errors."""
    pass


class RetryableError(TGSystemError):
    """Errors that can be retried."""
    pass


class NonRetryableError(TGSystemError):
    """Errors that should not be retried."""
    pass


def handle_database_error(func):
    """Decorator for handling database errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise DatabaseError(
                    f"Database connection error in {func.__name__}: {e}",
                    error_code="DB_CONNECTION_ERROR",
                    context={"function": func.__name__}
                )
            elif "duplicate" in str(e).lower() or "unique" in str(e).lower():
                raise DatabaseError(
                    f"Database constraint violation in {func.__name__}: {e}",
                    error_code="DB_CONSTRAINT_ERROR",
                    context={"function": func.__name__}
                )
            else:
                raise DatabaseError(
                    f"Database error in {func.__name__}: {e}",
                    error_code="DB_GENERAL_ERROR",
                    context={"function": func.__name__}
                )
    return wrapper


def handle_kafka_error(func):
    """Decorator for handling Kafka errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "connection" in str(e).lower() or "broker" in str(e).lower():
                raise KafkaError(
                    f"Kafka connection error in {func.__name__}: {e}",
                    error_code="KAFKA_CONNECTION_ERROR",
                    context={"function": func.__name__}
                )
            elif "timeout" in str(e).lower():
                raise KafkaError(
                    f"Kafka timeout error in {func.__name__}: {e}",
                    error_code="KAFKA_TIMEOUT_ERROR",
                    context={"function": func.__name__}
                )
            else:
                raise KafkaError(
                    f"Kafka error in {func.__name__}: {e}",
                    error_code="KAFKA_GENERAL_ERROR",
                    context={"function": func.__name__}
                )
    return wrapper


def handle_telegram_error(func):
    """Decorator for handling Telegram API errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if "flood" in error_str or "too many requests" in error_str:
                raise RetryableError(
                    f"Telegram rate limit error in {func.__name__}: {e}",
                    error_code="TELEGRAM_RATE_LIMIT",
                    context={"function": func.__name__}
                )
            elif "unauthorized" in error_str or "auth" in error_str:
                raise NonRetryableError(
                    f"Telegram authorization error in {func.__name__}: {e}",
                    error_code="TELEGRAM_AUTH_ERROR",
                    context={"function": func.__name__}
                )
            elif "blocked" in error_str or "banned" in error_str:
                raise NonRetryableError(
                    f"Telegram account blocked in {func.__name__}: {e}",
                    error_code="TELEGRAM_BLOCKED",
                    context={"function": func.__name__}
                )
            else:
                raise TelegramAPIError(
                    f"Telegram API error in {func.__name__}: {e}",
                    error_code="TELEGRAM_API_ERROR",
                    context={"function": func.__name__}
                )
    return wrapper
