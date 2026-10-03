"""Route and direct-tool smoke tests for MOP page competency questions."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_CATALOG = REPO / "demos" / "mop_competency_questions.json"


def test_mop_catalog_has_eight_remote_questions():
    data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    questions = data["ontomops"]["questions"]
    assert len(questions) == 8
    ids = {q["id"] for q in questions}
    assert ids == {"MQ49", "MQ50", "MQ51", "MQ53", "MQ54", "MQ55", "MQ56", "MQ57"}


def test_lookup_mop_question_exact():
    from demos.mop_specs import lookup_mop_question

    spec = lookup_mop_question("Which MOPs have an outer diameter greater than 70 Angstrom?")
    assert spec is not None
    assert spec["id"] == "MQ49"
    assert spec["tool"] == "get_mops_by_outer_diameter_min"


def test_question_catalog_includes_mop_mq():
    from mini_marie.kgqa.question_catalog import match_catalog_exact

    entry = match_catalog_exact("Which MOPs have an outer diameter greater than 70 Angstrom?")
    assert entry is not None
    assert entry.id == "MQ49"
    assert entry.domain == "mops"


def test_router_mq49():
    from mini_marie.kgqa.mcp_router import route_question

    route = route_question("Which MOPs have an outer diameter greater than 70 Angstrom?")
    assert "twa-mops" in route.mcp_servers


def test_direct_mop_tool_dispatch(monkeypatch):
    from demos.mop_specs import lookup_mop_question, run_mop_competency_tool
    from demos.twa_adapter import _try_direct_mop_competency
    from mini_marie.kgqa.mcp_router import RouteResult
    import demos.mop_specs as mop_specs

    captured = {}

    def _fake_tool(**kwargs):
        captured.update(kwargs)
        return "mopLabel\touterDiameter\nTestMOP\t80"

    monkeypatch.setitem(mop_specs._tool_registry(), "get_mops_by_outer_diameter_min", _fake_tool)

    spec = lookup_mop_question("Which MOPs have an outer diameter greater than 70 Angstrom?")
    out = run_mop_competency_tool(spec)
    assert "TestMOP" in out
    assert captured.get("min_angstrom") == 70

    route = RouteResult(mcp_servers=["twa-mops"], domain="mops", reason="test", domains=["mops"])
    direct = _try_direct_mop_competency(spec["question"], route)
    assert direct is not None
    assert direct["metadata"]["catalog_entry_id"] == "MQ49"
