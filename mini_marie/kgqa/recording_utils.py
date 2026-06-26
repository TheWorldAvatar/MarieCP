"""Extract recording paths and workflow ids from ReAct tool outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

RECORDING_PATH_LINE = re.compile(r"^recording_path\t(.+)$", re.MULTILINE)
WORKFLOW_ID_LINE = re.compile(r"^workflow_id\t(.+)$", re.MULTILINE)
ONLINE_JSON = re.compile(r"([^\s\"']+_online_\d+\.json)", re.IGNORECASE)


def parse_tsv_field(text: str, field: str) -> Optional[str]:
    for line in text.splitlines():
        if line.startswith(f"{field}\t"):
            return line.split("\t", 1)[1].strip()
    return None


def _normalize_recording_path(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return str(Path(raw.strip().strip('"')).resolve())


def extract_from_text(text: str) -> Dict[str, Optional[str]]:
    recording = parse_tsv_field(text, "recording_path")
    workflow_id = parse_tsv_field(text, "workflow_id")
    if not recording:
        match = ONLINE_JSON.search(text or "")
        if match:
            recording = match.group(1)
    recording = _normalize_recording_path(recording)
    return {"recording_path": recording, "workflow_id": workflow_id}


def extract_all_from_text(text: str) -> List[Dict[str, Optional[str]]]:
    """All recording_path / workflow_id pairs found in one tool output or answer."""
    if not (text or "").strip():
        return []
    out: List[Dict[str, Optional[str]]] = []
    seen: set[str] = set()

    recording = parse_tsv_field(text, "recording_path")
    workflow_id = parse_tsv_field(text, "workflow_id")
    if recording:
        path = _normalize_recording_path(recording)
        if path and path not in seen:
            seen.add(path)
            out.append({"recording_path": path, "workflow_id": workflow_id})

    for match in ONLINE_JSON.finditer(text or ""):
        path = _normalize_recording_path(match.group(1))
        if path and path not in seen:
            seen.add(path)
            out.append({"recording_path": path, "workflow_id": workflow_id})

    return out


def extract_all_from_metadata(metadata: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """Ordered unique recordings from all tool outputs."""
    tool_activity = metadata.get("tool_activity") or {}
    out: List[Dict[str, Optional[str]]] = []
    seen: set[str] = set()

    for item in tool_activity.get("tool_outputs") or []:
        content = item.get("content") or ""
        for parsed in extract_all_from_text(content):
            path = parsed.get("recording_path")
            if not path or path in seen:
                continue
            seen.add(path)
            out.append(parsed)

    return out


def extract_recording_info(
    *,
    online_answer: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Best-effort extraction from tool outputs then agent answer text."""
    recordings = extract_all_from_metadata(metadata or [])

    if not recordings and online_answer:
        for parsed in extract_all_from_text(online_answer):
            path = parsed.get("recording_path")
            if not path:
                continue
            if not any(r.get("recording_path") == path for r in recordings):
                recordings.append(parsed)

    recording_paths = [r["recording_path"] for r in recordings if r.get("recording_path")]
    primary = recordings[0] if recordings else {}
    return {
        "recording_path": primary.get("recording_path"),
        "workflow_id": primary.get("workflow_id"),
        "recording_paths": recording_paths,
        "recordings": recordings,
    }


def load_recording_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
