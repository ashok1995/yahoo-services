# Production VM Deployment Guide

Deploy Yahoo Services to production VM (203.57.85.72) on port 8185.

---

## 🚀 Quick Deploy

```bash
# From your local machine or on the VM
./deploy-vm-prod.sh
```

**The script automatically detects the environment and deploys accordingly.**

---

## 📋 Prerequisites

### On Your Local Machine (for remote deployment)

```bash
# Install sshpass (for SSH automation)
brew install sshpass  # macOS
# or
apt install sshpass   # Linux
```

### On Production VM

- ✅ Docker installed and running
- ✅ Git installed
- ✅ Port 8185 available
- ✅ Internet access (for pulling images)

---

## 🎯 Deployment Methods

### Method 1: Deploy from Local Machine (Recommended)

```bash
# Clone the repository (if not already)
git clone https://github.com/ashok1995/yahoo-services.git
cd yahoo-services

# Make sure you're on main branch
git checkout main
git pull origin main

# Run deployment script
./deploy-vm-prod.sh
```

**What happens:**
1. Script connects to VM via SSH using sshpass
2. Clones/updates repository on VM (`/opt/yahoo-services`)
3. Pulls latest code from main branch
4. Builds Docker images with Poetry
5. Starts containers (yahoo-services-prod + redis-prod)
6. Verifies health endpoint
7. Displays deployment summary

---

### Method 1b: Build Locally, Transfer Image (when VM build is too slow)

If the VM is slow (e.g. 20+ min on the Poetry install step), build the image on your Mac and transfer it. The VM only loads the image and runs it—no build on the VM.

```bash
cd yahoo-services
git checkout main
git pull origin main

# Build on your machine (fast), then transfer and run on VM
./deploy-vm-prod.sh --build-local
```

**What happens:**
1. Builds `yahoo-services:production` locally for **linux/amd64** (VM architecture)
2. Saves image to a tar file and SCPs it to the VM
3. On VM: loads the image, pulls latest repo (for compose file), starts containers
4. No Docker build on the VM—deploy finishes in a couple of minutes

Use this when the default deploy (build on VM) is too slow.

---

### Method 2: Deploy Directly on VM

```bash
# SSH into the VM
ssh root@203.57.85.72

# Clone repository (first time only)
git clone https://github.com/ashok1995/yahoo-services.git /opt/yahoo-services
cd /opt/yahoo-services

# Checkout main branch
git checkout main

# Run deployment script
./deploy-vm-prod.sh
```

---

## 📦 What Gets Deployed

### Docker Containers

| Container | Port | Purpose |
|-----------|------|---------|
| `yahoo-services-prod` | 8185 | Main FastAPI service |
| `yahoo-redis-prod` | 6379 (internal) | Redis cache |

### Network Configuration

- **Network**: `yahoo-network-prod` (isolated bridge network)
- **External Port**: 8185 (mapped to host)
- **Redis**: Internal only (no external exposure)

### Volumes

- **redis-data-prod**: Persistent Redis data
- **logs**: Application logs (mounted to host)

---

## 🔍 Verification

### 1. Check Service Health

```bash
# From VM or local machine
curl http://203.57.85.72:8185/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "yahoo-services",
  "yahoo_finance_available": true,
  "alpha_vantage_available": false,
  "timestamp": "2026-02-14T..."
}
```

---

### 2. Test Global Context Endpoint

```bash
curl http://203.57.85.72:8185/api/v1/global-context
```

**Expected Response:**
```json
{
  "sp500": {"price": 6832.76, "change_percent": -1.57},
  "nasdaq": {"price": 22597.15, "change_percent": -2.03},
  "dow_jones": {"price": 49451.98, "change_percent": -1.34},
  "vix": {"value": 20.78},
  "gold": {"price": 4995.1, "change_percent": 0.94},
  "usd_inr": {"rate": 90.64, "change_percent": 0.13},
  "crude_oil": {"price": 62.93, "change_percent": 0.14},
  "timestamp": "2026-02-14T..."
}
```

---

### 3. Test Fundamentals Endpoint

```bash
curl -X POST http://203.57.85.72:8185/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "TCS.NS"]}'
```

---

### 4. Check Docker Containers

```bash
# SSH into VM
ssh root@203.57.85.72

# Check running containers
docker ps --filter "name=yahoo"

# Expected output:
# yahoo-services-prod   Up X minutes (healthy)
# yahoo-redis-prod      Up X minutes
```

---

### 5. Check Logs

```bash
# SSH into VM
ssh root@203.57.85.72
cd /opt/yahoo-services

# View live logs
docker compose -f docker-compose.prod.yml logs -f

# View last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

---

## 🔧 Management Commands

All commands should be run from `/opt/yahoo-services` directory on the VM.

### View Status

```bash
docker compose -f docker-compose.prod.yml ps
```

---

### View Logs

```bash
# Live logs (follow)
docker compose -f docker-compose.prod.yml logs -f

# Last N lines
docker compose -f docker-compose.prod.yml logs --tail=50

# Specific service
docker compose -f docker-compose.prod.yml logs -f yahoo-services-prod
```

---

### Restart Service

```bash
# Restart both containers
docker compose -f docker-compose.prod.yml restart

