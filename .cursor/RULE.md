# Yahoo-Services — Master Development Rules

## Core Principle: Zero Redundancy, Maximum Efficiency

**This service provides ONLY what Kite cannot. No demos. No redundant code. Production-grade only.**

---

## 1. Scope Enforcement (STRICT)

### ✅ ALLOWED — What Yahoo-Services Should Provide

| Data Type | Reason |
|-----------|--------|
| Global indices (S&P 500, NASDAQ, Dow, VIX) | Kite doesn't have US/global data |
| Commodities (Gold, Crude Oil) | Kite doesn't have commodities |
| Forex (USD/INR) | Kite has limited forex |
| Fundamentals (P/E, ROE, market cap, margins) | Kite has minimal fundamental data |

### ❌ FORBIDDEN — Use Kite Instead

- ❌ NSE/BSE stock quotes → **Use Kite batch quotes**
- ❌ NSE/BSE historical candles → **Use Kite historical API**
- ❌ NSE/BSE OHLC data → **Use Kite**
- ❌ Market breadth (Nifty 50) → **Use Kite market context**

**If you're about to fetch NSE/BSE stock data from Yahoo, STOP. Use Kite instead.**

---

## 2. Endpoint Requirements (ONLY 4 ENDPOINTS)

### Required Endpoints

1. **`GET /api/v1/global-context`** (PRIMARY — 90% of usage)
   - S&P 500, NASDAQ, Dow Jones, VIX, Gold, USD/INR, Crude Oil
   - Called every 5 minutes by seed-stocks-service
   - Cache TTL: 300s (5 minutes)

2. **`POST /api/v1/fundamentals/batch`**
   - Batch fundamentals: P/E, P/B, market cap, ROE, margins
   - Called weekly (not critical path)
   - Cache TTL: 86400s (1 day)

3. **`GET /api/v1/alpha-vantage/global-context`** (OPTIONAL)
   - Fallback for global context when Yahoo rate-limited
   - Only if `ALPHA_VANTAGE_API_KEY` is set

4. **`GET /health`**
   - Health check with service status

**DO NOT create additional endpoints unless explicitly required.**

---

## 3. Code Architecture Standards

### File Structure (FastAPI Best Practices)

```
yahoo-services/
├── main.py                          # FastAPI app entry point
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── global_context.py        # Global context endpoint
│   │   ├── fundamentals.py          # Fundamentals batch endpoint
│   │   ├── alpha_vantage.py         # Alpha Vantage fallback (optional)
│   │   └── health.py                # Health check
│   └── models/
│       ├── __init__.py
│       ├── requests.py              # Pydantic request models
│       └── responses.py             # Pydantic response models
├── services/
│   ├── __init__.py
│   ├── yahoo_finance_service.py     # Yahoo Finance integration (EXISTS)
│   ├── cache_service.py             # Redis caching (EXISTS)
│   ├── rate_limiter.py              # Rate limiting (EXISTS)
│   └── alpha_vantage_service.py     # Alpha Vantage integration (NEW, OPTIONAL)
├── config/
│   ├── __init__.py
│   └── settings.py                  # Centralized config (pydantic-settings)
├── utils/
│   ├── __init__.py
│   ├── logger.py                    # Centralized logging
│   └── exceptions.py                # Custom exceptions
└── tests/                           # Unit tests (only if requested)
```

### Mandatory Patterns

1. **Configuration Management**
   - Use `pydantic-settings` for all config
   - NO hardcoded values in code
   - Environment variables loaded from `.env`
   - Validate all config on startup

2. **Data Models (Pydantic)**
   - All request/response bodies use Pydantic models
   - All service layer data uses Pydantic models
   - Enables automatic validation and serialization

3. **Logging (Structured)**
   - Use Python `logging` module
   - Log to file: `logs/yahoo-services.log`
   - JSON format for structured logging
   - Include: timestamp, level, module, message, context
   - Log rotation: 10MB per file, keep 5 files

