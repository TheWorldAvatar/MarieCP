"""Marie demo OntoSpecies search/explorer API backed by local SQLite cache."""

from __future__ import annotations

import sqlite3
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from mini_marie.marie.chemistry.chemistry_cache import db_path
from mini_marie.marie.chemistry.query_builder import _execute, _prefix_block

# Marie UI query keys (module 1987) → identifier columns in corpus_species_identifiers
IDENTIFIER_COLUMNS = {
    "IUPACName": "iupac",
    "InChI": "inchi",
    "InChIKey": "inchikey",
    "MolecularFormula": "formula",
    "SMILES": "smiles",
    "CID": "cid",
    "ChebiId": "chebi",
}

# Marie phys property keys → corpus_species_physprops_wide columns (subset)
PHYSPROP_COLUMNS = {
    "HydrogenBondDonorCount": "hbond_donors",
    "HydrogenBondAcceptorCount": "hbond_acceptors",
    "PolarSurfaceArea": "tpsa",
    "ExactMass": "exact_mass",
}

CHEMICAL_CLASS = "ChemicalClass"
USE = "Use"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_species(rows: List[sqlite3.Row], *, partial: bool) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = {
            "IRI": row["species_iri"],
            "label": row["primary_label"] or row["species_iri"],
        }
        if not partial:
            item["IUPACName"] = row["iupac"] if "iupac" in row.keys() else ""
            item["InChI"] = row["inchi"] if "inchi" in row.keys() else ""
        out.append(item)
    return out


def _parse_range_filters(params: Dict[str, str]) -> List[Tuple[str, str, float]]:
    """Parse Marie property filters like MolecularWeight=gte:1.2."""
    filters: List[Tuple[str, str, float]] = []
    for key, raw in params.items():
        col = PHYSPROP_COLUMNS.get(key)
        if not col or not raw:
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
                filters.append((col, op, float(val.strip())))
            except ValueError:
                continue
    return filters


def _op_sql(op: str) -> str:
    return {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<", "eq": "="}[op]


def search_species(params: Dict[str, str], *, partial: bool = False, limit: int = 200) -> List[Dict[str, Any]]:
    """Advanced species search from URL query params (Marie search form)."""
    decoded = {k: urllib.parse.unquote(v) for k, v in params.items()}
    conn = _connect()
    try:
        joins: List[str] = []
        where: List[str] = []
        args: List[Any] = []

        joins.append("FROM corpus_species_identifiers i")
        if _table_exists(conn, "corpus_species_physprops_wide"):
            joins.append("LEFT JOIN corpus_species_physprops_wide p ON p.species_iri = i.species_iri")

        use_val = decoded.get(USE, "").strip()
        if use_val and _table_exists(conn, "corpus_species_uses_enriched"):
            joins.append(
                "INNER JOIN corpus_species_uses_enriched u ON u.species_iri = i.species_iri"
            )
            where.append("(u.use_value = ? OR u.use_value LIKE ?)")
            args.extend([use_val, f"%{use_val}%"])

        chem_class = decoded.get(CHEMICAL_CLASS, "").strip()
        class_iris: Optional[List[str]] = None
        if chem_class:
            class_iris = _species_for_chemical_class(chem_class)
            if not class_iris:
                return []
            placeholders = ",".join("?" for _ in class_iris)
            where.append(f"i.species_iri IN ({placeholders})")
            args.extend(class_iris)

        for param_key, col in IDENTIFIER_COLUMNS.items():
            val = decoded.get(param_key, "").strip()
            if not val:
                continue
            if col in {"cid", "chebi"}:
                where.append(
                    """
                    EXISTS (
                      SELECT 1 FROM corpus_species_names n
                      WHERE n.species_iri = i.species_iri
                        AND n.name_type = ?
                        AND LOWER(n.name_value) LIKE ?
                    )
                    """
                )
                args.extend([col, f"%{val.lower()}%"])
            else:
                where.append(f"LOWER(i.{col}) LIKE ?")
                args.append(f"%{val.lower()}%")

        for col, op, val in _parse_range_filters(decoded):
            where.append(f"CAST(p.{col} AS REAL) {_op_sql(op)} ?")
            args.append(val)

        select_cols = "i.species_iri, i.primary_label, i.iupac, i.inchi"
        sql = f"SELECT DISTINCT {select_cols} {' '.join(joins)}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY i.primary_label LIMIT ?"
        args.append(limit)

        rows = conn.execute(sql, args).fetchall()
        return _rows_to_species(rows, partial=partial)
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _species_for_chemical_class(class_iri: str) -> List[str]:
    q = (
        _prefix_block("ontospecies")
        + f"""
SELECT DISTINCT ?species WHERE {{
  ?species a os:Species ;
             os:hasChemicalClass <{class_iri}> .
}}
LIMIT 5000
"""
    )
    rows = _execute("ontospecies", q)
    return [str(r.get("species", "")).strip() for r in rows if r.get("species")]


def list_chemical_classes(limit: int = 500) -> List[Dict[str, str]]:
    q = (
        _prefix_block("ontospecies")
        + """
SELECT DISTINCT ?cls ?label WHERE {
  ?cls a os:ChemicalClass .
  ?cls rdfs:label ?label .
}
ORDER BY ?label
LIMIT %d
"""
        % limit
    )
    rows = _execute("ontospecies", q)
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        iri = str(row.get("cls", "")).strip()
        label = str(row.get("label", "")).strip()
        if not iri or iri in seen:
            continue
        seen.add(iri)
        out.append({"IRI": iri, "label": label or iri})
    return out


def list_uses(limit: int = 500) -> List[Dict[str, str]]:
    conn = _connect()
    try:
        if not _table_exists(conn, "corpus_species_uses"):
            return []
        rows = conn.execute(
            """
            SELECT DISTINCT use_value
            FROM corpus_species_uses
            WHERE TRIM(use_value) != ''
            ORDER BY use_value
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [{"IRI": r["use_value"], "label": r["use_value"]} for r in rows]
    finally:
        conn.close()


def cache_status() -> Dict[str, Any]:
    from mini_marie.cache_paths import data_dir, mini_marie_cache_root
    from mini_marie.kg_catalog.catalog import kg_cache_status_text

    conn = _connect()
    try:
        stats: Dict[str, Any] = {
            "data_dir": str(data_dir()),
            "cache_root": str(mini_marie_cache_root()),
            "db_path": str(db_path()),
        }
        if _table_exists(conn, "corpus_species"):
            stats["species_rows"] = conn.execute("SELECT COUNT(*) FROM corpus_species").fetchone()[0]
        if _table_exists(conn, "corpus_species_names"):
            stats["name_rows"] = conn.execute("SELECT COUNT(*) FROM corpus_species_names").fetchone()[0]
        if _table_exists(conn, "corpus_species_uses"):
            stats["use_rows"] = conn.execute("SELECT COUNT(*) FROM corpus_species_uses").fetchone()[0]
        stats["kg_cache_status"] = kg_cache_status_text()
        return stats
    finally:
        conn.close()
