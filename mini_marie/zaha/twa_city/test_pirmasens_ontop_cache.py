"""Smoke tests for Pirmasens Ontop SQLite cache."""

from __future__ import annotations

from mini_marie.zaha.twa_city.pirmasens_md_sparql import page_ontop_warm_specs
from mini_marie.zaha.twa_city.pirmasens_ontop_cache import (
    PirmasensOntopCache,
    invoke_run_sparql,
    warm_run_sparql,
)
from mini_marie.zaha.twa_city.warm_pirmasens_ontop_cache import page_warm_specs


def test_page_warm_specs_cover_ontop_questions() -> None:
    specs = page_warm_specs()
    ontop = page_ontop_warm_specs()
    assert len(ontop) == 20
    assert len(specs) == len(ontop) + 3  # + city named stats files


def test_warm_and_read_from_cache(tmp_path) -> None:
    db = tmp_path / "test_ontop.sqlite"
    spec = page_ontop_warm_specs()[0]
    args = spec["args"]
    warm_run_sparql(
        args["endpoint_id"],
        args["query"],
        force=True,
        cache=PirmasensOntopCache(db),
    )
    ck = PirmasensOntopCache(db)
    try:
        assert ck.has_full("run_sparql", args)
        rows, meta = invoke_run_sparql(
            args["endpoint_id"],
            args["query"],
            mode="online",
            limit=5,
            use_cache=True,
            cache=ck,
        )
        assert rows
        assert meta.get("from_cache")
    finally:
        ck.close()
