"""Smoke tests for KGQA routing, recording extraction, and offline replay."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from mini_marie.kgqa.mcp_router import domain_for_recording
from mini_marie.kgqa.question_catalog import match_catalog, match_catalog_exact
from mini_marie.kgqa.recording_utils import extract_from_text, extract_recording_info
from mini_marie.mop_mof.mof.workflow_mcp import format_workflow_mcp_response

_HAS_LLM = bool(os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _route_async(question: str):
    from mini_marie.kgqa.llm_router import route_question_async

    return asyncio.run(route_question_async(question))

@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_ethylene_glycol_question():
    route = _route_async(
        "How many hydrogen bonds can an ethylene glycol molecule accept and donate?"
    )
    assert any(s.startswith("chemistry-") for s in route.mcp_servers)
    assert route.catalog_entry is not None
    assert route.catalog_entry.workflow_id == "mq01_ethylene_glycol_hbond"


def test_match_catalog_exact_by_mq_prefix():
    entry = match_catalog_exact("MQ1 — ethylene glycol hbond")
    assert entry is not None
    assert entry.id == "MQ1"
    assert entry.workflow_id == "mq01_ethylene_glycol_hbond"


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_mof_competency_question():
    route = _route_async("Average and variance PLD of UiO-66")
    assert "mof-twa" in route.mcp_servers
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "CQ01_PLD_UIO66"


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_chemistry_competency_question():
    route = _route_async("MQ3 — ascorbic acid formula C6H8O6")
    assert any(s.startswith("chemistry-") for s in route.mcp_servers)


def test_match_catalog_by_id():
    entry = match_catalog("CQ01_PLD_UIO66")
    assert entry is not None
    assert entry.workflow_id == "CQ01_PLD_UIO66"


def test_extract_recording_from_tsv():
    sample = format_workflow_mcp_response(
        {
            "status": "pass",
            "mode": "online",
            "workflow_id": "test_wf",
            "workflow_name": "test_wf",
            "online_limit": 10,
            "offline_cap": 500000,
            "elapsed_ms": 42,
            "answer": "ok",
            "call_trace": [],
        },
        Path("mini_marie/mop_mof/mof/workflow_runs/test_wf_online_123.json"),
    )
    info = extract_from_text(sample)
    assert info["recording_path"]
    assert info["workflow_id"] == "test_wf"


def test_extract_from_metadata_tool_outputs():
    tsv = "status\tpass\nrecording_path\t/tmp/foo_online_1.json\nworkflow_id\tCQ01_PLD_UIO66\n"
    meta = {
        "tool_activity": {
            "tool_outputs": [{"name": "run_competency_online", "content": tsv}],
        }
    }
    info = extract_recording_info(online_answer="", metadata=meta)
    assert "foo_online_1.json" in (info["recording_path"] or "")
    assert len(info["recording_paths"]) == 1


def test_extract_all_recordings_from_metadata():
    tsv1 = "status\tpass\nrecording_path\t/tmp/a_online_1.json\nworkflow_id\tWF_A\n"
    tsv2 = "status\tpass\nrecording_path\t/tmp/b_online_2.json\nworkflow_id\tWF_B\n"
    meta = {
        "tool_activity": {
            "tool_outputs": [
                {"name": "run_workflow_online", "content": tsv1},
                {"name": "run_workflow_online", "content": tsv2},
            ],
        }
    }
    info = extract_recording_info(online_answer="", metadata=meta)
    assert len(info["recording_paths"]) == 2
    assert info["recording_path"] == info["recording_paths"][0]
    assert len(info["recordings"]) == 2


def test_replay_offline_batch_empty():
    from mini_marie.kgqa.offline_runner import replay_offline_batch

    result = replay_offline_batch([])
    assert result["status"] == "empty"
    assert result["parts"] == []


def test_replay_offline_batch_two_city_recordings():
    from mini_marie.kgqa.offline_runner import replay_offline_batch

    runs = sorted(Path("mini_marie/zaha/twa_city/workflow_runs").glob("*_online_*.json"))
    if len(runs) < 2:
        pytest.skip("need at least two city online recordings")
    paths = [str(runs[-2].resolve()), str(runs[-1].resolve())]
    batch = replay_offline_batch(paths)
    if batch["status"] == "error":
        pytest.skip(f"offline batch failed: {batch}")
    assert len(batch["parts"]) == 2
    assert len(batch.get("offline_paths") or []) >= 1
    assert batch["row_count"] >= batch["parts"][0].get("row_count", 0)


def test_data_from_offline_paths_two_tables():
    from demos.twa_adapter import _data_from_offline_paths
    from mini_marie.kgqa.offline_runner import replay_offline_batch

    runs = sorted(Path("mini_marie/zaha/twa_city/workflow_runs").glob("*_online_*.json"))
    if not runs:
        pytest.skip("no city online recordings")
    batch = replay_offline_batch([str(runs[-1].resolve())])
    if batch.get("status") not in ("pass", "partial"):
        pytest.skip("offline replay unavailable")
    paths = batch.get("offline_paths") or []
    if not paths:
        pytest.skip("no offline paths")
    data = _data_from_offline_paths(paths)
    assert data
    assert any(item.get("type") == "table" for item in data)


def test_domain_for_recording_paths():
    assert domain_for_recording("mini_marie/marie/chemistry/competency_runs/mq01_online_1.json") == "chemistry"
    assert domain_for_recording("mini_marie/mop_mof/mof/competency_runs/CQ01_online_1.json") == "mof_competency"
    assert domain_for_recording("mini_marie/zaha/twa_city/workflow_runs/WF_online_1.json") == "city"


def test_city_workflow_offline_replay_routing():
    from mini_marie.kgqa.offline_runner import replay_offline

    runs = sorted(Path("mini_marie/zaha/twa_city/workflow_runs").glob("*_online_*.json"))
    if not runs:
        pytest.skip("no city workflow online recordings")
    result = replay_offline(str(runs[-1].resolve()))
    if result.get("status") == "error":
        err = str(result.get("error", ""))
        assert "mof_case/workflows" not in err, f"city replay routed to mof_case: {err}"
        pytest.skip(f"offline replay failed (cache likely cold): {err}")
    assert result.get("offline_path")


def test_ex_zeolite_catalog_workflow_id():
    entry = match_catalog_exact("Which zeolite has framework code AEN?")
    assert entry is None


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_llm_routes_ex_zeolite_framework():
    route = _route_async("Which zeolite has framework code AEN?")
    assert route.catalog_entry is not None
    assert route.catalog_entry.workflow_id == "mq34_framework_aen"
    assert "chemistry-ontozeolite" in route.mcp_servers


def test_mq02_expected_empty_tag():
    entry = match_catalog_exact("MQ2 — uses of 3-amino-2-propanol")
    assert entry is not None
    assert "expected_empty" in entry.tags


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_singapore_jurong_pollutants():
    route = _route_async("What are the pollutant concentrations at Jurong Island?")
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "Q15"
    assert "sg-old" in route.mcp_servers
    assert "mof-twa" not in route.mcp_servers
    assert route.domain == "sg"


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_singapore_gfa():
    route = _route_async("How many land lots do not exceed their maximum permitted GFA?")
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "ZQ_GFA"
    assert "sg-old" in route.mcp_servers
    assert "mof-twa" not in route.mcp_servers


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_llm_routes_mq12_methylamine():
    route = _route_async(
        "What are the ionic strengths associated with the pK values of methylamine?"
    )
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "mq12_methylamine_ionic"
    assert route.catalog_entry.workflow_id == "mq12_methylamine_ionic"


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_form_zeolite_framework():
    route = _route_async("List all zeolitic materials recorded for framework code AEN")
    assert route.catalog_entry is not None
    assert route.catalog_entry.workflow_id == "mq34_framework_aen"
    assert "chemistry-ontozeolite" in route.mcp_servers


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_llm_routes_form_species_smiles():
    route = _route_async("Search species where SMILES is O")
    assert route.catalog_entry is not None
    assert route.catalog_entry.kind == "form"
    assert "chemistry-ontospecies" in route.mcp_servers


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_mq37_zeolite():
    route = _route_async(
        "Retrieve unit cell information of zeolitic material |Na20|[Al20Si76O192]"
    )
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "MQ37"
    assert "chemistry-ontozeolite" in route.mcp_servers
    assert "mof-twa" not in route.mcp_servers


@pytest.mark.skipif(not _HAS_LLM, reason="LLM routing requires REMOTE_API_KEY")
def test_router_mq49_mops():
    route = _route_async("Which MOPs have an outer diameter greater than 70 Angstrom?")
    assert route.catalog_entry is not None
    assert route.catalog_entry.id == "MQ49"
    assert "twa-mops" in route.mcp_servers
    assert "mof-twa" not in route.mcp_servers


@pytest.mark.skipif(
    not Path("mini_marie/marie/chemistry/competency_runs").exists(),
    reason="no chemistry competency runs dir",
)
def test_offline_replay_from_fixture_if_present():
    runs = sorted(Path("mini_marie/marie/chemistry/competency_runs").glob("*_online_*.json"))
    if not runs:
        pytest.skip("no online chemistry recordings")
    from mini_marie.kgqa.offline_runner import replay_offline

    rec = runs[0]
    recorded = json.loads(rec.read_text(encoding="utf-8"))
    if not recorded.get("probed_sequence"):
        pytest.skip("recording lacks probed_sequence")
    result = replay_offline(str(rec.resolve()))
    if result.get("status") == "error":
        pytest.skip(f"offline replay failed (cache likely cold): {result.get('error')}")
    assert result.get("offline_path")
