"""Cross-domain routing: Marie UI and Zaha UI share one unified KGQA backend."""

from __future__ import annotations

import asyncio
import os

from demos.twa_adapter import route_for_qa_domain_async

_HAS_LLM = bool(os.environ.get("REMOTE_API_KEY") or os.environ.get("OPENAI_API_KEY"))


async def _route(q: str, qa_domain: str):
    return await route_for_qa_domain_async(q, qa_domain)


def test_marie_ui_routes_singapore_question_to_sg():
    q = "What are the concentrations of air pollutants in Jurong Island, Singapore."
    route = asyncio.run(_route(q, "marie"))
    assert "sg" in (route.domains or [route.domain])
    assert "sg-old" in route.mcp_servers


def test_zaha_ui_routes_chemistry_question_to_chemistry():
    q = "List all zeolitic materials recorded for framework code AEN"
    route = asyncio.run(_route(q, "singapore"))
    assert route.domain == "chemistry" or "chemistry" in route.domains
    assert any(s.startswith("chemistry-") for s in route.mcp_servers)


def test_zaha_ui_still_routes_sg_when_content_is_urban():
    q = "Find me the carpark nearest to CREATE Tower"
    route = asyncio.run(_route(q, "singapore"))
    assert "sg" in (route.domains or [route.domain])
    assert "sg-old" in route.mcp_servers


def test_marie_ui_routes_agricultural_land_to_sg():
    q = "What is the size of the smallest argriculutral land in Singapore"
    route = asyncio.run(_route(q, "marie"))
    assert "sg" in (route.domains or [route.domain])
    assert "sg-old" in route.mcp_servers


def test_c6h8o6_routes_to_chemistry():
    q = "Show me all species with molecular formula C6H8O6"
    route = asyncio.run(_route(q, "marie"))
    assert route.domain == "chemistry" or "chemistry" in route.domains
    assert "chemistry-ontospecies" in route.mcp_servers


def test_cross_domain_question_gets_both_servers():
    q = (
        "Show me all species with molecular formula C6H8O6 and "
        "the size of the smallest agricultural land in Singapore"
    )
    route = asyncio.run(_route(q, "marie"))
    assert route.domain == "cross_kg" or len(route.domains or []) > 1
    assert "sg-old" in route.mcp_servers
    assert any(s.startswith("chemistry-") for s in route.mcp_servers)


if __name__ == "__main__":
    if not _HAS_LLM:
        raise SystemExit("SKIP: set REMOTE_API_KEY to run LLM routing tests")
    test_marie_ui_routes_singapore_question_to_sg()
    test_zaha_ui_routes_chemistry_question_to_chemistry()
    test_zaha_ui_still_routes_sg_when_content_is_urban()
    test_marie_ui_routes_agricultural_land_to_sg()
    test_c6h8o6_routes_to_chemistry()
    test_cross_domain_question_gets_both_servers()
    print("unified routing tests OK")
