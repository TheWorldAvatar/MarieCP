"""Smoke tests for demo cache config and Marie search API."""

from __future__ import annotations

import os
from pathlib import Path

from demos.demo_env import load_demo_env

REPO = Path(__file__).resolve().parents[1]
load_demo_env()


def test_cache_paths_point_at_d_drive():
    from mini_marie.cache_paths import data_dir, mini_marie_cache_root

    data = data_dir()
    cache = mini_marie_cache_root()
    assert "mini_marie_data" in str(data).replace("\\", "/").lower()
    assert cache.name == "mini_marie_cache"
    db = cache / "chemistry" / "chemistry_cache.sqlite"
    assert db.is_file(), f"missing {db}"


def test_species_search_iupac_api():
    from demos.marie_ontospecies_api import search_species

    rows = search_species({"IUPACName": "benzene"}, partial=False, limit=5)
    assert isinstance(rows, list)
    assert rows, "expected benzene IUPAC matches in warmed cache"
    assert "IRI" in rows[0] and "label" in rows[0]


def test_species_search_smiles():
    from demos.marie_ontospecies_api import search_species

    rows = search_species({"SMILES": "O"}, partial=False, limit=5)
    assert isinstance(rows, list)
    assert rows, "expected at least one water match in warmed cache"
    assert "IRI" in rows[0] and "label" in rows[0]


def test_uses_and_classes():
    from demos.marie_ontospecies_api import list_chemical_classes, list_uses

    uses = list_uses(limit=10)
    assert uses and "IRI" in uses[0]
    classes = list_chemical_classes(limit=10)
    assert isinstance(classes, list)


def test_zeolite_materials_by_framework():
    from demos.marie_ontozeolite_api import search_zeolitic_materials

    rows = search_zeolitic_materials(
        {"Framework": "http://www.theworldavatar.com/kg/ontozeolite/ZeoFramework_AEN"},
        limit=5,
    )
    assert isinstance(rows, list)
    assert rows, "expected AEN materials in warmed zeolite cache"
    assert "IRI" in rows[0] and "ChemicalFormula" in rows[0]


def test_zeolite_frameworks_partial():
    from demos.marie_ontozeolite_api import search_zeolite_frameworks

    rows = search_zeolite_frameworks(
        {"ReturnField": ["SphereDiameter", "TopologicalDensity"]},
        partial=True,
        limit=5,
    )
    assert isinstance(rows, list)
    assert rows and "code" in rows[0]
    assert "TopologicalProperties" in rows[0]


def test_zeolite_lookup_lists():
    from demos.marie_ontozeolite_api import _lookup_items

    guests = _lookup_items("guest-components", limit=10)
    assert isinstance(guests, list)
    if guests:
        assert "IRI" in guests[0]
    journals = _lookup_items("journals", limit=5)
    assert isinstance(journals, list)


def test_zeolite_framework_search():
    from demos.marie_ontozeolite_api import search_zeolite_frameworks

    rows = search_zeolite_frameworks({"FrameworkCode": "AEN"}, partial=False, limit=5)
    assert isinstance(rows, list)
    assert rows
    assert rows[0].get("FrameworkCode") == "AEN"


def test_zeolitic_material_search():
    from demos.marie_ontozeolite_api import search_zeolitic_materials

    rows = search_zeolitic_materials({"FrameworkCode": "AEN"}, limit=5)
    assert isinstance(rows, list)
    assert rows
    assert "IRI" in rows[0]


if __name__ == "__main__":
    test_cache_paths_point_at_d_drive()
    test_uses_and_classes()
    test_species_search_iupac_api()
    test_species_search_smiles()
    test_zeolite_framework_search()
    test_zeolitic_material_search()
    test_zeolite_lookup_lists()
    print("demo setup smoke tests OK")
