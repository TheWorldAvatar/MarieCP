"""
Generic workflow parameter extraction and binding for NL questions.

Workflows declare a ``parameters`` schema (defaults + comparator hints).
Values are parsed from the question text and merged with optional overrides
before ``$param`` substitution in filter transforms.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

_THRESHOLD_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:greater than|more than|above|over)\s+([\d][\d,.\s]*)", re.I), "gt"),
    (re.compile(r"(?:less than|below|under)\s+([\d][\d,.\s]*)", re.I), "lt"),
    (re.compile(r"(?:at least|minimum of|min\.?)\s+([\d][\d,.\s]*)", re.I), "gte"),
    (re.compile(r"(?:at most|maximum of|max\.?)\s+([\d][\d,.\s]*)", re.I), "lte"),
    (re.compile(r"(?:>=)\s*([\d][\d,.\s]*)"), "gte"),
    (re.compile(r"(?:<=)\s*([\d][\d,.\s]*)"), "lte"),
    (re.compile(r"(?<![<>=])(>)\s*([\d][\d,.\s]*)"), "gt"),
    (re.compile(r"(?<![<>=])(<)\s*([\d][\d,.\s]*)"), "lt"),
]


def _parse_float(text: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    return float(cleaned) if cleaned else 0.0


def extract_ordered_thresholds(question: str) -> List[Tuple[str, float]]:
    """Return comparative thresholds in question order: [(op, value), ...]."""
    hits: List[Tuple[int, str, float]] = []
    for pattern, op in _THRESHOLD_PATTERNS:
        for match in pattern.finditer(question):
            groups = match.groups()
            raw = groups[-1] if groups else ""
            if not raw:
                continue
            hits.append((match.start(), op, _parse_float(str(raw))))
    hits.sort(key=lambda item: item[0])
    out: List[Tuple[str, float]] = []
    seen: set[Tuple[str, float]] = set()
    for _pos, op, val in hits:
        key = (op, val)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _comparator_match(expected: Optional[str], actual: str) -> bool:
    if not expected:
        return True
    if expected == actual:
        return True
    if expected == "gt" and actual in ("gt", "gte"):
        return True
    if expected == "lt" and actual in ("lt", "lte"):
        return True
    if expected == "gte" and actual == "gt":
        return True
    if expected == "lte" and actual == "lt":
        return True
    return False


def resolve_workflow_parameters(
    workflow: Dict[str, Any],
    question: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge schema defaults, parsed question thresholds, and explicit overrides."""
    schema: Dict[str, Any] = workflow.get("parameters") or {}
    if not schema:
        return dict(overrides or {})

    out: Dict[str, Any] = {}
    for name, spec in schema.items():
        default = spec.get("default") if isinstance(spec, dict) else spec
        out[name] = default

    thresholds = extract_ordered_thresholds(question)
    ordered = sorted(
        schema.items(),
        key=lambda item: int((item[1] or {}).get("order", 0)) if isinstance(item[1], dict) else 0,
    )
    pool = list(thresholds)
    for name, spec in ordered:
        if not isinstance(spec, dict):
            continue
        comparator = spec.get("comparator")
        if not pool:
            break
        pick: Optional[int] = None
        for idx, (op, _val) in enumerate(pool):
            if _comparator_match(comparator, op):
                pick = idx
                break
        if pick is None:
            pick = 0
        _op, value = pool.pop(pick)
        out[name] = value

    if overrides:
        out.update(overrides)
    return out


def seed_workflow_variables(
    workflow: Dict[str, Any],
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Build variable pool for ``$param`` resolution in workflow steps."""
    variables: Dict[str, Any] = dict(workflow.get("variables") or {})
    variables.update(parameters)
    for key, val in workflow.items():
        if key in {
            "id",
            "title",
            "question",
            "steps",
            "answer_variable",
            "parameters",
            "variables",
            "tags",
            "stamp_row_columns",
        }:
            continue
        if isinstance(val, (int, float, str, bool)):
            variables.setdefault(key, parameters.get(key, val))
    return variables


def parameters_hint_text(parameters: Dict[str, Any]) -> str:
    if not parameters:
        return ""
    payload = json.dumps(parameters, ensure_ascii=False)
    return (
        f"\nParsed workflow parameters from the question: {payload}. "
        "Pass the same object as `parameters_json` to `run_competency_online` "
        "(JSON string). Threshold changes in the question must change these values."
    )


def parse_parameters_json(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("parameters_json must be a JSON object")
    return data


def workflow_with_parameters(
    workflow: Dict[str, Any],
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Shallow copy; parameters are carried via variables, not baked into steps."""
    wf = deepcopy(workflow)
    wf["variables"] = seed_workflow_variables(wf, parameters)
    wf["_resolved_parameters"] = parameters
    return wf
