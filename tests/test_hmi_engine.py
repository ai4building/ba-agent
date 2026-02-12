"""Tests for HmiEngine — HMI auto-generation from device topology."""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.services.hmi_engine import (
    EquipType,
    HmiEngine,
    HmiLayout,
    HmiPage,
    Widget,
    WidgetBinding,
    WidgetType,
    _classify_equip,
    _classify_point_widget,
    _generate_page,
    _short_label,
)


# ── Helpers ──


def _make_point(
    point_id: str = "@p:1",
    dis: str = "Supply Air Temp",
    cur_val: Any = 22.5,
) -> dict[str, Any]:
    return {"id": point_id, "dis": dis, "curVal": cur_val}


def _make_equip(
    equip_id: str = "@e:ahu-1",
    equip_name: str = "AHU-1",
    points: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if points is None:
        points = [
            _make_point("@p:1", "AHU-1 Supply Air Temp", 22.5),
            _make_point("@p:2", "AHU-1 Return Air Temp", 24.0),
            _make_point("@p:3", "AHU-1 Fan Speed", 75.0),
            _make_point("@p:4", "AHU-1 Cooling Valve", 60.0),
            _make_point("@p:5", "AHU-1 Fan Status", True),
        ]
    return {"equip_id": equip_id, "equip_name": equip_name, "points": points}


@pytest.fixture
def engine() -> HmiEngine:
    return HmiEngine()


@pytest.fixture
def ahu_payload() -> dict[str, Any]:
    return {"equipment": [_make_equip()]}


@pytest.fixture
def multi_equip_payload() -> dict[str, Any]:
    return {"equipment": [
        _make_equip("@e:ahu-1", "AHU-1"),
        _make_equip("@e:vav-1", "VAV-101", points=[
            _make_point("@p:10", "VAV-101 Damper Position", 45.0),
            _make_point("@p:11", "VAV-101 Airflow", 800),
            _make_point("@p:12", "VAV-101 Zone Temp", 23.0),
        ]),
    ]}


# ── Equipment Classification ──


class TestEquipClassification:
    @pytest.mark.parametrize("name,expected", [
        ("AHU-1", EquipType.AHU),
        ("Air Handling Unit 3", EquipType.AHU),
        ("空调机组-1", EquipType.AHU),
        ("VAV-101", EquipType.VAV),
        ("变风量箱-5", EquipType.VAV),
        ("Chiller-1", EquipType.CHILLER),
        ("冷水机-2", EquipType.CHILLER),
        ("Boiler-1", EquipType.BOILER),
        ("锅炉-1", EquipType.BOILER),
        ("FCU-201", EquipType.FCU),
        ("Fan Coil Unit 3", EquipType.FCU),
        ("风机盘管-1", EquipType.FCU),
        ("CHW Pump-1", EquipType.PUMP),
        ("水泵-3", EquipType.PUMP),
        ("Cooling Tower 1", EquipType.COOLING_TOWER),
        ("冷却塔-1", EquipType.COOLING_TOWER),
    ])
    def test_classify_by_name(self, name: str, expected: EquipType) -> None:
        assert _classify_equip(name, []) == expected

    def test_classify_generic_fallback(self) -> None:
        assert _classify_equip("Unit-X", []) == EquipType.GENERIC

    def test_classify_by_point_names_ahu(self) -> None:
        points = [
            {"dis": "Supply Air Temp"},
            {"dis": "Return Air Temp"},
        ]
        assert _classify_equip("Equipment-1", points) == EquipType.AHU

    def test_classify_by_point_names_vav(self) -> None:
        points = [
            {"dis": "Zone Damper Position"},
            {"dis": "Zone Airflow"},
        ]
        assert _classify_equip("Equipment-2", points) == EquipType.VAV

    def test_classify_by_point_names_chiller(self) -> None:
        points = [
            {"dis": "CHW Supply Temp"},
            {"dis": "CHW Return Temp"},
        ]
        assert _classify_equip("Equipment-3", points) == EquipType.CHILLER

    def test_classify_by_condenser_point(self) -> None:
        points = [{"dis": "Condenser Water Temp"}]
        assert _classify_equip("Equipment-4", points) == EquipType.CHILLER

    def test_classify_by_fan_speed_point(self) -> None:
        points = [{"dis": "Fan Speed"}]
        assert _classify_equip("Equipment-5", points) == EquipType.AHU


# ── Point-to-Widget Mapping ──


class TestPointWidgetMapping:
    @pytest.mark.parametrize("name,expected_type", [
        ("Supply Air Temp", WidgetType.GAUGE),
        ("Zone 温度", WidgetType.GAUGE),
        ("Temp Setpoint", WidgetType.SETPOINT),
        ("Zone Temp SP", WidgetType.SETPOINT),
        ("温度设定值", WidgetType.SETPOINT),
        ("Cooling Valve", WidgetType.VALVE_GRAPHIC),
        ("HW Vlv Position", WidgetType.VALVE_GRAPHIC),
        ("热水阀", WidgetType.VALVE_GRAPHIC),
        ("Supply Fan Speed", WidgetType.FAN_GRAPHIC),
        ("CHW Pump", WidgetType.FAN_GRAPHIC),
        ("VFD Output", WidgetType.FAN_GRAPHIC),
        ("风机输出", WidgetType.FAN_GRAPHIC),
        ("OA Damper", WidgetType.VALVE_GRAPHIC),
        ("风阀位置", WidgetType.VALVE_GRAPHIC),
        ("Duct Pressure", WidgetType.GAUGE),
        ("Supply Airflow", WidgetType.GAUGE),
        ("Zone Humidity", WidgetType.GAUGE),
        ("Room CO2", WidgetType.GAUGE),
        ("Total Power", WidgetType.GAUGE),
        ("Fan Status", WidgetType.STATUS),
        ("Enable Command", WidgetType.STATUS),
        ("Run Status", WidgetType.STATUS),
        ("运行状态", WidgetType.STATUS),
    ])
    def test_classify_by_name(self, name: str, expected_type: WidgetType) -> None:
        widget_type, _ = _classify_point_widget(name, 0)
        assert widget_type == expected_type

    def test_numeric_value_defaults_to_gauge(self) -> None:
        widget_type, config = _classify_point_widget("Unknown Point", 42.0)
        assert widget_type == WidgetType.GAUGE
        assert config.get("unit") == ""

    def test_non_numeric_defaults_to_label(self) -> None:
        widget_type, _ = _classify_point_widget("Unknown Point", "some text")
        assert widget_type == WidgetType.LABEL

    def test_none_value_defaults_to_label(self) -> None:
        widget_type, _ = _classify_point_widget("Unknown Point", None)
        assert widget_type == WidgetType.LABEL

    def test_temp_gauge_has_unit(self) -> None:
        _, config = _classify_point_widget("Supply Air Temp", 22.0)
        assert config["unit"] == "°C"

    def test_setpoint_has_range(self) -> None:
        _, config = _classify_point_widget("Temp Setpoint", 22.0)
        assert config["min"] == 5
        assert config["max"] == 35

    def test_pressure_unit(self) -> None:
        _, config = _classify_point_widget("Duct Pressure", 250)
        assert config["unit"] == "Pa"

    def test_flow_unit(self) -> None:
        _, config = _classify_point_widget("Supply Airflow CFM", 1200)
        assert config["unit"] == "CFM"

    def test_humidity_unit(self) -> None:
        _, config = _classify_point_widget("Zone RH", 55)
        assert config["unit"] == "%RH"

    def test_co2_unit(self) -> None:
        _, config = _classify_point_widget("Room CO2 Level", 800)
        assert config["unit"] == "ppm"

    def test_power_unit(self) -> None:
        _, config = _classify_point_widget("Total Power kW", 120)
        assert config["unit"] == "kW"


# ── Short Label ──


class TestShortLabel:
    def test_removes_equip_prefix(self) -> None:
        assert _short_label("AHU-1 Supply Air Temp", "AHU-1") == "Supply Air Temp"

    def test_removes_partial_prefix(self) -> None:
        assert _short_label("AHU Supply Air Temp", "AHU-1") == "Supply Air Temp"

    def test_no_prefix_match(self) -> None:
        assert _short_label("Zone Temp", "AHU-1") == "Zone Temp"

    def test_empty_after_strip_returns_original(self) -> None:
        assert _short_label("AHU-1", "AHU-1") == "AHU-1"


# ── Page Generation ──


class TestPageGeneration:
    def test_page_has_title_widget(self) -> None:
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, [], 0)
        title_widgets = [w for w in page.widgets if w.config.get("style") == "header"]
        assert len(title_widgets) == 1
        assert title_widgets[0].label == "AHU-1"

    def test_page_has_alarm_badge(self) -> None:
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, [], 0)
        alarm_widgets = [w for w in page.widgets if w.widget_type == WidgetType.ALARM_BADGE]
        assert len(alarm_widgets) == 1

    def test_page_generates_point_widgets(self) -> None:
        points = [
            _make_point("@p:1", "Supply Air Temp", 22.5),
            _make_point("@p:2", "Fan Speed", 75.0),
        ]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        # Title + alarm + 2 point widgets + 1 trend (for temp) = 5
        assert len(page.widgets) >= 4

    def test_point_widgets_have_bindings(self) -> None:
        points = [_make_point("@p:1", "Supply Air Temp", 22.5)]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        bound = [w for w in page.widgets if w.binding is not None]
        assert len(bound) >= 1
        assert bound[0].binding.point_id == "@p:1"

    def test_setpoint_widget_is_writable(self) -> None:
        points = [_make_point("@p:1", "Temp Setpoint", 22.0)]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        sp_widgets = [w for w in page.widgets if w.widget_type == WidgetType.SETPOINT]
        assert len(sp_widgets) == 1
        assert sp_widgets[0].binding is not None
        assert sp_widgets[0].binding.writable is True

    def test_temp_points_generate_trend_widget(self) -> None:
        points = [
            _make_point("@p:1", "Supply Air Temp", 22.5),
            _make_point("@p:2", "Return Air Temp", 24.0),
        ]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        trend_widgets = [w for w in page.widgets if w.widget_type == WidgetType.TREND]
        assert len(trend_widgets) == 1
        assert len(trend_widgets[0].config["traces"]) == 2

    def test_no_temp_points_no_trend(self) -> None:
        points = [
            _make_point("@p:1", "Fan Speed", 75.0),
            _make_point("@p:2", "Fan Status", True),
        ]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        trend_widgets = [w for w in page.widgets if w.widget_type == WidgetType.TREND]
        assert len(trend_widgets) == 0

    def test_max_4_trend_traces(self) -> None:
        points = [_make_point(f"@p:{i}", f"Temp Sensor {i}", 20 + i) for i in range(6)]
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, points, 0)
        trend_widgets = [w for w in page.widgets if w.widget_type == WidgetType.TREND]
        assert len(trend_widgets) == 1
        assert len(trend_widgets[0].config["traces"]) == 4

    def test_grid_position_wraps(self) -> None:
        points = [_make_point(f"@p:{i}", f"Sensor {i}", float(i)) for i in range(8)]
        page = _generate_page("@e:1", "Test", EquipType.GENERIC, points, 0)
        # All widgets should have valid positions
        for w in page.widgets:
            assert w.x >= 0
            assert w.x < page.grid_columns
            assert w.y >= 0

    def test_page_id_uses_index(self) -> None:
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, [], 5)
        assert page.page_id == "page_5"

    def test_empty_points_still_has_header_and_alarm(self) -> None:
        page = _generate_page("@e:1", "AHU-1", EquipType.AHU, [], 0)
        assert len(page.widgets) == 2  # Title + alarm


