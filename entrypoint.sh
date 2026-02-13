#!/bin/bash
# Entrypoint script for yahoo-services
# Loads correct environment file based on ENVIRONMENT variable

set -e

# Default to development if not set
ENVIRONMENT=${ENVIRONMENT:-development}

echo "🚀 Starting yahoo-services in $ENVIRONMENT mode..."

# Load appropriate environment file
case "$ENVIRONMENT" in
  development)
    ENV_FILE="envs/env.dev"
    ;;
  staging)
    ENV_FILE="envs/env.stage"
    ;;
  production)
    ENV_FILE="envs/env.prod"
    ;;
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Valid values: development, staging, production"
    exit 1
    ;;
esac

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Environment file not found: $ENV_FILE"
  exit 1
fi

echo "✅ Loading environment from: $ENV_FILE"

# Export variables from env file
set -a
source "$ENV_FILE"
set +a

# Start the application
echo "🎯 Starting server on port $SERVICE_PORT..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${SERVICE_PORT}" \
  --log-level "${LOG_LEVEL,,}" \
  "$@"
