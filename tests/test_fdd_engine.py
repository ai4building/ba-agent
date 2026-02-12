"""Tests for FDD engine — fault pattern recognition and root cause analysis.

Acceptance: simulated alarm → AI returns diagnosis with confidence score.
"""

from __future__ import annotations

import pytest

from baAgentPy.services.fdd_engine import (
    DiagnosisResult,
    FaultCategory,
    FaultSeverity,
    FddEngine,
    _evaluate_conditions,
)


@pytest.fixture
def engine() -> FddEngine:
    return FddEngine()


# ── Simulated alarm scenarios ──


def _make_ahu_high_sat_scenario() -> dict:
    """Simulate: AHU supply air temp high + cooling valve fully open."""
    return {
        "alarm_id": "@p:ahu1-sat-alarm",
        "alarm_message": "AHU-1 supply air temperature high alarm",
        "equip_id": "@e:ahu-1",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:1", "dis": "AHU-1 Supply Air Temp", "curVal": 22.5, "hisAvg": 13.0, "hisMin": 12.0, "hisMax": 14.5},
                {"id": "@p:2", "dis": "AHU-1 Cooling Valve Cmd", "curVal": 95.0, "hisAvg": 60.0, "hisMin": 30.0, "hisMax": 80.0},
                {"id": "@p:3", "dis": "AHU-1 Return Air Temp", "curVal": 24.0, "hisAvg": 23.5, "hisMin": 22.0, "hisMax": 25.0},
                {"id": "@p:4", "dis": "AHU-1 Fan Speed", "curVal": 85.0, "hisAvg": 80.0, "hisMin": 60.0, "hisMax": 90.0},
            ],
            "meta": {},
        },
    }


def _make_vav_low_airflow_scenario() -> dict:
    """Simulate: VAV airflow below minimum, damper fully open."""
    return {
        "alarm_id": "@p:vav3-flow-alarm",
        "alarm_message": "VAV-3 airflow too low",
        "equip_id": "@e:vav-3",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:10", "dis": "VAV-3 Airflow CFM", "curVal": 30.0, "hisAvg": 200.0, "hisMin": 150.0, "hisMax": 350.0},
                {"id": "@p:11", "dis": "VAV-3 Damper Position", "curVal": 95.0, "hisAvg": 50.0, "hisMin": 20.0, "hisMax": 70.0},
                {"id": "@p:12", "dis": "VAV-3 Zone Temp", "curVal": 26.5, "hisAvg": 23.0, "hisMin": 22.0, "hisMax": 24.0},
            ],
            "meta": {},
        },
    }


def _make_frozen_sensor_scenario() -> dict:
    """Simulate: sensor output stuck at constant value."""
    return {
        "alarm_id": "@p:sensor-frozen",
        "alarm_message": "Sensor reading unchanged",
        "equip_id": "@e:ahu-2",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:20", "dis": "AHU-2 Zone Temp Sensor", "curVal": 22.0, "hisAvg": 22.0, "hisMin": 22.0, "hisMax": 22.005},
                {"id": "@p:21", "dis": "AHU-2 Return Air Temp", "curVal": 23.5, "hisAvg": 23.2, "hisMin": 22.5, "hisMax": 24.0},
            ],
            "meta": {},
        },
    }


def _make_simultaneous_heat_cool_scenario() -> dict:
    """Simulate: heating and cooling active simultaneously."""
    return {
        "alarm_id": "@p:energy-waste",
        "alarm_message": "Heating and cooling both active",
        "equip_id": "@e:ahu-3",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:30", "dis": "AHU-3 Heating Valve Position", "curVal": 45.0, "hisAvg": 40.0, "hisMin": 35.0, "hisMax": 50.0},
                {"id": "@p:31", "dis": "AHU-3 Cooling Valve Position", "curVal": 60.0, "hisAvg": 55.0, "hisMin": 50.0, "hisMax": 65.0},
                {"id": "@p:32", "dis": "AHU-3 Supply Air Temp", "curVal": 15.0, "hisAvg": 14.5, "hisMin": 13.5, "hisMax": 15.5},
            ],
            "meta": {},
        },
    }


def _make_no_data_scenario() -> dict:
    """Simulate: alarm with no point data available."""
    return {
        "alarm_id": "@p:orphan-alarm",
        "alarm_message": "Unknown alarm",
        "equip_id": "",
        "grid": {"columns": [], "rows": [], "meta": {}},
    }


# ── Tests ──


