"""
Local TWA demo server — unified KGQA backend for Marie + Zaha.

Marie and Zaha share the same routing: question content selects MCP servers;
qa_domain from each UI is only a fallback hint. Either frontend can answer
chemistry or Singapore urban questions.

Marie UI is the official next_app_marie dev server (port 3000), proxied at /demos/marie/
when MARIE_FRONTEND_PROXY=1 (default). Flask serves /demos/marie/api/* directly.

API contract (same as the original TWA demos):
  POST /demos/zaha/qa/       {question, qa_domain}
  POST /demos/zaha/chat/     {question, data: "<json string>"}
  POST /demos/marie/api/qa/  same
  POST /demos/marie/api/chat/ same

Run from repo root:
  python -m demos.server
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
MARIE_CLASSIC_ROOT = Path(__file__).resolve().parent / "marie-classic"
HUB_ROOT = Path(__file__).resolve().parent / "hub"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from demos.demo_env import load_demo_env  # noqa: E402
from mini_marie.cache_paths import load_repo_env, data_dir, mini_marie_cache_root  # noqa: E402

load_repo_env()
load_demo_env()

from demos.marie_proxy import (  # noqa: E402
    marie_proxy_enabled,
    marie_public_base,
    proxy_marie_request,
    resolve_marie_upstream,
)
from demos.twa_adapter import (  # noqa: E402
    run_marie_qa,
    run_twa_qa,
    stream_chat_events,
    stream_marie_chat_events,
)
from demos.marie_ontospecies_api import (  # noqa: E402
    cache_status as ontospecies_cache_status,
    list_chemical_classes,
    list_uses,
    search_species,
)
from demos.marie_ontozeolite_api import (  # noqa: E402
    _lookup_items,
    cache_status as ontozeolite_cache_status,
    search_zeolite_frameworks,
    search_zeolitic_materials,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
)
_loop = asyncio.new_event_loop()

if os.environ.get("MARIE_FRONTEND_DEV", "").lower() in {"1", "true", "yes"}:
    from flask_cors import CORS

    CORS(app, resources={r"/demos/marie/api/*": {"origins": "*"}})


def _ensure_loop_thread() -> None:
    def _run() -> None:
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


def _marie_frontend_base() -> str:
    """Public Marie UI URL (same-origin when proxied)."""
    return marie_public_base().rstrip("/")


def _render_demo_hub():
    return render_template(
        "hub.html",
        marie_url="/demos/marie-classic/",
        zaha_url="/demos/zaha/",
    )


def _marie_classic_root() -> Path:
    """Committed static UI (``demos/marie-classic/``), with optional mirrored override."""
    mirrored = STATIC_ROOT / "marie-classic"
    if mirrored.is_dir() and (mirrored / "index.html").is_file():
        return mirrored
    return MARIE_CLASSIC_ROOT


def _parse_body() -> dict:
    if not request.is_json:
        return {}
    return request.get_json(silent=True) or {}


def _qa_handler():
    body = _parse_body()
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"detail": "Field required: question"}), 422
    qa_domain = body.get("qa_domain")
    model = os.environ.get("DEMO_LLM_MODEL", "gpt-4o")
    try:
        payload = _run_async(
            run_twa_qa(
                question,
                qa_domain=qa_domain,
                model_name=model,
            )
        )
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"detail": str(exc)}), 500


def _chat_handler():
    body = _parse_body()
    question = (body.get("question") or "").strip()
    raw_data = body.get("data")
    data_items: list = []
    if isinstance(raw_data, str) and raw_data.strip():
        try:
            data_items = json.loads(raw_data)
        except json.JSONDecodeError:
            data_items = []
    elif isinstance(raw_data, list):
        data_items = raw_data

    def generate():
        for chunk in stream_chat_events(question, data_items):
            yield chunk

    return Response(generate(), mimetype="text/event-stream")


@app.post("/demos/zaha/qa")
@app.post("/demos/zaha/qa/")
def zaha_qa():
    return _qa_handler()


@app.post("/demos/zaha/chat")
@app.post("/demos/zaha/chat/")
def zaha_chat():
    return _chat_handler()


@app.post("/demos/marie/api/qa")
@app.post("/demos/marie/api/qa/")
def marie_qa():
    body = _parse_body()
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"detail": "Field required: question"}), 422
    qa_domain = body.get("qa_domain") or "marie"
    model = os.environ.get("DEMO_LLM_MODEL", "gpt-4o")
    try:
        payload = _run_async(
            run_marie_qa(
                question,
                qa_domain=qa_domain,
                model_name=model,
            )
        )
        return jsonify(payload)
    except Exception as exc:
        app.logger.exception("Marie QA failed")
        return jsonify({"detail": str(exc)}), 500


@app.post("/demos/marie/api/chat")
@app.post("/demos/marie/api/chat/")
def marie_chat():
    body = _parse_body()
    qa_request_id = (body.get("qa_request_id") or "").strip()
    if not qa_request_id:
        return jsonify({"detail": "Field required: qa_request_id"}), 422

    def generate():
        for chunk in stream_marie_chat_events(qa_request_id):
            yield chunk

    return Response(generate(), mimetype="text/event-stream")


HUB_FAVICON = HUB_ROOT / "favicon.png"


@app.get("/favicon.ico")
def favicon():
    if HUB_FAVICON.is_file():
        return send_from_directory(HUB_ROOT, "favicon.png", mimetype="image/png")
    return ("Not found", 404)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "static_root": str(STATIC_ROOT)})


@app.get("/health/cache")
def health_cache():
    try:
        payload: dict = {
            "status": "ok",
            "data_dir": str(data_dir()),
            "mini_marie_cache_root": str(mini_marie_cache_root()),
        }
        payload.update(ontospecies_cache_status())
        payload.update(ontozeolite_cache_status())
        from mini_marie.zaha.sg_old.ontop_operations import get_sg_ontop_cache_status

        sg_status = get_sg_ontop_cache_status()
        if sg_status:
            payload["sg_ontop"] = sg_status[0]
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 500


@app.get("/demos/marie/api/ontospecies/chemical-classes")
def marie_ontospecies_chemical_classes():
    try:
        return jsonify(list_chemical_classes())
    except Exception as exc:
        app.logger.exception("chemical-classes failed")
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontospecies/uses")
def marie_ontospecies_uses():
    try:
        return jsonify(list_uses())
    except Exception as exc:
        app.logger.exception("uses failed")
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontospecies/species")
def marie_ontospecies_species():
    try:
        params = {k: v for k, v in request.args.items()}
        return jsonify(search_species(params, partial=False))
    except Exception as exc:
        app.logger.exception("species search failed")
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontospecies/species-partial")
def marie_ontospecies_species_partial():
    try:
        params = {k: v for k, v in request.args.items()}
        return jsonify(search_species(params, partial=True))
    except Exception as exc:
        app.logger.exception("species-partial search failed")
        return jsonify({"detail": str(exc)}), 500


def _ontozeolite_lookup(kind: str):
    try:
        return jsonify(_lookup_items(kind))
    except Exception as exc:
        app.logger.exception("%s lookup failed", kind)
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontozeolite/framework-components")
def marie_ontozeolite_framework_components():
    return _ontozeolite_lookup("framework-components")


@app.get("/demos/marie/api/ontozeolite/guest-components")
def marie_ontozeolite_guest_components():
    return _ontozeolite_lookup("guest-components")


@app.get("/demos/marie/api/ontozeolite/secondary-building-units")
def marie_ontozeolite_secondary_building_units():
    return _ontozeolite_lookup("secondary-building-units")


@app.get("/demos/marie/api/ontozeolite/composite-building-units")
def marie_ontozeolite_composite_building_units():
    return _ontozeolite_lookup("composite-building-units")


@app.get("/demos/marie/api/ontozeolite/journals")
def marie_ontozeolite_journals():
    return _ontozeolite_lookup("journals")


def _query_params() -> dict:
    out: dict = {}
    for key in request.args:
        values = request.args.getlist(key)
        if len(values) == 1:
            out[key] = values[0]
        else:
            out[key] = values
    return out


@app.get("/demos/marie/api/ontozeolite/zeolite-frameworks")
def marie_ontozeolite_zeolite_frameworks():
    try:
        return jsonify(search_zeolite_frameworks(_query_params(), partial=False))
    except Exception as exc:
        app.logger.exception("zeolite-frameworks search failed")
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontozeolite/zeolite-frameworks-partial")
def marie_ontozeolite_zeolite_frameworks_partial():
    try:
        return jsonify(search_zeolite_frameworks(_query_params(), partial=True))
    except Exception as exc:
        app.logger.exception("zeolite-frameworks-partial search failed")
        return jsonify({"detail": str(exc)}), 500


@app.get("/demos/marie/api/ontozeolite/zeolitic-materials")
def marie_ontozeolite_zeolitic_materials():
    try:
        return jsonify(search_zeolitic_materials(_query_params()))
    except Exception as exc:
        app.logger.exception("zeolitic-materials search failed")
        return jsonify({"detail": str(exc)}), 500


# --- Demo hub (Marie / Zaha landing page) ---


@app.route("/demos")
@app.route("/demos/")
def demos_index():
    return redirect("/demos/hub/", code=302)


@app.route("/demos/hub/")
def demo_hub_page():
    return _render_demo_hub()


@app.route("/demos/hub/<path:subpath>")
def demo_hub_assets(subpath: str):
    return send_from_directory(HUB_ROOT, subpath)


# --- Marie UI (proxy to Next.js, or redirect when MARIE_FRONTEND_PROXY=0) ---


@app.route("/demos/marie")
@app.route("/demos/marie/", defaults={"subpath": ""})
@app.route("/demos/marie/<path:subpath>")
def marie_frontend(subpath: str = ""):
    if subpath.startswith("api/") or subpath == "api":
        return ("Not found", 404)
    if marie_proxy_enabled() and request.path.endswith("/") and not subpath:
        return redirect("/demos/marie", code=308)
    if marie_proxy_enabled():
        return proxy_marie_request(request, subpath)
    explicit = os.environ.get("MARIE_FRONTEND_URL", "").strip().rstrip("/")
    if explicit:
        target = f"{explicit}/{subpath}" if subpath else f"{explicit}/"
        return redirect(target, code=302)
    classic = "/demos/marie-classic/"
    target = f"{classic}{subpath}" if subpath else classic
    return redirect(target, code=302)


# --- static Marie (TWA classic UI — same style as Zaha) ---


@app.post("/demos/marie-classic/qa")
@app.post("/demos/marie-classic/qa/")
def marie_classic_qa():
    return _qa_handler()


@app.post("/demos/marie-classic/chat")
@app.post("/demos/marie-classic/chat/")
def marie_classic_chat():
    return _chat_handler()


@app.route("/demos/marie-classic/")
@app.route("/demos/marie-classic/<path:subpath>")
def marie_classic_static(subpath: str = ""):
    root = _marie_classic_root()
    if not root.is_dir() or not (root / "index.html").is_file():
        return ("Marie classic UI missing under demos/marie-classic/", 503)
    if not subpath:
        return send_from_directory(root, "index.html")
    target = root / subpath
    if target.is_file():
        return send_from_directory(root, subpath)
    return ("Not found", 404)


# --- static Zaha ---

@app.route("/demos/zaha/")
@app.route("/demos/zaha/<path:subpath>")
def zaha_static(subpath: str = ""):
    zaha_root = STATIC_ROOT / "zaha"
    if not zaha_root.exists():
        return (
            "Zaha static mirror missing. Run: python -m demos.mirror",
            503,
        )
    if not subpath:
        return send_from_directory(zaha_root, "index.html")
    target = zaha_root / subpath
    if target.is_file():
        return send_from_directory(zaha_root, subpath)
    return ("Not found", 404)


@app.route("/")
def demo_hub():
    return _render_demo_hub()


def main() -> None:
    from mini_marie.cache_paths import ensure_runtime_dirs

    ensure_runtime_dirs()
    # Ensure MCP subprocesses use the same Python as this server.
    venv_scripts = Path(sys.executable).resolve().parent
    os.environ["PATH"] = str(venv_scripts) + os.pathsep + os.environ.get("PATH", "")
    # Propagate cache root to stdio MCP child processes.
    os.environ["MINI_MARIE_DATA_DIR"] = str(data_dir())
    _ensure_loop_thread()
    host = os.environ.get("DEMO_HOST", "127.0.0.1")
    port = int(os.environ.get("DEMO_PORT", "8080"))
    cache_root = mini_marie_cache_root()
    print(f"Demo server http://{host}:{port}/")
    print(f"  Hub     http://{host}:{port}/")
    print(f"  Marie   http://{host}:{port}/demos/marie-classic/  (TWA classic UI)")
    print(f"  Marie+  {_marie_frontend_base()}/  (Next.js advanced UI)")
    if marie_proxy_enabled():
        print(f"  Marie upstream  {resolve_marie_upstream()}{marie_public_base()}/")
    print(f"  Zaha    http://{host}:{port}/demos/zaha/")
    print(f"  Marie API  http://{host}:{port}/demos/marie/api/")
    print(f"  Cache  {cache_root}")
    try:
        from mini_marie.zaha.sg_old.ontop_operations import get_sg_ontop_cache_status

        sg = get_sg_ontop_cache_status()[0]
        print(
            f"  SG Ontop ready={sg.get('ready')} "
            f"buildings={sg.get('building_rows')} land_plots={sg.get('land_plot_rows')}"
        )
    except Exception as exc:
        print(f"  SG Ontop status unavailable: {exc}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
