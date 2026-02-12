"""Tests for EnergyOptEngine — load profiling and setpoint optimization.

Acceptance: simulated equipment data → AI returns optimization with savings estimate.
"""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.services.energy_opt import (
    EnergyOptEngine,
    OptimizationTarget,
    SetpointType,
    _analyze_load_profile,
    _avg_val,
    _classify_point,
    _evaluate_chw_optimization,
    _evaluate_sat_optimization,
    _evaluate_static_pressure_optimization,
    _generate_warnings,
)


@pytest.fixture
def engine() -> EnergyOptEngine:
    return EnergyOptEngine()


# ── Simulated equipment scenarios ──


def _make_ahu_cooling_scenario() -> dict[str, Any]:
    """AHU with low cooling load — opportunity to raise SAT."""
    return {
        "equip_id": "@e:ahu-1",
        "equip_name": "AHU-1",
        "target": "energy",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:1", "dis": "AHU-1 Supply Air Temp", "curVal": 12.5, "hisAvg": 12.8, "hisMin": 11.5, "hisMax": 13.5},
                {"id": "@p:2", "dis": "AHU-1 Cooling Valve Cmd", "curVal": 35.0, "hisAvg": 40.0, "hisMin": 20.0, "hisMax": 65.0},
                {"id": "@p:3", "dis": "AHU-1 Return Air Temp", "curVal": 23.0, "hisAvg": 23.2, "hisMin": 22.0, "hisMax": 24.0},
                {"id": "@p:4", "dis": "AHU-1 Zone Temp", "curVal": 22.5, "hisAvg": 22.8, "hisMin": 21.5, "hisMax": 23.5},
                {"id": "@p:5", "dis": "AHU-1 Fan Speed", "curVal": 65.0, "hisAvg": 60.0, "hisMin": 40.0, "hisMax": 75.0},
                {"id": "@p:6", "dis": "AHU-1 Outdoor Air Temp", "curVal": 30.0, "hisAvg": 28.5, "hisMin": 22.0, "hisMax": 35.0},
            ],
        },
    }


def _make_ahu_high_load_scenario() -> dict[str, Any]:
    """AHU with high cooling load — limited optimization opportunity."""
    return {
        "equip_id": "@e:ahu-2",
        "equip_name": "AHU-2",
        "target": "balanced",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:10", "dis": "AHU-2 Supply Air Temp", "curVal": 13.0, "hisAvg": 13.2, "hisMin": 12.0, "hisMax": 14.5},
                {"id": "@p:11", "dis": "AHU-2 Cooling Valve Cmd", "curVal": 90.0, "hisAvg": 85.0, "hisMin": 70.0, "hisMax": 95.0},
                {"id": "@p:12", "dis": "AHU-2 Zone Temp", "curVal": 24.5, "hisAvg": 23.8, "hisMin": 22.5, "hisMax": 25.0},
                {"id": "@p:13", "dis": "AHU-2 Fan Speed", "curVal": 85.0, "hisAvg": 82.0, "hisMin": 70.0, "hisMax": 92.0},
            ],
        },
    }


def _make_static_pressure_scenario() -> dict[str, Any]:
    """AHU with low fan load — opportunity to reduce static pressure."""
    return {
        "equip_id": "@e:ahu-3",
        "equip_name": "AHU-3",
        "target": "energy",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:20", "dis": "AHU-3 Duct Static Pressure", "curVal": 400.0, "hisAvg": 380.0, "hisMin": 300.0, "hisMax": 450.0},
                {"id": "@p:21", "dis": "AHU-3 Fan Speed", "curVal": 45.0, "hisAvg": 50.0, "hisMin": 35.0, "hisMax": 65.0},
                {"id": "@p:22", "dis": "AHU-3 Supply Air Temp", "curVal": 13.0, "hisAvg": 12.8, "hisMin": 12.0, "hisMax": 13.5},
                {"id": "@p:23", "dis": "AHU-3 Cooling Valve Cmd", "curVal": 30.0, "hisAvg": 35.0, "hisMin": 20.0, "hisMax": 55.0},
            ],
        },
    }


