#!/usr/bin/env bash
# Server Organisms - one-command install (Linux/macOS). Your data stays on your server.
set -euo pipefail
command -v docker >/dev/null || { echo "Docker required: https://docs.docker.com/get-docker/"; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose v2 required"; exit 1; }
[ -f .env ] || cp .env.example .env
# Generate a private broker token on first install (never commit .env)
if grep -q "demo-broker-token" .env 2>/dev/null || ! grep -q "^BROKER_TOKEN=" .env; then
  TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(24))" 2>/dev/null || openssl rand -hex 24)
  printf "\nBROKER_TOKEN=%s\n" "$TOKEN" >> .env
  echo "Generated private BROKER_TOKEN in .env (keep secret)"
fi
docker compose up --build -d
TOK=$(grep "^BROKER_TOKEN=" .env | head -1 | cut -d= -f2-)
echo ""
echo "OPEN YOUR DASHBOARD (judge/demo link, contains your private token - do not share publicly):"
echo "http://127.0.0.1:18000/?token=$TOK"
echo "(Optional: set META_API_KEY in .env for live Muse, then: docker compose up -d)"
