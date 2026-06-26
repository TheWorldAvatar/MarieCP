"""Tests for generic workflow parameter extraction."""

from mini_marie.workflow_parameters import (
    extract_ordered_thresholds,
    resolve_workflow_parameters,
)


def test_extract_two_thresholds_in_order():
    q = (
        "Show me all zeolites with accessible area per cell greater than 300 Å² "
        "and occupiable volume per cell less than 400 Å³."
    )
    got = extract_ordered_thresholds(q)
    assert got == [("gt", 300.0), ("lt", 400.0)]


def test_resolve_mq41_parameters_from_question():
    wf = {
        "parameters": {
            "min_accessible_area": {"default": 500, "comparator": "gt", "order": 0},
            "max_volume_per_cell": {"default": 200, "comparator": "lt", "order": 1},
        }
    }
    q = (
        "Show me all zeolites with accessible area per cell greater than 300 Å² "
        "and occupiable volume per cell less than 400 Å³."
    )
    params = resolve_workflow_parameters(wf, q)
    assert params["min_accessible_area"] == 300.0
    assert params["max_volume_per_cell"] == 400.0


def test_overrides_beat_defaults():
    wf = {"parameters": {"min_source_count": {"default": 1, "comparator": "gt", "order": 0}}}
    params = resolve_workflow_parameters(wf, "sources across multiple databases", {"min_source_count": 5})
    assert params["min_source_count"] == 5
