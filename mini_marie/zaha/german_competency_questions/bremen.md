# Bremen — Competency Questions (Zaha / twa-city)

**SPARQL endpoint:** `https://bremen.cmpg.io/ontop/sparql/`  
**Ontop UI:** [https://bremen.cmpg.io/ontop/ui/](https://bremen.cmpg.io/ontop/ui/)  
**MCP server:** `twa-city` (`python -m mini_marie.zaha.twa_city.main`)

Catalog source: `demos/german_city_competency_questions.json` (city key `bremen`).  
Parameterized workflow: `city_ranked_buildings` (`mini_marie/zaha/twa_city/workflows/city_ranked_buildings.json`).

## Data summary (deep probe)

| Metric | Value |
|--------|------:|
| CityGML buildings | 268,281 |
| With measuredHeight | 268,281 |
| With usage type | 267,585 |
| With geometry (WKT) | 268,281 |
| Max height | 249.02 m |

Prefixes: `bldg:` CityGML Building, `be:` OntoBuiltEnv usage, `geo:` GeoSPARQL.  
See `mini_marie/zaha/twa_city/BUILDING_SCHEMA.md` for full probe output.

## Competency questions

| ID | Question | Workflow | Parameters | Map |
|----|----------|----------|------------|-----|
| DE-BR-01 | 14 tallest building in bremen and where are they? what kind of type | `city_ranked_buildings` | `city=bremen`, `top_n=14`, `sort_field=height`, `include_locations=true` | yes |
| DE-BR-02 | List the tallest non-domestic buildings in Bremen. | `city_ranked_buildings` | `city=bremen`, `top_n=50`, `sort_field=height`, `usage_type=Non-Domestic` | no |
| DE-BR-03 | Find the locations of the 10 highest buildings in Bremen | `city_ranked_buildings` | `city=bremen`, `top_n=10`, `sort_field=height`, `include_locations=true` | yes |

Legacy named workflow for non-domestic + locations: `top50_non_domestic_locations_bremen`.

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
LIMIT 15
```

### CQ2. Tallest non-domestic buildings

```sparql
PREFIX bldg: <http://www.opengis.net/citygml/building/2.0/>
PREFIX be: <https://www.theworldavatar.com/kg/ontobuiltenv/>
SELECT ?building ?height ?usage_type
WHERE {
  ?building a bldg:Building ;
            bldg:measuredHeight ?height ;
            be:hasPropertyUsage ?u .
  ?u a be:Non-Domestic .
}
ORDER BY DESC(?height)
LIMIT 50
```

### CQ3. Top buildings with footprint WKT

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
python -m mini_marie.zaha.twa_city.run_workflow --workflow top10_buildings_locations_bremen
```