def _make_chiller_scenario() -> dict[str, Any]:
    """Chiller plant with CHW optimization opportunity."""
    return {
        "equip_id": "@e:chiller-1",
        "equip_name": "Chiller-1",
        "target": "energy",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:30", "dis": "Chiller-1 CHW Supply Temp", "curVal": 6.5, "hisAvg": 6.8, "hisMin": 5.5, "hisMax": 7.5},
                {"id": "@p:31", "dis": "Chiller-1 Cooling Valve Cmd", "curVal": 40.0, "hisAvg": 45.0, "hisMin": 25.0, "hisMax": 60.0},
                {"id": "@p:32", "dis": "Chiller-1 Power kW", "curVal": 150.0, "hisAvg": 140.0, "hisMin": 80.0, "hisMax": 200.0},
            ],
        },
    }


def _make_comfort_scenario() -> dict[str, Any]:
    """AHU optimized for comfort (conservative adjustments)."""
    return {
        "equip_id": "@e:ahu-4",
        "equip_name": "AHU-4 (VIP Zone)",
        "target": "comfort",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:40", "dis": "AHU-4 Supply Air Temp", "curVal": 12.0, "hisAvg": 12.2, "hisMin": 11.0, "hisMax": 13.0},
                {"id": "@p:41", "dis": "AHU-4 Cooling Valve Cmd", "curVal": 30.0, "hisAvg": 35.0, "hisMin": 20.0, "hisMax": 50.0},
                {"id": "@p:42", "dis": "AHU-4 Zone Temp", "curVal": 22.0, "hisAvg": 22.2, "hisMin": 21.0, "hisMax": 23.0},
            ],
        },
    }


def _make_extreme_weather_scenario() -> dict[str, Any]:
    """AHU with extreme outdoor temperature — should generate warning."""
    return {
        "equip_id": "@e:ahu-5",
        "equip_name": "AHU-5",
        "target": "energy",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:50", "dis": "AHU-5 Supply Air Temp", "curVal": 12.0, "hisAvg": 12.5, "hisMin": 11.0, "hisMax": 14.0},
                {"id": "@p:51", "dis": "AHU-5 Cooling Valve Cmd", "curVal": 40.0, "hisAvg": 45.0, "hisMin": 30.0, "hisMax": 60.0},
                {"id": "@p:52", "dis": "AHU-5 Outdoor Air Temp", "curVal": 42.0, "hisAvg": 38.0, "hisMin": 35.0, "hisMax": 44.0},
            ],
        },
    }


def _make_no_data_scenario() -> dict[str, Any]:
    """Equipment with no point data."""
    return {
        "equip_id": "@e:orphan",
        "equip_name": "Unknown Equipment",
        "target": "energy",
        "grid": {"columns": [], "rows": [], "meta": {}},
    }


def _make_already_optimal_scenario() -> dict[str, Any]:
    """AHU already running at optimal conditions (high load, everything maxed)."""
    return {
        "equip_id": "@e:ahu-6",
        "equip_name": "AHU-6",
        "target": "energy",
        "grid": {
            "columns": ["id", "dis", "curVal", "hisAvg", "hisMin", "hisMax"],
            "rows": [
                {"id": "@p:60", "dis": "AHU-6 Supply Air Temp", "curVal": 12.0, "hisAvg": 12.0, "hisMin": 11.5, "hisMax": 12.5},
                {"id": "@p:61", "dis": "AHU-6 Cooling Valve Cmd", "curVal": 75.0, "hisAvg": 72.0, "hisMin": 60.0, "hisMax": 85.0},
                {"id": "@p:62", "dis": "AHU-6 Fan Speed", "curVal": 80.0, "hisAvg": 78.0, "hisMin": 65.0, "hisMax": 88.0},
            ],
        },
    }


# ── Tests ──


