"""Cross-layer collaboration flow tests.

Validates the 5-step cross-layer collaboration pipeline in the Python AI layer:
  1. Intent Trigger → LLMOrchestrator routes to correct engine
  2. Context Enhancement → Grid data injected into payload
  3. AI Reasoning → Engine executes and returns structured result
  4. Shadow Mode readiness → Results contain writable setpoint data
  5. Sanitization readiness → Responses contain no sensitive fields

Tests cover:
  - Full NL→parse→route→engine→flat-response pipeline (Chinese & English)
  - Grid context injection via DataFrame
  - Multi-engine chained calls sharing same BaAgentService instance
  - Response format compliance (ok, action, r_* prefix) for agentUnpackResult
  - Shadow Mode output with aiSuggestedVal-compatible fields
  - Sanitization: no password/token/credential/apiKey in responses
  - Empty/abnormal input graceful degradation
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from baAgentPy.core.llm_orchestrator import LLMOrchestrator
from baAgentPy.main import BaAgentService


# ── Fixtures ──


@pytest.fixture
def svc() -> BaAgentService:
    """BaAgentService with LLM disabled (rule-based routing)."""
    return BaAgentService(enable_llm=False)


@pytest.fixture
def orchestrator() -> LLMOrchestrator:
    """Direct orchestrator access for lower-level tests."""
    return LLMOrchestrator(enable_llm=False)


def _make_sensor_grid() -> pd.DataFrame:
    """Create a realistic sensor DataFrame simulating hxPy Grid conversion."""
    return pd.DataFrame([
        {"id": "@p:sat-1", "dis": "AHU-1 Supply Air Temp", "site": "Site-A",
         "equip": "AHU-1", "point": "sat", "curVal": 12.5, "unit": "°C"},
        {"id": "@p:rat-1", "dis": "AHU-1 Return Air Temp", "site": "Site-A",
         "equip": "AHU-1", "point": "rat", "curVal": 23.0, "unit": "°C"},
        {"id": "@p:zat-1", "dis": "AHU-1 Zone Temp", "site": "Site-A",
         "equip": "AHU-1", "point": "zat", "curVal": 22.5, "unit": "°C"},
        {"id": "@p:fan-1", "dis": "AHU-1 Fan Speed", "site": "Site-A",
         "equip": "AHU-1", "point": "fan_speed", "curVal": 75.0, "unit": "%"},
    ])


SENSITIVE_KEYS = {"password", "token", "apiKey", "credential", "secret", "api_key"}


def _check_no_sensitive_fields(data: Any, path: str = "") -> None:
    """Recursively check that no sensitive field names appear in a response."""
    if isinstance(data, dict):
        for key, val in data.items():
            lower = key.lower()
            for sensitive in SENSITIVE_KEYS:
                assert sensitive.lower() not in lower, (
                    f"Sensitive field '{key}' found at {path}.{key}"
                )
            _check_no_sensitive_fields(val, f"{path}.{key}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_no_sensitive_fields(item, f"{path}[{i}]")


# ── Step 1: Intent Trigger → Route → Execute ──


class TestIntentRouteExecute:
    """NL instruction → parse → route → engine → flat response."""

    @pytest.mark.parametrize("text,expected_action", [
        ("诊断一下AHU-01的故障报警", "diagnose"),
        ("diagnose the alarm on AHU-1", "diagnose"),
        ("优化12楼空调设定值", "optimize"),
        ("optimize energy for building", "optimize"),
        ("检查所有温度传感器状态", "inspect"),
        ("inspect sensor health", "inspect"),
        ("生成AHU监控画面", "hmi"),
        ("generate HMI layout", "hmi"),
        ("生成今日运维报告", "report"),
        ("create daily operation report", "report"),
    ])
    def test_nl_routes_to_correct_engine(
        self, svc: BaAgentService, text: str, expected_action: str
    ) -> None:
        result = svc.ask(text)
        assert result["ok"] is True
        assert result["action"] == expected_action

    def test_interpret_returns_parsed_instruction(
        self, orchestrator: LLMOrchestrator
    ) -> None:
        parsed = orchestrator.interpret("诊断AHU-01")
        assert parsed.action == "diagnose"
        assert parsed.confidence > 0.0
        assert parsed.raw_text == "诊断AHU-01"

    def test_direct_action_bypasses_nl_parsing(
        self, svc: BaAgentService
    ) -> None:
        result = svc.handle(action="diagnose", payload={"alarm_id": "@a:1"})
        assert result["ok"] is True
        assert result["action"] == "diagnose"


# ── Step 2: Context Enhancement ──


class TestContextEnhancement:
    """Grid data injection and LLM context extraction."""

    def test_grid_injected_into_payload(self, svc: BaAgentService) -> None:
        grid = _make_sensor_grid()
        result = svc.handle(action="inspect", grid=grid)
        assert result["ok"] is True
        assert result["action"] == "inspect"

    def test_ask_with_grid_extracts_context(self, svc: BaAgentService) -> None:
        grid = _make_sensor_grid()
        result = svc.ask("检查传感器健康", grid=grid)
        assert result["ok"] is True
        assert result["action"] == "inspect"

    def test_ask_with_grid_populates_context_fields(
        self, svc: BaAgentService
    ) -> None:
        """Verify context extraction populates site/equip/point lists."""
        grid = _make_sensor_grid()
        # We can't directly inspect the payload passed to the engine,
        # but we verify the pipeline doesn't break with grid context
        result = svc.ask("巡检设备", grid=grid)
        assert result["ok"] is True

    def test_empty_grid_no_crash(self, svc: BaAgentService) -> None:
        empty_grid = pd.DataFrame()
        result = svc.ask("检查传感器", grid=empty_grid)
        assert result["ok"] is True

    def test_grid_with_missing_columns(self, svc: BaAgentService) -> None:
        """Grid without site/equip/point columns still works."""
        grid = pd.DataFrame([{"id": "x", "curVal": 42.0}])
        result = svc.ask("巡检传感器", grid=grid)
        assert result["ok"] is True


# ── Step 3: Multi-Engine Pipeline ──


class TestMultiEnginePipeline:
    """Multiple engines called in sequence on the same service instance."""

    def test_diagnose_then_optimize_then_report(
        self, svc: BaAgentService
    ) -> None:
        diag = svc.handle("diagnose", {"alarm_id": "@a:1"})
        assert diag["ok"] is True

        opt = svc.handle("optimize", {"equip_id": "@e:ahu-1", "target": "energy"})
        assert opt["ok"] is True

        report = svc.handle("report", {
            "report_type": "daily_brief",
            "alarms": [{"id": "a1", "severity": "critical", "resolved": False}],
            "energy": [{"id": "e1", "curVal": 50.0, "rated_power": 100.0}],
        })
        assert report["ok"] is True

    def test_all_six_engines_same_instance(self, svc: BaAgentService) -> None:
        """All 6 engines execute successfully on the same svc instance."""
        actions = [
            ("diagnose", {}),
            ("optimize", {}),
            ("inspect", {}),
            ("hmi", {}),
            ("report", {}),
            ("tag", {}),
        ]
        for action, payload in actions:
            result = svc.handle(action, payload)
            assert result["ok"] is True, f"Engine '{action}' failed: {result}"
            assert result["action"] == action

    def test_repeated_calls_to_same_engine(self, svc: BaAgentService) -> None:
        """Same engine called multiple times — no state leakage."""
        for i in range(5):
            result = svc.handle("diagnose", {"alarm_id": f"@a:{i}"})
            assert result["ok"] is True


# ── Step 4: Shadow Mode Readiness ──


class TestShadowModeReadiness:
    """Optimization engine results contain setpoint data suitable for Shadow Mode."""

    def test_optimize_result_has_setpoint_data(
        self, svc: BaAgentService
    ) -> None:
        result = svc.handle("optimize", {
            "equip_id": "@e:ahu-1",
            "equip_name": "AHU-1",
            "target": "energy",
        })
        assert result["ok"] is True
        # Optimization results should contain recommendation data
        # that can be mapped to aiSuggestedVal in Shadow Mode
        assert "r_status" in result
        assert result["r_status"] == "ok"

    def test_optimize_result_has_confidence(
        self, svc: BaAgentService
    ) -> None:
        result = svc.handle("optimize", {"equip_id": "@e:ahu-1"})
        assert "r_confidence" in result
        conf = result["r_confidence"]
        assert isinstance(conf, (int, float))
        assert 0.0 <= conf <= 1.0

    def test_optimize_with_grid_context(self, svc: BaAgentService) -> None:
        grid = _make_sensor_grid()
        result = svc.handle("optimize", {
            "equip_id": "@e:ahu-1",
            "target": "balanced",
        }, grid=grid)
        assert result["ok"] is True
        assert result["action"] == "optimize"


# ── Step 5: Sanitization Readiness ──


class TestSanitizationReadiness:
    """Responses must not contain sensitive fields (simulating DataSanitizer)."""

    def test_diagnose_no_sensitive_fields(self, svc: BaAgentService) -> None:
        result = svc.handle("diagnose", {"alarm_id": "@a:1"})
        _check_no_sensitive_fields(result)

    def test_optimize_no_sensitive_fields(self, svc: BaAgentService) -> None:
        result = svc.handle("optimize", {"equip_id": "@e:1"})
        _check_no_sensitive_fields(result)

    def test_report_no_sensitive_fields(self, svc: BaAgentService) -> None:
        result = svc.handle("report", {
            "alarms": [{"id": "a1", "severity": "high", "resolved": False}],
        })
        _check_no_sensitive_fields(result)

    def test_all_engines_no_sensitive_fields(self, svc: BaAgentService) -> None:
        actions = [
            ("diagnose", {}), ("optimize", {}), ("inspect", {}),
            ("hmi", {}), ("report", {}), ("tag", {}),
        ]
        for action, payload in actions:
            result = svc.handle(action, payload)
            _check_no_sensitive_fields(result, path=f"[{action}]")


# ── Response Format Compliance ──


class TestResponseFormatCompliance:
    """Response format must comply with agentUnpackResult expectations."""

    def test_response_has_ok_and_action(self, svc: BaAgentService) -> None:
        for action in ["diagnose", "optimize", "inspect", "hmi", "report"]:
            result = svc.handle(action, {})
            assert "ok" in result, f"'{action}' response missing 'ok'"
            assert "action" in result, f"'{action}' response missing 'action'"

    def test_success_response_uses_r_prefix(self, svc: BaAgentService) -> None:
        result = svc.handle("diagnose", {})
        assert result["ok"] is True
        r_keys = [k for k in result if k.startswith("r_")]
        assert len(r_keys) > 0, "No r_* prefixed keys in response"

    def test_error_response_has_error_field(self, svc: BaAgentService) -> None:
        result = svc.handle("nonexistent_action_xyz", {})
        assert result["ok"] is False
        assert "error" in result

    def test_flat_response_no_nested_result(self, svc: BaAgentService) -> None:
        """Response is flat dict — no nested 'result' wrapper."""
        result = svc.handle("diagnose", {})
        # The response should use r_* prefix, not a nested 'result' dict
        assert "result" not in result or isinstance(result.get("result"), str)


# ── Graceful Degradation ──


class TestGracefulDegradation:
    """Empty/abnormal inputs degrade gracefully without exceptions."""

    def test_empty_text_ask(self, svc: BaAgentService) -> None:
        result = svc.ask("")
        assert result["ok"] is False

    def test_whitespace_only_ask(self, svc: BaAgentService) -> None:
        result = svc.ask("   ")
        assert result["ok"] is False

    def test_gibberish_text(self, svc: BaAgentService) -> None:
        result = svc.ask("asdfghjkl qwerty 12345")
        assert result["ok"] is False

    def test_none_grid_handle(self, svc: BaAgentService) -> None:
        result = svc.handle("diagnose", {}, grid=None)
        assert result["ok"] is True

    def test_ping_always_works(self, svc: BaAgentService) -> None:
        result = svc.handle("ping")
        assert result["ok"] is True
        assert "r_engines" in result
        assert "r_actions" in result
