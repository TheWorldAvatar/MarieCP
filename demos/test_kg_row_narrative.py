"""Tests for generic KG row narrative helpers."""

from __future__ import annotations

from demos.kg_row_narrative import (
    decode_binary_property_token,
    is_weak_tool_summary,
    pick_best_step_tsv,
    summarize_rows,
)
from demos.twa_adapter import _try_direct_from_route, kgqa_result_to_marie, stream_chat_events
from mini_marie.kgqa.mcp_router import route_question


def test_decode_binary_property_token():
    text = decode_binary_property_token("CO2N2P09T298mmolg")
    assert text
    assert "CO2" in text
    assert "0.9" in text
    assert "298" in text


def test_is_weak_tool_summary():
    assert is_weak_tool_summary("get_thermal_stable_mofs: 986 rows")
    assert is_weak_tool_summary("topology=sod; corpus_count=150; facet_sample_count=150")
    assert not is_weak_tool_summary("For UiO-66, average PLD is 3.81 Å.")


def test_summarize_pld_aggregate():
    row = {"avgPLD": "3.806825", "variance": "0.03655", "n": "4"}
    text = summarize_rows([row], "PLD for UiO-66?")
    assert "3.81" in text
    assert "variance" in text.lower()
    assert "Summary:" not in text


def test_summarize_topology_peers():
    rows = [
        {"name": "ZIF-8", "topology": "sod", "mofid": "CC1=NC=C[N]1.[Zn] MOFid-v1.sod.cat0", "refcode": "EWIDUK"},
        {"mof": "mof_cu_sod", "topology": "sod", "mofid": "MOFid-v1.sod.cat1", "source": "CoRE MOF 2025"},
    ]
    text = summarize_rows(rows, "Which MOFs have the same topology as ZIF-8?")
    assert "ZIF-8" in text
    assert "sod" in text
    assert "MOFid-v1.sod.cat1" in text
    assert "EWIDUK" not in text.split("Other MOFs")[1] if "Other MOFs" in text else True


def test_pick_best_step_tsv_prefers_peers_over_identity():
    envelope = """status\tpass
answer\ttopology=sod

sample_results
--- step 1 ---
name\ttopology\tmofid
ZIF-8\tsod\tCC1=NC=C[N]1.[Zn] MOFid-v1.sod.cat0
--- step 2 ---
mof\ttopology\tmofid\tsource
mof_peer\tsod\tMOFid-v1.sod.cat1\tCoRE MOF 2025

next_step\tdone
"""
    block = pick_best_step_tsv(envelope, "Which MOFs have the same topology as ZIF-8?")
    assert "mof_peer" in block
    assert "ZIF-8" not in block


CANONICAL_DEMO_TWELVE = [
    "What are the average and variance of the pore limiting diameter for UiO-66?",
    "Which MOFs have the same topology as ZIF-8?",
    "What synthesis routes are recorded for UiO-66?",
    "Which MOFs are reported as thermally stable?",
    "Which MOFs have high binary gas uptake?",
    "Which Zr-containing MOFs have carboxylate linkers?",
    "How is pcu topology distributed across MOF source databases?",
    "Which ZIF-8 refcodes have matching synthesis records?",
    "Which MOFs have aqueous low-temperature synthesis routes?",
    "Which MOFs are reported as water-stable?",
    "How many experimental Cu-containing MOFs are recorded?",
    "How many experimental MOFs have pcu topology?",
]


def test_mof_questions_narrative_not_tool_summary():
    questions = CANONICAL_DEMO_TWELVE
    for q in questions:
        route = route_question(q)
        kgqa = _try_direct_from_route(q, route)
        assert kgqa, q
        payload = kgqa_result_to_marie(kgqa)
        narrative = payload.get("_narrative", "")
        chat = "".join(
            __import__("json").loads(c[6:])["content"]
            for c in stream_chat_events(q, payload.get("data") or [], narrative=narrative)
            if c.startswith("data: ")
        )
        for text in (narrative, chat):
            assert not is_weak_tool_summary(text), f"weak narrative for {q!r}: {text[:120]}"
            assert "Summary:" not in text, f"generic summary for {q!r}: {text[:120]}"


if __name__ == "__main__":
    test_decode_binary_property_token()
    test_is_weak_tool_summary()
    test_summarize_pld_aggregate()
    test_summarize_topology_peers()
    test_pick_best_step_tsv_prefers_peers_over_identity()
    test_mof_questions_narrative_not_tool_summary()
    print("kg_row_narrative tests OK")
