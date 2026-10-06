"""German city competency question specs for direct Zaha workflow routing."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[1]
_CATALOG = Path(__file__).resolve().parent / "german_city_competency_questions.json"


@lru_cache(maxsize=1)
def load_german_city_catalog() -> Dict[str, Any]:
    if not _CATALOG.is_file():
        return {}
    return json.loads(_CATALOG.read_text(encoding="utf-8"))


def iter_german_city_questions() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for city_key, block in load_german_city_catalog().items():
        if not isinstance(block, dict):
            continue
        for item in block.get("questions") or []:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    **item,
                    "city_key": city_key,
                    "city_label": block.get("label") or city_key,
                    "qa_domain": block.get("qa_domain") or "city",
                }
            )
    return out


def lookup_german_city_question(question: str) -> Optional[Dict[str, Any]]:
    text = (question or "").strip()
    if not text:
        return None
    for item in iter_german_city_questions():
        if (item.get("question") or "").strip() == text:
            return item
    return None


def is_workflow_spec(spec: Dict[str, Any]) -> bool:
    return bool(spec.get("workflow"))


def is_location_workflow_spec(spec: Dict[str, Any]) -> bool:
    params = spec.get("parameters") or {}
    return is_workflow_spec(spec) and bool(params.get("include_locations"))


@lru_cache(maxsize=1)
def _load_pirmasens_cq_parameters() -> Dict[str, Dict[str, Any]]:
    path = _REPO / "mini_marie" / "zaha" / "twa_city" / "competency_questions_pirmasens.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("questions", raw) if isinstance(raw, dict) else raw
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        question = (item.get("question") or "").strip()
        params = item.get("parameters")
        if question and isinstance(params, dict):
            out[question] = dict(params)
    return out


def resolve_city_workflow_parameters(
    question: str,
    workflow_name: str,
    *,
    spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge catalog parameters with workflow schema defaults."""
    from mini_marie.workflow_parameters import resolve_workflow_parameters
    from mini_marie.zaha.twa_city.workflow_engine import load_workflow

    overrides: Dict[str, Any] = {}
    if spec and spec.get("parameters"):
        overrides.update(dict(spec["parameters"]))
    else:
        overrides.update(_load_pirmasens_cq_parameters().get((question or "").strip(), {}))

    wf = load_workflow(workflow_name)
    return resolve_workflow_parameters(wf, question, overrides or None)
