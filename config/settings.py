"""
Centralized configuration using pydantic-settings.
All settings loaded from environment variables.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file="envs/env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Service
    service_name: str = Field(default="yahoo-services", description="Service name")
    service_port: int = Field(default=8014, description="Service port")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development|production)")
    
    # Yahoo Finance
    yahoo_finance_enabled: bool = Field(default=True, description="Enable Yahoo Finance")
    yahoo_finance_rate_limit: int = Field(default=100, description="Yahoo Finance rate limit (req/min)")
    yahoo_finance_timeout: int = Field(default=10, description="Yahoo Finance timeout (seconds)")
    
    # Alpha Vantage (optional)
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API key")
    alpha_vantage_enabled: bool = Field(default=False, description="Enable Alpha Vantage")
    alpha_vantage_rate_limit: int = Field(default=5, description="Alpha Vantage rate limit (req/min)")
    
    # Global context symbols (Yahoo Finance tickers)
    # Only non-Kite data: US indices, VIX, commodities, USD/INR, Asian indices
    # Nifty 50 / Bank Nifty come from Kite Connect
    global_context_symbols: str = Field(
        default="^GSPC,^IXIC,^DJI,^VIX,GC=F,USDINR=X,CL=F,^N225,^HSI",
        description="Global context symbols (comma-separated)"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/3", description="Redis URL")
    redis_enabled: bool = Field(default=True, description="Enable Redis caching")
    
    # Cache TTLs (seconds)
    # Quote TTL derived from rate limit: 180 req/hr budget, 9 trend fetches/hr fixed cost
    # → 171 remaining / 9 symbols = 19 refreshes/symbol/hr → TTL = 3600/19 ≈ 190s
    # 200s gives 18 refreshes/symbol/hr (162 quotes + 9 trends = 171/hr), ~5% headroom
    cache_ttl_global_context: int = Field(default=200, description="Global context quote cache TTL (200s — rate-limit optimal)")
    cache_ttl_fundamentals: int = Field(default=86400, description="Fundamentals cache TTL (1 day)")
    cache_ttl_trends: int = Field(default=3600, description="Trend analysis cache TTL (1 hour — trends shift slowly)")
    
    def get_global_context_symbols(self) -> List[str]:
        """Parse global context symbols from comma-separated string."""
        return [s.strip() for s in self.global_context_symbols.split(",") if s.strip()]


# Global settings instance
settings = Settings()
