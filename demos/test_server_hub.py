"""Smoke tests for demo hub routes and Marie classic static root."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_marie_classic_committed():
    root = REPO / "demos" / "marie-classic"
    assert (root / "index.html").is_file(), f"missing {root / 'index.html'}"
    assert (root / "static" / "js" / "script.js").is_file()


def test_hub_routes():
    from demos.server import app

    client = app.test_client()
    for path in ("/", "/demos/", "/demos/hub/"):
        resp = client.get(path)
        assert resp.status_code in {200, 302}, path
        if resp.status_code == 302:
            assert "/demos/hub/" in resp.headers.get("Location", "")

    resp = client.get("/demos/hub/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Marie" in body and "Zaha" in body and "Elisa" in body
    assert "https://qa.theworldavatar.io/" in body
    assert 'href="/demos/elisa/' not in body

    resp = client.get("/demos/marie-classic/")
    assert resp.status_code == 200
    assert "Marie" in resp.get_data(as_text=True)

    resp = client.get("/demos/marie/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Marie" in resp.get_data()


if __name__ == "__main__":
    test_marie_classic_committed()
    test_hub_routes()
    print("hub route smoke tests OK")
