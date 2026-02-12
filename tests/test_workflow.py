"""Tests for AgentWorkflow — instruction parsing and action routing."""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.core.agent_workflow import AgentWorkflow, ParsedInstruction
from baAgentPy.services import (
    BaseEngine,
    EngineResult,
    EnergyOptEngine,
    FddEngine,
    HmiEngine,
    InspectEngine,
    ReportEngine,
    TaggingEngine,
)


@pytest.fixture
def workflow() -> AgentWorkflow:
    """Workflow with all engines registered."""
    return AgentWorkflow(engines=[
        FddEngine(),
        EnergyOptEngine(),
        InspectEngine(),
        HmiEngine(),
        ReportEngine(),
        TaggingEngine(),
    ])


# ── Engine registration ──


class TestEngineRegistration:
    def test_all_engines_registered(self, workflow: AgentWorkflow) -> None:
        assert "fdd" in workflow.registered_engines
        assert "energy" in workflow.registered_engines
        assert "inspect" in workflow.registered_engines
        assert "hmi" in workflow.registered_engines
        assert "report" in workflow.registered_engines
        assert "tagging" in workflow.registered_engines

    def test_all_actions_indexed(self, workflow: AgentWorkflow) -> None:
        actions = workflow.registered_actions
        for expected in ["diagnose", "optimize", "inspect", "hmi", "report", "tag"]:
            assert expected in actions

    def test_empty_workflow(self) -> None:
        wf = AgentWorkflow()
        assert wf.registered_engines == []
        assert wf.registered_actions == []

    def test_register_engine_dynamically(self) -> None:
        wf = AgentWorkflow()
        wf.register_engine(FddEngine())
        assert "fdd" in wf.registered_engines
        assert "diagnose" in wf.registered_actions


# ── Direct routing ──


class TestRouting:
    @pytest.mark.parametrize("action", [
        "tag",
    ])
    def test_route_to_stub_engine(self, workflow: AgentWorkflow, action: str) -> None:
        result = workflow.route(action)
        assert result.status == "stub"

    @pytest.mark.parametrize("action", [
        "diagnose", "optimize", "inspect", "hmi", "report",
    ])
    def test_route_implemented_engine(self, workflow: AgentWorkflow, action: str) -> None:
        result = workflow.route(action)
        assert result.status == "ok"

    def test_route_unknown_action_raises(self, workflow: AgentWorkflow) -> None:
        with pytest.raises(ValueError, match="No engine registered"):
            workflow.route("nonexistent")

    def test_route_passes_payload(self, workflow: AgentWorkflow) -> None:
        result = workflow.route("diagnose", {"alarm_id": "abc"})
        assert result.status == "ok"


# ── NL instruction parsing ──


class TestInterpret:
    # English
    def test_parse_diagnose_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("diagnose the alarm on AHU-1")
        assert parsed.action == "diagnose"
        assert parsed.confidence > 0

    def test_parse_optimize_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("optimize energy consumption")
        assert parsed.action == "optimize"

    def test_parse_inspect_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("inspect sensor health")
        assert parsed.action == "inspect"

    def test_parse_hmi_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("generate HMI layout")
        assert parsed.action == "hmi"

    def test_parse_report_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("create a daily report summary")
        assert parsed.action == "report"

    def test_parse_tag_english(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("auto-tag these points with haystack labels")
        assert parsed.action == "tag"

    # Chinese
    def test_parse_diagnose_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("诊断一下这个报警")
        assert parsed.action == "diagnose"

    def test_parse_optimize_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("优化能耗设定值")
        assert parsed.action == "optimize"

    def test_parse_inspect_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("巡检传感器健康状态")
        assert parsed.action == "inspect"

    def test_parse_hmi_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("生成画面布局")
        assert parsed.action == "hmi"

    def test_parse_report_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("生成今天的运维日报")
        assert parsed.action == "report"

    def test_parse_tag_chinese(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("给这些点位打标签")
        assert parsed.action == "tag"

    # Unknown
    def test_parse_unknown(self, workflow: AgentWorkflow) -> None:
        parsed = workflow.interpret("hello world")
        assert parsed.action == "unknown"
        assert parsed.confidence == 0.0

    # Confidence
    def test_multiple_keywords_boost_confidence(self, workflow: AgentWorkflow) -> None:
        single = workflow.interpret("diagnose")
        multi = workflow.interpret("diagnose this alarm fault")
        assert multi.confidence > single.confidence


# ── interpret_and_route ──


class TestInterpretAndRoute:
    def test_successful_interpretation_diagnose(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("diagnose alarm on AHU-1")
        assert result.status == "ok"  # FDD engine is implemented

    def test_successful_interpretation_optimize(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("optimize energy consumption")
        assert result.status == "ok"  # Energy engine is implemented

    def test_successful_interpretation_inspect(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("inspect sensor health")
        assert result.status == "ok"  # Inspect engine is implemented

    def test_successful_interpretation_hmi(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("generate HMI layout")
        assert result.status == "ok"

    def test_successful_interpretation_stub(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("auto-tag these points with haystack labels")
        assert result.status == "stub"

    def test_unknown_returns_error(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route("hello world")
        assert result.status == "error"
        assert "Could not understand" in result.message

    def test_extra_payload_merged(self, workflow: AgentWorkflow) -> None:
        result = workflow.interpret_and_route(
            "diagnose alarm",
            extra_payload={"alarm_id": "test-123"},
        )
        assert result.status == "ok"


# ── BaseEngine interface ──


class TestBaseEngineInterface:
    def test_can_handle_positive(self) -> None:
        engine = FddEngine()
        assert engine.can_handle("diagnose") is True

    def test_can_handle_negative(self) -> None:
        engine = FddEngine()
        assert engine.can_handle("optimize") is False

    def test_execute_unsupported_action_raises(self) -> None:
        engine = FddEngine()
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("optimize", {})

    @pytest.mark.parametrize("engine_cls,expected_name", [
        (FddEngine, "fdd"),
        (EnergyOptEngine, "energy"),
        (InspectEngine, "inspect"),
        (HmiEngine, "hmi"),
        (ReportEngine, "report"),
        (TaggingEngine, "tagging"),
    ])
    def test_engine_metadata(self, engine_cls: type[BaseEngine], expected_name: str) -> None:
        engine = engine_cls()
        assert engine.name == expected_name
        assert len(engine.description) > 0
        assert len(engine.actions) > 0
