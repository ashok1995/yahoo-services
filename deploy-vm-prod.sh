#!/bin/bash
# Deploy Yahoo Services to Production VM
# Fetches pre-built image from GHCR (built by CI on push to main).
# Usage:
#   From local: ./deploy-vm-prod.sh   # SSH to VM, pull compose + image from GHCR, up
#   On VM:      ./deploy-vm-prod.sh   # Same steps
# For private GHCR package: set GHCR_TOKEN on VM (GitHub PAT with read:packages).
# See BRANCH-WORKFLOW.md.

set -e

VM_HOST="203.57.85.201"
VM_USER="root"
VM_PASSWORD="CkpkBPB1unsOyOfd"
PROJECT_DIR="/opt/yahoo-services"
SERVICE_PORT="8185"
REPO_URL="https://github.com/ashok1995/yahoo-services.git"
GHCR_IMAGE="ghcr.io/ashok1995/yahoo-services:main"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Yahoo Services - Production VM Deployment             ║${NC}"
echo -e "${BLUE}║         (Pull compose + image from GHCR → up)                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# FROM LOCAL: SSH to VM and run deploy (pull compose + image from GHCR)
# ============================================================
if [ "$(hostname)" != "vm488109385" ] && [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}📡 Deploying via VM: pull compose + image from GHCR.${NC}"
    echo ""

    if ! command -v sshpass &> /dev/null; then
        echo -e "${RED}❌ sshpass not found. Install: brew install sshpass (macOS) or apt install sshpass (Linux)${NC}"
        exit 1
    fi

    sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" << ENDSSH
        set -e
        PROJECT_DIR="/opt/yahoo-services"
        SERVICE_PORT="8185"
        REPO_URL="https://github.com/ashok1995/yahoo-services.git"
        GHCR_IMAGE="$GHCR_IMAGE"

        echo "[1/6] Checking project directory..."
        if [ ! -d "\$PROJECT_DIR" ]; then
            git clone "\$REPO_URL" "\$PROJECT_DIR"
            cd "\$PROJECT_DIR" && git checkout main
        else
            cd "\$PROJECT_DIR"
        fi

        echo "[2/6] Pulling latest compose from main..."
        git fetch origin
        git checkout main
        git pull origin main
        echo "✅ Compose/config updated"

        echo "[3/6] Checking Docker..."
        command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }

        [ -n "\$GHCR_TOKEN" ] && echo "\$GHCR_TOKEN" | docker login ghcr.io -u ashok1995 --password-stdin 2>/dev/null || true

        echo "[4/6] Stopping containers and pulling image from GHCR..."
        docker compose -f docker-compose.prod.yml down 2>/dev/null || true
        docker compose -f docker-compose.prod.yml pull
        docker compose -f docker-compose.prod.yml up -d
        echo "✅ Containers started"

        echo "[5/6] Waiting for service (up to 60s)..."
        sleep 40
        HEALTH_OK=0
        n=0
        while [ \$n -lt 10 ]; do
            if curl -sf http://localhost:\$SERVICE_PORT/health > /dev/null 2>&1; then
                HEALTH_OK=1
                break
            fi
            n=\$((n+1))
            sleep 2
        done

        echo "[6/6] Verifying service health..."
        if [ \$HEALTH_OK -eq 0 ]; then
            echo "❌ Health check failed after 60s"
            docker compose -f docker-compose.prod.yml logs --tail=40
            exit 1
        fi
        echo "✅ Service is healthy!"
        curl -s http://localhost:\$SERVICE_PORT/health | python3 -m json.tool 2>/dev/null || true
        echo ""
        echo "✅ Deployment complete! http://${VM_HOST}:\$SERVICE_PORT"
        echo "   If curl from Mac fails, on VM: ufw allow 8185 && ufw reload"
ENDSSH

    echo ""
    echo -e "${GREEN}✅ Remote deployment completed!${NC}"
    exit 0
fi

# ============================================================
# ON VM: pull compose + image from GHCR, up
# ============================================================
echo -e "${YELLOW}📍 Running on VM, deploying directly...${NC}"
echo ""

echo -e "${YELLOW}[1/6]${NC} Checking project directory..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⚠️  Project directory not found. Cloning repository...${NC}"
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    git checkout main
else
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✅ Project directory exists${NC}"
fi

echo -e "${YELLOW}[2/6]${NC} Pulling latest compose from main..."
git fetch origin
git checkout main
git pull origin main
echo -e "${GREEN}✅ Compose/config updated${NC}"

echo -e "${YELLOW}[3/6]${NC} Checking Docker..."
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker not found${NC}"; exit 1; }
echo -e "${GREEN}✅ Docker is available${NC}"

[ -n "$GHCR_TOKEN" ] && echo "$GHCR_TOKEN" | docker login ghcr.io -u ashok1995 --password-stdin 2>/dev/null || true

echo -e "${YELLOW}[4/6]${NC} Stopping containers and pulling image from GHCR..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✅ Containers started${NC}"

echo -e "${YELLOW}[5/6]${NC} Waiting for service (up to 60s)..."
sleep 40
HEALTH_OK=0
n=0
while [ $n -lt 10 ]; do
    if curl -sf http://localhost:$SERVICE_PORT/health > /dev/null 2>&1; then
        HEALTH_OK=1
        break
    fi
    n=$((n+1))
    sleep 2
done

echo -e "${YELLOW}[6/6]${NC} Verifying service health..."
if [ "$HEALTH_OK" -eq 0 ]; then
    echo -e "${RED}❌ Health check failed after 60s${NC}"
    docker compose -f docker-compose.prod.yml logs --tail=40
    exit 1
fi
echo -e "${GREEN}✅ Service is healthy!${NC}"
curl -s http://localhost:$SERVICE_PORT/health | python3 -m json.tool 2>/dev/null || true

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Production Deployment Successful ✅                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service:${NC} yahoo-services-prod"
echo -e "${GREEN}Port:${NC} $SERVICE_PORT"
echo -e "${GREEN}URL:${NC} http://${VM_HOST}:$SERVICE_PORT"
echo ""
echo -e "${YELLOW}📋 Quick Tests:${NC}"
echo -e "  Health:         curl http://${VM_HOST}:$SERVICE_PORT/health"
echo -e "  Global Context: curl http://${VM_HOST}:$SERVICE_PORT/api/v1/global-context"
echo -e "  API Docs:       http://${VM_HOST}:$SERVICE_PORT/docs"
echo ""
echo -e "${YELLOW}📊 View Logs:${NC}"
echo -e "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo -e "${YELLOW}🔄 Restart:${NC}"
echo -e "  docker compose -f docker-compose.prod.yml restart"
echo ""
echo -e "${YELLOW}📌 If curl from Mac fails, on VM:${NC} ufw allow 8185 && ufw reload"
echo ""
