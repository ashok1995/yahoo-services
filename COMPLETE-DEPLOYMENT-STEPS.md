# Complete Production VM Deployment - Step-by-Step Guide

**Target**: Deploy Yahoo Services to VM 203.57.85.72 on port 8185

---

## 📋 Pre-Deployment Checklist

### 1. Verify Branch Status

```bash
# Ensure you're on main branch (locally)
cd /Users/ashokkumar/Desktop/ashok-personal/stocks/yahoo-services
git checkout main
git pull origin main

# Verify main is up to date
git status
# Should show: "Your branch is up to date with 'origin/main'"
```

**Status**: ✅ Main branch has all changes (feature branch is outdated)

---

### 2. Prerequisites on Local Machine

```bash
# Check if sshpass is installed (for SSH automation)
which sshpass

# If not installed, install it:
brew install sshpass  # macOS
```

---

## 🔐 STEP 1: Setup Git Authentication on VM

The VM needs to pull code from GitHub. You have two options:

### Option A: Personal Access Token (Recommended)

**1.1 Generate GitHub Personal Access Token**

```bash
# On your local machine, go to:
# https://github.com/settings/tokens/new

# Settings:
- Note: "Yahoo Services VM Deployment"
- Expiration: 90 days (or as needed)
- Scopes: 
  ✅ repo (all)
  
# Click "Generate token"
# Copy the token (starts with ghp_...)
```

**1.2 Configure Git on VM with Token**

```bash
# SSH into VM
ssh root@203.57.85.72

# Configure Git
git config --global user.name "Ashok Kumar"
git config --global user.email "your-email@example.com"

# Store credentials (will prompt for username and password)
git config --global credential.helper store

# Clone repository (will ask for credentials once)
cd /opt
git clone https://github.com/ashok1995/yahoo-services.git

# When prompted:
# Username: ashok1995
# Password: [paste your GitHub token here]

# Credentials will be saved for future pulls
```

---

### Option B: SSH Key (Alternative)

**1.1 Generate SSH Key on VM**

```bash
# SSH into VM
ssh root@203.57.85.72

# Generate SSH key
ssh-keygen -t ed25519 -C "vm-yahoo-services"
# Press Enter for all prompts (use defaults)

# Display public key
cat ~/.ssh/id_ed25519.pub
# Copy this entire output
```

**1.2 Add SSH Key to GitHub**

```bash
# On your local machine, go to:
# https://github.com/settings/keys

# Click "New SSH key"
# Title: "VM 203.57.85.72 - Yahoo Services"
# Key: [paste the public key from VM]
# Click "Add SSH key"
```

**1.3 Clone with SSH on VM**

```bash
# On VM, test SSH connection
ssh -T git@github.com
# Should see: "Hi ashok1995! You've successfully authenticated..."

# Clone repository
cd /opt
git clone git@github.com:ashok1995/yahoo-services.git
```

---

## 🚀 STEP 2: Deploy to Production VM

### Option 1: Deploy from Local Machine (Easiest)

```bash
# On your local machine
cd /Users/ashokkumar/Desktop/ashok-personal/stocks/yahoo-services

# Run deployment script
./deploy-vm-prod.sh
```

**What happens:**
1. Script connects to VM via SSH (using sshpass)
2. Checks if repository exists at `/opt/yahoo-services`
3. If not, clones it (requires Git auth from Step 1)
4. Pulls latest from main branch
5. Builds Docker images
6. Starts containers
7. Verifies health

---

### Option 2: Deploy Directly on VM

```bash
# SSH into VM
ssh root@203.57.85.72

# Navigate to project (or clone if first time)
cd /opt/yahoo-services || git clone https://github.com/ashok1995/yahoo-services.git /opt/yahoo-services

# Checkout main and pull
cd /opt/yahoo-services
git checkout main
git pull origin main

# Run deployment script
./deploy-vm-prod.sh
```

---

