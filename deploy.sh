#!/usr/bin/env bash
# Deploy script for PROpitashka -> root@82.38.66.177:/opt/propitashka
# Uses isolated docker compose project to coexist with existing stacks.
set -euo pipefail

SSH_KEY="${SSH_KEY:-$HOME/.ssh/propitashka_deploy}"
SERVER="${SERVER:-root@82.38.66.177}"
REMOTE_DIR="${REMOTE_DIR:-/opt/propitashka}"
PROJECT_NAME="propitashka"

cd "$(dirname "$0")"

echo "==> 1. Ensure remote dir"
ssh -i "$SSH_KEY" "$SERVER" "mkdir -p $REMOTE_DIR"

echo "==> 2. Rsync project to $SERVER:$REMOTE_DIR"
rsync -az --delete \
  -e "ssh -i $SSH_KEY" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude '*.log' \
  --exclude '.DS_Store' \
  --exclude 'terminals' \
  --exclude 'agent-transcripts' \
  --exclude '.env' \
  --exclude '.env.prod' \
  --exclude '.env.prod.bak' \
  ./ "$SERVER:$REMOTE_DIR/"

echo "==> 3. Build & start containers (project=$PROJECT_NAME)"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker compose -p $PROJECT_NAME --env-file .env.prod -f docker-compose.prod.yml up -d --build"

echo "==> 4. Wait for backend healthcheck"
ssh -i "$SSH_KEY" "$SERVER" "for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  s=\$(docker inspect -f '{{.State.Health.Status}}' propitashka-backend 2>/dev/null || echo 'pending');
  echo \"backend health: \$s\";
  [ \"\$s\" = 'healthy' ] && break;
  sleep 5;
done"

echo "==> 5. Status"
ssh -i "$SSH_KEY" "$SERVER" "docker compose -p $PROJECT_NAME -f $REMOTE_DIR/docker-compose.prod.yml ps"

echo "==> Done. Frontend: http://82.38.66.177:3200"
