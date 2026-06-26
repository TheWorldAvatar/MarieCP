"""Reverse-proxy Marie Next.js dev server through Flask (Windows ↔ WSL)."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from flask import Request, Response

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

_MARIE_UPSTREAM: str | None = None
_MARIE_BASE_PATH = os.environ.get("MARIE_FRONTEND_BASE_PATH", "/demos/marie").rstrip("/") or "/demos/marie"


def marie_proxy_enabled() -> bool:
    raw = os.environ.get("MARIE_FRONTEND_PROXY", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def marie_public_base() -> str:
    """Browser-facing Marie UI base (same origin as Flask when proxying)."""
    if marie_proxy_enabled():
        return _MARIE_BASE_PATH
    url = os.environ.get("MARIE_FRONTEND_URL", f"http://127.0.0.1:3000{_MARIE_BASE_PATH}").rstrip("/")
    return url


def _wsl_host_ip() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        proc = subprocess.run(
            ["wsl", "hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first = (proc.stdout or "").strip().split()
    return first[0] if first else None


def _probe_upstream(base: str, timeout: float = 2.0) -> bool:
    try:
        resp = httpx.get(f"{base}{_MARIE_BASE_PATH}/", follow_redirects=False, timeout=timeout)
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def resolve_marie_upstream(force: bool = False) -> str:
    global _MARIE_UPSTREAM
    if _MARIE_UPSTREAM is not None and not force:
        return _MARIE_UPSTREAM

    explicit = os.environ.get("MARIE_FRONTEND_UPSTREAM", "").strip().rstrip("/")
    if explicit:
        _MARIE_UPSTREAM = explicit
        return explicit

    port = os.environ.get("MARIE_FRONTEND_PORT", "3000")
    candidates = [f"http://127.0.0.1:{port}"]
    wsl_ip = _wsl_host_ip()
    if wsl_ip:
        candidates.append(f"http://{wsl_ip}:{port}")

    for base in candidates:
        if _probe_upstream(base):
            _MARIE_UPSTREAM = base
            return base

    _MARIE_UPSTREAM = candidates[0]
    return _MARIE_UPSTREAM


def _rewrite_location(value: str, _upstream_base: str, public_prefix: str) -> str:
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme in {"http", "https"} else value.split("?", 1)[0].split("#", 1)[0]
    query = f"?{parsed.query}" if parsed.query else ""
    if "?" in value and not parsed.scheme:
        query = "?" + value.split("?", 1)[1].split("#", 1)[0]
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    if "#" in value and not parsed.scheme:
        fragment = "#" + value.split("#", 1)[1]

    if path == _MARIE_BASE_PATH:
        return f"{public_prefix}{query}{fragment}"
    if path.startswith(f"{_MARIE_BASE_PATH}/"):
        suffix = path[len(_MARIE_BASE_PATH) :]
        return f"{public_prefix}{suffix}{query}{fragment}"
    return value


def _forward_headers(request: Request) -> dict[str, str]:
    skip = _HOP_BY_HOP | {"host", "content-length"}
    headers: dict[str, str] = {}
    for key, value in request.headers:
        if key.lower() in skip:
            continue
        headers[key] = value
    return headers


def proxy_marie_request(request: Request, subpath: str) -> Response:
    upstream_base = resolve_marie_upstream()
    upstream_path = f"{_MARIE_BASE_PATH}/{subpath}" if subpath else _MARIE_BASE_PATH
    target = urljoin(f"{upstream_base}/", upstream_path.lstrip("/"))
    if request.query_string:
        target = f"{target}?{request.query_string.decode()}"

    body = request.get_data()
    method = request.method.upper()
    headers = _forward_headers(request)

    try:
        upstream = httpx.request(
            method,
            target,
            headers=headers,
            content=body if body else None,
            follow_redirects=False,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    except httpx.HTTPError as exc:
        hint = (
            f"Marie UI unavailable at {upstream_base}{_MARIE_BASE_PATH}/ "
            f"(start Next.js: bash demos/run_marie_compat_wsl.sh frontend). Error: {exc}"
        )
        return Response(hint, status=502, mimetype="text/plain")

    out_headers: list[tuple[str, str]] = []
    for key, value in upstream.headers.items():
        lower = key.lower()
        if lower in _HOP_BY_HOP or lower in {"content-encoding", "content-length"}:
            continue
        if lower == "location":
            value = _rewrite_location(value, upstream_base, _MARIE_BASE_PATH)
        out_headers.append((key, value))

    return Response(upstream.content, status=upstream.status_code, headers=out_headers)
