"""MQ2 empty-result presentation tests."""

from demos.marie_format import build_marie_data, build_marie_narrative, tables_from_tool_outputs
from demos.twa_adapter import _summarize_competency_tool_output, kgqa_result_to_marie

MQ2_ENVELOPE = """status\tempty
mode\tonline
workflow_id\tmq02_amino_propanol_uses
title\tMQ2 — uses of 3-amino-2-propanol
answer\t[]

step\ttype\ttool\tstatus\trow_count\telapsed_ms
1\ttool\tsearch_uses_enriched\tempty\t0\t0

sample_results

next_step\tOffline full answer
"""

QUESTION = "Find all uses of 3-amino-2-propanol"


def test_competency_envelope_not_shown_as_table():
    tables = tables_from_tool_outputs(
        [{"name": "run_competency_online", "content": MQ2_ENVELOPE}]
    )
    assert tables == []


def test_mq02_summary_and_narrative():
    summary = _summarize_competency_tool_output(MQ2_ENVELOPE, QUESTION)
    assert "3-amino-2-propanol" in summary
    assert "workflow_id" not in summary
    assert "recording_path" not in summary
    assert "**Question:**" not in summary

    kgqa = {
        "question": QUESTION,
        "online_answer": "The workflow completed.",
        "metadata": {
            "tool_activity": {
                "tool_outputs": [{"name": "run_competency_online", "content": MQ2_ENVELOPE}],
            }
        },
        "route": {"mcp_servers": ["chemistry-ontospecies"], "reason": "test"},
        "offline": {"status": "empty", "answer": []},
    }
    payload = kgqa_result_to_marie(kgqa)
    assert payload["data"]
    cols = payload["data"][0].get("columns") or []
    assert "status" not in cols or cols == ["Summary"]
    narrative = payload["_narrative"]
    assert "workflow_id" not in narrative
    assert "3-amino-2-propanol" in narrative
    assert "**Question:**" not in narrative


def test_competency_envelope_from_agent_metadata():
    from demos.twa_adapter import _competency_envelope_from_metadata

    meta = {
        "tool_activity": {
            "tool_outputs": [{"name": "run_competency_online", "content": MQ2_ENVELOPE}],
        }
    }
    assert _competency_envelope_from_metadata(meta).strip() == MQ2_ENVELOPE.strip()


if __name__ == "__main__":
    test_competency_envelope_not_shown_as_table()
    test_mq02_summary_and_narrative()
    from demos.twa_adapter import _summarize_competency_tool_output

    mq18 = """status\tempty
answer\tNone
step\ttype\ttool\tstatus\trow_count\telapsed_ms
1\ttool\tquery_pka_enriched\tempty\t0\t0
sample_results
"""
    text = _summarize_competency_tool_output(
        mq18,
        "List all compounds studied by Perrin together with their counts of pK measurements.",
    )
    assert "Perrin" in text and text != "None"
    print("mq02 tests OK")
