#!/bin/bash
# Deploy Yahoo Services to Production VM
# Run this script locally or on the VM
#
# Usage (run only from main branch):
#   git checkout main && ./deploy-vm-prod.sh              # Build locally, transfer, run on VM
#   ./deploy-vm-prod.sh --build-on-vm                     # Build on VM (slow)
#   ./deploy-vm-prod.sh --no-cache                        # Force full rebuild
# See BRANCH-WORKFLOW.md for branch rules.

set -e

# ============================================================
# CONFIGURATION
# ============================================================
VM_HOST="203.57.85.72"
VM_USER="root"
VM_PASSWORD="i1sS4UMRi7FXnDy9"
PROJECT_DIR="/opt/yahoo-services"
SERVICE_PORT="8185"
REPO_URL="https://github.com/ashok1995/yahoo-services.git"
IMAGE_NAME="yahoo-services:production"
IMAGE_TAR="/tmp/yahoo-services-prod.tar.gz"

# Default to building locally when deploying from local machine (VM is slow)
# Use --build-on-vm to force building on VM instead
BUILD_LOCAL=true
NO_CACHE=false
for arg in "$@"; do
    case $arg in
        --build-on-vm)
            BUILD_LOCAL=false
            ;;
        --no-cache)
            NO_CACHE=true
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Yahoo Services - Production VM Deployment             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# DEPLOY FROM LOCAL: BUILD LOCALLY, TRANSFER IMAGE, RUN ON VM
# (Use when VM build is too slow - build on your Mac, VM only loads image)
# ============================================================
if [[ "$BUILD_LOCAL" == true ]] && [ "$(hostname)" != "vm488109385" ]; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo -e "${RED}❌ Production deploy must run from main branch (current: $CURRENT_BRANCH)${NC}"
        echo -e "${YELLOW}  Merge to main first, then: git checkout main && ./deploy-vm-prod.sh${NC}"
        echo -e "${YELLOW}  See BRANCH-WORKFLOW.md${NC}"
        exit 1
    fi
    echo -e "${YELLOW}🔨 Build-local mode: building image on this machine, then transferring to VM${NC}"
    echo ""
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    
    echo -e "${YELLOW}[1/5]${NC} Building image for linux/amd64 (VM architecture)..."
    if [[ "$NO_CACHE" == true ]]; then
        echo -e "${YELLOW}   ⚠️  Using --no-cache (fresh build)${NC}"
    fi
    export DOCKER_BUILDKIT=1
    if [[ "$NO_CACHE" == true ]]; then
        docker buildx build --no-cache --platform linux/amd64 -t "$IMAGE_NAME" --load -f Dockerfile .
    else
        docker buildx build --platform linux/amd64 -t "$IMAGE_NAME" --load -f Dockerfile .
    fi
    echo -e "${GREEN}✅ Image built${NC}"
    
    echo -e "${YELLOW}[2/5]${NC} Saving image to tar..."
    docker save "$IMAGE_NAME" | gzip > "$IMAGE_TAR"
    echo -e "${GREEN}✅ Saved to $IMAGE_TAR${NC}"
    
    echo -e "${YELLOW}[3/5]${NC} Transferring image to VM..."
    sshpass -p "$VM_PASSWORD" scp -o StrictHostKeyChecking=no "$IMAGE_TAR" "$VM_USER@$VM_HOST:$IMAGE_TAR"
    rm -f "$IMAGE_TAR"
    echo -e "${GREEN}✅ Transferred${NC}"
    
    echo -e "${YELLOW}[4/5]${NC} On VM: loading image and starting containers..."
    sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" << ENDSSH
        set -e
        if [ ! -d /opt/yahoo-services ]; then
            git clone $REPO_URL /opt/yahoo-services
            cd /opt/yahoo-services && git checkout main
        fi
        cd /opt/yahoo-services
        git pull origin main
        docker compose -f docker-compose.prod.yml down 2>/dev/null || true
        docker load < $IMAGE_TAR
        rm -f $IMAGE_TAR
        docker compose -f docker-compose.prod.yml up -d
        echo "Waiting for service (up to 60s)..."
        sleep 40
        HEALTH_OK=0
        n=0
        while [ \$n -lt 10 ]; do
            if curl -sf http://localhost:8185/health > /dev/null 2>&1; then
                HEALTH_OK=1
                break
            fi
            n=\$((n+1))
            sleep 2
        done
        if [ \$HEALTH_OK -eq 0 ]; then
            echo "❌ Health check failed after 60s"
            docker compose -f docker-compose.prod.yml logs --tail=40
            exit 1
        fi
        echo "✅ Service is healthy!"
        curl -s http://localhost:8185/health | python3 -m json.tool 2>/dev/null || true
        echo ""
        echo "✅ Deployment complete! http://203.57.85.72:8185"
        echo "   If curl from Mac fails, on VM open port: ufw allow 8185 && ufw reload"
