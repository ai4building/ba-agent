"""Tests for ModelingEngine — BACnet/Modbus point name parsing and Haystack 4 tag assignment."""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.main import BaAgentService
from baAgentPy.services.modeling_engine import (
    AxonScriptGenerator,
    HaystackTagMapper,
    ModelingEngine,
    PointNameParser,
    TaggingEngine,
)


# ── PointNameParser Tests ──


class TestPointNameParser:
    """Test parsing of various BACnet/Modbus naming conventions."""

    # Tridium / Niagara style
    def test_tridium_ahu_sat(self) -> None:
        parsed = PointNameParser.parse("AHU-01.SAT")
        assert parsed.equip_type == "AHU"
        assert parsed.equip_id == "AHU-01"
        assert "supply_air_temp" in parsed.point_features
        assert parsed.confidence > 0.5

    def test_tridium_ahu_fan_speed(self) -> None:
        parsed = PointNameParser.parse("AHU-01.FanSpd")
        assert parsed.equip_type == "AHU"
        assert "fan_speed" in parsed.point_features

    # Siemens style
    def test_siemens_vav_zone_temp(self) -> None:
        parsed = PointNameParser.parse("B1_FL12_VAV301_ZnTemp")
        assert parsed.equip_type == "VAV"
        assert parsed.equip_id == "VAV301"
        assert "zone_temp" in parsed.point_features

    def test_siemens_ahu_status(self) -> None:
        parsed = PointNameParser.parse("B2_FL01_AHU02_Status")
        assert parsed.equip_type == "AHU"
        assert "status" in parsed.point_features

    # Johnson / Metasys style
    def test_metasys_ahu_sat(self) -> None:
        parsed = PointNameParser.parse("AHU1:SupplyAirTemp")
        assert parsed.equip_type == "AHU"
        assert "supply_air_temp" in parsed.point_features

    def test_metasys_fcu_valve(self) -> None:
        parsed = PointNameParser.parse("FCU-2/VlvPos")
        assert parsed.equip_type == "FCU"
        assert "valve_pos" in parsed.point_features

    # Generic / verbose style
    def test_generic_ahu_supply_air_temp(self) -> None:
        parsed = PointNameParser.parse("AHU-01 Supply Air Temp")
        assert parsed.equip_type == "AHU"
        assert "supply_air_temp" in parsed.point_features

    def test_generic_rat(self) -> None:
        parsed = PointNameParser.parse("AHU-01 RAT")
        assert parsed.equip_type == "AHU"
        assert "return_air_temp" in parsed.point_features

    # Equipment types
    @pytest.mark.parametrize("name,expected_type", [
        ("AHU-01.SAT", "AHU"),
        ("VAV-301.DamperPos", "VAV"),
        ("FCU-2.VlvPos", "FCU"),
        ("CHWP-1.Status", "CHWP"),
        ("CT-1.FanSpd", "CT"),
        ("Boiler-1.Status", "Boiler"),
    ])
    def test_equip_type_detection(self, name: str, expected_type: str) -> None:
        parsed = PointNameParser.parse(name)
        assert parsed.equip_type == expected_type

    # Point feature types
    @pytest.mark.parametrize("name,expected_feature", [
        ("AHU-01.SAT", "supply_air_temp"),
        ("AHU-01.RAT", "return_air_temp"),
        ("AHU-01.DAT", "discharge_air_temp"),
        ("AHU-01.MAT", "mixed_air_temp"),
        ("AHU-01.OAT", "outdoor_air_temp"),
        ("VAV-1.ZnTemp", "zone_temp"),
        ("AHU-01.Status", "status"),
        ("AHU-01.Cmd", "cmd"),
        ("AHU-01.Alarm", "alarm"),
        ("AHU-01.FanSpd", "fan_speed"),
        ("AHU-01.VlvPos", "valve_pos"),
        ("AHU-01.DamperPos", "damper_pos"),
        ("AHU-01.StaticPress", "static_pressure"),
        ("AHU-01.AirFlow", "airflow"),
        ("AHU-01.Humidity", "humidity"),
        ("AHU-01.CO2", "co2"),
        ("AHU-01.kW", "power"),
    ])
    def test_feature_detection(self, name: str, expected_feature: str) -> None:
        parsed = PointNameParser.parse(name)
        assert expected_feature in parsed.point_features

    # Chilled / hot water temps
    def test_chw_supply_temp(self) -> None:
        parsed = PointNameParser.parse("Chiller-1 CHW Supply Temp")
        assert "chw_supply_temp" in parsed.point_features

    def test_hhw_supply_temp(self) -> None:
        parsed = PointNameParser.parse("Boiler-1 HHW Supply Temp")
        assert "hhw_supply_temp" in parsed.point_features

    # Unknown / unparseable
    def test_unknown_name(self) -> None:
        parsed = PointNameParser.parse("XYZ123")
        assert parsed.equip_type == ""
        assert parsed.point_features == ()
        assert parsed.confidence == 0.0

    def test_empty_name(self) -> None:
        parsed = PointNameParser.parse("")
        assert parsed.confidence == 0.0


