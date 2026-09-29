"""Generic rule-based narratives from KG / workflow table rows (domain-agnostic)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

_TOOL_STEP_SUMMARY_RE = re.compile(
    r"^(?:[a-z_][a-z0-9_]*:\s*\d+\s*rows?|topology=\S.*corpus_count=|.*=\$\w+.*)$",
    re.I,
)
_STEP_BLOCK_RE = re.compile(r"^--- step (\d+) ---\s*$", re.M)
_REFERENCE_AS_RE = re.compile(
    r"\b(?:same\s+(?:topology|structure)\s+as|topology\s+as|similar\s+to)\s+([A-Za-z0-9][A-Za-z0-9\-]+)",
    re.I,
)
_REFERENCE_FOR_RE = re.compile(
    r"\b(?:for|of|recorded\s+for|routes?\s+for)\s+([A-Za-z0-9][A-Za-z0-9\-]+)\??\s*$",
    re.I,
)
_MOF_NAME_IN_Q_RE = re.compile(r"\b(UiO[- ]?66|ZIF[- ]?8|HKUST[- ]?1|MIL[- ]?\d+|DUT[- ]?\d+)\b", re.I)
_LIST_QUESTION_RE = re.compile(
    r"\b(which|list|top|highest|reported\s+as|other|same\s+.+\s+as)\b",
    re.I,
)
_PEER_QUESTION_RE = re.compile(
    r"\b(same\s+(?:topology|structure)\s+as|other\s+\w+|peers?\s+sharing)\b",
    re.I,
)
_PROPERTY_TOKEN_RE = re.compile(
    r"^(?P<gas1>[A-Z0-9]+)(?P<gas2>[A-Z0-9]+)?P(?P<press>[\d_]+)T(?P<temp>\d+)(?P<unit>[a-z]+)?$",
    re.I,
)

_TOP_N_DEFAULT = 5

_HOW_MANY_RE = re.compile(
    r"\bhow many\s+(.+?)(?:\s+are\s+(?:recorded|there)|\?|\.\s*$)",
    re.I,
)
_TOPOLOGY_CATALOG_RE = re.compile(
    r"\b(distributed|distribution|grouped by|across\s+.+\s+source)\b",
    re.I,
)
_STABILITY_SIGNAL_KEYS = frozenset(
    {"water_pred", "burtch", "burtchlabel", "acidstability", "basestability"}
)


def human_number(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if num.is_integer():
        return f"{int(num):,}"
    return f"{num:,.2f}".rstrip("0").rstrip(".")


def short_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    if text.startswith(("http://", "https://")):
        segment = text.rsplit("/", 1)[-1]
        segment = segment.split("#")[-1]
        return segment or text
    return text


def is_weak_tool_summary(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return True
    if _TOOL_STEP_SUMMARY_RE.match(stripped):
        return True
    if re.match(r"^[a-z_][a-z0-9_]*:\s*\d+\s*rows?$", stripped, re.I):
        return True
    if "corpus_count=" in stripped and "topology=" in stripped:
        return True
    if stripped.startswith("Refcodes=") or "filtered synthesis rows=" in stripped:
        return True
    if re.match(r"^[A-Za-z_][\w]*=\[", stripped):
        return True
    return False


def reference_entity_from_question(question: str) -> Optional[str]:
    q = (question or "").strip()
    for pattern in (_REFERENCE_AS_RE, _REFERENCE_FOR_RE):
        match = pattern.search(q)
        if match:
            return match.group(1).strip()
    match = _MOF_NAME_IN_Q_RE.search(q)
    if match:
        return match.group(1).strip()
    return None


def asks_for_peer_list(question: str) -> bool:
    return bool(_PEER_QUESTION_RE.search(question or ""))


def asks_for_list(question: str) -> bool:
    return bool(_LIST_QUESTION_RE.search(question or ""))


def asks_for_topology_catalog(question: str) -> bool:
    return bool(_TOPOLOGY_CATALOG_RE.search(question or ""))


def count_subject_from_question(question: str) -> str:
    q = (question or "").strip()
    match = _HOW_MANY_RE.search(q)
    if match:
        return match.group(1).strip().rstrip("?.")
    if q.lower().startswith("how many"):
        rest = q[8:].strip().rstrip("?.")
        return rest or "matching records"
    return "matching records"


def _table_item_row_total(item: Dict[str, Any]) -> int:
    rows = item.get("bindings") or item.get("data") or []
    n = len(rows) if isinstance(rows, list) else 0
    for key in ("row_count", "total_rows"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        try:
            n = max(n, int(raw))
        except (TypeError, ValueError):
            pass
    return n


def _looks_like_literature_synthesis_routes(rows: Sequence[Dict[str, Any]]) -> bool:
    """Park_Syn / SynMOF style named routes — not aqueous corpora or stability lists."""
    if not rows:
        return False
    keys = _row_keys(rows[0])
    if _STABILITY_SIGNAL_KEYS & keys:
        return False
    if "water_pred" in keys:
        return False
    if "mof" in keys and ("temperature" in keys or "temp" in keys) and (
        "solvents" in keys or "solvent" in keys
    ):
        if "yield" not in keys:
            return False
    route_markers = {"yield", "method", "solvent", "solvents", "temp", "tempc", "temperature"}
    if not (route_markers & keys):
        return False
    if "name" in keys and not ({"yield", "method"} & keys or {"solvent", "solvents"} & keys):
        return False
    return True


def _looks_like_synthesis_condition_corpus(rows: Sequence[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    keys = _row_keys(rows[0])
    return (
        "mof" in keys
        and ("solvents" in keys or "solvent" in keys)
        and ("temperature" in keys or "temp" in keys)
        and "yield" not in keys
    )


def _looks_like_chemistry_fragment_rows(rows: Sequence[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    keys = _row_keys(rows[0])
    return ("node" in keys and "linker" in keys) or ("metal" in keys and "linker" in keys)


def _looks_like_refcoded_publication_rows(rows: Sequence[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    keys = _row_keys(rows[0])
    return "refcode" in keys and ("name" in keys or "doi" in keys)


def decode_binary_property_token(token: str) -> Optional[str]:
    """Decode ARC-style property suffixes, e.g. CO2N2P09T298mmolg."""
    cleaned = (token or "").strip()
    if not cleaned:
        return None
    match = _PROPERTY_TOKEN_RE.match(cleaned)
    if not match:
        return None
    gas1 = match.group("gas1")
    gas2 = match.group("gas2") or ""
    press_token = match.group("press").replace("_", ".")
    try:
        if press_token.startswith("0") and not press_token.startswith("0."):
            press = float("0." + press_token.lstrip("0") or "0")
        else:
            press = float(press_token)
    except ValueError:
        press = press_token
    temp = match.group("temp")
    unit = match.group("unit") or "mmol/g"
    mixture = f"{gas1}/{gas2}" if gas2 else gas1
    return f"{mixture} at {press} bar, {temp} K ({unit})"


def decode_uptake_conditions(field_prefix: str) -> str:
    """Map row field prefixes postcomb/precomb to standard condition text."""
    mapping = {
        "postcomb": decode_binary_property_token("CO2N2P09T298mmolg")
        or "CO₂/N₂ post-combustion (0.9 bar, 298 K)",
        "precomb": decode_binary_property_token("CO2H2P40T313mmolg")
        or "CO₂/H₂ pre-combustion (40 bar, 313 K)",
    }
    return mapping.get(field_prefix, field_prefix)


def _row_keys(row: Dict[str, Any]) -> set[str]:
    return {str(k).lower() for k in row}


def _norm_name(value: Any) -> str:
    return re.sub(r"[\s\-]+", "-", str(value or "").strip().lower())


def filter_reference_rows(
    rows: Sequence[Dict[str, Any]],
    reference: Optional[str],
) -> List[Dict[str, Any]]:
    if not reference or not rows:
        return list(rows)
    ref = _norm_name(reference)
    out: List[Dict[str, Any]] = []
    for row in rows:
        name = row.get("name") or row.get("core_name") or row.get("mof_name")
        if name and _norm_name(name) == ref:
            continue
        mofid = str(row.get("mofid") or "")
        if mofid and ref.replace("-", "") in mofid.lower().replace("-", ""):
            if ref in ("zif-8", "zif8") and "zif" in mofid.lower():
                continue
        out.append(row)
    return out


def _looks_like_identity_rows(rows: Sequence[Dict[str, Any]], question: str) -> bool:
    """Heuristic: named reference MOF identity vs peer/corpus listing rows."""
    if not rows or not asks_for_peer_list(question):
        return False
    keys = _row_keys(rows[0])
    if {"name", "space_group"} <= keys or {"name", "refcode", "mofid", "sourcedb"} <= keys:
        ref = reference_entity_from_question(question)
        if ref and any(_norm_name(r.get("name")) == _norm_name(ref) for r in rows[:5]):
            return True
    return False


def _looks_like_peer_listing_rows(rows: Sequence[Dict[str, Any]], question: str) -> bool:
    if not rows or not asks_for_peer_list(question):
        return False
    keys = _row_keys(rows[0])
    return "mof" in keys and "name" not in keys and "topology" in keys


def score_table_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    question: str,
    step_tool: str = "",
    count_only: bool = False,
) -> int:
    if not rows:
        return -10_000
    score = len(rows)
    keys = _row_keys(rows[0])
    if count_only or (len(rows) == 1 and "count" in keys):
        score -= 5000
    if "identity" in step_tool or step_tool.endswith("get_mof_identity_by_name"):
        if asks_for_peer_list(question):
            score -= 10_000
    if _looks_like_identity_rows(rows, question):
        score -= 10_000
    if _looks_like_peer_listing_rows(rows, question):
        score += 8000
    if asks_for_peer_list(question):
        ref = reference_entity_from_question(question)
        peers = filter_reference_rows(rows, ref)
        if peers and len(peers) < len(rows):
            score += 5000
    if asks_for_list(question) and len(rows) > 1:
        score += 1000
    if {"avgpld", "variance"} <= keys or {"avgpld", "variance", "n"} <= keys:
        score += 8000
    if "thermal" in keys and "refcode" in keys:
        score += 7000
    if "postcomb" in keys or "precomb" in keys:
        score += 7000
    if _STABILITY_SIGNAL_KEYS & keys or "water_pred" in keys:
        score += 8500
    if _looks_like_chemistry_fragment_rows(rows):
        score += 6500
    if _looks_like_refcoded_publication_rows(rows):
        score += 7200
        if "refcode" in (question or "").lower() or "synthesis" in (question or "").lower():
            score += 3000
    if asks_for_topology_catalog(question) and "topology" in keys and "sourcedb" in keys:
        score += 7000
    if {"method", "solvent"} & keys or "yield" in keys:
        if _looks_like_literature_synthesis_routes(rows):
            score += 6000
            if "synthesis" in (question or "").lower():
                sample_source = str(rows[0].get("sourcedb") or rows[0].get("source") or "")
                if sample_source in ("Park_Syn", "SynMOF"):
                    score += 4000
                elif sample_source:
                    score -= 8000
        elif _looks_like_synthesis_condition_corpus(rows):
            score += 6200
    return score


def pick_narrative_rows(
    data: Sequence[Dict[str, Any]],
    question: str,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Choose the best table rows for narrative generation."""
    candidates: List[Tuple[int, List[Dict[str, Any]], int]] = []
    for item in data:
        if item.get("type") != "table":
            continue
        rows = item.get("bindings") or item.get("data") or []
        rows = [r for r in rows if isinstance(r, dict)]
        if not rows:
            continue
        tool = str(item.get("step_tool") or item.get("label") or "")
        score = score_table_rows(rows, question=question, step_tool=tool)
        if asks_for_peer_list(question):
            ref = reference_entity_from_question(question)
            filtered = filter_reference_rows(rows, ref)
            if filtered:
                rows = filtered
        candidates.append((score, rows, _table_item_row_total(item)))

    if not candidates:
        return [], None
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    best = candidates[0][1]
    total = candidates[0][2]
    return best, total


