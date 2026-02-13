"""Alpha Vantage fallback endpoint (optional)."""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from api.models.responses import GlobalContextResponse
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import AlphaVantageException

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/v1/alpha-vantage/global-context", response_model=GlobalContextResponse, tags=["alpha-vantage"])
async def get_alpha_vantage_global_context() -> Dict[str, Any]:
    """
    Get global context from Alpha Vantage (fallback for Yahoo).
    
    This endpoint is used as a fallback when Yahoo Finance is rate-limited.
    Only available if ALPHA_VANTAGE_API_KEY is set in configuration.
    
    Returns:
        Global market context (normalized to match Yahoo format)
    """
    try:
        # Check if Alpha Vantage is enabled
        if not settings.alpha_vantage_enabled or not settings.alpha_vantage_api_key:
            raise HTTPException(
                status_code=501,
                detail={
                    "error": {
                        "code": "ALPHA_VANTAGE_NOT_CONFIGURED",
                        "message": "Alpha Vantage is not configured. Set ALPHA_VANTAGE_API_KEY to enable.",
                        "details": {}
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # TODO: Implement Alpha Vantage integration
        # For now, return not implemented
        logger.warning("Alpha Vantage endpoint called but not fully implemented")
        
        raise HTTPException(
            status_code=501,
            detail={
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "Alpha Vantage integration not yet implemented",
                    "details": {"note": "Use Yahoo Finance endpoint for now"}
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except AlphaVantageException as e:
        logger.error(f"Alpha Vantage error: {e}")
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
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in Alpha Vantage endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Failed to fetch from Alpha Vantage",
                    "details": {"error": str(e)}
                },
                "timestamp": datetime.now().isoformat()
            }
        )
