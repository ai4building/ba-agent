"""End-to-end integration tests across all BA-Agent engines.

Tests the full pipeline: NL instruction → parse → route → engine → result,
cross-engine scenarios on shared building data, result structure validation,
and error edge cases.
"""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.main import BaAgentService


@pytest.fixture
def svc() -> BaAgentService:
    return BaAgentService()


# ── Shared building data fixtures ──


def _building_alarm_data() -> list[dict[str, Any]]:
    return [
        {"id": "a1", "severity": "critical", "resolved": False, "point_id": "p1"},
        {"id": "a2", "severity": "high", "resolved": True, "point_id": "p2"},
        {"id": "a3", "severity": "medium", "resolved": False, "point_id": "p3"},
    ]


def _building_energy_data() -> list[dict[str, Any]]:
    return [
        {"id": "e1", "curVal": 50.0, "rated_power": 100.0},
        {"id": "e2", "curVal": 85.0, "rated_power": 100.0},
    ]


def _building_sensor_grid() -> dict[str, Any]:
    return {
        "rows": [
            {"id": "@p:1", "dis": "AHU-1 Supply Air Temp", "curVal": 12.5,
             "hisAvg": 12.8, "hisMin": 11.5, "hisMax": 13.5},
            {"id": "@p:2", "dis": "AHU-1 Return Air Temp", "curVal": 23.0,
             "hisAvg": 23.2, "hisMin": 22.0, "hisMax": 24.0},
            {"id": "@p:3", "dis": "AHU-1 Zone Temp", "curVal": 22.5,
             "hisAvg": 22.8, "hisMin": 21.5, "hisMax": 23.5},
        ],
    }


def _building_equipment_data() -> list[dict[str, Any]]:
    return [
        {"equip_id": "@e:ahu-1", "equip_name": "AHU-1", "points": [
            {"id": "@p:1", "dis": "AHU-1 Supply Air Temp", "curVal": 12.5},
            {"id": "@p:2", "dis": "AHU-1 Fan Speed", "curVal": 75.0},
        ]},
    ]


# ── Full Pipeline NL Tests ──


class TestFullPipelineNL:
    def test_nl_diagnose_english(self, svc: BaAgentService) -> None:
        result = svc.ask("diagnose the alarm on AHU-1")
        assert result["ok"] is True
        assert result["action"] == "diagnose"
        assert result["r_status"] == "ok"

    def test_nl_diagnose_chinese(self, svc: BaAgentService) -> None:
        result = svc.ask("诊断一下AHU-1的报警")
        assert result["ok"] is True
        assert result["action"] == "diagnose"

    def test_nl_optimize_english(self, svc: BaAgentService) -> None:
        result = svc.ask("optimize energy for floor 3")
        assert result["ok"] is True
        assert result["action"] == "optimize"

    def test_nl_optimize_chinese(self, svc: BaAgentService) -> None:
        result = svc.ask("优化三楼的能耗")
        assert result["ok"] is True
        assert result["action"] == "optimize"

    def test_nl_inspect_english(self, svc: BaAgentService) -> None:
        result = svc.ask("inspect sensor health on floor 2")
        assert result["ok"] is True
        assert result["action"] == "inspect"

    def test_nl_inspect_chinese(self, svc: BaAgentService) -> None:
        result = svc.ask("巡检二楼传感器健康")
        assert result["ok"] is True
        assert result["action"] == "inspect"

    def test_nl_hmi_english(self, svc: BaAgentService) -> None:
        result = svc.ask("generate HMI layout for AHU system")
        assert result["ok"] is True
        assert result["action"] == "hmi"

    def test_nl_report_english(self, svc: BaAgentService) -> None:
        result = svc.ask("create a daily operation report")
        assert result["ok"] is True
        assert result["action"] == "report"

    def test_nl_report_chinese(self, svc: BaAgentService) -> None:
        result = svc.ask("生成今天的运维日报")
        assert result["ok"] is True
        assert result["action"] == "report"

    def test_nl_unknown_returns_error(self, svc: BaAgentService) -> None:
        result = svc.ask("hello world how are you")
        assert result["ok"] is False


# ── Cross-Engine Scenarios ──