## 🔍 STEP 3: Verify Deployment

### 3.1 Check Health Endpoint

```bash
# From local machine or VM
curl http://203.57.85.72:8185/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "yahoo-services",
  "yahoo_finance_available": true,
  "alpha_vantage_available": false,
  "timestamp": "2026-02-14T..."
}
```

---

### 3.2 Test Global Context Endpoint

```bash
curl http://203.57.85.72:8185/api/v1/global-context | jq .
```

**Expected**: JSON with sp500, nasdaq, dow_jones, vix, gold, usd_inr, crude_oil

---

### 3.3 Test Fundamentals Endpoint

```bash
curl -X POST http://203.57.85.72:8185/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS"]}' | jq .
```

---

### 3.4 Check Docker Containers

```bash
# SSH to VM
ssh root@203.57.85.72

# Check containers
docker ps --filter "name=yahoo"

# Expected output:
# CONTAINER ID   IMAGE                    STATUS
# xxxx           yahoo-services-prod      Up X minutes (healthy)
# xxxx           redis:7-alpine           Up X minutes
```

---

### 3.5 View Logs

```bash
# On VM
cd /opt/yahoo-services
docker compose -f docker-compose.prod.yml logs -f

# Or last 50 lines
docker compose -f docker-compose.prod.yml logs --tail=50
```

---

## 📊 STEP 4: Post-Deployment Checklist

Run these checks to ensure everything is working:

```bash
# 1. Health check
curl http://203.57.85.72:8185/health
# Status: ✅ Should return "healthy"

# 2. Global context
curl http://203.57.85.72:8185/api/v1/global-context
# Status: ✅ Should return 7 market indicators

# 3. Fundamentals
curl -X POST http://203.57.85.72:8185/api/v1/fundamentals/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["RELIANCE.NS", "TCS.NS"]}'
# Status: ✅ Should return P/E, P/B, market cap

# 4. API Documentation
open http://203.57.85.72:8185/docs
# Status: ✅ Should load Swagger UI

# 5. Check containers (on VM)
docker ps --filter "name=yahoo"
# Status: ✅ Both containers running and healthy

# 6. Check logs for errors (on VM)
docker compose -f docker-compose.prod.yml logs --tail=100 | grep -i error
# Status: ✅ No critical errors
```

---

## 🔧 Common Issues & Solutions

### Issue 1: Git Clone Fails - Authentication Error

**Symptoms:**
```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

**Solution:**
```bash
# On VM, setup Git credentials
git config --global credential.helper store

# Try cloning again, enter GitHub token when prompted
cd /opt
git clone https://github.com/ashok1995/yahoo-services.git
# Username: ashok1995
# Password: [your GitHub personal access token]
```

---

### Issue 2: Port 8185 Already in Use

**Symptoms:**
```
Error: Bind for 0.0.0.0:8185 failed: port is already allocated
```

**Solution:**
```bash
# On VM, find and kill process
lsof -i:8185
kill -9 <PID>

# Or stop existing yahoo services
cd /opt/yahoo-services
docker compose -f docker-compose.prod.yml down

# Redeploy
./deploy-vm-prod.sh
```

---

### Issue 3: Docker Not Running

**Symptoms:**
```
Cannot connect to the Docker daemon
```

**Solution:**
```bash
# On VM, start Docker
systemctl start docker
systemctl enable docker

# Verify Docker is running
docker ps
```

---

### Issue 4: sshpass Not Found (Local Machine)

**Symptoms:**
```
command not found: sshpass
```

**Solution:**
```bash
# On macOS
brew install sshpass

# On Ubuntu/Debian
sudo apt install sshpass

# Then retry deployment
./deploy-vm-prod.sh
```

---

### Issue 5: Git Pull Fails - Divergent Branches

**Symptoms:**
```
error: Your local changes to the following files would be overwritten by merge
```

**Solution:**
```bash
# On VM
cd /opt/yahoo-services

