#!/bin/sh
set -e
if [ -z "${ADMIN_EMAIL:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
  echo "error: ADMIN_EMAIL and ADMIN_PASSWORD must be set for bootstrap (GitHub secrets / docker -e)." >&2
  exit 1
fi
python /app/seed_admin.py
exec "$@"
