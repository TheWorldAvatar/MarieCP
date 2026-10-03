"""MOF competency defaults to ReAct (no direct bypass unless env opt-in)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from demos.twa_adapter import _try_direct_from_route
from mini_marie.kgqa.mcp_router import route_question
from mini_marie.kgqa.question_catalog import match_catalog_exact


def test_mof_default_skips_direct_bypass() -> None:
    question = "Which MOFs have the same topology as ZIF-8?"
    entry = match_catalog_exact(question)
    assert entry and entry.workflow_id == "CQ07_SAME_TOPO_ZIF8"
    route = route_question(question)
    for key in ("MOF_COMPETENCY_DIRECT", "MARIE_MOF_DIRECT"):
        os.environ.pop(key, None)
    assert _try_direct_from_route(question, route) is None


def test_mof_direct_bypass_when_env_set() -> None:
    question = "Which MOFs have the same topology as ZIF-8?"
    route = route_question(question)
    os.environ["MOF_COMPETENCY_DIRECT"] = "1"
    try:
        direct = _try_direct_from_route(question, route)
        assert direct is not None
        assert (direct.get("metadata") or {}).get("workflow_id") == "CQ07_SAME_TOPO_ZIF8"
    finally:
        os.environ.pop("MOF_COMPETENCY_DIRECT", None)


if __name__ == "__main__":
    test_mof_default_skips_direct_bypass()
    test_mof_direct_bypass_when_env_set()
    print("OK: MOF agent routing default")
