"""Marie demo OntoZeolite search/explorer API backed by local SQLite cache + SPARQL."""

from __future__ import annotations

import sqlite3
import urllib.parse
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mini_marie.marie.chemistry.chemistry_cache import db_path
from mini_marie.marie.chemistry.query_builder import _execute, _prefix_block
from mini_marie.marie.chemistry.zeolite_corpus import ZeoliteCorpusStore

# Marie zeolitic-materials form query keys (module 7997 / page JS)
FRAMEWORK_PARAM = "Framework"
NAME_PARAM = "name"
FORMULA_PARAM = "ChemicalFormula"
FRAMEWORK_COMPONENT_PARAM = "FrameworkComponent"
GUEST_COMPONENT_PARAM = "GuestComponent"
RETURN_FIELD_PARAM = "ReturnField"
FRAMEWORK_CODE_PARAM = "FrameworkCode"
UNIT_CELL_PREFIX = "UnitCell-"

# Numeric / topological property keys used in advanced search forms
TOPO_PROPERTY_KEYS = {
    "AccessibleAreaPerCell",
    "AccessibleAreaPerGram",
    "AccessibleVolume",
    "AccessibleVolumePerCell",
    "OccupiableAreaPerCell",
    "OccupiableAreaPerGram",
    "OccupiableVolume",
    "OccupiableVolumePerCell",
    "SpecificAccessibleArea",
    "SpecificOccupiableArea",
    "Density",
    "FrameworkDensity",
    "TopologicalDensity",
    "RingSizes",
    "SecondaryBU",
    "CompositeBU",
    "SphereDiameter",
    "TAtom",
    "ABCSequence",
}

