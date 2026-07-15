"""Shape KGQA output for TWA Zaha / Marie Classic demo UI (tables, maps, narrative)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from demos.marie_format import (
    _is_weak_answer,
    build_marie_narrative,
    parse_tabular_content,
    tables_from_tool_outputs,
)

TWA_IRI_PREFIXES = (
    "http://www.theworldavatar.com/kb/",
    "https://www.theworldavatar.com/kg/",
    "http://www.theworldavatar.com/ontology/",
    "https://www.theworldavatar.com/ontology/",
)

_WKT_KEYS = frozenset({"wkt", "footprint_wkt", "geometry", "geom", "footprint"})
_BUILDING_KEYS = ("building_iri", "building", "Building")
_VIZ_URL_RE = re.compile(r"https?://[^\s\t\"']+/visualisation/?", re.I)
_LOCATION_Q_RE = re.compile(
    r"\b(footprint|map|where|location|nearest|carpark|geometry|dispersion|pollutant)\b",
    re.I,
)
_SCATTER_Q_RE = re.compile(r"\b(percent|percentage|residential|commercial|ratio)\b", re.I)

_ROW_LIMIT = 500


def _is_iri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text.startswith(("http://", "https://")):
        return False
    return any(text.startswith(prefix) for prefix in TWA_IRI_PREFIXES) or "/" in text[8:]


def _iri_label(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def _humanize_cell(key: str, value: Any) -> Any:
    if value is None:
        return value
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if not text:
        return text
    lk = key.lower()
    if _is_iri(text) or lk.endswith("_iri") or lk in {"building", "usage", "land_use", "land_use_label"}:
        if _is_iri(text) or text.startswith("http"):
            return _iri_label(text)
    return text


def _column_priority(name: str) -> int:
    lk = name.lower()
    if lk in {"name", "building_name", "facility_name", "label"}:
        return 0
    if "count" in lk or lk.endswith("_pct") or lk in {"area_sqm", "height", "max_gfa", "calc_gfa"}:
        return 1
    if lk.endswith("_iri") or _is_iri(name):
        return 9
    if "wkt" in lk or lk in {"geometry", "geom", "footprint"}:
        return 8
    return 5


def _humanize_rows(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    if not rows:
        return [], []
    all_keys: List[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen_keys:
                seen_keys.add(key)
                all_keys.append(key)

    wkt_cols = [k for k in all_keys if k.lower() in _WKT_KEYS or "wkt" in k.lower()]
    display_keys: List[str] = []
    for key in sorted(all_keys, key=_column_priority):
        if key in wkt_cols:
            continue
        sample_vals = [row.get(key) for row in rows[:5] if row.get(key) not in (None, "")]
        if not sample_vals:
            display_keys.append(key)
            continue
        if all(_is_iri(str(v)) for v in sample_vals if v):
            if any(
                _humanize_cell(key, v) != str(v)
                for v in sample_vals
                if v
            ):
                display_keys.append(key)
            continue
        display_keys.append(key)

    if not display_keys and wkt_cols:
        display_keys = [k for k in all_keys if k not in wkt_cols][:6]

    out_rows: List[Dict[str, Any]] = []
    for row in rows:
        out_rows.append({k: _humanize_cell(k, row.get(k)) for k in display_keys})
    return display_keys, out_rows


def _row_fingerprint(row: Dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    for field in _BUILDING_KEYS:
        if any(row.get(field) for row in rows):
            try:
                from mini_marie.zaha.twa_city.city_cache import dedupe_rows_by_building

                return dedupe_rows_by_building(rows, building_field=field)
            except Exception:
                break
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        fp = _row_fingerprint(row)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(row)
    return out


def _normalize_wkt(text: str) -> Optional[str]:
    """Strip GeoSPARQL CRS prefix and Z/M for OpenLayers WKT."""
    if not text or not isinstance(text, str):
        return None
    cleaned = text.strip()
    if cleaned.startswith("<") and ">" in cleaned:
        cleaned = cleaned.split(">", 1)[1].strip()
    cleaned = re.sub(r"\bPOLYGON Z\b", "POLYGON", cleaned, flags=re.I)
    cleaned = re.sub(r"\bMULTIPOLYGON Z\b", "MULTIPOLYGON", cleaned, flags=re.I)
    cleaned = re.sub(r"\bLINESTRING Z\b", "LINESTRING", cleaned, flags=re.I)
    cleaned = re.sub(r"\bPOINT Z\b", "POINT", cleaned, flags=re.I)
    upper = cleaned.upper()
    if not upper.startswith(("POINT", "POLYGON", "LINESTRING", "MULTI")):
        return None
    try:
        from shapely import force_2d, wkt as shapely_wkt

        return shapely_wkt.dumps(force_2d(shapely_wkt.loads(cleaned)))
    except Exception:
        # Fallback: drop elevation from numeric triplets (lon lat z -> lon lat)
        cleaned = re.sub(
            r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)",
            r"\1 \2",
            cleaned,
        )
        return cleaned


def _wkt_from_row(row: Dict[str, Any]) -> Optional[str]:
    for key, val in row.items():
        if not isinstance(val, str):
            continue
        lk = key.lower()
        if lk in _WKT_KEYS or "wkt" in lk or lk in {"geometry", "geom", "footprint"}:
            normalized = _normalize_wkt(val)
            if normalized:
                return normalized
        normalized = _normalize_wkt(val)
        if normalized:
            return normalized
    return None


def _collect_wkts(rows: List[Dict[str, Any]], *, limit: int = 50) -> List[str]:
    wkts: List[str] = []
    seen: set[str] = set()
    for row in rows:
        wkt = _wkt_from_row(row)
        if not wkt or wkt in seen:
            continue
        seen.add(wkt)
        wkts.append(wkt)
        if len(wkts) >= limit:
            break
    return wkts


def _merge_wkts(wkts: Sequence[str]) -> Optional[str]:
    if not wkts:
        return None
    normalized = [_normalize_wkt(w) for w in wkts]
    normalized = [w for w in normalized if w]
    if not normalized:
        return None
    if len(normalized) == 1:
        return normalized[0]
    try:
        from shapely import force_2d, wkt as shapely_wkt
        from shapely.ops import unary_union

        geoms = [force_2d(shapely_wkt.loads(text)) for text in normalized]
        merged = unary_union(geoms)
        return merged.wkt
    except Exception:
        return normalized[0]


def _extract_visualisation_url(tool_outputs: List[Dict[str, str]]) -> Optional[str]:
    for item in tool_outputs:
        content = item.get("content") or ""
        match = _VIZ_URL_RE.search(content)
        if match:
            url = match.group(0).rstrip("'\",)")
            if not url.endswith("/"):
                url += "/"
            return url
        parsed = parse_tabular_content(content)
        if parsed:
            _cols, rows = parsed
            for row in rows:
                for val in row.values():
                    if isinstance(val, str) and _VIZ_URL_RE.search(val):
                        url = _VIZ_URL_RE.search(val).group(0).rstrip("'\",)")
                        return url if url.endswith("/") else url + "/"
    return None


def _scatter_from_rows(name: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    row = rows[0]
    x_key = None
    y_keys: List[str] = []
    for key, val in row.items():
        lk = key.lower()
        if lk.endswith("_pct") or lk.endswith("_count"):
            if "residential" in lk or "commercial" in lk or "office" in lk:
                y_keys.append(key)
        if lk in {"land_use_label", "category", "name", "label"}:
            x_key = key
    if not y_keys:
        return None
    labels = [str(row.get(x_key or "category", f"item {i}")) for i, row in enumerate(rows[:20])]
    traces = []
    for y_key in y_keys[:3]:
        traces.append(
            {
                "name": y_key.replace("_", " "),
                "x": {"type": "category", "data": labels},
                "y": {"type": "number", "data": [float(row.get(y_key) or 0) for row in rows[:20]]},
            }
        )
    if not traces:
        return None
    return {"type": "scatter_plot", "title": name, "traces": traces}


def _attach_viz_items(
    name: str,
    rows: List[Dict[str, Any]],
    *,
    question: str,
    tool_outputs: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    raw_rows = rows
    wkts = _collect_wkts(raw_rows)
    normalized = [_normalize_wkt(w) for w in wkts]
    normalized = [w for w in normalized if w]
    city = ""
    for row in raw_rows[:20]:
        c = row.get("city")
        if isinstance(c, str) and c.strip():
            city = c.strip().lower()
            break
    if not city:
        blob = f"{name} {question}".lower()
        for key in ("pirmasens", "bremen", "kaiserslautern"):
            if key in blob:
                city = key
                break
    if city and normalized:
        from mini_marie.zaha.twa_city.gis_visualization import recenter_wkts_to_city

        normalized = recenter_wkts_to_city(normalized, city)
    merged = _merge_wkts(normalized)
    if merged:
        map_item: Dict[str, Any] = {"type": "map", "title": name, "wkt_crs84": merged}
        if len(normalized) > 1:
            map_item["wkt_list"] = normalized
        items.append(map_item)

    viz_url = _extract_visualisation_url(tool_outputs)
    if viz_url and (_LOCATION_Q_RE.search(question) or not merged):
        items.append(
            {
                "type": "embed",
                "title": "Singapore visualisation (TWA-VF)",
                "url": viz_url,
            }
        )

    if _SCATTER_Q_RE.search(question):
        scatter = _scatter_from_rows(name, raw_rows)
        if scatter:
            items.append(scatter)
    return items


def _twa_table_item(name: str, columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    trimmed = _dedupe_rows(rows[:_ROW_LIMIT])
    vars_, bindings = _humanize_rows(trimmed)
    if not vars_:
        vars_, bindings = columns, trimmed
    return {"type": "table", "vars": vars_, "bindings": bindings}


def _rows_to_twa_items(
    name: str,
    rows: List[Dict[str, Any]],
    *,
    question: str = "",
    tool_outputs: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    if not rows:
        return []
    tool_outputs = tool_outputs or []
    table = _twa_table_item(name, list(rows[0].keys()), rows)
    items: List[Dict[str, Any]] = [table]
    items.extend(
        _attach_viz_items(name, rows, question=question, tool_outputs=tool_outputs)
    )
    return items


def _tables_from_tool_outputs_twa(
    tool_outputs: List[Dict[str, str]],
    *,
    question: str = "",
    skip_meta: bool = True,
) -> List[Dict[str, Any]]:
    marie_tables = tables_from_tool_outputs(tool_outputs, skip_meta=skip_meta)
    items: List[Dict[str, Any]] = []
    seen_blocks: set[str] = set()
    for table in marie_tables:
        cols = table.get("columns") or []
        rows = table.get("data") or []
        if not cols or not rows:
            continue
        fp = f"{':'.join(cols)}:{_row_fingerprint(rows[0])}:{len(rows)}"
        if fp in seen_blocks:
            continue
        seen_blocks.add(fp)
        name = cols[0] if len(cols) == 1 else "Results"
        items.extend(
            _rows_to_twa_items(name, rows, question=question, tool_outputs=tool_outputs)
        )
    return items


def _is_answer_only_table(item: Dict[str, Any]) -> bool:
    if item.get("type") != "table":
        return False
    vars_ = item.get("vars") or []
    return vars_ in (["answer"], ["Summary"])


def _has_substantive_table(items: List[Dict[str, Any]]) -> bool:
    return any(
        item.get("type") == "table" and not _is_answer_only_table(item)
        for item in items
    )


def _dedupe_data_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        if item.get("type") == "table":
            vars_ = item.get("vars") or []
            bindings = item.get("bindings") or []
            fp = f"table:{':'.join(vars_)}:{len(bindings)}"
            if bindings:
                fp += f":{_row_fingerprint(bindings[0])}"
        else:
            fp = json.dumps(item, sort_keys=True, default=str)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(item)
    return out


def build_twa_data(kgqa: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build TWA data[] items with humanized tables, dedupe, and viz attachments."""
    from demos.twa_adapter import (
        _data_from_offline_paths,
        _display_answer,
        _resolve_offline_recording_paths,
    )

    question = kgqa.get("question") or ""
    metadata = kgqa.get("metadata") or {}
    tool_outputs = (metadata.get("tool_activity") or {}).get("tool_outputs") or []

    offline_paths = _resolve_offline_recording_paths(kgqa)
    data: List[Dict[str, Any]] = _data_from_offline_paths(offline_paths)

    if not _has_substantive_table(data):
        data.extend(_tables_from_tool_outputs_twa(tool_outputs, question=question))

    if not data:
        answer = kgqa.get("online_answer") or _display_answer(kgqa)
        if isinstance(answer, list) and answer and isinstance(answer[0], dict):
            data = _rows_to_twa_items("answer", answer, question=question, tool_outputs=tool_outputs)
        elif isinstance(answer, str) and answer.strip():
            if not _is_weak_answer(answer):
                data = [
                    {
                        "type": "table",
                        "vars": ["Summary"],
                        "bindings": [{"Summary": answer.strip()}],
                    }
                ]
            else:
                data = [
                    {
                        "type": "table",
                        "vars": ["answer"],
                        "bindings": [{"answer": answer.strip()}],
                    }
                ]

    if _has_substantive_table(data):
        data = [item for item in data if not _is_answer_only_table(item)]

    for item in data:
        if item.get("type") == "table":
            bindings = item.get("bindings") or []
            vars_ = item.get("vars") or []
            if bindings and vars_:
                deduped = _dedupe_rows(bindings)
                hvars, hrows = _humanize_rows(deduped)
                item["vars"] = hvars or vars_
                item["bindings"] = hrows or deduped

    if not any(item.get("type") == "map" for item in data):
        raw_rows: List[Dict[str, Any]] = []
        for item in data:
            if item.get("type") == "table":
                raw_rows.extend(item.get("bindings") or [])
        for tool in tool_outputs:
            parsed = parse_tabular_content(tool.get("content") or "")
            if parsed:
                _cols, rows = parsed
                raw_rows.extend(rows)
        if raw_rows:
            label = "Footprint" if _LOCATION_Q_RE.search(question) else "Results"
            data.extend(
                _attach_viz_items(label, raw_rows, question=question, tool_outputs=tool_outputs)
            )

    return _dedupe_data_items(data)


