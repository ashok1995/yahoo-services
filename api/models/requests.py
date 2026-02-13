"""Request Pydantic models for API endpoints."""

from typing import List
from pydantic import BaseModel, Field


class FundamentalsRequest(BaseModel):
    """Request model for fundamentals batch endpoint."""
    
    symbols: List[str] = Field(
        ...,
        description="List of symbols to fetch fundamentals for (e.g., ['RELIANCE.NS', 'SBIN.NS'])",
        min_length=1,
        max_length=50
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["RELIANCE.NS", "SBIN.NS", "TCS.NS"]
            }
        }
