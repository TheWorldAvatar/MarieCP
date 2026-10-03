"""Human-readable MOF labels from heterogeneous KG row shapes (demo + competency tables)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import unquote

_BRACKET_TOKEN_RE = re.compile(r"\[(.*?)\]")
_MEANINGLESS_NAMES = frozenset({"", "-", "—", "n/a", "na", "none", "null"})


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def is_meaningful_name(value: Any) -> bool:
    text = _clean_text(value)
    return bool(text) and text.lower() not in _MEANINGLESS_NAMES


def truncate_mofid(mofid: str, *, max_len: int = 72) -> str:
    text = _clean_text(mofid)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def decode_core_mof_slug(mof: Any) -> str:
    """
    Decode CoRE-style internal ids (often URL-encoded) into chemistry/topology tokens.

    Example: mof_2000%5BCu%5D%5Bsod%5D3%5BASR%5D1 → Cu · sod · ASR
    """
    raw = unquote(_clean_text(mof))
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        raw = raw.rsplit("/", 1)[-1]
        raw = raw.split("#")[-1]
    if raw.lower().startswith("mof_"):
        raw = raw[4:]
    tokens = _BRACKET_TOKEN_RE.findall(raw)
    if tokens:
        seen: List[str] = []
        for tok in tokens:
            t = tok.strip()
            if t and t not in seen:
                seen.append(t)
        if seen:
            return " · ".join(seen[:6])
    compact = raw.replace("_", " ").strip()
    return compact[:80] if compact else ""


def mof_row_display_label(row: Dict[str, Any]) -> str:
    """Primary human label for a MOF row (schema-driven priority)."""
    if is_meaningful_name(row.get("name")):
        return _clean_text(row["name"])
    if is_meaningful_name(row.get("core_name")):
        return _clean_text(row["core_name"])
    refcode = _clean_text(row.get("refcode"))
    if refcode:
        return refcode
    mofid = _clean_text(row.get("mofid"))
    if mofid:
        return truncate_mofid(mofid)
    decoded = decode_core_mof_slug(row.get("mof"))
    if decoded:
        return decoded
    fallback = _clean_text(row.get("mof"))
    if fallback.startswith(("http://", "https://")):
        return fallback.rsplit("/", 1)[-1].split("#")[-1] or "MOF entry"
    if fallback:
        return truncate_mofid(fallback, max_len=64)
    return "MOF entry"


def mof_row_display_detail(row: Dict[str, Any]) -> str:
    """Secondary context line (source, topology, refcode, metal)."""
    keys = {str(k).lower() for k in row}
    if {"temperature", "method", "solvents", "solvent"} & keys:
        from demos.table_presentation import normalize_synthesis_solvents

        parts: List[str] = []
        method = _clean_text(row.get("method"))
        if method:
            parts.append(method)
        temp = row.get("temperature") or row.get("temp")
        unit = _clean_text(row.get("temperatureUnit") or row.get("temp_unit"))
        if temp not in (None, ""):
            temp_bit = f"{temp} {unit}".strip() if unit else str(temp)
            parts.append(temp_bit)
        solv = normalize_synthesis_solvents(row.get("solvents") or row.get("solvent"))
        if solv:
            parts.append(f"solvents: {solv[:100]}{'…' if len(solv) > 100 else ''}")
        if parts:
            return " · ".join(parts)

    parts: List[str] = []
    topo = _clean_text(row.get("topology"))
    if topo:
        parts.append(f"topology **{topo}**")
    metal = _clean_text(row.get("metal"))
    if metal:
        parts.append(f"metal {metal}")
    src = _clean_text(row.get("sourcedb") or row.get("source"))
    if src:
        parts.append(src)
    refcode = _clean_text(row.get("refcode"))
    if refcode and mof_row_display_label(row) != refcode:
        parts.append(f"refcode {refcode}")
    mofid = _clean_text(row.get("mofid"))
    if mofid and len(mofid) < 48 and mof_row_display_label(row) != mofid:
        parts.append(f"MOFid `{truncate_mofid(mofid, max_len=40)}`")
    return " · ".join(parts)


def mof_row_display_line(row: Dict[str, Any]) -> str:
    """Single bullet-friendly line: label (detail)."""
    label = mof_row_display_label(row)
    detail = mof_row_display_detail(row)
    if detail:
        return f"**{label}** — {detail}"
    return f"**{label}**"


def row_has_mof_identity_fields(row: Dict[str, Any]) -> bool:
    keys = {str(k).lower() for k in row}
    return bool({"mof", "mofid", "name", "refcode"} & keys)


def table_benefits_from_display_column(rows: Sequence[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    if not any(row_has_mof_identity_fields(r) for r in rows if isinstance(r, dict)):
        return False
    for row in rows[: min(20, len(rows))]:
        if not isinstance(row, dict):
            continue
        if not row.get("mof") and not row.get("mofid"):
            continue
        if is_meaningful_name(row.get("name")) or row.get("refcode"):
            return True
        raw_mof = _clean_text(row.get("mof"))
        if raw_mof and (
            "%5B" in raw_mof
            or raw_mof.startswith("mof_")
            or raw_mof.startswith("http")
        ):
            return True
    return False


def enrich_rows_with_display_identity(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add display_label / display_detail without removing raw KG fields."""
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            out.append(row)  # type: ignore[arg-type]
            continue
        enriched = dict(row)
        if row_has_mof_identity_fields(enriched):
            enriched["display_label"] = mof_row_display_label(enriched)
            detail = mof_row_display_detail(enriched)
            if detail:
                enriched["display_detail"] = detail
        out.append(enriched)
    return out
