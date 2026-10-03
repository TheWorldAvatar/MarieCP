"""Tests for OntoMOPs Blazegraph endpoint resolution and query cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mini_marie.mop_mof.mops import ontomop_operations as ops
from mini_marie.mop_mof.mops.mop_blazegraph_cache import MopBlazegraphCache


def test_endpoint_candidates_env_override(monkeypatch):
    monkeypatch.setenv("ONTOMOPS_OGM_ENDPOINT", "http://example.test/sparql")
    assert ops.endpoint_candidates() == ["http://example.test/sparql"]


def test_resolve_endpoint_from_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "endpoint_probe.json"
    monkeypatch.setattr(ops, "endpoint_probe_cache_path", lambda: cache_path)
    cache_path.write_text(
        json.dumps(
            {
                "probed_at_unix": 9_999_999_999,
                "preferred_endpoint": "http://cached.test/sparql",
                "working": ["http://cached.test/sparql"],
                "results": [],
            }
        ),
        encoding="utf-8",
    )
    assert ops.resolve_endpoint(force_probe=False) == "http://cached.test/sparql"


def test_remote_or_cached_tsv_uses_cache_when_remote_fails(tmp_path, monkeypatch):
    db = tmp_path / "cache.sqlite"
    monkeypatch.setattr(
        "mini_marie.mop_mof.mops.mop_blazegraph_cache.db_path",
        lambda: db,
    )

    cache = MopBlazegraphCache(path=db)
    cache.put(
        "get_mop_corpus_stats",
        {},
        "http://cached.test/sparql",
        [{"mopCount": "2383"}],
    )

    def _boom():
        raise RuntimeError("endpoint down")

    monkeypatch.setattr(ops, "resolve_endpoint", lambda force_probe=False: (_ for _ in ()).throw(RuntimeError("down")))

    out = ops.remote_or_cached_tsv("get_mop_corpus_stats", {}, _boom)
    assert "cache_fallback" in out
    assert "2383" in out


def test_execute_remote_sparql_uses_query_cache_when_endpoint_down(tmp_path, monkeypatch):
    db = tmp_path / "cache.sqlite"
    monkeypatch.setattr("mini_marie.mop_mof.mops.mop_blazegraph_cache.db_path", lambda: db)
    cache = MopBlazegraphCache(path=db)
    query = "SELECT ?x WHERE { BIND(1 AS ?x) }"
    cache.put_query(query, "http://cached.test/sparql", [{"x": "1"}])

    probe_path = tmp_path / "endpoint_probe.json"
    monkeypatch.setattr(ops, "endpoint_probe_cache_path", lambda: probe_path)
    probe_path.write_text(
        json.dumps(
            {
                "probed_at_unix": 9_999_999_999,
                "preferred_endpoint": None,
                "working": [],
                "results": [],
            }
        ),
        encoding="utf-8",
    )

    rows = ops.execute_remote_sparql(query)
    assert rows == [{"x": "1"}]


def test_execute_remote_sparql_skips_remote_when_endpoint_down_and_tool_cache_exists(
    tmp_path, monkeypatch
):
    db = tmp_path / "cache.sqlite"
    monkeypatch.setattr("mini_marie.mop_mof.mops.mop_blazegraph_cache.db_path", lambda: db)
    cache = MopBlazegraphCache(path=db)
    cache.put("get_mop_corpus_stats", {}, "http://cached.test/sparql", [{"mopCount": "99"}])

    probe_path = tmp_path / "endpoint_probe.json"
    monkeypatch.setattr(ops, "endpoint_probe_cache_path", lambda: probe_path)
    probe_path.write_text(
        json.dumps({"probed_at_unix": 9_999_999_999, "preferred_endpoint": None, "working": [], "results": []}),
        encoding="utf-8",
    )

    def _never_called(*_a, **_k):
        raise AssertionError("live SPARQL should not run when endpoint down and cache exists")

    monkeypatch.setattr(ops, "execute_sparql", _never_called)
    rows = ops.get_mop_corpus_stats()
    assert rows == [{"mopCount": "99"}]


def test_get_endpoint_status_uses_negative_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "endpoint_probe.json"
    monkeypatch.setattr(ops, "endpoint_probe_cache_path", lambda: cache_path)
    cache_path.write_text(
        json.dumps(
            {
                "probed_at_unix": 9_999_999_999,
                "preferred_endpoint": None,
                "working": [],
                "results": [{"url": "http://down.test/sparql", "ok": False, "error": "timed out"}],
            }
        ),
        encoding="utf-8",
    )

    def _should_not_probe():
        raise AssertionError("probe_all_endpoints should not run when negative cache is fresh")

    monkeypatch.setattr(ops, "probe_all_endpoints", _should_not_probe)
    status = ops.get_endpoint_status(force_probe=False)
    assert status.get("from_cache") is True
    assert status.get("preferred_endpoint") is None


def test_probe_blazegraph_module_import():
    from mini_marie.mop_mof.mops import probe_blazegraph

    assert callable(probe_blazegraph.main)
