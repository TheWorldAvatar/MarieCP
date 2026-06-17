"""Backward-compatible re-export; scalable workflows live in mini_marie.mop_mof.mof.workflow_engine."""

from mini_marie.mop_mof.mof.competency_engine import (  # noqa: F401
    MCP_SERVER_NAME,
    TRANSFORMS,
    TOOL_REGISTRY,
    extract_from_step,
    resolve_value,
    run_workflow,
)