# ── HaystackTagMapper Tests ──


class TestHaystackTagMapper:
    def test_supply_air_temp_tags(self) -> None:
        parsed = PointNameParser.parse("AHU-01.SAT")
        match = HaystackTagMapper.match(parsed)
        assert match.score > 0
        assert match.tags.get("air") is True
        assert match.tags.get("temp") is True
        assert match.tags.get("sensor") is True
        assert match.tags.get("supply") is True
        assert match.tags.get("point") is True
        assert match.tags.get("kind") == "Number"
        assert match.tags.get("unit") == "°C"

    def test_fan_speed_tags(self) -> None:
        parsed = PointNameParser.parse("AHU-01.FanSpd")
        match = HaystackTagMapper.match(parsed)
        assert match.tags.get("fan") is True
        assert match.tags.get("speed") is True
        assert match.tags.get("unit") == "%"

    def test_status_tags(self) -> None:
        parsed = PointNameParser.parse("AHU-01.Status")
        match = HaystackTagMapper.match(parsed)
        assert match.tags.get("run") is True
        assert match.tags.get("kind") == "Bool"

    def test_equip_type_tag_added(self) -> None:
        parsed = PointNameParser.parse("AHU-01.SAT")
        match = HaystackTagMapper.match(parsed)
        assert match.tags.get("ahu") is True

    def test_vav_equip_tag(self) -> None:
        parsed = PointNameParser.parse("VAV-301.ZnTemp")
        match = HaystackTagMapper.match(parsed)
        assert match.tags.get("vav") is True

    def test_no_features_returns_empty(self) -> None:
        parsed = PointNameParser.parse("XYZ123")
        match = HaystackTagMapper.match(parsed)
        assert match.score == 0.0
        assert match.tags == {}

    def test_template_name_set(self) -> None:
        parsed = PointNameParser.parse("AHU-01.SAT")
        match = HaystackTagMapper.match(parsed)
        assert match.template_name != ""


# ── AxonScriptGenerator Tests ──


class TestAxonScriptGenerator:
    def test_generate_diff_markers_only(self) -> None:
        script = AxonScriptGenerator.generate_diff(
            "@p:123", {"air": True, "temp": True, "sensor": True}
        )
        assert script.startswith("diff(readById(@p:123)")
        assert ".commit" in script
        assert "air" in script
        assert "temp" in script

    def test_generate_diff_with_valued_tags(self) -> None:
        script = AxonScriptGenerator.generate_diff(
            "@p:456", {"kind": "Number", "unit": "°C", "point": True}
        )
        assert 'kind:"Number"' in script
        assert 'unit:"°C"' in script
        assert "point" in script

    def test_generate_diff_empty_tags(self) -> None:
        script = AxonScriptGenerator.generate_diff("@p:789", {})
        assert script == ""

    def test_generate_batch(self) -> None:
        assignments = [
            ("@p:1", {"air": True, "temp": True}),
            ("@p:2", {"fan": True, "speed": True}),
        ]
        script = AxonScriptGenerator.generate_batch(assignments)
        lines = script.strip().split("\n")
        assert len(lines) == 2
        assert "readById(@p:1)" in lines[0]
        assert "readById(@p:2)" in lines[1]

    def test_generate_batch_empty(self) -> None:
        script = AxonScriptGenerator.generate_batch([])
        assert script == ""

    def test_axon_syntax_correctness(self) -> None:
        """Verify the generated AXON script has correct syntax."""
        script = AxonScriptGenerator.generate_diff(
            "@p:test", {"air": True, "temp": True, "kind": "Number", "unit": "°C"}
        )
        # Should follow: diff(readById(@id), {tags}).commit
        assert script.startswith("diff(readById(@p:test), {")
        assert script.endswith("}).commit")


