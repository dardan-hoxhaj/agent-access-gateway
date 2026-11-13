"""OPA client tests."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from gateway.opa import OPAClient, OPAError


def test_allow_true():
    client = OPAClient("http://opa:8181")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": True}
    mock_resp.raise_for_status.return_value = None
    with patch("gateway.opa.httpx.post", return_value=mock_resp):
        assert client.allow("ticket-agent", "tickets", "read") is True


def test_allow_false():
    client = OPAClient("http://opa:8181")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": False}
    mock_resp.raise_for_status.return_value = None
    with patch("gateway.opa.httpx.post", return_value=mock_resp):
        assert client.allow("billing-agent", "tickets", "read") is False


def test_opa_unreachable():
    client = OPAClient("http://opa:8181")
    with patch("gateway.opa.httpx.post", side_effect=httpx.ConnectError("down")):
        with pytest.raises(OPAError):
            client.allow("ticket-agent", "tickets", "read")