# ── Equipment Extraction ──


class TestEquipmentExtraction:
    def test_extract_from_equipment_list(self) -> None:
        payload = {"equipment": [_make_equip()]}
        result = HmiEngine._extract_equipment(payload)
        assert len(result) == 1
        assert result[0]["equip_id"] == "@e:ahu-1"

    def test_extract_from_grid_dict(self) -> None:
        payload = {
            "grid": {
                "rows": [
                    {"id": "@p:1", "dis": "Temp", "equipRef": "@e:ahu-1"},
                    {"id": "@p:2", "dis": "Fan", "equipRef": "@e:ahu-1"},
                    {"id": "@p:3", "dis": "Valve", "equipRef": "@e:vav-1"},
                ],
            },
        }
        result = HmiEngine._extract_equipment(payload)
        assert len(result) == 2

    def test_extract_from_grid_list(self) -> None:
        payload = {
            "grid": [
                {"id": "@p:1", "dis": "Temp", "equipRef": "@e:ahu-1"},
                {"id": "@p:2", "dis": "Fan", "equipRef": "@e:ahu-1"},
            ],
        }
        result = HmiEngine._extract_equipment(payload)
        assert len(result) == 1
        assert len(result[0]["points"]) == 2

    def test_extract_empty_payload(self) -> None:
        assert HmiEngine._extract_equipment({}) == []

    def test_extract_empty_equipment_list(self) -> None:
        assert HmiEngine._extract_equipment({"equipment": []}) == []

    def test_extract_grid_groups_by_equip_ref(self) -> None:
        payload = {
            "grid": [
                {"id": "@p:1", "equipRef": "A"},
                {"id": "@p:2", "equipRef": "B"},
                {"id": "@p:3", "equipRef": "A"},
            ],
        }
        result = HmiEngine._extract_equipment(payload)
        groups = {r["equip_id"]: r for r in result}
        assert len(groups["A"]["points"]) == 2
        assert len(groups["B"]["points"]) == 1

    def test_extract_grid_default_equip_ref(self) -> None:
        payload = {"grid": [{"id": "@p:1", "dis": "Temp"}]}
        result = HmiEngine._extract_equipment(payload)
        assert len(result) == 1
        assert result[0]["equip_id"] == "default"


