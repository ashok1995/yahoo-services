"""Global context endpoint - primary endpoint (90% usage)."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends

from api.models.responses import (
    GlobalContextResponse, MarketData, VIXData, ForexData, TrendInfo, TrendData,
)
from services.yahoo_finance_service import YahooFinanceService
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import YahooRateLimitException, ServiceUnavailableException

router = APIRouter()
logger = get_logger(__name__)


_yahoo_service: YahooFinanceService = None

def set_yahoo_service(service: YahooFinanceService):
    """Set Yahoo Finance service instance."""
    global _yahoo_service
    _yahoo_service = service

def get_yahoo_service() -> YahooFinanceService:
    """Dependency to get Yahoo Finance service."""
    return _yahoo_service


SYMBOL_MAP = {
    "^GSPC": "sp500",
    "^IXIC": "nasdaq",
    "^DJI": "dow_jones",
    "^VIX": "vix",
    "GC=F": "gold",
    "USDINR=X": "usd_inr",
    "CL=F": "crude_oil",
    "^N225": "nikkei",
    "^HSI": "hang_seng",
}


async def fetch_quote_data(
    service: YahooFinanceService,
    symbol: str
) -> Optional[Dict[str, Any]]:
    """Fetch quote data for a single symbol."""
    try:
        return await service.get_quote(symbol, market="US", use_cache=True)
    except Exception as e:
        logger.error(f"Error fetching quote {symbol}: {e}")
        return None


async def fetch_trend_data(
    service: YahooFinanceService,
    symbol: str,
    current_price: float,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Fetch trend data for a single symbol. Returns None on any failure."""
    try:
        return await service.get_trend_data(
            symbol, current_price,
            market="US", use_cache=True,
            cache_ttl=settings.cache_ttl_trends,
        )
    except Exception as e:
        logger.warning(f"Trend fetch failed for {symbol} (non-critical): {e}")
        return None


def _build_trend_info(trend_dict: Optional[Dict]) -> Optional[TrendInfo]:
    """Convert raw trend dict to TrendInfo model. Returns None if data is missing."""
    if not trend_dict:
        return None
    try:
        return TrendInfo(
            short_term=TrendData(**trend_dict["short_term"]) if trend_dict.get("short_term") else None,
            medium_term=TrendData(**trend_dict["medium_term"]) if trend_dict.get("medium_term") else None,
            long_term=TrendData(**trend_dict["long_term"]) if trend_dict.get("long_term") else None,
        )
    except Exception as e:
        logger.warning(f"Failed to build TrendInfo: {e}")
        return None


@router.get("/api/v1/global-context", response_model=GlobalContextResponse, tags=["global-context"])
async def get_global_context(
    yahoo_service: YahooFinanceService = Depends(get_yahoo_service)
) -> Dict[str, Any]:
    """
    Get global market context with multi-timeframe trend analysis.

    Fetches S&P 500, NASDAQ, Dow Jones, VIX, Gold, USD/INR, Crude Oil; optional Asian (Nikkei, Hang Seng).
    Each asset includes optional trend analysis (short/medium/long term) with
    ML-ready metrics: ROC, regression slope, R², RSI, volatility, regime bins.
    Indian indices (Nifty, Bank Nifty) come from Kite. Quotes cached 5 min, trends 1 hr.
    """
    start_time = datetime.now()

    try:
        symbols_str = settings.global_context_symbols
        symbols = [s.strip() for s in symbols_str.split(",")]

        # SYMBOL_MAP already includes ^N225->nikkei, ^HSI->hang_seng when symbols list has them
        logger.info(f"Fetching global context for symbols: {symbols}")
        quote_tasks = [fetch_quote_data(yahoo_service, s) for s in symbols]
        quote_results = await asyncio.gather(*quote_tasks)

        quotes: Dict[str, Dict[str, Any]] = {}
        failed_symbols = []

        for symbol, data in zip(symbols, quote_results):
            key = SYMBOL_MAP.get(symbol)
            if not key or data is None or data.get("price") is None:
                failed_symbols.append(symbol)
                continue
            quotes[key] = {"symbol": symbol, "data": data}

        required_critical = ["sp500", "nasdaq", "vix"]
        missing_keys = [k for k in SYMBOL_MAP.values() if k not in quotes]
        if any(k in required_critical for k in missing_keys):
            raise ServiceUnavailableException(
                message="Critical market data unavailable",
                details={"missing": missing_keys, "failed_symbols": failed_symbols},
            )

        # ── Phase 2: Fetch trends concurrently (lightweight, 1hr cache) ──
        trend_tasks = []
        trend_keys = []
        for key, info in quotes.items():
            trend_tasks.append(
                fetch_trend_data(yahoo_service, info["symbol"], info["data"]["price"])
            )
            trend_keys.append(key)

        trend_results = await asyncio.gather(*trend_tasks)
        trends: Dict[str, Optional[TrendInfo]] = {}
        for key, raw_trend in zip(trend_keys, trend_results):
            trends[key] = _build_trend_info(raw_trend)

        # ── Phase 3: Build response ──
        response_data = {}

        for key, info in quotes.items():
            data = info["data"]
            price = data.get("price")
            change_pct = data.get("change_percent", 0.0) or 0.0
            trend_info = trends.get(key)

            if key == "vix":
                response_data[key] = VIXData(value=price, trend=trend_info).model_dump()
            elif key == "usd_inr":
                response_data[key] = ForexData(
                    rate=price, change_percent=change_pct, trend=trend_info,
                ).model_dump()
            else:
                response_data[key] = MarketData(
                    price=price, change_percent=change_pct, trend=trend_info,
                ).model_dump()

        response_data["timestamp"] = datetime.now().isoformat()

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        trends_ok = sum(1 for t in trends.values() if t is not None)
        logger.info(
            "Global context fetched successfully",
            extra={
                "context": {
                    "duration_ms": duration_ms,
                    "symbols_fetched": len(quotes),
                    "symbols_failed": len(failed_symbols),
                    "trends_attached": trends_ok,
                    "trends_failed": len(quotes) - trends_ok,
                }
            }
        )

        return response_data

    except YahooRateLimitException as e:
        logger.error(f"Yahoo rate limit exceeded: {e}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": {"code": e.code, "message": e.message, "details": e.details},
                "timestamp": datetime.now().isoformat(),
            }
        )

    except ServiceUnavailableException as e:
        logger.error(f"Service unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": {"code": e.code, "message": e.message, "details": e.details},
                "timestamp": datetime.now().isoformat(),
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
                    "details": {"error": str(e)},
                },
                "timestamp": datetime.now().isoformat(),
            }
        )