# Option A: Discard local changes
git reset --hard origin/main
git pull origin main

# Option B: Stash local changes
git stash
git pull origin main
git stash pop
```

---

## 🔄 STEP 5: Update Deployment (Future)

When you need to deploy updates:

```bash
# Method 1: Run deployment script (easiest)
./deploy-vm-prod.sh

# Method 2: Manual update on VM
ssh root@203.57.85.72
cd /opt/yahoo-services
git pull origin main
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 📝 Management Commands (On VM)

```bash
# View status
docker compose -f docker-compose.prod.yml ps

# View logs (follow)
docker compose -f docker-compose.prod.yml logs -f

# View logs (last 100 lines)
docker compose -f docker-compose.prod.yml logs --tail=100

# Restart service
docker compose -f docker-compose.prod.yml restart

# Stop service
docker compose -f docker-compose.prod.yml stop

# Start service
docker compose -f docker-compose.prod.yml start

# Full restart with rebuild
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Check resource usage
docker stats yahoo-services-prod yahoo-redis-prod

# Execute command in container
docker exec -it yahoo-services-prod /bin/bash

# Check Redis
docker exec -it yahoo-redis-prod redis-cli ping
```

---

## 🎯 Quick Reference

### URLs
```
Production API:  http://203.57.85.72:8185
Health:          http://203.57.85.72:8185/health
Global Context:  http://203.57.85.72:8185/api/v1/global-context
Fundamentals:    http://203.57.85.72:8185/api/v1/fundamentals/batch
API Docs:        http://203.57.85.72:8185/docs
```

### VM Details
```
Host:     203.57.85.72
User:     root
Password: i1sS4UMRi7FXnDy9
Location: /opt/yahoo-services
Port:     8185
```

### Key Files
```
Dockerfile:              docker-compose.prod.yml
Deployment Script:       deploy-vm-prod.sh
Environment Config:      envs/env.prod
```

---

## ✅ Complete Deployment Checklist

Use this checklist when deploying:

**Pre-Deployment:**
- [ ] On main branch locally
- [ ] Latest code pulled from GitHub
- [ ] sshpass installed (if deploying remotely)
- [ ] Git authentication setup on VM
- [ ] Docker running on VM
- [ ] Port 8185 available on VM

**Deployment:**
- [ ] Run `./deploy-vm-prod.sh`
- [ ] Script completes without errors
- [ ] Health endpoint returns "healthy"

**Verification:**
- [ ] Health check passes
- [ ] Global context endpoint working
- [ ] Fundamentals endpoint working
- [ ] API docs accessible
- [ ] Both Docker containers running
- [ ] No errors in logs

**Post-Deployment:**
- [ ] Monitor for 15 minutes
- [ ] Test from seed-stocks-service
- [ ] Update seed-stocks config to use 203.57.85.72:8185
- [ ] Document deployment in team notes

---

## 🎉 Summary

**Complete these steps in order:**

1. ✅ **Setup Git on VM** (one-time setup)
   - Generate GitHub token OR SSH key
   - Configure Git credentials on VM

2. ✅ **Run Deployment**
   ```bash
   ./deploy-vm-prod.sh
   ```

3. ✅ **Verify Service**
   ```bash
   curl http://203.57.85.72:8185/health
   curl http://203.57.85.72:8185/api/v1/global-context
   ```

4. ✅ **Monitor Logs**
   ```bash
   ssh root@203.57.85.72
   cd /opt/yahoo-services
   docker compose -f docker-compose.prod.yml logs -f
   ```

**That's it! Your service is now running on production VM.**

---

**Need Help?**
- Check logs: `docker compose -f docker-compose.prod.yml logs -f`
- Check containers: `docker ps --filter "name=yahoo"`
- Check health: `curl http://203.57.85.72:8185/health`
- Restart: `docker compose -f docker-compose.prod.yml restart`

---

Last Updated: 2026-02-14
