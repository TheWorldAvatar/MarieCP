could also manage to get some information about public toilets that we have instantiated few years back :
 
Competency Questions and SPARQL Queries for Public Toilets
 
SAPRQL ENDPOINT: https://pirmasens.cmpg.io/ontop-toilet/ui/
 
CQ1. What public toilets are available in the knowledge graph? 
PREFIX
obe: https://www.theworldavatar.com/kg/ontobuiltenv/ SELECT ?toilet
WHERE { ?toilet a obe:Toilet . }
 
CQ2. What is the location (geometry) of each public toilet? 
PREFIX obe:
https://www.theworldavatar.com/kg/ontobuiltenv/ PREFIX geo:
http://www.opengis.net/ont/geosparql# SELECT ?toilet ?geometry WHERE {
?toilet a obe:Toilet ; geo:asWKT ?geometry . }
 
CQ3. Which public toilets are wheelchair accessible? 
PREFIX ex:
https://example.org/ PREFIX obe:
https://www.theworldavatar.com/kg/ontobuiltenv/ SELECT ?toilet WHERE {
?toilet a obe:Toilet ; ex:isWheelchairAccessible true . }
 
CQ4. Which public toilets are not wheelchair accessible? 
SELECT ?toilet
WHERE { ?toilet a obe:Toilet ;
https://example.org/isWheelchairAccessible false . }
 
CQ5. Which public toilets require a usage fee? 
SELECT ?toilet WHERE {
?toilet a obe:Toilet ; https://example.org/requiresFee true . }
 
CQ6. Which public toilets are free to use? 
SELECT ?toilet WHERE {
?toilet a obe:Toilet ; https://example.org/requiresFee false . }
 
CQ7. Which public toilets provide facilities for both male and female
users? 
SELECT ?toilet WHERE { ?toilet a obe:Toilet ;
https://example.org/hasMaleFacility true ;
https://example.org/hasFemaleFacility true . }


Competency Questions and SPARQL Queries

Ontop Endpoint : https://pirmasens.cmpg.io/ontop-plots/ui/sparql

CQ1. What plots are available in the knowledge graph?

    PREFIX plt: <https://www.theworldavatar.com/kg/ontoplot/>
    SELECT ?plot WHERE { ?plot a plt:Plot . }

CQ2. Which zone does each plot belong to?

    PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
    SELECT ?plot ?zone WHERE { ?zone zone:hasPlot ?plot . }

CQ3. What is the area of each plot?

    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    SELECT ?plot ?area WHERE {
      ?plot geo:hasDefaultGeometry ?geom .
      ?geom geo:hasMetricArea ?area .
    }

CQ4. What is the geometry (WKT) of each plot?

    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    SELECT ?plot ?wkt WHERE {
      ?plot geo:hasDefaultGeometry ?geom .
      ?geom geo:asWKT ?wkt .
    }

CQ5. What is the maximum permitted building height for each plot?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?height WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsBuildingHeight ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?height .
    }

CQ6. What is the maximum permitted site coverage (GRZ) for each plot?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?grz WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsSiteCoverage ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?grz .
    }

CQ7. What is the permitted building mass ratio (BMZ) for each plot?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?bmz WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsBuildingMassRatio ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?bmz .
    }

CQ8. What is the maximum permitted height above normal null (OK) for each plot?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?ok WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsHeightAboveNormalNull ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?ok .
    }

CQ9. Which plots belong to a particular zoning category (2 Zone data :"Industry"@de and  "Automeile"@de)?

    PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?plot WHERE {
      ?zone zone:hasPlot ?plot ;
            zone:hasZoneType ?type .
      ?type rdfs:label "Automeile"@de .
    }

CQ10. What zoning type is associated with each zone?

    PREFIX zone: <https://www.theworldavatar.com/kg/ontozoning/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?zone ?type WHERE {
      ?zone zone:hasZoneType ?zt .
      ?zt rdfs:label ?type .
    }

CQ11. Which plots permit buildings taller than 20 metres?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?height WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsBuildingHeight ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?height .
      FILTER(?height > 20)
    }

CQ12. Which plots allow a site coverage greater than 0.6?

    PREFIX regs: <https://www.theworldavatar.com/kg/ontoplanningregulations/>
    PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
    SELECT ?plot ?grz WHERE {
      ?reg regs:appliesTo ?plot ;
           regs:allowsSiteCoverage ?quantity .
      ?quantity om:hasValue ?measure .
      ?measure om:hasNumericalValue ?grz .
      FILTER(?grz > 0.6)
    }




For Solarthermie SPARQL Endpoint : https://pirmasens.cmpg.io/ontop-solarthermie/ui/

CQ1. Which buildings have solar thermal collectors installed?
A1) 
PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX db: <http://www.purl.org/oema/enaeq/>

SELECT ?building ?collector
WHERE {
    ?building a db:Building ;
              ub:hasDevice ?collector .
}

CQ2. What is the annual heat supply of the plate thermal collectors for each building?
A2)
PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>

SELECT ?building ?heat
WHERE {
    ?building ub:hasDevice ?collector .

    ?collector a ub:RoofThermalPlateCollectors ;
               db:producesEnergy ?quantity .

    ?quantity om:hasValue ?measure .

    ?measure om:hasNumericalValue ?heat .
}

CQ3. What is the annual heat supply of the tube thermal collectors?
PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>
PREFIX db: <http://www.purl.org/oema/enaeq/>

SELECT ?building ?heat
WHERE {
    ?building ub:hasDevice ?collector .

    ?collector a ub:RoofThermalTubeCollectors ;
               db:producesEnergy ?quantity .

    ?quantity om:hasValue ?measure .

    ?measure om:hasNumericalValue ?heat .
}

CQ4. Which buildings have roofs suitable for solar collectors?
PREFIX bot: <http://w3id.org/bot#>
PREFIX bim: <http://www.theworldavatar.com/ontology/ontobim/OntoBIM.owl#>
PREFIX db: <http://www.purl.org/oema/enaeq/>

SELECT ?building
WHERE {
    ?building a db:Building ;
              bot:containsElement ?roof .

    ?roof bim:isSolarCollectorSuitable true .
}

CQ5. Which buildings achieve annual CO₂ savings greater than 50 kg/m²?
PREFIX ub: <http://www.theworldavatar.com/kg/ontoubemmp/>
PREFIX om: <http://www.ontology-of-units-of-measure.org/resource/om-2/>

SELECT ?building ?co2
WHERE {
    ?building ub:hasDevice ?collector .

    ?collector ub:producesCO2Savings ?quantity .

    ?quantity om:hasValue ?measure .

    ?measure om:hasNumericalValue ?co2 .

    FILTER(?co2 > 100)
}
LIMIT 20
