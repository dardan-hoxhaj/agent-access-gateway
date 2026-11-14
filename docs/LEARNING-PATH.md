# Rebuild path

Do these in order. After each step, you should be able to say why that piece exists.

1. **Policy first.** Write `policies/agent.rego` with `default allow = false` and one `allow` rule that reads `data.agents`. Write `policies/data.json` with two agents. Run `opa test policies/`. You should see the allow and deny cases pass. If you cannot explain why a missing action is a deny, stop and re-read the rule.

2. **JWT validation.** Generate a local RSA key. Write `gateway/auth.py` that loads JWKS, pins `RS256`, and checks `iss`, `aud`, and `exp`. Write `tests/test_auth.py` that signs tokens with the local key and covers expired, wrong issuer, wrong audience, and bad algorithm. Run `pytest tests/test_auth.py`.

3. **OPA client.** Write `gateway/opa.py`. On any HTTP or parse error, raise and let the caller deny. Write the three unit tests in `tests/test_opa.py`.

4. **Gateway.** Wire FastAPI routes for `/tools/tickets` and `/tools/billing`. Extract the bearer, validate, ask OPA, call the mock, and call `audit` on every path. Never put the token in the log. Write `tests/test_gateway.py` with the allow, deny, invalid, expired, and OPA-down cases.

5. **Keycloak realm.** Export or hand-write `keycloak/realm.json` with two confidential clients, client-credentials enabled, 300s token lifetime, and an audience mapper for `agent-gateway`.

6. **Compose.** Add Keycloak, OPA, and the gateway to `docker-compose.yml`. `make up`, wait for Keycloak, `make demo`. You should see one 200, one 403, and one 401.

7. **CI and Terraform.** Add the GitHub Actions workflow (ruff, pytest, opa test, docker build, Trivy, gitleaks, terraform fmt/validate). Write the ECR + OIDC module. Run `terraform fmt -check` and `terraform validate`. Do not apply.

8. **Docs.** Update the README so every command is one you actually ran. Note what you did not verify.

## ISSUER vs KEYCLOAK_URL

The first demo returned 401 on every call. The cause was an issuer mismatch.

Keycloak sets the token `iss` claim from the URL the client used. The demo script talks to `http://localhost:8080`, so the token carries `iss=http://localhost:8080/realms/agent-gateway`.

The gateway runs inside Docker. It fetches JWKS from the service name `http://keycloak:8080` (KEYCLOAK_URL), because `localhost` inside the container is the container itself, not the host.

Those two URLs are different hosts for the same Keycloak. If the gateway also uses KEYCLOAK_URL as the expected issuer, signature and audience can be fine and the token still fails the issuer check.

The fix is two env vars:

- `KEYCLOAK_URL` is the URL the gateway uses to fetch JWKS (internal, `http://keycloak:8080`).
- `ISSUER` is the issuer the client saw (`http://localhost:8080/realms/agent-gateway`).

Keep them separate. Changing one without the other brings the 401s back.
