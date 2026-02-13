"""Custom exception classes for yahoo-services."""

from typing import Any, Dict, Optional


class YahooServicesException(Exception):
    """Base exception for yahoo-services."""
    
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class YahooRateLimitException(YahooServicesException):
    """Yahoo Finance rate limit exceeded."""
    
    def __init__(self, message: str = "Yahoo Finance rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="YAHOO_RATE_LIMIT_EXCEEDED",
            details=details
        )


class YahooAPIException(YahooServicesException):
    """Yahoo Finance API error."""
    
    def __init__(self, message: str = "Yahoo Finance API error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="YAHOO_API_ERROR",
            details=details
        )


class AlphaVantageException(YahooServicesException):
    """Alpha Vantage API error."""
    
    def __init__(self, message: str = "Alpha Vantage API error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ALPHA_VANTAGE_ERROR",
            details=details
        )


class CacheException(YahooServicesException):
    """Cache service error."""
    
    def __init__(self, message: str = "Cache service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            details=details
        )


class ServiceUnavailableException(YahooServicesException):
    """Service unavailable."""
    
    def __init__(self, message: str = "Service unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            details=details
        )
