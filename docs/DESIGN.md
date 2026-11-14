# Design choices

## Identity: Keycloak, client credentials

Each agent is its own Keycloak client. The gateway uses the `azp` (authorized party) claim as the agent id. Tokens last 300 seconds.

**Why Keycloak instead of Okta:** it runs in Docker with no tenant signup, so anyone can reproduce the demo. Okta is fine for a real org; it is the wrong default for a public, local portfolio project.

**Tradeoff:** Keycloak in `start-dev` is not a production IdP. The realm export is the source of truth for the demo clients.

## Authorization: OPA, deny by default

Policies live in Rego. `default allow = false`. A grant exists only when `data.agents[agent][tool][action] == true`.

**Why OPA instead of Cedar:** OPA is widely used in cloud-native and Kubernetes environments, and `opa test` is a first-class unit-test story. Cedar is strong; the testing and local-run story for OPA was the deciding factor for this project.

**Tradeoff:** the policy data is a static JSON file. A real system would load grants from a store and version them.

## Fail closed

If the gateway cannot reach OPA, the request is denied. If JWKS cannot be fetched, the token is rejected. The audit log records the reason in both cases.

## Audit

Every allow and deny writes one JSON line to stdout. The token and any Authorization header are stripped. The request id is a UUID so a log line can be correlated without leaking credentials.

## Terraform

The module creates an ECR repository and a GitHub OIDC role that can push to it. It is validate/plan only in CI; not applied. Applying it would create real AWS resources.

## What was cut

- No real ticket or billing service. The handlers are in-process mocks.
- No token revocation. Expiry is the only time bound.
- No multi-region or multi-cluster story.
