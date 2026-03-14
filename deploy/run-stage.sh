#!/usr/bin/env bash
# Staging: pull image from GHCR and run. Port 8285. Run from repo root.
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
COMPOSE_FILE="deploy/docker-compose.stage.yml"
IMAGE="ghcr.io/ashok1995/yahoo-services:stage"
echo "Stopping and removing existing staging containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
echo "Pulling $IMAGE..."
docker pull "$IMAGE"
echo "Starting staging (port 8285)..."
docker compose -f "$COMPOSE_FILE" up -d
echo "Waiting for health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8285/health > /dev/null 2>&1; then
    echo "Staging is up: http://localhost:8285"
    exit 0
  fi
  sleep 1
done
echo "Health check timeout. Logs: docker compose -f $COMPOSE_FILE logs -f"
exit 1
