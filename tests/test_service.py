"""Tests for BaAgentService — main service routing and response handling."""

from __future__ import annotations

import pandas as pd
import pytest

from baAgentPy.main import BaAgentService


@pytest.fixture
def svc() -> BaAgentService:
    return BaAgentService()


class TestServiceRouting:
    def test_ping(self, svc: BaAgentService) -> None:
        result = svc.handle(action="ping")
        assert result["ok"] is True
        assert result["action"] == "ping"
        assert result["r_status"] == "ok"
        assert result["r_initialized"] is True

    def test_ping_lists_engines(self, svc: BaAgentService) -> None:
        result = svc.handle(action="ping")
        engines = result["r_engines"]
        assert "fdd" in engines
        assert "energy" in engines

    def test_ping_lists_actions(self, svc: BaAgentService) -> None:
        result = svc.handle(action="ping")
        actions = result["r_actions"]
        assert "diagnose" in actions
        assert "optimize" in actions

    def test_unknown_action_returns_error(self, svc: BaAgentService) -> None:
        result = svc.handle(action="nonexistent")
        assert result["ok"] is False
        assert "Unknown action" in result["error"]

    @pytest.mark.parametrize("action", [
        "diagnose", "optimize", "inspect", "hmi", "report", "tag", "model",
    ])
    def test_implemented_actions_return_ok(self, svc: BaAgentService, action: str) -> None:
        result = svc.handle(action=action)
        assert result["ok"] is True
        assert result["action"] == action
        assert result["r_status"] == "ok"


class TestServiceWithGrid:
    def test_handle_with_dataframe(self, svc: BaAgentService) -> None:
        df = pd.DataFrame({
            "id": ["@p:1", "@p:2"],
            "curVal": [72.5, 55.0],
        })
        result = svc.handle(action="ping", grid=df)
        assert result["ok"] is True

    def test_handle_with_payload(self, svc: BaAgentService) -> None:
        result = svc.handle(action="ping", payload={"foo": "bar"})
        assert result["ok"] is True

    def test_handle_none_payload(self, svc: BaAgentService) -> None:
        result = svc.handle(action="ping", payload=None)
        assert result["ok"] is True


class TestServiceAsk:
    def test_ask_diagnose_chinese(self, svc: BaAgentService) -> None:
        result = svc.ask("诊断一下AHU-1的报警")
        assert result["ok"] is True
        assert result["action"] == "diagnose"

    def test_ask_optimize_english(self, svc: BaAgentService) -> None:
        result = svc.ask("optimize energy for floor 3")
        assert result["ok"] is True
        assert result["action"] == "optimize"

    def test_ask_unknown_instruction(self, svc: BaAgentService) -> None:
        result = svc.ask("hello world")
        assert result["ok"] is False
        assert result["action"] == "ask"

    def test_ask_with_grid(self, svc: BaAgentService) -> None:
        df = pd.DataFrame({"id": ["@p:1"], "curVal": [72.5]})
        result = svc.ask("检查传感器健康", grid=df)
        assert result["ok"] is True
        assert result["action"] == "inspect"