# ── Confidence Scoring ──


class TestConfidenceScoring:
    def test_empty_equipment_returns_zero(self) -> None:
        assert HmiEngine._compute_confidence([], 0) == 0.0

    def test_named_points_increase_confidence(self) -> None:
        no_names = [{"points": [{"id": "@p:1"}, {"id": "@p:2"}]}]
        with_names = [{"points": [{"id": "@p:1", "dis": "Temp"}, {"id": "@p:2", "dis": "Fan"}]}]
        c_no = HmiEngine._compute_confidence(no_names, 4)
        c_yes = HmiEngine._compute_confidence(with_names, 4)
        assert c_yes > c_no

    def test_more_widgets_increase_confidence(self) -> None:
        equip = [{"points": [{"id": "@p:1", "dis": "Temp"}]}]
        c_few = HmiEngine._compute_confidence(equip, 2)
        c_many = HmiEngine._compute_confidence(equip, 20)
        assert c_many > c_few

    def test_confidence_capped_at_095(self) -> None:
        equip = [{"points": [{"id": f"@p:{i}", "dis": f"Point {i}"} for i in range(100)]}]
        c = HmiEngine._compute_confidence(equip, 100)
        assert c <= 0.95

    def test_base_confidence_is_at_least_05(self) -> None:
        equip = [{"points": [{"id": "@p:1"}]}]
        c = HmiEngine._compute_confidence(equip, 1)
        assert c >= 0.5


