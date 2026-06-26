"""Stamp workflow parameters onto tabular result rows (e.g. city label per probe)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _scalar(value: Any) -> bool:
    return value is not None and not isinstance(value, (dict, list))


def stamp_row_columns(
    rows: List[Dict[str, Any]],
    *,
    parameters: Dict[str, Any],
    stamp_keys: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Copy scalar workflow parameters onto each row.

    - ``row_annotations`` in parameters: explicit {column: value} from the agent.
    - ``stamp_keys``: parameter names to copy when the row column is missing/empty
      (workflow JSON ``stamp_row_columns``).
    """
    if not rows:
        return rows

    annotations = parameters.get("row_annotations")
    if isinstance(annotations, dict):
        for col, val in annotations.items():
            if _scalar(val):
                for row in rows:
                    row[col] = val

    for key in stamp_keys or ():
        if key in ("row_annotations",):
            continue
        val = parameters.get(key)
        if not _scalar(val):
            continue
        for row in rows:
            if row.get(key) in (None, ""):
                row[key] = val

    return rows


def stamp_variables(
    variables: Dict[str, Any],
    *,
    parameters: Dict[str, Any],
    stamp_keys: Optional[Sequence[str]] = None,
    variable_names: Optional[Sequence[str]] = None,
) -> None:
    """Apply stamp_row_columns to named list variables in a workflow result."""
    names = variable_names or (
        "top_building_rows",
        "buildings_with_wkt",
        "tall_building_rows",
        "location_join_rows",
    )
    for name in names:
        value = variables.get(name)
        if isinstance(value, list):
            stamp_row_columns(value, parameters=parameters, stamp_keys=stamp_keys)
        elif isinstance(value, dict) and isinstance(value.get("sample"), list):
            stamp_row_columns(value["sample"], parameters=parameters, stamp_keys=stamp_keys)


def parameters_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return dict(
        payload.get("resolved_parameters")
        or payload.get("seed_variables")
        or {}
    )


def stamp_offline_table_rows(
    rows: List[Dict[str, Any]],
    payload: Dict[str, Any],
    *,
    workflow: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Stamp rows loaded from an offline recording JSON (UI adapter path)."""
    wf = workflow or payload.get("workflow_definition") or {}
    params = parameters_from_payload(payload)
    stamp_keys = wf.get("stamp_row_columns") or ["city"]
    return stamp_row_columns(rows, parameters=params, stamp_keys=stamp_keys)
