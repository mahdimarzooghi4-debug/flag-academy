#!/usr/bin/env sh
# Isolated GitHub Actions identity, never for production or reusable Academy users.
set -eu
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?}"
: "${PARCHAM_DEV_SOURCE_REVIEWER_PASSWORD:?}"

COMPOSE="docker compose -f infra/docker-compose.yml"
KCADM="/opt/keycloak/bin/kcadm.sh"
$COMPOSE exec -T keycloak "$KCADM" config credentials \
  --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
$COMPOSE exec -T keycloak "$KCADM" create users -r parcham \
  -s id=55555555-5555-5555-5555-555555555555 \
  -s username=assessor-reviewer -s enabled=true >/dev/null
$COMPOSE exec -T keycloak "$KCADM" set-password -r parcham \
  --username assessor-reviewer --new-password "$PARCHAM_DEV_SOURCE_REVIEWER_PASSWORD"
