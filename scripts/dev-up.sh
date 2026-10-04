#!/usr/bin/env sh
set -eu

docker compose -f infra/docker-compose.yml up -d
echo "Waiting for PostgreSQL..."
until docker compose -f infra/docker-compose.yml exec -T postgres pg_isready -U parcham -d parcham >/dev/null 2>&1; do
  sleep 1
done

cd backend
alembic upgrade head
python -m app.seed

echo "Parcham dependencies are ready."
echo "Run backend: cd backend && uvicorn app.main:app --reload"
echo "Run frontend: cd frontend && npm install && npm run dev"
