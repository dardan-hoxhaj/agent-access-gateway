"""Gateway tests with mocked JWKS and OPA. No Docker required."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from gateway.auth import JWKSClient
from gateway.main import app
from gateway.opa import OPAClient

ISSUER = "http://localhost:8080/realms/agent-gateway"
AUDIENCE = "agent-gateway"

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
PUBLIC = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def _jwks():
    from jose.backends.cryptography_backend import CryptographyRSAKey
    pub = CryptographyRSAKey(PUBLIC, algorithm="RS256")
    jwk = pub.to_dict()
    jwk["kid"] = "k"
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


def _token(agent: str, exp_offset: int = 300) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "azp": agent,
        "sub": agent,
        "exp": now + exp_offset,
        "iat": now,
    }
    return jwt.encode(claims, PRIVATE, algorithm="RS256", headers={"kid": "k", "alg": "RS256"})


@pytest.fixture
def client():
    with patch.object(JWKSClient, "_load_jwks", return_value=_jwks()):
        yield TestClient(app)


def test_allow_ticket_read(client):
    with patch.object(OPAClient, "allow", return_value=True):
        resp = client.get("/tools/tickets", headers={"Authorization": f"Bearer {_token('ticket-agent')}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_id"] == "ticket-agent"
    assert body["result"]["tool"] == "tickets"


def test_deny_wrong_agent(client):
    with patch.object(OPAClient, "allow", return_value=False):
        resp = client.get("/tools/tickets", headers={"Authorization": f"Bearer {_token('billing-agent')}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "policy_deny"


def test_invalid_token(client):
    resp = client.get("/tools/tickets", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401


def test_expired_token(client):
    resp = client.get("/tools/tickets", headers={"Authorization": f"Bearer {_token('ticket-agent', exp_offset=-10)}"})
    assert resp.status_code == 401


def test_opa_down(client):
    from gateway.opa import OPAError
    with patch.object(OPAClient, "allow", side_effect=OPAError("opa_unavailable")):
        resp = client.get("/tools/tickets", headers={"Authorization": f"Bearer {_token('ticket-agent')}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "opa_unavailable"


def test_allow_ticket_write(client):
    with patch.object(OPAClient, "allow", return_value=True):
        resp = client.post(
            "/tools/tickets",
            headers={"Authorization": f"Bearer {_token('ticket-agent')}"},
            json={"title": "new ticket"},
        )
    assert resp.status_code == 200
    assert resp.json()["result"]["created"]["title"] == "new ticket"


def test_missing_bearer(client):
    resp = client.get("/tools/tickets")
    assert resp.status_code == 401


def test_health(client):
    assert client.get("/health").status_code == 200
