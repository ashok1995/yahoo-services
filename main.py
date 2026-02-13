"""
Yahoo Services Microservice
============================

FastAPI microservice providing ONLY data that Kite cannot provide:
- US/global indices (S&P 500, NASDAQ, VIX)
- Commodities (Gold, Crude Oil)
- Forex (USD/INR)
- Fundamentals (P/E, ROE, market cap, margins)

Port: 8014
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import health, global_context, fundamentals, alpha_vantage
from services.yahoo_finance_service import YahooFinanceService, YahooFinanceConfig
from services.cache_service import CacheService, CacheConfig
from services.rate_limiter import RateLimiter, RateLimitConfig
from config.settings import settings
from utils.logger import setup_logger, get_logger
from utils.exceptions import YahooServicesException

# Setup logging
setup_logger(
    name="yahoo-services",
    log_level=settings.log_level,
    service_name=settings.service_name
)
logger = get_logger(__name__)

# Global service instances
yahoo_finance_service: YahooFinanceService = None
cache_service: CacheService = None
rate_limiter: RateLimiter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global yahoo_finance_service, cache_service, rate_limiter
    
    # Startup
    logger.info(f"🚀 Starting {settings.service_name} on port {settings.service_port}...")
    
    try:
        # Initialize rate limiter
        rate_limit_config = RateLimitConfig()
        rate_limiter = RateLimiter(rate_limit_config)
        await rate_limiter.initialize()
        
        # Initialize cache service
        cache_config = CacheConfig.from_env()
        cache_service = CacheService(cache_config)
        await cache_service.initialize()
        
        # Initialize Yahoo Finance service
        yahoo_config = YahooFinanceConfig.from_env()
        yahoo_finance_service = YahooFinanceService(yahoo_config, cache_service, rate_limiter)
        await yahoo_finance_service.initialize()
        
        # Set service instances in route modules
        global_context.set_yahoo_service(yahoo_finance_service)
        fundamentals.set_yahoo_service(yahoo_finance_service)
        
        logger.info("✅ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down services...")
    
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
    title="Yahoo Services",
    description="Microservice providing data Kite cannot provide (US indices, commodities, forex, fundamentals)",
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


# Dependency injection for routes
def get_yahoo_finance_service() -> YahooFinanceService:
    """Get Yahoo Finance service instance."""
    if yahoo_finance_service is None:
        raise HTTPException(status_code=503, detail="Yahoo Finance service not initialized")
    return yahoo_finance_service


# Override dependency in route modules (will be set after services initialize)
# This is done in the lifespan startup


# Include routers
app.include_router(health.router)
app.include_router(global_context.router)
app.include_router(fundamentals.router)
app.include_router(alpha_vantage.router)


# Exception handlers
@app.exception_handler(YahooServicesException)
async def yahoo_services_exception_handler(request: Request, exc: YahooServicesException):
    """Handle custom exceptions."""
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)}
            },
            "timestamp": datetime.now().isoformat()
        }
    )


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "description": "Microservice providing data Kite cannot provide",
        "endpoints": {
            "health": "/health",
            "global_context": "/api/v1/global-context",
            "fundamentals_batch": "/api/v1/fundamentals/batch",
            "alpha_vantage_fallback": "/api/v1/alpha-vantage/global-context (optional)"
        },
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Kill any process using port 8014
    import os
    import subprocess
    
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{settings.service_port}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                logger.info(f"Killing process {pid} using port {settings.service_port}")
                subprocess.run(["kill", "-9", pid])
    except Exception as e:
        logger.warning(f"Could not kill processes on port {settings.service_port}: {e}")
    
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
