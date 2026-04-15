from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import Settings
from app.core.security import require_proxy_api_key


def build_request(headers: list[tuple[bytes, bytes]], client_host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/proxy/resolve",
        "raw_path": b"/api/proxy/resolve",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_require_proxy_api_key_accepts_valid_key_and_allowed_ip():
    settings = Settings(proxy_api_key="secret-key", proxy_allowed_ips="127.0.0.1")
    request = build_request([(b"x-proxy-key", b"secret-key")])

    require_proxy_api_key(request, settings)


def test_require_proxy_api_key_rejects_invalid_key():
    settings = Settings(proxy_api_key="secret-key", proxy_allowed_ips="127.0.0.1")
    request = build_request([(b"x-proxy-key", b"wrong-key")])

    try:
        require_proxy_api_key(request, settings)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Expected invalid proxy key to raise HTTPException")


def test_require_proxy_api_key_rejects_disallowed_ip():
    settings = Settings(proxy_api_key="secret-key", proxy_allowed_ips="10.0.0.2")
    request = build_request([(b"x-proxy-key", b"secret-key")], client_host="127.0.0.1")

    try:
        require_proxy_api_key(request, settings)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected disallowed proxy origin to raise HTTPException")
