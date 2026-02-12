"""Tests for ReportEngine — operation brief generation.

Acceptance: aggregated building data → structured operation reports with sections.
"""

from __future__ import annotations

from typing import Any

import pytest

from baAgentPy.main import BaAgentService
from baAgentPy.services.report_engine import (
    AlarmSummarySection,
    EnergySummarySection,
    EquipmentStatusSection,
    OperationReport,
    ReportEngine,
    ReportSection,
    ReportType,
    SectionType,
    SensorHealthSection,
    TimeRange,
    _build_alarm_section,
    _build_energy_section,
    _build_equipment_section,
    _build_executive_summary,
    _build_recommendations,
    _build_sensor_section,
    _extract_alarm_data,
    _extract_energy_data,
    _extract_equipment_data,
    _extract_sensor_data,
    _parse_time_range,
)


@pytest.fixture
def engine() -> ReportEngine:
    return ReportEngine()


# ── Simulated data helpers ──


def _make_alarm_data() -> list[dict[str, Any]]:
    return [
        {"id": "a1", "severity": "critical", "resolved": False, "point_id": "p1"},
        {"id": "a2", "severity": "high", "resolved": True, "point_id": "p2"},
        {"id": "a3", "severity": "medium", "resolved": False, "point_id": "p1"},
        {"id": "a4", "severity": "low", "resolved": True, "point_id": "p3"},
        {"id": "a5", "severity": "critical", "resolved": False, "point_id": "p1"},
    ]


def _make_energy_data() -> list[dict[str, Any]]:
    return [
        {"id": "e1", "curVal": 50.0, "rated_power": 100.0},
        {"id": "e2", "curVal": 30.0, "rated_power": 100.0},
        {"id": "e3", "curVal": 95.0, "rated_power": 100.0},
    ]


def _make_sensor_data() -> list[dict[str, Any]]:
    return [
        {"id": "s1", "health_score": 95, "status": "healthy"},
        {"id": "s2", "health_score": 70, "status": "warning"},
        {"id": "s3", "health_score": 30, "status": "fault"},
        {"id": "s4", "health_score": 0, "status": "offline"},
    ]


def _make_equipment_data() -> list[dict[str, Any]]:
    return [
        {"id": "eq1", "dis": "AHU-1", "status": "running"},
        {"id": "eq2", "dis": "AHU-2", "status": "running"},
        {"id": "eq3", "dis": "Chiller-1", "status": "fault"},
        {"id": "eq4", "dis": "Pump-1", "status": "stopped"},
    ]


def _make_full_payload() -> dict[str, Any]:
    return {
        "report_type": "daily_brief",
        "time_range": {"start": "2025-01-01", "end": "2025-01-02", "label": "Jan 1"},
        "alarms": _make_alarm_data(),
        "energy": _make_energy_data(),
        "sensors": _make_sensor_data(),
        "equipment": _make_equipment_data(),
    }


# ── Data Models ──


class TestDataModels:
    def test_report_type_values(self) -> None:
        assert ReportType.DAILY_BRIEF == "daily_brief"
        assert ReportType.ALARM_SUMMARY == "alarm_summary"
        assert ReportType.ENERGY_SUMMARY == "energy_summary"
        assert ReportType.MAINTENANCE == "maintenance"

    def test_section_type_values(self) -> None:
        assert SectionType.ALARMS == "alarms"
        assert SectionType.ENERGY == "energy"
        assert SectionType.SENSORS == "sensors"
        assert SectionType.EQUIPMENT == "equipment"
        assert SectionType.RECOMMENDATIONS == "recommendations"

    def test_time_range_defaults(self) -> None:
        tr = TimeRange()
        assert tr.start == ""
        assert tr.end == ""
        assert tr.label == "past 24h"

    def test_alarm_summary_section_defaults(self) -> None:
        s = AlarmSummarySection()
        assert s.total_count == 0
        assert s.critical_count == 0
        assert s.top_alarm_points == []

    def test_energy_summary_section_defaults(self) -> None:
        s = EnergySummarySection()
        assert s.total_consumption_kwh == 0.0
        assert s.load_trend == "stable"

    def test_sensor_health_section_defaults(self) -> None:
        s = SensorHealthSection()
        assert s.total_count == 0
        assert s.avg_score == 0.0

    def test_equipment_status_section_defaults(self) -> None:
        s = EquipmentStatusSection()
        assert s.total_count == 0
        assert s.equipment_summary == []

    def test_operation_report_defaults(self) -> None:
        r = OperationReport(report_type=ReportType.DAILY_BRIEF, title="Test")
        assert r.sections == []
        assert r.recommendations == []
        assert r.executive_summary == ""


