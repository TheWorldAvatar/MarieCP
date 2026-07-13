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


def is_location_workflow_spec(spec: Dict[str, Any]) -> bool:
    params = spec.get("parameters") or {}
    return bool(spec.get("workflow")) and bool(params.get("include_locations"))
