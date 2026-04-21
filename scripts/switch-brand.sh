#!/usr/bin/env bash
# ================================================================
# switch-brand.sh — переключение активного бренда для freemium-стека.
#
# Два бренда живут в одной кодовой базе: "propitashka" (для конкурса)
# и "profit" (публичный). Переключение меняет:
#   1. .env.freemium: BRAND=, NEXT_PUBLIC_BRAND=
#   2. Пересобирает frontend_freemium (логотип, title, favicon статичны)
#   3. Рестартует backend_freemium (бренд в AI-промптах и боте)
#
# Использование:
#   ./scripts/switch-brand.sh profit
#   ./scripts/switch-brand.sh propitashka
#
# Время переключения: ~2-3 минуты (из них frontend-rebuild ~2 мин).
# ================================================================

set -euo pipefail

BRAND="${1:-}"
if [[ "$BRAND" != "profit" && "$BRAND" != "propitashka" ]]; then
  echo "Usage: $0 {profit|propitashka}" >&2
  echo "Current .env.freemium:" >&2
  grep -E '^(BRAND|NEXT_PUBLIC_BRAND)=' .env.freemium 2>/dev/null || echo "  (нет .env.freemium)" >&2
  exit 1
fi

ENV_FILE=".env.freemium"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found. Run from repo root." >&2
  exit 1
fi

echo "→ switching brand to: $BRAND"

# 1. Правим env. BSD-sed и GNU-sed совместимо.
if grep -q '^BRAND=' "$ENV_FILE"; then
  sed -i.bak "s/^BRAND=.*/BRAND=$BRAND/" "$ENV_FILE"
else
  printf '\nBRAND=%s\n' "$BRAND" >> "$ENV_FILE"
fi
if grep -q '^NEXT_PUBLIC_BRAND=' "$ENV_FILE"; then
  sed -i.bak "s/^NEXT_PUBLIC_BRAND=.*/NEXT_PUBLIC_BRAND=$BRAND/" "$ENV_FILE"
else
  printf 'NEXT_PUBLIC_BRAND=%s\n' "$BRAND" >> "$ENV_FILE"
fi
rm -f "${ENV_FILE}.bak"

echo "  ✓ env updated"
grep -E '^(BRAND|NEXT_PUBLIC_BRAND)=' "$ENV_FILE"

# 2. Пересобираем frontend (brand fixed at build time).
echo "→ rebuilding frontend_freemium (this takes ~2 minutes)..."
docker compose -p propitashka-freemium \
  --env-file "$ENV_FILE" \
  -f docker-compose.freemium.yml \
  up -d --build frontend

# 3. Рестартуем backend (brand reads from env on every request, ~5s).
echo "→ restarting backend_freemium..."
docker compose -p propitashka-freemium \
  --env-file "$ENV_FILE" \
  -f docker-compose.freemium.yml \
  restart backend

# 4. Smoke-test: читаем /api/brand и проверяем соответствие.
echo "→ waiting for backend to come back (~10s)..."
sleep 10
ACTUAL=$(curl -fsS "http://127.0.0.1:8102/api/brand" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "?")
if [[ "$ACTUAL" == "$BRAND" ]]; then
  echo "  ✓ backend reports brand=$ACTUAL"
else
  echo "  ✗ backend reports brand=$ACTUAL (expected $BRAND). Check logs." >&2
  exit 2
fi

echo "✓ done. Active brand: $BRAND"
