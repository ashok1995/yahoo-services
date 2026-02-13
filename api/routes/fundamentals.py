"""Fundamentals batch endpoint."""

import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from api.models.requests import FundamentalsRequest
from api.models.responses import FundamentalsResponse, FundamentalsData
from services.yahoo_finance_service import YahooFinanceService
from utils.logger import get_logger
from utils.exceptions import YahooRateLimitException

router = APIRouter()
logger = get_logger(__name__)


def get_yahoo_service() -> YahooFinanceService:
    """Dependency to get Yahoo Finance service (placeholder for DI)."""
    pass


async def fetch_fundamentals_data(
    service: YahooFinanceService,
    symbol: str
) -> Dict[str, Any]:
    """Fetch fundamentals for a single symbol."""
    try:
        data = await service.get_fundamentals(symbol, market="IN", use_cache=True)
        if data is None:
            return {"symbol": symbol, "data": None}
        
        # Extract relevant fundamental metrics
        fundamentals = FundamentalsData(
            market_cap=data.get("market_cap"),
            pe_ratio=data.get("pe_ratio"),
            pb_ratio=data.get("pb_ratio"),
            roe=data.get("roe"),
            debt_to_equity=data.get("debt_to_equity"),
            profit_margin=data.get("profit_margin"),
            operating_margin=data.get("operating_margin")
        )
        
        return {"symbol": symbol, "data": fundamentals}
        
    except Exception as e:
        logger.error(f"Error fetching fundamentals for {symbol}: {e}")
        return {"symbol": symbol, "data": None}


@router.post("/api/v1/fundamentals/batch", response_model=FundamentalsResponse, tags=["fundamentals"])
async def get_fundamentals_batch(
    request: FundamentalsRequest,
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
) -> Dict[str, Any]:
    """
    Get fundamentals for multiple stocks in batch.
    
    Fetches P/E, P/B, market cap, ROE, debt-to-equity, and margins.
    Called weekly for fundamental enrichment (not critical path).
    Cached for 1 day as fundamentals don't change frequently.
    
    Args:
        request: List of symbols to fetch fundamentals for
    
    Returns:
        Fundamentals data by symbol
    """
    start_time = datetime.now()
    
    try:
        symbols = request.symbols
        logger.info(f"Fetching fundamentals for {len(symbols)} symbols")
        
        # Fetch fundamentals concurrently
        tasks = [fetch_fundamentals_data(yahoo_service, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        # Build response
        fundamentals_map = {}
        failed_symbols = []
        
        for result in results:
            symbol = result["symbol"]
            data = result["data"]
            
            if data is None:
                failed_symbols.append(symbol)
                continue
            
            fundamentals_map[symbol] = data.model_dump()
        
        if failed_symbols:
            logger.warning(f"Failed to fetch fundamentals for: {failed_symbols}")
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            "Fundamentals batch fetched successfully",
            extra={
                "context": {
                    "duration_ms": duration_ms,
                    "symbols_requested": len(symbols),
                    "symbols_fetched": len(fundamentals_map),
                    "symbols_failed": len(failed_symbols)
                }
            }
        )
        
        return {
            "fundamentals": fundamentals_map,
            "timestamp": datetime.now().isoformat()
        }
        
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
    
    except Exception as e:
        logger.error(f"Unexpected error in fundamentals batch: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Failed to fetch fundamentals",
                    "details": {"error": str(e)}
                },
                "timestamp": datetime.now().isoformat()
            }
        )
