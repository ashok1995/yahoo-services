# Yahoo Services Deployment Guide

## Port Configuration

| Environment | Port | Redis DB | Use Case |
|-------------|------|----------|----------|
| Development | 8085 | DB 3 | Local development |
| Staging | 8285 | DB 4 | Pre-production testing |
| Production | 8185 | DB 3 | Production deployment |

## Local Development (Port 8085)

### Method 1: Direct Python (Recommended for Dev)

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment (loads envs/env.dev)
export ENVIRONMENT=development

# Start service
python3 main.py
```

Service will start on `http://localhost:8085`

### Method 2: Using Entrypoint Script

```bash
# Make sure script is executable
chmod +x entrypoint.sh

# Run with development settings
ENVIRONMENT=development ./entrypoint.sh
```

### Method 3: Docker Compose (Dev Profile)

```bash
# Start development environment with Redis
docker-compose --profile dev up -d

# View logs
docker-compose logs -f yahoo-services-dev

# Stop
docker-compose --profile dev down
```

## Staging Deployment (Port 8285)

### Local Staging Test

```bash
# Using entrypoint
ENVIRONMENT=staging ./entrypoint.sh
```

### Docker Staging

```bash
# Start staging environment
docker-compose --profile stage up -d

# View logs
docker-compose logs -f yahoo-services-stage

# Stop
docker-compose --profile stage down
```

## Production Deployment (Port 8185)

### VM Deployment (Recommended)

```bash
# On production VM

# 1. Pull latest code
cd /path/to/yahoo-services
git pull origin main

# 2. Set environment
export ENVIRONMENT=production

# 3. Start with Docker Compose
docker-compose --profile prod up -d

# 4. Check logs
docker-compose logs -f yahoo-services-prod

# 5. Health check
curl http://localhost:8185/health
```

### Manual Production Deployment

```bash
# Activate virtual environment
source venv/bin/activate

# Start production service
ENVIRONMENT=production ./entrypoint.sh
```

## Health Checks

All environments expose a health endpoint:

```bash
# Development
curl http://localhost:8085/health

# Staging
curl http://localhost:8285/health

# Production
curl http://localhost:8185/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "yahoo-services",
  "yahoo_finance_available": true,
  "alpha_vantage_available": false,
  "timestamp": "2026-02-13T..."
}
```

## Testing Endpoints

### 1. Health Check

```bash
curl http://localhost:8085/health
```

### 2. Global Context (Primary Endpoint)

```bash
curl http://localhost:8085/api/v1/global-context
```

### 3. Fundamentals Batch

```bash
curl -X POST http://localhost:8085/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "SBIN.NS", "TCS.NS"]}'
```

### 4. Alpha Vantage Fallback (Not Implemented)

```bash
curl http://localhost:8085/api/v1/alpha-vantage/global-context
```

## Environment Variables

Each environment has its own file in `envs/`:
- `envs/env.dev` - Development (port 8085)
- `envs/env.stage` - Staging (port 8285)
- `envs/env.prod` - Production (port 8185)

**DO NOT** commit sensitive data (API keys, passwords) to these files.

## Troubleshooting

### Port Already in Use

```bash
# Kill process on specific port
lsof -ti:8085 | xargs kill -9  # Dev
lsof -ti:8285 | xargs kill -9  # Stage
lsof -ti:8185 | xargs kill -9  # Prod
```

### Redis Connection Error

```bash
# Check Redis is running
redis-cli ping

# Start Redis if not running
redis-server
```

### View Service Logs

```bash
# Local logs (JSON format)
tail -f logs/yahoo-services.log

# Docker logs
docker-compose logs -f yahoo-services-dev   # Dev
docker-compose logs -f yahoo-services-stage # Stage
docker-compose logs -f yahoo-services-prod  # Prod
```

## API Documentation

Once service is running, access interactive API docs:
- Swagger UI: `http://localhost:8085/docs`
- ReDoc: `http://localhost:8085/redoc`

## Monitoring

Check service status:
```bash
# Service info
curl http://localhost:8085/

# Health with details
curl http://localhost:8085/health
```

Monitor logs in real-time:
```bash
# JSON logs
tail -f logs/yahoo-services.log | jq .
```

## Scaling

For production scaling:
1. Use Docker Compose with multiple replicas
2. Add load balancer (nginx) in front
3. Monitor with Prometheus/Grafana
4. Set up log aggregation (ELK stack)

---

**Last Updated**: 2026-02-13
