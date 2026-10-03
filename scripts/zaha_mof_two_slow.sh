#!/usr/bin/env bash
set -euo pipefail
cd ~/mariecp
export PYTHONPATH=.
python3 <<'PY'
import json
import urllib.request

BASE = "http://127.0.0.1:3001"
QUESTIONS = [
    "Which MOFs have high binary gas uptake?",
    "Which Zr-containing MOFs have carboxylate linkers?",
]

def rows(question: str) -> int:
    body = json.dumps({"question": question, "qa_domain": "marie"}).encode()
    req = urllib.request.Request(
        f"{BASE}/demos/marie/api/qa",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read().decode())
    data = payload.get("data") or []
    return sum(len(t.get("data") or []) for t in data if t.get("type") == "table")

for q in QUESTIONS:
    print(f"{rows(q)}\t{q}")
PY