class TestEnergyOptDiagnosis:
    """Test the full optimization workflow with simulated scenarios."""

    def test_ahu_cooling_optimization(self, engine: EnergyOptEngine) -> None:
        """Low cooling load AHU → should recommend raising SAT."""
        result = engine.execute("optimize", _make_ahu_cooling_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence > 0.5
        data = result.data
        assert data["target"] == "energy"
        assert data["equipment_id"] == "@e:ahu-1"
        assert len(data["setpoint_recommendations"]) > 0

        # Should have SAT raise recommendation
        sat_recs = [r for r in data["setpoint_recommendations"]
                    if r["setpoint_type"] == "supply_air_temp"]
        assert len(sat_recs) > 0
        rec = sat_recs[0]
        assert rec["recommended_value"] > rec["current_value"]
        assert rec["savings_pct"] > 0

    def test_high_load_limited_optimization(self, engine: EnergyOptEngine) -> None:
        """High cooling load AHU → comfort-priority SAT lowering with balanced target."""
        result = engine.execute("optimize", _make_ahu_high_load_scenario())

        assert result.status == "ok"
        data = result.data
        # Should have SAT lowering recommendation (cooling at 90%, balanced target)
        sat_recs = [r for r in data["setpoint_recommendations"]
                    if r["setpoint_type"] == "supply_air_temp"]
        if sat_recs:
            # If SAT recommendation exists, it should lower SAT
            assert sat_recs[0]["recommended_value"] < sat_recs[0]["current_value"]

    def test_static_pressure_optimization(self, engine: EnergyOptEngine) -> None:
        """Low fan speed → should recommend reducing static pressure."""
        result = engine.execute("optimize", _make_static_pressure_scenario())

        assert result.status == "ok"
        data = result.data
        assert len(data["setpoint_recommendations"]) > 0

        # Should have static pressure reduction
        sp_recs = [r for r in data["setpoint_recommendations"]
                   if r["setpoint_type"] == "static_pressure"]
        assert len(sp_recs) > 0
        rec = sp_recs[0]
        assert rec["recommended_value"] < rec["current_value"]
        assert rec["savings_pct"] > 0

    def test_chw_optimization(self, engine: EnergyOptEngine) -> None:
        """Chiller with low cooling load → should recommend raising CHW temp."""
        result = engine.execute("optimize", _make_chiller_scenario())

        assert result.status == "ok"
        data = result.data
        assert len(data["setpoint_recommendations"]) > 0

        chw_recs = [r for r in data["setpoint_recommendations"]
                    if r["setpoint_type"] == "chilled_water_temp"]
        assert len(chw_recs) > 0
        rec = chw_recs[0]
        assert rec["recommended_value"] > rec["current_value"]
        assert rec["savings_pct"] > 0

    def test_comfort_target_conservative(self, engine: EnergyOptEngine) -> None:
        """Comfort target → smaller adjustments than energy target."""
        # Run same-ish data with comfort vs energy target
        comfort_result = engine.execute("optimize", _make_comfort_scenario())
        energy_scenario = _make_comfort_scenario()
        energy_scenario["target"] = "energy"
        energy_result = engine.execute("optimize", energy_scenario)

        comfort_recs = comfort_result.data["setpoint_recommendations"]
        energy_recs = energy_result.data["setpoint_recommendations"]

        # Both should have SAT recommendations
        comfort_sat = [r for r in comfort_recs if r["setpoint_type"] == "supply_air_temp"]
        energy_sat = [r for r in energy_recs if r["setpoint_type"] == "supply_air_temp"]

        if comfort_sat and energy_sat:
            # Comfort raise should be smaller than energy raise
            comfort_raise = comfort_sat[0]["recommended_value"] - comfort_sat[0]["current_value"]
            energy_raise = energy_sat[0]["recommended_value"] - energy_sat[0]["current_value"]
            assert energy_raise >= comfort_raise

    def test_extreme_weather_warning(self, engine: EnergyOptEngine) -> None:
        """Extreme outdoor temp → should include warning."""
        result = engine.execute("optimize", _make_extreme_weather_scenario())

        assert result.status == "ok"
        warnings = result.data["warnings"]
        assert len(warnings) > 0
        assert any("outdoor temperature" in w.lower() or "extreme" in w.lower() for w in warnings)

    def test_no_data_low_confidence(self, engine: EnergyOptEngine) -> None:
        """No point data → should return ok with zero confidence."""
        result = engine.execute("optimize", _make_no_data_scenario())

        assert result.status == "ok"
        assert result.confidence is not None
        assert result.confidence == 0.0
        assert len(result.data["setpoint_recommendations"]) == 0

    def test_already_optimal(self, engine: EnergyOptEngine) -> None:
        """Equipment at optimal → no or minimal recommendations."""
        result = engine.execute("optimize", _make_already_optimal_scenario())

        assert result.status == "ok"
        # Cooling at 75%, not below 50 threshold for SAT raise
        # Fan at 80%, not below 60 threshold for SP reduction
        # So no recommendations expected
        assert len(result.data["setpoint_recommendations"]) == 0

    def test_result_has_load_profile(self, engine: EnergyOptEngine) -> None:
        """Result should include a load profile summary."""
        result = engine.execute("optimize", _make_ahu_cooling_scenario())

        load_profile = result.data["load_profile"]
        assert "avg_load_pct" in load_profile
        assert "peak_load_pct" in load_profile
        assert "load_trend" in load_profile
        assert load_profile["avg_load_pct"] >= 0

    def test_result_has_savings_estimate(self, engine: EnergyOptEngine) -> None:
        """Result with recommendations should have savings estimates."""
        result = engine.execute("optimize", _make_ahu_cooling_scenario())

        assert result.data["estimated_savings_pct"] > 0
        assert "kWh/day" in result.message or result.data["estimated_savings_kwh"] >= 0

    def test_result_has_explanation(self, engine: EnergyOptEngine) -> None:
        """Result should include a human-readable explanation."""
        result = engine.execute("optimize", _make_ahu_cooling_scenario())
        assert len(result.message) > 0
        assert "AHU-1" in result.message

    def test_default_target_is_balanced(self, engine: EnergyOptEngine) -> None:
        """No target specified → defaults to balanced."""
        scenario = _make_ahu_cooling_scenario()
        del scenario["target"]
        result = engine.execute("optimize", scenario)
        assert result.data["target"] == "balanced"

    def test_invalid_target_defaults_balanced(self, engine: EnergyOptEngine) -> None:
        """Invalid target string → defaults to balanced."""
        scenario = _make_ahu_cooling_scenario()
        scenario["target"] = "invalid"
        result = engine.execute("optimize", scenario)
        assert result.data["target"] == "balanced"


class TestPointClassification:
    """Test individual point classification logic."""

    def test_classify_supply_air_temp(self) -> None:
        assert _classify_point("AHU-1 Supply Air Temp") == "supply_air_temp"

    def test_classify_chw_temp(self) -> None:
        assert _classify_point("Chiller CHW Supply Temp") == "chilled_water_temp"

    def test_classify_static_pressure(self) -> None:
        assert _classify_point("Duct Static Pressure") == "static_pressure"

    def test_classify_zone_temp(self) -> None:
        assert _classify_point("Zone 3 Room Temp") == "zone_temp"

    def test_classify_cooling_valve(self) -> None:
        assert _classify_point("AHU-1 Cooling Valve Cmd") == "cooling_output"

    def test_classify_fan_speed(self) -> None:
        assert _classify_point("AHU-1 Fan Speed") == "fan_speed"

    def test_classify_power(self) -> None:
        assert _classify_point("Chiller Power kW") == "power"

    def test_classify_outdoor_temp(self) -> None:
        assert _classify_point("Outdoor Air Temp") == "outdoor_temp"

    def test_classify_return_air_temp(self) -> None:
        assert _classify_point("AHU-1 Return Air Temp") == "return_air_temp"

    def test_classify_unknown(self) -> None:
        assert _classify_point("Random Point XYZ") is None


class TestLoadProfileAnalysis:
    """Test load profile analysis from classified data."""

    def test_normal_load_profile(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "cooling_output": [{"curVal": 40.0, "hisAvg": 45.0, "hisMax": 65.0}],
            "fan_speed": [{"curVal": 55.0, "hisAvg": 50.0, "hisMax": 70.0}],
        }
        profile = _analyze_load_profile(classified)
        assert profile.avg_load_pct > 0
        assert profile.peak_load_pct > 0
        assert profile.load_trend in ("stable", "increasing", "decreasing")

    def test_empty_load_profile(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {}
        profile = _analyze_load_profile(classified)
        assert profile.avg_load_pct == 50.0  # Default
        assert profile.peak_load_pct == 80.0  # Default
        assert profile.load_trend == "stable"

    def test_increasing_trend(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "cooling_output": [{"curVal": 80.0, "hisAvg": 50.0, "hisMax": 85.0}],
        }
        profile = _analyze_load_profile(classified)
        assert profile.load_trend == "increasing"

    def test_decreasing_trend(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "cooling_output": [{"curVal": 30.0, "hisAvg": 50.0, "hisMax": 70.0}],
        }
        profile = _analyze_load_profile(classified)
        assert profile.load_trend == "decreasing"


class TestHelperFunctions:
    """Test utility functions."""

    def test_avg_val_normal(self) -> None:
        points = [{"curVal": 10.0}, {"curVal": 20.0}, {"curVal": 30.0}]
        assert _avg_val(points, "curVal") == 20.0

    def test_avg_val_empty(self) -> None:
        assert _avg_val([], "curVal") is None

    def test_avg_val_missing_key(self) -> None:
        points = [{"other": 10.0}]
        assert _avg_val(points, "curVal") is None

    def test_avg_val_non_numeric(self) -> None:
        points = [{"curVal": "not a number"}, {"curVal": 20.0}]
        assert _avg_val(points, "curVal") == 20.0


class TestWarnings:
    """Test warning generation."""

    def test_extreme_heat_warning(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "outdoor_temp": [{"curVal": 42.0}],
        }
        warnings = _generate_warnings(classified, [])
        assert len(warnings) > 0
        assert any("extreme" in w.lower() or "outdoor" in w.lower() for w in warnings)

    def test_extreme_cold_warning(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "outdoor_temp": [{"curVal": -15.0}],
        }
        warnings = _generate_warnings(classified, [])
        assert len(warnings) > 0
        assert any("cold" in w.lower() for w in warnings)

    def test_no_warnings_normal_conditions(self) -> None:
        classified: dict[str, list[dict[str, Any]]] = {
            "outdoor_temp": [{"curVal": 25.0}],
        }
        warnings = _generate_warnings(classified, [])
        assert len(warnings) == 0


class TestEngineInterface:
    """Test engine metadata and interface compliance."""

    def test_engine_name(self, engine: EnergyOptEngine) -> None:
        assert engine.name == "energy"

    def test_engine_actions(self, engine: EnergyOptEngine) -> None:
        assert "optimize" in engine.actions

    def test_can_handle_optimize(self, engine: EnergyOptEngine) -> None:
        assert engine.can_handle("optimize") is True

    def test_cannot_handle_diagnose(self, engine: EnergyOptEngine) -> None:
        assert engine.can_handle("diagnose") is False

    def test_unsupported_action_raises(self, engine: EnergyOptEngine) -> None:
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("diagnose", {})


class TestEngineIntegration:
    """Test EnergyOptEngine through the full BaAgentService pipeline."""

    def test_service_optimize_action(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.handle(
            action="optimize",
            payload=_make_ahu_cooling_scenario(),
        )
        assert result["ok"] is True
        assert result["action"] == "optimize"
        assert result["r_status"] == "ok"

    def test_service_ask_optimize(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.ask("优化AHU-1的能耗设定值")
        assert result["ok"] is True
        assert result["action"] == "optimize"

    def test_service_ask_optimize_english(self) -> None:
        from baAgentPy.main import BaAgentService

        svc = BaAgentService()
        result = svc.ask("optimize energy for floor 3")
        assert result["ok"] is True
        assert result["action"] == "optimize"
