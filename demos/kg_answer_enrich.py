"""Live KG probes to enrich PDF-style competency answers at narrative time."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

_SYNTHESIS_DBS = frozenset({"Park_Syn", "SynMOF"})


def _safe_float(value: Any) -> Optional[float]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num


def burtch_water_stability_text(label: Any) -> str:
    try:
        level = int(float(label))
    except (TypeError, ValueError):
        return "unknown water stability"
    if level >= 4:
        return "highly stable (4) water stability"
    if level <= 1:
        return "unstable (1) water stability"
    return f"moderate ({level}) water stability"


def acid_base_text(acid: Any, base: Any) -> str:
    parts: List[str] = []
    for name, val in (("acid", acid), ("base", base)):
        if val in (None, ""):
            continue
        text = str(val).strip().upper()
        if text in ("YES", "TRUE", "1"):
            parts.append(f"stable in {name}")
        elif text in ("NO", "FALSE", "0"):
            parts.append(f"unstable in {name}")
        else:
            parts.append(f"{name}: {val}")
    return "; ".join(parts) if parts else ""


def filter_synthesis_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        source = row.get("sourcedb") or row.get("source") or ""
        if source in _SYNTHESIS_DBS:
            out.append(dict(row))
    return out


def fetch_pld_source_summary(mof_name: str) -> Optional[str]:
    try:
        from mini_marie.mop_mof.mof import mof_competency_operations as co

        rows = co.get_pld_breakdown_by_mof_name(mof_name)
    except Exception:
        return None
    if not rows:
        return None
    sources: Dict[str, List[str]] = {}
    for row in rows:
        src = str(row.get("sourcedb") or "unknown")
        pld = row.get("pld")
        ref = row.get("refcode") or ""
        bit = f"{pld} Å" + (f" ({ref})" if ref else "")
        sources.setdefault(src, []).append(bit)
    parts = []
    for src, values in sorted(sources.items()):
        parts.append(f"**{src}**: {', '.join(values)}")
    return "PLD values by source: " + "; ".join(parts) + "."


def fetch_thermal_count(min_thermal: float = 300) -> Optional[int]:
    try:
        from mini_marie.mop_mof.mof import mof_competency_operations as co

        rows = co.count_thermal_stable_mofs(min_thermal=min_thermal)
    except Exception:
        return None
    if not rows:
        return None
    try:
        return int(float(rows[0].get("count", 0)))
    except (TypeError, ValueError):
        return None


def fetch_ws24_for_refcodes(refcodes: Sequence[str]) -> Optional[Dict[str, Any]]:
    try:
        from mini_marie.mop_mof.mof import mof_competency_operations as co
    except Exception:
        return None
    for refcode in refcodes:
        if not refcode:
            continue
        try:
            rows = co.get_ws24_stability_by_refcode(str(refcode), limit=1)
        except Exception:
            continue
        if rows:
            row = dict(rows[0])
            row["refcode"] = refcode
            return row
    return None


def format_ws24_clause(ws24: Dict[str, Any]) -> str:
    refcode = ws24.get("refcode") or "this MOF"
    burtch = ws24.get("burtch")
    acid = ws24.get("acid")
    base = ws24.get("base")
    water = burtch_water_stability_text(burtch) if burtch not in (None, "") else ""
    ab = acid_base_text(acid, base)
    bits = []
    if burtch not in (None, ""):
        bits.append(
            f"**{refcode}** has a Burtch label of **{burtch}** ({water})"
        )
    if ab:
        bits.append(ab)
    if not bits:
        return ""
    return " ".join(bits) + ", as recorded in the **WS24** dataset."


def aggregate_pore_properties(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick best non-zero pore metrics across sources for one MOFid."""
    best: Dict[str, Any] = {}
    priority = ("CoRE MOF 2025", "CoRE MOF 2019", "ARC_MOF 2025", "Tobassco")
    ordered = sorted(
        rows,
        key=lambda r: (
            priority.index(r.get("sourcedb", ""))
            if r.get("sourcedb") in priority
            else len(priority)
        ),
    )
    for key in ("pld", "lfpd", "gsa", "gpv"):
        for row in ordered:
            val = _safe_float(row.get(key))
            if val is not None and val > 0:
                best[key] = val
                best[f"{key}_source"] = row.get("sourcedb")
                break
    return best


def fetch_pore_properties(mofid: str) -> Dict[str, Any]:
    try:
        from mini_marie.mop_mof.mof import mof_competency_operations as co

        rows = co.get_pore_properties_by_mofid(mofid, limit=20)
    except Exception:
        return {}
    return aggregate_pore_properties(rows)


def format_pore_properties_clause(props: Dict[str, Any]) -> str:
    if not props:
        return ""
    parts: List[str] = []
    labels = (
        ("pld", "PLD", "Å"),
        ("lfpd", "LFPD", "Å"),
        ("gsa", "GSA", "m²/g"),
        ("gpv", "GPV", "m³/g"),
    )
    for key, label, unit in labels:
        val = props.get(key)
        if val is None:
            continue
        parts.append(f"**{label}** = {val:g} {unit}")
    if not parts:
        return ""
    return "Pore properties: " + ", ".join(parts) + "."