def extract_step_blocks(tool_content: str) -> List[Tuple[int, str]]:
    """Split competency MCP sample_results into per-step TSV blocks."""
    if "sample_results" not in tool_content:
        return []
    tail = tool_content.split("sample_results", 1)[1]
    tail = tail.split("next_step")[0]
    blocks: List[Tuple[int, str]] = []
    matches = list(_STEP_BLOCK_RE.finditer(tail))
    if not matches:
        cleaned = tail.strip()
        return [(1, cleaned)] if cleaned else []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tail)
        blocks.append((int(match.group(1)), tail[start:end].strip()))
    return blocks


def pick_best_step_tsv(tool_content: str, question: str) -> str:
    """From a multi-step competency envelope, return the best step TSV block."""
    from demos.marie_format import parse_tabular_content

    blocks = extract_step_blocks(tool_content)
    if not blocks:
        return ""
    if len(blocks) == 1:
        return blocks[0][1]

    best_score = -10_000
    best_text = blocks[-1][1]
    for _step_num, block in blocks:
        parsed = parse_tabular_content(block)
        if not parsed:
            continue
        _cols, rows = parsed
        score = score_table_rows(rows, question=question)
        if score > best_score:
            best_score = score
            best_text = block
    return best_text


def pick_best_call_trace_rows(
    payload: Dict[str, Any],
    question: str,
) -> List[Dict[str, Any]]:
    """Select the most relevant call_trace step rows from an offline recording."""
    best_score = -10_000
    best_rows: List[Dict[str, Any]] = []
    for step in payload.get("call_trace") or []:
        rows = step.get("rows") or []
        if isinstance(rows, dict):
            rows = rows.get("sample") or []
        if not isinstance(rows, list):
            continue
        rows = [r for r in rows if isinstance(r, dict)]
        if not rows:
            continue
        tool = str(step.get("tool") or step.get("name") or "")
        count_only = bool((step.get("input") or {}).get("count_only"))
        score = score_table_rows(rows, question=question, step_tool=tool, count_only=count_only)
        if asks_for_peer_list(question):
            ref = reference_entity_from_question(question)
            filtered = filter_reference_rows(rows, ref)
            if filtered:
                rows = filtered
        if score > best_score:
            best_score = score
            best_rows = rows
    return best_rows


