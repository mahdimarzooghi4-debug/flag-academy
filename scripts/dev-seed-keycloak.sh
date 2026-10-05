#!/usr/bin/env sh
set -eu

: "${KC_BOOTSTRAP_ADMIN_USERNAME:?set KC_BOOTSTRAP_ADMIN_USERNAME}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?set KC_BOOTSTRAP_ADMIN_PASSWORD}"
: "${PARCHAM_DEV_CANDIDATE_PASSWORD:?set PARCHAM_DEV_CANDIDATE_PASSWORD}"
: "${PARCHAM_DEV_INSTRUCTOR_PASSWORD:?set PARCHAM_DEV_INSTRUCTOR_PASSWORD}"
: "${PARCHAM_DEV_ADMIN_PASSWORD:?set PARCHAM_DEV_ADMIN_PASSWORD}"

COMPOSE="docker compose -f infra/docker-compose.yml"
KCADM="/opt/keycloak/bin/kcadm.sh"

echo "Waiting for Keycloak..."
until $COMPOSE exec -T keycloak "$KCADM" config credentials   --server http://localhost:8080   --realm master   --user "$KC_BOOTSTRAP_ADMIN_USERNAME"   --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done

$COMPOSE exec -T keycloak "$KCADM" set-password   -r parcham --username candidate --new-password "$PARCHAM_DEV_CANDIDATE_PASSWORD"
$COMPOSE exec -T keycloak "$KCADM" set-password   -r parcham --username instructor --new-password "$PARCHAM_DEV_INSTRUCTOR_PASSWORD"
$COMPOSE exec -T keycloak "$KCADM" set-password   -r parcham --username academy-admin --new-password "$PARCHAM_DEV_ADMIN_PASSWORD"

echo "Development Keycloak users are ready."
