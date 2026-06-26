"""Regression tests for generic numeric threshold binding in competency workflows."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dotenv import load_dotenv

load_dotenv(REPO / ".env", override=True)
load_dotenv(REPO / "configs" / "demo_local.env", override=True)

from mini_marie.kgqa.question_catalog import match_catalog
from mini_marie.marie.chemistry.chemistry_workflow_engine import (
    load_workflow,
    run_competency_workflow,
)
from mini_marie.marie.chemistry.query_builder import list_zeolite_numeric_props_rows
from mini_marie.marie.chemistry.workflow_mcp import run_competency_online
from mini_marie.workflow_parameters import resolve_workflow_parameters


def _answer_row_count(result: dict) -> int:
    answer = result.get("answer")
    if isinstance(answer, list):
        return len(answer)
    return 0


def _filter_step(result: dict) -> dict | None:
    for step in result.get("call_trace") or []:
        if step.get("transform") == "filter_rows":
            return step
    return None


def test_zeolite_row_pool_exists():
    rows = list_zeolite_numeric_props_rows("ontozeolite", row_limit=5000)
    assert rows, "expected zeolite material rows"
    with_area = sum(1 for r in rows if r.get("accessible_area_per_cell") is not None)
    with_vol = sum(1 for r in rows if r.get("occupiable_volume_per_cell") is not None)
    print(
        f"zeolite rows={len(rows)} with area={with_area} with volume={with_vol} "
        "(live endpoint may lack numeric reified props)"
    )


def test_mq41_workflow_uses_parameter_variables():
    wf = load_workflow("mq41_zeolite_area_volume")
    assert wf.get("parameters")
    filters = wf["steps"][1]["filters"]
    assert filters[0]["value"] == "$min_accessible_area"
    assert filters[1]["value"] == "$max_volume_per_cell"


def test_mq41_parameters_parse_from_question():
    wf = load_workflow("mq41_zeolite_area_volume")
    q = (
        "Show me all zeolites with accessible area per cell greater than 300 Å² "
        "and occupiable volume per cell less than 400 Å³."
    )
    params = resolve_workflow_parameters(wf, q)
    assert params["min_accessible_area"] == 300.0
    assert params["max_volume_per_cell"] == 400.0


def test_mq41_online_runs_filter_preview():
    wf = load_workflow("mq41_zeolite_area_volume")
    q = (
        "Show me all zeolites with accessible area per cell greater than 300 Å² "
        "and occupiable volume per cell less than 400 Å³."
    )
    params = resolve_workflow_parameters(wf, q)
    online = run_competency_workflow(
        wf, mode="online", force_refresh=True, question=q, parameters=params
    )
    filt = _filter_step(online)
    assert filt is not None
    assert filt.get("status") == "preview"
    print(f"mq41 online preview rows={filt.get('row_count')}, answer rows={_answer_row_count(online)}")


def test_variant_questions_same_catalog_workflow():
    variants = [
        "Show me all zeolites with accessible area per cell greater than 500 Å² and occupiable volume per cell less than 200 Å³.",
        "Show me all zeolites with accessible area per cell greater than 300 Å² and occupiable volume per cell less than 400 Å³.",
        "Show me all zeolites with accessible area per cell greater than 800 Å² and occupiable volume per cell less than 100 Å³.",
    ]
    entries = [match_catalog(q) for q in variants]
    wf_ids = [e.workflow_id for e in entries if e]
    print("catalog workflow_ids:", wf_ids)
    assert all(wid == "mq41_zeolite_area_volume" for wid in wf_ids)


def test_mq13_online_preview_differs_by_parameter():
    wf = load_workflow("mq13_multi_source_pka")
    loose = run_competency_workflow(
        wf, mode="online", parameters={"min_source_count": 1}
    )
    strict = run_competency_workflow(
        wf, mode="online", parameters={"min_source_count": 5}
    )
    loose_n = _answer_row_count(loose)
    strict_n = _answer_row_count(strict)
    print(f"mq13 online preview loose={loose_n} strict={strict_n}")
    assert loose_n > strict_n


def test_mq13_offline_parameters_change_counts():
    wf = load_workflow("mq13_multi_source_pka")
    loose = run_competency_workflow(
        wf, mode="offline", parameters={"min_source_count": 1}
    )
    strict = run_competency_workflow(
        wf, mode="offline", parameters={"min_source_count": 10}
    )
    assert _answer_row_count(loose) > _answer_row_count(strict)


def test_online_mcp_respects_question_parameters():
    q_loose = "List compounds with pKa values reported across more than 1 source."
    q_strict = "List compounds with pKa values reported across more than 5 sources."
    out_loose = run_competency_online(
        "mq13_multi_source_pka", question=q_loose, force_refresh=True
    )
    out_strict = run_competency_online(
        "mq13_multi_source_pka", question=q_strict, force_refresh=True
    )
    path_loose = re.search(r"recording_path\t(.+)", out_loose)
    path_strict = re.search(r"recording_path\t(.+)", out_strict)
    assert path_loose and path_strict
    rec_loose = json.loads(Path(path_loose.group(1).strip()).read_text(encoding="utf-8"))
    rec_strict = json.loads(Path(path_strict.group(1).strip()).read_text(encoding="utf-8"))
    assert rec_loose.get("resolved_parameters") != rec_strict.get("resolved_parameters")
    loose_n = _answer_row_count(rec_loose)
    strict_n = _answer_row_count(rec_strict)
    print(f"mcp mq13 preview counts loose={loose_n} strict={strict_n}")
    assert loose_n >= strict_n


def test_mq13_offline_filter_sensitive_when_data_exists():
    wf = load_workflow("mq13_multi_source_pka")
    strict = run_competency_workflow(
        wf,
        mode="offline",
        force_refresh=True,
        parameters={"min_source_count": 1},
    )
    loose = run_competency_workflow(
        wf,
        mode="offline",
        force_refresh=True,
        parameters={"min_source_count": 10},
    )
    c_strict = _answer_row_count(strict)
    c_loose = _answer_row_count(loose)
    print(f"mq13 offline source_count>1: {c_strict}, >10: {c_loose}")
    assert c_strict > 0
    assert c_loose < c_strict


def test_mq13_online_runs_threshold_preview():
    wf = load_workflow("mq13_multi_source_pka")
    online = run_competency_workflow(
        wf,
        mode="online",
        force_refresh=True,
        parameters={"min_source_count": 1},
    )
    filt = _filter_step(online)
    assert filt is not None
    assert filt.get("status") == "preview"
    print(f"mq13 online preview rows={filt.get('row_count')}")


def main() -> int:
    tests = [
        test_zeolite_row_pool_exists,
        test_mq41_workflow_uses_parameter_variables,
        test_mq41_parameters_parse_from_question,
        test_mq41_online_runs_filter_preview,
        test_variant_questions_same_catalog_workflow,
        test_mq13_online_preview_differs_by_parameter,
        test_mq13_offline_parameters_change_counts,
        test_online_mcp_respects_question_parameters,
        test_mq13_offline_filter_sensitive_when_data_exists,
        test_mq13_online_runs_threshold_preview,
    ]
    failed = 0
    for fn in tests:
        name = fn.__name__
        try:
            fn()
            print(f"[PASS] {name}\n")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {name}: {exc}\n")
    print(f"{'All passed' if not failed else f'{failed} failed'} ({len(tests)} tests)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
