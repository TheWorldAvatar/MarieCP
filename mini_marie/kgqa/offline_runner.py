"""Deterministic offline replay (no LLM) after online probe."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from mini_marie.kgqa.mcp_router import domain_for_recording
from mini_marie.kgqa.recording_utils import load_recording_json


def _aggregate_batch_status(parts: Sequence[Dict[str, Any]]) -> str:
    if not parts:
        return "empty"
    statuses = {p.get("status") for p in parts}
    if statuses <= {"pass"}:
        return "pass"
    if "pass" in statuses or "partial" in statuses:
        return "partial"
    return "error"


def _row_count(result: Dict[str, Any]) -> int:
    answer = result.get("answer")
    if isinstance(answer, list):
        return len(answer)
    digest = result.get("answer_digest") or {}
    auth = digest.get("authoritative") or {}
    for key in ("buildings_with_wkt", "top_buildings", "top_building_iris"):
        val = auth.get(key)
        if isinstance(val, dict) and val.get("_row_count"):
            return int(val["_row_count"])
        if isinstance(val, list):
            return len(val)
    sidecar = result.get("sidecar") or {}
    for artifact in sidecar.get("artifacts") or []:
        if artifact.get("kind") == "variable" and artifact.get("name") in (
            "buildings_with_wkt",
            "top_building_rows",
        ):
            count = artifact.get("row_count")
            if count:
                return int(count)
    for step in reversed(result.get("call_trace") or []):
        tool = step.get("tool") or step.get("transform") or step.get("name") or ""
        if tool in ("top_n_by_field", "buildings_with_locations_sql"):
            count = step.get("row_count")
            if count:
                return int(count)
    trace = result.get("call_trace") or []
    return sum(int(s.get("row_count") or 0) for s in trace)


def _answer_text(result: Dict[str, Any]) -> Any:
    if result.get("answer") is not None:
        return result.get("answer")
    digest = result.get("answer_digest") or {}
    if digest.get("summary_text"):
        return digest["summary_text"]
    trace = result.get("call_trace") or []
    if trace:
        return trace[-1].get("summary") or trace[-1].get("tsv")
    return None


def _replay_workflow_offline(
    domain: str,
    recording_path: str,
    *,
    offline_cap: int,
    workflow_name: Optional[str] = None,
) -> tuple[Dict[str, Any], Path]:
    """Dispatch workflow offline replay to the correct domain package."""
    if domain == "city":
        from mini_marie.zaha.twa_city.workflow_mcp import replay_workflow_offline
    elif domain == "mops":
        from mini_marie.mop_mof.mops.workflow_mcp import replay_workflow_offline
    else:
        from mini_marie.mop_mof.mof.workflow_mcp import replay_workflow_offline

    tsv = replay_workflow_offline(
        recording_path,
        offline_cap=offline_cap,
        workflow_name=workflow_name,
    )
    offline_path_str = None
    for line in tsv.splitlines():
        if line.startswith("recording_path\t"):
            offline_path_str = line.split("\t", 1)[1].strip()
            break
    if not offline_path_str:
        raise RuntimeError("Offline replay did not return recording_path")
    result = load_recording_json(offline_path_str)
    return result, Path(offline_path_str)


def replay_offline(
    recording_path: str,
    *,
    workflow_id: Optional[str] = None,
    offline_cap: int = 500_000,
) -> Dict[str, Any]:
    """
    Replay full-scale results from an online recording file.

    Returns dict with offline_path, answer, row_count, status, domain.
    """
    path = Path(recording_path)
    if not path.exists():
        return {
            "status": "error",
            "error": f"Recording not found: {path}",
            "offline_path": None,
            "domain": domain_for_recording(str(path), workflow_id),
        }

    recorded = load_recording_json(str(path))
    wf_id = workflow_id or recorded.get("workflow_id")
    domain = domain_for_recording(str(path), str(wf_id or ""))

    try:
        if domain == "chemistry":
            from mini_marie.marie.chemistry.chemistry_workflow_engine import (
                replay_from_recording,
                save_run,
            )

            result = replay_from_recording(path)
            offline_path = save_run(result)
        elif domain == "mof_competency":
            from mini_marie.mop_mof.mof.competency_workflow_engine import (
                load_workflow,
                replay_competency_from_recording,
                save_run,
            )

            wf = recorded.get("workflow_definition") or load_workflow(str(wf_id))
            result = replay_competency_from_recording(recorded, wf)
            result["replayed_from"] = str(path.resolve())
            offline_path = save_run(result)
        elif domain in ("mof_workflow", "city", "mops"):
            result, offline_path = _replay_workflow_offline(
                domain,
                str(path),
                offline_cap=offline_cap,
                workflow_name=recorded.get("workflow_name"),
            )
        else:
            mode = recorded.get("mode")
            if mode == "online" and recorded.get("probed_sequence"):
                from mini_marie.mop_mof.mof.competency_workflow_engine import (
                    load_workflow,
                    replay_competency_from_recording,
                    save_run,
                )

                wf = recorded.get("workflow_definition") or load_workflow(str(wf_id))
                result = replay_competency_from_recording(recorded, wf)
                offline_path = save_run(result)
                domain = "mof_competency"
            elif recorded.get("workflow_name"):
                wf_domain = domain_for_recording(str(path), recorded.get("workflow_name", ""))
                if wf_domain == "unknown":
                    wf_domain = "mof_workflow"
                result, offline_path = _replay_workflow_offline(
                    wf_domain,
                    str(path),
                    offline_cap=offline_cap,
                    workflow_name=recorded.get("workflow_name"),
                )
                domain = wf_domain
            else:
                from mini_marie.marie.chemistry.chemistry_workflow_engine import (
                    replay_from_recording,
                    save_run,
                )

                result = replay_from_recording(path)
                offline_path = save_run(result)
                domain = "chemistry"

        return {
            "status": result.get("status", "pass"),
            "domain": domain,
            "offline_path": str(Path(offline_path).resolve()),
            "answer": _answer_text(result),
            "row_count": _row_count(result),
            "result": result,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc) or type(exc).__name__,
            "domain": domain,
            "offline_path": None,
        }


def replay_offline_batch(
    recording_paths: Sequence[str],
    *,
    workflow_ids: Optional[Sequence[Optional[str]]] = None,
    offline_cap: int = 500_000,
) -> Dict[str, Any]:
    """
    Replay full-scale results for every online recording from a multi-probe agent run.

    Returns a batch envelope with ``parts`` (one per recording) plus backward-compatible
    ``offline_path`` / ``row_count`` / ``answer`` fields from the first successful part.
    """
    paths = [str(Path(p).resolve()) for p in recording_paths if p]
    if not paths:
        return {
            "status": "empty",
            "parts": [],
            "offline_paths": [],
            "offline_path": None,
            "row_count": 0,
            "answer": None,
        }

    wf_ids: List[Optional[str]] = list(workflow_ids or [])
    while len(wf_ids) < len(paths):
        wf_ids.append(None)

    parts: List[Dict[str, Any]] = []
    for index, path in enumerate(paths):
        part = replay_offline(
            path,
            workflow_id=wf_ids[index],
            offline_cap=offline_cap,
        )
        part["recording_path"] = path
        parts.append(part)

    offline_paths = [p.get("offline_path") for p in parts if p.get("offline_path")]
    row_count = sum(int(p.get("row_count") or 0) for p in parts)
    answers = [p.get("answer") for p in parts if not _is_blank(p.get("answer"))]
    primary = next((p for p in parts if p.get("status") == "pass"), parts[0])

    return {
        "status": _aggregate_batch_status(parts),
        "parts": parts,
        "offline_paths": offline_paths,
        "offline_path": primary.get("offline_path"),
        "row_count": row_count,
        "answer": answers[0] if len(answers) == 1 else answers or None,
        "domain": primary.get("domain"),
        "recording_paths": paths,
    }


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False
