"""SPARQL probes for pirmasens.md competency questions (shared warm + e2e)."""

from __future__ import annotations

from typing import Any, Dict, List

EX_PREFIX = "https://example.org/"
EX = f"<{EX_PREFIX}>"

ENDPOINTS = {
    "toilet": "https://pirmasens.cmpg.io/ontop-toilet/sparql/",
    "plots": "https://pirmasens.cmpg.io/ontop-plots/sparql/",
    "solarthermie": "https://pirmasens.cmpg.io/ontop-solarthermie/sparql/",
}

# Zaha page question IDs → md CQ ids (ontop sections only).
PAGE_DE_TO_MD: Dict[str, str] = {
    "DE-PT-01": "TO-CQ01",
    "DE-PT-02": "TO-CQ02",
    "DE-PT-03": "TO-CQ03",
    "DE-PT-04": "TO-CQ06",
    "DE-PT-05": "TO-CQ04",
    "DE-PL-01": "PL-CQ01",
    "DE-PL-02": "PL-CQ02",
    "DE-PL-03": "PL-CQ03",
    "DE-PL-04": "PL-CQ05",
    "DE-PL-05": "PL-CQ09",
    "DE-PL-06": "PL-CQ12",
    "DE-PL-07": "PL-CQ04",
    "DE-PL-08": "PL-CQ06",
    "DE-PL-09": "PL-CQ07",
    "DE-PL-10": "PL-CQ08",
    "DE-PL-11": "PL-CQ10",
    "DE-ST-01": "ST-CQ01",
    "DE-ST-02": "ST-CQ02",
    "DE-ST-03": "ST-CQ03",
    "DE-ST-04": "ST-CQ05",
}

# Named .sparql files on the main Pirmasens city endpoint used by the Zaha page.
PIRMASENS_CITY_PAGE_QUERY_FILES: List[str] = [
    "heat_supply_stats.sparql",
    "co2_savings_stats.sparql",
    "15_property_coverage.sparql",
]