# ── ModelingEngine Integration Tests ──


class TestModelingEngine:
    @pytest.fixture
    def engine(self) -> ModelingEngine:
        return ModelingEngine()

    def test_engine_metadata(self, engine: ModelingEngine) -> None:
        assert engine.name == "modeling"
        assert "tag" in engine.actions
        assert "model" in engine.actions

    def test_tag_action(self, engine: ModelingEngine) -> None:
        result = engine.execute("tag", {"points": [
            {"id": "@p:1", "dis": "AHU-01.SAT"},
        ]})
        assert result.status == "ok"
        assert result.confidence > 0

    def test_model_action(self, engine: ModelingEngine) -> None:
        result = engine.execute("model", {"points": [
            {"id": "@p:1", "dis": "AHU-01.SAT"},
        ]})
        assert result.status == "ok"

    def test_unsupported_action(self, engine: ModelingEngine) -> None:
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("unknown", {})

    def test_empty_points(self, engine: ModelingEngine) -> None:
        result = engine.execute("tag", {})
        assert result.status == "ok"
        assert result.confidence == 0.0

    def test_multiple_points(self, engine: ModelingEngine) -> None:
        result = engine.execute("model", {"points": [
            {"id": "@p:1", "dis": "AHU-01.SAT"},
            {"id": "@p:2", "dis": "AHU-01.RAT"},
            {"id": "@p:3", "dis": "AHU-01.FanSpd"},
            {"id": "@p:4", "dis": "AHU-01.Status"},
            {"id": "@p:5", "dis": "Unknown Point"},
        ]})
        assert result.status == "ok"
        data = result.data
        assert data["total_points"] == 5
        assert data["matched_count"] >= 4
        assert data["axon_batch_script"] != ""

    def test_grid_format_input(self, engine: ModelingEngine) -> None:
        """Accept grid format with rows key."""
        result = engine.execute("tag", {"grid": {"rows": [
            {"id": "@p:1", "dis": "VAV-301.ZnTemp"},
        ]}})
        assert result.status == "ok"
        assert result.data["matched_count"] == 1

    def test_grid_list_format(self, engine: ModelingEngine) -> None:
        """Accept grid as a flat list."""
        result = engine.execute("tag", {"grid": [
            {"id": "@p:1", "dis": "FCU-2.VlvPos"},
        ]})
        assert result.status == "ok"
        assert result.data["matched_count"] == 1


# ── BaAgentService Integration ──


class TestModelingServiceIntegration:
    @pytest.fixture
    def svc(self) -> BaAgentService:
        return BaAgentService()

    def test_handle_tag_action(self, svc: BaAgentService) -> None:
        result = svc.handle(action="tag", payload={"points": [
            {"id": "@p:1", "dis": "AHU-01.SAT"},
        ]})
        assert result["ok"] is True
        assert result["r_status"] == "ok"

    def test_handle_model_action(self, svc: BaAgentService) -> None:
        result = svc.handle(action="model", payload={"points": [
            {"id": "@p:1", "dis": "AHU-01.SAT"},
            {"id": "@p:2", "dis": "VAV-301.ZnTemp"},
        ]})
        assert result["ok"] is True
        assert result["r_status"] == "ok"
        assert result["r_matched_count"] == 2

    def test_ask_tag_instruction(self, svc: BaAgentService) -> None:
        result = svc.ask("给这些点位打标签")
        assert result["ok"] is True
        assert result["action"] == "tag"


# ── Backward Compatibility ──


class TestBackwardCompatibility:
    def test_tagging_engine_alias(self) -> None:
        """TaggingEngine is an alias for ModelingEngine."""
        assert TaggingEngine is ModelingEngine

    def test_import_from_services(self) -> None:
        from baAgentPy.services import TaggingEngine as TE
        engine = TE()
        assert engine.name == "modeling"
        assert "tag" in engine.actions
