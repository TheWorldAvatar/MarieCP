"""MCP/SPARQL e2e for German city questions on Zaha page (no LLM).

Maps each catalog question to a direct tool or workflow call and checks for data.

  python -m demos.test_german_city_mcp_e2e
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_CATALOG = REPO / "demos" / "german_city_competency_questions.json"


@dataclass
class CaseResult:
    qid: str
    city: str
    question: str
    ok: bool
    detail: str
    elapsed_ms: int
    rows: int = 0


def _rows_ok(rows: List[Dict[str, Any]], *, min_rows: int = 1) -> tuple[bool, str, int]:
    n = len(rows or [])
    if n < min_rows:
        return False, f"expected >= {min_rows} rows, got {n}", n
    sample = json.dumps(rows[0], ensure_ascii=False)[:120]
    return True, f"{n} row(s); sample={sample}", n


def _wf_ok(result: Dict[str, Any], *, min_rows: int = 1) -> tuple[bool, str, int]:
    status = result.get("status")
    trace = result.get("call_trace") or []
    rows = sum(int(s.get("row_count") or 0) for s in trace)
    if status != "pass":
        return False, f"workflow status={status!r}", rows
    digest = result.get("answer_digest") or {}
    auth = digest.get("authoritative") or {}
    if auth:
        return True, f"authoritative={json.dumps(auth, ensure_ascii=False)[:120]}", rows
    if rows >= min_rows:
        return True, f"trace rows={rows}", rows
    return False, f"no authoritative answer; trace rows={rows}", rows


def _run_wf(stem: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    from mini_marie.zaha.twa_city.workflow_engine import load_workflow, run_workflow

    wf = load_workflow(stem)
    merged = dict(wf)
    if params:
        merged.update(params)
    return run_workflow(merged, mode="online", online_limit=10, workflow_name=stem, use_cache=True)


def _checks() -> Dict[str, Callable[[], tuple[bool, str, int]]]:
    from mini_marie.zaha.twa_city.pirmasens_operations import (
        get_co2_savings_stats,
        get_heat_supply_stats,
        get_pirmasens_schema_summary,
        get_top_buildings_by_co2_savings,
        get_top_buildings_by_heat_supply,
    )
    from mini_marie.zaha.twa_city.pirmasens_ontop_operations import (
        list_entities_by_type,
        run_sparql_on_endpoint,
    )
    from mini_marie.zaha.twa_city.twa_city_operations import (
        get_building_count,
        get_buildings_by_usage,
        get_height_stats,
        get_top_buildings_by_height,
    )

    ex = "<https://example.org/>"
    obe = "<https://www.theworldavatar.com/kg/ontobuiltenv/>"

    return {
        "DE-BR-01": lambda: _rows_ok(get_top_buildings_by_height("bremen")[:14], min_rows=1),
        "DE-BR-02": lambda: _rows_ok(get_buildings_by_usage("bremen", "Non-Domestic"), min_rows=1),
        "DE-BR-03": lambda: _rows_ok(get_top_buildings_by_height("bremen")[:10], min_rows=1),
        "DE-KL-01": lambda: _rows_ok(get_top_buildings_by_height("kaiserslautern"), min_rows=1),
        "DE-KL-02": lambda: _rows_ok(get_top_buildings_by_height("kaiserslautern")[:10], min_rows=1),
        "DE-PS-01": lambda: _rows_ok(get_building_count("pirmasens")),
        "DE-PS-02": lambda: _rows_ok(get_height_stats("pirmasens")),
        "DE-PS-03": lambda: _rows_ok(get_top_buildings_by_height("pirmasens")[:7], min_rows=1),
        "DE-PS-04": lambda: _rows_ok(get_top_buildings_by_height("pirmasens")[:8], min_rows=1),
        "DE-PS-05": lambda: _rows_ok(
            [r for r in get_top_buildings_by_height("pirmasens") if float(r.get("height", 0) or 0) >= 60],
            min_rows=0,
        ),
        "DE-PS-06": lambda: _rows_ok(get_heat_supply_stats("pirmasens")),
        "DE-PS-07": lambda: _rows_ok(get_top_buildings_by_heat_supply("pirmasens")[:5], min_rows=1),
        "DE-PS-08": lambda: _rows_ok(get_top_buildings_by_co2_savings("pirmasens")[:6], min_rows=1),
        "DE-PS-09": lambda: _rows_ok(get_building_count("pirmasens")),
        "DE-PS-10": lambda: (
            (True, summary[:160], 1)
            if (summary := get_pirmasens_schema_summary("pirmasens"))
            else (False, "empty schema summary", 0)
        ),
        "DE-PS-11": lambda: _rows_ok(get_heat_supply_stats("pirmasens") + get_co2_savings_stats("pirmasens"), min_rows=2),
        "DE-PS-12": lambda: _rows_ok(get_top_buildings_by_height("pirmasens")[:10], min_rows=1),
        "DE-PS-13": lambda: _rows_ok(get_top_buildings_by_height("pirmasens")[:12], min_rows=1),
        # Pirmasens public toilets (ontop-toilet)
        "DE-PT-01": lambda: _rows_ok(
            list_entities_by_type("toilet", "https://www.theworldavatar.com/kg/ontobuiltenv/Toilet", var_name="toilet"),
            min_rows=1,
        ),
        "DE-PT-02": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "toilet",
                f"""PREFIX obe: {obe}
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?toilet ?geometry WHERE {{ ?toilet a obe:Toilet ; geo:asWKT ?geometry . }}""",
            ),
            min_rows=1,
        ),
        "DE-PT-03": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "toilet",
                f"""PREFIX ex: {ex}
