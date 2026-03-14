#!/usr/bin/env bash
# Production: pull image from GHCR and run. Port 8185. Run on VM from repo root.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
COMPOSE_FILE="deploy/docker-compose.prod.yml"
IMAGE="ghcr.io/ashok1995/yahoo-services:latest"
echo "Stopping and removing existing production containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
echo "Pulling $IMAGE..."
docker pull "$IMAGE"
echo "Starting production (port 8185)..."
docker compose -f "$COMPOSE_FILE" up -d
echo "Waiting for health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8185/health > /dev/null 2>&1; then
    echo "Production is up: http://localhost:8185"
    exit 0
  fi
  sleep 1
done
echo "Health check timeout. Logs: docker compose -f $COMPOSE_FILE logs -f"
exit 1
