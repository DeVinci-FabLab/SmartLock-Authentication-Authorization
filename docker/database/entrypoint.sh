#!/bin/sh

# Appliquer les migrations Alembic
echo "Applying database migrations..."
uv run alembic upgrade head

# Démarrer l'API
echo "Starting the API..."
exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000