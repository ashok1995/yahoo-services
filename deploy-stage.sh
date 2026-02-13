#!/bin/bash
# Staging Deployment Script for Yahoo Services
# Port: 8285 | Environment: staging | Deploy Method: Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PORT=8285
ENVIRONMENT="staging"
SERVICE_NAME="yahoo-services-stage"
PROFILE="stage"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Yahoo Services - Staging Deployment                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/8]${NC} Checking prerequisites..."

# Check if on develop branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo -e "${RED}❌ Not on develop branch (current: ${CURRENT_BRANCH})${NC}"
    echo -e "${YELLOW}Switch to develop branch:${NC} git checkout develop"
    exit 1
fi
echo -e "${GREEN}✅ On develop branch${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop and try again${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check if Redis is running (for local staging)
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Redis is not running. Starting...${NC}"
    brew services start redis || {
        echo -e "${RED}Failed to start Redis. Please start Redis manually.${NC}"
        exit 1
    }
    sleep 2
fi
echo -e "${GREEN}✅ Redis is running${NC}"

# Step 2: Kill any process on port 8285
echo -e "${YELLOW}[2/8]${NC} Checking port ${PORT}..."
if lsof -ti:${PORT} > /dev/null 2>&1; then
    PID=$(lsof -ti:${PORT})
    echo -e "${YELLOW}⚠️  Port ${PORT} is in use by PID ${PID}. Killing process...${NC}"
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ Port ${PORT} is now free${NC}"
else
    echo -e "${GREEN}✅ Port ${PORT} is available${NC}"
fi

# Step 3: Verify environment file
echo -e "${YELLOW}[3/8]${NC} Verifying environment configuration..."
if [ ! -f "envs/env.stage" ]; then
    echo -e "${RED}❌ Environment file not found: envs/env.stage${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Environment file found: envs/env.stage${NC}"

# Step 4: Stop existing staging containers
echo -e "${YELLOW}[4/8]${NC} Stopping existing staging containers..."
docker-compose --profile ${PROFILE} down > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Existing containers stopped${NC}"

# Step 5: Build Docker image
echo -e "${YELLOW}[5/8]${NC} Building Docker image..."
docker-compose --profile ${PROFILE} build --no-cache
echo -e "${GREEN}✅ Docker image built${NC}"

# Step 6: Start staging service
echo -e "${YELLOW}[6/8]${NC} Starting ${SERVICE_NAME} on port ${PORT}..."
docker-compose --profile ${PROFILE} up -d
echo -e "${GREEN}✅ Service started${NC}"

# Step 7: Wait for service to be ready
echo -e "${YELLOW}[7/8]${NC} Waiting for service to be ready..."
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:${PORT}/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is ready!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 1
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Service failed to start within 30 seconds${NC}"
    echo -e "${YELLOW}Check logs: docker-compose logs ${SERVICE_NAME}${NC}"
    exit 1
fi

# Step 8: Verify service health
echo -e "${YELLOW}[8/8]${NC} Verifying service health..."
HEALTH_RESPONSE=$(curl -s http://localhost:${PORT}/health)
STATUS=$(echo $HEALTH_RESPONSE | jq -r '.status' 2>/dev/null || echo "unknown")

if [ "$STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ Service is healthy!${NC}"
else
    echo -e "${RED}❌ Service is not healthy${NC}"
    echo -e "${YELLOW}Response: ${HEALTH_RESPONSE}${NC}"
    exit 1
fi

# Display summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Staging Deployment Successful ✅                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service:${NC} ${SERVICE_NAME}"
echo -e "${GREEN}Port:${NC} ${PORT}"
echo -e "${GREEN}Environment:${NC} ${ENVIRONMENT}"
echo -e "${GREEN}Branch:${NC} develop"
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
echo -e "${YELLOW}🛑 Stop Service:${NC}"
echo -e "  docker-compose --profile ${PROFILE} down"
echo ""
echo -e "${YELLOW}🔄 Restart Service:${NC}"
echo -e "  docker-compose --profile ${PROFILE} restart"
echo ""