UNIT_CELL_LENGTHS = {"a", "b", "c"}
UNIT_CELL_ANGLES = {"alpha", "beta", "gamma"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _decode_params(params: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, val in params.items():
        if isinstance(val, list):
            out[key] = [urllib.parse.unquote(str(v)) for v in val if str(v).strip()]
        else:
            out[key] = urllib.parse.unquote(str(val))
    return out


def _parse_multi(params: Dict[str, Any], key: str) -> List[str]:
    raw = params.get(key)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    text = str(raw).strip()
    return [text] if text else []


def _parse_range_filters(
    params: Dict[str, Any],
    *,
    keys: Sequence[str],
    prefix: str = "",
) -> List[Tuple[str, str, float]]:
    filters: List[Tuple[str, str, float]] = []
    for key in keys:
        raw_val = params.get(f"{prefix}{key}", params.get(key, ""))
        raw = raw_val[0] if isinstance(raw_val, list) else str(raw_val or "")
        raw = raw.strip()
        if not raw:
            continue
        for part in raw.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            op, val = part.split(":", 1)
            op = op.strip().lower()
            if op not in {"gte", "lte", "gt", "lt", "eq"}:
                continue
            try:
                filters.append((key, op, float(val.strip())))
            except ValueError:
                continue
    return filters


def _op_sql(op: str) -> str:
    return {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<", "eq": "="}[op]


def _framework_code_from_iri(iri: str) -> str:
    text = iri.strip()
    if not text:
        return ""
    if "ZeoFramework_" in text:
        tail = text.split("ZeoFramework_", 1)[1]
        return tail.split("_", 1)[0].upper()
    return ""


def _sparql_limited(q: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    body = q.rstrip()
    if "LIMIT" not in body.upper():
        body += f"\nLIMIT {max(1, int(limit))}"
    return _execute("ontozeolite", body)


def list_framework_options(limit: int = 500) -> List[Dict[str, str]]:
    """Framework dropdown: {IRI, code}."""
    conn = _connect()
    try:
        if _table_exists(conn, "corpus_zeolite_by_framework"):
            rows = conn.execute(
                """
                SELECT DISTINCT framework_code
                FROM corpus_zeolite_by_framework
                WHERE TRIM(framework_code) != ''
                ORDER BY framework_code
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            if rows:
                out: List[Dict[str, str]] = []
                for row in rows:
                    code = str(row["framework_code"]).strip().upper()
                    if not code:
                        continue
                    out.append(
                        {
                            "IRI": f"http://www.theworldavatar.com/kg/ontozeolite/ZeoFramework_{code}",
                            "code": code,
                        }
                    )
                return out
    finally:
        conn.close()

    q = (
        _prefix_block("ontozeolite")
        + """
SELECT DISTINCT ?fw ?code WHERE {
  ?fw a oz:ZeoliteFramework .
  ?fw oz:hasFrameworkCode ?code .
}
ORDER BY ?code
"""
    )
    rows = _sparql_limited(q, limit=limit)
    return [
        {"IRI": str(r.get("fw", "")).strip(), "code": str(r.get("code", "")).strip().upper()}
        for r in rows
        if str(r.get("fw", "")).strip() and str(r.get("code", "")).strip()
    ]


def _list_iri_label(
    sparql_body: str,
    *,
    iri_key: str = "iri",
    label_key: str = "label",
    limit: int = 500,
) -> List[Dict[str, str]]:
    rows = _sparql_limited(_prefix_block("ontozeolite") + sparql_body, limit=limit)
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        iri = str(row.get(iri_key, "")).strip()
        if not iri or iri in seen:
            continue
        seen.add(iri)
        label = str(row.get(label_key, "")).strip()
        item: Dict[str, str] = {"IRI": iri}
        if label_key == "symbol":
            item["symbol"] = label or iri.rsplit("/", 1)[-1]
        elif label_key == "title":
            item["title"] = label or iri.rsplit("/", 1)[-1]
        else:
            item["label"] = label or iri.rsplit("/", 1)[-1]
        out.append(item)
    return out


def list_framework_components(limit: int = 500) -> List[Dict[str, str]]:
    return _list_iri_label(
        """
SELECT DISTINCT ?iri ?label WHERE {
  ?iri a oz:ChemicalComponent .
  ?iri rdfs:label ?label .
}
ORDER BY ?label
""",
        iri_key="iri",
        label_key="symbol",
        limit=limit,
    )


def list_guest_components(limit: int = 500) -> List[Dict[str, Any]]:
    conn = _connect()
    guests: List[Dict[str, Any]] = []
    try:
        if _table_exists(conn, "corpus_zeolite_properties"):
            rows = conn.execute(
                """
                SELECT DISTINCT property_value
                FROM corpus_zeolite_properties
                WHERE property_local IN ('hasGuestSpecies', 'hasGuestFormula')
                  AND TRIM(property_value) != ''
                ORDER BY property_value
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            for row in rows:
                val = str(row["property_value"]).strip()
                if not val:
                    continue
                guests.append(
                    {
                        "IRI": f"http://www.theworldavatar.com/kg/ontozeolite/guest/{urllib.parse.quote(val, safe='')}",
                        "label": val,
                        "IUPACName": "",
                        "InChI": "",
                    }
                )
            if guests:
                return guests
    finally:
        conn.close()

    return _list_iri_label(
        """
SELECT DISTINCT ?iri ?label WHERE {
  ?m a oz:ZeoliticMaterial .
  ?m oz:hasGuestSpecies ?iri .
  OPTIONAL { ?iri rdfs:label ?label }
}
ORDER BY ?label
""",
        limit=limit,
    )


def list_secondary_building_units(limit: int = 500) -> List[Dict[str, str]]:
    return _list_iri_label(
        """
SELECT DISTINCT ?iri ?label WHERE {
  ?iri a oz:SecondaryBU .
  OPTIONAL { ?iri rdfs:label ?label }
}
ORDER BY ?label
""",
        limit=limit,
    )


def list_composite_building_units(limit: int = 500) -> List[Dict[str, str]]:
    return _list_iri_label(
        """
SELECT DISTINCT ?iri ?label WHERE {
  ?iri a oz:CompositeBU .
  OPTIONAL { ?iri rdfs:label ?label }
}
ORDER BY ?label
""",
        limit=limit,
    )


def list_journals(limit: int = 500) -> List[Dict[str, str]]:
    return _list_iri_label(
        """
SELECT DISTINCT ?iri ?label WHERE {
  ?iri a <http://www.theworldavatar.com/kg/ontoprovenance/Journal> .
  ?iri rdfs:label ?label .
}
ORDER BY ?label
""",
        iri_key="iri",
        label_key="title",
        limit=limit,
    )


def _material_property_map(conn: sqlite3.Connection, iris: Sequence[str]) -> Dict[str, Dict[str, str]]:
    if not iris or not _table_exists(conn, "corpus_zeolite_properties"):
        return {}
    placeholders = ",".join("?" for _ in iris)
    rows = conn.execute(
        f"""
        SELECT material_iri, property_local, property_value
        FROM corpus_zeolite_properties
        WHERE material_iri IN ({placeholders})
        """,
        list(iris),
    ).fetchall()
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        iri = str(row["material_iri"])
        out.setdefault(iri, {})[str(row["property_local"])] = str(row["property_value"])
    return out


def search_zeolitic_materials(params: Dict[str, str], *, limit: int = 200) -> List[Dict[str, Any]]:
    """Advanced zeolitic-material search from URL query params."""
    decoded = _decode_params(params)
    multi_keys = list(decoded.keys())
    for key in multi_keys:
        if key.endswith("[]"):
            decoded[key[:-2]] = decoded.pop(key)

    framework_iri = str(decoded.get(FRAMEWORK_PARAM, "") or "").strip()
    framework_code = (
        _framework_code_from_iri(framework_iri)
        or str(decoded.get(FRAMEWORK_CODE_PARAM, "") or "").strip().upper()
    )
    name = str(decoded.get(NAME_PARAM, "") or "").strip()
    formula = str(decoded.get(FORMULA_PARAM, "") or "").strip()
    guest_iris = _parse_multi(decoded, GUEST_COMPONENT_PARAM)

    conn = _connect()
    try:
        joins = ["FROM corpus_zeolite_materials m"]
        where: List[str] = []
        args: List[Any] = []

        if framework_code:
            where.append("UPPER(m.framework_code) = ?")
            args.append(framework_code.upper())
        if name:
            where.append("(LOWER(COALESCE(m.label,'')) LIKE ? OR LOWER(m.material_iri) LIKE ?)")
            frag = f"%{name.lower()}%"
            args.extend([frag, frag])
        if formula:
            where.append("LOWER(COALESCE(m.formula,'')) LIKE ?")
            args.append(f"%{formula.lower()}%")

        guest_filters: List[str] = []
        for guest in guest_iris:
            guest = guest.strip()
            if not guest:
                continue
            guest_filters.append(
                """
                EXISTS (
                  SELECT 1 FROM corpus_zeolite_properties gp
                  WHERE gp.material_iri = m.material_iri
                    AND gp.property_local IN ('hasGuestSpecies', 'hasGuestFormula')
                    AND (gp.property_value = ? OR gp.property_value LIKE ? OR gp.material_iri = ?)
                )
                """
            )
            frag = guest if guest.startswith("http") else guest.rsplit("/", 1)[-1]
            args.extend([frag, f"%{frag}%", guest])

        if guest_filters:
            where.append("(" + " OR ".join(guest_filters) + ")")

        range_keys = list(TOPO_PROPERTY_KEYS) + [
            f"{UNIT_CELL_PREFIX}{k}" for k in (*UNIT_CELL_LENGTHS, *UNIT_CELL_ANGLES)
        ]
        range_filters = _parse_range_filters(decoded, keys=range_keys)
        if range_filters and _table_exists(conn, "corpus_zeolite_properties"):
            for idx, (prop_key, op, val) in enumerate(range_filters):
                alias = f"p{idx}"
                prop_local = prop_key
                if prop_key.startswith(UNIT_CELL_PREFIX):
                    prop_local = f"has{prop_key.removeprefix(UNIT_CELL_PREFIX)}"
                joins.append(
                    f"INNER JOIN corpus_zeolite_properties {alias} ON {alias}.material_iri = m.material_iri"
                )
                where.append(f"{alias}.property_local = ? AND CAST({alias}.property_value AS REAL) {_op_sql(op)} ?")
                args.extend([prop_local, val])

        sql = f"SELECT DISTINCT m.material_iri, m.label, m.formula, m.framework_code {' '.join(joins)}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.framework_code, m.formula LIMIT ?"
        args.append(max(1, int(limit)))

        rows = conn.execute(sql, args).fetchall()
        iris = [str(r["material_iri"]) for r in rows]
        props = _material_property_map(conn, iris)
        out: List[Dict[str, Any]] = []
        for row in rows:
            iri = str(row["material_iri"])
            item: Dict[str, Any] = {
                "IRI": iri,
                "ChemicalFormula": row["formula"] or "",
                "label": row["label"] or row["formula"] or iri,
            }
            if row["framework_code"]:
                item["FrameworkCode"] = row["framework_code"]
            item.update(props.get(iri, {}))
            out.append(item)
        return out
    finally:
        conn.close()


def search_zeolite_frameworks(
    params: Dict[str, str],
    *,
    partial: bool = False,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Zeolite framework search / explorer partial payload."""
    decoded = _decode_params(params)
    code = str(decoded.get(FRAMEWORK_CODE_PARAM, decoded.get("code", "")) or "").strip().upper()
    return_fields = _parse_multi(decoded, RETURN_FIELD_PARAM)

    q = (
        _prefix_block("ontozeolite")
        + """
SELECT DISTINCT ?fw ?code WHERE {
  ?fw a oz:ZeoliteFramework .
  ?fw oz:hasFrameworkCode ?code .
"""
    )
    if code:
        q += f'  FILTER(STR(?code) = "{code}")\n'
    q += "}\nORDER BY ?code\n"

    rows = _sparql_limited(q, limit=limit)
    out: List[Dict[str, Any]] = []
    for row in rows:
        fw_iri = str(row.get("fw", "")).strip()
        fw_code = str(row.get("code", "")).strip().upper()
        if not fw_iri or not fw_code:
            continue
        item: Dict[str, Any] = {
            "IRI": fw_iri,
            "code": fw_code,
            "FrameworkCode": fw_code,
            "label": fw_code,
        }
        if partial or return_fields:
            item["TopologicalProperties"] = _framework_topo_stub(fw_code, return_fields)
            item["CrystalInformation"] = {}
        out.append(item)
    return out


def _framework_topo_stub(code: str, return_fields: Sequence[str]) -> Dict[str, Any]:
    """Best-effort topological property object for ZeoliteExplorer."""
    topo: Dict[str, Any] = {}
    store = ZeoliteCorpusStore()
    try:
        numeric = {
            r.get("framework_code"): r
            for r in store.materials_numeric_rows(limit=5000)
            if r.get("framework_code")
        }
        row = numeric.get(code.upper())
    finally:
        store.close()

    for field in return_fields:
        if field == "SphereDiameter":
            topo["SphereDiameter"] = {"component": []}
        elif field == "TopologicalDensity":
            topo["TopologicalDensity"] = {"TD10": None, "TD": None}
        elif field == "OccupiableAreaPerCell" and row and row.get("occupiable_area") is not None:
            topo["OccupiableAreaPerCell"] = {"value": row["occupiable_area"]}
        elif field == "OccupiableVolumePerCell" and row and row.get("unit_cell_volume") is not None:
            topo["OccupiableVolumePerCell"] = {"value": row["unit_cell_volume"]}
        else:
            topo.setdefault(field, {"value": None})
    return topo


def cache_status() -> Dict[str, Any]:
    from mini_marie.cache_paths import data_dir, mini_marie_cache_root
    from mini_marie.kg_catalog.catalog import kg_cache_status_text

    store = ZeoliteCorpusStore()
    try:
        stats = store.stats()
        return {
            "ontozeolite_material_rows": stats.get("material_rows", 0),
            "ontozeolite_property_rows": stats.get("property_rows", 0),
            "ontozeolite_framework_index_rows": stats.get("framework_index_rows", 0),
            "ontozeolite_reference_rows": stats.get("reference_rows", 0),
            "ontozeolite_db_path": str(db_path()),
            "ontozeolite_kg_cache_status": kg_cache_status_text(),
            "data_dir": str(data_dir()),
            "cache_root": str(mini_marie_cache_root()),
        }
    finally:
        store.close()


_LOOKUP_HANDLERS = {
    "framework-components": list_framework_components,
    "guest-components": list_guest_components,
    "secondary-building-units": list_secondary_building_units,
    "composite-building-units": list_composite_building_units,
    "journals": list_journals,
}


def _lookup_items(kind: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    handler = _LOOKUP_HANDLERS.get(kind)
    if handler is None:
        raise ValueError(f"unknown ontozeolite lookup kind: {kind}")
    return handler(limit=limit)