def _summarize_aggregate_pld(row: Dict[str, Any], question: str) -> Optional[str]:
    from demos.kg_answer_enrich import fetch_pld_source_summary

    keys = _row_keys(row)
    if not {"avgpld", "variance"} <= keys:
        return None
    subject = reference_entity_from_question(question) or "matching MOFs"
    n = row.get("n")
    n_bit = f" (n={human_number(n)} PLD values)" if n not in (None, "") else ""
    lines = [
        f"For **{subject}**, average pore limiting diameter (PLD) is "
        f"**{human_number(row.get('avgPLD') or row.get('avgpld'))} Å** "
        f"with variance **{human_number(row.get('variance'))} Å²**{n_bit}."
    ]
    source_summary = fetch_pld_source_summary(subject)
    if source_summary:
        lines.append(source_summary)
    return "\n".join(lines)


def _summarize_ranked_property_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    value_key: str,
    value_label: str,
    unit: str = "",
    top_n: int = _TOP_N_DEFAULT,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not rows:
        return None
    keys = _row_keys(rows[0])
    if value_key.lower() not in keys:
        return None

    total = total_count if total_count is not None else len(rows)
    min_thermal = 300.0
    if value_key.lower() == "thermal":
        from demos.kg_answer_enrich import (
            fetch_thermal_count,
            fetch_ws24_for_refcodes,
            format_ws24_clause,
        )

        live_count = fetch_thermal_count(min_thermal=min_thermal)
        if live_count is not None:
            total = live_count

    header = (
        f"**{total:,}** MOF(s) have an experimental thermal decomposition temperature "
        f"above **{human_number(min_thermal)} °C**"
        if value_key.lower() == "thermal"
        else f"**{total:,}** record(s) match"
    )
    lines = [f"{header}; top **{min(top_n, len(rows))}** by {value_label}:"]

    for row in rows[:top_n]:
        refcode = row.get("refcode") or short_label(row.get("mof"))
        val = human_number(row.get(value_key))
        source = row.get("sourcedb") or row.get("source") or ""
        doi = row.get("doi") or ""
        unit_bit = f" {unit}" if unit else ""
        extra = f" ({source})" if source else ""
        doi_bit = f" — DOI {doi}" if doi else ""
        lines.append(f"- **{refcode}**: {val}{unit_bit}{extra}{doi_bit}")

    if value_key.lower() == "thermal" and rows:
        top = rows[0]
        refcode = top.get("refcode") or short_label(top.get("mof"))
        val = human_number(top.get(value_key))
        doi = top.get("doi") or ""
        lead = (
            f"**{refcode}** has the highest thermal decomposition temperature of "
            f"**{val} °C**"
        )
        if doi:
            lead += f" from DOI **{doi}**"
        lead += ", recorded in **MOFSimplify Thermal Dataset**."
        lines.insert(1, lead)

        refcodes = [r.get("refcode") for r in rows[:5] if r.get("refcode")]
        ws24 = fetch_ws24_for_refcodes(refcodes)
        ws24_text = format_ws24_clause(ws24) if ws24 else ""
        if ws24_text:
            lines.append(ws24_text)
        elif refcode:
            lines.append(
                f"No **WS24** Burtch/acid–base stability record was found for the top "
                f"thermal MOFs ({', '.join(str(r) for r in refcodes[:3] if r)})."
            )

    return "\n".join(lines)