# ── Full Engine Scenarios ──


class TestHmiEngineScenarios:
    def test_single_ahu(self, engine: HmiEngine) -> None:
        payload = {"equipment": [_make_equip()]}
        result = engine.execute("hmi", payload)
        assert result.status == "ok"
        data = result.data
        assert data["total_pages"] == 1
        assert data["total_widgets"] > 0
        assert len(data["pages"]) == 1
        assert data["pages"][0]["equip_type"] == "ahu"

    def test_multi_equipment(self, engine: HmiEngine, multi_equip_payload: dict) -> None:
        result = engine.execute("hmi", multi_equip_payload)
        assert result.status == "ok"
        data = result.data
        assert data["total_pages"] == 2
        assert len(data["navigation"]) == 2
        types = {n["equip_type"] for n in data["navigation"]}
        assert "ahu" in types
        assert "vav" in types

    def test_no_equipment_data(self, engine: HmiEngine) -> None:
        result = engine.execute("hmi", {})
        assert result.status == "ok"
        assert result.confidence == 0.0
        assert result.data["total_pages"] == 0
        assert "No equipment" in result.message

    def test_grid_based_input(self, engine: HmiEngine) -> None:
        payload = {
            "grid": [
                {"id": "@p:1", "dis": "AHU-1 Supply Air Temp", "curVal": 22.5, "equipRef": "AHU-1"},
                {"id": "@p:2", "dis": "AHU-1 Fan Speed", "curVal": 75, "equipRef": "AHU-1"},
            ],
        }
        result = engine.execute("hmi", payload)
        assert result.status == "ok"
        assert result.data["total_pages"] == 1

    def test_chiller_classification(self, engine: HmiEngine) -> None:
        payload = {"equipment": [_make_equip("@e:ch-1", "Chiller-1", [
            _make_point("@p:1", "CHW Supply Temp", 7.0),
            _make_point("@p:2", "Condenser Water Temp", 32.0),
            _make_point("@p:3", "Chiller Power", 250.0),
        ])]}
        result = engine.execute("hmi", payload)
        assert result.data["pages"][0]["equip_type"] == "chiller"

    def test_chinese_equipment_name(self, engine: HmiEngine) -> None:
        payload = {"equipment": [_make_equip("@e:1", "空调机组-1", [
            _make_point("@p:1", "送风温度", 22.0),
            _make_point("@p:2", "风机状态", True),
        ])]}
        result = engine.execute("hmi", payload)
        assert result.data["pages"][0]["equip_type"] == "ahu"
        assert result.data["total_widgets"] > 0

    def test_equipment_without_name_uses_id(self, engine: HmiEngine) -> None:
        payload = {"equipment": [{"equip_id": "@e:mystery", "points": []}]}
        result = engine.execute("hmi", payload)
        assert result.status == "ok"
        assert result.data["pages"][0]["title"] == "@e:mystery"

    def test_equipment_without_id_or_name(self, engine: HmiEngine) -> None:
        payload = {"equipment": [{"points": []}]}
        result = engine.execute("hmi", payload)
        assert result.status == "ok"
        assert "Equipment-1" in result.data["pages"][0]["title"]

    def test_navigation_structure(self, engine: HmiEngine, multi_equip_payload: dict) -> None:
        result = engine.execute("hmi", multi_equip_payload)
        nav = result.data["navigation"]
        assert len(nav) == 2
        assert all("page_id" in n for n in nav)
        assert all("title" in n for n in nav)
        assert all("equip_type" in n for n in nav)

    def test_summary_message(self, engine: HmiEngine, ahu_payload: dict) -> None:
        result = engine.execute("hmi", ahu_payload)
        assert "page(s)" in result.message
        assert "widget(s)" in result.message

    def test_confidence_positive(self, engine: HmiEngine, ahu_payload: dict) -> None:
        result = engine.execute("hmi", ahu_payload)
        assert result.confidence > 0.5