ENDSSH
    echo -e "${GREEN}✅ Remote deployment completed!${NC}"
    echo ""
    exit 0
fi

# ============================================================
# DETECT ENVIRONMENT
# ============================================================
if [ "$(hostname)" != "vm488109385" ] && [ ! -d "$PROJECT_DIR" ] && [[ "$BUILD_LOCAL" == false ]]; then
    # Running locally, deploy via SSH (build on VM) - only if --build-on-vm flag used
    echo -e "${YELLOW}📡 Deploying from local machine to VM (building on VM - this will be slow)...${NC}"
    echo -e "${YELLOW}   Tip: remove --build-on-vm flag to build on your Mac instead (much faster)${NC}"
    echo ""
    
    if ! command -v sshpass &> /dev/null; then
        echo -e "${RED}❌ sshpass not found${NC}"
        echo -e "${YELLOW}Install: brew install sshpass (macOS) or apt install sshpass (Linux)${NC}"
        exit 1
    fi
    
    sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" << 'ENDSSH'
        set -e
        
        # Colors for output
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        BLUE='\033[0;34m'
        NC='\033[0m'
        
        PROJECT_DIR="/opt/yahoo-services"
        SERVICE_PORT="8185"
        REPO_URL="https://github.com/ashok1995/yahoo-services.git"
        
        echo -e "${YELLOW}[1/7]${NC} Checking project directory..."
        if [ ! -d "$PROJECT_DIR" ]; then
            echo -e "${YELLOW}⚠️  Project directory not found. Cloning repository...${NC}"
            git clone "$REPO_URL" "$PROJECT_DIR"
            cd "$PROJECT_DIR"
            git checkout main
        else
            cd "$PROJECT_DIR"
            echo -e "${GREEN}✅ Project directory exists${NC}"
        fi
        
        echo -e "${YELLOW}[2/7]${NC} Pulling latest code from main branch..."
        git fetch origin
        git checkout main
        git pull origin main
        echo -e "${GREEN}✅ Code updated to latest main${NC}"
        
        echo -e "${YELLOW}[3/7]${NC} Checking Docker..."
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Docker is available${NC}"
        
        echo -e "${YELLOW}[4/7]${NC} Stopping existing containers..."
        docker compose -f docker-compose.prod.yml down 2>/dev/null || true
        echo -e "${GREEN}✅ Existing containers stopped${NC}"
        
        echo -e "${YELLOW}[5/7]${NC} Building and starting production containers..."
        docker compose -f docker-compose.prod.yml pull 2>/dev/null || true
        export DOCKER_BUILDKIT=1 && docker compose -f docker-compose.prod.yml build
        docker compose -f docker-compose.prod.yml up -d
        echo -e "${GREEN}✅ Containers started${NC}"
        
        echo -e "${YELLOW}[6/7]${NC} Waiting for service to start..."
        sleep 20
        
        echo -e "${YELLOW}[7/7]${NC} Verifying service health..."
        RETRY_COUNT=0
        MAX_RETRIES=10
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if curl -f http://localhost:$SERVICE_PORT/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Service is healthy!${NC}"
                curl -s http://localhost:$SERVICE_PORT/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:$SERVICE_PORT/health
                break
            fi
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo -n "."
            sleep 3
        done
        
        echo ""
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo -e "${RED}❌ Service health check failed${NC}"
            echo -e "${YELLOW}📋 Container logs:${NC}"
            docker compose -f docker-compose.prod.yml logs --tail=50
            exit 1
        fi
        
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║              Production Deployment Successful ✅                ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}Service:${NC} yahoo-services-prod"
        echo -e "${GREEN}Port:${NC} $SERVICE_PORT"
        echo -e "${GREEN}URL:${NC} http://203.57.85.72:$SERVICE_PORT"
        echo ""
        echo -e "${YELLOW}📋 Quick Tests:${NC}"
        echo -e "  Health:         curl http://203.57.85.72:$SERVICE_PORT/health"
        echo -e "  Global Context: curl http://203.57.85.72:$SERVICE_PORT/api/v1/global-context"
        echo -e "  API Docs:       http://203.57.85.72:$SERVICE_PORT/docs"
        echo ""
        echo -e "${YELLOW}📊 View Logs:${NC}"
        echo -e "  docker compose -f docker-compose.prod.yml logs -f"
        echo ""
        echo -e "${YELLOW}🔄 Restart:${NC}"
        echo -e "  docker compose -f docker-compose.prod.yml restart"
        echo ""
