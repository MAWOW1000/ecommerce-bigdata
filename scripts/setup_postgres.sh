#!/usr/bin/env bash
# Tao role + database cho do an. Can sudo vi PostgreSQL dung peer auth.
set -euo pipefail

DB_USER="${DB_USER:-ecom}"
DB_PASS="${DB_PASS:-ecom_pass}"
DB_NAME="${DB_NAME:-ecommerce_db}"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}' CREATEDB;
  END IF;
END
\$\$;
SQL

if ! sudo -u postgres psql -lqt | cut -d'|' -f1 | grep -qw "${DB_NAME}"; then
  sudo -u postgres createdb -O "${DB_USER}" -E UTF8 "${DB_NAME}"
  echo ">> Da tao database ${DB_NAME} (owner: ${DB_USER})"
else
  echo ">> Database ${DB_NAME} da ton tai."
fi

PGPASSWORD="${DB_PASS}" psql -h 127.0.0.1 -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT version();"