# ── Helper Functions ──


class TestHelperFunctions:
    def test_parse_time_range_with_data(self) -> None:
        tr = _parse_time_range({"time_range": {"start": "a", "end": "b", "label": "test"}})
        assert tr.start == "a"
        assert tr.end == "b"
        assert tr.label == "test"

    def test_parse_time_range_missing(self) -> None:
        tr = _parse_time_range({})
        assert tr.label == "past 24h"

    def test_parse_time_range_non_dict(self) -> None:
        tr = _parse_time_range({"time_range": "invalid"})
        assert tr.label == "past 24h"

    def test_extract_alarm_data(self) -> None:
        result = _extract_alarm_data({"alarms": [{"id": "1"}]})
        assert len(result) == 1

    def test_extract_alarm_data_missing(self) -> None:
        assert _extract_alarm_data({}) == []

    def test_extract_alarm_data_non_list(self) -> None:
        assert _extract_alarm_data({"alarms": "bad"}) == []

    def test_extract_energy_data(self) -> None:
        result = _extract_energy_data({"energy": [{"id": "1"}]})
        assert len(result) == 1

    def test_extract_energy_data_missing(self) -> None:
        assert _extract_energy_data({}) == []

    def test_extract_sensor_data(self) -> None:
        result = _extract_sensor_data({"sensors": [{"id": "1"}]})
        assert len(result) == 1

    def test_extract_sensor_data_missing(self) -> None:
        assert _extract_sensor_data({}) == []

    def test_extract_equipment_data(self) -> None:
        result = _extract_equipment_data({"equipment": [{"id": "1"}]})
        assert len(result) == 1

    def test_extract_equipment_data_missing(self) -> None:
        assert _extract_equipment_data({}) == []

    def test_extract_energy_data_non_list(self) -> None:
        assert _extract_energy_data({"energy": 123}) == []

    def test_extract_sensor_data_non_list(self) -> None:
        assert _extract_sensor_data({"sensors": None}) == []


# ── Alarm Section ──