4. **Error Handling (Consistent)**
   - Custom exception classes in `utils/exceptions.py`
   - HTTP exception handlers in `main.py`
   - Return standardized error responses:
     ```json
     {
       "error": {
         "code": "YAHOO_RATE_LIMIT_EXCEEDED",
         "message": "Yahoo Finance rate limit exceeded",
         "details": {...}
       },
       "timestamp": "2026-02-13T..."
     }
     ```

5. **Dependency Injection**
   - Use FastAPI's dependency injection
   - Inject services, config, cache into routes
   - Makes testing easier (if tests are written)

---

## 4. Code Quality Rules

### Minimal Code, Maximum Reusability

1. **DRY Principle (Don't Repeat Yourself)**
   - If logic is used 2+ times, extract to function
   - If data structure is used 2+ times, create Pydantic model
   - Scan for similar logic before writing new code

2. **Single Responsibility**
   - Routes: Handle HTTP requests/responses only
   - Services: Business logic and external API calls
   - Models: Data validation and serialization
   - Utils: Shared utilities (logging, exceptions)

3. **No Premature Optimization**
   - Use Redis caching for rate limit protection
   - Batch requests when possible (e.g., `get_quotes_batch`)
   - Don't optimize until profiling shows bottleneck

4. **Type Hints Everywhere**
   - All functions have type hints
   - Use `typing` module for complex types
   - Enables better IDE support and catches errors early

---

## 5. Performance & Reliability

### Caching Strategy

- **Global context**: 5 minutes (matches call frequency)
- **Fundamentals**: 1 day (fundamentals change slowly)
- **Cache keys**: Structured as `yahoo:{endpoint}:{params_hash}`

### Rate Limiting

- **Yahoo Finance**: 100 requests/min (conservative to avoid blocks)
- **Alpha Vantage**: 5 requests/min (free tier: 500/day)
- Use exponential backoff on rate limit errors

### Timeout Configuration

- **Yahoo Finance**: 10 seconds
- **Alpha Vantage**: 10 seconds
- **Redis**: 5 seconds

### Error Handling & Fallbacks

1. If Yahoo rate-limited → Use cached data if available
2. If Yahoo unavailable → Try Alpha Vantage (if configured)
3. If both fail → Return 503 Service Unavailable with retry-after header

---

## 6. Configuration Management

### Environment Variables (Required)

```bash
# Service
SERVICE_NAME=yahoo-services
SERVICE_PORT=8014
LOG_LEVEL=INFO

# Yahoo Finance
YAHOO_FINANCE_ENABLED=true
YAHOO_FINANCE_RATE_LIMIT=100
YAHOO_FINANCE_TIMEOUT=10

# Alpha Vantage (Optional)
ALPHA_VANTAGE_API_KEY=
ALPHA_VANTAGE_ENABLED=false
ALPHA_VANTAGE_RATE_LIMIT=5

# Global context symbols (NO SPACES)
GLOBAL_CONTEXT_SYMBOLS=^GSPC,^IXIC,^DJI,^VIX,GC=F,USDINR=X,CL=F

# Redis
REDIS_URL=redis://localhost:6379/3
REDIS_ENABLED=true

# Cache TTLs (seconds)
CACHE_TTL_GLOBAL_CONTEXT=300
CACHE_TTL_FUNDAMENTALS=86400
```

### Config Loading Pattern

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str
    service_port: int = 8014
    log_level: str = "INFO"
    
    yahoo_finance_enabled: bool = True
    yahoo_finance_rate_limit: int = 100
    # ... etc
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 7. Testing Guidelines (Only if Explicitly Requested)

**Default: NO TESTS unless user asks.**

If tests are requested:
- Use `pytest`
- Mock external APIs (Yahoo, Alpha Vantage)
- Test only critical paths (global context endpoint)
- NO demo tests, NO test for the sake of testing

---

## 8. Logging Standards

### What to Log

- **INFO**: Successful API calls, cache hits/misses, startup/shutdown
- **WARNING**: Rate limits approaching, fallback triggered, stale cache served
- **ERROR**: API failures, exceptions, invalid responses
- **DEBUG**: Request/response payloads (only in development)

### Log Format (JSON)

```json
{
  "timestamp": "2026-02-13T14:30:00+05:30",
  "level": "INFO",
  "service": "yahoo-services",
  "module": "global_context",
  "message": "Fetched global context",
  "context": {
    "symbols": ["^GSPC", "^IXIC", "^DJI", "^VIX"],
    "cache_hit": false,
    "duration_ms": 245
  }
}
```

### Log Files

- Location: `logs/yahoo-services.log`
- Rotation: 10MB per file, keep 5 files
- Create logs directory on startup if missing

---

## 9. Dependencies Management

### Required Packages (requirements.txt)

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
yfinance==0.2.18
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
httpx==0.26.0
```

**NO additional packages unless absolutely necessary.**

---

## 10. Development Workflow

### Step-by-Step Checklist

1. **Configuration first**
   - Create `config/settings.py` with all env vars
   - Create `.env` file from `env.example`

2. **Models next**
   - Create Pydantic request/response models
   - Validate against requirements doc

3. **Services layer (already exists)**
   - Review existing services
   - Add Alpha Vantage service if needed

4. **Routes layer**
   - Implement endpoints one by one
   - Start with `/health` (simplest)
   - Then `/api/v1/global-context` (primary use case)
   - Then `/api/v1/fundamentals/batch`
   - Finally Alpha Vantage fallback (optional)

5. **Logging & error handling**
   - Add structured logging to all routes
   - Add exception handlers to main.py

6. **Testing (manual)**
   - Start service: `uvicorn main:app --host 0.0.0.0 --port 8014 --reload`
   - Test each endpoint with curl
   - Verify caching works (call twice, check logs)
   - Verify rate limiting works

---

## 11. What NOT to Do (STRICTLY FORBIDDEN)

❌ **No demos or example endpoints** — Production code only
❌ **No redundant Kite data fetching** — Use Kite for NSE/BSE
❌ **No hardcoded values** — Use config for everything
❌ **No print statements** — Use structured logging
❌ **No generic exceptions** — Use custom exception classes
❌ **No untyped functions** — Type hints are mandatory
❌ **No tests unless requested** — Focus on functionality
❌ **No extra endpoints** — Only the 4 required endpoints
❌ **No over-engineering** — Keep it simple and efficient

---

## 12. Integration with seed-stocks-service

**This service is called by seed-stocks-service's `GlobalContextCollector`.**

### Expected behavior:
- `/api/v1/global-context` called every 5 minutes
- Response cached for 5 minutes
- If Yahoo fails, fallback to Alpha Vantage (if configured)
- If both fail, return 503 with retry-after header

### Response format MUST match:

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

**DO NOT change this response format without updating seed-stocks-service.**

---

## 13. Quick Reference: File Creation Order

1. `config/settings.py` — Centralized config with pydantic-settings
2. `utils/logger.py` — Structured logging setup
3. `utils/exceptions.py` — Custom exception classes
4. `api/models/responses.py` — Response Pydantic models
5. `api/models/requests.py` — Request Pydantic models
6. `api/routes/health.py` — Health check endpoint
7. `api/routes/global_context.py` — Primary endpoint (global context)
8. `api/routes/fundamentals.py` — Fundamentals batch endpoint
9. `services/alpha_vantage_service.py` — Alpha Vantage integration (optional)
10. `api/routes/alpha_vantage.py` — Alpha Vantage fallback endpoint (optional)
11. `main.py` — Wire everything together

---

## Summary: Target & Efficient Development

✅ **Focus on the 4 required endpoints only**
✅ **Use existing services layer (already built)**
✅ **No duplication of Kite data**
✅ **Aggressive caching to avoid rate limits**
✅ **Structured logging to files**
✅ **Pydantic models for all data**
✅ **Config-driven, no hardcoded values**
✅ **Production-grade error handling**
✅ **Clean separation: routes → services → external APIs**

❌ **No demos, no tests (unless requested), no redundant code**

---

**This rule file ensures efficient, targeted work aligned with the requirements document.**
