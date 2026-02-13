#!/bin/bash
# Production Deployment Script for Yahoo Services
# Port: 8185 | Environment: production | Deploy Method: Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PORT=8185
ENVIRONMENT="production"
SERVICE_NAME="yahoo-services-prod"
PROFILE="prod"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Yahoo Services - Production Deployment                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# WARNING: Production deployment
echo -e "${RED}⚠️  WARNING: You are deploying to PRODUCTION${NC}"
echo -e "${YELLOW}Press CTRL+C within 5 seconds to cancel...${NC}"
sleep 5
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/9]${NC} Checking prerequisites..."

# Check if on main branch (production MUST deploy from main)
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}❌ Not on main branch (current: ${CURRENT_BRANCH})${NC}"
    echo -e "${RED}Production MUST be deployed from main branch only${NC}"
    echo -e "${YELLOW}Switch to main branch:${NC} git checkout main"
    exit 1
fi
echo -e "${GREEN}✅ On main branch (production)${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop and try again${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Step 2: Verify working directory is clean
echo -e "${YELLOW}[2/9]${NC} Verifying git status..."
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ You have uncommitted changes${NC}"
    echo -e "${YELLOW}Commit or stash changes before production deployment${NC}"
    git status --short
    exit 1
fi
echo -e "${GREEN}✅ Working directory is clean${NC}"

# Step 3: Pull latest changes from main
echo -e "${YELLOW}[3/9]${NC} Pulling latest changes from main..."
git pull origin main
echo -e "${GREEN}✅ Code updated to latest${NC}"

# Step 4: Kill any process on port 8185
echo -e "${YELLOW}[4/9]${NC} Checking port ${PORT}..."
if lsof -ti:${PORT} > /dev/null 2>&1; then
    PID=$(lsof -ti:${PORT})
    echo -e "${YELLOW}⚠️  Port ${PORT} is in use by PID ${PID}. Killing process...${NC}"
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ Port ${PORT} is now free${NC}"
else
    echo -e "${GREEN}✅ Port ${PORT} is available${NC}"
fi

# Step 5: Verify environment file
echo -e "${YELLOW}[5/9]${NC} Verifying production environment configuration..."
if [ ! -f "envs/env.prod" ]; then
    echo -e "${RED}❌ Environment file not found: envs/env.prod${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Production environment file found${NC}"

# Step 6: Stop existing production containers
echo -e "${YELLOW}[6/9]${NC} Stopping existing production containers..."
docker-compose --profile ${PROFILE} down > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Existing containers stopped${NC}"

# Step 7: Build Docker image
echo -e "${YELLOW}[7/9]${NC} Building production Docker image..."
docker-compose --profile ${PROFILE} build --no-cache
echo -e "${GREEN}✅ Production image built${NC}"

# Step 8: Start production service
echo -e "${YELLOW}[8/9]${NC} Starting ${SERVICE_NAME} on port ${PORT}..."
docker-compose --profile ${PROFILE} up -d
echo -e "${GREEN}✅ Production service started${NC}"

# Wait for service to be ready
echo -e "${YELLOW}Waiting for production service to be ready...${NC}"
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:${PORT}/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Production service is ready!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 1
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Production service failed to start within 30 seconds${NC}"
    echo -e "${YELLOW}Check logs: docker-compose logs ${SERVICE_NAME}${NC}"
    exit 1
fi

# Step 9: Verify production service health
echo -e "${YELLOW}[9/9]${NC} Verifying production service health..."
HEALTH_RESPONSE=$(curl -s http://localhost:${PORT}/health)
STATUS=$(echo $HEALTH_RESPONSE | jq -r '.status' 2>/dev/null || echo "unknown")

if [ "$STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ Production service is healthy!${NC}"
else
    echo -e "${RED}❌ Production service is not healthy${NC}"
    echo -e "${YELLOW}Response: ${HEALTH_RESPONSE}${NC}"
    exit 1
fi

# Display summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Production Deployment Successful ✅                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service:${NC} ${SERVICE_NAME}"
echo -e "${GREEN}Port:${NC} ${PORT}"
echo -e "${GREEN}Environment:${NC} ${ENVIRONMENT}"
echo -e "${GREEN}Branch:${NC} main"
echo -e "${GREEN}URL:${NC} http://localhost:${PORT}"
echo ""
echo -e "${YELLOW}📋 Quick Tests:${NC}"
echo -e "  Health Check:    curl http://localhost:${PORT}/health | jq ."
echo -e "  Global Context:  curl http://localhost:${PORT}/api/v1/global-context | jq ."
echo -e "  API Docs:        http://localhost:${PORT}/docs"
echo ""
echo -e "${YELLOW}📊 View Logs:${NC}"
echo -e "  docker-compose logs -f ${SERVICE_NAME}"
echo ""
echo -e "${YELLOW}🛑 Stop Production:${NC}"
echo -e "  docker-compose --profile ${PROFILE} down"
echo ""
echo -e "${YELLOW}🔄 Restart Production:${NC}"
echo -e "  docker-compose --profile ${PROFILE} restart"
echo ""
echo -e "${RED}⚠️  PRODUCTION IS NOW LIVE ⚠️${NC}"
echo ""
