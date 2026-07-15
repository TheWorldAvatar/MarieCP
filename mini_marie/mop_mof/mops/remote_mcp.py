"""Shared MCP tool implementations for remote OntoMOPs Blazegraph."""

from __future__ import annotations

from mini_marie.mop_mof.mops import ontomop_operations as remote


def get_mop_blazegraph_endpoint_status(force_probe: bool = False) -> str:
    return remote.endpoint_status_tsv(force_probe=force_probe)


def get_mop_corpus_statistics(force_probe: bool = False) -> str:
    return remote.remote_or_cached_tsv(
        "get_mop_corpus_stats",
        {},
        remote.get_mop_corpus_stats,
        force_probe=force_probe,
    )


def get_mops_by_outer_diameter_min(min_angstrom: float, limit: int = 10, force_probe: bool = False) -> str:
    args = {"min_angstrom": float(min_angstrom), "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_mops_by_outer_diameter_min",
        args,
        lambda: remote.get_mops_by_outer_diameter_min(min_angstrom, limit=limit),
        force_probe=force_probe,
    )


def get_mops_by_cbu_formula(cbu_formula: str, limit: int = 10, force_probe: bool = False) -> str:
    args = {"cbu_formula": cbu_formula, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_mops_by_cbu_formula",
        args,
        lambda: remote.get_mops_by_cbu_formula(cbu_formula, limit=limit),
        force_probe=force_probe,
    )


def get_assembly_models_by_polyhedral_shape(shape_symbol: str, limit: int = 10, force_probe: bool = False) -> str:
    args = {"shape_symbol": shape_symbol, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_assembly_models_by_polyhedral_shape",
        args,
        lambda: remote.get_assembly_models_by_polyhedral_shape(shape_symbol, limit=limit),
        force_probe=force_probe,
    )


def lookup_remote_mop_by_label(name: str, limit: int = 5, force_probe: bool = False) -> str:
    args = {"name": name, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "lookup_remote_mop_by_label",
        args,
        lambda: remote.lookup_remote_mop_by_label(name, limit=limit),
        force_probe=force_probe,
    )


def get_mop_provenance_by_formula(mop_formula: str, limit: int = 10, force_probe: bool = False) -> str:
    args = {"mop_formula": mop_formula, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_mop_provenance_by_formula",
        args,
        lambda: remote.get_mop_provenance_by_formula(mop_formula, limit=limit),
        force_probe=force_probe,
    )


def get_mop_with_largest_pore_diameter(limit: int = 1, force_probe: bool = False) -> str:
    args = {"limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_mop_with_largest_pore_diameter",
        args,
        lambda: remote.get_mop_with_largest_pore_diameter(limit=limit),
        force_probe=force_probe,
    )


def get_mops_by_reference_doi(doi: str, limit: int = 10, force_probe: bool = False) -> str:
    args = {"doi": doi, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_mops_by_reference_doi",
        args,
        lambda: remote.get_mops_by_reference_doi(doi, limit=limit),
        force_probe=force_probe,
    )


def get_cbus_as_linear_generic_building_units(
    label_fragment: str = "2-linear",
    limit: int = 10,
    force_probe: bool = False,
) -> str:
    args = {"label_fragment": label_fragment, "limit": int(limit)}
    return remote.remote_or_cached_tsv(
        "get_cbus_as_linear_generic_building_units",
        args,
        lambda: remote.get_cbus_as_linear_generic_building_units(label_fragment, limit=limit),
        force_probe=force_probe,
    )


def ontomops_data_routing_note() -> str:
    status = remote.get_endpoint_status(force_probe=False)
    endpoint = status.get("preferred_endpoint") or "(unreachable)"
    return (
        "OntoMOPs competency questions use remote Blazegraph A-box (ontomops_ogm).\n"
        f"Live endpoint: {endpoint}\n"
        "When remote is unreachable, tools automatically fall back to SQLite cache "
        "(data/mini_marie_cache/mop_blazegraph/query_cache.sqlite).\n"
        "Warm page questions: python -m mini_marie.mop_mof.mops.warm_blazegraph_cache --page\n"
        "Force cache-only mode: ONTOMOPS_CACHE_ONLY=1"
    )
