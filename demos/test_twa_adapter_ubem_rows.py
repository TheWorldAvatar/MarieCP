"""Unit tests: twa_adapter picks UBEM answer rows, not height rows."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from demos.twa_adapter import _answer_rows_from_offline_payload, _table_rows_from_offline_payload


def _ubem_offline_payload() -> dict:
    return {
        "workflow_name": "pirmasens_ubem_ranked",
        "workflow_definition": {
            "id": "WF_PIRMASENS_UBEM_RANKED",
            "answer_variable": "top_ubem_rows",
        },
        "variables": {
            "top_building_rows": [
                {
                    "building": "993c659a-dead-beef",
                    "city": "pirmasens",
                    "height": 159.285,
                }
            ],
            "top_ubem_rows": [
                {
                    "dab_building": "993c659a-dead-beef",
                    "city": "pirmasens",
                    "heat_kwh_per_m2": 842.5,
                    "device_type": "RoofThermalPlateCollectors",
                }
            ],
        },
    }


def test_answer_rows_prefers_top_ubem_over_height_rows():
    payload = _ubem_offline_payload()
    rows = _answer_rows_from_offline_payload(payload)
    assert rows, "expected UBEM rows"
    assert "heat_kwh_per_m2" in rows[0]
    assert "height" not in rows[0]


def test_table_rows_from_offline_payload_matches_answer_variable():
    payload = _ubem_offline_payload()
    rows = _table_rows_from_offline_payload(payload)
    assert rows
    assert rows[0].get("heat_kwh_per_m2") == 842.5


def test_co2_ubem_payload_prefers_co2_not_height():
    payload = {
        "workflow_definition": {
            "answer_variable": "top_ubem_rows",
        },
        "variables": {
            "top_building_rows": [{"building": "x", "height": 99.0}],
            "top_ubem_rows": [{"dab_building": "x", "co2_savings": 120.0}],
        },
    }
    rows = _table_rows_from_offline_payload(payload)
    assert rows
    assert "co2_savings" in rows[0]
    assert "height" not in rows[0]


def main() -> None:
    test_answer_rows_prefers_top_ubem_over_height_rows()
    test_table_rows_from_offline_payload_matches_answer_variable()
    test_co2_ubem_payload_prefers_co2_not_height()
    print("test_twa_adapter_ubem_rows: all passed")


if __name__ == "__main__":
    main()