def _summarize_binary_uptake_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
) -> Optional[str]:
    from demos.kg_answer_enrich import fetch_pore_properties, format_pore_properties_clause

    if not rows:
        return None
    keys = _row_keys(rows[0])
    if not ({"postcomb", "precomb"} & keys or {"mofid"} <= keys and ("postcomb" in keys or "precomb" in keys)):
        return None
    row = rows[0]
    mofid = str(row.get("mofid") or short_label(row.get("mof")) or "Top MOF")
    parts = [f"The MOF with the highest binary-gas uptake has **MOFid**: `{mofid}`."]
    if row.get("postcomb") not in (None, ""):
        cond = decode_uptake_conditions("postcomb")
        parts.append(
            f"- Post-combustion ({cond}): **{human_number(row['postcomb'])} mmol/g**"
        )
    if row.get("precomb") not in (None, ""):
        cond = decode_uptake_conditions("precomb")
        parts.append(
            f"- Pre-combustion ({cond}): **{human_number(row['precomb'])} mmol/g**"
        )
    source = row.get("source") or row.get("sourcedb")
    if source:
        parts.append(f"Source: **{source}**.")
    pore_clause = format_pore_properties_clause(fetch_pore_properties(mofid))
    if pore_clause:
        parts.append(pore_clause)
    if len(rows) > 1 and asks_for_list(question):
        parts.append(f"({len(rows):,} MOFs exceed the uptake thresholds.)")
    return "\n".join(parts)


