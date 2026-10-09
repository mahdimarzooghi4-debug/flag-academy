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
  -s username=assessor-reviewer -s enabled=true \
  -s email=assessor-reviewer@ci.parcham.invalid -s emailVerified=true \
  -s firstName=CI -s lastName=Reviewer >/dev/null
$COMPOSE exec -T keycloak "$KCADM" set-password -r parcham \
  --username assessor-reviewer --new-password "$PARCHAM_DEV_SOURCE_REVIEWER_PASSWORD"

# Keycloak owns generated OIDC subject IDs. Export the *actual* subject
# into the next isolated CI step; never assume that kcadm accepts client IDs.
subject=$($COMPOSE exec -T keycloak "$KCADM" get users -r parcham \
  -q username=assessor-reviewer --fields id,username | python3 -c '
import json, sys, uuid
users = json.load(sys.stdin)
assert len(users) == 1 and users[0]["username"] == "assessor-reviewer"
print(str(uuid.UUID(users[0]["id"])))
')
test -n "$subject"
echo "PARCHAM_CI_REVIEWER_SUBJECT=$subject" >> "$GITHUB_ENV"
