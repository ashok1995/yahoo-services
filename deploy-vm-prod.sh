#!/bin/bash
# Deploy Yahoo Services to Production VM
# Run this script locally or on the VM

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
# DETECT ENVIRONMENT
# ============================================================
if [ "$(hostname)" != "vm488109385" ] && [ ! -d "$PROJECT_DIR" ]; then
    # Running locally, deploy via SSH
    echo -e "${YELLOW}📡 Deploying from local machine to VM...${NC}"
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
        docker compose -f docker-compose.prod.yml build --no-cache
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
    docker compose -f docker-compose.prod.yml build --no-cache
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
