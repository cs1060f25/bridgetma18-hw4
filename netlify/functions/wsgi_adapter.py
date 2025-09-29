"""Minimal WSGI-to-Lambda adapter for Netlify Python functions."""

# Source: Implemented with assistance from OpenAI's GPT-5 (Codex) in the Harvard CS106 Codex CLI.

from __future__ import annotations

import base64
import io
import sys
from typing import Dict, Iterable, Tuple

Headers = Dict[str, str]


def _convert_headers(headers: Headers) -> Headers:
    """Normalize headers into lowercase keys."""
    normalized: Headers = {}
    for name, value in headers.items():
        normalized[name.lower()] = value
    return normalized


def _build_environ(event: Dict, body_bytes: bytes) -> Dict:
    headers = _convert_headers(event.get("headers") or {})
    path_info = event.get("path", "/")
    prefix = "/.netlify/functions/"
    if path_info.startswith(prefix):
        path_info = "/" + path_info[len(prefix):]

    environ: Dict[str, object] = {
        "REQUEST_METHOD": event.get("httpMethod", "GET"),
        "SCRIPT_NAME": "",
        "PATH_INFO": path_info,
        "QUERY_STRING": event.get("rawQueryString", ""),
        "SERVER_NAME": headers.get("host", "netlify"),
        "SERVER_PORT": headers.get("x-forwarded-port", "443"),
        "SERVER_PROTOCOL": event.get("requestContext", {}).get("http", {}).get("protocol", "HTTP/1.1"),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": headers.get("x-forwarded-proto", "https"),
        "wsgi.input": io.BytesIO(body_bytes),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": True,
        "CONTENT_LENGTH": str(len(body_bytes)),
    }

    content_type = headers.get("content-type")
    if content_type:
        environ["CONTENT_TYPE"] = content_type

    for name, value in headers.items():
        header_key = "HTTP_" + name.upper().replace("-", "_")
        environ[header_key] = value

    return environ


def wsgi_handler(app):  # type: ignore[no-untyped-def]
    """Return a Netlify-compatible handler for the provided WSGI app."""

    def handler(event, context):  # type: ignore[no-untyped-def]
        body = event.get("body", "")
        if body and event.get("isBase64Encoded"):
            body_bytes = base64.b64decode(body)
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
        else:
            body_bytes = b""

        environ = _build_environ(event, body_bytes)

        status_headers = {
            "status": 200,
            "headers": {},
        }
        buffer = bytearray()

        def start_response(status: str, response_headers: Iterable[Tuple[str, str]], exc_info=None):  # type: ignore[no-untyped-def]
            status_headers["status"] = int(status.split(" ", 1)[0])
            headers_dict: Headers = {}
            for header, value in response_headers:
                headers_dict[header] = value
            status_headers["headers"] = headers_dict

            def write(data: bytes) -> None:
                buffer.extend(data)

            return write

        result = app(environ, start_response)
        try:
            for data in result:
                if data:
                    buffer.extend(data)
        finally:
            if hasattr(result, "close"):
                result.close()  # type: ignore[attr-defined]

        return {
            "statusCode": status_headers["status"],
            "headers": status_headers["headers"],
            "body": buffer.decode("utf-8"),
            "isBase64Encoded": False,
        }

    return handler
