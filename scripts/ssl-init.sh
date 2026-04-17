#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> <email>}"
EMAIL="${2:?Usage: $0 <domain> <email>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== SSL Certificate Setup for $DOMAIN ==="

echo "[1/3] Ensuring nginx is running on port 80..."
docker compose up -d nginx

echo "[2/3] Obtaining certificate from Let's Encrypt..."
docker run --rm \
  -v "$(docker volume inspect propitashka_certbot_conf -f '{{.Mountpoint}}' 2>/dev/null || echo certbot_conf):/etc/letsencrypt" \
  -v "$(docker volume inspect propitashka_certbot_www -f '{{.Mountpoint}}' 2>/dev/null || echo certbot_www):/var/www/certbot" \
  --network host \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "[3/3] Certificate obtained. Now:"
echo "  1. Edit nginx/nginx.conf — uncomment the SSL server block"
echo "  2. Replace 'your-domain.com' with '$DOMAIN'"
echo "  3. Run: docker compose restart nginx"
echo ""
echo "Auto-renewal cron (add to crontab):"
echo "  0 3 * * * cd $PROJECT_DIR && docker run --rm -v certbot_conf:/etc/letsencrypt -v certbot_www:/var/www/certbot certbot/certbot renew --quiet && docker compose restart nginx"
