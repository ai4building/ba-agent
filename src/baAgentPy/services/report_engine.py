"""Automated operation report generation.

Handles:
    - report: generate operation briefs and maintenance summaries

Design (from DESIGN.md Phase 7):
    - Aggregates building operations data (alarms, energy, sensors, equipment)
    - Generates structured operation briefs for O&M teams
    - Report types: daily brief, alarm summary, energy summary, maintenance
    - Rule-based aggregation, no LLM dependency
    - Confidence based on data completeness
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class ReportType(str, Enum):
    """Type of operation report."""
    DAILY_BRIEF = "daily_brief"
    ALARM_SUMMARY = "alarm_summary"
    ENERGY_SUMMARY = "energy_summary"
    MAINTENANCE = "maintenance"


class SectionType(str, Enum):
    """Section types within a report."""
    ALARMS = "alarms"
    ENERGY = "energy"
    SENSORS = "sensors"
    EQUIPMENT = "equipment"
    RECOMMENDATIONS = "recommendations"


class TimeRange(BaseModel):
    """Time range for report data collection."""
    start: str = Field(default="", description="Start time (ISO or label)")
    end: str = Field(default="", description="End time (ISO or label)")
    label: str = Field(default="past 24h", description="Human-readable label")


class AlarmSummarySection(BaseModel):
    """Alarm statistics for a report section."""
    total_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    unresolved_count: int = 0
    top_alarm_points: list[str] = Field(default_factory=list)


class EnergySummarySection(BaseModel):
    """Energy statistics for a report section."""
    total_consumption_kwh: float = 0.0
    avg_load_pct: float = 0.0
    peak_load_pct: float = 0.0
    load_trend: str = Field(default="stable")
    optimization_opportunities: int = 0


class SensorHealthSection(BaseModel):
    """Sensor health statistics for a report section."""
    total_count: int = 0
    healthy_count: int = 0
    warning_count: int = 0
    fault_count: int = 0
    offline_count: int = 0
    avg_score: float = 0.0
    flagged_sensors: list[str] = Field(default_factory=list)


class EquipmentStatusSection(BaseModel):
    """Equipment status statistics for a report section."""
    total_count: int = 0
    running_count: int = 0
    stopped_count: int = 0
    fault_count: int = 0
    equipment_summary: list[dict[str, Any]] = Field(default_factory=list)


class ReportSection(BaseModel):
    """A single section within an operation report."""
    section_type: SectionType
    title: str
    content: dict[str, Any] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)


class OperationReport(BaseModel):
    """Complete operation report output."""
    report_type: ReportType
    title: str
    time_range: TimeRange = Field(default_factory=TimeRange)
    sections: list[ReportSection] = Field(default_factory=list)
    executive_summary: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)


# ── Helper Functions ──


def _parse_time_range(payload: dict[str, Any]) -> TimeRange:
    """Extract time range from payload."""
    tr_data = payload.get("time_range", {})
    if not isinstance(tr_data, dict):
        return TimeRange()
    return TimeRange(
        start=str(tr_data.get("start", "")),
        end=str(tr_data.get("end", "")),
        label=str(tr_data.get("label", "past 24h")),
    )


def _extract_alarm_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract alarm records from payload."""
    alarms = payload.get("alarms", [])
    if not isinstance(alarms, list):
        return []
    return alarms


def _build_alarm_section(alarm_data: list[dict[str, Any]]) -> ReportSection:
    """Build alarm summary section from alarm records."""
    severity_counts: dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0,
    }
    unresolved = 0
    point_counts: dict[str, int] = {}

    for alarm in alarm_data:
        sev = str(alarm.get("severity", "medium")).lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
        else:
            severity_counts["medium"] += 1

        resolved = alarm.get("resolved", False)
        if not resolved:
            unresolved += 1

        point_id = str(alarm.get("point_id", alarm.get("id", "")))
        if point_id:
            point_counts[point_id] = point_counts.get(point_id, 0) + 1

    # Top alarm points by frequency
    sorted_points = sorted(point_counts.items(), key=lambda x: x[1], reverse=True)
    top_points = [p[0] for p in sorted_points[:5]]

    summary = AlarmSummarySection(
        total_count=len(alarm_data),
        critical_count=severity_counts["critical"],
        high_count=severity_counts["high"],
        medium_count=severity_counts["medium"],
        low_count=severity_counts["low"],
        unresolved_count=unresolved,
        top_alarm_points=top_points,
    )

    highlights: list[str] = []
    if severity_counts["critical"] > 0:
        highlights.append(f"{severity_counts['critical']} critical alarm(s) require immediate attention")
    if unresolved > 0:
        highlights.append(f"{unresolved} unresolved alarm(s)")
    if top_points:
        highlights.append(f"Most frequent alarm point: {top_points[0]}")

    return ReportSection(
        section_type=SectionType.ALARMS,
        title="Alarm Summary",
        content=summary.model_dump(),
        highlights=highlights,
    )


