"""
Yahoo Finance Service
====================

Enhanced service for Yahoo Finance data integration with caching and rate limiting.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random

import aiohttp
import yfinance as yf
import pandas as pd
from pydantic import BaseModel

from .cache_service import CacheService
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class YahooFinanceConfig(BaseModel):
    """Configuration for Yahoo Finance service"""
    timeout: int = 30
    retries: int = 3
    delay: float = 1.0
    user_agents: List[str] = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ]
    default_market: str = "US"
    supported_markets: List[str] = ["US", "IN", "UK", "CA", "AU"]
    indian_symbol_suffix: str = ".NS"
    
    @classmethod
    def from_env(cls) -> "YahooFinanceConfig":
        """Create configuration from environment variables"""
        import os
        return cls(
            timeout=int(os.getenv("YAHOO_FINANCE_TIMEOUT", "30")),
            retries=int(os.getenv("YAHOO_FINANCE_RETRIES", "3")),
            delay=float(os.getenv("YAHOO_FINANCE_DELAY", "1.0")),
            default_market=os.getenv("DEFAULT_MARKET", "US"),
            indian_symbol_suffix=os.getenv("INDIAN_SYMBOL_SUFFIX", ".NS")
        )


class YahooFinanceService:
    """Enhanced Yahoo Finance service with caching and rate limiting"""
    
    def __init__(self, config: YahooFinanceConfig, cache_service: CacheService, rate_limiter: RateLimiter):
        self.config = config
        self.cache_service = cache_service
        self.rate_limiter = rate_limiter
        self.session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    async def initialize(self) -> None:
        """Initialize the service"""
        try:
            logger.info("🔧 Initializing Yahoo Finance Service...")
            
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": random.choice(self.config.user_agents),
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            
            self._initialized = True
            logger.info("✅ Yahoo Finance Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Yahoo Finance Service: {e}")
            raise
    
    def _convert_symbol(self, symbol: str, market: str = "US") -> str:
        """Convert symbol to appropriate format for Yahoo Finance"""
        if market == "IN" and not symbol.endswith(('.NS', '.BO')):
            return f"{symbol}{self.config.indian_symbol_suffix}"
        return symbol
    
    async def _make_request(self, operation: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make a rate-limited request to Yahoo Finance"""
        try:
            # Acquire rate limit permit
            permit_acquired = await self.rate_limiter.acquire_permit()
            if not permit_acquired:
                raise Exception("Rate limit exceeded")
            
            try:
                # Wait if needed
                await self.rate_limiter.wait_if_needed()
                
                # Make the actual request
                result = await self._execute_request(operation, symbol, **kwargs)
                
                # Record successful request
                await self.rate_limiter.record_request(success=True)
                self.total_requests += 1
                self.successful_requests += 1
                
                return result
                
            finally:
                # Always release permit
                self.rate_limiter.release_permit()
                
        except Exception as e:
            # Record failed request
            await self.rate_limiter.record_request(success=False)
            self.total_requests += 1
            self.failed_requests += 1
            logger.error(f"❌ Request failed for {symbol}: {e}")
            return None
    
    async def _execute_request(self, operation: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Execute the actual Yahoo Finance request"""
        try:
            yahoo_symbol = self._convert_symbol(symbol, kwargs.get('market', 'US'))
            ticker = yf.Ticker(yahoo_symbol)
            
            if operation == "quote":
                return await self._get_quote_data(ticker, symbol)
            elif operation == "historical":
                return await self._get_historical_data(ticker, symbol, **kwargs)
            elif operation == "company":
                return await self._get_company_info(ticker, symbol)
            elif operation == "fundamentals":
                return await self._get_fundamental_data(ticker, symbol)
            elif operation == "statements":
                return await self._get_financial_statements(ticker, symbol, **kwargs)
            elif operation == "statistics":
                return await self._get_market_statistics(ticker, symbol)
            else:
                raise ValueError(f"Unknown operation: {operation}")
                
        except Exception as e:
            logger.error(f"❌ Error executing {operation} for {symbol}: {e}")
            return None
    
    async def _get_quote_data(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote data from ticker"""
        try:
            info = ticker.info
            
            if not info or len(info) < 5:
                return None
            
            quote = {
                "symbol": symbol,
                "price": info.get('regularMarketPrice'),
                "change": info.get('regularMarketChange'),
                "change_percent": info.get('regularMarketChangePercent'),
                "volume": info.get('volume'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "dividend_yield": info.get('dividendYield'),
                "high_52_week": info.get('fiftyTwoWeekHigh'),
                "low_52_week": info.get('fiftyTwoWeekLow'),
                "open": info.get('regularMarketOpen'),
                "previous_close": info.get('regularMarketPreviousClose'),
                "day_high": info.get('dayHigh'),
                "day_low": info.get('dayLow'),
                "timestamp": datetime.now().isoformat()
            }
            
            return quote
            
        except Exception as e:
            logger.error(f"❌ Error getting quote for {symbol}: {e}")
            return None
    
    async def _get_historical_data(self, ticker: yf.Ticker, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get historical data from ticker"""
        try:
            period = kwargs.get('period', '1y')
            interval = kwargs.get('interval', '1d')
            
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            # Convert to list of dictionaries
            data = []
            for date, row in hist.iterrows():
                data.append({
                    "date": date.isoformat(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume'])
                })
            
            return {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": data,
                "total_points": len(data),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return None
    
    async def _get_company_info(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company information from ticker"""
        try:
            info = ticker.info
            
            if not info:
                return None
            
            company_info = {
                "symbol": symbol,
                "name": info.get('longName'),
                "short_name": info.get('shortName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "country": info.get('country'),
                "currency": info.get('currency'),
                "market_cap": info.get('marketCap'),
                "enterprise_value": info.get('enterpriseValue'),
                "description": info.get('longBusinessSummary'),
                "website": info.get('website'),
                "employees": info.get('fullTimeEmployees'),
                "timestamp": datetime.now().isoformat()
            }
            
            return company_info
            
        except Exception as e:
            logger.error(f"❌ Error getting company info for {symbol}: {e}")
            return None
    
    async def _get_fundamental_data(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamental data from ticker"""
        try:
            info = ticker.info
            
            if not info:
                return None
            
            fundamentals = {
                "symbol": symbol,
                "pe_ratio": info.get('trailingPE'),
                "pb_ratio": info.get('priceToBook'),
                "peg_ratio": info.get('pegRatio'),
                "roe": info.get('returnOnEquity'),
                "roa": info.get('returnOnAssets'),
                "debt_to_equity": info.get('debtToEquity'),
                "current_ratio": info.get('currentRatio'),
                "quick_ratio": info.get('quickRatio'),
                "dividend_yield": info.get('dividendYield'),
                "payout_ratio": info.get('payoutRatio'),
                "market_cap": info.get('marketCap'),
                "enterprise_value": info.get('enterpriseValue'),
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth'),
                "profit_margin": info.get('profitMargins'),
                "operating_margin": info.get('operatingMargins'),
                "gross_margin": info.get('grossMargins'),
                "book_value": info.get('bookValue'),
                "cash_per_share": info.get('totalCashPerShare'),
                "beta": info.get('beta'),
                "forward_pe": info.get('forwardPE'),
                "price_to_sales": info.get('priceToSalesTrailing12Months'),
                "timestamp": datetime.now().isoformat()
            }
            
            return fundamentals
            
        except Exception as e:
            logger.error(f"❌ Error getting fundamental data for {symbol}: {e}")
            return None
    
    async def _get_financial_statements(self, ticker: yf.Ticker, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get financial statements from ticker"""
        try:
            statement_type = kwargs.get('statement_type', 'income')
            
            if statement_type == "income":
                statements = ticker.income_stmt
            elif statement_type == "balance":
                statements = ticker.balance_sheet
            elif statement_type == "cashflow":
                statements = ticker.cashflow
            else:
                raise ValueError(f"Invalid statement type: {statement_type}")
            
            if statements is None or statements.empty:
                return None
            
            # Convert to dictionary format
            data = {
                "symbol": symbol,
                "statement_type": statement_type,
                "data": statements.to_dict('index'),
                "timestamp": datetime.now().isoformat()
            }
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error getting {statement_type} statement for {symbol}: {e}")
            return None
    
    async def _get_market_statistics(self, ticker: yf.Ticker, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market statistics from ticker"""
        try:
            info = ticker.info
            
            if not info:
                return None
            
            stats = {
                "symbol": symbol,
                "market_cap": info.get('marketCap'),
                "enterprise_value": info.get('enterpriseValue'),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "price_to_book": info.get('priceToBook'),
                "price_to_sales": info.get('priceToSalesTrailing12Months'),
                "dividend_yield": info.get('dividendYield'),
                "beta": info.get('beta'),
                "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
                "fifty_two_week_low": info.get('fiftyTwoWeekLow'),
                "fifty_day_average": info.get('fiftyDayAverage'),
                "two_hundred_day_average": info.get('twoHundredDayAverage'),
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting market statistics for {symbol}: {e}")
            return None
    
    async def get_quote(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get real-time quote for a symbol"""
        try:
            # Check cache first
            if use_cache:
                cached_data = await self.cache_service.get("quote", symbol)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("quote", symbol, market=market)
            
            if result and use_cache:
                await self.cache_service.set("quote", symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting quote for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, period: str = "1y", interval: str = "1d", 
                                market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get historical price data for a symbol"""
        try:
            # Check cache first
            if use_cache:
                cache_key = f"{symbol}_{period}_{interval}"
                cached_data = await self.cache_service.get("historical", cache_key)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("historical", symbol, period=period, interval=interval, market=market)
            
            if result and use_cache:
                await self.cache_service.set("historical", cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return None
    
    async def get_company_info(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get company information"""
        try:
            # Check cache first
            if use_cache:
                cached_data = await self.cache_service.get("company", symbol)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("company", symbol, market=market)
            
            if result and use_cache:
                await self.cache_service.set("company", symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting company info for {symbol}: {e}")
            return None
    
    async def get_fundamentals(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get fundamental data"""
        try:
            # Check cache first
            if use_cache:
                cached_data = await self.cache_service.get("fundamental", symbol)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("fundamentals", symbol, market=market)
            
            if result and use_cache:
                await self.cache_service.set("fundamental", symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting fundamentals for {symbol}: {e}")
            return None
    
    async def get_financial_statements(self, symbol: str, statement_type: str = "income", 
                                     market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get financial statements"""
        try:
            # Check cache first
            if use_cache:
                cache_key = f"{symbol}_{statement_type}"
                cached_data = await self.cache_service.get("statement", cache_key)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("statements", symbol, statement_type=statement_type, market=market)
            
            if result and use_cache:
                await self.cache_service.set("statement", cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting financial statements for {symbol}: {e}")
            return None
    
    async def get_market_statistics(self, symbol: str, market: str = "US", use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get market statistics"""
        try:
            # Check cache first
            if use_cache:
                cached_data = await self.cache_service.get("statistics", symbol)
                if cached_data:
                    return cached_data
            
            # Make request
            result = await self._make_request("statistics", symbol, market=market)
            
            if result and use_cache:
                await self.cache_service.set("statistics", symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting market statistics for {symbol}: {e}")
            return None
    
    async def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for symbols by name or ticker"""
        try:
            # Check cache first
            cache_key = f"search_{query}_{limit}"
            cached_data = await self.cache_service.get("search", cache_key)
            if cached_data:
                return cached_data.get("results", [])
            
            # For now, return a placeholder implementation
            # In a real implementation, you might use a different API or database
            results = []
            
            # Common stocks for demonstration
            common_stocks = [
                {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
                {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
                {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
                {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
                {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
                {"symbol": "RELIANCE.NS", "name": "Reliance Industries Limited", "exchange": "NSE"},
                {"symbol": "TCS.NS", "name": "Tata Consultancy Services Limited", "exchange": "NSE"},
                {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Limited", "exchange": "NSE"}
            ]
            
            query_upper = query.upper()
            for stock in common_stocks:
                if (query_upper in stock["symbol"].upper() or 
                    query_upper in stock["name"].upper()):
                    results.append({
                        "symbol": stock["symbol"],
                        "name": stock["name"],
                        "exchange": stock["exchange"]
                    })
                    
                    if len(results) >= limit:
                        break
            
            # Cache results
            await self.cache_service.set("search", cache_key, {"results": results})
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching symbols for {query}: {e}")
            return []
    
    async def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            rate_limit_stats = await self.rate_limiter.get_statistics()
            cache_stats = await self.cache_service.get_cache_info()
            
            return {
                "yahoo_finance": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": self.successful_requests / max(self.total_requests, 1)
                },
                "rate_limiting": rate_limit_stats,
                "caching": cache_stats,
                "configuration": {
                    "timeout": self.config.timeout,
                    "retries": self.config.retries,
                    "delay": self.config.delay,
                    "default_market": self.config.default_market,
                    "supported_markets": self.config.supported_markets
                }
            }
        except Exception as e:
            logger.error(f"❌ Error getting service statistics: {e}")
            return {}
    
    async def close(self) -> None:
        """Close the service"""
        if self.session:
            await self.session.close()
            logger.info("🔌 Yahoo Finance Service connections closed")
    
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized 