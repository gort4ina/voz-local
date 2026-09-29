#!/usr/bin/env bash
# Reconstrói e recria o container do frontend garantindo que o Docker sirva a última versão.
# Uso: ./scripts/rebuild-frontend.sh [--no-cache]

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Rebuild frontend (Docker)"

if [[ "${1:-}" == "--no-cache" ]]; then
    docker compose build --no-cache frontend
else
    docker compose build --pull frontend
fi

docker compose up -d --force-recreate --no-deps frontend

sleep 2
docker compose ps --format "{{.Name}} {{.Status}}" | grep frontend || true

echo ""
echo "==> Frontend recriado. Abra http://127.0.0.1:8081"
echo "==> Faça Ctrl+F5 no navegador para descartar cache local."
