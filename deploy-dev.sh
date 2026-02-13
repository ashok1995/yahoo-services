#!/bin/bash
# Development Deployment Script for Yahoo Services
# Port: 8085 | Environment: development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PORT=8085
ENVIRONMENT="development"
SERVICE_NAME="yahoo-services-dev"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Yahoo Services - Development Deployment               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7]${NC} Checking prerequisites..."

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}❌ Redis is not running${NC}"
    echo -e "${YELLOW}Starting Redis...${NC}"
    brew services start redis || {
        echo -e "${RED}Failed to start Redis. Please start Redis manually.${NC}"
        exit 1
    }
    sleep 2
fi
echo -e "${GREEN}✅ Redis is running${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ Virtual environment exists${NC}"
fi

# Step 2: Kill any process on port 8085
echo -e "${YELLOW}[2/7]${NC} Checking port ${PORT}..."
if lsof -ti:${PORT} > /dev/null 2>&1; then
    PID=$(lsof -ti:${PORT})
    echo -e "${YELLOW}⚠️  Port ${PORT} is in use by PID ${PID}. Killing process...${NC}"
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✅ Port ${PORT} is now free${NC}"
else
    echo -e "${GREEN}✅ Port ${PORT} is available${NC}"
fi

# Step 3: Verify environment file exists
echo -e "${YELLOW}[3/7]${NC} Verifying environment configuration..."
if [ ! -f "envs/env.dev" ]; then
    echo -e "${RED}❌ Environment file not found: envs/env.dev${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Environment file found: envs/env.dev${NC}"

# Step 4: Create logs directory
echo -e "${YELLOW}[4/7]${NC} Setting up logs directory..."
mkdir -p logs
echo -e "${GREEN}✅ Logs directory ready${NC}"

# Step 5: Activate virtual environment and start service
echo -e "${YELLOW}[5/7]${NC} Starting ${SERVICE_NAME} on port ${PORT}..."
source venv/bin/activate
export ENVIRONMENT=${ENVIRONMENT}

# Start service in background
nohup python3 main.py > logs/dev-startup.log 2>&1 &
SERVICE_PID=$!

echo -e "${GREEN}✅ Service started with PID: ${SERVICE_PID}${NC}"

# Step 6: Wait for service to be ready
echo -e "${YELLOW}[6/7]${NC} Waiting for service to be ready..."
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
    echo -e "${YELLOW}Check logs: tail -f logs/yahoo-services.log${NC}"
    exit 1
fi

# Step 7: Verify service health
echo -e "${YELLOW}[7/7]${NC} Verifying service health..."
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
echo -e "${BLUE}║              Deployment Successful ✅                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service:${NC} ${SERVICE_NAME}"
echo -e "${GREEN}Port:${NC} ${PORT}"
echo -e "${GREEN}Environment:${NC} ${ENVIRONMENT}"
echo -e "${GREEN}PID:${NC} ${SERVICE_PID}"
echo -e "${GREEN}URL:${NC} http://localhost:${PORT}"
echo ""
echo -e "${YELLOW}📋 Quick Tests:${NC}"
echo -e "  Health Check:    curl http://localhost:${PORT}/health"
echo -e "  Global Context:  curl http://localhost:${PORT}/api/v1/global-context"
echo -e "  API Docs:        http://localhost:${PORT}/docs"
echo ""
echo -e "${YELLOW}📊 View Logs:${NC}"
echo -e "  tail -f logs/yahoo-services.log"
echo ""
echo -e "${YELLOW}🛑 Stop Service:${NC}"
echo -e "  lsof -ti:${PORT} | xargs kill -9"
echo ""