def _summarize_count_row(row: Dict[str, Any], question: str) -> Optional[str]:
    keys = _row_keys(row)
    if "count" not in keys:
        return None
    extra = keys - {"count", "total", "n", "label"}
    if extra and len(keys) > 3:
        return None
    subject = count_subject_from_question(question)
    return (
        f"The knowledge graph records **{human_number(row.get('count'))}** {subject}."
    )


def _summarize_water_stability_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not rows:
        return None
    keys = _row_keys(rows[0])
    if not (_STABILITY_SIGNAL_KEYS & keys or "water_pred" in keys):
        return None
    total = total_count if total_count is not None else len(rows)
    lines = [
        f"**{total:,}** MOF(s) carry a reported **water-stability** signal in the KG (top sample):"
    ]
    for row in rows[:_TOP_N_DEFAULT]:
        raw_name = str(row.get("name") or "").strip()
        name = raw_name if raw_name and raw_name != "-" else short_label(row.get("mof"))
        name = name or "MOF"
        signal = row.get("water_pred") or row.get("burtch") or row.get("burtchlabel")
        src = row.get("sourcedb") or row.get("source") or ""
        sig_bit = f" — score/label **{human_number(signal)}**" if signal not in (None, "") else ""
        src_bit = f" ({src})" if src else ""
        lines.append(f"- **{name}**{sig_bit}{src_bit}")
    if total > _TOP_N_DEFAULT:
        lines.append(f"See the table for **{total:,}** rows.")
    return "\n".join(lines)


