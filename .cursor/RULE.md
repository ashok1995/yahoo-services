# Yahoo-Services — Implementation Rules

**Core Principle**: Zero Redundancy, Maximum Efficiency, Production-Grade Only

Port: **8014** | Global/index market context ONLY (data Kite cannot provide)

---

## 1. Scope (Strict)

### ✅ ALLOWED — This service provides:
- Global indices: S&P 500 (`^GSPC`), NASDAQ (`^IXIC`), Dow Jones (`^DJI`), VIX (`^VIX`)
- Commodities: Gold (`GC=F`), Crude Oil (`CL=F`)
- Forex: USD/INR (`USDINR=X`)
- Multi-timeframe trend analysis (5d / 1mo / 3mo) for ALL the above
- Fundamentals (P/E, P/B, ROE, margins) for NSE stocks — batch only, weekly

### ❌ FORBIDDEN — Kite API handles these:
- NSE/BSE stock quotes / live prices
- NSE/BSE candles / OHLC / historical data
- Any per-stock Indian market data
- **Never duplicate what Kite provides. This service is exclusively for global context.**

---

## 2. Endpoints (Exactly 4)

1. `GET /api/v1/global-context` — PRIMARY (90%), quotes + ML-ready trends
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
│   ├── routes/                   # Thin (call services only)
│   └── models/                   # Pydantic request/response
├── services/
│   ├── yahoo_finance_service.py  # Yahoo API client (quotes + candles)
│   ├── trend_analyzer.py         # Pure computation: candles → ML-ready metrics
│   ├── cache_service.py          # Redis caching
│   └── rate_limiter.py           # Rate limiting
├── config/settings.py            # pydantic-settings
├── utils/
│   ├── logger.py
│   └── exceptions.py
├── envs/env.dev                  # NOT root .env
├── tests/
├── logs/                         # Gitignored
└── docs/                         # See §8
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
CACHE_TTL_TRENDS=3600
```

### Yahoo Finance Rate Limits (unofficial, community-observed)
- 60 requests/minute, 360/hour, 8,000/day
- `ticker.info` is ~6.5x heavier than `ticker.history`
- Current budget: 91 calls/hour (84 quote + 7 trend) = 25% of hourly limit
- **Never exceed 50% of hourly limit**
- Trend uses `ticker.history` (light) with 1hr cache — adds only 7 calls/hour

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

**Branch & deploy (mandatory):** See **BRANCH-WORKFLOW.md**. Summary:
- Work on **feature/xxx** or **bugfix/xxx** (from `develop`). Never commit on `main` or `develop`.
- Merge to **develop** → deploy **staging** (local port 8285): `./deploy-stage.sh`
- When staging OK: merge **develop** → **main** → deploy VM **only from main**: `git checkout main && ./deploy-vm-prod.sh`

1. **Config**: `config/settings.py` + `envs/env.dev`
2. **Models**: Pydantic request/response
3. **Services**: Review existing, add Alpha Vantage if needed
4. **Routes**: `/health` → `/api/v1/global-context` → `/api/v1/fundamentals/batch` → Alpha Vantage
5. **Wire**: Add logging, exception handlers to `main.py`
6. **Test**: Start server, curl endpoints, verify caching

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
❌ Indian stock quotes/candles/prices (use Kite for all NSE/BSE data)
❌ Exceeding 50% of Yahoo's hourly rate limit (360/hr)
❌ Demos, tests (unless requested), over-engineering

---

## 11. Integration Response Format

Called by seed-stocks-service every 5 min. `trend` is optional (null if cache cold or fetch failed):
```json
{
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
      "medium_term": {"...same fields, 22 candles..."},
      "long_term": {"...same fields, ~61 candles..."}
    }
  },
  "vix": {"value": 13.45, "trend": {"..."}},
  "timestamp": "2026-02-12T14:30:00+05:30"
}
```

**Trend regime bins**: `strong_bullish | bullish | weak_bullish | consolidating | weak_bearish | bearish | strong_bearish`
**Volatility regime bins**: `low | normal | high | extreme`

---

## 12. Trend Analysis Architecture

- **`trend_analyzer.py`**: Pure computation, no API calls. Input: OHLCV DataFrame. Output: metrics dict.
- **`yahoo_finance_service.get_trend_data()`**: Fetches 3mo daily candles → runs analyzer → caches 1hr.
- **`global_context.py`**: Fetches quotes (phase 1) then trends (phase 2) concurrently. Merges into response.
- **Graceful degradation**: Trend failure → `trend: null` in response. Quotes always returned.
- **One fetch, three horizons**: Single `ticker.history(period="3mo")` call sliced for 5d / 22d / full.

---

## Summary

✅ 4 endpoints, global/index context only, aggressive caching, production-grade
✅ Max 300 LOC/file, 30 LOC/function, DRY, type hints
✅ Config-driven (`envs/env.dev`), structured logging, Pydantic everywhere
✅ Test before commit, document APIs, keep docs synced
✅ Git: feature branches → develop → main
✅ Rate-limit safe: 25% of Yahoo's hourly budget

❌ No Indian stock data (use Kite), demos, redundancy, hardcoded values, working on main
