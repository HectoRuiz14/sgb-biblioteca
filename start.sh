#!/usr/bin/env bash
set -e

echo "Ejecutando migraciones de Alembic..."
alembic upgrade head

echo "Iniciando la aplicación con Uvicorn..."
exec uvicorn sgb.main:app --host 0.0.0.0 --port 8000
