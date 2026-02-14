#!/bin/bash
# Staging Deployment Script for Yahoo Services
# Port: 8285 | Environment: staging | Deploy Method: Docker Compose
#
# Usage:
#   ./deploy-stage.sh           # Foreground (blocks until health check)
#   ./deploy-stage.sh --background   # Run in background, log to file (non-blocking)
#   ./deploy-stage.sh -b             # Same as --background

set -e

# Ensure Docker socket is used (helps when run in background; macOS Docker Desktop)
if [ -n "$HOME" ] && [ -S "$HOME/.docker/run/docker.sock" ]; then
    export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
fi

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
STAGE_LOG="${STAGE_LOG:-./logs/deploy-stage.log}"

# If --background or -b, re-run in background (without this flag) and exit
for arg in "$@"; do
    case $arg in
        --background|-b)
            mkdir -p "$(dirname "$STAGE_LOG")"
            echo "Starting staging deploy in background. Log: $STAGE_LOG"
            # Run self without --background/-b so it does full deploy; output to log
            RUN_ARGS=()
            for a in "$@"; do [[ "$a" != "--background" && "$a" != "-b" ]] && RUN_ARGS+=("$a"); done
            nohup "$0" "${RUN_ARGS[@]}" > "$STAGE_LOG" 2>&1 &
            echo "PID: $!"
            echo "Tail log: tail -f $STAGE_LOG"
            exit 0
            ;;
    esac
done

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
    echo -e "${YELLOW}Starting Docker Desktop...${NC}"
    open -a Docker
    echo -e "${YELLOW}Waiting for Docker to start (up to 60 seconds)...${NC}"
    
    # Wait for Docker to start
    DOCKER_WAIT=0
    while [ $DOCKER_WAIT -lt 60 ]; do
        if docker info > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Docker is now running${NC}"
            break
        fi
        echo -n "."
        sleep 2
        DOCKER_WAIT=$((DOCKER_WAIT + 2))
    done
    echo ""
    
    if [ $DOCKER_WAIT -ge 60 ]; then
        echo -e "${RED}❌ Docker failed to start within 60 seconds${NC}"
        echo -e "${YELLOW}Please start Docker Desktop manually and try again${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Docker is running${NC}"
fi

# Redis is in Docker (redis-stage container), no need to check local Redis
echo -e "${GREEN}✅ Redis will run in Docker (redis-stage)${NC}"

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

# Step 5: Build Docker image (ensure daemon is reachable before build)
echo -e "${YELLOW}[5/8]${NC} Building Docker image..."
DOCKER_READY=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if docker info > /dev/null 2>&1; then
        DOCKER_READY=1
        break
    fi
    echo -e "${YELLOW}   Waiting for Docker daemon...${NC}"
    sleep 3
done
if [ "$DOCKER_READY" -eq 0 ]; then
    echo -e "${RED}❌ Cannot connect to Docker daemon. Ensure Docker Desktop is running and try again.${NC}"
    exit 1
fi
export DOCKER_BUILDKIT=1 && docker-compose --profile ${PROFILE} build
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
echo -e "${YELLOW}📌 Run without blocking (background):${NC}"
echo -e "  ./deploy-stage.sh --background   # or: ./deploy-stage.sh -b"
echo ""
