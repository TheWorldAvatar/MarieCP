"""Composable evidence helpers for Singapore dispersion, ships, and carparks."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from mini_marie.zaha.sg_old.local_store import db_path, ensure_db

DERIV_MAIN = "https://www.theworldavatar.com/kg/ontodispersion/DerivationWithTimeSeries_79119944-40dd-41b3-a924-6307fed779f2"


def get_sg_virtual_sensor_pollutants(limit: int = 20) -> List[Dict[str, Any]]:
    """Virtual sensors in kb: pollutants reported and derivation linkage."""
    ensure_db()
    conn = sqlite3.connect(db_path())
    rows = conn.execute(
        """
        SELECT vs.s AS vs_iri, MAX(vl.o) AS label, MAX(deriv.o) AS derivation,
               GROUP_CONCAT(DISTINCT qt.o) AS pollutant_types,
               COUNT(DISTINCT rep.o) AS quantity_count
        FROM triples vs
        LEFT JOIN triples vl ON vl.ns='kb' AND vl.s=vs.s AND vl.p LIKE '%label%'
        LEFT JOIN triples deriv ON deriv.ns='kb' AND deriv.s=vs.s AND deriv.p LIKE '%belongsTo%'
        LEFT JOIN triples rep ON rep.ns='kb' AND rep.s=vs.s AND rep.p LIKE '%reports%'
        LEFT JOIN triples qt ON qt.ns='kb' AND qt.s=rep.o AND qt.p LIKE '%type%'
        WHERE vs.ns='kb' AND vs.s LIKE '%virtualsensor_%'
        GROUP BY vs.s
        ORDER BY vs.s
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        pollutants = (r[3] or "").split(",") if r[3] else []
        short = [p.rsplit("/", 1)[-1] for p in pollutants if p]
        out.append(
            {
                "virtual_sensor_iri": r[0],
                "label": r[1],
                "derivation_iri": r[2],
                "pollutant_types": "; ".join(short),
                "quantity_links": r[4],
                "values_in_rdf": False,
                "values_via": "quantity->measure->hasTimeSeries->PostGIS",
            }
        )
    if not out:
        return [{"note": "No ontoems virtual sensors in kb cache"}]
    return out


def get_sg_jurong_pollutant_status() -> List[Dict[str, Any]]:
    """KB evidence for whether point pollutant concentrations are reachable."""
    ensure_db()
    conn = sqlite3.connect(db_path())
    jn = conn.execute(
        "SELECT COUNT(*) FROM triples WHERE ns='kb' AND (LOWER(s) LIKE '%jurong%' OR LOWER(o) LIKE '%jurong%')"
    ).fetchone()[0]
    vs = conn.execute(
        "SELECT COUNT(DISTINCT s) FROM triples WHERE ns='kb' AND s LIKE '%virtualsensor_%'"
    ).fetchone()[0]
    co_chain = conn.execute(
        """
        SELECT q.s, m.s, ts.o
        FROM triples q
        JOIN triples t ON t.ns='kb' AND t.s=q.s AND t.o LIKE '%CarbonMonoxideConcentration%'
        JOIN triples hv ON hv.ns='kb' AND hv.s=q.s AND hv.p LIKE '%hasValue%'
        JOIN triples m ON m.ns='kb' AND m.s=hv.o
        LEFT JOIN triples ts ON ts.ns='kb' AND ts.s=m.s AND ts.p LIKE '%hasTimeSeries%'
        WHERE q.ns='kb'
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    return [
        {
            "jurong_triples_in_kb": jn,
            "virtual_sensor_count": vs,
            "virtual_sensor_labels": "all 'Virtual sensor at 0.00 m' (no lat/lon in RDF)",
            "co_quantity_example": co_chain[0] if co_chain else "",
            "co_measure_example": co_chain[1] if co_chain else "",
            "co_timeseries_example": co_chain[2] if co_chain else "",
            "jurong_point_filter_possible": False,
            "singapore_grid_metadata": "get_sg_dispersion_simulations returns pollutants + derivationIri",
            "live_value_api": "GetDispersionSimulations 200; GetPollutantConcentrations/GetColourBar 500 (PostGIS backend); CreateVirtualSensor POST 403",
            "feature_info_params": "iri + endpoint (twa-vf.min.js); returns 500 class-determination error",
            "conclusion": "Singapore-wide CO/PM/uHC grid exists in PostGIS via derivation; Jurong point numerics blocked by backend 500 + no geo on virtual sensors",
        }
    ]


def get_sg_ship_measurable_properties(mmsi: str = "563071320") -> List[Dict[str, Any]]:
    """Static ship measures with RDF numerics vs speed (timeseries-only)."""
    ensure_db()
    conn = sqlite3.connect(db_path())
    base = f"https://www.theworldavatar.com/kg/ontodispersion/Ship{mmsi}"
    label = conn.execute(
        "SELECT o FROM triples WHERE ns='kb' AND s=? AND p LIKE '%label%'", (base,)
    ).fetchone()
    rows = conn.execute(
        """
        SELECT m.s, num.o
        FROM triples m
        JOIN triples num ON num.ns='kb' AND num.s=m.s AND num.p LIKE '%hasNumericalValue%'
        WHERE m.ns='kb' AND m.s LIKE ?
        ORDER BY m.s
        """,
        (f"%Ship{mmsi}%Measure%",),
    ).fetchall()
    speed_ts = conn.execute(
        """
        SELECT o FROM triples WHERE ns='kb' AND s=? AND p LIKE '%hasTimeSeries%'
        """,
        (f"https://www.theworldavatar.com/kg/ontodispersion/Ship{mmsi}SpeedMeasure",),
    ).fetchone()
    conn.close()
    out: List[Dict[str, Any]] = [
        {
            "ship_iri": base,
            "label": label[0] if label else "",
            "speed_timeseries": speed_ts[0] if speed_ts else "",
            "speed_numerical_in_rdf": False,
            "note": "Speed/lat/lon/course share one PostGIS timeseries; static measures below have RDF numerics",
        }
    ]
    for s, val in rows:
        out.append({"measure": s.rsplit("/", 1)[-1], "hasNumericalValue": val})
    return out
