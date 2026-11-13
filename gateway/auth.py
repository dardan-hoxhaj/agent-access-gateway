"""JWT validation against a Keycloak JWKS endpoint.

We pin the allowed algorithms, check issuer and audience, and reject
expired or malformed tokens. The token itself is never logged.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from jose import JWTError, jwt

ALLOWED_ALGORITHMS = ["RS256"]
JWKS_CACHE_SECONDS = 300


class AuthError(Exception):
    """Raised when a token fails validation. Message is safe to return."""


class JWKSClient:
    """Fetches and caches Keycloak's JWKS. Fail closed on fetch errors."""

    def __init__(self, jwks_url: str, issuer: str, audience: str) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self._keys: dict[str, Any] | None = None
        self._fetched_at: float = 0

    def _load_jwks(self) -> dict[str, Any]:
        now = time.time()
        if self._keys is not None and (now - self._fetched_at) < JWKS_CACHE_SECONDS:
            return self._keys
        try:
            resp = httpx.get(self.jwks_url, timeout=5.0)
            resp.raise_for_status()
            self._keys = resp.json()
            self._fetched_at = now
            return self._keys
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthError("jwks_unavailable") from exc

    def validate(self, token: str) -> dict[str, Any]:
        if not token or token.count(".") != 2:
            raise AuthError("malformed_token")
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthError("malformed_token") from exc

        alg = header.get("alg")
        if alg not in ALLOWED_ALGORITHMS:
            raise AuthError("unsupported_algorithm")

        jwks = self._load_jwks()
        try:
            claims = jwt.decode(
                token,
                jwks,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
            )
        except JWTError as exc:
            raise AuthError("invalid_token") from exc
        return claims

    def agent_id(self, claims: dict[str, Any]) -> str:
        azp = claims.get("azp") or claims.get("client_id")
        if not azp or not isinstance(azp, str):
            raise AuthError("missing_agent_id")
        return azp
