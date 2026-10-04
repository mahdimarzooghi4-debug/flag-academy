#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=10000}"
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?KC_BOOTSTRAP_ADMIN_USERNAME is required}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?KC_BOOTSTRAP_ADMIN_PASSWORD is required}"
: "${PARCHAM_STAGE_CANDIDATE_PASSWORD:?PARCHAM_STAGE_CANDIDATE_PASSWORD is required}"
: "${PARCHAM_STAGE_INSTRUCTOR_PASSWORD:?PARCHAM_STAGE_INSTRUCTOR_PASSWORD is required}"

echo "Starting Parcham Stage Keycloak on port $PORT"
/opt/keycloak/bin/kc.sh start-dev --http-port="$PORT" --import-realm &
KC_PID=$!

until /opt/keycloak/bin/kcadm.sh config credentials   --server "http://127.0.0.1:$PORT"   --realm master   --user "$KC_BOOTSTRAP_ADMIN_USERNAME"   --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null 2>&1; do
  if ! kill -0 "$KC_PID" 2>/dev/null; then
    wait "$KC_PID"
    exit 1
  fi
  sleep 2
done

/opt/keycloak/bin/kcadm.sh set-password   -r parcham --username candidate --new-password "$PARCHAM_STAGE_CANDIDATE_PASSWORD"
/opt/keycloak/bin/kcadm.sh set-password   -r parcham --username instructor --new-password "$PARCHAM_STAGE_INSTRUCTOR_PASSWORD"

wait "$KC_PID"