# Restart only the app (not Redis)
docker compose -f docker-compose.prod.yml restart yahoo-services-prod
```

---

### Stop Service

```bash
docker compose -f docker-compose.prod.yml stop
```

---

### Start Service

```bash
docker compose -f docker-compose.prod.yml start
```

---

### Full Rebuild

```bash
# Stop and remove containers
docker compose -f docker-compose.prod.yml down

# Rebuild and start
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

---

### View Resource Usage

```bash
docker stats yahoo-services-prod yahoo-redis-prod
```

---

## 🔄 Update Deployment

### Update to Latest Code

```bash
# Option 1: Run deployment script again
./deploy-vm-prod.sh

# Option 2: Manual update
ssh root@203.57.85.72
cd /opt/yahoo-services
git pull origin main
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 🐛 Troubleshooting

### Service Not Starting

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs --tail=100

# Check if port is available
lsof -i:8185

# Restart containers
docker compose -f docker-compose.prod.yml restart
```

---

### Health Check Failing

```bash
# Check service logs
docker compose -f docker-compose.prod.yml logs yahoo-services-prod

# Check if Redis is running
docker compose -f docker-compose.prod.yml ps redis-prod

# Test Redis connection
docker exec -it yahoo-redis-prod redis-cli ping
# Should return: PONG
```

---

### Redis Issues

```bash
# Check Redis logs
docker compose -f docker-compose.prod.yml logs redis-prod

# Connect to Redis
docker exec -it yahoo-redis-prod redis-cli

# Inside Redis CLI:
# Check memory
INFO memory

# Check cached keys
KEYS *

# Clear cache (if needed)
FLUSHDB
```

---

### Port Already in Use

```bash
# Find process using port 8185
lsof -i:8185

# Kill process
kill -9 <PID>

# Or stop all yahoo services
docker compose -f docker-compose.prod.yml down

# Restart
docker compose -f docker-compose.prod.yml up -d
```

---

### Container Crashes

```bash
# View container logs
docker compose -f docker-compose.prod.yml logs yahoo-services-prod

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart specific container
docker compose -f docker-compose.prod.yml restart yahoo-services-prod
```

---

## 📊 Monitoring

### Health Endpoint

Set up monitoring to check health endpoint every minute:

```bash
curl -f http://203.57.85.72:8185/health || alert
```

---

### Log Monitoring

```bash
# Watch for errors in logs
docker compose -f docker-compose.prod.yml logs -f | grep -i error
```

---

### Resource Monitoring

```bash
# Check CPU and memory usage
docker stats yahoo-services-prod yahoo-redis-prod
```

---

## 🔒 Security Notes

1. **Firewall**: Ensure port 8185 is open in VM firewall
2. **Redis**: Not exposed externally (internal network only)
3. **Logs**: Review logs regularly for suspicious activity
4. **Updates**: Keep Docker images updated

---

## 📝 Configuration

### Production Environment Variables

Located in `envs/env.prod`:

```bash
SERVICE_PORT=8185
ENVIRONMENT=production
LOG_LEVEL=WARNING
REDIS_HOST=redis-prod
REDIS_DB=0
CACHE_TTL_GLOBAL_CONTEXT=300    # 5 minutes
CACHE_TTL_FUNDAMENTALS=86400    # 1 day
```

---

## 🎯 Integration

### Service URL

```
Production: http://203.57.85.72:8185
```

### Endpoints

```
Health:         GET  /health
Global Context: GET  /api/v1/global-context
Fundamentals:   POST /api/v1/fundamentals/batch
API Docs:       GET  /docs
```

---

## 📞 Support

### Quick Diagnostics

```bash
# 1. Check service health
curl http://203.57.85.72:8185/health

# 2. Check containers
docker ps --filter "name=yahoo"

# 3. Check logs
cd /opt/yahoo-services
docker compose -f docker-compose.prod.yml logs --tail=50

# 4. Check disk space
df -h

# 5. Check memory
free -h
```

---

## ✅ Deployment Checklist

Before deploying:
- [ ] Code merged to main branch
- [ ] All tests passing on staging
- [ ] Docker available on VM
- [ ] Port 8185 available
- [ ] Sufficient disk space (> 2GB free)

After deploying:
- [ ] Health endpoint returns "healthy"
- [ ] Global context endpoint working
- [ ] Fundamentals endpoint working
- [ ] Logs look clean
- [ ] Redis connected
- [ ] Containers auto-restart enabled

---

## 📚 Related Documentation

- [Deployment Scripts Guide](./DEPLOYMENT-SCRIPTS.md)
- [Poetry Guide](./POETRY-GUIDE.md)
- [Endpoint Verification](./ENDPOINT-VERIFICATION.md)
- [Integration Guide](./docs/integration/yahoo-service-integration.md)

---

**Deployment Script**: `./deploy-vm-prod.sh`  
**Production URL**: `http://203.57.85.72:8185`  
**VM**: `203.57.85.72` (root)  
**Location**: `/opt/yahoo-services`

---

Last Updated: 2026-02-14
