"""Check MarieCP Flask API against endpoints expected by next_app_marie.

Run from repo root (demo server need not be running — uses Flask test client):
  python -m demos.verify_marie_frontend_compat
"""

from __future__ import annotations

import sys
from pathlib import Path

from demos.demo_env import load_demo_env

REPO = Path(__file__).resolve().parents[1]
load_demo_env()

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Endpoints read from next_app_marie src/lib/api/*.ts
GET_CHECKS = [
    ("/demos/marie/api/ontospecies/chemical-classes", {}),
    ("/demos/marie/api/ontospecies/uses", {}),
    ("/demos/marie/api/ontospecies/species", {"IUPACName": "benzene"}),
    ("/demos/marie/api/ontospecies/species-partial", {"IUPACName": "benzene"}),
    ("/demos/marie/api/ontozeolite/framework-components", {}),
    ("/demos/marie/api/ontozeolite/guest-components", {}),
    ("/demos/marie/api/ontozeolite/secondary-building-units", {}),
    ("/demos/marie/api/ontozeolite/composite-building-units", {}),
    ("/demos/marie/api/ontozeolite/journals", {}),
    ("/demos/marie/api/ontozeolite/zeolite-frameworks", {}),
    ("/demos/marie/api/ontozeolite/zeolite-frameworks-partial", {}),
    ("/demos/marie/api/ontozeolite/zeolitic-materials", {"FrameworkCode": "AEN"}),
]

POST_CHECKS = [
    ("/demos/marie/api/qa/", {}, 422),  # frontend sends {question}; empty -> 422
]

# Full QA round-trip (LLM) — opt in with --with-llm
LLM_POST_CHECKS = [
    ("/demos/marie/api/qa/", {"question": "What is benzene?"}),
]

# Detail / structure endpoints used by species/zeolite IRI pages (may 404 until implemented)
OPTIONAL_GET = [
    "/demos/marie/api/ontospecies/species/one",
    "/demos/marie/api/ontospecies/species/xyz",
    "/demos/marie/api/ontozeolite/zeolite-frameworks/one",
    "/demos/marie/api/ontozeolite/zeolite-frameworks/cif",
    "/demos/marie/api/ontozeolite/zeolitic-materials/one",
    "/demos/marie/api/ontozeolite/zeolitic-materials/cif",
]


def _json_ok(response) -> bool:
    if response.status_code != 200:
        return False
    if "json" not in (response.content_type or ""):
        return False
    try:
        response.get_json()
    except Exception:
        return False
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify MarieCP API vs next_app_marie")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Also POST a real NL question to /qa/ (slow; needs LLM credentials)",
    )
    args = parser.parse_args()

    from demos.server import app

    client = app.test_client()
    failed = 0
    warned = 0

    print("Marie frontend ↔ backend compatibility (next_app_marie API contract)\n")

    for path, params in GET_CHECKS:
        r = client.get(path, query_string=params)
        ok = _json_ok(r)
        symbol = "OK" if ok else "FAIL"
        print(f"  [{symbol}] GET {path} -> {r.status_code}")
        if not ok:
            failed += 1

    for path, body, expect in POST_CHECKS:
        r = client.post(path, json=body)
        ok = r.status_code == expect
        symbol = "OK" if ok else "FAIL"
        print(f"  [{symbol}] POST {path} (validation) -> {r.status_code}")
        if not ok:
            failed += 1

    if args.with_llm:
        for path, body in LLM_POST_CHECKS:
            r = client.post(path, json=body)
            ok = r.status_code == 200
            symbol = "OK" if ok else "FAIL"
            print(f"  [{symbol}] POST {path} (LLM) -> {r.status_code}")
            if ok:
                data = r.get_json() or {}
                if "request_id" not in data:
                    print("       missing request_id in QA response (frontend expects it)")
                    failed += 1
            else:
                failed += 1
    else:
        print("  [skip] POST /demos/marie/api/qa/ LLM round-trip (pass --with-llm to run)")

    print("\nOptional detail endpoints (IRI / CIF pages — not required for search/QA):")
    for path in OPTIONAL_GET:
        r = client.get(path, query_string={"iri": "http://example.org/test"})
        if _json_ok(r) or (r.status_code == 200 and r.data and r.data[:1] in (b"#", b"data")):
            print(f"  [OK] GET {path} -> {r.status_code}")
        elif r.status_code == 404:
            print(f"  [skip] GET {path} -> 404 (not implemented)")
            warned += 1
        else:
            print(f"  [warn] GET {path} -> {r.status_code} (likely static HTML fallback, not API)")
            warned += 1

    print()
    if failed:
        print(f"{failed} required check(s) failed.")
        return 1
    print("Required endpoints compatible with next_app_marie.")
    if warned:
        print(f"{warned} optional detail endpoint(s) not implemented yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
