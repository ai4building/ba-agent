"""BA-Agent Python AI Service — hxPy entry point.

This module serves as the main interface for BA-Agent system,
loaded by hxPy containers in Haxall/FIN Framework environment.

BaAgentService is a thin backward-compatible wrapper around LLMOrchestrator,
which handles all engine routing, intent parsing, and LLM integration.

Usage from AXON:
    session: py(image: "ba-agent-py:latest")
    pyExec(session, "from baAgentPy.main import BaAgentService; svc = BaAgentService()")
    pyEval(session, "svc.ask('诊断一下AHU-01')")
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from baAgentPy.core.llm_orchestrator import LLMOrchestrator
from baAgentPy.services import (
    EnergyOptEngine,
    FddEngine,
    HmiEngine,
    InspectEngine,
    ModelingEngine,
    ReportEngine,
)
from baAgentPy.utils.grid_converter import GridConverter


# ── Request/Response Models (backward compat) ──


class ServiceRequest(BaseModel):
    """Incoming request from AXON via pyEval()."""

    action: str = Field(description="Service action: diagnose | optimize | inspect | hmi | report | query")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Action-specific parameters"
    )


class ServiceResponse(BaseModel):
    """Response returned to AXON via pyEval() return value."""

    ok: bool = True
    action: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


# ── Default Engine Set ──


def _create_default_engines() -> list[Any]:
    """Create the default set of domain engines."""
    return [
        FddEngine(),
        EnergyOptEngine(),
        InspectEngine(),
        HmiEngine(),
        ReportEngine(),
        ModelingEngine(),
    ]


# ── Main Service Class ──


class BaAgentService:
    """Central AI service loaded by hxPy — backward-compatible wrapper.

    Delegates all routing, parsing, and LLM integration to LLMOrchestrator.
    This class adds only:
    - Haystack Grid ↔ Pandas DataFrame conversion (via GridConverter)
    - Context extraction from grid data for LLM enrichment
    - The AXON-facing handle()/ask() API signatures
    """

    def __init__(self, enable_llm: bool = True) -> None:
        self._converter = GridConverter()
        self._orchestrator = LLMOrchestrator(
            engines=_create_default_engines(),
            enable_llm=enable_llm,
        )
        self._initialized = True

    @property
    def registered_actions(self) -> list[str]:
        """List all supported service actions."""
        return self._orchestrator.registered_actions + ["ping", "ask", "query"]

    @property
    def registered_engines(self) -> list[str]:
        """List all registered engine names."""
        return self._orchestrator.registered_engines

    @property
    def llm_status(self) -> dict[str, str]:
        """Get LLM service status."""
        return self._orchestrator.llm_status

    def handle(self, action: str, payload: dict[str, Any] | None = None,
               grid: pd.DataFrame | None = None) -> dict[str, Any]:
        """Route a structured action to the appropriate engine.

        Args:
            action: The service action to perform.
            payload: Action-specific parameters as a dict.
            grid: Optional DataFrame with context data.

        Returns:
            Flat dict with ok, action, r_* keys for hxPy Grid conversion.
        """
        if payload is None:
            payload = {}

        if grid is not None:
            payload["grid"] = self._converter.normalize_dataframe(grid)

        return self._orchestrator.handle(action, payload)

    def ask(self, text: str, grid: pd.DataFrame | None = None) -> dict[str, Any]:
        """Natural language entry point — parse instruction and route.

        Args:
            text: Natural language instruction (Chinese or English).
            grid: Optional DataFrame with context data.

        Returns:
            Flat dict with action result for hxPy Grid conversion.
        """
        payload: dict[str, Any] = {"text": text}
        if grid is not None:
            payload["grid"] = self._converter.normalize_dataframe(grid)

        # Extract context from grid for LLM enrichment
        context: dict[str, Any] = {}
        if grid is not None and not grid.empty:
            if "site" in grid.columns:
                sites = grid["site"].dropna().unique().tolist()
                if sites:
                    context["available_sites"] = sites[:5]
            if "equip" in grid.columns:
                equips = grid["equip"].dropna().unique().tolist()
                if equips:
                    context["available_equips"] = equips[:10]
            if "point" in grid.columns:
                points = grid["point"].dropna().unique().tolist()
                if points:
                    context["available_points"] = points[:20]
            context["context_summary"] = f"系统包含{len(grid)}条记录"

        payload["context"] = json.dumps(context, ensure_ascii=False)

        return self._orchestrator.handle(action="ask", payload=payload)


# ── Local Debugging Entry Point ──


def main() -> None:
    """Local debugging: test BaAgentService outside hxPy."""
    print("=" * 60)
    print("BA-Agent Service - Local Testing Mode")
    print("=" * 60)
    print()

    svc = BaAgentService(enable_llm=True)
    print("Registered Actions:", svc.registered_actions)
    print("Registered Engines:", svc.registered_engines)
    print("LLM Status:", svc.llm_status)
    print()

    test_cases = [
        ("诊断一下 AHU-01 的故障", "diagnose"),
        ("优化12楼空调设定值", "optimize"),
        ("检查所有温度传感器状态", "inspect"),
        ("生成12楼AHU监控画面", "hmi"),
        ("生成今日运维报告", "report"),
    ]

    for i, (test_input, expected_action) in enumerate(test_cases, 1):
        print(f"Test {i}: {test_input}")
        print(f"Expected action: {expected_action}")
        print("-" * 40)
        response = svc.ask(test_input)
        print(f"  OK: {response.get('ok')}")
        print(f"  Action: {response.get('action')}")
        print()
