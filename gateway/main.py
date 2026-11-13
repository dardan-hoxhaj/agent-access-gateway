"""FastAPI gateway. Validates JWT, asks OPA, logs, then calls the mock tool."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from gateway.audit import audit
from gateway.auth import AuthError, JWKSClient
from gateway.opa import OPAClient, OPAError
from gateway import tools

app = FastAPI(title="agent-access-gateway", version="0.1.0")

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.environ.get("REALM", "agent-gateway")
AUDIENCE = os.environ.get("AUDIENCE", "agent-gateway")
OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")

jwks = JWKSClient(
    jwks_url=f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs",
    issuer=f"{KEYCLOAK_URL}/realms/{REALM}",
    audience=AUDIENCE,
)
opa = OPAClient(OPA_URL)

ROUTES = {
    ("GET", "/tools/tickets"): ("tickets", "read"),
    ("POST", "/tools/tickets"): ("tickets", "write"),
    ("GET", "/tools/billing"): ("billing", "read"),
}


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("missing_bearer")
    return authorization.split(" ", 1)[1].strip()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.api_route("/tools/{tool}", methods=["GET", "POST"])
async def gateway(tool: str, request: Request, authorization: str | None = Header(default=None)) -> Any:
    request_id = str(uuid.uuid4())
    action = "write" if request.method == "POST" else "read"
    route = (request.method, f"/tools/{tool}")
    if route not in ROUTES:
        audit("deny", None, tool, action, "unknown_route", request_id)
        raise HTTPException(status_code=404, detail="unknown_tool")

    try:
        token = _bearer(authorization)
        claims = jwks.validate(token)
        agent_id = jwks.agent_id(claims)
    except AuthError as exc:
        audit("deny", None, tool, action, str(exc), request_id)
        return JSONResponse(status_code=401, content={"detail": str(exc), "request_id": request_id})

    try:
        allowed = opa.allow(agent_id, tool, action)
    except OPAError:
        audit("deny", agent_id, tool, action, "opa_unavailable", request_id)
        return JSONResponse(status_code=403, content={"detail": "opa_unavailable", "request_id": request_id})

    if not allowed:
        audit("deny", agent_id, tool, action, "policy_deny", request_id)
        return JSONResponse(status_code=403, content={"detail": "policy_deny", "request_id": request_id})

    body: dict[str, Any] = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}

    if tool == "tickets" and action == "read":
        result = tools.tickets_read()
    elif tool == "tickets" and action == "write":
        result = tools.tickets_write(body)
    elif tool == "billing" and action == "read":
        result = tools.billing_read()
    else:
        audit("deny", agent_id, tool, action, "no_handler", request_id)
        raise HTTPException(status_code=404, detail="no_handler")

    audit("allow", agent_id, tool, action, "policy_allow", request_id)
    return {"request_id": request_id, "agent_id": agent_id, "result": result}
