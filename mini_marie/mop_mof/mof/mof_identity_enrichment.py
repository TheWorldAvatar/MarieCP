"""
Generic MOF row identity enrichment (names, refcodes, MOFid) for any competency result shape.

Used by MCP tools, offline replay, and Marie demo presentation — not tied to one question.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING
from urllib.parse import unquote

from mini_marie.mop_mof.mof.mof_operations import (
    MOFS_PREFIX,
    _escape_literal,
    execute_sparql,
)

if TYPE_CHECKING:
    from mini_marie.mop_mof.mof.competency_cache import CompetencyCache

IDENTITY_MERGE_FIELDS = (
    "name",
    "refcode",
    "mofid",
    "sourcedb",
    "source",
    "topology",
    "space_group",
)

_MOF_ROW_KEYS = ("mof", "mof_iri", "mof_uri", "entry", "individual")
_CHUNK_SIZE = 20
_MAX_ENTRIES = 80


def _clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_mof_key(value: Any) -> str:
    """Canonical key for joining identity onto result rows."""
    text = unquote(_clean(value))
    if text.startswith(("http://", "https://")):
        text = text.rsplit("/", 1)[-1]
        text = text.split("#")[-1]
    return text.lower()


def extract_mof_keys_from_rows(rows: Sequence[Dict[str, Any]]) -> List[str]:
    keys: List[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for field in _MOF_ROW_KEYS:
            raw = row.get(field)
            if not raw:
                continue
            key = normalize_mof_key(raw)
            if key and key not in seen:
                seen.add(key)
                keys.append(_clean(raw))
            break
    return keys[:_MAX_ENTRIES]


def _values_clause(entries: Sequence[str]) -> str:
    tokens: List[str] = []
    for entry in entries:
        e = _clean(entry)
        if not e:
            continue
        if e.startswith(("http://", "https://")):
            tokens.append(f"<{e}>")
        else:
            escaped = e.replace("\\", "\\\\").replace('"', '\\"')
            tokens.append(f'"{escaped}"')
    return " ".join(tokens)


def lookup_mof_identity_by_entries(
    mof_entries: Sequence[str],
    *,
    timeout: int = 120,
) -> List[Dict[str, Any]]:
    """
    Batch SPARQL lookup: attach hasNames, refcode, MOFid, source, topology to MOF individuals.

    Accepts full IRIs or internal entry tokens (matched with STR(?mof) CONTAINS).
    """
    entries = [_clean(e) for e in mof_entries if _clean(e)][: _MAX_ENTRIES]
    if not entries:
        return []

    out: List[Dict[str, Any]] = []
    for i in range(0, len(entries), _CHUNK_SIZE):
        chunk = entries[i : i + _CHUNK_SIZE]
        iris = [e for e in chunk if e.startswith(("http://", "https://"))]
        frags = [e for e in chunk if e not in iris]
        blocks: List[str] = []

        if iris:
            values = _values_clause(iris)
            blocks.append(
                f"""
  {{
    VALUES ?mof {{ {values} }}
    ?mof a mofs:MetalOrganicFramework .
    OPTIONAL {{ ?mof mofs:hasNames ?name }}
    OPTIONAL {{ ?mof mofs:hasCsdRefcode ?refcode }}
    OPTIONAL {{ ?mof mofs:hasMofidV1 ?mofid }}
    OPTIONAL {{ ?mof mofs:hasSourcedb ?sourcedb }}
    OPTIONAL {{ ?mof mofs:hasRCSRSym ?topology }}
    OPTIONAL {{ ?mof mofs:hasSpaceGroupNumber ?space_group }}
  }}"""
            )

        for frag in frags:
            needle = _escape_literal(unquote(frag).lower())
            blocks.append(
                f"""
  {{
    ?mof a mofs:MetalOrganicFramework .
    FILTER(CONTAINS(LCASE(STR(?mof)), "{needle}"))
    OPTIONAL {{ ?mof mofs:hasNames ?name }}
    OPTIONAL {{ ?mof mofs:hasCsdRefcode ?refcode }}
    OPTIONAL {{ ?mof mofs:hasMofidV1 ?mofid }}
    OPTIONAL {{ ?mof mofs:hasSourcedb ?sourcedb }}
    OPTIONAL {{ ?mof mofs:hasRCSRSym ?topology }}
    OPTIONAL {{ ?mof mofs:hasSpaceGroupNumber ?space_group }}
  }}"""
            )

        if not blocks:
            continue

        query = f"""
