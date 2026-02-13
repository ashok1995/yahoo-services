"""Global context endpoint - primary endpoint (90% usage)."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from api.models.responses import GlobalContextResponse, MarketData, VIXData, ForexData
from services.yahoo_finance_service import YahooFinanceService
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import YahooRateLimitException, ServiceUnavailableException

router = APIRouter()
logger = get_logger(__name__)


# This will be set by main.py
_yahoo_service: YahooFinanceService = None

def set_yahoo_service(service: YahooFinanceService):
    """Set Yahoo Finance service instance."""
    global _yahoo_service
    _yahoo_service = service

def get_yahoo_service() -> YahooFinanceService:
    """Dependency to get Yahoo Finance service."""
    return _yahoo_service


async def fetch_quote_data(
    service: YahooFinanceService,
    symbol: str
) -> Optional[Dict[str, Any]]:
    """Fetch quote data for a single symbol."""
    try:
        return await service.get_quote(symbol, market="US", use_cache=True)
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None


@router.get("/api/v1/global-context", response_model=GlobalContextResponse, tags=["global-context"])
async def get_global_context(
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
) -> Dict[str, Any]:
    """
    Get global market context.
    
    Fetches S&P 500, NASDAQ, Dow Jones, VIX, Gold, USD/INR, and Crude Oil data.
    Called every 5 minutes by seed-stocks-service.
    Cached for 5 minutes to avoid rate limits.
    
    Returns:
        Global market context with all major indices and commodities
    """
    start_time = datetime.now()
    
    try:
        # Get symbols from config
        symbols_str = settings.global_context_symbols
        symbols = [s.strip() for s in symbols_str.split(",")]
        
        # Mapping of symbols to response keys
        symbol_map = {
            "^GSPC": "sp500",
            "^IXIC": "nasdaq",
            "^DJI": "dow_jones",
            "^VIX": "vix",
            "GC=F": "gold",
            "USDINR=X": "usd_inr",
            "CL=F": "crude_oil"
        }
        
        # Fetch all quotes concurrently
        logger.info(f"Fetching global context for symbols: {symbols}")
        tasks = [fetch_quote_data(yahoo_service, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        # Build response
        response_data = {}
        failed_symbols = []
        
        for symbol, data in zip(symbols, results):
            if data is None:
                failed_symbols.append(symbol)
                continue
            
            key = symbol_map.get(symbol)
            if not key:
                continue
            
            # Extract price and change percent
            price = data.get("price")
            change_percent = data.get("change_percent")
            
            if price is None:
                failed_symbols.append(symbol)
                continue
            
            # Special handling for VIX and USD/INR
            if key == "vix":
                response_data[key] = VIXData(value=price).model_dump()
            elif key == "usd_inr":
                response_data[key] = ForexData(
                    rate=price,
                    change_percent=change_percent or 0.0
                ).model_dump()
            else:
                response_data[key] = MarketData(
                    price=price,
                    change_percent=change_percent or 0.0
                ).model_dump()
        
        # Check if we have all required data
        required_keys = ["sp500", "nasdaq", "dow_jones", "vix", "gold", "usd_inr", "crude_oil"]
        missing_keys = [k for k in required_keys if k not in response_data]
        
        if missing_keys:
            logger.warning(f"Missing data for: {missing_keys}. Failed symbols: {failed_symbols}")
            
            # If critical data is missing, raise error
            if any(k in ["sp500", "nasdaq", "vix"] for k in missing_keys):
                raise ServiceUnavailableException(
                    message="Critical market data unavailable",
                    details={"missing": missing_keys, "failed_symbols": failed_symbols}
                )
        
        # Add timestamp
        response_data["timestamp"] = datetime.now().isoformat()
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            "Global context fetched successfully",
            extra={
                "context": {
                    "duration_ms": duration_ms,
                    "symbols_fetched": len(symbols) - len(failed_symbols),
                    "symbols_failed": len(failed_symbols)
                }
            }
        )
        
        return response_data
        
    except YahooRateLimitException as e:
        logger.error(f"Yahoo rate limit exceeded: {e}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                },
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except ServiceUnavailableException as e:
        logger.error(f"Service unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                },
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in global context: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Failed to fetch global context",
                    "details": {"error": str(e)}
                },
                "timestamp": datetime.now().isoformat()
            }
        )
