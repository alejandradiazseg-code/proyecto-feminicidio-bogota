#!/usr/bin/env bash
# Levanta el observatorio en local:
#   - Backend FastAPI  → http://localhost:8000  (documentación en /docs)
#   - Página web       → http://localhost:5500
# Detener: Ctrl+C (cierra ambos procesos).
set -e
cd "$(dirname "$0")"

python3 -m uvicorn backend.main:app --port 8000 --reload &
BACK=$!
python3 -m http.server 5500 --directory frontend >/dev/null 2>&1 &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null' EXIT INT TERM

# Esperar a que responda la API antes de abrir el navegador
for _ in $(seq 1 30); do
    curl -s -o /dev/null http://localhost:8000/api/zonas && break
    sleep 0.5
done

echo ""
echo "  Observatorio listo:  http://localhost:5500"
echo "  API:                 http://localhost:8000/docs"
echo "  (Ctrl+C para detener)"
xdg-open http://localhost:5500 >/dev/null 2>&1 || true
wait