def _summarize_synthesis_condition_corpus(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not _looks_like_synthesis_condition_corpus(rows):
        return None
    total = total_count if total_count is not None else len(rows)
    lines = [
        f"**{total:,}** synthesis record(s) match **aqueous / low-temperature** filters (sample):"
    ]
    for row in rows[:_TOP_N_DEFAULT]:
        entry = short_label(row.get("mof")) or row.get("name") or "MOF"
        temp = row.get("temperature") or row.get("temp")
        unit = str(row.get("temperatureUnit") or row.get("temp_unit") or "").strip()
        solv = row.get("solvents") or row.get("solvent") or ""
        method = row.get("method") or ""
        src = row.get("sourcedb") or row.get("source") or ""
        temp_bit = (
            f" at **{human_number(temp)}** {unit}".rstrip()
            if temp not in (None, "")
            else ""
        )
        method_bit = f", **{method}**" if method else ""
        src_bit = f" ({src})" if src else ""
        solv_short = str(solv)[:120] + ("…" if len(str(solv)) > 120 else "")
        lines.append(
            f"- `{entry}`{temp_bit}{method_bit}; solvents: {solv_short}{src_bit}"
        )
    return "\n".join(lines)


def _summarize_chemistry_fragment_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not _looks_like_chemistry_fragment_rows(rows):
        return None
    total = total_count if total_count is not None else len(rows)
    lines = [
        f"**{total:,}** MOF(s) match the **metal / linker** chemistry filters (sample):"
    ]
    by_source = Counter(
        str(r.get("sourcedb") or r.get("source") or "unknown") for r in rows
    )
    if by_source:
        top_src = by_source.most_common(3)
        src_line = ", ".join(f"**{s}** ({n:,})" for s, n in top_src)
        lines.append(f"By source in sample: {src_line}.")
    for row in rows[:_TOP_N_DEFAULT]:
        label = short_label(row.get("mof")) or row.get("name") or "entry"
        src = row.get("sourcedb") or row.get("source") or ""
        src_bit = f" ({src})" if src else ""
        lines.append(f"- `{label}`{src_bit}")
    return "\n".join(lines)


def _summarize_topology_catalog_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not rows:
        return None
    keys = _row_keys(rows[0])
    if "topology" not in keys:
        return None
    if asks_for_peer_list(question):
        return None
    if not asks_for_topology_catalog(question) and not re.search(
        r"\btopology\b", question or "", re.I
    ):
        return None
    if asks_for_topology_catalog(question) or "distributed" in (question or "").lower():
        pass
    elif not ({"mofid", "topology", "sourcedb"} <= keys or {"topology", "sourcedb"} <= keys):
        return None

    topo = str(rows[0].get("topology") or "unknown")
    total = total_count if total_count is not None else len(rows)
    by_source = Counter(
        str(r.get("sourcedb") or r.get("source") or "unknown") for r in rows
    )
    lines = [
        f"**{total:,}** MOF(s) with **{topo}** topology appear in this sample; "
        f"**{len(by_source)}** source database(s):"
    ]
    for src, n in by_source.most_common(_TOP_N_DEFAULT):
        lines.append(f"- **{src}**: **{n:,}**")
    if len(by_source) > _TOP_N_DEFAULT:
        lines.append(f"- … and **{len(by_source) - _TOP_N_DEFAULT}** more sources in the table.")
    return "\n".join(lines)


def _summarize_refcoded_publication_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    if not _looks_like_refcoded_publication_rows(rows):
        return None
    ref_name = reference_entity_from_question(question)
    total = total_count if total_count is not None else len(rows)
    distinct_rc = len({str(r.get("refcode")) for r in rows if r.get("refcode")})
    header_name = f"**{ref_name}**" if ref_name else "Matching MOF name(s)"
    lines = [
        f"**{total:,}** row(s) link {header_name} to **CSD refcodes** and publications "
        f"({distinct_rc} distinct refcodes in sample):"
    ]
    for row in rows[:_TOP_N_DEFAULT]:
        rc = row.get("refcode") or "?"
        src = row.get("sourcedb") or row.get("source") or ""
        doi = row.get("doi") or ""
        doi_bit = f" — DOI **{doi}**" if doi else ""
        src_bit = f" ({src})" if src else ""
        lines.append(f"- **{rc}**{src_bit}{doi_bit}")
    if total > _TOP_N_DEFAULT:
        lines.append("Expand the table for the full refcode list.")
    return "\n".join(lines)


def _summarize_topology_peers(
    rows: Sequence[Dict[str, Any]],
    question: str,
) -> Optional[str]:
    if not rows:
        return None
    if asks_for_topology_catalog(question):
        return None
    ref = reference_entity_from_question(question)
    keys = _row_keys(rows[0])
    if not ({"topology"} & keys or "mofid" in keys):
        return None
    if not asks_for_peer_list(question) and not ref:
        if "topology" in keys and len(rows) > 3 and "sourcedb" in keys:
            return None

    topology = None
    identity_rows = rows
    if ref and asks_for_peer_list(question):
        for row in rows:
            name = row.get("name")
            if name and _norm_name(name) == _norm_name(ref):
                topology = row.get("topology")
                break
    peer_rows = filter_reference_rows(rows, ref) if ref else list(rows)
    if not topology and peer_rows:
        topology = peer_rows[0].get("topology")
    if not topology and identity_rows:
        topology = identity_rows[0].get("topology")

    if ref and topology:
        header = f"**{ref}** has **{topology}** topology."
    elif topology:
        header = f"Reference topology: **{topology}**."
    else:
        header = "Shared topology records:"

    if not peer_rows:
        return header + " No other MOFs with this topology were returned in the sample."

    lines = [header, "Other MOFs with the same topology include:"]
    for row in peer_rows[:_TOP_N_DEFAULT]:
        mofid = row.get("mofid") or short_label(row.get("mof"))
        refcode = row.get("refcode") or ""
        source = row.get("source") or row.get("sourcedb") or ""
        ref_bit = f", refcode **{refcode}**" if refcode else ""
        src_bit = f" from **{source}**" if source else ""
        lines.append(f"- `{mofid}`{ref_bit}{src_bit}")
    if len(peer_rows) > _TOP_N_DEFAULT:
        lines.append(f"- … and **{len(peer_rows) - _TOP_N_DEFAULT}** more in the table.")
    return "\n".join(lines)


def _summarize_synthesis_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
) -> Optional[str]:
    from demos.kg_answer_enrich import filter_synthesis_rows

    if not rows:
        return None
    if not _looks_like_literature_synthesis_routes(rows):
        return None

    rows = filter_synthesis_rows(rows)
    if not rows:
        subject = reference_entity_from_question(question) or "the MOF"
        return (
            f"No **Park_Syn** or **SynMOF** synthesis routes with yield/method data "
            f"were found for **{subject}** in the knowledge graph."
        )

    subject = reference_entity_from_question(question) or "the MOF"

    def _yield_val(row: Dict[str, Any]) -> float:
        try:
            return float(row.get("yield") or -1)
        except (TypeError, ValueError):
            return -1

    ranked = sorted(rows, key=_yield_val, reverse=True)
    best = ranked[0]
    lines = [
        f"**{len(rows)}** synthesis route(s) from **Park_Syn** / **SynMOF** "
        f"for **{subject}**:"
    ]
    route_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for idx, row in enumerate(rows[:_TOP_N_DEFAULT]):
        label = route_labels[idx] if idx < len(route_labels) else str(idx + 1)
        mof = row.get("name") or subject
        route = f"Route {label}"
        temp = row.get("tempC") or row.get("temp") or row.get("temperature")
        temp_unit = row.get("temp_unit") or row.get("temperatureUnit") or ("°C" if row.get("tempC") else "")
        solvents = row.get("solvent") or row.get("solvents") or ""
        yield_v = row.get("yield")
        source = row.get("sourcedb") or row.get("source") or ""
        temp_bit = f" at **{human_number(temp)}**{temp_unit}" if temp not in (None, "") else ""
        yield_bit = f", yield **{human_number(yield_v)}%**" if yield_v not in (None, "") else ""
        solv_bit = f", solvents: {solvents}" if solvents else ""
        src_bit = f" ({source})" if source else ""
        lines.append(
            f"- **{route}** — **{mof}**{temp_bit}{solv_bit}{yield_bit}{src_bit}"
        )

    if best.get("yield") not in (None, ""):
        best_label = route_labels[0]
        temp = best.get("tempC") or best.get("temp") or best.get("temperature")
        temp_unit = best.get("temp_unit") or best.get("temperatureUnit") or ""
        temp_bit = f" at **{human_number(temp)}**{temp_unit}" if temp not in (None, "") else ""
        solv = best.get("solvent") or best.get("solvents") or ""
        solv_bit = f" with {solv}" if solv else ""
        lines.append(
            f"**Route {best_label}**{temp_bit}{solv_bit} has the highest reported yield "
            f"of **{human_number(best.get('yield'))}%**."
        )
    return "\n".join(lines)


