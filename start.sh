#!/usr/bin/env bash
set -euo pipefail

echo "[*] Initializing Smart Courier on Render Linux runtime..."

# Apply non-destructive Alembic migrations against persistent PostgreSQL
echo "[*] Applying database migrations to latest head..."
python -m flask --app wsgi.py db upgrade

# Ensure all nine roles, permissions, and essential courier catalog exist in PostgreSQL
echo "[*] Ensuring all nine roles, permissions, and essential courier catalog exist..."
python -m flask --app wsgi.py init-prod

# Optional idempotent administrator bootstrapping
if [ -n "${ADMIN_BOOTSTRAP_EMAIL:-}" ] && [ -n "${ADMIN_BOOTSTRAP_PASSWORD:-}" ]; then
    echo "[*] Running idempotent admin account check/bootstrap..."
    python -m flask --app wsgi.py bootstrap-admin
fi

# Optional idempotent viva 9-role demo accounts provisioning
if [ "${VIVA_SEED_DEMO_ACCOUNTS:-false}" = "true" ] || [ "${VIVA_LOGIN_PICKER_ENABLED:-false}" = "true" ]; then
    echo "[*] Ensuring all 9 viva demonstration accounts exist in database..."
    python -m flask --app wsgi.py seed-viva-accounts --confirm
fi

# Launch Gunicorn WSGI production server
echo "[*] Starting Gunicorn WSGI server on port ${PORT:-10000}..."
exec gunicorn \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app
