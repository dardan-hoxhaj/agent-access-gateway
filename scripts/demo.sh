#!/usr/bin/env bash
# Three-case demo: allow, deny (wrong agent), invalid token.
set -euo pipefail

KC="${KEYCLOAK_URL:-http://localhost:8080}"
GW="${GATEWAY_URL:-http://localhost:8000}"
REALM="agent-gateway"

get_token() {
  local client_id="$1" secret="$2"
  curl -sS -X POST "${KC}/realms/${REALM}/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=${client_id}" \
    -d "client_secret=${secret}" \
    -d "audience=agent-gateway" | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
}

echo "=== 1. Allowed: ticket-agent reads tickets ==="
TOKEN=$(get_token ticket-agent ticket-agent-secret)
curl -sS -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer ${TOKEN}" "${GW}/tools/tickets"

echo
echo "=== 2. Denied: billing-agent tries tickets ==="
TOKEN=$(get_token billing-agent billing-agent-secret)
curl -sS -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer ${TOKEN}" "${GW}/tools/tickets"

echo
echo "=== 3. Invalid token ==="
# Intentionally not a JWT. The string is a placeholder, not a credential.
curl -sS -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer clearly-invalid" "${GW}/tools/tickets"
