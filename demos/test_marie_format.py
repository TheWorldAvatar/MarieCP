"""Tests for Marie demo response formatting."""

from demos.marie_format import (
    build_marie_data,
    build_marie_narrative,
    parse_tabular_content,
    tables_from_tool_outputs,
)


def test_parse_list_kg_domains_tsv():
    tsv = "id\tmcp_server\tendpoint\tscale\nchemistry_ontospecies\tchemistry-ontospecies\thttp://x/sparql\tSpecies"
    parsed = parse_tabular_content(tsv)
    assert parsed is not None
    cols, rows = parsed
    assert cols[0] == "id"
    assert rows[0]["id"] == "chemistry_ontospecies"


def test_tables_from_tool_outputs():
    outputs = [
        {
            "name": "list_kg_domains",
            "content": "id\tmcp_server\tendpoint\tscale\na\tb\thttp://x\ty",
        }
    ]
    tables = tables_from_tool_outputs(outputs)
    assert len(tables) == 1
    assert tables[0]["columns"] == ["id", "mcp_server", "endpoint", "scale"]


def test_build_marie_data_skips_meta_tools():
    outputs = [
        {
            "name": "list_kg_domains",
            "content": "id\tmcp_server\tendpoint\tscale\na\tb\thttp://x\ty",
        }
    ]
    data = build_marie_data(
        offline_tables=[],
        tool_outputs=outputs,
        online_answer="Sorry, need more steps to process this request.",
    )
    assert data == [] or not any("mcp_server" in (t.get("columns") or []) for t in data)


def test_narrative_never_echoes_question_only():
    text = build_marie_narrative(
        "Find all uses of ethanol",
        online_answer="",
        tool_outputs=[],
        data=[],
    )
    assert "**Question:**" not in text
    assert (
        "no matching records" in text.lower()
        or "empty" in text.lower()
        or "no structured results" in text.lower()
    )


def test_narrative_skips_meta_tool_dump():
    outputs = [
        {
            "name": "list_kg_domains",
            "content": "id\tmcp_server\tendpoint\tscale\na\tb\thttp://x\ty",
        }
    ]
    data = build_marie_data(
        offline_tables=[],
        tool_outputs=outputs,
        online_answer="Sorry, need more steps",
    )
    text = build_marie_narrative(
        "List domains",
        online_answer="Sorry, need more steps",
        tool_outputs=outputs,
        data=data,
    )
    assert "mcp_server" not in text
    assert "infrastructure" in text.lower() or "Example Questions" in text