class TestAlarmSection:
    def test_severity_counts(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        assert section.content["critical_count"] == 2
        assert section.content["high_count"] == 1
        assert section.content["medium_count"] == 1
        assert section.content["low_count"] == 1
        assert section.content["total_count"] == 5

    def test_unresolved_count(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        assert section.content["unresolved_count"] == 3

    def test_top_alarm_points(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        top = section.content["top_alarm_points"]
        assert top[0] == "p1"  # 3 alarms on p1

    def test_highlights_critical(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        assert any("critical" in h for h in section.highlights)

    def test_empty_alarm_data(self) -> None:
        section = _build_alarm_section([])
        assert section.content["total_count"] == 0
        assert section.highlights == []

    def test_unknown_severity_defaults_to_medium(self) -> None:
        section = _build_alarm_section([{"id": "x", "severity": "unknown_sev"}])
        assert section.content["medium_count"] == 1


# ── Energy Section ──


class TestEnergySection:
    def test_consumption_total(self) -> None:
        section = _build_energy_section(_make_energy_data())
        assert section.content["total_consumption_kwh"] == 175.0

    def test_load_percentages(self) -> None:
        section = _build_energy_section(_make_energy_data())
        assert section.content["avg_load_pct"] > 0
        assert section.content["peak_load_pct"] == 95.0

    def test_optimization_opportunities(self) -> None:
        section = _build_energy_section(_make_energy_data())
        assert section.content["optimization_opportunities"] == 1  # e2 at 30%

    def test_high_peak_highlight(self) -> None:
        section = _build_energy_section(_make_energy_data())
        assert any("near capacity" in h for h in section.highlights)

    def test_empty_energy_data(self) -> None:
        section = _build_energy_section([])
        assert section.content["total_consumption_kwh"] == 0.0
        assert section.content["avg_load_pct"] == 0.0

    def test_trend_high(self) -> None:
        data = [{"curVal": 90.0, "rated_power": 100.0}]
        section = _build_energy_section(data)
        assert section.content["load_trend"] == "high"

    def test_trend_low(self) -> None:
        data = [{"curVal": 20.0, "rated_power": 100.0}]
        section = _build_energy_section(data)
        assert section.content["load_trend"] == "low"


# ── Sensor Section ──


class TestSensorSection:
    def test_status_counts(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        assert section.content["healthy_count"] == 1
        assert section.content["warning_count"] == 1
        assert section.content["fault_count"] == 1
        assert section.content["offline_count"] == 1

    def test_avg_score(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        assert section.content["avg_score"] == 48.8  # (95+70+30+0)/4

    def test_flagged_sensors(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        flagged = section.content["flagged_sensors"]
        assert "s2" in flagged  # warning
        assert "s3" in flagged  # fault
        assert "s4" in flagged  # offline

    def test_highlights_fault(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        assert any("fault" in h for h in section.highlights)

    def test_empty_sensor_data(self) -> None:
        section = _build_sensor_section([])
        assert section.content["total_count"] == 0

    def test_unknown_status_defaults_to_healthy(self) -> None:
        section = _build_sensor_section([{"id": "x", "status": "bizarre"}])
        assert section.content["healthy_count"] == 1


# ── Equipment Section ──


class TestEquipmentSection:
    def test_status_counts(self) -> None:
        section = _build_equipment_section(_make_equipment_data())
        assert section.content["running_count"] == 2
        assert section.content["stopped_count"] == 1
        assert section.content["fault_count"] == 1

    def test_highlights_fault(self) -> None:
        section = _build_equipment_section(_make_equipment_data())
        assert any("fault" in h for h in section.highlights)

    def test_empty_equipment_data(self) -> None:
        section = _build_equipment_section([])
        assert section.content["total_count"] == 0

    def test_equipment_summary_contents(self) -> None:
        section = _build_equipment_section(_make_equipment_data())
        summary = section.content["equipment_summary"]
        assert len(summary) == 4
        assert summary[0]["dis"] == "AHU-1"


# ── Recommendations ──


class TestRecommendations:
    def test_critical_alarms_generate_urgent(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        recs = _build_recommendations([section])
        assert any("URGENT" in r for r in recs)

    def test_offline_sensors_generate_restore(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        recs = _build_recommendations([section])
        assert any("offline" in r.lower() for r in recs)

    def test_energy_opt_opportunity(self) -> None:
        section = _build_energy_section(_make_energy_data())
        recs = _build_recommendations([section])
        assert any("optimization" in r.lower() for r in recs)

    def test_empty_sections_no_recommendations(self) -> None:
        section = _build_alarm_section([])
        recs = _build_recommendations([section])
        assert recs == []

    def test_equipment_fault_recommendation(self) -> None:
        section = _build_equipment_section(_make_equipment_data())
        recs = _build_recommendations([section])
        assert any("maintenance" in r.lower() for r in recs)


# ── Executive Summary ──


class TestExecutiveSummary:
    def test_daily_brief_summary(self) -> None:
        alarm_sec = _build_alarm_section(_make_alarm_data())
        energy_sec = _build_energy_section(_make_energy_data())
        summary = _build_executive_summary(ReportType.DAILY_BRIEF, [alarm_sec, energy_sec])
        assert "Daily Brief" in summary
        assert "alarms" in summary.lower()

    def test_empty_sections_summary(self) -> None:
        summary = _build_executive_summary(ReportType.DAILY_BRIEF, [])
        assert "no data" in summary.lower()

    def test_alarm_summary_with_critical(self) -> None:
        section = _build_alarm_section(_make_alarm_data())
        summary = _build_executive_summary(ReportType.ALARM_SUMMARY, [section])
        assert "critical" in summary.lower()

    def test_sensor_issues_in_summary(self) -> None:
        section = _build_sensor_section(_make_sensor_data())
        summary = _build_executive_summary(ReportType.MAINTENANCE, [section])
        assert "sensor issue" in summary.lower()

    def test_equipment_fault_in_summary(self) -> None:
        section = _build_equipment_section(_make_equipment_data())
        summary = _build_executive_summary(ReportType.MAINTENANCE, [section])
        assert "fault" in summary.lower()


# ── Report Scenarios ──


class TestReportScenarios:
    def test_daily_brief_all_data(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert result.status == "ok"
        data = result.data
        assert data["report_type"] == "daily_brief"
        assert len(data["sections"]) == 4

    def test_daily_brief_title(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert "Daily Operation Brief" in result.data["title"]
        assert "Jan 1" in result.data["title"]

    def test_alarm_only_report(self, engine: ReportEngine) -> None:
        payload = {"report_type": "alarm_summary", "alarms": _make_alarm_data()}
        result = engine.execute("report", payload)
        assert result.status == "ok"
        assert len(result.data["sections"]) == 1
        assert result.data["sections"][0]["section_type"] == "alarms"

    def test_energy_only_report(self, engine: ReportEngine) -> None:
        payload = {"report_type": "energy_summary", "energy": _make_energy_data()}
        result = engine.execute("report", payload)
        assert result.status == "ok"
        assert len(result.data["sections"]) == 1
        assert result.data["sections"][0]["section_type"] == "energy"

    def test_maintenance_report(self, engine: ReportEngine) -> None:
        payload = {
            "report_type": "maintenance",
            "sensors": _make_sensor_data(),
            "equipment": _make_equipment_data(),
        }
        result = engine.execute("report", payload)
        assert result.status == "ok"
        assert len(result.data["sections"]) == 2

    def test_empty_payload(self, engine: ReportEngine) -> None:
        result = engine.execute("report", {})
        assert result.status == "ok"
        assert result.data["report_type"] == "daily_brief"

    def test_partial_data_daily_brief(self, engine: ReportEngine) -> None:
        payload = {"alarms": _make_alarm_data()}
        result = engine.execute("report", payload)
        assert result.status == "ok"
        assert len(result.data["sections"]) == 4  # All sections created, most empty

    def test_unknown_report_type_defaults(self, engine: ReportEngine) -> None:
        payload = {"report_type": "nonexistent", "alarms": _make_alarm_data()}
        result = engine.execute("report", payload)
        assert result.data["report_type"] == "daily_brief"

    def test_recommendations_present(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert len(result.data["recommendations"]) > 0

    def test_executive_summary_present(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert len(result.data["executive_summary"]) > 0

    def test_time_range_in_report(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert result.data["time_range"]["label"] == "Jan 1"

    def test_message_equals_executive_summary(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert result.message == result.data["executive_summary"]


# ── Confidence Scoring ──


class TestConfidenceScoring:
    def test_full_data_high_confidence(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert result.confidence is not None
        assert result.confidence >= 0.9

    def test_no_data_zero_confidence(self, engine: ReportEngine) -> None:
        result = engine.execute("report", {})
        assert result.confidence == 0.0

    def test_partial_data_medium_confidence(self, engine: ReportEngine) -> None:
        payload = {
            "alarms": _make_alarm_data(),
            "energy": _make_energy_data(),
        }
        result = engine.execute("report", payload)
        assert result.confidence is not None
        assert 0.0 < result.confidence < 0.95

    def test_confidence_capped(self, engine: ReportEngine) -> None:
        result = engine.execute("report", _make_full_payload())
        assert result.confidence is not None
        assert result.confidence <= 0.95

    def test_single_section_report_confidence(self, engine: ReportEngine) -> None:
        payload = {"report_type": "alarm_summary", "alarms": _make_alarm_data()}
        result = engine.execute("report", payload)
        assert result.confidence is not None
        assert result.confidence == 0.95  # 1/1 sections populated


# ── Engine Interface ──


class TestEngineInterface:
    def test_name(self, engine: ReportEngine) -> None:
        assert engine.name == "report"

    def test_description(self, engine: ReportEngine) -> None:
        assert len(engine.description) > 0

    def test_actions(self, engine: ReportEngine) -> None:
        assert engine.actions == {"report"}

    def test_can_handle(self, engine: ReportEngine) -> None:
        assert engine.can_handle("report") is True
        assert engine.can_handle("diagnose") is False

    def test_unsupported_action_raises(self, engine: ReportEngine) -> None:
        with pytest.raises(ValueError, match="does not support"):
            engine.execute("diagnose", {})


# ── Integration via BaAgentService ──


class TestEngineIntegration:
    def test_handle_report(self) -> None:
        svc = BaAgentService()
        result = svc.handle(action="report", payload=_make_full_payload())
        assert result["ok"] is True
        assert result["action"] == "report"
        assert result["r_status"] == "ok"

    def test_handle_report_empty(self) -> None:
        svc = BaAgentService()
        result = svc.handle(action="report")
        assert result["ok"] is True
        assert result["r_status"] == "ok"

    def test_ask_report_chinese(self) -> None:
        svc = BaAgentService()
        result = svc.ask("生成今天的运维日报")
        assert result["ok"] is True
        assert result["action"] == "report"

    def test_ask_report_english(self) -> None:
        svc = BaAgentService()
        result = svc.ask("generate daily operation report")
        assert result["ok"] is True
        assert result["action"] == "report"
