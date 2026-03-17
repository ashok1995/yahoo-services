"""
Yahoo Finance Service
====================

Orchestration layer: caching, rate limiting, and request dispatch.
Actual data extraction lives in yahoo_fetchers.py.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

import aiohttp
import yfinance as yf
import pandas as pd
from pydantic import BaseModel

from .cache_service import CacheService
from .rate_limiter import RateLimiter
from .trend_analyzer import analyze_candles
from .yahoo_fetchers import (
    extract_quote,
    extract_historical,
    extract_company_info,
    extract_fundamentals,
    extract_financial_statements,
    extract_market_statistics,
    search_common_stocks,
)

logger = logging.getLogger(__name__)

_EXTRACTORS = {
    "quote": lambda t, s, **kw: extract_quote(t, s),
    "historical": lambda t, s, **kw: extract_historical(t, s, **kw),
    "company": lambda t, s, **kw: extract_company_info(t, s),
    "fundamentals": lambda t, s, **kw: extract_fundamentals(t, s),
    "statements": lambda t, s, **kw: extract_financial_statements(t, s, **kw),
    "statistics": lambda t, s, **kw: extract_market_statistics(t, s),
}


class YahooFinanceConfig(BaseModel):
    """Configuration for Yahoo Finance service"""
    timeout: int = 30
    retries: int = 3
    delay: float = 1.0
    user_agents: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ]
    default_market: str = "US"
    supported_markets: List[str] = ["US", "IN", "UK", "CA", "AU"]
    indian_symbol_suffix: str = ".NS"

    @classmethod
    def from_env(cls) -> "YahooFinanceConfig":
        import os
        return cls(
            timeout=int(os.getenv("YAHOO_FINANCE_TIMEOUT", "30")),
            retries=int(os.getenv("YAHOO_FINANCE_RETRIES", "3")),
            delay=float(os.getenv("YAHOO_FINANCE_DELAY", "1.0")),
            default_market=os.getenv("DEFAULT_MARKET", "US"),
            indian_symbol_suffix=os.getenv("INDIAN_SYMBOL_SUFFIX", ".NS"),
        )


class YahooFinanceService:
    """Yahoo Finance service with caching and rate limiting."""

    def __init__(self, config: YahooFinanceConfig, cache_service: CacheService, rate_limiter: RateLimiter):
        self.config = config
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    async def initialize(self) -> None:
        try:
            logger.info("🔧 Initializing Yahoo Finance Service...")
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": random.choice(self.config.user_agents),
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            self._initialized = True
            logger.info("✅ Yahoo Finance Service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Yahoo Finance Service: {e}")
            raise

    def _convert_symbol(self, symbol: str, market: str = "US") -> str:
        if market == "IN" and not symbol.endswith((".NS", ".BO")):
            return f"{symbol}{self.config.indian_symbol_suffix}"
        return symbol

    async def _make_request(self, operation: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Rate-limited request dispatcher."""
        permit_acquired = await self.rate_limiter.acquire_permit()
        if not permit_acquired:
            logger.warning(f"Rate limit exceeded for {symbol}, request blocked")
            self.total_requests += 1
            self.failed_requests += 1
            return None
        try:
            await self.rate_limiter.wait_if_needed()
            yahoo_symbol = self._convert_symbol(symbol, kwargs.pop("market", "US"))
            ticker = yf.Ticker(yahoo_symbol)

            extractor = _EXTRACTORS.get(operation)
            if extractor is None:
                raise ValueError(f"Unknown operation: {operation}")
            result = await extractor(ticker, symbol, **kwargs)

            await self.rate_limiter.record_request(success=True)
            self.total_requests += 1
            self.successful_requests += 1
            return result
        except Exception as e:
            await self.rate_limiter.record_request(success=False)
            self.total_requests += 1
            self.failed_requests += 1
            logger.error(f"Request failed for {symbol}: {e}")
            return None
        finally:
            self.rate_limiter.release_permit()

    async def _cached_request(
        self, cache_type: str, cache_key: str, operation: str,
        symbol: str, use_cache: bool = True, **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Check cache → make request → store result. Shared by all public accessors."""
        try:
            if use_cache:
                cached = await self.cache_service.get(cache_type, cache_key)
                if cached:
                    return cached
            result = await self._make_request(operation, symbol, **kwargs)
            if result and use_cache:
                await self.cache_service.set(cache_type, cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting {cache_type} for {symbol}: {e}")
            return None

    # ── Public data accessors ───────────────────────────────────

    async def get_quote(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        return await self._cached_request("quote", symbol, "quote", symbol, use_cache, market=market)

    async def get_historical_data(
        self, symbol: str, period: str = "1y", interval: str = "1d",
        market: str = "US", use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        cache_key = f"{symbol}_{period}_{interval}"
        return await self._cached_request(
            "historical", cache_key, "historical", symbol, use_cache,
            market=market, period=period, interval=interval,
        )

    async def get_company_info(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        return await self._cached_request("company", symbol, "company", symbol, use_cache, market=market)

    async def get_fundamentals(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        return await self._cached_request("fundamental", symbol, "fundamentals", symbol, use_cache, market=market)

    async def get_financial_statements(
        self, symbol: str, statement_type: str = "income",
        market: str = "US", use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        cache_key = f"{symbol}_{statement_type}"
        return await self._cached_request(
            "statement", cache_key, "statements", symbol, use_cache,
            market=market, statement_type=statement_type,
        )

    async def get_market_statistics(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        return await self._cached_request("statistics", symbol, "statistics", symbol, use_cache, market=market)

    async def get_trend_data(
        self, symbol: str, current_price: float,
        market: str = "US", use_cache: bool = True, cache_ttl: int = 3600,
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """Fetch 3-month daily candles → compute ML-ready trend analysis."""
        try:
            cache_key = f"trend_{symbol}"
            if use_cache:
                cached = await self.cache_service.get("trend", cache_key)
                if cached:
                    return cached

            result = await self._make_request(
                "historical", symbol, period="3mo", interval="1d", market=market,
            )
            if not result or not result.get("data"):
                return None

            df = pd.DataFrame(result["data"])
            for col in ("open", "high", "low", "close"):
                if col in df.columns:
                    df.rename(columns={col: col.capitalize()}, inplace=True)

            trends = analyze_candles(df, current_price)
            if trends and use_cache:
                await self.cache_service.set("trend", cache_key, trends, ttl=cache_ttl)
            return trends
        except Exception as e:
            logger.error(f"Error computing trend for {symbol}: {e}")
            return None

    async def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            cache_key = f"search_{query}_{limit}"
            cached = await self.cache_service.get("search", cache_key)
            if cached:
                return cached.get("results", [])

            results = search_common_stocks(query, limit)
            await self.cache_service.set("search", cache_key, {"results": results})
            return results
        except Exception as e:
            logger.error(f"Error searching symbols for {query}: {e}")
            return []

    async def get_service_statistics(self) -> Dict[str, Any]:
        try:
            rate_limit_stats = await self.rate_limiter.get_statistics()
            cache_stats = await self.cache_service.get_cache_info()
            return {
                "yahoo_finance": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": self.successful_requests / max(self.total_requests, 1),
                },
                "rate_limiting": rate_limit_stats,
                "caching": cache_stats,
                "configuration": {
                    "timeout": self.config.timeout,
                    "retries": self.config.retries,
                    "delay": self.config.delay,
                    "default_market": self.config.default_market,
                    "supported_markets": self.config.supported_markets,
                },
            }
        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            return {}

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            logger.info("🔌 Yahoo Finance Service connections closed")

    def is_initialized(self) -> bool:
        return self._initialized
