#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== PROpitashka Deploy ==="

# Check .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.production.example -> .env and fill values."
  exit 1
fi

echo "[1/4] Pulling latest images..."
docker compose pull postgres redis nginx

echo "[2/4] Building application images..."
docker compose build --no-cache backend frontend

echo "[3/4] Running database migrations..."
docker compose run --rm backend alembic upgrade head

echo "[4/4] Starting services..."
docker compose up -d

echo ""
echo "=== Deploy complete ==="
echo "Services status:"
docker compose ps
echo ""
echo "Logs: docker compose logs -f"
echo "Stop:  docker compose down"
