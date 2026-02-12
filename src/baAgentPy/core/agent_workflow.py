"""AI task routing and instruction parsing.

AgentWorkflow is the central orchestrator that:
1. Maintains a registry of domain-specific engines (FDD, energy, etc.)
2. Parses natural language instructions into structured actions
3. Routes requests to the appropriate engine
4. Returns standardized results

Currently uses keyword-based NL parsing. Will be upgraded to LLM-based
instruction parsing (via LangChain) in a later phase.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


class ParsedInstruction(BaseModel):
    """Result of parsing a natural language instruction."""

    action: str = Field(description="Resolved action name")
    confidence: float = Field(description="Parsing confidence 0.0–1.0")
    payload: dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    raw_text: str = Field(description="Original instruction text")


# ── Keyword patterns for NL instruction parsing ──
# Each entry: (compiled regex pattern, action name, confidence)
_INTENT_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # FDD / diagnostics
    (re.compile(r"diagnos|fault|alarm|rca|root.?cause|故障|诊断|报警", re.IGNORECASE), "diagnose", 0.85),
    # Energy optimization
    (re.compile(r"optimi[zs]|energy|setpoint|pid|节能|优化|能耗|设定值", re.IGNORECASE), "optimize", 0.85),
    # Virtual inspection
    (re.compile(r"inspect|health|drift|sensor.?check|巡检|传感器|健康", re.IGNORECASE), "inspect", 0.85),
    # HMI generation
    (re.compile(r"hmi|layout|graphic|interface|画面|界面|布局", re.IGNORECASE), "hmi", 0.85),
    # Report generation
    (re.compile(r"report|brief|summar|日报|报告|摘要|运维总结", re.IGNORECASE), "report", 0.85),
    # Auto-tagging
    (re.compile(r"tag|label|haystack|标签|打标|自动标注", re.IGNORECASE), "tag", 0.85),
]


class AgentWorkflow:
    """Central orchestrator for BA-Agent AI operations.

    Manages a registry of domain engines, parses instructions, and routes
    requests to the appropriate engine.

    Usage:
        workflow = AgentWorkflow(engines=[FddEngine(), EnergyOptEngine(), ...])
        result = workflow.route("diagnose", {"alarm_id": "..."})
        result = workflow.interpret_and_route("诊断一下这个报警")
    """

    def __init__(self, engines: list[BaseEngine] | None = None) -> None:
        self._engines: dict[str, BaseEngine] = {}
        self._action_map: dict[str, BaseEngine] = {}

        if engines:
            for engine in engines:
                self.register_engine(engine)

    def register_engine(self, engine: BaseEngine) -> None:
        """Register a domain engine and index its actions."""
        self._engines[engine.name] = engine
        for action in engine.actions:
            self._action_map[action] = engine

    @property
    def registered_actions(self) -> list[str]:
        """List all actions supported by registered engines."""
        return list(self._action_map.keys())

    @property
    def registered_engines(self) -> list[str]:
        """List all registered engine names."""
        return list(self._engines.keys())

    def route(self, action: str, payload: dict[str, Any] | None = None) -> EngineResult:
        """Route a structured action to the appropriate engine.

        Args:
            action: The action name (e.g., 'diagnose', 'optimize').
            payload: Action-specific data.

        Returns:
            EngineResult from the domain engine.

        Raises:
            ValueError: If no engine is registered for the action.
        """
        if payload is None:
            payload = {}

        engine = self._action_map.get(action)
        if engine is None:
            raise ValueError(
                f"No engine registered for action '{action}'. "
                f"Available: {self.registered_actions}"
            )

        return engine.execute(action, payload)

    def interpret(self, text: str) -> ParsedInstruction:
        """Parse a natural language instruction into a structured action.

        Uses keyword-based pattern matching. Will be upgraded to LLM-based
        parsing in a later phase.

        Args:
            text: Natural language instruction (Chinese or English).

        Returns:
            ParsedInstruction with the best-matching action and confidence.
        """
        text_clean = text.strip()
        best_action = ""
        best_confidence = 0.0
        match_count = 0

        for pattern, action, base_confidence in _INTENT_PATTERNS:
            matches = pattern.findall(text_clean)
            if matches:
                # More keyword hits → higher confidence
                adjusted = min(base_confidence + len(matches) * 0.05, 0.95)
                if adjusted > best_confidence:
                    best_action = action
                    best_confidence = adjusted
                    match_count = len(matches)

        if not best_action:
            return ParsedInstruction(
                action="unknown",
                confidence=0.0,
                payload={"hint": "Could not parse instruction. Try: diagnose, optimize, inspect, hmi, report, tag"},
                raw_text=text_clean,
            )

        return ParsedInstruction(
            action=best_action,
            confidence=best_confidence,
            payload={"match_count": match_count},
            raw_text=text_clean,
        )

    def interpret_and_route(self, text: str, extra_payload: dict[str, Any] | None = None) -> EngineResult:
        """Parse an NL instruction and route to the appropriate engine.

        Combines interpret() and route() in one step. If parsing confidence
        is too low or the action is unknown, returns an error result instead
        of raising.

        Args:
            text: Natural language instruction.
            extra_payload: Additional payload data to merge with parsed payload.

        Returns:
            EngineResult from the matched engine, or an error result.
        """
        parsed = self.interpret(text)

        if parsed.action == "unknown":
            return EngineResult(
                status="error",
                message=f"Could not understand instruction: {text}",
                data={"parsed": parsed.model_dump()},
            )

        payload = {**parsed.payload, **(extra_payload or {})}
        payload["_parsed"] = parsed.model_dump()

        try:
            return self.route(parsed.action, payload)
        except ValueError as e:
            return EngineResult(
                status="error",
                message=str(e),
                data={"parsed": parsed.model_dump()},
            )
