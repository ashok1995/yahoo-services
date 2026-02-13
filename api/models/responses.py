"""Response Pydantic models for API endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MarketData(BaseModel):
    """Market data for a single asset."""
    
    price: float = Field(..., description="Current price")
    change_percent: float = Field(..., description="Percentage change")


class VIXData(BaseModel):
    """VIX volatility index data."""
    
    value: float = Field(..., description="VIX value")


class GlobalContextResponse(BaseModel):
    """Response model for global context endpoint."""
    
    sp500: MarketData = Field(..., description="S&P 500 index data")
    nasdaq: MarketData = Field(..., description="NASDAQ index data")
    dow_jones: MarketData = Field(..., description="Dow Jones index data")
    vix: VIXData = Field(..., description="VIX volatility index data")
    gold: MarketData = Field(..., description="Gold futures data")
    usd_inr: MarketData = Field(..., description="USD/INR exchange rate data")
    crude_oil: MarketData = Field(..., description="Crude oil futures data")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sp500": {"price": 5845.20, "change_percent": 0.45},
                "nasdaq": {"price": 18234.50, "change_percent": 0.62},
                "dow_jones": {"price": 44320.10, "change_percent": 0.28},
                "vix": {"value": 13.45},
                "gold": {"price": 2024.30, "change_percent": -0.15},
                "usd_inr": {"rate": 83.25, "change_percent": 0.08},
                "crude_oil": {"price": 78.45, "change_percent": 1.20},
                "timestamp": "2026-02-13T14:30:00+05:30"
            }
        }


class FundamentalsData(BaseModel):
    """Fundamentals data for a single stock."""
    
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[float] = Field(None, description="Price-to-book ratio")
    roe: Optional[float] = Field(None, description="Return on equity")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-equity ratio")
    profit_margin: Optional[float] = Field(None, description="Profit margin")
    operating_margin: Optional[float] = Field(None, description="Operating margin")


class FundamentalsResponse(BaseModel):
    """Response model for fundamentals batch endpoint."""
    
    fundamentals: Dict[str, FundamentalsData] = Field(..., description="Fundamentals by symbol")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fundamentals": {
                    "RELIANCE.NS": {
                        "market_cap": 1660000000000,
                        "pe_ratio": 28.5,
                        "pb_ratio": 2.8,
                        "roe": 12.5,
                        "debt_to_equity": 0.45,
                        "profit_margin": 8.2,
                        "operating_margin": 11.5
                    }
                },
                "timestamp": "2026-02-13T14:30:00+05:30"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Health status (healthy|unhealthy)")
    service: str = Field(..., description="Service name")
    yahoo_finance_available: bool = Field(..., description="Yahoo Finance availability")
    alpha_vantage_available: bool = Field(..., description="Alpha Vantage availability")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "yahoo-services",
                "yahoo_finance_available": True,
                "alpha_vantage_available": False,
                "timestamp": "2026-02-13T14:30:00+05:30"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: str = Field(..., description="Timestamp in ISO format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "YAHOO_RATE_LIMIT_EXCEEDED",
                    "message": "Yahoo Finance rate limit exceeded",
                    "details": {}
                },
                "timestamp": "2026-02-13T14:30:00+05:30"
            }
        }