PREFIX mofs: <{MOFS_PREFIX}>
SELECT DISTINCT ?mof ?name ?refcode ?mofid ?sourcedb ?topology ?space_group
WHERE {{
  {" UNION ".join(blocks)}
}}
LIMIT 500
"""
        rows = execute_sparql(query, timeout=timeout)
        for row in rows:
            if row.get("sourcedb") and not row.get("source"):
                row["source"] = row["sourcedb"]
            out.append(row)
    return out


def _index_identity_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        mof_key = normalize_mof_key(row.get("mof"))
        if not mof_key:
            continue
        bucket = index.setdefault(mof_key, {})
        for field in IDENTITY_MERGE_FIELDS:
            val = row.get(field)
            if val in (None, ""):
                continue
            if field not in bucket or not bucket[field]:
                bucket[field] = val
    return index


def merge_identity_into_rows(
    rows: Sequence[Dict[str, Any]],
    identity_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Fill missing identity fields on result rows from lookup rows."""
    index = _index_identity_rows(identity_rows)
    if not index:
        return [dict(r) for r in rows if isinstance(r, dict)]

    merged: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out = dict(row)
        key = ""
        for field in _MOF_ROW_KEYS:
            if out.get(field):
                key = normalize_mof_key(out[field])
                break
        if not key:
            merged.append(out)
            continue
        ident = index.get(key)
        if not ident:
            # suffix match for IRI tail vs full IRI keys
            for ik, iv in index.items():
                if key.endswith(ik) or ik.endswith(key):
                    ident = iv
                    break
        if ident:
            for field in IDENTITY_MERGE_FIELDS:
                if out.get(field) in (None, "", "-"):
                    if ident.get(field) not in (None, ""):
                        out[field] = ident[field]
        merged.append(out)
    return merged


def enrich_mof_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    cache: Optional["CompetencyCache"] = None,
    allow_remote: bool = True,
) -> List[Dict[str, Any]]:
    """
    Enrich arbitrary MOF result rows using local facet cache first, then optional SPARQL.
    """
    base = [dict(r) for r in rows if isinstance(r, dict)]
    if not base:
        return []

    keys = extract_mof_keys_from_rows(base)
    if not keys:
        return base

    identity: List[Dict[str, Any]] = []
    if cache is not None:
        identity.extend(cache.local_identity_by_mof_keys(keys))

    covered = {normalize_mof_key(r.get("mof")) for r in identity if r.get("mof")}
    missing = [k for k in keys if normalize_mof_key(k) not in covered]

    if allow_remote and missing:
        try:
            identity.extend(lookup_mof_identity_by_entries(missing))
        except RuntimeError:
            pass

    return merge_identity_into_rows(base, identity)


def parse_rows_json(rows_json: str) -> List[Dict[str, Any]]:
    parsed = json.loads(rows_json)
    if isinstance(parsed, dict):
        for key in ("rows", "data", "bindings", "results"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
    if not isinstance(parsed, list):
        raise ValueError("rows_json must be a JSON array of objects")
    return [r for r in parsed if isinstance(r, dict)]


def parse_entries_json(entries_json: str) -> List[str]:
    parsed = json.loads(entries_json)
    if isinstance(parsed, str):
        return [_clean(parsed)]
    if not isinstance(parsed, list):
        raise ValueError("entries_json must be a JSON array of strings")
    return [_clean(x) for x in parsed if _clean(x)]