def _extract_energy_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract energy records from payload."""
    energy = payload.get("energy", [])
    if not isinstance(energy, list):
        return []
    return energy


def _build_energy_section(energy_data: list[dict[str, Any]]) -> ReportSection:
    """Build energy summary section from energy records."""
    total_kwh = 0.0
    load_values: list[float] = []
    opt_opportunities = 0

    for rec in energy_data:
        cur_val = rec.get("curVal")
        rated = rec.get("rated_power")

        if isinstance(cur_val, (int, float)):
            total_kwh += cur_val

        if isinstance(cur_val, (int, float)) and isinstance(rated, (int, float)) and rated > 0:
            load_pct = (cur_val / rated) * 100.0
            load_values.append(load_pct)
            if load_pct < 40.0:
                opt_opportunities += 1

    avg_load = sum(load_values) / len(load_values) if load_values else 0.0
    peak_load = max(load_values) if load_values else 0.0

    # Determine trend (simple: based on average load level)
    if avg_load > 80.0:
        trend = "high"
    elif avg_load < 30.0:
        trend = "low"
    else:
        trend = "stable"

    summary = EnergySummarySection(
        total_consumption_kwh=round(total_kwh, 1),
        avg_load_pct=round(avg_load, 1),
        peak_load_pct=round(peak_load, 1),
        load_trend=trend,
        optimization_opportunities=opt_opportunities,
    )

    highlights: list[str] = []
    if peak_load > 90.0:
        highlights.append(f"Peak load at {peak_load:.0f}% — near capacity")
    if opt_opportunities > 0:
        highlights.append(f"{opt_opportunities} equipment running below 40% load — optimization possible")
    if total_kwh > 0:
        highlights.append(f"Total consumption: {total_kwh:.1f} kWh")

    return ReportSection(
        section_type=SectionType.ENERGY,
        title="Energy Summary",
        content=summary.model_dump(),
        highlights=highlights,
    )


def _extract_sensor_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract sensor records from payload."""
    sensors = payload.get("sensors", [])
    if not isinstance(sensors, list):
        return []
    return sensors


def _build_sensor_section(sensor_data: list[dict[str, Any]]) -> ReportSection:
    """Build sensor health section from sensor records."""
    status_counts = {"healthy": 0, "warning": 0, "fault": 0, "offline": 0}
    scores: list[float] = []
    flagged: list[str] = []

    for sensor in sensor_data:
        status = str(sensor.get("status", "healthy")).lower()
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["healthy"] += 1

        score = sensor.get("health_score")
        if isinstance(score, (int, float)):
            scores.append(float(score))

        if status in ("fault", "offline", "warning"):
            sensor_id = str(sensor.get("id", sensor.get("point_id", "")))
            if sensor_id:
                flagged.append(sensor_id)

    avg_score = sum(scores) / len(scores) if scores else 0.0

    summary = SensorHealthSection(
        total_count=len(sensor_data),
        healthy_count=status_counts["healthy"],
        warning_count=status_counts["warning"],
        fault_count=status_counts["fault"],
        offline_count=status_counts["offline"],
        avg_score=round(avg_score, 1),
        flagged_sensors=flagged[:10],
    )

    highlights: list[str] = []
    if status_counts["fault"] > 0:
        highlights.append(f"{status_counts['fault']} sensor(s) in fault state")
    if status_counts["offline"] > 0:
        highlights.append(f"{status_counts['offline']} sensor(s) offline")
    if avg_score > 0:
        highlights.append(f"Average health score: {avg_score:.0f}/100")

    return ReportSection(
        section_type=SectionType.SENSORS,
        title="Sensor Health",
        content=summary.model_dump(),
        highlights=highlights,
    )


