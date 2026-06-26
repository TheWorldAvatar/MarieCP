"""KgqaAgent — multi-domain ReAct wrapper over BaseAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.BaseAgent import BaseAgent
from models.ModelConfig import ModelConfig
from mini_marie.kgqa.mcp_router import RouteResult
from mini_marie.kgqa.question_catalog import CatalogEntry
from src.utils.global_logger import get_logger


class KgqaAgent:
    """ReAct agent for multi-KG Q&A with dynamic MCP loading."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        remote_model: bool = True,
        model_config: Optional[ModelConfig] = None,
    ):
        self.logger = get_logger("agent", "KgqaAgent")
        self.model_name = model_name
        self.remote_model = remote_model
        self.model_config = model_config
        from mini_marie.cache_paths import configs_dir

        self.config_path = configs_dir() / "mini_marie_mcps.json"

    async def ask(
        self,
        question: str,
        *,
        route: RouteResult,
        recursion_limit: int = 200,
    ) -> Tuple[str, Dict[str, Any]]:
        enhanced = self._enhance_question(question, route)
        base_agent = BaseAgent(
            model_name=self.model_name,
            remote_model=self.remote_model,
            model_config=self.model_config,
            mcp_set_name=str(self.config_path),
            mcp_tools=route.mcp_servers,
            structured_output=False,
        )
        result, metadata = await base_agent.run(
            task_instruction=enhanced,
            recursion_limit=recursion_limit,
        )
        metadata["mcp_servers"] = route.mcp_servers
        metadata["route_reason"] = route.reason
        metadata["route_domain"] = route.domain
        metadata["route_domains"] = route.domains or ([route.domain] if route.domain else [])
        if route.catalog_entry:
            metadata["catalog_entry_id"] = route.catalog_entry.id
            metadata["workflow_id"] = route.catalog_entry.workflow_id
        if route.catalog_entries:
            metadata["catalog_entry_ids"] = [e.id for e in route.catalog_entries]
        return result, metadata

    def _enhance_question(self, question: str, route: RouteResult) -> str:
        entry: Optional[CatalogEntry] = route.catalog_entry
        workflow_hint = ""
        if entry and entry.workflow_id:
            param_hint = self._workflow_parameter_hint(entry.workflow_id, question, entry.domain)
            if entry.domain == "mof":
                workflow_hint = (
                    f"\nCatalog match: workflow_id `{entry.workflow_id}`. "
                    "You MUST call `run_competency_online` with this exact workflow_id first. "
                    "Do not substitute atomic tools for catalog competency questions."
                    f"{param_hint}"
                )
            elif entry.domain == "chemistry":
                workflow_hint = (
                    f"\nCatalog match: workflow_id `{entry.workflow_id}`. "
                    "You MUST call `run_competency_online` with this exact workflow_id. "
                    "Pass the user question (and parsed parameters_json when shown) so numeric "
                    "thresholds from the question are applied. "
                    "Do not invent other workflow ids or substitute atomic-only tool chains."
                    f"{param_hint}"
                )
            elif entry.domain == "city":
                workflow_hint = (
                    "\nCity question: use twa-city atomic workflow tools. "
                    "Call `run_workflow_online('city_ranked_buildings', parameters_json=<JSON you compose>)`."
                    f"{self._city_parameters_hint()}"
                )
        else:
            domain = entry.domain if entry else route.domain
            if domain in ("sg", "sg_kb", "sg_carpark", "sg_plot", "sg_company"):
                workflow_hint = (
                    "\nSingapore (Zaha) question: use ONLY sg-old atomic MCP tools and compose "
                    "the answer from their outputs. Do NOT call run_competency_online, "
                    "run_workflow_online, or any mof-twa tools. "
                    "Examples: pollutant concentrations → get_sg_dispersion_simulations, "
                    "get_sg_concentration_value_chain, get_sg_virtual_sensor_pollutants, "
                    "probe_sg_dispersion_point; ship speed → get_sg_ship_timeseries_info, "
                    "get_sg_ship_speed_value_chain; nearest carpark → find_nearest_sg_carpark_to_create; "
                    "GFA/buildings → count_sg_within_max_gfa, get_sg_building_count."
                )
            elif domain == "mops":
                workflow_hint = (
                    "\nMOP polyhedra question: use twa-mops and/or chemistry-ontomops tools only. "
                    "Do NOT use mof-twa Metal-Organic Framework corpus tools."
                )
            elif "twa-mops" in route.mcp_servers:
                workflow_hint = (
                    "\nMOP instance question: call twa-mops tools for synthesis recipes, CBU, CCDC, "
                    "and polyhedra data. chemistry-ontomops only has T-box routing — do not stop at "
                    "ontomops_instance_routing; query twa-mops for actual MOP individuals."
                )
            elif domain == "city" or "twa-city" in route.mcp_servers:
                workflow_hint = (
                    "\nCity question: use twa-city workflow MCP tools. "
                    "Call `run_workflow_online('city_ranked_buildings', parameters_json=...)` "
                    "with parameters you derive from the question."
                    f"{self._city_parameters_hint()}"
                )
            elif entry and entry.domain == "chemistry":
                workflow_hint = (
                    f"\nChemistry question (catalog id `{entry.id}`): use chemistry MCP atomic tools only. "
                    "Do NOT use mof-twa."
                )

        servers = ", ".join(route.mcp_servers)
        domain_labels = ", ".join(route.domains) if route.domains else route.domain
        return f"""You are a KGQA assistant for The World Avatar knowledge graphs.

**Loaded MCP servers:** {servers}
**Routing:** {route.reason} (domains: {domain_labels})
{workflow_hint}

**User question:**
{question}

**Online → offline policy (mandatory):**
1. Use MCP tools to answer with **online probe limits** (compact TSV responses).
2. For multi-step questions, use `run_workflow_online` or `run_competency_online` when a named workflow applies.
3. When the question has **multiple distinct sub-questions** (e.g. several cities, several workflows), call the appropriate online tool **once per sub-question** before summarizing. Do not stop after the first `recording_path` if other sub-questions remain.
4. When a single sub-question is complete, stop further tool use and summarize compact online results.
5. **Do NOT** call `replay_workflow_offline` or `replay_competency_offline` yourself — offline full-scale replay runs outside the LLM.
6. Include **every** `recording_path` from tool outputs in your final answer when present.

Provide a clear, structured answer citing key numeric results from tool output.
"""

    def _city_parameters_hint(self) -> str:
        try:
            from mini_marie.zaha.twa_city.workflow_engine import load_workflow

            wf = load_workflow("city_ranked_buildings")
            schema = wf.get("parameters") or {}
            if not schema:
                return ""
            return (
                "\nParameters schema keys: "
                f"{', '.join(schema.keys())}. "
                "Compose parameters_json from the user question. "
                "Use sort_field \"height\" (not measuredHeight). "
                "Set include_locations true when the question asks where buildings are. "
                "For multiple cities, call run_workflow_online once per city with its own parameters_json. "
                "When the question asks to label rows (e.g. with city), set row_annotations in parameters_json "
                "to the columns to add, e.g. {\"city\": \"bremen\"} (city is also auto-stamped from the city param). "
                "Do not use legacy top10/top50 workflow names."
            )
        except (FileNotFoundError, ImportError, ValueError):
            return ""

    def _workflow_parameter_hint(self, workflow_id: str, question: str, domain: str) -> str:
        if domain not in ("chemistry", "mof"):
            return ""
        try:
            if domain == "chemistry":
                from mini_marie.marie.chemistry.chemistry_workflow_engine import load_workflow
            else:
                from mini_marie.mop_mof.mof.competency_workflow_engine import load_workflow
            from mini_marie.workflow_parameters import (
                parameters_hint_text,
                resolve_workflow_parameters,
            )

            wf = load_workflow(workflow_id)
            if not wf.get("parameters"):
                return ""
            params = resolve_workflow_parameters(wf, question)
            return parameters_hint_text(params)
        except (KeyError, ImportError, ValueError):
            return ""
