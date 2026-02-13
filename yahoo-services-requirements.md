# Yahoo-Services — Requirements for Bayesian Engine

**Service**: `yahoo-services` (port 8014)  
**Related**: [Market Data Requirements](./market-data-requirements.md), [Kite Service Requirements](./kite-service-requirements.md), [Design doc](../architecture/bayesian-engine-design.md)

This document defines what `yahoo-services` needs to provide for the Bayesian engine.

---

## Scope: Only data Kite CANNOT provide

**IMPORTANT**: We use Kite for all NSE/BSE stock data (quotes, historical, OHLC). Yahoo-services provides **ONLY** data that Kite cannot:

| Data type | Provider | Reason |
|-----------|----------|--------|
| NSE/BSE stock quotes | **Kite** ✅ | Real-time, reliable, official |
| NSE/BSE historical candles | **Kite** ✅ | Real-time, reliable, official |
| Global indices (S&P, NASDAQ, VIX) | **Yahoo** | Kite doesn't have US/global data |
| Commodities (Gold, Crude Oil) | **Yahoo** | Kite doesn't have commodities |
| Forex (USD/INR) | **Yahoo** | Kite has limited forex |
| Fundamentals (P/E, ROE, margins) | **Yahoo** | Kite has minimal fundamental data |
| Financial statements | **Yahoo** | Kite doesn't provide statements |
| Market cap | **Yahoo** | Kite doesn't expose market cap easily |

**No duplication** — avoid Yahoo rate limits by using Kite for all Indian stock data.

---

## Current state

**Location**: `/Users/ashokkumar/Desktop/ashok-personal/stocks/yahoo-services`  
**Port**: 8014  
**Framework**: FastAPI  
**Dependencies**: `yfinance==0.2.18`, Redis caching, rate limiting

**What exists**:
- `services/yahoo_finance_service.py` — full Yahoo Finance integration
- `services/cache_service.py` — Redis caching
- `services/rate_limiter.py` — Rate limiting

**What's broken**:
- Missing `api/routes/` layer — `main.py` imports routes that don't exist
- Service won't start until routes are implemented

---

## Endpoints to implement

### 1. Global context endpoint (PRIMARY USE CASE)

**Purpose**: Fetch S&P 500, NASDAQ, Dow Jones, VIX, Gold, USD/INR, Crude in one call.

**Why Yahoo**: Kite doesn't have US indices, commodities, or global forex.

```python
@router.get("/api/v1/global-context")
async def get_global_context():
    """Get global market context (S&P, NASDAQ, VIX, Gold, USD/INR, Crude)."""
    symbols = ["^GSPC", "^IXIC", "^DJI", "^VIX", "GC=F", "USDINR=X", "CL=F"]
    # Fetch batch from Yahoo Finance
    quotes = await yahoo_service.get_quotes_batch(symbols)
    return {
        "sp500": {"price": ..., "change_percent": ...},
        "nasdaq": {"price": ..., "change_percent": ...},
        "dow_jones": {"price": ..., "change_percent": ...},
        "vix": {"value": ...},
        "gold": {"price": ..., "change_percent": ...},
        "usd_inr": {"rate": ..., "change_percent": ...},
        "crude_oil": {"price": ..., "change_percent": ...},
        "timestamp": "2026-02-12T14:30:00+05:30"
    }
```

**Example request**:
```bash
curl http://localhost:8014/api/v1/global-context
```

**Expected response**:
```json
{
  "sp500": {"price": 5845.20, "change_percent": 0.45},
  "nasdaq": {"price": 18234.50, "change_percent": 0.62},
  "dow_jones": {"price": 44320.10, "change_percent": 0.28},
  "vix": {"value": 13.45},
  "gold": {"price": 2024.30, "change_percent": -0.15},
  "usd_inr": {"rate": 83.25, "change_percent": 0.08},
  "crude_oil": {"price": 78.45, "change_percent": 1.20},
  "timestamp": "2026-02-12T14:30:00+05:30"
}
```

**Called by**: `GlobalContextCollector` in seed-stocks-service (every 5 min).

### 2. Fundamentals endpoint (batch)

**Purpose**: Get P/E, P/B, market cap, ROE, margins for NSE stocks (supplement Kite data).

**Why Yahoo**: Kite has minimal fundamental data; Yahoo provides comprehensive fundamentals.

```python
@router.post("/api/v1/fundamentals/batch")
async def get_fundamentals_batch(request: FundamentalsRequest):
    """Get fundamentals for multiple stocks."""
    # request.symbols: List[str] (e.g., ["RELIANCE.NS", "SBIN.NS"])
    results = {}
    for symbol in request.symbols:
        results[symbol] = await yahoo_service.get_fundamentals(symbol)
    return {
        "fundamentals": results,
        "timestamp": ...
    }
```

**Example request**:
```bash
curl -X POST http://localhost:8014/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "SBIN.NS", "TCS.NS"]}'
```