def _marie_data_from_twa(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if item.get("type") != "table":
            continue
        cols = item.get("vars") or item.get("columns") or []
        rows = item.get("bindings") or item.get("data") or []
        if cols and rows:
            out.append({"type": "table", "columns": list(cols), "data": rows})
    return out


def _looks_like_raw_json(text: Any) -> bool:
    if not isinstance(text, str):
        return isinstance(text, (dict, list))
    s = text.strip()
    if not s:
        return False
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            json.loads(s)
            return True
        except json.JSONDecodeError:
            return False
    return False


def _human_number(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if num.is_integer():
        return f"{int(num):,}"
    return f"{num:,.2f}".rstrip("0").rstrip(".")


def _summarize_metric_row(row: Dict[str, Any], question: str = "") -> Optional[str]:
    """Turn a single stats/count row into a short Markdown sentence."""
    if not row:
        return None
    q = (question or "").lower()

    if {"min_kwh_per_m2", "max_kwh_per_m2", "avg_kwh_per_m2"} <= set(row):
        where = "Pirmasens" if "pirmasens" in q else "the city"
        count = row.get("measure_count")
        count_bit = f" across **{_human_number(count)}** measurements" if count not in (None, "") else ""
        return (
            f"For {where} thermal collectors, annual heat supply ranges from "
            f"**{_human_number(row['min_kwh_per_m2'])}** to **{_human_number(row['max_kwh_per_m2'])}** "
            f"kWh/m² (average **{_human_number(row['avg_kwh_per_m2'])}** kWh/m²{count_bit})."
        )

    if {"min_co2", "max_co2", "avg_co2"} <= set(row) or {
        "min_co2_savings",
        "max_co2_savings",
        "avg_co2_savings",
    } <= set(row):
        mn = row.get("min_co2_savings", row.get("min_co2"))
        mx = row.get("max_co2_savings", row.get("max_co2"))
        avg = row.get("avg_co2_savings", row.get("avg_co2"))
        where = "Pirmasens" if "pirmasens" in q else "the city"
        return (
            f"For {where} solar collectors, modelled annual CO₂ savings range from "
            f"**{_human_number(mn)}** to **{_human_number(mx)}** "
            f"(average **{_human_number(avg)}**)."
        )

    if "office_building_count" in row:
        return f"There are **{_human_number(row['office_building_count'])}** office buildings."

    if "commercial_plot_count" in row:
        return f"There are **{_human_number(row['commercial_plot_count'])}** plots zoned commercial."

    if "building_count" in row and len(row) <= 3:
        where = (
            "Pirmasens"
            if "pirmasens" in q
            else ("Bremen" if "bremen" in q else ("Singapore" if "singapore" in q else "the graph"))
        )
        return f"There are **{_human_number(row['building_count'])}** buildings in {where}."

    if "min_height" in row and "max_height" in row and "avg_height" in row:
        where = "Pirmasens" if "pirmasens" in q else ("Bremen" if "bremen" in q else "the city")
        return (
            f"Building measuredHeight in {where} ranges from "
            f"**{_human_number(row['min_height'])}** m to **{_human_number(row['max_height'])}** m "
            f"(average **{_human_number(row['avg_height'])}** m)."
        )

    # Generic compact scalar row (avoid dumping JSON braces).
    if len(row) <= 6 and all(not isinstance(v, (dict, list)) for v in row.values()):
        parts = [f"**{_human_number(v)}** {k.replace('_', ' ')}" for k, v in row.items() if v not in (None, "")]
        if parts:
            return "Summary: " + "; ".join(parts) + "."
    return None


def _first_table_rows(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for item in data:
        if item.get("type") != "table":
            continue
        rows = item.get("bindings") or item.get("data") or []
        if rows:
            return [r for r in rows if isinstance(r, dict)]
    return []


def _narrative_from_data(question: str, data: List[Dict[str, Any]]) -> Optional[str]:
    rows = _first_table_rows(data)
    if not rows:
        return None
    summary = _summarize_metric_row(rows[0], question)
    if summary:
        return summary
    if len(rows) == 1:
        preview = ", ".join(
            f"{k.replace('_', ' ')} {_human_number(v)}"
            for k, v in rows[0].items()
            if v not in (None, "") and "wkt" not in k.lower()
        )
        return f"Result: {preview}." if preview else None
    return f"Found **{len(rows)}** matching rows for your question."


def build_twa_narrative_rule(
    question: str,
    kgqa: Dict[str, Any],
    data: List[Dict[str, Any]],
) -> str:
    """Rule-based narrative fallback (no LLM). Always prefer natural language over raw JSON."""
    from demos.twa_adapter import _display_answer, _summarize_sg_tool_rows

    metadata = kgqa.get("metadata") or {}
    tool_outputs = (metadata.get("tool_activity") or {}).get("tool_outputs") or []
    online_answer = _display_answer(kgqa) or kgqa.get("online_answer")

    from_data = _narrative_from_data(question, data)
    if from_data:
        # Prefer structured NL when the agent answer is raw JSON / a dict dump.
        if _looks_like_raw_json(online_answer) or not (
            isinstance(online_answer, str) and not _is_weak_answer(online_answer)
        ):
            return from_data

    for item in tool_outputs:
        parsed = parse_tabular_content(item.get("content") or "")
        if parsed:
            _cols, rows = parsed
            if rows:
                metric = _summarize_metric_row(rows[0], question)
                if metric:
                    return metric
            summary = _summarize_sg_tool_rows(rows, question)
            if summary and not _is_weak_answer(summary) and not _looks_like_raw_json(summary):
                return summary

    if isinstance(online_answer, str) and not _is_weak_answer(online_answer) and not _looks_like_raw_json(online_answer):
        return online_answer.strip()

    if from_data:
        return from_data

    marie_data = _marie_data_from_twa(data)
    text = build_marie_narrative(
        question,
        online_answer=online_answer if not _looks_like_raw_json(online_answer) else "",
        tool_outputs=tool_outputs,
        data=marie_data,
    )
    if text and not _looks_like_raw_json(text):
        return text
    return from_data or "I found structured results in the table, but could not phrase a summary."


def _llm_narrative_enabled() -> bool:
    if os.environ.get("DEMO_LLM_NARRATIVE", "1").strip().lower() in {"0", "false", "no", "off"}:
        return False
    return bool(os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _narrative_model_name() -> str:
    return os.environ.get("DEMO_NARRATIVE_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _data_preview_for_llm(data: List[Dict[str, Any]], *, max_rows: int = 10) -> str:
    lines: List[str] = []
    for item in data:
        if item.get("type") == "table":
            vars_ = item.get("vars") or []
            for row in (item.get("bindings") or [])[:max_rows]:
                preview = ", ".join(f"{k}: {v}" for k, v in row.items() if v not in (None, ""))
                if preview:
                    lines.append(f"- {preview}")
        elif item.get("type") == "map":
            lines.append(f"- Map: {item.get('title') or 'geometry'}")
        elif item.get("type") == "embed":
            lines.append(f"- Embedded visualisation: {item.get('url')}")
    return "\n".join(lines[: max_rows * 3])


async def build_twa_narrative_llm(
    question: str,
    kgqa: Dict[str, Any],
    data: List[Dict[str, Any]],
) -> str:
    """LLM-organized Markdown narrative; falls back to rule-based text."""
    rule_text = build_twa_narrative_rule(question, kgqa, data)
    if not _llm_narrative_enabled():
        return rule_text

    from langchain_core.messages import HumanMessage, SystemMessage
    from models.LLMCreator import LLMCreator
    from models.ModelConfig import ModelConfig

    from demos.twa_adapter import _display_answer

    online_answer = _display_answer(kgqa) or kgqa.get("online_answer") or ""
    if _looks_like_raw_json(online_answer):
        online_answer = ""
    preview = _data_preview_for_llm(data)
    has_map = any(item.get("type") in {"map", "embed"} for item in data)

    system = (
        "You write concise natural-language Markdown answers for an urban knowledge-graph demo (Zaha). "
        "Use the user's question and structured data preview only. "
        "Never paste raw JSON, Python dicts, full HTTP IRIs, or key:value dumps — always write prose. "
        "All numbers must come from the data preview or agent answer. "
        "If data is missing, state the limitation clearly "
        "and mention that an interactive map may appear below when available. "
        "Use **bold** for key figures and short bullet lists when helpful."
    )
    user = f"""Question:
{question.strip()}

Agent answer (may be partial; ignore if empty):
{str(online_answer).strip()[:2000]}

Structured data preview:
{preview or '(no tabular rows)'}

Includes map or embed: {has_map}

Write a clear natural-language Markdown response (2–6 sentences or short bullets). Do not output JSON."""

    try:
        llm = LLMCreator(
            model=_narrative_model_name(),
            remote_model=True,
            model_config=ModelConfig(),
        ).setup_llm()
        result = await llm.ainvoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        text = (result.content if hasattr(result, "content") else str(result)).strip()
        if text and len(text) >= 20 and not _looks_like_raw_json(text):
            return text
    except Exception:
        pass
    return rule_text


async def kgqa_result_to_twa_display(kgqa: Dict[str, Any]) -> Dict[str, Any]:
    """Convert orchestrator output to {metadata, data, narrative} for POST /qa/."""
    from demos.twa_adapter import _steps_from_metadata

    question = kgqa.get("question") or ""
    timing = kgqa.get("timing") or {}
    metadata = kgqa.get("metadata") or {}
    online_ms = int(timing.get("online_ms") or timing.get("total_ms") or 0)

    data = build_twa_data(kgqa)
    narrative = await build_twa_narrative_llm(question, kgqa, data)

    return {
        "metadata": {"steps": _steps_from_metadata(question, metadata, online_ms)},
        "data": data,
        "narrative": narrative,
    }


def kgqa_result_to_twa(kgqa: Dict[str, Any]) -> Dict[str, Any]:
    """Sync TWA payload without LLM narrative (used by Marie API conversion)."""
    from demos.twa_adapter import _steps_from_metadata

    question = kgqa.get("question") or ""
    timing = kgqa.get("timing") or {}
    metadata = kgqa.get("metadata") or {}
    online_ms = int(timing.get("online_ms") or timing.get("total_ms") or 0)
    data = build_twa_data(kgqa)
    return {
        "metadata": {"steps": _steps_from_metadata(question, metadata, online_ms)},
        "data": data,
    }
