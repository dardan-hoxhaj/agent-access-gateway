# Runbook

For the local Docker Compose stack (`make up`). Every gateway response carries a `request_id`, and every allow or deny writes one JSON audit line with the same `request_id` and a `reason`. Start from that line.

```bash
docker compose logs gateway | grep '<request_id>'
```

## An agent gets 403 it should not get

The audit line says `"decision":"deny"`. Read `reason`.

**`reason: policy_deny`** means OPA answered and said no.

1. Note `agent_id`, `tool`, and `action` from the audit line.
2. Ask OPA directly with the same input:
   ```bash
   curl -s localhost:8181/v1/data/agent/authz/allow \
     -d '{"input":{"agent_id":"ticket-agent","tool":"tickets","action":"read"}}'
   ```
   `{"result":true}` means the grant exists. `{"result":false}` means it does not.
3. Check `policies/data.json`. A grant exists only when `agents.<agent_id>.<tool>.<action>` is `true`. A typo in the agent, tool, or action name is a deny.
4. Check `agent_id`. The gateway reads it from the token's `azp` claim, which is the Keycloak client id. A token from a different client is a different agent.
5. If the grant is missing and should exist, add it to `data.json`, run `opa test policies/ -v`, and restart OPA (`docker compose restart opa`). Do not change `default allow := false`.

**`reason: opa_unavailable`** means the gateway could not reach OPA, so it failed closed (denied on purpose).

1. `docker compose ps opa`. Is it running?
2. `docker compose logs opa`. A Rego syntax error stops the policies from loading.
3. `curl -s localhost:8181/health` should return `{}`.
4. Fix OPA, then retry the call. Do not make the gateway allow when OPA is down.

## Every call returns 401

The audit line has `agent_id: null` because the token was rejected before an agent was known. Read `reason`.

| reason | Meaning | Check |
|---|---|---|
| `missing_bearer` | No `Authorization: Bearer ...` header | The client's request headers |
| `malformed_token` | Not a JWT | Is the client sending the access token, not the whole JSON response? |
| `unsupported_algorithm` | Token not signed with an allowed algorithm | Keycloak realm signing keys |
| `jwks_unavailable` | Gateway could not fetch Keycloak's signing keys | `docker compose ps keycloak`; Keycloak takes about a minute to start |
| `invalid_token` | Signature, issuer, audience, or expiry failed | See below |

For `invalid_token`, decode the token's payload (the middle part, base64) and compare:

1. `iss` must equal the gateway's `ISSUER`. If every call fails, this is the first suspect. See "What broke" in the README: `ISSUER` and `KEYCLOAK_URL` are different on purpose.
2. `aud` must include `agent-gateway`.
3. `exp` must be in the future. Tokens last 5 minutes; get a new one.

## Escalate when

- `policy_deny` for a grant that is in `data.json` and `opa eval` returns true. That is a gateway bug.
- `invalid_token` with matching `iss`, `aud`, and a future `exp`. Check whether Keycloak rotated its keys.
