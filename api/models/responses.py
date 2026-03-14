"""Response Pydantic models for API endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TrendData(BaseModel):
    """ML-ready trend metrics for a single timeframe horizon."""

    roc: float = Field(..., description="Rate of change (%)")
    slope_per_day: float = Field(..., description="Linear regression slope (%/day, normalized)")
    r_squared: float = Field(..., description="Trend consistency (0-1, higher = cleaner trend)")
    rsi: float = Field(..., description="Relative Strength Index (0-100)")
    volatility_annualized: float = Field(..., description="Annualized return volatility (%)")
    atr_pct: float = Field(..., description="Average True Range as % of price")
    sma: float = Field(..., description="Simple Moving Average of close prices")
    sma_distance_pct: float = Field(..., description="Price distance from SMA (%)")
    period_high: float = Field(..., description="Highest price in window")
    period_low: float = Field(..., description="Lowest price in window")
    regime: str = Field(..., description="Trend regime: strong_bullish|bullish|weak_bullish|consolidating|weak_bearish|bearish|strong_bearish")
    volatility_regime: str = Field(..., description="Volatility regime: low|normal|high|extreme")
    candles_used: int = Field(..., description="Number of candles in this window")


class TrendInfo(BaseModel):
    """Multi-timeframe trend analysis. Cached with 1-hour TTL (separate from quote cache)."""

    short_term: Optional[TrendData] = Field(None, description="5-day trend")
    medium_term: Optional[TrendData] = Field(None, description="1-month (~22 trading days) trend")
    long_term: Optional[TrendData] = Field(None, description="3-month trend")


class MarketData(BaseModel):
    """Market data for a single asset."""

    price: float = Field(..., description="Current price")
    change_percent: float = Field(..., description="Percentage change")
    trend: Optional[TrendInfo] = Field(None, description="Multi-timeframe trend analysis")


class ForexData(BaseModel):
    """Forex exchange rate data."""

    rate: float = Field(..., description="Exchange rate")
    change_percent: float = Field(..., description="Percentage change")
    trend: Optional[TrendInfo] = Field(None, description="Multi-timeframe trend analysis")


class VIXData(BaseModel):
    """VIX volatility index data."""

    value: float = Field(..., description="VIX value")
    trend: Optional[TrendInfo] = Field(None, description="Multi-timeframe trend analysis")


class GlobalContextResponse(BaseModel):
    """Response model for global context endpoint."""

    sp500: MarketData = Field(..., description="S&P 500 index data")
    nasdaq: MarketData = Field(..., description="NASDAQ index data")
    dow_jones: MarketData = Field(..., description="Dow Jones index data")
    vix: VIXData = Field(..., description="VIX volatility index data")
    gold: MarketData = Field(..., description="Gold futures data")
    usd_inr: ForexData = Field(..., description="USD/INR exchange rate data")
    crude_oil: MarketData = Field(..., description="Crude oil futures data")
    timestamp: str = Field(..., description="Timestamp in ISO format")

    class Config:
        json_schema_extra = {
            "example": {
                "sp500": {
                    "price": 5845.20, "change_percent": 0.45,
                    "trend": {
                        "short_term": {
                            "roc": -2.41, "slope_per_day": -0.65, "r_squared": 0.87,
                            "rsi": 38.5, "volatility_annualized": 10.3, "atr_pct": 1.12,
                            "sma": 5870.5, "sma_distance_pct": -0.43,
                            "period_high": 5920.0, "period_low": 5800.0,
                            "regime": "bearish", "volatility_regime": "normal", "candles_used": 5
                        },
                        "medium_term": None,
                        "long_term": None
                    }
                },
                "nasdaq": {"price": 18234.50, "change_percent": 0.62, "trend": None},
                "dow_jones": {"price": 44320.10, "change_percent": 0.28, "trend": None},
                "vix": {"value": 13.45, "trend": None},
                "gold": {"price": 2024.30, "change_percent": -0.15, "trend": None},
                "usd_inr": {"rate": 83.25, "change_percent": 0.08, "trend": None},
                "crude_oil": {"price": 78.45, "change_percent": 1.20, "trend": None},
                "timestamp": "2026-02-12T14:30:00+05:30"
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