def summarize_rows(
    rows: Sequence[Dict[str, Any]],
    question: str,
    *,
    total_count: Optional[int] = None,
) -> Optional[str]:
    """Build a natural-language answer from tabular rows (schema-driven)."""
    if not rows:
        return None

    row0 = rows[0]
    for fn in (
        lambda: _summarize_aggregate_pld(row0, question),
        lambda: _summarize_count_row(row0, question) if len(rows) == 1 else None,
        lambda: _summarize_water_stability_rows(
            rows, question, total_count=total_count
        ),
        lambda: _summarize_synthesis_condition_corpus(
            rows, question, total_count=total_count
        ),
        lambda: _summarize_ranked_property_rows(
            rows,
            question,
            value_key="thermal",
            value_label="thermal stability",
            unit="°C",
            total_count=total_count,
        ),
        lambda: _summarize_binary_uptake_rows(rows, question),
        lambda: _summarize_topology_catalog_rows(
            rows, question, total_count=total_count
        ),
        lambda: _summarize_topology_peers(rows, question),
        lambda: _summarize_refcoded_publication_rows(
            rows, question, total_count=total_count
        ),
        lambda: _summarize_chemistry_fragment_rows(
            rows, question, total_count=total_count
        ),
        lambda: _summarize_synthesis_rows(rows, question),
    ):
        text = fn()
        if text:
            return text

    if len(rows) == 1:
        keys = _row_keys(row0)
        if "count" in keys and len(keys) <= 3:
            return _summarize_count_row(row0, question)
        preview = ", ".join(
            f"**{human_number(v)}** {k.replace('_', ' ')}"
            for k, v in row0.items()
            if v not in (None, "") and "wkt" not in k.lower()
        )
        if preview:
            return f"Result: {preview}."

    count = total_count if total_count is not None else len(rows)
    if asks_for_list(question):
        return f"Found **{count:,}** matching record(s). See the table for details."
    return None


def summarize_metric_row(row: Dict[str, Any], question: str = "") -> Optional[str]:
    """Single-row summary; delegates to summarize_rows when useful."""
    if not row:
        return None
    return summarize_rows([row], question)


def summarize_from_data(
    question: str,
    data: Sequence[Dict[str, Any]],
) -> Optional[str]:
    rows, total = pick_narrative_rows(data, question)
    if not rows:
        return None
    return summarize_rows(rows, question, total_count=total)
