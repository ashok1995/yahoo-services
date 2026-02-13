# Yahoo Services - Integration with seed-stocks-service

**Purpose**: Guide for integrating yahoo-services with seed-stocks-service  
**Primary Endpoint**: `/api/v1/global-context`  
**Called By**: `GlobalContextCollector`

---

## 🎯 Integration Overview

Yahoo Services provides global market data that Kite API doesn't have:

- **US/Global Indices**: S&P 500, NASDAQ, Dow Jones, VIX
- **Commodities**: Gold, Crude Oil
- **Forex**: USD/INR
- **Fundamentals**: P/E, P/B, market cap, margins

---

## 📋 Environment URLs

| Environment | URL | Port | Use Case |
|-------------|-----|------|----------|
| **Development** | `http://localhost:8085` | 8085 | Local development |
| **Staging** | `http://localhost:8285` | 8285 | Pre-production testing |
| **Production** | `http://localhost:8185` | 8185 | Production deployment |

---

## 🔌 Integration Points

### 1. GlobalContextCollector Integration

**Purpose**: Fetch global market context every 5 minutes

**Endpoint**: `GET /api/v1/global-context`

**Python Integration Example**:

```python
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

class YahooServicesClient:
    """Client for Yahoo Services integration."""
    
    def __init__(self, base_url: str = "http://localhost:8085"):
        self.base_url = base_url
        self.timeout = 10.0
    
    async def get_global_context(self) -> Optional[Dict[str, Any]]:
        """
        Fetch global market context.
        
        Returns:
            {
                "sp500": {"price": float, "change_percent": float},
                "nasdaq": {"price": float, "change_percent": float},
                "dow_jones": {"price": float, "change_percent": float},
                "vix": {"value": float},
                "gold": {"price": float, "change_percent": float},
                "usd_inr": {"rate": float, "change_percent": float},
                "crude_oil": {"price": float, "change_percent": float},
                "timestamp": str
            }
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/v1/global-context")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    # Service unavailable (critical data missing)
                    print(f"Yahoo Services unavailable: {response.json()}")
                    return None
                else:
                    print(f"Unexpected status: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            print("Yahoo Services timeout")
            return None
        except Exception as e:
            print(f"Error fetching global context: {e}")
            return None


# Usage in GlobalContextCollector
class GlobalContextCollector:
    """Collector for global market context."""
    
    def __init__(self):
        self.yahoo_client = YahooServicesClient(
            base_url="http://localhost:8285"  # Use staging URL
        )
    
    async def collect(self) -> Dict[str, Any]:
        """Collect global context every 5 minutes."""
        
        # Fetch from Yahoo Services
        data = await self.yahoo_client.get_global_context()
        
        if data is None:
            print("Failed to fetch global context")
            return {}
        
        # Extract data for your use case
        context = {
            "market_sentiment": self._calculate_sentiment(data),
            "sp500_price": data["sp500"]["price"],
            "sp500_change": data["sp500"]["change_percent"],
            "vix_level": data["vix"]["value"],
            "usd_inr_rate": data["usd_inr"]["rate"],  # Note: "rate" not "price"
            "gold_price": data["gold"]["price"],
            "timestamp": data["timestamp"]
        }
        
        return context
    
    def _calculate_sentiment(self, data: Dict[str, Any]) -> str:
        """Calculate market sentiment from indicators."""
        sp500_change = data["sp500"]["change_percent"]
        vix = data["vix"]["value"]
        
        if sp500_change > 1.0 and vix < 15:
            return "bullish"
        elif sp500_change < -1.0 or vix > 25:
            return "bearish"
        else:
            return "neutral"
```

---

### 2. Fundamentals Enrichment Integration

**Purpose**: Enrich stock data with fundamentals weekly

**Endpoint**: `POST /api/v1/fundamentals/batch`

**Python Integration Example**:

```python
from typing import List, Dict, Any

class FundamentalsEnrichment:
    """Enrich stock data with fundamentals."""
    
    def __init__(self):
        self.yahoo_client = YahooServicesClient(
            base_url="http://localhost:8285"
        )
    
    async def enrich_stocks(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch fundamentals for multiple stocks.
        
        Args:
            symbols: List of NSE symbols (e.g., ["RELIANCE.NS", "SBIN.NS"])
        
        Returns:
            Dict mapping symbol to fundamentals
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.yahoo_client.base_url}/api/v1/fundamentals/batch",
                    json={"symbols": symbols}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["fundamentals"]
                else:
                    print(f"Fundamentals request failed: {response.status_code}")
                    return {}
                    
        except Exception as e:
            print(f"Error fetching fundamentals: {e}")
            return {}


# Usage
async def weekly_enrichment():
    """Run weekly fundamentals enrichment."""
    enricher = FundamentalsEnrichment()
    
    # Get list of stocks to enrich
    nse_stocks = ["RELIANCE.NS", "SBIN.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
    
    # Fetch fundamentals
    fundamentals = await enricher.enrich_stocks(nse_stocks)
    
    # Store in database
    for symbol, metrics in fundamentals.items():
        print(f"{symbol}:")
        print(f"  Market Cap: {metrics.get('market_cap')}")
        print(f"  P/E Ratio: {metrics.get('pe_ratio')}")
        print(f"  P/B Ratio: {metrics.get('pb_ratio')}")
        print(f"  Profit Margin: {metrics.get('profit_margin')}")
```

---

## 🔄 Scheduled Collection

### GlobalContextCollector Schedule

**Frequency**: Every 5 minutes  
**Cache Duration**: 5 minutes

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Schedule global context collection every 5 minutes
scheduler.add_job(
    func=collect_global_context,
    trigger="interval",
    minutes=5,
    id="global_context_collector"
)