def _extract_equipment_data(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract equipment records from payload."""
    equipment = payload.get("equipment", [])
    if not isinstance(equipment, list):
        return []
    return equipment


def _build_equipment_section(equip_data: list[dict[str, Any]]) -> ReportSection:
    """Build equipment status section from equipment records."""
    status_counts = {"running": 0, "stopped": 0, "fault": 0}
    equip_summary: list[dict[str, Any]] = []

    for equip in equip_data:
        status = str(equip.get("status", "running")).lower()
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["running"] += 1

        equip_summary.append({
            "id": str(equip.get("id", "")),
            "dis": str(equip.get("dis", equip.get("name", ""))),
            "status": status,
        })

    summary = EquipmentStatusSection(
        total_count=len(equip_data),
        running_count=status_counts["running"],
        stopped_count=status_counts["stopped"],
        fault_count=status_counts["fault"],
        equipment_summary=equip_summary[:20],
    )

    highlights: list[str] = []
    if status_counts["fault"] > 0:
        highlights.append(f"{status_counts['fault']} equipment in fault state")
    if status_counts["stopped"] > 0:
        highlights.append(f"{status_counts['stopped']} equipment stopped")
    highlights.append(f"{status_counts['running']} equipment running normally")

    return ReportSection(
        section_type=SectionType.EQUIPMENT,
        title="Equipment Status",
        content=summary.model_dump(),
        highlights=highlights,
    )


def _build_recommendations(sections: list[ReportSection]) -> list[str]:
    """Build prioritized recommendations from all sections.

    Priority: critical alarms > offline sensors > energy optimization > maintenance.
    """
    recommendations: list[str] = []

    for section in sections:
        if section.section_type == SectionType.ALARMS:
            critical = section.content.get("critical_count", 0)
            unresolved = section.content.get("unresolved_count", 0)
            if critical > 0:
                recommendations.append(
                    f"URGENT: Investigate {critical} critical alarm(s) immediately"
                )
            if unresolved > 0:
                recommendations.append(
                    f"Resolve {unresolved} outstanding alarm(s)"
                )

        elif section.section_type == SectionType.SENSORS:
            offline = section.content.get("offline_count", 0)
            fault = section.content.get("fault_count", 0)
            if offline > 0:
                recommendations.append(
                    f"Restore {offline} offline sensor(s) — data gaps affect monitoring"
                )
            if fault > 0:
                recommendations.append(
                    f"Recalibrate or replace {fault} faulty sensor(s)"
                )

        elif section.section_type == SectionType.ENERGY:
            opt = section.content.get("optimization_opportunities", 0)
            if opt > 0:
                recommendations.append(
                    f"Review {opt} low-load equipment for energy optimization"
                )
            peak = section.content.get("peak_load_pct", 0.0)
            if peak > 90.0:
                recommendations.append(
                    "Peak load near capacity — consider load shedding schedule"
                )

        elif section.section_type == SectionType.EQUIPMENT:
            fault = section.content.get("fault_count", 0)
            if fault > 0:
                recommendations.append(
                    f"Schedule maintenance for {fault} faulted equipment"
                )

    return recommendations


def _build_executive_summary(
    report_type: ReportType,
    sections: list[ReportSection],
) -> str:
    """Build a 1-3 sentence executive summary from sections."""
    parts: list[str] = []

    for section in sections:
        if section.section_type == SectionType.ALARMS:
            total = section.content.get("total_count", 0)
            critical = section.content.get("critical_count", 0)
            if total > 0:
                if critical > 0:
                    parts.append(f"{total} alarms ({critical} critical)")
                else:
                    parts.append(f"{total} alarms")

        elif section.section_type == SectionType.ENERGY:
            avg_load = section.content.get("avg_load_pct", 0.0)
            if avg_load > 0:
                parts.append(f"avg load {avg_load:.0f}%")

        elif section.section_type == SectionType.SENSORS:
            avg_score = section.content.get("avg_score", 0.0)
            fault = section.content.get("fault_count", 0)
            offline = section.content.get("offline_count", 0)
            issues = fault + offline
            if issues > 0:
                parts.append(f"{issues} sensor issue(s)")
            elif avg_score > 0:
                parts.append(f"sensor health {avg_score:.0f}/100")

        elif section.section_type == SectionType.EQUIPMENT:
            fault = section.content.get("fault_count", 0)
            running = section.content.get("running_count", 0)
            if fault > 0:
                parts.append(f"{fault} equipment fault(s)")
            elif running > 0:
                parts.append(f"{running} equipment running")

    type_label = report_type.value.replace("_", " ").title()

    if not parts:
        return f"{type_label}: no data available."

    return f"{type_label}: " + "; ".join(parts) + "."


# ── Section selection by report type ──

_REPORT_TYPE_SECTIONS: dict[ReportType, list[SectionType]] = {
    ReportType.DAILY_BRIEF: [
        SectionType.ALARMS,
        SectionType.ENERGY,
        SectionType.SENSORS,
        SectionType.EQUIPMENT,
    ],
    ReportType.ALARM_SUMMARY: [SectionType.ALARMS],
    ReportType.ENERGY_SUMMARY: [SectionType.ENERGY],
    ReportType.MAINTENANCE: [SectionType.SENSORS, SectionType.EQUIPMENT],
}



# ── Report Engine ──


class ReportEngine(BaseEngine):
    """Report generation engine.

    Aggregates operational data, alarm history, and energy metrics
    into structured operation briefs. Rule-based aggregation, no LLM.

    Input payload keys:
        - report_type (str): "daily_brief", "alarm_summary", "energy_summary", "maintenance"
        - time_range (dict): {"start": "", "end": "", "label": "past 24h"}
        - alarms (list): Alarm records with id, severity, resolved fields
        - energy (list): Energy records with curVal, rated_power fields
        - sensors (list): Sensor records with health_score, status fields
        - equipment (list): Equipment records with id, dis, status fields
    """

    @property
    def name(self) -> str:
        return "report"

    @property
    def description(self) -> str:
        return "Automated operation briefs and maintenance report generation"

    @property
    def actions(self) -> set[str]:
        return {"report"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"ReportEngine does not support action: {action}")

        return self._generate_report(payload)

    def _generate_report(self, payload: dict[str, Any]) -> EngineResult:
        """Generate an operation report from the provided data."""
        # 1. Parse report type
        report_type_str = str(payload.get("report_type", "daily_brief"))
        try:
            report_type = ReportType(report_type_str)
        except ValueError:
            report_type = ReportType.DAILY_BRIEF

        # 2. Parse time range
        time_range = _parse_time_range(payload)

        # 3. Select sections based on report type
        section_types = _REPORT_TYPE_SECTIONS.get(
            report_type,
            list(SectionType),
        )

        # 4. Build sections
        sections: list[ReportSection] = []
        populated_count = 0

        for st in section_types:
            section = self._build_section(st, payload)
            if section is not None:
                sections.append(section)
                # Count sections that have real data
                if self._section_has_data(section):
                    populated_count += 1

        # 5. Recommendations
        recommendations = _build_recommendations(sections)

        # 6. Executive summary
        executive_summary = _build_executive_summary(report_type, sections)

        # 7. Build report
        title = self._build_title(report_type, time_range)
        report = OperationReport(
            report_type=report_type,
            title=title,
            time_range=time_range,
            sections=sections,
            executive_summary=executive_summary,
            recommendations=recommendations,
        )

        # 8. Confidence = data completeness
        total_possible = len(section_types)
        if total_possible > 0:
            confidence = min(populated_count / total_possible * 0.95, 0.95)
        else:
            confidence = 0.0
        confidence = round(confidence, 2)

        return EngineResult(
            status="ok",
            confidence=confidence,
            message=executive_summary,
            data=report.model_dump(),
        )

    @staticmethod
    def _build_section(
        section_type: SectionType,
        payload: dict[str, Any],
    ) -> ReportSection | None:
        """Build a single section by type."""
        if section_type == SectionType.ALARMS:
            data = _extract_alarm_data(payload)
            return _build_alarm_section(data)
        if section_type == SectionType.ENERGY:
            data = _extract_energy_data(payload)
            return _build_energy_section(data)
        if section_type == SectionType.SENSORS:
            data = _extract_sensor_data(payload)
            return _build_sensor_section(data)
        if section_type == SectionType.EQUIPMENT:
            data = _extract_equipment_data(payload)
            return _build_equipment_section(data)
        return None

    @staticmethod
    def _section_has_data(section: ReportSection) -> bool:
        """Check if a section has meaningful data (not all zeros)."""
        content = section.content
        if section.section_type == SectionType.ALARMS:
            return bool(content.get("total_count", 0) > 0)
        if section.section_type == SectionType.ENERGY:
            return bool(content.get("total_consumption_kwh", 0.0) > 0)
        if section.section_type == SectionType.SENSORS:
            return bool(content.get("total_count", 0) > 0)
        if section.section_type == SectionType.EQUIPMENT:
            return bool(content.get("total_count", 0) > 0)
        return False

    @staticmethod
    def _build_title(report_type: ReportType, time_range: TimeRange) -> str:
        """Build a report title."""
        type_labels = {
            ReportType.DAILY_BRIEF: "Daily Operation Brief",
            ReportType.ALARM_SUMMARY: "Alarm Summary Report",
            ReportType.ENERGY_SUMMARY: "Energy Summary Report",
            ReportType.MAINTENANCE: "Maintenance Report",
        }
        title = type_labels.get(report_type, "Operation Report")
        if time_range.label:
            title += f" ({time_range.label})"
        return title
