"""KGQA orchestrator: route → online ReAct → offline replay."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from mini_marie.kgqa.agent import KgqaAgent
from mini_marie.kgqa.llm_router import route_question_async
from mini_marie.kgqa.offline_runner import replay_offline, replay_offline_batch
from mini_marie.kgqa.recording_utils import extract_recording_info


def _replay_from_rec_info(
    rec_info: Dict[str, Any],
    *,
    offline_cap: int,
    skip_offline_if_no_cache: bool,
) -> tuple[Optional[Dict[str, Any]], int]:
    """Replay one or many online recordings; returns (offline_result, offline_ms)."""
    paths = rec_info.get("recording_paths") or []
    if not paths and rec_info.get("recording_path"):
        paths = [rec_info["recording_path"]]
    if not paths:
        return None, 0

    recordings = rec_info.get("recordings") or []
    workflow_ids = [r.get("workflow_id") for r in recordings]
    while len(workflow_ids) < len(paths):
        workflow_ids.append(rec_info.get("workflow_id"))

    t0 = time.perf_counter()
    if len(paths) == 1:
        offline_result = replay_offline(
            paths[0],
            workflow_id=workflow_ids[0] if workflow_ids else rec_info.get("workflow_id"),
            offline_cap=offline_cap,
        )
    else:
        offline_result = replay_offline_batch(
            paths,
            workflow_ids=workflow_ids,
            offline_cap=offline_cap,
        )

    offline_ms = round((time.perf_counter() - t0) * 1000)
    if (
        skip_offline_if_no_cache
        and offline_result.get("status") in ("error", "partial")
    ):
        parts = offline_result.get("parts") or [offline_result]
        cache_errors = [
            p for p in parts
            if p.get("status") == "error"
            and p.get("error")
            and any(k in str(p.get("error", "")).lower() for k in ("cache", "not found"))
        ]
        if cache_errors and not any(p.get("status") == "pass" for p in parts):
            offline_result["skipped"] = True

    return offline_result, offline_ms


def _route_dict(route) -> Dict[str, Any]:
    if isinstance(route, dict):
        return route
    return {
        "mcp_servers": route.mcp_servers,
        "domain": route.domain,
        "domains": getattr(route, "domains", None) or [],
        "reason": route.reason,
        "catalog_entry_id": route.catalog_entry.id if route.catalog_entry else None,
        "catalog_entry_ids": [e.id for e in (getattr(route, "catalog_entries", None) or [])],
    }


def _build_result(
    *,
    question: str,
    route,
    online_answer: str,
    metadata: Dict[str, Any],
    recording_path: Optional[str],
    workflow_id: Optional[str],
    offline_result: Optional[Dict[str, Any]],
    timing: Dict[str, Any],
    recording_paths: Optional[list] = None,
) -> Dict[str, Any]:
    total = timing.get("total_ms")
    if total is None:
        total = (timing.get("route_ms") or 0) + (timing.get("online_ms") or 0) + (timing.get("offline_ms") or 0)
    paths = recording_paths or []
    if not paths and recording_path:
        paths = [recording_path]
    offline_paths = (offline_result or {}).get("offline_paths") or []
    if not offline_paths and (offline_result or {}).get("offline_path"):
        offline_paths = [offline_result["offline_path"]]
    return {
        "question": question,
        "online_answer": online_answer,
        "recording_path": recording_path or (paths[0] if paths else None),
        "recording_paths": paths,
        "workflow_id": workflow_id,
        "route": _route_dict(route),
        "metadata": metadata,
        "offline": offline_result,
        "offline_recording_path": (offline_result or {}).get("offline_path"),
        "offline_recording_paths": offline_paths,
        "timing": timing,
        "elapsed_ms": total,
    }


async def run_online_phase_async(
    question: str,
    *,
    model_name: str = "gpt-4o-mini",
    remote_model: bool = True,
    recursion_limit: int = 200,
) -> Dict[str, Any]:
    """Online ReAct only — returns partial result for GUI phase 1."""
    t0 = time.perf_counter()
    route = await route_question_async(question)
    route_ms = round((time.perf_counter() - t0) * 1000)

    t1 = time.perf_counter()
    agent = KgqaAgent(model_name=model_name, remote_model=remote_model)
    online_answer, metadata = await agent.ask(
        question,
        route=route,
        recursion_limit=recursion_limit,
    )
    online_ms = round((time.perf_counter() - t1) * 1000)

    rec_info = extract_recording_info(online_answer=online_answer, metadata=metadata)
    recording_path = rec_info.get("recording_path")
    recording_paths = rec_info.get("recording_paths") or []
    workflow_id = rec_info.get("workflow_id") or metadata.get("workflow_id")

    return _build_result(
        question=question,
        route=route,
        online_answer=online_answer,
        metadata=metadata,
        recording_path=recording_path,
        recording_paths=recording_paths,
        workflow_id=workflow_id,
        offline_result=None,
        timing={
            "route_ms": route_ms,
            "online_ms": online_ms,
            "offline_ms": 0,
            "total_ms": route_ms + online_ms,
        },
    )


def run_offline_phase(
    partial: Dict[str, Any],
    *,
    offline_cap: int = 500_000,
    skip_offline_if_no_cache: bool = True,
) -> Dict[str, Any]:
    """Offline replay from online partial result — returns completed result."""
    rec_info = extract_recording_info(
        online_answer=partial.get("online_answer") or "",
        metadata=partial.get("metadata") or {},
    )
    recording_path = partial.get("recording_path") or rec_info.get("recording_path")
    recording_paths = partial.get("recording_paths") or rec_info.get("recording_paths") or []
    workflow_id = partial.get("workflow_id") or rec_info.get("workflow_id")
    offline_result: Optional[Dict[str, Any]] = None
    offline_ms = 0

    if recording_paths or recording_path:
        if not recording_paths and recording_path:
            rec_info = {
                **rec_info,
                "recording_path": recording_path,
                "recording_paths": [recording_path],
            }
        offline_result, offline_ms = _replay_from_rec_info(
            rec_info,
            offline_cap=offline_cap,
            skip_offline_if_no_cache=skip_offline_if_no_cache,
        )

    timing = dict(partial.get("timing") or {})
    timing["offline_ms"] = offline_ms
    timing["total_ms"] = (timing.get("route_ms") or 0) + (timing.get("online_ms") or 0) + offline_ms

    return _build_result(
        question=partial["question"],
        route=partial["route"],
        online_answer=partial["online_answer"],
        metadata=partial["metadata"],
        recording_path=recording_path,
        recording_paths=recording_paths,
        workflow_id=workflow_id,
        offline_result=offline_result,
        timing=timing,
    )


def run_online_phase(
    question: str,
    *,
    model_name: str = "gpt-4o-mini",
    remote_model: bool = True,
    recursion_limit: int = 200,
) -> Dict[str, Any]:
    return asyncio.run(
        run_online_phase_async(
            question,
            model_name=model_name,
            remote_model=remote_model,
            recursion_limit=recursion_limit,
        )
    )


async def run_kgqa_async(
    question: str,
    *,
    model_name: str = "gpt-4o-mini",
    remote_model: bool = True,
    recursion_limit: int = 200,
    auto_offline: bool = True,
    skip_offline_if_no_cache: bool = True,
    offline_cap: int = 500_000,
) -> Dict[str, Any]:
    started = time.perf_counter()
    t_route = time.perf_counter()
    route = await route_question_async(question)
    route_ms = round((time.perf_counter() - t_route) * 1000)

    agent = KgqaAgent(model_name=model_name, remote_model=remote_model)
    t_online = time.perf_counter()
    online_answer, metadata = await agent.ask(
        question,
        route=route,
        recursion_limit=recursion_limit,
    )
    online_ms = round((time.perf_counter() - t_online) * 1000)

    rec_info = extract_recording_info(online_answer=online_answer, metadata=metadata)
    recording_path = rec_info.get("recording_path")
    recording_paths = rec_info.get("recording_paths") or []
    workflow_id = rec_info.get("workflow_id") or metadata.get("workflow_id")

    offline_result: Optional[Dict[str, Any]] = None
    offline_ms = 0
    if auto_offline and (recording_paths or recording_path):
        offline_result, offline_ms = _replay_from_rec_info(
            rec_info,
            offline_cap=offline_cap,
            skip_offline_if_no_cache=skip_offline_if_no_cache,
        )

    total_ms = round((time.perf_counter() - started) * 1000)
    return _build_result(
        question=question,
        route=route,
        online_answer=online_answer,
        metadata=metadata,
        recording_path=recording_path,
        recording_paths=recording_paths,
        workflow_id=workflow_id,
        offline_result=offline_result,
        timing={
            "route_ms": route_ms,
            "online_ms": online_ms,
            "offline_ms": offline_ms,
            "total_ms": total_ms,
        },
    )


def run_kgqa(
    question: str,
    *,
    model_name: str = "gpt-4o-mini",
    remote_model: bool = True,
    recursion_limit: int = 200,
    auto_offline: bool = True,
    skip_offline_if_no_cache: bool = True,
    offline_cap: int = 500_000,
) -> Dict[str, Any]:
    """Synchronous entry point for Streamlit and CLI."""
    return asyncio.run(
        run_kgqa_async(
            question,
            model_name=model_name,
            remote_model=remote_model,
            recursion_limit=recursion_limit,
            auto_offline=auto_offline,
            skip_offline_if_no_cache=skip_offline_if_no_cache,
            offline_cap=offline_cap,
        )
    )
