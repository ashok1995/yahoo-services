# External APIs Used

This document lists all external APIs used by yahoo-services.

---

## 1. Yahoo Finance API

**Base URL**: `https://query1.finance.yahoo.com/`

**Purpose**: Fetch global indices (S&P 500, NASDAQ, VIX), commodities (Gold, Crude), forex (USD/INR), and fundamentals.

**Endpoints Used**:
- `/v8/finance/chart/{symbol}` - Get quote data for symbols
- `/v10/finance/quoteSummary/{symbol}` - Get detailed quote and fundamentals

**Authentication**: None (public API)

**Rate Limits**: ~100-200 requests/minute (conservative limit: 100 req/min to avoid blocks)

**Data Models**:

### Request (via yfinance library):
```python
import yfinance as yf
ticker = yf.Ticker(symbol)
info = ticker.info  # Returns dict with quote and fundamental data
```

### Response Fields Used:
```python
{
    "regularMarketPrice": float,           # Current price
    "regularMarketChangePercent": float,   # Percentage change
    "marketCap": float,                    # Market capitalization
    "trailingPE": float,                   # P/E ratio
    "priceToBook": float,                  # P/B ratio
    "returnOnEquity": float,               # ROE
    "debtToEquity": float,                 # Debt-to-equity
    "profitMargin": float,                 # Profit margin
    "operatingMargin": float               # Operating margin
}
```

**Pydantic Models**:
- Request: N/A (uses symbol strings)
- Response: `MarketData`, `VIXData`, `FundamentalsData` (see `api/models/responses.py`)

**Test Coverage**:
- ✅ Success: Fetch valid symbols (^GSPC, RELIANCE.NS)
- ✅ Failure: Rate limit handling, invalid symbols
- ✅ Edge: Partial data, missing fields

**Integration Points**:
- `/api/v1/global-context` - Fetches 7 symbols (S&P, NASDAQ, Dow, VIX, Gold, USD/INR, Crude)
- `/api/v1/fundamentals/batch` - Fetches fundamentals for multiple NSE stocks

**Pre-Integration Check**:
```bash
# Verify Yahoo Finance is reachable
curl -s 'https://query1.finance.yahoo.com/v8/finance/chart/^GSPC'
```

---

## 2. Alpha Vantage API (Optional)

**Base URL**: `https://www.alphavantage.co/query`

**Purpose**: Fallback for global context when Yahoo Finance is rate-limited.

**Endpoints Used**:
- `/query?function=GLOBAL_QUOTE&symbol={symbol}` - Get quote data

**Authentication**: API key required (`alpha_vantage_api_key`)

**Rate Limits**: Free tier - 5 requests/minute, 500 requests/day

**Status**: Not yet implemented (returns 501 Not Implemented)

**Configuration**:
```bash
ALPHA_VANTAGE_API_KEY=your_api_key_here
ALPHA_VANTAGE_ENABLED=true
ALPHA_VANTAGE_RATE_LIMIT=5
```

**Pre-Integration Check**:
```bash
# Verify Alpha Vantage is reachable (requires API key)
curl 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY&apikey=YOUR_API_KEY'
```

---

## 3. Redis Cache

**Connection**: `redis://localhost:6379/3`

**Purpose**: Cache Yahoo Finance responses to avoid rate limits.

**Cache Keys**:
- `yahoo:quote:{symbol}` - Quote data (TTL: 5 minutes)
- `yahoo:fundamental:{symbol}` - Fundamental data (TTL: 1 day)
- `yahoo:global_context:batch` - Global context batch (TTL: 5 minutes)

**Configuration**:
```bash
REDIS_URL=redis://localhost:6379/3
REDIS_ENABLED=true
CACHE_TTL_GLOBAL_CONTEXT=300
CACHE_TTL_FUNDAMENTALS=86400
```

**Pre-Integration Check**:
```bash
# Verify Redis is reachable
redis-cli -u redis://localhost:6379/3 ping
```

---

## Summary

| API | Purpose | Rate Limit | Auth | Status |
|-----|---------|------------|------|--------|
| Yahoo Finance | Primary data source | 100 req/min | None | ✅ Implemented |
| Alpha Vantage | Fallback | 5 req/min | API key | ⏳ Planned |
| Redis | Caching | N/A | None | ✅ Implemented |

---

## Error Handling

All external API calls follow this pattern:

1. **Rate limit check** - Ensure we're within limits
2. **Cache check** - Return cached data if available and fresh
3. **API call** - Make request with timeout (10s)
4. **Cache store** - Store successful response
5. **Error handling**:
   - Rate limit exceeded → Return cached data or 429
   - API unavailable → Try fallback (Alpha Vantage) or 503
   - Timeout → Retry with exponential backoff
   - Invalid data → Log error, return partial data or 500

---

Last updated: 2026-02-13
