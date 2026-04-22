"""Unit tests for payment_service HTTP client (mocked requests)."""
from __future__ import annotations

import json
from unittest.mock import patch

import requests
from requests import Response

from services import payment_service


def _response(status: int, body: dict | str | bytes) -> Response:
    r = Response()
    r.status_code = status
    if isinstance(body, dict):
        raw = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = body
    r._content = raw
    r.encoding = "utf-8"
    return r


@patch.object(payment_service.requests, "request")
def test_send_otp_success(mock_request):
    mock_request.return_value = _response(200, {"success": True, "expires_in_minutes": 5})

    out = payment_service.send_otp("03001234567")

    assert out["success"] is True
    assert out["expires_in_minutes"] == 5


@patch.object(payment_service.requests, "request")
def test_send_otp_request_exception_returns_failure_dict(mock_request):
    mock_request.side_effect = requests.exceptions.Timeout("timed out")

    out = payment_service.send_otp("03001234567")

    assert out["success"] is False
    assert "timed out" in out["error"].lower() or "timeout" in out["error"].lower()