# ── Engine Interface ──


class TestHmiEngineInterface:
    def test_name(self, engine: HmiEngine) -> None:
        assert engine.name == "hmi"

    def test_description(self, engine: HmiEngine) -> None:
        assert len(engine.description) > 0

    def test_actions(self, engine: HmiEngine) -> None:
        assert "hmi" in engine.actions

    def test_can_handle(self, engine: HmiEngine) -> None:
        assert engine.can_handle("hmi") is True
        assert engine.can_handle("diagnose") is False

    def test_unsupported_action_raises(self, engine: HmiEngine) -> None:
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("diagnose", {})


# ── Data Model Validation ──


class TestDataModels:
    def test_widget_binding_defaults(self) -> None:
        b = WidgetBinding(point_id="@p:1")
        assert b.point_name == ""
        assert b.property == "curVal"
        assert b.writable is False

    def test_hmi_page_defaults(self) -> None:
        p = HmiPage(page_id="p1", title="Test")
        assert p.equip_id == ""
        assert p.equip_type == EquipType.GENERIC
        assert p.widgets == []
        assert p.grid_columns == 4
        assert p.grid_rows == 6

    def test_hmi_layout_defaults(self) -> None:
        layout = HmiLayout()
        assert layout.pages == []
        assert layout.total_widgets == 0
        assert layout.total_pages == 0
        assert layout.summary == ""

    def test_equip_type_values(self) -> None:
        assert EquipType.AHU.value == "ahu"
        assert EquipType.GENERIC.value == "generic"

    def test_widget_type_values(self) -> None:
        assert WidgetType.GAUGE.value == "gauge"
        assert WidgetType.TREND.value == "trend"
        assert WidgetType.SETPOINT.value == "setpoint"
