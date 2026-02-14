# Branch & Deployment Workflow

**Follow this process every time. Do not work on `main` or `develop` directly.**

---

## Branches

| Branch | Use | Where |
|--------|-----|--------|
| **feature/xxx** or **bugfix/xxx** | All code changes | Local only |
| **develop** | Integration, staging | Local staging (port 8285) |
| **main** | Production only | **VM only** — never develop on main locally |

---

## Standard Process (every change)

### 1. Create a feature branch from `develop`

```bash
git checkout develop
git pull origin develop
git checkout -b feature/short-description   # or bugfix/xxx
```

### 2. Make changes, test, commit on the feature branch

```bash
# work, test, then:
git add .
git commit -m "feat: or fix: description"
```

### 3. Merge to `develop` (no direct commits to develop)

```bash
git checkout develop
git pull origin develop
git merge feature/short-description
git push origin develop
```

### 4. Deploy to **staging** (local, port 8285) — always before prod

```bash
git checkout develop
./deploy-stage.sh          # or ./deploy-stage.sh -b for background
curl http://localhost:8285/health | jq .
# Test your endpoints on staging
```

- Staging **always** uses branch **develop**.
- If staging fails, fix on a new feature branch → merge to develop → redeploy stage. **Do not deploy to production until staging is OK.**

### 5. When staging is OK: merge `develop` → `main` (for production only)

```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```

### 6. Deploy to **production (VM)** — only from `main`

```bash
git checkout main
git pull origin main
./deploy-vm-prod.sh       # builds from current dir (main), pushes image to VM
```

- Production **always** uses branch **main**.
- **Do not run `deploy-vm-prod.sh` from a feature branch.** Checkout main, then deploy.

---

## Quick reference

```
feature/xxx  →  develop  →  staging (local :8285)  →  main  →  VM prod (203.57.85.72:8185)
     ↑              ↑              ↑                      ↑              ↑
  you code      merge PR      test here              merge when     deploy only
  & commit                    before prod             staging OK    from main
```

---

## Rules (strict)

- **Never** commit directly on `main` or `develop`.
- **Never** deploy to VM from a feature branch; always from `main`.
- **Always** test on staging (develop) before merging to main and deploying to prod.
- **main** = production only. Local development and staging use **develop** and **feature/xxx**.

---

## Production health & firewall

- **Health (from your Mac):** `curl http://203.57.85.72:8185/health`
- If "Connection refused" or timeout: on the VM, ensure port **8185** is open (e.g. `ufw allow 8185` if using ufw, or open in cloud firewall).
- On VM, health from inside: `curl -s http://localhost:8185/health | jq .`
