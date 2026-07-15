"""Warm SQLite cache for remote OntoMOPs Blazegraph queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from mini_marie.mop_mof.mops import ontomop_operations as ops
from mini_marie.mop_mof.mops.mop_blazegraph_cache import MopBlazegraphCache

_REPO = Path(__file__).resolve().parents[2]
_PAGE_CATALOG = _REPO / "demos" / "mop_competency_questions.json"

WARM_SPECS: List[Tuple[str, Dict[str, Any], Callable[[], List[Dict[str, Any]]]]] = [
    ("get_mop_corpus_stats", {}, ops.get_mop_corpus_stats),
    (
        "get_mops_by_outer_diameter_min",
        {"min_angstrom": 70.0, "limit": 10},
        lambda: ops.get_mops_by_outer_diameter_min(70.0, limit=10),
    ),
    (
        "get_assembly_models_by_polyhedral_shape",
        {"shape_symbol": "icosahedral", "limit": 10},
        lambda: ops.get_assembly_models_by_polyhedral_shape("icosahedral", limit=10),
    ),
    (
        "get_mops_by_reference_doi",
        {"doi": "10.1016/j.chempr.2017.02.002", "limit": 10},
        lambda: ops.get_mops_by_reference_doi("10.1016/j.chempr.2017.02.002", limit=10),
    ),
]

_TOOL_FETCHERS: Dict[str, Callable[[Dict[str, Any]], List[Dict[str, Any]]]] = {
    "get_mops_by_outer_diameter_min": lambda p: ops.get_mops_by_outer_diameter_min(
        float(p["min_angstrom"]), limit=int(p.get("limit", 10))
    ),
    "get_mops_by_cbu_formula": lambda p: ops.get_mops_by_cbu_formula(
        str(p["cbu_formula"]), limit=int(p.get("limit", 10))
    ),
    "get_mop_with_largest_pore_diameter": lambda p: ops.get_mop_with_largest_pore_diameter(
        limit=int(p.get("limit", 1))
    ),
    "get_assembly_models_by_polyhedral_shape": lambda p: ops.get_assembly_models_by_polyhedral_shape(
        str(p["shape_symbol"]), limit=int(p.get("limit", 10))
    ),
    "get_mop_provenance_by_formula": lambda p: ops.get_mop_provenance_by_formula(
        str(p["mop_formula"]), limit=int(p.get("limit", 10))
    ),
    "get_mops_by_reference_doi": lambda p: ops.get_mops_by_reference_doi(
        str(p["doi"]), limit=int(p.get("limit", 10))
    ),
    "get_cbus_as_linear_generic_building_units": lambda p: ops.get_cbus_as_linear_generic_building_units(
        str(p.get("label_fragment", "2-linear")), limit=int(p.get("limit", 10))
    ),
    "get_mop_corpus_statistics": lambda _p: ops.get_mop_corpus_stats(),
}


def _page_warm_specs() -> List[Tuple[str, Dict[str, Any], Callable[[], List[Dict[str, Any]]]]]:
    if not _PAGE_CATALOG.is_file():
        return []
    data = json.loads(_PAGE_CATALOG.read_text(encoding="utf-8"))
    out: List[Tuple[str, Dict[str, Any], Callable[[], List[Dict[str, Any]]]]] = []
    for block in data.values():
        if not isinstance(block, dict):
            continue
        for item in block.get("questions") or []:
            tool = str(item.get("tool") or "")
            params = dict(item.get("parameters") or {})
            fn = _TOOL_FETCHERS.get(tool)
            if fn:
                out.append((tool, params, lambda p=params, f=fn: f(p)))
    return out


def _run_warm(specs: List[Tuple[str, Dict[str, Any], Callable[[], List[Dict[str, Any]]]]], force_probe: bool) -> Dict[str, Any]:
    cache = MopBlazegraphCache()
    endpoint = ""
    try:
        endpoint = ops.resolve_endpoint(force_probe=force_probe)
    except Exception as exc:
        endpoint = cache.last_known_endpoint() or ""
        if not cache.has_entries():
            return {
                "endpoint": endpoint,
                "error": str(exc)[:200],
                "results": [],
                "cache_stats": cache.stats(),
            }

    results = []
    for tool, tool_args, fetcher in specs:
        try:
            rows = fetcher()
            key = cache.make_key(tool, tool_args)
            cached = cache.get(tool, tool_args)
            results.append(
                {
                    "tool": tool,
                    "id_args": tool_args,
                    "status": "ok",
                    "rows": len(rows),
                    "cache_key": (cached or {}).get("cache_key", key)[:12],
                    "from_cache": endpoint == "" and bool(cached),
                }
            )
        except Exception as exc:
            cached = cache.get(tool, tool_args)
            if cached:
                results.append(
                    {
                        "tool": tool,
                        "status": "cache_only",
                        "rows": len(cached.get("rows") or []),
                        "remote_error": str(exc)[:120],
                    }
                )
            else:
                results.append({"tool": tool, "status": "error", "error": str(exc)[:200]})

    return {"endpoint": endpoint or cache.last_known_endpoint(), "results": results, "cache_stats": cache.stats()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm OntoMOPs Blazegraph query cache")
    parser.add_argument("--force-probe", action="store_true", help="Re-probe endpoints before fetch")
    parser.add_argument("--page", action="store_true", help="Warm all Marie page competency questions")
    args = parser.parse_args()

    specs = list(WARM_SPECS)
    if args.page:
        specs.extend(_page_warm_specs())

    summary = _run_warm(specs, force_probe=args.force_probe)
    print(json.dumps(summary, indent=2))
    ok = all(r.get("status") in ("ok", "cache_only") for r in summary.get("results") or [])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
