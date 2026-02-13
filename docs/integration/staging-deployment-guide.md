# Yahoo Services - Staging Deployment Guide

**Environment**: Staging  
**Port**: 8285  
**Purpose**: Pre-production testing before main deployment

---

## 🎯 Staging Environment Overview

| Configuration | Value |
|---------------|-------|
| **Port** | 8285 |
| **Environment** | staging |
| **Config File** | `envs/env.stage` |
| **Redis DB** | 4 (separate from dev/prod) |
| **Redis Host** | localhost (for local staging) |
| **Log Level** | INFO |

---

## 📋 Pre-Deployment Checklist

Before deploying to staging:

- [x] ✅ All endpoints tested on development (port 8085)
- [x] ✅ Code pushed to feature branch
- [x] ✅ Feature branch merged to `develop`
- [ ] ⏳ Redis running locally
- [ ] ⏳ Port 8285 available (no conflicts)
- [ ] ⏳ Docker installed and running

---

## 🚀 Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Step 1: Ensure You're on Develop Branch

```bash
# Switch to develop branch
git checkout develop

# Pull latest changes
git pull origin develop

# Verify you're on develop
git branch --show-current
```

#### Step 2: Kill Any Process on Port 8285

```bash
# Kill process if port is in use
lsof -ti:8285 | xargs kill -9

# Verify port is free
lsof -ti:8285
```

#### Step 3: Start Staging Environment with Docker

```bash
# Build and start staging service
docker-compose --profile stage up -d

# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f yahoo-services-stage
```

**Service will be available at**: `http://localhost:8285`

#### Step 4: Verify Service Health

```bash
# Health check
curl http://localhost:8285/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "yahoo-services",
#   "yahoo_finance_available": true,
#   "alpha_vantage_available": false,
#   "timestamp": "..."
# }
```

---

### Method 2: Direct Docker Build

```bash
# Build Docker image
docker build -t yahoo-services:staging .

# Run staging container
docker run -d \
  --name yahoo-services-stage \
  -p 8285:8285 \
  -e ENVIRONMENT=staging \
  -v $(pwd)/logs:/app/logs \
  --network host \
  yahoo-services:staging

# Check logs
docker logs -f yahoo-services-stage
```

---

### Method 3: Direct Python (Local Staging Test)

```bash
# Activate virtual environment
source venv/bin/activate

# Kill any process on port 8285
lsof -ti:8285 | xargs kill -9

# Set environment to staging
export ENVIRONMENT=staging

# Start service
python3 main.py

# Service will start on port 8285
```

---

## 🧪 Staging Testing Checklist

Once staging is running, test all endpoints:

### 1. Health Check

```bash
curl http://localhost:8285/health
```

**Expected**: `"status": "healthy"`

---

### 2. Global Context Endpoint (Primary)

```bash
curl http://localhost:8285/api/v1/global-context
```

**Expected Response**:
```json
{
  "sp500": {"price": 6832.76, "change_percent": -1.57},
  "nasdaq": {"price": 22597.15, "change_percent": -2.03},
  "dow_jones": {"price": 49451.98, "change_percent": -1.34},
  "vix": {"value": 20.49},
  "gold": {"price": 4998.8, "change_percent": 1.02},
  "usd_inr": {"rate": 90.631, "change_percent": 0.12},
  "crude_oil": {"price": 63.0, "change_percent": 0.25},
  "timestamp": "2026-02-13T..."
}
```

**Verify**:
- ✅ All 7 symbols present
- ✅ `usd_inr` uses `"rate"` field (not `"price"`)
- ✅ Response time < 5 seconds

---

### 3. Fundamentals Batch Endpoint

```bash
curl -X POST http://localhost:8285/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "SBIN.NS", "TCS.NS"]}'
```

**Expected**: Fundamentals for all requested symbols

---

### 4. Caching Test

```bash
# First call (fetches from Yahoo)
time curl -s http://localhost:8285/api/v1/global-context > /dev/null

# Second call (should be faster, from cache)
time curl -s http://localhost:8285/api/v1/global-context > /dev/null
```

**Expected**: Second call significantly faster (< 500ms)

---

### 5. API Documentation

Open in browser: `http://localhost:8285/docs`

**Verify**:
- ✅ Swagger UI loads
- ✅ All 4 endpoints listed
- ✅ Can test endpoints interactively

---

## 🔍 Integration Testing with seed-stocks-service

### Update seed-stocks-service Configuration

In your `seed-stocks-service` configuration, update the Yahoo Services URL:

```python
# For staging testing
YAHOO_SERVICES_URL = "http://localhost:8285"
```

### Test GlobalContextCollector Integration