class TestFddDiagnosis:
    """Test the full diagnosis workflow with simulated alarm scenarios."""

    def test_ahu_high_sat_diagnosed(self, engine: FddEngine) -> None:
        """AHU supply air temp high → should match supply_air_temp_high pattern."""
        result = engine.execute("diagnose", _make_ahu_high_sat_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence > 0.5
        data = result.data
        assert data["fault_category"] == "mechanical"
        assert "cooling" in data["root_cause"].lower() or "coil" in data["root_cause"].lower()
        assert len(data["recommendations"]) > 0

    def test_vav_low_airflow_diagnosed(self, engine: FddEngine) -> None:
        """VAV low airflow + damper open → should match vav_low_airflow pattern."""
        result = engine.execute("diagnose", _make_vav_low_airflow_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence > 0.5
        data = result.data
        assert data["fault_category"] == "mechanical"
        assert "airflow" in data["root_cause"].lower() or "vav" in data["root_cause"].lower()

    def test_frozen_sensor_diagnosed(self, engine: FddEngine) -> None:
        """Sensor output unchanged → should match frozen_sensor pattern."""
        result = engine.execute("diagnose", _make_frozen_sensor_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence > 0
        data = result.data
        assert data["fault_category"] == "sensor"
        assert "frozen" in data["root_cause"].lower() or "wiring" in data["root_cause"].lower()

    def test_simultaneous_heat_cool_diagnosed(self, engine: FddEngine) -> None:
        """Heating + cooling active → should match simultaneous pattern."""
        result = engine.execute("diagnose", _make_simultaneous_heat_cool_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence > 0.5
        data = result.data
        assert data["fault_category"] == "energy"
        assert "simultaneous" in data["root_cause"].lower() or "deadband" in data["root_cause"].lower()

    def test_no_data_returns_unknown(self, engine: FddEngine) -> None:
        """No point data → should return unknown with low confidence."""
        result = engine.execute("diagnose", _make_no_data_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence < 0.3
        assert result.data["fault_category"] == "unknown"

    def test_diagnosis_has_rca_chain(self, engine: FddEngine) -> None:
        """Diagnosis should include RCA chain tracing affected points."""
        result = engine.execute("diagnose", _make_ahu_high_sat_scenario())
        rca_chain = result.data["rca_chain"]

        assert len(rca_chain) > 0
        # At least one point should be flagged abnormal
        abnormal = [s for s in rca_chain if s["is_abnormal"]]
        assert len(abnormal) > 0

    def test_diagnosis_has_affected_equipment(self, engine: FddEngine) -> None:
        """Diagnosis should list affected equipment."""
        result = engine.execute("diagnose", _make_ahu_high_sat_scenario())
        assert "@e:ahu-1" in result.data["affected_equipment"]


class TestConditionEvaluation:
    """Test individual fault condition evaluators."""

    def test_sat_high_detected(self) -> None:
        data = [{"dis": "Supply Air Temp", "curVal": 22.0}]
        conditions = _evaluate_conditions(data)
        assert "sat_high" in conditions

    def test_sat_normal_not_flagged(self) -> None:
        data = [{"dis": "Supply Air Temp", "curVal": 12.0}]
        conditions = _evaluate_conditions(data)
        assert "sat_high" not in conditions

    def test_airflow_low_detected(self) -> None:
        data = [{"dis": "Zone Airflow CFM", "curVal": 20.0}]
        conditions = _evaluate_conditions(data)
        assert "airflow_low" in conditions

    def test_damper_open_detected(self) -> None:
        data = [{"dis": "VAV Damper Position", "curVal": 95.0}]
        conditions = _evaluate_conditions(data)
        assert "damper_open" in conditions

    def test_frozen_sensor_detected(self) -> None:
        data = [{"dis": "Temp Sensor", "curVal": 22.0, "hisMin": 22.0, "hisMax": 22.005}]
        conditions = _evaluate_conditions(data)
        assert "value_frozen" in conditions

    def test_reading_deviation_detected(self) -> None:
        data = [{"dis": "Temp Sensor", "curVal": 30.0, "hisAvg": 22.0}]
        conditions = _evaluate_conditions(data)
        assert "reading_deviation" in conditions

    def test_null_curval_skipped(self) -> None:
        data = [{"dis": "Supply Air Temp", "curVal": None}]
        conditions = _evaluate_conditions(data)
        assert len(conditions) == 0


class TestEngineIntegration:
    """Test FDD engine through the full BaAgentService pipeline."""

    def test_service_diagnose_action(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.handle(
            action="diagnose",
            payload=_make_ahu_high_sat_scenario(),
        )
        assert result["ok"] is True
        assert result["action"] == "diagnose"

    def test_service_ask_diagnose(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.ask("诊断一下AHU-1的供风温度报警")
        assert result["ok"] is True
        assert result["action"] == "diagnose"