PREFIX obe: {obe}
SELECT ?toilet WHERE {{ ?toilet a obe:Toilet ; ex:isWheelchairAccessible true . }}""",
            ),
            min_rows=1,
        ),
        "DE-PT-04": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "toilet",
                f"""PREFIX ex: {ex}
PREFIX obe: {obe}
SELECT ?toilet WHERE {{ ?toilet a obe:Toilet ; ex:requiresFee false . }}""",
            ),
            min_rows=1,
        ),
        "DE-PT-05": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "toilet",
                f"""PREFIX ex: {ex}
PREFIX obe: {obe}
SELECT ?toilet WHERE {{ ?toilet a obe:Toilet ; ex:isWheelchairAccessible false . }}""",
            ),
            min_rows=1,
        ),
        # Pirmasens plots / zoning (ontop-plots)
        "DE-PL-01": lambda: _rows_ok(
            list_entities_by_type("plots", "https://www.theworldavatar.com/kg/ontoplot/Plot", var_name="plot"),
            min_rows=1,
        ),
        "DE-PL-02": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
SELECT ?plot ?zone WHERE { ?zone zone:hasPlot ?plot . }""",
            ),
            min_rows=1,
        ),
        "DE-PL-03": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?plot ?area WHERE {
  ?plot geo:hasDefaultGeometry ?geom .
  ?geom geo:hasMetricArea ?area .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-04": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?height WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsBuildingHeight ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?height .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-05": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plot WHERE {
  ?zone zone:hasPlot ?plot ;
        zone:hasZoneType ?type .
  ?type rdfs:label "Automeile"@de .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-06": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?grz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsSiteCoverage ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?grz .
  FILTER(?grz > 0.6)
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-07": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?plot ?wkt WHERE {
  ?plot geo:hasDefaultGeometry ?geom .
  ?geom geo:asWKT ?wkt .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-08": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?grz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsSiteCoverage ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?grz .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-09": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?bmz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsBuildingMassRatio ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?bmz .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-10": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?ok WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsHeightAboveNormalNull ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?ok .
}""",
            ),
            min_rows=1,
        ),
        "DE-PL-11": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "plots",
                """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?zone ?type WHERE {
  ?zone zone:hasZoneType ?zt .
  ?zt rdfs:label ?type .
}""",
            ),
            min_rows=1,
        ),
        # Pirmasens solarthermie (ontop-solarthermie)
        "DE-ST-01": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "solarthermie",
                """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?collector WHERE {
  ?building a db:Building ; ub:hasDevice ?collector .
}""",
            ),
            min_rows=1,
        ),
        "DE-ST-02": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "solarthermie",
                """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?heat WHERE {
  ?building ub:hasDevice ?collector .
  ?collector a ub:RoofThermalPlateCollectors ; db:producesEnergy ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?heat .
}""",
            ),
            min_rows=1,
        ),
        "DE-ST-03": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "solarthermie",
                """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?heat WHERE {
  ?building ub:hasDevice ?collector .
  ?collector a ub:RoofThermalTubeCollectors ; db:producesEnergy ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?heat .
}""",
            ),
            min_rows=1,
        ),
        "DE-ST-04": lambda: _rows_ok(
            run_sparql_on_endpoint(
                "solarthermie",
                """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?building ?co2 WHERE {
  ?building ub:hasDevice ?collector .
  ?collector ub:producesCO2Savings ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?co2 .
  FILTER(?co2 > 50)
}""",
            ),
            min_rows=1,
        ),
    }


def run_all() -> List[CaseResult]:
    data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    checks = _checks()
    results: List[CaseResult] = []

    for city_key, block in data.items():
        label = block.get("label") or city_key
        for item in block.get("questions") or []:
            qid = str(item.get("id") or "")
            question = str(item.get("question") or "").strip()
            fn = checks.get(qid)
            t0 = time.perf_counter()
            if not fn:
                results.append(
                    CaseResult(qid, label, question, False, "no mcp check mapped", 0)
                )
                continue
            try:
                ok, detail, rows = fn()
                results.append(
                    CaseResult(
                        qid,
                        label,
                        question,
                        ok,
                        detail,
                        int((time.perf_counter() - t0) * 1000),
                        rows,
                    )
                )
            except Exception as exc:
                results.append(
                    CaseResult(
                        qid,
                        label,
                        question,
                        False,
                        f"{type(exc).__name__}: {exc}",
                        int((time.perf_counter() - t0) * 1000),
                    )
                )
    return results


def main() -> None:
    results = run_all()
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    print(f"\nGerman city MCP e2e: {len(results)} total, {len(passed)} passed, {len(failed)} failed\n")
    print(f"{'ID':<10} {'City':<14} {'ms':>7} {'Rows':>4}  Status")
    print("-" * 88)
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        q_short = r.question[:40] + ("…" if len(r.question) > 40 else "")
        print(f"{r.qid:<10} {r.city:<14} {r.elapsed_ms:>7} {r.rows:>4}  [{mark}] {q_short}")
        if not r.ok:
            print(f"           -> {r.detail}")
    if failed:
        print(f"\nFailed: {', '.join(r.qid for r in failed)}")
        raise SystemExit(1)
    print("\nAll MCP e2e checks passed.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
