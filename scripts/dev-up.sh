#!/usr/bin/env sh
set -eu

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example to .env and replace local-only credentials."
  exit 1
fi

set -a
. ./.env
set +a

docker compose -f infra/docker-compose.yml up -d
echo "Waiting for PostgreSQL..."
until docker compose -f infra/docker-compose.yml exec -T postgres pg_isready -U "${POSTGRES_USER:-parcham}" -d "${POSTGRES_DB:-parcham}" >/dev/null 2>&1; do
  sleep 1
done

./scripts/dev-seed-keycloak.sh

cd backend
alembic upgrade head
python -m app.seed

echo "Parcham dependencies are ready."
echo "Run backend: cd backend && uvicorn app.main:app --reload"
echo "Run frontend: cd frontend && npm install && npm run dev"
