# Deployment Scripts

Three automated deployment scripts for each environment.

---

## 📜 Available Scripts

| Script | Environment | Port | Method |
|--------|-------------|------|--------|
| `deploy-dev.sh` | Development | 8085 | Direct Python |
| `deploy-stage.sh` | Staging | 8285 | Docker Compose |
| `deploy-prod.sh` | Production | 8185 | Docker Compose |

---

## 🚀 Usage

### Development Deployment (Port 8085)

```bash
./deploy-dev.sh
```

**What it does:**
1. Checks Redis is running
2. Kills any process on port 8085
3. Verifies environment file (`envs/env.dev`)
4. Activates virtual environment
5. Starts service with Python
6. Waits for service to be ready
7. Verifies health endpoint
8. Displays service info

**Use when:** Local development and testing

---

### Staging Deployment (Port 8285)

```bash
# First, merge to develop
git checkout develop
git merge feature/implement-api-routes
git push origin develop

# Then deploy staging
./deploy-stage.sh
```

**What it does:**
1. Verifies you're on `develop` branch
2. Checks Docker is running
3. Checks Redis is running
4. Kills any process on port 8285
5. Verifies environment file (`envs/env.stage`)
6. Stops existing staging containers
7. Builds Docker image
8. Starts staging service with Docker Compose
9. Waits for service to be ready
10. Verifies health endpoint
11. Displays service info

**Use when:** Pre-production testing before deploying to production

---

### Production Deployment (Port 8185)

```bash
# First, merge develop to main
git checkout main
git merge develop
git push origin main

# Then deploy production
./deploy-prod.sh
```

**What it does:**
1. **⚠️ Shows 5-second warning** (can cancel with CTRL+C)
2. **Enforces main branch** (production MUST deploy from main)
3. Verifies working directory is clean
4. Pulls latest changes from main
5. Checks Docker is running
6. Kills any process on port 8185
7. Verifies environment file (`envs/env.prod`)
8. Stops existing production containers
9. Builds Docker image
10. Starts production service with Docker Compose
11. Waits for service to be ready
12. Verifies health endpoint
13. Displays service info

**Use when:** Deploying to production (ONLY from main branch)

---

## 🔒 Safety Features

### Development Script
- ✅ Checks Redis availability
- ✅ Kills conflicting processes by port
- ✅ Creates logs directory
- ✅ Verifies service health before completing

### Staging Script
- ✅ Enforces `develop` branch
- ✅ Checks Docker is running
- ✅ Kills conflicting processes by port
- ✅ Clean build (no cache)
- ✅ Verifies service health before completing

### Production Script
- ✅ **5-second warning** before deployment
- ✅ **Enforces `main` branch only**
- ✅ Verifies working directory is clean
- ✅ Pulls latest code from remote
- ✅ Clean build (no cache)
- ✅ Verifies service health before completing

---

## 📋 Prerequisites

### For All Environments
- Git repository
- Redis running locally
- `jq` installed (for JSON parsing)

### For Development Only
- Python 3.13
- Virtual environment (`venv/`)

### For Staging & Production
- Docker Desktop running
- Docker Compose installed

---

## 🧪 Testing After Deployment

Each script displays test commands at the end. Example:

```bash
# Health Check
curl http://localhost:8085/health | jq .

# Global Context
curl http://localhost:8085/api/v1/global-context | jq .

# Fundamentals
curl -X POST http://localhost:8085/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS"]}' | jq .

# API Documentation
open http://localhost:8085/docs
```

---

## 🔧 Troubleshooting

### Script Fails: Redis Not Running

```bash
# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should output: PONG

# Re-run deployment script
./deploy-dev.sh
```

---

### Script Fails: Docker Not Running

```bash
# Start Docker Desktop
open -a Docker

# Wait for Docker to be ready
docker info

# Re-run deployment script
./deploy-stage.sh
```

---

### Script Fails: Port Already in Use

```bash
# Kill process manually
lsof -ti:8085 | xargs kill -9  # Dev
lsof -ti:8285 | xargs kill -9  # Stage
lsof -ti:8185 | xargs kill -9  # Prod

# Re-run deployment script
```

---

### Script Fails: Permission Denied

```bash
# Make scripts executable
chmod +x deploy-dev.sh deploy-stage.sh deploy-prod.sh

# Re-run deployment script
```

---

### Service Unhealthy After Deployment

```bash
# View logs
tail -f logs/yahoo-services.log  # Dev
docker-compose logs -f yahoo-services-stage  # Stage
docker-compose logs -f yahoo-services-prod  # Prod

# Check Redis connection
redis-cli ping

# Restart service
./deploy-dev.sh  # Dev
docker-compose --profile stage restart  # Stage
docker-compose --profile prod restart  # Prod
```

---

## 🔄 Workflow Examples

### Example 1: Deploy Development

```bash
# From any branch
./deploy-dev.sh

# Service starts on port 8085
# Test: curl http://localhost:8085/health
```

---

### Example 2: Deploy Staging

```bash
# Ensure you're on develop branch
git checkout develop

# Pull latest changes
git pull origin develop

# Deploy
./deploy-stage.sh

# Service starts on port 8285
# Test: curl http://localhost:8285/health
```

---

### Example 3: Deploy Production

```bash
# Merge develop to main first
git checkout main
git merge develop
git push origin main

# Deploy production
./deploy-prod.sh

# Service starts on port 8185
# Test: curl http://localhost:8185/health
```

---

## 📊 Script Output

Each script provides:
- ✅ Step-by-step progress
- ✅ Color-coded status messages
- ✅ Service information (port, URL, PID/container)
- ✅ Quick test commands
- ✅ Log viewing commands
- ✅ Stop/restart commands

---

## 🎯 Quick Reference

```bash
# Deploy development (port 8085)
./deploy-dev.sh

# Deploy staging (port 8285) - requires develop branch
./deploy-stage.sh

# Deploy production (port 8185) - requires main branch
./deploy-prod.sh

# Stop services
lsof -ti:8085 | xargs kill -9  # Dev
docker-compose --profile stage down  # Stage
docker-compose --profile prod down  # Prod

# View logs
tail -f logs/yahoo-services.log  # Dev
docker-compose logs -f yahoo-services-stage  # Stage
docker-compose logs -f yahoo-services-prod  # Prod
```

---

## ⚠️ Important Notes

1. **Production Deployment**:
   - MUST be done from `main` branch only
   - 5-second warning before deployment
   - Verifies working directory is clean
   - Pulls latest code automatically

2. **Staging Deployment**:
   - MUST be done from `develop` branch
   - Used for pre-production testing
   - Isolated Redis DB (DB 4)

3. **Development Deployment**:
   - Can be run from any branch
   - Uses virtual environment (not Docker)
   - Direct Python execution for faster iteration

---

**All scripts are idempotent** - safe to run multiple times.

---

Last Updated: 2026-02-13
