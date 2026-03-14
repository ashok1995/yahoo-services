#!/usr/bin/env bash
# Dev: run server locally (no Docker). Uses envs/env.dev. Port from config (e.g. 8085).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
if [ ! -f envs/env.dev ]; then
  echo "Missing envs/env.dev"
  exit 1
fi
echo "Starting dev server from $REPO_ROOT (no Docker)..."
exec python main.py
