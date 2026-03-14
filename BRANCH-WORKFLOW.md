# Branch & Deployment Workflow

**Follow this process every time. Do not work on `main` or `develop` directly.**

**Merge only via remote UI (GitHub Pull Requests).** Do not merge from the command line (`git merge` / `git push` to develop or main).

---

## Branches

| Branch | Use | Where |
|--------|-----|--------|
| **feature/xxx** or **bugfix/xxx** | All code changes | Push to remote, open PR |
| **develop** | Integration, staging | Staging (local port 8285); only updated by merging PRs in UI |
| **main** | Production only | VM only; only updated by merging PRs in UI |

---

## Standard Process (every change)

### 1. Create a feature branch from `develop`

```bash
git checkout develop
git pull origin develop
git checkout -b feature/short-description   # or bugfix/xxx
```

### 2. Make changes, test, commit, push branch

```bash
git add .
git commit -m "feat: or fix: description"
git push -u origin feature/short-description
```

### 3. Merge to `develop` — **only via GitHub UI (Pull Request)**

- On GitHub: open **Pull Request**: base `develop` ← head `feature/short-description`.
- Review and merge the PR in the UI.
- Do **not** run `git merge` or `git push origin develop` from the command line.

After merge, update your local develop:

```bash
git checkout develop
git pull origin develop
```

### 4. Deploy to **staging** (local, port 8285) — always before prod

```bash
git checkout develop
git pull origin develop
./deploy-stage.sh          # or ./deploy-stage.sh -b for background
curl http://localhost:8285/health | jq .
```

- Staging uses branch **develop**. If staging fails, fix on a new feature branch → open PR to develop → merge in UI → pull develop → redeploy stage.

### 5. When staging is OK: merge `develop` → `main` — **only via GitHub UI (Pull Request)**

- On GitHub: open **Pull Request**: base `main` ← head `develop`.
- Review and merge the PR in the UI.
- Do **not** run `git merge` or `git push origin main` from the command line.

### 6. CI & Deploy to **production (VM)**

**CI (GitHub Actions):** On every push to `main`, the image is built and pushed to GHCR (`ghcr.io/ashok1995/yahoo-services:main`). Triggered by merge or direct push to main.

**Deploy (manual):**

- **From your Mac:** run `./deploy-vm-prod.sh` — SSHs to VM, pulls compose from main, **pulls pre-built image from GHCR**, and starts containers.
- **On the VM:** run `./deploy-vm-prod.sh` from `/opt/yahoo-services` (same steps).

```bash
# From local (VM pulls image from GHCR)
./deploy-vm-prod.sh
```

- For **private** GHCR package, set `GHCR_TOKEN` on the VM (GitHub PAT with `read:packages`).

---

## Quick reference

```
feature/xxx  →  PR (UI) → develop  →  staging (:8285)  →  PR (UI) → main  →  deploy VM
     ↑                    ↑                                    ↑
  push branch        merge in GitHub                      merge in GitHub
  open PR            then pull develop                    then pull main, deploy
```

---

## Rules (strict)

- **Never** commit directly on `main` or `develop`.
- **Merge only via remote UI:** use Pull Requests to update `develop` and `main`; no command-line merge/push to those branches.
- **Never** deploy to VM from a feature branch; always from `main` after pulling.
- **Always** test on staging (develop) before opening PR from develop to main.

---

## Production health & firewall

- **Health (from your Mac):** `curl http://203.57.85.201:8185/health`
- If "Connection refused" or timeout: on the VM, ensure port **8185** is open (e.g. `ufw allow 8185` if using ufw, or open in cloud firewall).
- On VM, health from inside: `curl -s http://localhost:8185/health | jq .`
