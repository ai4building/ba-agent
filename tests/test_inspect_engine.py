"""Tests for InspectEngine — sensor health scoring and drift detection.

Acceptance: simulated sensor data → health scores (0-100) with findings.
"""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.services.inspect_engine import (
    FindingType,
    InspectEngine,
    SensorStatus,
    _check_consistency,
    _check_drift,
    _check_frozen,
    _check_missing,
    _check_range,
    _check_spike,
    _infer_sensor_type,
)


@pytest.fixture
def engine() -> InspectEngine:
    return InspectEngine()


# ── Simulated sensor scenarios ──


def _make_healthy_sensors() -> dict[str, Any]:
    """All sensors in good health."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
                {"id": "@p:2", "dis": "Zone-1 Humidity Sensor", "curVal": 55.0, "hisAvg": 54.0, "hisMin": 48.0, "hisMax": 62.0},
                {"id": "@p:3", "dis": "AHU-1 Supply Air Temp", "curVal": 13.0, "hisAvg": 12.8, "hisMin": 11.5, "hisMax": 14.0},
                {"id": "@p:4", "dis": "AHU-1 Fan Speed", "curVal": 65.0, "hisAvg": 62.0, "hisMin": 40.0, "hisMax": 80.0},
            ],
        },
    }


def _make_frozen_sensor() -> dict[str, Any]:
    """One sensor frozen (zero variance), others healthy."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 22.0, "hisAvg": 22.0, "hisMin": 22.0, "hisMax": 22.005},
                {"id": "@p:2", "dis": "Zone-2 Temp Sensor", "curVal": 23.0, "hisAvg": 22.8, "hisMin": 21.5, "hisMax": 24.0},
                {"id": "@p:3", "dis": "Zone-3 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
            ],
        },
    }


def _make_drifted_sensor() -> dict[str, Any]:
    """One sensor with severe drift from baseline."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 35.0, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.5},
                {"id": "@p:2", "dis": "Zone-2 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
                {"id": "@p:3", "dis": "Zone-3 Temp Sensor", "curVal": 22.8, "hisAvg": 22.5, "hisMin": 21.5, "hisMax": 23.8},
            ],
        },
    }


def _make_range_violation() -> dict[str, Any]:
    """Sensor reading outside physical bounds."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 150.0, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.0},
                {"id": "@p:2", "dis": "Zone-1 Humidity Sensor", "curVal": 120.0, "hisAvg": 55.0, "hisMin": 45.0, "hisMax": 65.0},
            ],
        },
    }


def _make_offline_sensor() -> dict[str, Any]:
    """Sensor with no current value (offline)."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": None, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.0},
                {"id": "@p:2", "dis": "Zone-2 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
            ],
        },
    }


def _make_spike_sensor() -> dict[str, Any]:
    """Sensor with a sudden spike above historical range."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 30.0, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 24.0},
            ],
        },
    }


