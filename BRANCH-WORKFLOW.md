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

### 6. Deploy to **production (VM)** — only from `main` (no image transfer)

After the PR is merged to main:

- **From your Mac:** run `./deploy-vm-prod.sh` — it SSHs to the VM, then on the VM: **git pull origin main**, **build image there**, and start containers. No image is built or transferred from your machine.
- **On the VM:** you can also run `./deploy-vm-prod.sh` from `/opt/yahoo-services` (same steps: pull main, build on VM, up).

```bash
# From local (triggers VM to pull main + build on VM)
./deploy-vm-prod.sh

# Optional: force full rebuild on VM
./deploy-vm-prod.sh --no-cache
```

- Production **always** uses **main** on the VM. The VM pulls main and builds the image on the VM for reliability (single source of truth: git).

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

- **Health (from your Mac):** `curl http://203.57.85.72:8185/health`
- If "Connection refused" or timeout: on the VM, ensure port **8185** is open (e.g. `ufw allow 8185` if using ufw, or open in cloud firewall).
- On VM, health from inside: `curl -s http://localhost:8185/health | jq .`