class TestCrossEngineScenarios:
    def test_diagnose_then_report(self, svc: BaAgentService) -> None:
        """FDD diagnosis followed by report on same building."""
        diag = svc.handle(action="diagnose", payload={
            "alarm_id": "@a:1",
            "grid": _building_sensor_grid(),
        })
        assert diag["ok"] is True
        assert diag["r_status"] == "ok"

        report = svc.handle(action="report", payload={
            "report_type": "alarm_summary",
            "alarms": _building_alarm_data(),
        })
        assert report["ok"] is True
        assert report["r_status"] == "ok"

    def test_inspect_then_report(self, svc: BaAgentService) -> None:
        """Inspect sensors, then generate maintenance report."""
        inspect_result = svc.handle(action="inspect", payload={
            "grid": _building_sensor_grid(),
        })
        assert inspect_result["ok"] is True

        report = svc.handle(action="report", payload={
            "report_type": "maintenance",
            "sensors": [
                {"id": "s1", "health_score": 95, "status": "healthy"},
                {"id": "s2", "health_score": 40, "status": "fault"},
            ],
            "equipment": [
                {"id": "eq1", "dis": "AHU-1", "status": "running"},
            ],
        })
        assert report["ok"] is True

    def test_optimize_then_energy_report(self, svc: BaAgentService) -> None:
        """Energy optimization followed by energy summary report."""
        opt = svc.handle(action="optimize", payload={
            "equip_id": "@e:ahu-1",
            "equip_name": "AHU-1",
            "target": "energy",
            "grid": _building_sensor_grid(),
        })
        assert opt["ok"] is True

        report = svc.handle(action="report", payload={
            "report_type": "energy_summary",
            "energy": _building_energy_data(),
        })
        assert report["ok"] is True

    def test_hmi_generation(self, svc: BaAgentService) -> None:
        """HMI generation for building equipment."""
        result = svc.handle(action="hmi", payload={
            "equipment": _building_equipment_data(),
        })
        assert result["ok"] is True
        assert result["r_status"] == "ok"

    def test_all_engines_sequential(self, svc: BaAgentService) -> None:
        """Run all engines in sequence on the same service instance."""
        actions = [
            ("diagnose", {"alarm_id": "@a:1", "grid": _building_sensor_grid()}),
            ("optimize", {"equip_id": "@e:1", "grid": _building_sensor_grid()}),
            ("inspect", {"grid": _building_sensor_grid()}),
            ("hmi", {"equipment": _building_equipment_data()}),
            ("report", {"alarms": _building_alarm_data(), "energy": _building_energy_data()}),
        ]
        for action, payload in actions:
            result = svc.handle(action=action, payload=payload)
            assert result["ok"] is True, f"Failed on action={action}"
            assert result["r_status"] == "ok"

    def test_daily_brief_with_all_data(self, svc: BaAgentService) -> None:
        """Full daily brief with data from all domains."""
        result = svc.handle(action="report", payload={
            "report_type": "daily_brief",
            "alarms": _building_alarm_data(),
            "energy": _building_energy_data(),
            "sensors": [
                {"id": "s1", "health_score": 90, "status": "healthy"},
                {"id": "s2", "health_score": 60, "status": "warning"},
            ],
            "equipment": [
                {"id": "eq1", "dis": "AHU-1", "status": "running"},
                {"id": "eq2", "dis": "Chiller-1", "status": "fault"},
            ],
        })
        assert result["ok"] is True
        data = result.get("r_data", result.get("result", {}))
        # Report should have sections and recommendations
        assert result["r_status"] == "ok"

    def test_ping_between_operations(self, svc: BaAgentService) -> None:
        """Ping still works between engine calls."""
        svc.handle(action="diagnose", payload={"grid": _building_sensor_grid()})
        ping = svc.handle(action="ping")
        assert ping["ok"] is True
        svc.handle(action="report", payload={"alarms": _building_alarm_data()})

    def test_multiple_report_types(self, svc: BaAgentService) -> None:
        """Generate multiple report types from same service."""
        for rtype in ["daily_brief", "alarm_summary", "energy_summary", "maintenance"]:
            result = svc.handle(action="report", payload={
                "report_type": rtype,
                "alarms": _building_alarm_data(),
                "energy": _building_energy_data(),
                "sensors": [{"id": "s1", "health_score": 80, "status": "healthy"}],
                "equipment": [{"id": "eq1", "dis": "AHU-1", "status": "running"}],
            })
            assert result["ok"] is True, f"Failed on report_type={rtype}"


# ── Result Structure Validation ──


