"""Unit tests for JWT validation. Uses a local RSA key, no Keycloak required."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from gateway.auth import AuthError, JWKSClient

ISSUER = "http://localhost:8080/realms/agent-gateway"
AUDIENCE = "agent-gateway"


def _key_pair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


PRIVATE, PUBLIC = _key_pair()
KID = "test-key"


def _jwks():
    from jose.backends.cryptography_backend import CryptographyRSAKey
    pub = CryptographyRSAKey(PUBLIC, algorithm="RS256")
    jwk = pub.to_dict()
    jwk["kid"] = KID
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return {"keys": [jwk]}


def _token(claims: dict, alg: str = "RS256") -> str:
    headers = {"kid": KID, "alg": alg}
    return jwt.encode(claims, PRIVATE, algorithm=alg, headers=headers)


def _base_claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "azp": "ticket-agent",
        "sub": "ticket-agent",
        "exp": now + 300,
        "iat": now,
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def client():
    c = JWKSClient(
        jwks_url="http://unused",
        issuer=ISSUER,
        audience=AUDIENCE,
    )
    with patch.object(c, "_load_jwks", return_value=_jwks()):
        yield c


def test_valid_token(client):
    token = _token(_base_claims())
    claims = client.validate(token)
    assert client.agent_id(claims) == "ticket-agent"


def test_expired_token(client):
    token = _token(_base_claims(exp=int(time.time()) - 10))
    with pytest.raises(AuthError):
        client.validate(token)


def test_wrong_issuer(client):
    token = _token(_base_claims(iss="http://evil.example"))
    with pytest.raises(AuthError):
        client.validate(token)


def test_wrong_audience(client):
    token = _token(_base_claims(aud="other"))
    with pytest.raises(AuthError):
        client.validate(token)


def test_bad_algorithm(client):
    # python-jose 3.5 refuses to sign HS256 with an RSA key (CVE-2024-33663).
    # Sign with a symmetric secret instead, then confirm the gateway rejects it.
    token = jwt.encode(_base_claims(), "not-a-real-secret", algorithm="HS256")
    with pytest.raises(AuthError):
        client.validate(token)


def test_malformed(client):
    with pytest.raises(AuthError):
        client.validate("not-a-jwt")


def test_missing_agent(client):
    token = _token(_base_claims(azp=None))
    claims = client.validate(token)
    with pytest.raises(AuthError):
        client.agent_id(claims)
