#!/bin/bash
# Setup Git Authentication on VM for Yahoo Services
# This script guides you through the process

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

VM_HOST="203.57.85.72"
VM_USER="root"
VM_PASSWORD="i1sS4UMRi7FXnDy9"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Git Authentication Setup for Yahoo Services VM                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}This script will help you setup Git credentials on the VM.${NC}"
echo ""

# Step 1: Check if sshpass is available
echo -e "${YELLOW}[1/4]${NC} Checking prerequisites..."
if ! command -v sshpass &> /dev/null; then
    echo -e "${RED}❌ sshpass not found${NC}"
    echo -e "${YELLOW}Install it with: brew install sshpass${NC}"
    exit 1
fi
echo -e "${GREEN}✅ sshpass is available${NC}"
echo ""

# Step 2: Generate GitHub token
echo -e "${YELLOW}[2/4]${NC} GitHub Personal Access Token"
echo -e "${CYAN}──────────────────────────────────────────────────────────────────${NC}"
echo ""
echo -e "${GREEN}1. Open this URL in your browser:${NC}"
echo -e "   ${CYAN}https://github.com/settings/tokens/new${NC}"
echo ""
echo -e "${GREEN}2. Fill in the form:${NC}"
echo -e "   Note: ${CYAN}Yahoo Services VM Deployment${NC}"
echo -e "   Expiration: ${CYAN}90 days${NC}"
echo -e "   Scopes: ${CYAN}✅ repo (all)${NC}"
echo ""
echo -e "${GREEN}3. Click 'Generate token'${NC}"
echo ""
echo -e "${GREEN}4. Copy the token (starts with ghp_...)${NC}"
echo -e "   ${RED}⚠️  You won't be able to see it again!${NC}"
echo ""
read -p "Press ENTER when you have the token ready..."
echo ""

# Step 3: Get the token
echo -e "${YELLOW}[3/4]${NC} Enter your GitHub token"
echo -e "${CYAN}──────────────────────────────────────────────────────────────────${NC}"
echo ""
read -sp "Paste your GitHub token here (hidden): " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ No token provided${NC}"
    exit 1
fi

if [[ ! $GITHUB_TOKEN == ghp_* ]]; then
    echo -e "${YELLOW}⚠️  Warning: Token doesn't start with 'ghp_' - are you sure it's correct?${NC}"
    read -p "Continue anyway? (y/n): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Token received${NC}"
echo ""

# Step 4: Setup Git on VM
echo -e "${YELLOW}[4/4]${NC} Configuring Git on VM..."
echo -e "${CYAN}──────────────────────────────────────────────────────────────────${NC}"
echo ""

sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" << ENDSSH
set -e

echo "Configuring Git..."
git config --global user.name "Ashok Kumar"
git config --global user.email "ashok@example.com"
git config --global credential.helper store

echo "Creating credentials file..."
mkdir -p ~/.git-credentials
echo "https://ashok1995:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

echo "Testing Git access..."
if [ -d "/opt/yahoo-services" ]; then
    echo "Repository already exists, pulling latest..."
    cd /opt/yahoo-services
    git pull origin main 2>&1 | head -5
else
    echo "Cloning repository..."
    cd /opt
    git clone https://github.com/ashok1995/yahoo-services.git 2>&1 | head -10
fi

echo ""
echo "✅ Git authentication configured successfully!"
ENDSSH

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Git Authentication Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Deploy to production: ${YELLOW}./deploy-vm-prod.sh${NC}"
echo -e "  2. Verify health: ${YELLOW}curl http://203.57.85.72:8185/health${NC}"
echo ""
echo -e "${CYAN}The VM can now pull code from GitHub without prompting for credentials.${NC}"
echo ""