ENDSSH

    echo ""
    echo -e "${GREEN}✅ Remote deployment completed!${NC}"
    
else
    # Running on VM directly
    echo -e "${YELLOW}📍 Running on VM, deploying directly...${NC}"
    echo ""
    
    echo -e "${YELLOW}[1/7]${NC} Checking project directory..."
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${YELLOW}⚠️  Project directory not found. Cloning repository...${NC}"
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        git checkout main
    else
        cd "$PROJECT_DIR"
        echo -e "${GREEN}✅ Project directory exists${NC}"
    fi
    
    echo -e "${YELLOW}[2/7]${NC} Pulling latest code from main branch..."
    git fetch origin
    git checkout main
    git pull origin main
    echo -e "${GREEN}✅ Code updated to latest main${NC}"
    
    echo -e "${YELLOW}[3/7]${NC} Checking Docker..."
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker is available${NC}"
    
    echo -e "${YELLOW}[4/7]${NC} Stopping existing containers..."
    docker compose -f docker-compose.prod.yml down 2>/dev/null || true
    echo -e "${GREEN}✅ Existing containers stopped${NC}"
    
    echo -e "${YELLOW}[5/7]${NC} Building and starting production containers..."
    docker compose -f docker-compose.prod.yml pull 2>/dev/null || true
    export DOCKER_BUILDKIT=1 && docker compose -f docker-compose.prod.yml build
    docker compose -f docker-compose.prod.yml up -d
    echo -e "${GREEN}✅ Containers started${NC}"
    
    echo -e "${YELLOW}[6/7]${NC} Waiting for service to start..."
    sleep 20
    
    echo -e "${YELLOW}[7/7]${NC} Verifying service health..."
    RETRY_COUNT=0
    MAX_RETRIES=10
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f http://localhost:$SERVICE_PORT/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Service is healthy!${NC}"
            curl -s http://localhost:$SERVICE_PORT/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:$SERVICE_PORT/health
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 3
    done
    
    echo ""
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Service health check failed${NC}"
        echo -e "${YELLOW}📋 Container logs:${NC}"
        docker compose -f docker-compose.prod.yml logs --tail=50
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              Production Deployment Successful ✅                ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Service:${NC} yahoo-services-prod"
    echo -e "${GREEN}Port:${NC} $SERVICE_PORT"
    echo -e "${GREEN}URL:${NC} http://203.57.85.72:$SERVICE_PORT"
    echo ""
    echo -e "${YELLOW}📋 Quick Tests:${NC}"
    echo -e "  Health:         curl http://203.57.85.72:$SERVICE_PORT/health"
    echo -e "  Global Context: curl http://203.57.85.72:$SERVICE_PORT/api/v1/global-context"
    echo -e "  API Docs:       http://203.57.85.72:$SERVICE_PORT/docs"
    echo ""
    echo -e "${YELLOW}📊 View Logs:${NC}"
    echo -e "  docker compose -f docker-compose.prod.yml logs -f"
    echo ""
    echo -e "${YELLOW}🔄 Restart:${NC}"
    echo -e "  docker compose -f docker-compose.prod.yml restart"
    echo ""
fi