```python
import httpx

async def test_yahoo_services_integration():
    """Test Yahoo Services staging endpoint."""
    
    async with httpx.AsyncClient() as client:
        # Test global context
        response = await client.get("http://localhost:8285/api/v1/global-context")
        
        if response.status_code == 200:
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
            
            # Verify USD/INR has "rate" field (not "price")
            assert "rate" in data["usd_inr"]
            
            print("✅ Integration test passed!")
            return data
        else:
            print(f"❌ Integration test failed: {response.status_code}")
            return None
```

---

## 📊 Monitoring Staging

### View Logs

```bash
# Docker logs
docker-compose logs -f yahoo-services-stage

# Or view log file directly
tail -f logs/yahoo-services.log | jq .
```

### Check Service Status

```bash
# Service info
curl http://localhost:8285/

# Detailed health
curl http://localhost:8285/health
```

### Monitor Redis Cache

```bash
# Connect to Redis
redis-cli

# Select staging database (DB 4)
SELECT 4

# List all keys
KEYS yahoo:*

# Check cache hit rate
INFO stats

# View specific cached item
GET yahoo:quote:^GSPC
```

---

## 🔧 Troubleshooting

### Issue: Port Already in Use

```bash
# Find and kill process
lsof -ti:8285 | xargs kill -9

# Restart service
docker-compose --profile stage restart yahoo-services-stage
```

---

### Issue: Redis Connection Error

```bash
# Check Redis is running
redis-cli ping

# Start Redis if not running
brew services start redis   # macOS
# OR
sudo systemctl start redis  # Linux

# Check Redis logs
redis-cli INFO
```

---

### Issue: Service Not Starting

```bash
# Check Docker logs
docker-compose logs yahoo-services-stage

# Check if image built correctly
docker images | grep yahoo-services

# Rebuild if needed
docker-compose --profile stage down
docker-compose --profile stage build --no-cache
docker-compose --profile stage up -d
```

---

### Issue: Slow Response Times

```bash
# Check if Redis cache is working
curl http://localhost:8285/api/v1/global-context
# Should be fast on subsequent calls

# Check Redis connection
redis-cli -n 4 DBSIZE

# Clear cache if needed
redis-cli -n 4 FLUSHDB
```

---

## 🎯 Staging Validation Checklist

Before promoting to production:

- [ ] All endpoints respond correctly
- [ ] Response format matches requirements exactly
- [ ] `usd_inr` field uses `"rate"` (not `"price"`)
- [ ] Caching is working (5 min for global, 1 day for fundamentals)
- [ ] Integration with seed-stocks-service tested
- [ ] Performance is acceptable (global context < 5s, cached < 500ms)
- [ ] Error handling works correctly
- [ ] API documentation accessible
- [ ] Logs are structured and readable
- [ ] No errors in service logs

---

## 🚀 Promoting to Production

Once staging validation is complete:

### Step 1: Merge develop to main

```bash
# Switch to main branch
git checkout main

# Merge develop
git merge develop

# Push to remote
git push origin main
```

### Step 2: Deploy Production

```bash
# Stop staging
docker-compose --profile stage down

# Start production
docker-compose --profile prod up -d

# Verify production
curl http://localhost:8185/health
```

**Production will run on port 8185**

---

## 📝 Environment Comparison

| Aspect | Development | Staging | Production |
|--------|------------|---------|------------|
| **Port** | 8085 | 8285 | 8185 |
| **Branch** | feature/* | develop | main |
| **Redis DB** | 3 | 4 | 3 |
| **Redis Host** | localhost | localhost | redis |
| **Log Level** | INFO | INFO | WARNING |
| **Auto Reload** | Yes | No | No |
| **Volume Mount** | Full code | Logs only | Logs only |

---

## 🔗 Quick Commands Reference

```bash
# Start staging
docker-compose --profile stage up -d

# Stop staging
docker-compose --profile stage down

# Restart staging
docker-compose --profile stage restart

# View logs
docker-compose logs -f yahoo-services-stage

# Check status
docker-compose ps

# Health check
curl http://localhost:8285/health

# Test global context
curl http://localhost:8285/api/v1/global-context

# Test fundamentals
curl -X POST http://localhost:8285/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS"]}'

# View API docs
open http://localhost:8285/docs
```

---

## 📞 Support

If you encounter issues during staging deployment:

1. Check service logs: `docker-compose logs yahoo-services-stage`
2. Verify Redis: `redis-cli -n 4 ping`
3. Check port availability: `lsof -ti:8285`
4. Review configuration: `cat envs/env.stage`

---

**Last Updated**: 2026-02-13  
**Status**: Ready for Staging Deployment  
**Next**: Test in staging → Validate → Promote to production
