# Deployment — Single source of truth

Three environments. **Dev** = local server (no Docker). **Staging** and **Prod** = run from Docker image from GHCR only (no local build).

| Environment | Where        | How to run                          | Image / server      |
|-------------|--------------|-------------------------------------|---------------------|
| **Dev**     | Local        | `./deploy/run-dev.sh`               | No image — run app with Python/uvicorn |
| **Staging** | Local        | `./deploy/run-stage.sh`             | `ghcr.io/ashok1995/yahoo-services:stage` |
| **Prod**    | VM           | On VM: `./deploy/run-prod.sh`       | `ghcr.io/ashok1995/yahoo-services:latest` |

Images are built in CI only: **develop** → `:stage`, **main** → `:latest`. Never build images locally for staging/prod; always pull from GHCR.

---

## Dev (local server, no Docker)

- Port: from `envs/env.dev` (e.g. 8085).
- No image: run the app directly (Poetry/uvicorn or `python main.py`).

```bash
./deploy/run-dev.sh
```

Requires: Python, deps installed (`pip install -r requirements.txt` or Poetry), Redis (optional; app can run without it). Uses `envs/env.dev`.

---

## Staging (local, Docker image from GHCR)

- Port: **8285**.
- Image: `ghcr.io/ashok1995/yahoo-services:stage` (pushed on merge to **develop**).

```bash
./deploy/run-stage.sh
```

Pulls `:stage` and starts app + Redis via `deploy/docker-compose.stage.yml`. Run from **repo root**. If repo is private: `docker login ghcr.io -u USER -p PAT` first.

---

## Prod (VM, Docker image from GHCR)

- Port: **8185**.
- Image: `ghcr.io/ashok1995/yahoo-services:latest` (pushed on merge to **main**).

**On the VM** (after clone or pull of this repo):

```bash
./deploy/run-prod.sh
```

Pulls `:latest` and starts app + Redis via `deploy/docker-compose.prod.yml`. Run from **repo root** on the VM. If repo is private: on the VM, `docker login ghcr.io -u USER -p PAT` first.

---

## File layout

```
deploy/
  README.md                 # This file
  docker-compose.stage.yml # Staging stack (image :stage, port 8285)
  docker-compose.prod.yml  # Prod stack (image :latest, port 8185)
  run-dev.sh               # Start dev server (no Docker)
  run-stage.sh             # Pull :stage + compose up (local)
  run-prod.sh              # Pull :latest + compose up (on VM)
envs/
  env.dev   # Dev config
  env.stage # Staging config
  env.prod  # Prod config
```

All compose and scripts assume they are run from the **repository root** (paths like `envs/env.stage` and `./logs` are relative to repo root).

**Verify after deploy:** `python scripts/verify_global_context.py http://localhost:8285` (staging) or `http://localhost:8185` (prod).
