"""Generic presentation metadata for KGQA table results."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

_NUMERIC_KEYS = frozenset(
    {
        "avgpld",
        "variance",
        "n",
        "thermal",
        "postcomb",
        "precomb",
        "yield",
        "gsa",
        "lcd",
        "pld",
        "lfpd",
        "gpv",
        "burtch",
        "count",
        "uptake",
        "density",
        "asa",
    }
)
_BADGE_KEYS = frozenset({"sourcedb", "source", "refcode"})
_LONG_TEXT_KEYS = frozenset({"mofid", "linker", "node", "nodes", "linkers"})
_DOI_KEYS = frozenset({"doi"})

# Human label + tooltip for common KG / competency table columns.
_COLUMN_GLOSSARY: Dict[str, Dict[str, str]] = {
    "avgpld": {
        "label": "Average PLD (Å)",
        "description": "Mean pore limiting diameter — the narrowest passageway a probe can travel through.",
    },
    "variance": {
        "label": "PLD variance (Å²)",
        "description": "Spread of pore limiting diameter values across source records.",
    },
    "n": {
        "label": "Sample count",
        "description": "Number of values aggregated in this row.",
    },
    "count": {
        "label": "Number of MOFs",
        "description": "How many structures match the question filters in the knowledge graph.",
    },
    "refcode": {
        "label": "CSD refcode",
        "description": "Cambridge Structural Database identifier for the crystal structure.",
    },
    "sourcedb": {
        "label": "Source database",
        "description": "Dataset in the MOF knowledge graph that supplied this record.",
    },
    "source": {
        "label": "Dataset",
        "description": "Which catalogue in the knowledge graph supplied this record.",
    },
    "mofid": {
        "label": "Structure ID (MOFid)",
        "description": "Compact structural identifier (chemistry + topology).",
    },
    "mof": {
        "label": "Internal entry ID",
        "description": "Technical identifier in the knowledge graph (often a URI slug).",
    },
    "name": {
        "label": "MOF name",
        "description": "Common or literature name (when recorded in the graph).",
    },
    "postcomb": {
        "label": "Post-combustion uptake (mmol/g)",
        "description": "Predicted CO₂ uptake from CO₂/N₂ at 0.9 bar and 298 K (ARC_MOF).",
    },
    "precomb": {
        "label": "Pre-combustion uptake (mmol/g)",
        "description": "Predicted CO₂ uptake from CO₂/H₂ at 40 bar and 313 K (ARC_MOF).",
    },
    "thermal": {
        "label": "Thermal stability (°C)",
        "description": "Experimental thermal decomposition temperature.",
    },
    "yield": {
        "label": "Yield (%)",
        "description": "Reported synthesis yield as a percentage.",
    },
    "method": {
        "label": "Synthesis method",
        "description": "Reported preparation route (e.g. solvothermal).",
    },
    "solvent": {
        "label": "Solvents",
        "description": "Solvents used during synthesis.",
    },
    "solvents": {
        "label": "Solvents",
        "description": "Solvents used during synthesis.",
    },
    "topology": {
        "label": "Network topology",
        "description": "RCSR symbol for the underlying crystal net (e.g. sod, pcu).",
    },
    "space_group": {
        "label": "Space group",
        "description": "Crystallographic space group number.",
    },
    "doi": {
        "label": "Publication DOI",
        "description": "Reference DOI linked to this MOF record.",
    },
    "temp": {
        "label": "Temperature",
        "description": "Synthesis or measurement temperature.",
    },
    "tempc": {
        "label": "Temperature (°C)",
        "description": "Synthesis temperature in degrees Celsius.",
    },
    "temp_unit": {
        "label": "Temperature unit",
        "description": "Unit for the reported temperature (Kelvin or Celsius).",
    },
    "time_val": {
        "label": "Duration",
        "description": "Reported reaction or synthesis time.",
    },
    "pld": {
        "label": "PLD (Å)",
        "description": "Pore limiting diameter in ångströms.",
    },
    "lcd": {
        "label": "LCD (Å)",
        "description": "Largest cavity diameter in ångströms.",
    },
    "lfpd": {
        "label": "LFPD (Å)",
        "description": "Largest free-path diameter in ångströms.",
    },
    "gsa": {
        "label": "Surface area (m²/g)",
        "description": "Gravimetric surface area.",
    },
    "asa": {
        "label": "Accessible surface area",
        "description": "Accessible surface area from pore geometry.",
    },
    "density": {
        "label": "Density (g/cm³)",
        "description": "Framework density.",
    },
    "linker": {
        "label": "Linker (SMILES)",
        "description": "Organic linker encoded as SMILES.",
    },
    "node": {
        "label": "Metal node (SMILES)",
        "description": "Secondary building unit / node SMILES.",
    },
    "metal": {
        "label": "Metal",
        "description": "Metal species in the framework.",
    },
    "burtch": {
        "label": "Burtch water-stability label",
        "description": "Experimental water stability class (1 = unstable, 4 = highly stable).",
    },
    "water_pred": {
        "label": "Predicted water stability",
        "description": "Model or literature-derived water stability score for the framework.",
    },
    "burtch": {
        "label": "Burtch label (experimental)",
        "description": "WS24 experimental water-stability class (values ≥ 3 indicate high stability).",
    },
    "acid": {
        "label": "Acid stability (experimental)",
        "description": "Reported acid stability for the framework.",
    },
    "base": {
        "label": "Base stability (experimental)",
        "description": "Reported base stability for the framework.",
    },
    "details": {
        "label": "Stability notes",
        "description": "Additional experimental stability information from the source record.",
    },
    "temperatureunit": {
        "label": "Temperature unit",
        "description": "Unit for synthesis temperature (e.g. Kelvin or Celsius).",
    },
    "display_label": {
        "label": "MOF",
        "description": "Best available short label (name, refcode, or chemistry/topology hint).",
    },
    "display_detail": {
        "label": "At a glance",
        "description": "Dataset, topology, and other context for this row.",
    },
    "temperature": {
        "label": "Synthesis temperature",
        "description": "Temperature reported for the synthesis step.",
    },
}

# Preferred column order for demo tables (human-facing first).
_COLUMN_DISPLAY_PRIORITY: Tuple[str, ...] = (
    "display_label",
    "name",
    "refcode",
    "mofid",
    "metal",
    "topology",
    "thermal",
    "postcomb",
    "precomb",
    "water_pred",
    "burtch",
    "acid",
    "base",
    "details",
    "yield",
    "method",
    "solvents",
    "solvent",
    "temperature",
    "tempc",
    "temp",
    "temperatureunit",
    "temperatureUnit",
    "temp_unit",
    "sourcedb",
    "source",
    "doi",
    "space_group",
    "avgpld",
    "avgPLD",
    "variance",
    "n",
    "count",
    "pld",
    "lcd",
    "lfpd",
    "gsa",
    "asa",
    "density",
    "display_detail",
    "node",
    "linker",
    "mof",
)

# Keys shown only when user toggles “Technical fields”.
_TECHNICAL_DEFAULT_KEYS = frozenset(
    {
        "mof",
        "node",
        "linker",
        "mof_iri",
        "mof_uri",
        "name_lc",
    }
)

# Token replacements for fallback label generation (longest first).
_LABEL_TOKEN_REPLACEMENTS = (
    ("postcomb", "post-combustion uptake"),
    ("precomb", "pre-combustion uptake"),
    ("sourcedb", "source database"),
    ("refcode", "CSD refcode"),
    ("mofid", "MOFid"),
    ("avgpld", "average PLD"),
    ("space_group", "space group"),
    ("temp_unit", "temperature unit"),
    ("time_val", "duration"),
)


def _sample_values(rows: Sequence[Dict[str, Any]], key: str, limit: int = 8) -> List[Any]:
    out: List[Any] = []
    for row in rows:
        val = row.get(key)
        if val in (None, ""):
            continue
        out.append(val)
        if len(out) >= limit:
            break
    return out


def infer_column_kind(key: str, rows: Sequence[Dict[str, Any]]) -> str:
    lk = key.lower()
    if lk in _DOI_KEYS:
        return "doi"
    if lk in _BADGE_KEYS:
        return "badge"
    if lk in _LONG_TEXT_KEYS:
        return "longtext"
    samples = _sample_values(rows, key)
    if lk in _NUMERIC_KEYS or lk.endswith("_count"):
        return "numeric"
    if samples and all(_looks_numeric(v) for v in samples):
        return "numeric"
    if samples and all(str(v).startswith("10.") and "/" in str(v) for v in samples):
        return "doi"
    return "text"


_WATER_TOKENS = frozenset({"h2o", "water", "distilled water", "deionized water", "deionised water"})


def normalize_synthesis_solvents(value: Any) -> str:
    """Clean solvent lists for display: drop bare numbers, unify water/H2O."""
    if value in (None, ""):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parts: List[str] = []
    seen: set[str] = set()
    for raw in re.split(r"[;|]", text):
        tok = raw.strip()
        if not tok:
            continue
        if re.fullmatch(r"[\d.]+", tok):
            continue
        low = tok.lower()
        if low in _WATER_TOKENS or low == "h2o":
            tok = "water"
        elif "water" in low and len(low) < 40:
            tok = "water"
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        parts.append(tok)
    return "; ".join(parts)


def _looks_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _glossary_entry(key: str) -> Optional[Dict[str, str]]:
    lk = key.lower()
    if lk in _COLUMN_GLOSSARY:
        return _COLUMN_GLOSSARY[lk]
    if key in _COLUMN_GLOSSARY:
        return _COLUMN_GLOSSARY[key]
    return None


def _fallback_label(key: str) -> str:
    lk = key.lower()
    text = lk
    for old, new in _LABEL_TOKEN_REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", key) if key != lk else text
    text = text.replace("_", " ").strip()
    # Title-case words but keep acronyms
    words = []
    for word in text.split():
        upper = word.upper()
        if upper in {"PLD", "LCD", "LFPD", "GSA", "ASA", "MOF", "DOI", "CSD", "RCSR", "CO2", "N2", "H2"}:
            words.append(upper if word.isupper() or len(word) <= 4 else word.capitalize())
        elif word.lower() in {"avg", "max", "min"}:
            words.append(word.capitalize() + ".")
        else:
            words.append(word.capitalize())
    return " ".join(words)


def human_column_label(key: str, *, columns: Optional[Sequence[str]] = None) -> str:
    entry = _glossary_entry(key)
    if entry:
        return entry["label"]
    return _fallback_label(key)


def _resolve_key(name: str, keys: Sequence[str]) -> Optional[str]:
    key_set = set(keys)
    if name in key_set:
        return name
    lower_map = {k.lower(): k for k in keys}
    return lower_map.get(name.lower())


def _display_detail_redundant_with_source(
    keys: Sequence[str],
    rows: Sequence[Dict[str, Any]],
) -> bool:
    src = _resolve_key("sourcedb", keys) or _resolve_key("source", keys)
    det = _resolve_key("display_detail", keys)
    if not src or not det or not rows:
        return False
    for row in rows[: min(40, len(rows))]:
        if str(row.get(det) or "").strip() != str(row.get(src) or "").strip():
            return False
    return True


def plan_display_columns(
    keys: Sequence[str],
    rows: Sequence[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """Order columns for humans and split default-visible vs technical."""
    if not keys:
        return [], []

    ordered: List[str] = []
    seen: set[str] = set()
    for pref in _COLUMN_DISPLAY_PRIORITY:
        actual = _resolve_key(pref, keys)
        if actual and actual not in seen:
            ordered.append(actual)
            seen.add(actual)
    for key in keys:
        if key not in seen:
            ordered.append(key)
            seen.add(key)

    has_display = _resolve_key("display_label", keys) is not None
    has_sourcedb = _resolve_key("sourcedb", keys) is not None
    only_count = len(ordered) == 1 and _resolve_key("count", ordered) is not None
    detail_is_redundant = _display_detail_redundant_with_source(ordered, rows)

    visible: List[str] = []
    hidden: List[str] = []
    for key in ordered:
        lk = key.lower()
        hide = lk in _TECHNICAL_DEFAULT_KEYS
        if lk == "mof" and has_display:
            hide = True
        if lk == "source" and has_sourcedb:
            hide = True
        if lk == "display_detail" and detail_is_redundant:
            hide = True
        if only_count and lk == "count":
            hide = False
        (hidden if hide else visible).append(key)
    return visible, hidden


def column_header_label(key: str, *, all_columns: Sequence[str]) -> str:
    """Context-aware header text for UI and exports."""
    if len(all_columns) == 1 and key.lower() == "count":
        return "Number of matching MOFs"
    return human_column_label(key)


def human_column_description(key: str) -> str:
    entry = _glossary_entry(key)
    if entry and entry.get("description"):
        return entry["description"]
    label = human_column_label(key)
    return f"Knowledge-graph field “{key}” — displayed as {label}."


def _table_title(question: str, columns: Sequence[str], row_count: int) -> str:
    q = (question or "").strip()
    cols = {c.lower() for c in columns}
    if {"thermal", "refcode"} <= cols:
        return f"Thermal stability records ({row_count:,})"
    if "postcomb" in cols or "precomb" in cols:
        return f"Binary gas uptake ({row_count:,})"
    if {"avgpld", "variance"} <= cols:
        return "Pore limiting diameter statistics"
    if {"method", "solvent", "yield"} & cols:
        return f"Synthesis routes ({row_count:,})"
    if "topology" in cols:
        return f"Topology matches ({row_count:,})"
    if q:
        short = q[:72] + ("…" if len(q) > 72 else "")
        return f"Results: {short}"
    return f"Results ({row_count:,} rows)"


def _chart_spec(columns: Sequence[str], rows: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    cols = list(columns)
    lower = [c.lower() for c in cols]
    label_key = None
    for candidate in ("display_label", "refcode", "name", "mofid", "mof"):
        if candidate in lower:
            label_key = cols[lower.index(candidate)]
            break
    value_key = None
    for candidate in ("thermal", "postcomb", "precomb", "avgpld", "yield", "gsa"):
        if candidate in lower:
            value_key = cols[lower.index(candidate)]
            break
    if not label_key or not value_key or len(rows) < 2:
        return None
    return {
        "type": "bar",
        "x_key": label_key,
        "y_key": value_key,
        "y_label": human_column_label(value_key),
        "top_n": min(10, len(rows)),
    }


def enrich_table_item(
    item: Dict[str, Any],
    *,
    question: str = "",
    table_index: int = 0,
) -> Dict[str, Any]:
    """Attach title, column metadata, and optional chart spec to a table item."""
    if item.get("type") != "table":
        return item
    vars_ = item.get("vars") or item.get("columns") or []
    bindings = item.get("bindings") or item.get("data") or []
    if not vars_ or not bindings:
        return item

    from demos.mof_display_identity import (
        enrich_rows_with_display_identity,
        table_benefits_from_display_column,
    )

    bindings = enrich_rows_with_display_identity(bindings)
    for row in bindings:
        for sk in ("solvents", "solvent"):
            if sk in row and row.get(sk) not in (None, ""):
                row[sk] = normalize_synthesis_solvents(row[sk])
    if table_benefits_from_display_column(bindings):
        extra = [k for k in ("display_label", "display_detail") if bindings[0].get(k)]
        vars_ = extra + [v for v in vars_ if v not in extra]

    visible_cols, hidden_cols = plan_display_columns(vars_, bindings)
    ordered_cols = visible_cols + hidden_cols

    columns_meta: List[Dict[str, Any]] = []
    for key in ordered_cols:
        columns_meta.append(
            {
                "key": key,
                "label": column_header_label(key, all_columns=ordered_cols),
                "description": human_column_description(key),
                "kind": infer_column_kind(key, bindings),
                "visible": key in visible_cols,
            }
        )

    enriched = dict(item)
    enriched["vars"] = ordered_cols
    enriched["display_columns"] = visible_cols
    enriched["technical_columns"] = hidden_cols
    enriched["bindings"] = bindings
    enriched["title"] = item.get("title") or _table_title(
        question, visible_cols or ordered_cols, len(bindings)
    )
    enriched["row_count"] = len(bindings)
    enriched["columns_meta"] = columns_meta
    chart = _chart_spec(visible_cols or ordered_cols, bindings)
    if chart:
        y_key = chart.get("y_key")
        if y_key:
            chart["y_label"] = column_header_label(y_key, all_columns=ordered_cols)
        x_key = chart.get("x_key")
        if x_key:
            chart["x_label"] = column_header_label(x_key, all_columns=ordered_cols)
    if chart:
        enriched["chart"] = chart
    enriched["table_index"] = table_index
    return enriched


def enrich_data_items(data: Sequence[Dict[str, Any]], *, question: str = "") -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    table_idx = 0
    for item in data:
        if item.get("type") == "table":
            out.append(enrich_table_item(item, question=question, table_index=table_idx))
            table_idx += 1
        else:
            out.append(dict(item))
    return out


def enrich_marie_tables(data: Sequence[Dict[str, Any]], *, question: str = "") -> List[Dict[str, Any]]:
    """Enrich Marie API tables that use columns/data instead of vars/bindings."""
    out: List[Dict[str, Any]] = []
    table_idx = 0
    for item in data:
        if item.get("type") != "table":
            out.append(dict(item))
            continue
        twa_item = {
            "type": "table",
            "vars": item.get("columns") or item.get("vars") or [],
            "bindings": item.get("data") or item.get("bindings") or [],
        }
        enriched = enrich_table_item(twa_item, question=question, table_index=table_idx)
        table_idx += 1
        marie_item = {
            "type": "table",
            "columns": enriched.get("vars") or [],
            "data": enriched.get("bindings") or [],
        }
        for key in (
            "title",
            "row_count",
            "columns_meta",
            "chart",
            "table_index",
            "display_columns",
            "technical_columns",
        ):
            if key in enriched:
                marie_item[key] = enriched[key]
        out.append(marie_item)
    return out
