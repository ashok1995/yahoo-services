"""Health check endpoint."""

from datetime import datetime
from fastapi import APIRouter, Depends
from typing import Dict, Any

from api.models.responses import HealthResponse
from config.settings import settings
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns service health status and availability of external APIs.
    """
    try:
        health_data = {
            "status": "healthy",
            "service": settings.service_name,
            "yahoo_finance_available": settings.yahoo_finance_enabled,
            "alpha_vantage_available": settings.alpha_vantage_enabled and bool(settings.alpha_vantage_api_key),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Health check successful", extra={"context": health_data})
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": settings.service_name,
            "yahoo_finance_available": False,
            "alpha_vantage_available": False,
            "timestamp": datetime.now().isoformat()
        }
