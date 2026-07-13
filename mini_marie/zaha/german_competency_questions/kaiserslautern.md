# Kaiserslautern — Competency Questions (Zaha / twa-city)

**SPARQL endpoint:** `https://kaiserslautern.cmpg.io/ontop/sparql/`  
**Ontop UI:** [https://kaiserslautern.cmpg.io/ontop/ui/](https://kaiserslautern.cmpg.io/ontop/ui/)  
**MCP server:** `twa-city` (`python -m mini_marie.zaha.twa_city.main`)

Catalog source: `demos/german_city_competency_questions.json` (city key `kaiserslautern`).  
Parameterized workflow: `city_ranked_buildings` (`mini_marie/zaha/twa_city/workflows/city_ranked_buildings.json`).

## Data summary (probe)

| Metric | Value |
|--------|------:|
| CityGML buildings | ~118,000 |
| Building IRI | `https://theworldavatar.io/kg/Building/{uuid}` |
| Usage types | OntoBuiltEnv (`Domestic`, `Office`, …) |
| Geo | GeoSPARQL `geo:asWKT`, `geo:hasGeometry` |

See `mini_marie/zaha/twa_city/seed.md` and `BUILDING_SCHEMA.md` (Bremen section uses the same CityGML/OntoBuiltEnv pattern).

## Competency questions

| ID | Question | Workflow | Parameters | Map |
|----|----------|----------|------------|-----|
| DE-KL-01 | What are the tallest buildings in Kaiserslautern? | `city_ranked_buildings` | `city=kaiserslautern`, `top_n=10`, `sort_field=height` | no |
| DE-KL-02 | Find the locations of the 10 highest buildings in Kaiserslautern (2-step: rank then locate) | `city_ranked_buildings` | `city=kaiserslautern`, `top_n=10`, `sort_field=height`, `include_locations=true` | yes |

Legacy named workflow: `top10_buildings_locations_kl` (rank top 10, then fetch WKT).

## SPARQL patterns

### CQ1. Top buildings by measuredHeight

```sparql
PREFIX bldg: <http://www.opengis.net/citygml/building/2.0/>
PREFIX be: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?building ?height ?storeys ?usage_type ?label
WHERE {
  ?building a bldg:Building ;
            bldg:measuredHeight ?height .
  OPTIONAL { ?building bldg:storeysAboveGround ?storeys }
  OPTIONAL {
    ?building be:hasPropertyUsage ?u .
    ?u a ?usage_type .
  }
  OPTIONAL { ?building <http://www.w3.org/2000/01/rdf-schema#label> ?label }
}
ORDER BY DESC(?height)
LIMIT 10
```

### CQ2. Top buildings with footprint WKT (2-step pattern)

Step 1 — rank by height; step 2 — join geometry (mirrors `city_ranked_buildings` with `include_locations=true`):

```sparql
PREFIX bldg: <http://www.opengis.net/citygml/building/2.0/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX be: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?building ?height ?wkt ?usage_type ?label
WHERE {
  {
    SELECT ?building (MAX(?h) AS ?height)
    WHERE {
      ?building a bldg:Building ;
                bldg:measuredHeight ?h .
    }
    GROUP BY ?building
    ORDER BY DESC(?height)
    LIMIT 10
  }
  ?building geo:hasGeometry ?g .
  ?g geo:asWKT ?wkt .
  OPTIONAL {
    ?building be:hasPropertyUsage ?u .
    ?u a ?usage_type .
  }
  OPTIONAL { ?building <http://www.w3.org/2000/01/rdf-schema#label> ?label }
}
```

## Verification

```bash
python -m demos.test_german_city_specs
python -m demos.test_german_city_page_questions
python -m demos.test_german_city_mcp_e2e
python -m mini_marie.zaha.twa_city.run_workflow --workflow top10_buildings_locations_kl
python -m mini_marie.zaha.twa_city.visualize --city kaiserslautern --limit 10
```