**Expected response**:
```json
{
  "fundamentals": {
    "RELIANCE.NS": {
      "market_cap": 1660000000000,
      "pe_ratio": 28.5,
      "pb_ratio": 2.8,
      "roe": 12.5,
      "debt_to_equity": 0.45,
      "profit_margin": 8.2,
      "operating_margin": 11.5
    },
    "SBIN.NS": { ... }
  },
  "timestamp": "2026-02-12T14:30:00+05:30"
}
```

**Called by**: Weekly fundamental enrichment job (not critical path).

### 3. Alpha Vantage integration (optional fallback)

**Purpose**: Backup for global context when Yahoo is rate-limited.

**Why needed**: Yahoo has rate limits (~100-200 req/min); Alpha Vantage as fallback.

```python
@router.get("/api/v1/alpha-vantage/global-context")
async def get_alpha_vantage_global_context():
    """Get global context from Alpha Vantage (fallback for Yahoo)."""
    # Call Alpha Vantage for S&P, VIX if Yahoo fails
    # Return normalized format matching Yahoo response
```

**Config**: Set `ALPHA_VANTAGE_API_KEY` in yahoo-services env (optional).

### 4. Health check

```python
@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "yahoo-services",
        "yahoo_finance_available": True,
        "alpha_vantage_available": False,  # if key not set
        "timestamp": "2026-02-12T14:30:00+05:30"
    }
```

---

## Configuration (add to yahoo-services env files)

```bash
# Yahoo Finance
YAHOO_FINANCE_ENABLED=true
YAHOO_FINANCE_RATE_LIMIT=100      # Conservative limit to avoid blocks
YAHOO_FINANCE_TIMEOUT=10

# Alpha Vantage (optional fallback)
ALPHA_VANTAGE_API_KEY=             # Set if you have one (500 calls/day free)
ALPHA_VANTAGE_ENABLED=false
ALPHA_VANTAGE_RATE_LIMIT=5

# Global context symbols
GLOBAL_CONTEXT_SYMBOLS=^GSPC,^IXIC,^DJI,^VIX,GC=F,USDINR=X,CL=F

# Redis caching
REDIS_URL=redis://localhost:6379/3
REDIS_ENABLED=true

# Cache TTLs (aggressive caching to reduce Yahoo calls)
CACHE_TTL_GLOBAL_CONTEXT=300       # 5 minutes (called every 5 min)
CACHE_TTL_FUNDAMENTALS=86400       # 1 day (fundamentals don't change often)
```

---

## Endpoints summary for seed-stocks-service consumption

| Endpoint | Method | Purpose | Frequency | Cache TTL | Why not Kite? |
|----------|--------|---------|-----------|-----------|---------------|
| `/api/v1/global-context` | GET | S&P, NASDAQ, VIX, Gold, USD/INR, Crude | Every 5 min | 300s | Kite doesn't have US/global data |
| `/api/v1/fundamentals/batch` | POST | P/E, market cap, ROE, margins | Weekly | 86400s | Kite has minimal fundamentals |
| `/api/v1/alpha-vantage/global-context` | GET | Fallback for global context | On Yahoo failure | 300s | Backup when Yahoo rate-limited |
| `/health` | GET | Health check | — | — | — |

**NOT included** (use Kite instead):
- ❌ Stock quotes (NSE/BSE) → Use Kite batch quotes
- ❌ Historical candles → Use Kite historical API
- ❌ Market breadth (Nifty 50) → Use Kite market context

---

## Pre-integration verification

Before integrating with seed-stocks-service, verify yahoo-services is working:

```bash
# Start yahoo-services
cd /Users/ashokkumar/Desktop/ashok-personal/stocks/yahoo-services
uvicorn main:app --host 0.0.0.0 --port 8014 --reload

# Test endpoints
curl http://localhost:8014/health

# Test global context (PRIMARY ENDPOINT)
curl http://localhost:8014/api/v1/global-context

# Test fundamentals batch
curl -X POST http://localhost:8014/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "SBIN.NS", "TCS.NS"]}'
```

**Expected output**: Global context should return S&P, NASDAQ, VIX, Gold, USD/INR, Crude with current prices.

---

## Timeline for yahoo-services setup

| Task | Duration | Deliverable |
|------|----------|------------|
| Fix service startup | 1 hour | Remove broken imports, get service running |
| Add global context endpoint | 2-3 hours | `/api/v1/global-context` (S&P, VIX, Gold, etc.) |
| Add fundamentals batch endpoint | 1-2 hours | `/api/v1/fundamentals/batch` |
| Add Alpha Vantage fallback (optional) | 2 hours | `/api/v1/alpha-vantage/global-context` |
| Testing + caching | 2 hours | Test endpoints, verify caching works |
| **Total** | **6-10 hours** | **Ready for seed-stocks integration** |

**Simplified scope** — only 2-3 endpoints instead of 6+, focused on data Kite doesn't provide.

---

## Related

- [Market Data Requirements](./market-data-requirements.md)
- [Kite Service Requirements](./kite-service-requirements.md)
- [Design doc](../architecture/bayesian-engine-design.md)