async def collect_global_context():
    """Collect global context."""
    collector = GlobalContextCollector()
    context = await collector.collect()
    
    # Store in database or Redis
    await store_global_context(context)
    
    print(f"Global context collected at {context.get('timestamp')}")

scheduler.start()
```

---

## 🧪 Testing Integration

### Development Environment Testing

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_yahoo_services_health():
    """Test Yahoo Services health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8085/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "yahoo-services"


@pytest.mark.asyncio
async def test_global_context_integration():
    """Test global context endpoint integration."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8085/api/v1/global-context")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "sp500" in data
        assert "nasdaq" in data
        assert "dow_jones" in data
        assert "vix" in data
        assert "gold" in data
        assert "usd_inr" in data
        assert "crude_oil" in data
        assert "timestamp" in data
        
        # Verify USD/INR has "rate" field
        assert "rate" in data["usd_inr"]
        assert "change_percent" in data["usd_inr"]


@pytest.mark.asyncio
async def test_fundamentals_integration():
    """Test fundamentals batch endpoint integration."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8085/api/v1/fundamentals/batch",
            json={"symbols": ["RELIANCE.NS", "SBIN.NS"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "fundamentals" in data
        assert "timestamp" in data
        
        # Verify fundamentals structure
        for symbol, metrics in data["fundamentals"].items():
            assert "market_cap" in metrics
            assert "pe_ratio" in metrics
            assert "pb_ratio" in metrics
```

---

## 🎯 Staging Integration Testing

### Update Configuration for Staging

```python
# config/settings.py in seed-stocks-service

class Settings:
    # Yahoo Services URL by environment
    YAHOO_SERVICES_URL: str = os.getenv(
        "YAHOO_SERVICES_URL",
        "http://localhost:8285"  # Default to staging
    )
```

### Run Integration Tests Against Staging

```bash
# Set environment variable
export YAHOO_SERVICES_URL=http://localhost:8285

# Run integration tests
pytest tests/integration/test_yahoo_services.py -v

# Expected output:
# ✅ test_yahoo_services_health PASSED
# ✅ test_global_context_integration PASSED
# ✅ test_fundamentals_integration PASSED
```

---

## 📊 Performance Considerations

### Expected Response Times

| Endpoint | First Call | Cached Call |
|----------|-----------|-------------|
| `/health` | < 500ms | < 500ms |
| `/api/v1/global-context` | 3-5 seconds | < 500ms |
| `/api/v1/fundamentals/batch` | 1-3 seconds | < 500ms |

### Caching Strategy

- **Global Context**: Cached for 5 minutes (matches collection frequency)
- **Fundamentals**: Cached for 1 day (fundamentals don't change often)

### Timeout Configuration

```python
# Recommended timeout settings
YAHOO_SERVICES_TIMEOUT = 10.0  # seconds

# For batch operations
YAHOO_SERVICES_BATCH_TIMEOUT = 30.0  # seconds
```

---

## 🔒 Error Handling

### Handle Service Unavailability

```python
async def fetch_with_fallback(client: YahooServicesClient):
    """Fetch global context with fallback."""
    
    # Try to fetch from Yahoo Services
    context = await client.get_global_context()
    
    if context is None:
        # Fallback: Use cached data from database
        context = await get_cached_global_context()
        
        if context is None:
            # Last resort: Use default values
            context = get_default_global_context()
            print("⚠️  Using default global context")
    
    return context
```

### Handle Partial Data

```python
def validate_global_context(data: Dict[str, Any]) -> bool:
    """Validate global context has all required fields."""
    required_fields = [
        "sp500", "nasdaq", "dow_jones", "vix",
        "gold", "usd_inr", "crude_oil", "timestamp"
    ]
    
    return all(field in data for field in required_fields)
```

---

## 🚀 Production Configuration

### Environment Variables

```bash
# In seed-stocks-service .env file

# Production
YAHOO_SERVICES_URL=http://localhost:8185

# Staging
YAHOO_SERVICES_URL=http://localhost:8285

# Development
YAHOO_SERVICES_URL=http://localhost:8085
```

### Circuit Breaker Pattern (Optional)

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def fetch_global_context():
    """Fetch with circuit breaker protection."""
    client = YahooServicesClient()
    return await client.get_global_context()
```

---

## 📝 Response Format Reference

### Global Context Response

```json
{
  "sp500": {
    "price": 6832.76,
    "change_percent": -1.57
  },
  "nasdaq": {
    "price": 22597.15,
    "change_percent": -2.03
  },
  "dow_jones": {
    "price": 49451.98,
    "change_percent": -1.34
  },
  "vix": {
    "value": 20.49
  },
  "gold": {
    "price": 4998.8,
    "change_percent": 1.02
  },
  "usd_inr": {
    "rate": 90.631,
    "change_percent": 0.12
  },
  "crude_oil": {
    "price": 63.0,
    "change_percent": 0.25
  },
  "timestamp": "2026-02-13T16:08:35.467563"
}
```

**⚠️ Important**: `usd_inr` uses `"rate"` field, not `"price"`

---

## 📞 Support & Troubleshooting

### Common Issues

1. **Connection Refused**: Check Yahoo Services is running
   ```bash
   curl http://localhost:8285/health
   ```

2. **Timeout**: Increase timeout setting
   ```python
   timeout = 30.0  # seconds
   ```

3. **Missing Fields**: Verify response format
   ```python
   assert "rate" in data["usd_inr"]  # Not "price"
   ```

---

**Last Updated**: 2026-02-13  
**Status**: Ready for Integration  
**Next Steps**: Test in staging → Validate → Deploy to production