CASES: List[Dict[str, Any]] = [
    {
        "id": "TO-CQ01",
        "domain": "toilet",
        "question": "What public toilets are available in the knowledge graph?",
        "query": """PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE { ?toilet a obe:Toilet . }""",
        "min_rows": 1,
    },
    {
        "id": "TO-CQ02",
        "domain": "toilet",
        "question": "What is the location (geometry) of each public toilet?",
        "query": """PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?toilet ?geometry WHERE {
  ?toilet a obe:Toilet ; geo:asWKT ?geometry .
}""",
        "min_rows": 1,
    },
    {
        "id": "TO-CQ03",
        "domain": "toilet",
        "question": "Which public toilets are wheelchair accessible?",
        "query": f"""PREFIX ex: {EX}
PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE {{
  ?toilet a obe:Toilet ; ex:isWheelchairAccessible true .
}}""",
        "min_rows": 0,
    },
    {
        "id": "TO-CQ04",
        "domain": "toilet",
        "question": "Which public toilets are not wheelchair accessible?",
        "query": f"""PREFIX ex: {EX}
PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE {{
  ?toilet a obe:Toilet ; ex:isWheelchairAccessible false .
}}""",
        "min_rows": 0,
    },
    {
        "id": "TO-CQ05",
        "domain": "toilet",
        "question": "Which public toilets require a usage fee?",
        "query": f"""PREFIX ex: {EX}
PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE {{
  ?toilet a obe:Toilet ; ex:requiresFee true .
}}""",
        "min_rows": 0,
    },
    {
        "id": "TO-CQ06",
        "domain": "toilet",
        "question": "Which public toilets are free to use?",
        "query": f"""PREFIX ex: {EX}
PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE {{
  ?toilet a obe:Toilet ; ex:requiresFee false .
}}""",
        "min_rows": 0,
    },
    {
        "id": "TO-CQ07",
        "domain": "toilet",
        "question": "Which public toilets provide facilities for both male and female users?",
        "query": f"""PREFIX ex: {EX}
PREFIX obe: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?toilet WHERE {{
  ?toilet a obe:Toilet ;
          ex:hasMaleFacility true ;
          ex:hasFemaleFacility true .
}}""",
        "min_rows": 0,
    },
    {
        "id": "PL-CQ01",
        "domain": "plots",
        "question": "What plots are available in the knowledge graph?",
        "query": """PREFIX plt: <https://www.theworldavatar.com/kg/ontoplot/>
SELECT ?plot WHERE { ?plot a plt:Plot . }""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ02",
        "domain": "plots",
        "question": "Which zone does each plot belong to?",
        "query": """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
SELECT ?plot ?zone WHERE { ?zone zone:hasPlot ?plot . }""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ03",
        "domain": "plots",
        "question": "What is the area of each plot?",
        "query": """PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?plot ?area WHERE {
  ?plot geo:hasDefaultGeometry ?geom .
  ?geom geo:hasMetricArea ?area .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ04",
        "domain": "plots",
        "question": "What is the geometry (WKT) of each plot?",
        "query": """PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?plot ?wkt WHERE {
  ?plot geo:hasDefaultGeometry ?geom .
  ?geom geo:asWKT ?wkt .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ05",
        "domain": "plots",
        "question": "What is the maximum permitted building height for each plot?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?height WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsBuildingHeight ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?height .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ06",
        "domain": "plots",
        "question": "What is the maximum permitted site coverage (GRZ) for each plot?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?grz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsSiteCoverage ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?grz .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ07",
        "domain": "plots",
        "question": "What is the permitted building mass ratio (BMZ) for each plot?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?bmz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsBuildingMassRatio ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?bmz .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ08",
        "domain": "plots",
        "question": "What is the maximum permitted height above normal null (OK) for each plot?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?ok WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsHeightAboveNormalNull ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?ok .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ09",
        "domain": "plots",
        "question": 'Which plots belong to zoning category "Automeile"@de?',
        "query": """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plot WHERE {
  ?zone zone:hasPlot ?plot ;
        zone:hasZoneType ?type .
  ?type rdfs:label "Automeile"@de .
}""",
        "min_rows": 0,
    },
    {
        "id": "PL-CQ10",
        "domain": "plots",
        "question": "What zoning type is associated with each zone?",
        "query": """PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?zone ?type WHERE {
  ?zone zone:hasZoneType ?zt .
  ?zt rdfs:label ?type .
}""",
        "min_rows": 1,
    },
    {
        "id": "PL-CQ11",
        "domain": "plots",
        "question": "Which plots permit buildings taller than 20 metres?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?height WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsBuildingHeight ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?height .
  FILTER(?height > 20)
}""",
        "min_rows": 0,
    },
    {
        "id": "PL-CQ12",
        "domain": "plots",
        "question": "Which plots allow a site coverage greater than 0.6?",
        "query": """PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?plot ?grz WHERE {
  ?reg regs:appliesTo ?plot ;
       regs:allowsSiteCoverage ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?grz .
  FILTER(?grz > 0.6)
}""",
        "min_rows": 0,
    },
    {
        "id": "ST-CQ01",
        "domain": "solarthermie",
        "question": "Which buildings have solar thermal collectors installed?",
        "query": """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?collector WHERE {
  ?building a db:Building ; ub:hasDevice ?collector .
}""",
        "min_rows": 1,
    },
    {
        "id": "ST-CQ02",
        "domain": "solarthermie",
        "question": "What is the annual heat supply of the plate thermal collectors for each building?",
        "query": """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?heat WHERE {
  ?building ub:hasDevice ?collector .
  ?collector a ub:RoofThermalPlateCollectors ; db:producesEnergy ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?heat .
}""",
        "min_rows": 1,
    },
    {
        "id": "ST-CQ03",
        "domain": "solarthermie",
        "question": "What is the annual heat supply of the tube thermal collectors?",
        "query": """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building ?heat WHERE {
  ?building ub:hasDevice ?collector .
  ?collector a ub:RoofThermalTubeCollectors ; db:producesEnergy ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?heat .
}""",
        "min_rows": 1,
    },
    {
        "id": "ST-CQ04",
        "domain": "solarthermie",
        "question": "Which buildings have roofs suitable for solar collectors?",
        "query": """PREFIX bot: <http://w3id.org/bot#>
PREFIX bim: <http://www.theworldavatar.com/ontology/ontobim/OntoBIM.owl#>
PREFIX db: <http://www.purl.org/oema/enaeq/>
SELECT ?building WHERE {
  ?building a db:Building ; bot:containsElement ?roof .
  ?roof bim:isSolarCollectorSuitable true .
}""",
        "min_rows": 0,
    },
    {
        "id": "ST-CQ05",
        "domain": "solarthermie",
        "question": "Which buildings achieve annual CO2 savings greater than 50 kg/m²?",
        "query": """PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
SELECT ?building ?co2 WHERE {
  ?building ub:hasDevice ?collector .
  ?collector ub:producesCO2Savings ?quantity .
  ?quantity om:hasValue ?measure .
  ?measure om:hasNumericalValue ?co2 .
  FILTER(?co2 > 50)
}""",
        "min_rows": 0,
    },
]


def cases_by_id() -> Dict[str, Dict[str, Any]]:
    return {str(c["id"]): c for c in CASES}


def page_ontop_warm_specs() -> List[Dict[str, Any]]:
    """Warm specs for every Zaha page ontop question (toilet / plots / solarthermie)."""
    by_id = cases_by_id()
    specs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for de_id, md_id in PAGE_DE_TO_MD.items():
        case = by_id.get(md_id)
        if not case:
            continue
        key = f"{case['domain']}:{md_id}"
        if key in seen:
            continue
        seen.add(key)
        specs.append(
            {
                "tool": "run_sparql",
                "args": {
                    "endpoint_id": case["domain"],
                    "query": case["query"].strip(),
                },
                "label": f"{de_id}/{md_id}",
            }
        )
    return specs
