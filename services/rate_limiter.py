"""
Rate Limiter Service
===================

Service for managing rate limiting and quota management for Yahoo Finance API requests.
"""

import asyncio
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    daily_limit: int = 2000
    hourly_limit: int = 100
    minute_limit: int = 10
    delay_between_requests: float = 1.0
    max_concurrent_requests: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_DELAY
    retry_attempts: int = 3
    backoff_multiplier: float = 2.0


class RateLimiter:
    """Rate limiter for Yahoo Finance API requests"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._initialized = False
        
        # Request tracking
        self.daily_requests = 0
        self.hourly_requests = 0
        self.minute_requests = 0
        self.last_request_time = 0
        self.last_reset_daily = datetime.now().date()
        self.last_reset_hourly = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.last_reset_minute = datetime.now().replace(second=0, microsecond=0)
        
        # Concurrent request tracking
        self.active_requests = 0
        self.request_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
        # Error tracking
        self.consecutive_errors = 0
        self.last_error_time = 0
        
        # Statistics
        self.total_requests = 0
        self.total_errors = 0
        self.total_delays = 0
    
    async def initialize(self) -> None:
        """Initialize the rate limiter"""
        try:
            logger.info("🔧 Initializing Rate Limiter...")
            self._initialized = True
            logger.info("✅ Rate Limiter initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Rate Limiter: {e}")
            raise
    
    def _reset_counters_if_needed(self) -> None:
        """Reset counters if time periods have passed"""
        now = datetime.now()
        
        # Reset daily counter
        if now.date() != self.last_reset_daily:
            self.daily_requests = 0
            self.last_reset_daily = now.date()
            logger.info("🔄 Daily request counter reset")
        
        # Reset hourly counter
        if now >= self.last_reset_hourly + timedelta(hours=1):
            self.hourly_requests = 0
            self.last_reset_hourly = now.replace(minute=0, second=0, microsecond=0)
            logger.info("🔄 Hourly request counter reset")
        
        # Reset minute counter
        if now >= self.last_reset_minute + timedelta(minutes=1):
            self.minute_requests = 0
            self.last_reset_minute = now.replace(second=0, microsecond=0)
    
    async def acquire_permit(self) -> bool:
        """Acquire a permit for making a request"""
        if not self._initialized:
            raise RuntimeError("Rate limiter not initialized")
        
        # Reset counters if needed
        self._reset_counters_if_needed()
        
        # Check limits
        if self.daily_requests >= self.config.daily_limit:
            logger.warning(f"🚫 Daily limit reached: {self.daily_requests}/{self.config.daily_limit}")
            return False
        
        if self.hourly_requests >= self.config.hourly_limit:
            logger.warning(f"🚫 Hourly limit reached: {self.hourly_requests}/{self.config.hourly_limit}")
            return False
        
        if self.minute_requests >= self.config.minute_limit:
            logger.warning(f"🚫 Minute limit reached: {self.minute_requests}/{self.config.minute_limit}")
            return False
        
        # Acquire semaphore for concurrent requests
        await self.request_semaphore.acquire()
        self.active_requests += 1
        
        return True
    
    def release_permit(self) -> None:
        """Release a permit after request completion"""
        self.active_requests -= 1
        self.request_semaphore.release()
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limiting is needed"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.config.delay_between_requests:
            delay_needed = self.config.delay_between_requests - time_since_last
            
            # Apply strategy-specific delays
            if self.config.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
                if self.consecutive_errors > 0:
                    delay_needed *= (self.config.backoff_multiplier ** min(self.consecutive_errors, 5))
            
            logger.debug(f"⏳ Rate limiting delay: {delay_needed:.2f}s")
            await asyncio.sleep(delay_needed)
            self.total_delays += 1
        
        self.last_request_time = time.time()
    
    async def record_request(self, success: bool = True) -> None:
        """Record a request attempt"""
        self.total_requests += 1
        self.daily_requests += 1
        self.hourly_requests += 1
        self.minute_requests += 1
        
        if success:
            self.consecutive_errors = 0
        else:
            self.total_errors += 1
            self.consecutive_errors += 1
            self.last_error_time = time.time()
    
    async def get_statistics(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_delays": self.total_delays,
            "daily_requests": self.daily_requests,
            "daily_limit": self.config.daily_limit,
            "hourly_requests": self.hourly_requests,
            "hourly_limit": self.config.hourly_limit,
            "minute_requests": self.minute_requests,
            "minute_limit": self.config.minute_limit,
            "active_requests": self.active_requests,
            "max_concurrent_requests": self.config.max_concurrent_requests,
            "consecutive_errors": self.consecutive_errors,
            "last_error_time": self.last_error_time,
            "last_request_time": self.last_request_time,
            "delay_between_requests": self.config.delay_between_requests,
            "strategy": self.config.strategy.value
        }
    
    async def is_healthy(self) -> bool:
        """Check if rate limiter is healthy"""
        try:
            # Check if we're within reasonable limits
            daily_usage = self.daily_requests / self.config.daily_limit
            hourly_usage = self.hourly_requests / self.config.hourly_limit
            
            # Consider unhealthy if usage is too high
            if daily_usage > 0.95 or hourly_usage > 0.95:
                return False
            
            # Consider unhealthy if too many consecutive errors
            if self.consecutive_errors > 10:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close the rate limiter"""
        logger.info("🔌 Rate Limiter connections closed")
    
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized 