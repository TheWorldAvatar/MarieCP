"""MOP polyhedra competency specs for direct remote Blazegraph routing on Marie page."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_CATALOG = Path(__file__).resolve().parent / "mop_competency_questions.json"

_TOOL_DISPATCH: Dict[str, Callable[..., str]] = {}


def _tool_registry() -> Dict[str, Callable[..., str]]:
    global _TOOL_DISPATCH
    if _TOOL_DISPATCH:
        return _TOOL_DISPATCH
    from mini_marie.mop_mof.mops import remote_mcp as rm

    _TOOL_DISPATCH = {
        "get_mops_by_outer_diameter_min": rm.get_mops_by_outer_diameter_min,
        "get_mops_by_cbu_formula": rm.get_mops_by_cbu_formula,
        "get_mop_with_largest_pore_diameter": rm.get_mop_with_largest_pore_diameter,
        "get_assembly_models_by_polyhedral_shape": rm.get_assembly_models_by_polyhedral_shape,
        "get_mop_provenance_by_formula": rm.get_mop_provenance_by_formula,
        "get_mops_by_reference_doi": rm.get_mops_by_reference_doi,
        "get_cbus_as_linear_generic_building_units": rm.get_cbus_as_linear_generic_building_units,
        "get_mop_corpus_statistics": rm.get_mop_corpus_statistics,
    }
    return _TOOL_DISPATCH


@lru_cache(maxsize=1)
def load_mop_catalog() -> Dict[str, Any]:
    if not _CATALOG.is_file():
        return {}
    return json.loads(_CATALOG.read_text(encoding="utf-8"))


def iter_mop_questions() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for block_key, block in load_mop_catalog().items():
        if not isinstance(block, dict):
            continue
        for item in block.get("questions") or []:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    **item,
                    "block_key": block_key,
                    "block_label": block.get("label") or block_key,
                    "qa_domain": block.get("qa_domain") or "marie",
                }
            )
    return out


def lookup_mop_question(question: str) -> Optional[Dict[str, Any]]:
    text = (question or "").strip()
    if not text:
        return None
    for item in iter_mop_questions():
        if (item.get("question") or "").strip() == text:
            return item
    return None


def run_mop_competency_tool(spec: Dict[str, Any]) -> str:
    tool = str(spec.get("tool") or "")
    params = dict(spec.get("parameters") or {})
    fn = _tool_registry().get(tool)
    if fn is None:
        raise KeyError(f"Unknown MOP competency tool: {tool}")
    return fn(**params)
