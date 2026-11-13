"""OPA client. Fail closed: if OPA is unreachable, the decision is deny."""

from __future__ import annotations

import httpx


class OPAError(Exception):
    """OPA could not be reached or returned an unusable response."""


class OPAClient:
    def __init__(self, opa_url: str) -> None:
        self.decision_url = opa_url.rstrip("/") + "/v1/data/agent/authz/allow"

    def allow(self, agent_id: str, tool: str, action: str) -> bool:
        payload = {"input": {"agent_id": agent_id, "tool": tool, "action": action}}
        try:
            resp = httpx.post(self.decision_url, json=payload, timeout=3.0)
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OPAError("opa_unavailable") from exc
        return body.get("result") is True