class TestResultStructure:
    def test_diagnose_result_keys(self, svc: BaAgentService) -> None:
        result = svc.handle(action="diagnose", payload={"grid": _building_sensor_grid()})
        assert "ok" in result
        assert "action" in result
        assert "r_status" in result

    def test_optimize_result_keys(self, svc: BaAgentService) -> None:
        result = svc.handle(action="optimize", payload={
            "equip_id": "@e:1", "grid": _building_sensor_grid(),
        })
        assert result["r_status"] == "ok"
        assert "r_confidence" in result

    def test_inspect_result_keys(self, svc: BaAgentService) -> None:
        result = svc.handle(action="inspect", payload={"grid": _building_sensor_grid()})
        assert result["r_status"] == "ok"
        assert "r_confidence" in result

    def test_hmi_result_keys(self, svc: BaAgentService) -> None:
        result = svc.handle(action="hmi", payload={
            "equipment": _building_equipment_data(),
        })
        assert result["r_status"] == "ok"

    def test_report_result_keys(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "alarms": _building_alarm_data(),
        })
        assert result["r_status"] == "ok"
        assert "r_confidence" in result

    def test_all_engines_return_ok_status(self, svc: BaAgentService) -> None:
        """All implemented engines return status='ok' (not 'stub')."""
        test_cases = [
            ("diagnose", {"grid": _building_sensor_grid()}),
            ("optimize", {"equip_id": "@e:1", "grid": _building_sensor_grid()}),
            ("inspect", {"grid": _building_sensor_grid()}),
            ("hmi", {"equipment": _building_equipment_data()}),
            ("report", {"alarms": _building_alarm_data()}),
        ]
        for action, payload in test_cases:
            result = svc.handle(action=action, payload=payload)
            assert result["r_status"] == "ok", f"{action} returned {result['r_status']}"

    def test_modeling_engine_returns_ok(self, svc: BaAgentService) -> None:
        """Modeling engine (formerly tag stub) is now implemented."""
        result = svc.handle(action="tag")
        assert result["r_status"] == "ok"

    def test_unknown_action_returns_error(self, svc: BaAgentService) -> None:
        result = svc.handle(action="nonexistent_action")
        assert result["ok"] is False

    def test_report_confidence_is_numeric(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "alarms": _building_alarm_data(),
            "energy": _building_energy_data(),
        })
        conf = result.get("r_confidence")
        assert conf is not None
        assert isinstance(conf, (int, float))
        assert 0.0 <= conf <= 1.0


# ── Error Edge Cases ──


class TestErrorEdgeCases:
    def test_empty_payload_all_engines(self, svc: BaAgentService) -> None:
        """All implemented engines handle empty payloads gracefully."""
        for action in ["diagnose", "optimize", "inspect", "hmi", "report"]:
            result = svc.handle(action=action, payload={})
            assert result["ok"] is True, f"{action} failed on empty payload"

    def test_none_payload(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload=None)
        assert result["ok"] is True

    def test_malformed_alarm_data(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "alarms": "not a list",
        })
        assert result["ok"] is True  # Gracefully handles bad data

    def test_unicode_in_payload(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "alarms": [{"id": "报警-1", "severity": "critical", "resolved": False}],
        })
        assert result["ok"] is True

    def test_unicode_nl_instruction(self, svc: BaAgentService) -> None:
        result = svc.ask("请帮我诊断空调系统的故障报警")
        assert result["ok"] is True

    def test_very_large_alarm_list(self, svc: BaAgentService) -> None:
        alarms = [
            {"id": f"a{i}", "severity": "medium", "resolved": i % 2 == 0}
            for i in range(500)
        ]
        result = svc.handle(action="report", payload={"alarms": alarms})
        assert result["ok"] is True

    def test_mixed_types_in_energy(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "energy": [
                {"id": "e1", "curVal": "not_a_number", "rated_power": 100},
                {"id": "e2", "curVal": 50.0, "rated_power": None},
                {"id": "e3", "curVal": 75.0, "rated_power": 100.0},
            ],
        })
        assert result["ok"] is True

    def test_extra_keys_in_payload(self, svc: BaAgentService) -> None:
        result = svc.handle(action="report", payload={
            "report_type": "daily_brief",
            "alarms": _building_alarm_data(),
            "extra_key": "should be ignored",
            "another_one": 42,
        })
        assert result["ok"] is True
