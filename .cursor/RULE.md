# Yahoo-Services — Implementation Rules

**Core Principle**: Zero Redundancy, Maximum Efficiency, Production-Grade Only

Port: **8014** | Only data Kite cannot provide (US indices, commodities, forex, fundamentals)

---

## 1. Scope (Strict)

### ✅ ALLOWED
- Global indices (S&P, NASDAQ, VIX), Commodities (Gold, Crude), Forex (USD/INR), Fundamentals

### ❌ FORBIDDEN
- NSE/BSE quotes/candles/OHLC → Use Kite

---

## 2. Endpoints (Exactly 4)

1. `GET /api/v1/global-context` — PRIMARY (90% usage), cache: 5 min
2. `POST /api/v1/fundamentals/batch` — Weekly, cache: 1 day
3. `GET /api/v1/alpha-vantage/global-context` — Fallback (optional)
4. `GET /health` — Health check

**No new endpoints without approval.**

---

## 3. Code Architecture

### File Structure
```
yahoo-services/
├── main.py
├── api/
│   ├── routes/          # Thin (call services only)
│   └── models/          # Pydantic request/response
├── services/            # Business logic (stateless)
├── config/settings.py   # pydantic-settings
├── utils/
│   ├── logger.py
│   └── exceptions.py
├── envs/env.dev         # NOT root .env
├── tests/
├── logs/                # Gitignored
└── docs/                # See §8
```

### Mandatory Patterns
1. **Config**: pydantic-settings, load from `envs/env.dev`, NO hardcoded values
2. **Models**: Pydantic for all endpoints (request + response)
3. **Logging**: JSON to `logs/yahoo-services.log` (10MB rotation, keep 5)
4. **Errors**: Custom exceptions, standardized responses
5. **DI**: FastAPI dependency injection

---

## 4. Code Quality

**Size Limits**
- **Max 300 lines per file**
- **Max 30 lines per function**

**Standards**
- **DRY**: Extract logic used 2+ times
- **Type hints**: Mandatory
- **Single responsibility**: Routes → services → external APIs
- **Scan before writing**: Look for similar logic, refactor
- **Test before commit**: Run tests, fix breaks before push

**Error Handling**
1. Yahoo rate-limited → cached data
2. Yahoo down → Alpha Vantage (if configured)
3. Both fail → 503 with retry-after

---

## 5. Configuration

Location: `envs/env.dev` (NOT root `.env`)

```bash
SERVICE_PORT=8014
LOG_LEVEL=INFO
YAHOO_FINANCE_RATE_LIMIT=100
YAHOO_FINANCE_TIMEOUT=10
ALPHA_VANTAGE_API_KEY=
GLOBAL_CONTEXT_SYMBOLS=^GSPC,^IXIC,^DJI,^VIX,GC=F,USDINR=X,CL=F
REDIS_URL=redis://localhost:6379/3
CACHE_TTL_GLOBAL_CONTEXT=300
CACHE_TTL_FUNDAMENTALS=86400
```

---

## 6. External API Integration

**Before Wiring**: Verify service is reachable
```bash
curl -s https://query1.finance.yahoo.com/v8/finance/chart/^GSPC
```

**Document in `docs/api/apis-used.md`**:
- API name, base URL, endpoints
- Pydantic models (req/res)
- Purpose, auth, rate limits
- Test coverage (success/failure/edge)

**No raw HTTP calls** — use client wrapper with DI

---

## 7. Logging

Format: `{timestamp, level, service, module, message, context}`
- INFO: API calls, cache hits, startup
- WARNING: Rate limits, fallback triggered
- ERROR: Failures, exceptions
- DEBUG: Payloads (dev only)

NO `print()` statements

---

## 8. Documentation

**Current State Only** — remove process/status/history docs

**Structure** (no `.md` at `/docs/` root except `README.md`)
```
docs/
├── README.md           # Navigation only
├── api/
│   ├── api-reference.md
│   └── apis-used.md    # All external APIs
├── architecture/
├── integration/
└── deployment/
```

**Keep in Sync**: Code changes → update docs → update this master rule

---

## 9. Development Workflow

1. **Config**: `config/settings.py` + `envs/env.dev`
2. **Models**: Pydantic request/response
3. **Services**: Review existing, add Alpha Vantage if needed
4. **Routes**: `/health` → `/api/v1/global-context` → `/api/v1/fundamentals/batch` → Alpha Vantage
5. **Wire**: Add logging, exception handlers to `main.py`
6. **Test**: Start server, curl endpoints, verify caching

```bash
# Kill port, start service
lsof -ti:8014 | xargs kill -9
uvicorn main:app --host 0.0.0.0 --port 8014 --reload

# Test
curl http://localhost:8014/health
curl http://localhost:8014/api/v1/global-context
```

---

## 10. Strictly Forbidden

❌ Working/committing on `main`/`develop` directly
❌ Deploying production from non-`main` branch
❌ Files >300 lines, functions >30 lines
❌ Endpoints without Pydantic models
❌ API calls without models + `docs/api/apis-used.md` entry
❌ Committing without testing first
❌ Duplicate logic, hardcoded values, print statements
❌ New endpoints without approval
❌ `.md` outside repo root or `docs/` subfolders
❌ Env files outside `/envs/` or named other than `env.dev`
❌ Redundant Kite data (use Kite for NSE/BSE)
❌ Demos, tests (unless requested), over-engineering

---

## 11. Integration Response Format (DO NOT CHANGE)

Called by seed-stocks-service every 5 min:
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

---

## Summary

✅ 4 endpoints, existing services, aggressive caching, production-grade
✅ Max 300 LOC/file, 30 LOC/function, DRY, type hints
✅ Config-driven (`envs/env.dev`), structured logging, Pydantic everywhere
✅ Test before commit, document APIs, keep docs synced
✅ Git: feature branches → develop → main

❌ No demos, redundancy, hardcoded values, working on main