def _make_inconsistent_sensors() -> dict[str, Any]:
    """One sensor disagrees with peers of the same type."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 35.0, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.5},
                {"id": "@p:2", "dis": "Zone-2 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
                {"id": "@p:3", "dis": "Zone-3 Temp Sensor", "curVal": 22.0, "hisAvg": 22.1, "hisMin": 21.0, "hisMax": 23.0},
                {"id": "@p:4", "dis": "Zone-4 Temp Sensor", "curVal": 22.8, "hisAvg": 22.5, "hisMin": 21.5, "hisMax": 23.5},
            ],
        },
    }


def _make_mixed_fleet() -> dict[str, Any]:
    """Mix of healthy, frozen, drifted, and offline sensors."""
    return {
        "grid": {
            "rows": [
                # Healthy
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 22.5, "hisAvg": 22.3, "hisMin": 21.0, "hisMax": 23.5},
                # Frozen
                {"id": "@p:2", "dis": "Zone-2 Temp Sensor", "curVal": 22.0, "hisAvg": 22.0, "hisMin": 22.0, "hisMax": 22.005},
                # Drifted
                {"id": "@p:3", "dis": "Zone-3 Temp Sensor", "curVal": 35.0, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.5},
                # Offline
                {"id": "@p:4", "dis": "Zone-4 Temp Sensor", "curVal": None, "hisAvg": 22.0, "hisMin": 21.0, "hisMax": 23.0},
                # Healthy valve
                {"id": "@p:5", "dis": "AHU-1 Cooling Valve", "curVal": 45.0, "hisAvg": 42.0, "hisMin": 20.0, "hisMax": 70.0},
            ],
        },
    }


def _make_no_data() -> dict[str, Any]:
    """No sensor data at all."""
    return {"grid": {"columns": [], "rows": [], "meta": {}}}


def _make_no_history() -> dict[str, Any]:
    """Sensor with current value but no history."""
    return {
        "grid": {
            "rows": [
                {"id": "@p:1", "dis": "Zone-1 Temp Sensor", "curVal": 22.5},
            ],
        },
    }


# ── Tests ──


class TestInspectionScenarios:
    """Test the full inspection workflow with simulated scenarios."""

    def test_healthy_sensors_high_scores(self, engine: InspectEngine) -> None:
        """All healthy sensors → high aggregate score."""
        result = engine.execute("inspect", _make_healthy_sensors())

        assert result.status == "ok"
        data = result.data
        assert data["aggregate_score"] >= 80
        assert data["healthy_count"] == 4
        assert data["fault_count"] == 0
        assert data["offline_count"] == 0

        for report in data["sensor_reports"]:
            assert report["health_score"] >= 80
            assert report["status"] == "healthy"

    def test_frozen_sensor_detected(self, engine: InspectEngine) -> None:
        """Frozen sensor → low health score, fault/warning status."""
        result = engine.execute("inspect", _make_frozen_sensor())

        data = result.data
        reports = data["sensor_reports"]

        # First sensor is frozen
        frozen_report = reports[0]
        assert frozen_report["health_score"] < 80
        finding_types = [f["finding_type"] for f in frozen_report["findings"]]
        assert "frozen" in finding_types

        # Other sensors should be healthy
        assert reports[1]["status"] == "healthy"

    def test_drifted_sensor_detected(self, engine: InspectEngine) -> None:
        """Drifted sensor → findings include drift."""
        result = engine.execute("inspect", _make_drifted_sensor())

        data = result.data
        drifted = data["sensor_reports"][0]
        assert drifted["health_score"] < 80
        finding_types = [f["finding_type"] for f in drifted["findings"]]
        assert "drift" in finding_types

    def test_range_violation_detected(self, engine: InspectEngine) -> None:
        """Out-of-range sensor → critical range_violation finding."""
        result = engine.execute("inspect", _make_range_violation())

        data = result.data
        for report in data["sensor_reports"]:
            finding_types = [f["finding_type"] for f in report["findings"]]
            assert "range_violation" in finding_types
            assert report["health_score"] < 80

    def test_offline_sensor_detected(self, engine: InspectEngine) -> None:
        """Sensor with no curVal → offline status."""
        result = engine.execute("inspect", _make_offline_sensor())

        data = result.data
        offline_report = data["sensor_reports"][0]
        assert offline_report["status"] == "offline"
        assert offline_report["health_score"] <= 50
        assert data["offline_count"] == 1

    def test_spike_detected(self, engine: InspectEngine) -> None:
        """Sensor with spike above historical max → spike finding."""
        result = engine.execute("inspect", _make_spike_sensor())

        data = result.data
        report = data["sensor_reports"][0]
        finding_types = [f["finding_type"] for f in report["findings"]]
        assert "spike" in finding_types

    def test_inconsistency_detected(self, engine: InspectEngine) -> None:
        """One sensor disagrees with peers → inconsistency finding."""
        result = engine.execute("inspect", _make_inconsistent_sensors())

        data = result.data
        # First sensor reads 35 while others are ~22
        outlier = data["sensor_reports"][0]
        finding_types = [f["finding_type"] for f in outlier["findings"]]
        assert "inconsistency" in finding_types

    def test_mixed_fleet_aggregation(self, engine: InspectEngine) -> None:
        """Mixed fleet → correct aggregate counts."""
        result = engine.execute("inspect", _make_mixed_fleet())

        data = result.data
        assert data["healthy_count"] >= 1
        assert data["fault_count"] + data["offline_count"] >= 1
        assert len(data["sensor_reports"]) == 5
        assert data["aggregate_score"] < 100  # Not all perfect

    def test_no_data_returns_ok(self, engine: InspectEngine) -> None:
        """No data → ok status with zero confidence."""
        result = engine.execute("inspect", _make_no_data())

        assert result.status == "ok"
        assert result.confidence == 0.0
        assert len(result.data["sensor_reports"]) == 0

    def test_no_history_still_works(self, engine: InspectEngine) -> None:
        """Sensor without history → still produces a report (with missing_data finding)."""
        result = engine.execute("inspect", _make_no_history())

        data = result.data
        assert len(data["sensor_reports"]) == 1
        report = data["sensor_reports"][0]
        finding_types = [f["finding_type"] for f in report["findings"]]
        assert "missing_data" in finding_types

    def test_result_has_summary(self, engine: InspectEngine) -> None:
        """Result should include a human-readable summary."""
        result = engine.execute("inspect", _make_healthy_sensors())
        assert "Inspected" in result.message
        assert "health" in result.message.lower()

    def test_result_confidence_with_history(self, engine: InspectEngine) -> None:
        """Result with full history data should have decent confidence."""
        result = engine.execute("inspect", _make_healthy_sensors())
        assert result.confidence is not None
        assert result.confidence > 0.5

    def test_recommendations_generated(self, engine: InspectEngine) -> None:
        """Each sensor report should have a recommendation."""
        result = engine.execute("inspect", _make_frozen_sensor())
        for report in result.data["sensor_reports"]:
            assert len(report["recommendation"]) > 0


class TestIndividualChecks:
    """Test individual sensor check functions."""

    def test_check_frozen_detected(self) -> None:
        point = {"hisMin": 22.0, "hisMax": 22.005}
        finding = _check_frozen(point)
        assert finding is not None
        assert finding.finding_type == FindingType.FROZEN

    def test_check_frozen_normal(self) -> None:
        point = {"hisMin": 21.0, "hisMax": 23.5}
        assert _check_frozen(point) is None

    def test_check_frozen_flatline(self) -> None:
        point = {"hisMin": 22.0, "hisMax": 22.05}
        finding = _check_frozen(point)
        assert finding is not None
        assert finding.finding_type == FindingType.FLATLINE

    def test_check_drift_severe(self) -> None:
        point = {"curVal": 35.0, "hisAvg": 22.0}
        finding = _check_drift(point)
        assert finding is not None
        assert finding.severity == "critical"

    def test_check_drift_moderate(self) -> None:
        point = {"curVal": 28.0, "hisAvg": 22.0}
        finding = _check_drift(point)
        assert finding is not None
        assert finding.severity == "warning"

    def test_check_drift_normal(self) -> None:
        point = {"curVal": 22.5, "hisAvg": 22.0}
        assert _check_drift(point) is None

    def test_check_spike_above(self) -> None:
        point = {"curVal": 30.0, "hisMin": 21.0, "hisMax": 24.0}
        finding = _check_spike(point)
        assert finding is not None
        assert finding.finding_type == FindingType.SPIKE

    def test_check_spike_below(self) -> None:
        point = {"curVal": 15.0, "hisMin": 21.0, "hisMax": 24.0}
        finding = _check_spike(point)
        assert finding is not None
        assert finding.finding_type == FindingType.SPIKE

    def test_check_spike_normal(self) -> None:
        point = {"curVal": 22.5, "hisMin": 21.0, "hisMax": 24.0}
        assert _check_spike(point) is None

    def test_check_range_violation_temp(self) -> None:
        point = {"curVal": 150.0}
        finding = _check_range(point, "temp")
        assert finding is not None
        assert finding.finding_type == FindingType.RANGE_VIOLATION

    def test_check_range_normal(self) -> None:
        point = {"curVal": 22.0}
        assert _check_range(point, "temp") is None

    def test_check_range_no_type(self) -> None:
        point = {"curVal": 999.0}
        assert _check_range(point, None) is None

    def test_check_missing_curval(self) -> None:
        point = {"curVal": None, "hisAvg": 22.0}
        finding = _check_missing(point)
        assert finding is not None
        assert finding.severity == "critical"

    def test_check_missing_history(self) -> None:
        point = {"curVal": 22.0}
        finding = _check_missing(point)
        assert finding is not None
        assert finding.severity == "warning"

    def test_check_missing_all_present(self) -> None:
        point = {"curVal": 22.0, "hisAvg": 22.0}
        assert _check_missing(point) is None

    def test_check_consistency_outlier(self) -> None:
        point = {"id": "@p:1", "curVal": 35.0}
        peers = [
            {"id": "@p:2", "curVal": 22.0},
            {"id": "@p:3", "curVal": 22.5},
            {"id": "@p:4", "curVal": 22.8},
        ]
        finding = _check_consistency(point, peers)
        assert finding is not None
        assert finding.finding_type == FindingType.INCONSISTENCY

    def test_check_consistency_normal(self) -> None:
        point = {"id": "@p:1", "curVal": 22.5}
        peers = [
            {"id": "@p:2", "curVal": 22.0},
            {"id": "@p:3", "curVal": 22.8},
            {"id": "@p:4", "curVal": 23.0},
        ]
        assert _check_consistency(point, peers) is None

    def test_check_consistency_too_few_peers(self) -> None:
        point = {"id": "@p:1", "curVal": 35.0}
        peers = [{"id": "@p:2", "curVal": 22.0}]
        assert _check_consistency(point, peers) is None


class TestSensorTypeInference:
    """Test sensor type inference from point names."""

    def test_temp_english(self) -> None:
        assert _infer_sensor_type("Zone-1 Temp Sensor") == "temp"

    def test_temp_chinese(self) -> None:
        assert _infer_sensor_type("区域温度传感器") == "temp"

    def test_humidity(self) -> None:
        assert _infer_sensor_type("Zone RH Sensor") == "humidity"

    def test_pressure(self) -> None:
        assert _infer_sensor_type("Duct Static Pressure") == "pressure"

    def test_co2(self) -> None:
        assert _infer_sensor_type("Zone CO2 Level") == "co2"

    def test_flow(self) -> None:
        assert _infer_sensor_type("Supply Air CFM") == "flow"

    def test_valve(self) -> None:
        assert _infer_sensor_type("Cooling Valve Position") == "valve"

    def test_damper(self) -> None:
        assert _infer_sensor_type("OA Damper Position") == "damper"

    def test_speed(self) -> None:
        assert _infer_sensor_type("Fan VFD Speed") == "speed"

    def test_power(self) -> None:
        assert _infer_sensor_type("Chiller Power kW") == "power"

    def test_unknown(self) -> None:
        assert _infer_sensor_type("Random Point XYZ") is None


class TestEngineInterface:
    """Test engine metadata and interface compliance."""

    def test_engine_name(self, engine: InspectEngine) -> None:
        assert engine.name == "inspect"

    def test_engine_actions(self, engine: InspectEngine) -> None:
        assert "inspect" in engine.actions

    def test_can_handle_inspect(self, engine: InspectEngine) -> None:
        assert engine.can_handle("inspect") is True

    def test_cannot_handle_diagnose(self, engine: InspectEngine) -> None:
        assert engine.can_handle("diagnose") is False

    def test_unsupported_action_raises(self, engine: InspectEngine) -> None:
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("diagnose", {})


class TestEngineIntegration:
    """Test InspectEngine through the full BaAgentService pipeline."""

    def test_service_inspect_action(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.handle(
            action="inspect",
            payload=_make_healthy_sensors(),
        )
        assert result["ok"] is True
        assert result["action"] == "inspect"
        assert result["r_status"] == "ok"

    def test_service_ask_inspect_chinese(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.ask("巡检一下传感器健康状态")
        assert result["ok"] is True
        assert result["action"] == "inspect"

    def test_service_ask_inspect_english(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.ask("inspect sensor health")
        assert result["ok"] is True
        assert result["action"] == "inspect"
