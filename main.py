"""
Yahoo Finance Microservice
==========================

FastAPI-based microservice for comprehensive Yahoo Finance data integration.
Provides real-time quotes, historical data, fundamental analysis, and financial statements.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes.quotes_routes import router as quotes_router
from api.routes.historical_routes import router as historical_router
from api.routes.fundamentals_routes import router as fundamentals_router
from api.routes.statements_routes import router as statements_router
from api.routes.search_routes import router as search_router
from services.yahoo_finance_service import YahooFinanceService, YahooFinanceConfig
from services.cache_service import CacheService, CacheConfig
from services.rate_limiter import RateLimiter, RateLimitConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
yahoo_finance_service: YahooFinanceService = None
cache_service: CacheService = None
rate_limiter: RateLimiter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global yahoo_finance_service, cache_service, rate_limiter
    
    # Startup
    logger.info("🚀 Starting Yahoo Finance Microservice...")
    
    try:
        # Initialize rate limiter
        rate_limit_config = RateLimitConfig()
        rate_limiter = RateLimiter(rate_limit_config)
        await rate_limiter.initialize()
        
        # Initialize cache service
        cache_config = CacheConfig()
        cache_service = CacheService(cache_config)
        await cache_service.initialize()
        
        # Initialize Yahoo Finance service
        yahoo_config = YahooFinanceConfig()
        yahoo_finance_service = YahooFinanceService(yahoo_config, cache_service, rate_limiter)
        await yahoo_finance_service.initialize()
        
        logger.info("✅ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Yahoo Finance Microservice...")
    
    try:
        if yahoo_finance_service:
            await yahoo_finance_service.close()
        if cache_service:
            await cache_service.close()
        if rate_limiter:
            await rate_limiter.close()
        
        logger.info("✅ All services shut down successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Yahoo Finance Microservice",
    description="Comprehensive Yahoo Finance data integration microservice",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(quotes_router, prefix="/api/v1/quotes", tags=["quotes"])
app.include_router(historical_router, prefix="/api/v1/historical", tags=["historical"])
app.include_router(fundamentals_router, prefix="/api/v1/fundamentals", tags=["fundamentals"])
app.include_router(statements_router, prefix="/api/v1/statements", tags=["statements"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])


# Dependency injection
def get_yahoo_finance_service() -> YahooFinanceService:
    """Get Yahoo Finance service instance."""
    if yahoo_finance_service is None:
        raise HTTPException(status_code=503, detail="Yahoo Finance service not initialized")
    return yahoo_finance_service


def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if cache_service is None:
        raise HTTPException(status_code=503, detail="Cache service not initialized")
    return cache_service


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    if rate_limiter is None:
        raise HTTPException(status_code=503, detail="Rate limiter not initialized")
    return rate_limiter


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        # Check if all services are initialized
        services_status = {
            "yahoo_finance_service": yahoo_finance_service is not None,
            "cache_service": cache_service is not None,
            "rate_limiter": rate_limiter is not None,
        }
        
        all_healthy = all(services_status.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "service": "yahoo-finance-microservice",
            "version": "1.0.0",
            "services": services_status,
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "yahoo-finance-microservice",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
        )


# Service status endpoint
@app.get("/status")
async def get_service_status() -> Dict[str, Any]:
    """Get detailed service status."""
    return {
        "service": "yahoo-finance-microservice",
        "version": "1.0.0",
        "description": "Comprehensive Yahoo Finance data integration microservice",
        "features": [
            "Real-time Quotes",
            "Historical Data",
            "Fundamental Analysis",
            "Financial Statements",
            "Company Information",
            "Market Statistics",
            "Advanced Search",
            "Rate Limiting",
            "Caching System"
        ],
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "quotes": "/api/v1/quotes",
            "historical": "/api/v1/historical",
            "fundamentals": "/api/v1/fundamentals",
            "statements": "/api/v1/statements",
            "search": "/api/v1/search"
        },
        "configuration": {
            "port": os.getenv("PORT", "8014"),
            "cache": "Redis",
            "rate_limiting": "Enabled",
            "external_apis": ["Yahoo Finance"]
        }
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8014"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting Yahoo Finance Microservice on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 