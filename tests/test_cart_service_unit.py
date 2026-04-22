"""Unit tests for cart_service HTTP client (mocked requests)."""
from __future__ import annotations

import json
from unittest.mock import patch

import requests
from requests import Response

from services import cart_service


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


@patch.object(cart_service.requests, "request")
def test_add_to_cart_success(mock_request):
    mock_request.return_value = _response(200, {"success": True, "cart": {"items": [], "total": 0}})

    out = cart_service.add_to_cart("cust1", "product-a", quantity=2)

    assert out["success"] is True
    assert "cart" in out
    mock_request.assert_called_once()
    call_kw = mock_request.call_args[1]
    assert call_kw["json"]["product_id"] == "product-a"
    assert call_kw["json"]["quantity"] == 2
    assert call_kw["json"]["customer_id"] == "cust1"


@patch.object(cart_service.requests, "request")
def test_get_cart_success(mock_request):
    mock_request.return_value = _response(200, {"success": True, "cart": {"items": []}})

    out = cart_service.get_cart("cust1")

    assert out["success"] is True
    assert out["cart"] == {"items": []}


@patch.object(cart_service.requests, "request")
def test_add_to_cart_http_error_returns_failure_dict(mock_request):
    mock_request.return_value = _response(400, {"detail": "bad request"})

    out = cart_service.add_to_cart("cust1", "product-a", quantity=1)

    assert out["success"] is False
    assert "error" in out
    assert "400" in out["error"] or "bad request" in out["error"].lower()


@patch.object(cart_service.requests, "request")
def test_get_cart_connection_error_returns_failure_dict(mock_request):
    mock_request.side_effect = requests.exceptions.ConnectionError("refused")

    out = cart_service.get_cart("cust1")

    assert out["success"] is False
    assert "refused" in out["error"].lower() or "connection" in out["error"].lower()
