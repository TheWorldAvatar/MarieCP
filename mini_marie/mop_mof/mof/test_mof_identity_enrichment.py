"""Unit tests for generic MOF identity enrichment."""

from mini_marie.mop_mof.mof.mof_identity_enrichment import (
    enrich_mof_rows,
    extract_mof_keys_from_rows,
    merge_identity_into_rows,
    normalize_mof_key,
)


def test_normalize_mof_key():
    assert normalize_mof_key("mof_2000%5BCu%5D") == "mof_2000[cu]"


def test_merge_identity_fills_missing_name():
    rows = [{"mof": "mof_abc", "topology": "sod", "source": "CoRE MOF 2025"}]
    identity = [
        {
            "mof": "https://example/kg/mof_abc",
            "name": "ZIF-8 analogue",
            "refcode": "EWIDUK",
        }
    ]
    out = merge_identity_into_rows(rows, identity)
    assert out[0]["name"] == "ZIF-8 analogue"
    assert out[0]["refcode"] == "EWIDUK"
    assert out[0]["topology"] == "sod"


def test_extract_mof_keys():
    rows = [{"mof": "a"}, {"mof": "b"}, {"count": 1}]
    assert extract_mof_keys_from_rows(rows) == ["a", "b"]


def test_enrich_without_remote_is_noop_when_no_cache_hits():
    rows = [{"mof": "mof_unknown_token", "source": "X"}]
    out = enrich_mof_rows(rows, cache=None, allow_remote=False)
    assert out[0]["mof"] == "mof_unknown_token"


if __name__ == "__main__":
    test_normalize_mof_key()
    test_merge_identity_fills_missing_name()
    test_extract_mof_keys()
    test_enrich_without_remote_is_noop_when_no_cache_hits()
    print("mof_identity_enrichment tests OK")
