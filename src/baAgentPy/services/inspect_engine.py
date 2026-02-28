"""Virtual inspection — sensor health scoring and drift detection.

Handles:
    - inspect: score sensor health (0-100) and detect anomalies

Design (from DESIGN.md §3.4 & §4.3):
    - Per-sensor health scoring based on multiple quality checks
    - Frozen/stuck value detection (zero variance in history)
    - Drift detection (current value deviates from historical baseline)
    - Range violation detection (outside physically plausible bounds)
    - Consistency checks across correlated sensor groups
    - Rule-based engine (Phase 5); ML-based anomaly detection in later phase
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class SensorStatus(str, Enum):
    """Overall sensor status classification."""
    HEALTHY = "healthy"
    WARNING = "warning"
    FAULT = "fault"
    OFFLINE = "offline"


class FindingType(str, Enum):
    """Type of inspection finding."""
    FROZEN = "frozen"                # Value stuck / zero variance
    DRIFT = "drift"                  # Gradual deviation from baseline
    RANGE_VIOLATION = "range_violation"  # Outside physical bounds
    SPIKE = "spike"                  # Sudden large deviation
    FLATLINE = "flatline"            # No variation at all (hisMin == hisMax)
    INCONSISTENCY = "inconsistency"  # Disagrees with correlated sensors
    MISSING_DATA = "missing_data"    # No current value or history


class InspectionFinding(BaseModel):
    """A single finding from sensor inspection."""
    finding_type: FindingType
    severity: str = Field(description="'critical', 'warning', or 'info'")
    description: str
    penalty: int = Field(description="Health score deduction (0-100)")


class SensorHealthReport(BaseModel):
    """Health assessment for a single sensor."""
    point_id: str
    point_name: str
    health_score: int = Field(ge=0, le=100, description="0=failed, 100=perfect")
    status: SensorStatus
    findings: list[InspectionFinding] = Field(default_factory=list)
    recommendation: str = Field(default="")


class InspectionResult(BaseModel):
    """Complete inspection output for a group of sensors."""
    sensor_reports: list[SensorHealthReport] = Field(default_factory=list)
    aggregate_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Average health across all sensors")
    healthy_count: int = 0
    warning_count: int = 0
    fault_count: int = 0
    offline_count: int = 0
    summary: str = Field(default="")


# ── Physical Range Constants ──

# Plausible ranges for common HVAC sensor types: (min, max)
_PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "temp": (-40.0, 80.0),           # Temperature °C
    "humidity": (0.0, 100.0),        # Relative humidity %
    "pressure": (0.0, 5000.0),       # Pressure Pa
    "co2": (0.0, 10000.0),           # CO2 ppm
    "flow": (0.0, 100000.0),         # Airflow CFM / L/s
    "valve": (0.0, 100.0),           # Valve position %
    "damper": (0.0, 100.0),          # Damper position %
    "speed": (0.0, 100.0),           # Fan/pump speed %
    "power": (0.0, 100000.0),        # Power kW
}


# ── Analysis Functions ──


def _infer_sensor_type(name: str) -> str | None:
    """Infer sensor type from point name for range checking."""
    name_lower = name.lower()

    if any(kw in name_lower for kw in ["temp", "温度"]):
        return "temp"
    if any(kw in name_lower for kw in ["humid", "rh", "湿度"]):
        return "humidity"
    if any(kw in name_lower for kw in ["press", "压力", "static"]):
        return "pressure"
    if any(kw in name_lower for kw in ["co2", "二氧化碳"]):
        return "co2"
    if any(kw in name_lower for kw in ["flow", "cfm", "风量"]):
        return "flow"
    if any(kw in name_lower for kw in ["valve", "vlv", "阀"]):
        return "valve"
    if any(kw in name_lower for kw in ["damper", "风阀"]):
        return "damper"
    if any(kw in name_lower for kw in ["speed", "vfd", "freq", "转速"]):
        return "speed"
    if any(kw in name_lower for kw in ["power", "kw", "功率"]):
        return "power"

    return None


def _check_frozen(point: dict[str, Any]) -> InspectionFinding | None:
    """Check if sensor value is frozen (stuck)."""
    his_min = point.get("hisMin")
    his_max = point.get("hisMax")

    if his_min is None or his_max is None:
        return None
    if not isinstance(his_min, (int, float)) or not isinstance(his_max, (int, float)):
        return None

    spread = abs(his_max - his_min)
    if spread < 0.01 and his_max != 0:
        return InspectionFinding(
            finding_type=FindingType.FROZEN,
            severity="critical",
            description=f"Value frozen — history range is only {spread:.4f} (min={his_min}, max={his_max})",
            penalty=40,
        )

    if spread < 0.1 and his_max != 0:
        return InspectionFinding(
            finding_type=FindingType.FLATLINE,
            severity="warning",
            description=f"Very low variance — history range is {spread:.3f}",
            penalty=15,
        )

    return None


def _check_drift(point: dict[str, Any]) -> InspectionFinding | None:
    """Check if current value has drifted from historical average."""
    cur_val = point.get("curVal")
    his_avg = point.get("hisAvg")

    if cur_val is None or his_avg is None:
        return None
    if not isinstance(cur_val, (int, float)) or not isinstance(his_avg, (int, float)):
        return None
    if his_avg == 0:
        return None

    deviation_pct = abs(cur_val - his_avg) / abs(his_avg) * 100

    if deviation_pct > 50:
        return InspectionFinding(
            finding_type=FindingType.DRIFT,
            severity="critical",
            description=f"Severe drift: current {cur_val} vs avg {his_avg} ({deviation_pct:.0f}% deviation)",
            penalty=35,
        )
    if deviation_pct > 25:
        return InspectionFinding(
            finding_type=FindingType.DRIFT,
            severity="warning",
            description=f"Moderate drift: current {cur_val} vs avg {his_avg} ({deviation_pct:.0f}% deviation)",
            penalty=20,
        )

    return None


def _check_spike(point: dict[str, Any]) -> InspectionFinding | None:
    """Check if current value is a sudden spike beyond historical range."""
    cur_val = point.get("curVal")
    his_min = point.get("hisMin")
    his_max = point.get("hisMax")

    if cur_val is None or his_min is None or his_max is None:
        return None
    if not isinstance(cur_val, (int, float)):
        return None
    if not isinstance(his_min, (int, float)) or not isinstance(his_max, (int, float)):
        return None

    his_range = his_max - his_min
    if his_range < 0.01:
        return None  # Handled by frozen check

    if cur_val > his_max + his_range * 0.5:
        overshoot = cur_val - his_max
        return InspectionFinding(
            finding_type=FindingType.SPIKE,
            severity="warning",
            description=f"Spike above historical max: current {cur_val} > max {his_max} (+{overshoot:.1f})",
            penalty=15,
        )
    if cur_val < his_min - his_range * 0.5:
        undershoot = his_min - cur_val
        return InspectionFinding(
            finding_type=FindingType.SPIKE,
            severity="warning",
            description=f"Spike below historical min: current {cur_val} < min {his_min} (-{undershoot:.1f})",
            penalty=15,
        )

    return None


def _check_range(point: dict[str, Any], sensor_type: str | None) -> InspectionFinding | None:
    """Check if current value is outside physically plausible range."""
    if sensor_type is None:
        return None

    cur_val = point.get("curVal")
    if cur_val is None or not isinstance(cur_val, (int, float)):
        return None

    bounds = _PLAUSIBLE_RANGES.get(sensor_type)
    if bounds is None:
        return None

    low, high = bounds
    if cur_val < low or cur_val > high:
        return InspectionFinding(
            finding_type=FindingType.RANGE_VIOLATION,
            severity="critical",
            description=f"Value {cur_val} outside plausible range [{low}, {high}] for {sensor_type}",
            penalty=30,
        )

    return None


def _check_missing(point: dict[str, Any]) -> InspectionFinding | None:
    """Check if sensor has missing current value or no history data."""
    cur_val = point.get("curVal")
    his_avg = point.get("hisAvg")

    if cur_val is None:
        return InspectionFinding(
            finding_type=FindingType.MISSING_DATA,
            severity="critical",
            description="No current value — sensor may be offline",
            penalty=50,
        )

    if his_avg is None:
        return InspectionFinding(
            finding_type=FindingType.MISSING_DATA,
            severity="warning",
            description="No historical data available — cannot assess drift or trend",
            penalty=10,
        )

    return None


def _check_consistency(
    point: dict[str, Any],
    same_type_points: list[dict[str, Any]],
) -> InspectionFinding | None:
    """Check if this sensor is consistent with other sensors of the same type.

    If most similar sensors agree but this one diverges significantly,
    flag an inconsistency.
    """
    cur_val = point.get("curVal")
    if cur_val is None or not isinstance(cur_val, (int, float)):
        return None

    peer_vals: list[float] = []
    for peer in same_type_points:
        peer_id = peer.get("id", "")
        if peer_id == point.get("id", ""):
            continue  # Skip self
        pv = peer.get("curVal")
        if isinstance(pv, (int, float)):
            peer_vals.append(pv)

    if len(peer_vals) < 2:
        return None  # Need at least 2 peers for consistency check

    peer_avg = sum(peer_vals) / len(peer_vals)
    if peer_avg == 0:
        return None

    deviation_pct = abs(cur_val - peer_avg) / abs(peer_avg) * 100

    if deviation_pct > 40:
        return InspectionFinding(
            finding_type=FindingType.INCONSISTENCY,
            severity="warning",
            description=(
                f"Inconsistent with peers: this sensor reads {cur_val}, "
                f"but {len(peer_vals)} similar sensors average {peer_avg:.1f} "
                f"({deviation_pct:.0f}% deviation)"
            ),
            penalty=20,
        )

    return None


def _assess_sensor(
    point: dict[str, Any],
    same_type_points: list[dict[str, Any]],
) -> SensorHealthReport:
    """Run all checks on a single sensor and produce a health report."""
    point_id = str(point.get("id", ""))
    point_name = str(point.get("dis", point_id))
    sensor_type = _infer_sensor_type(point_name)

    findings: list[InspectionFinding] = []

    # Run each check
    for check_fn in [_check_missing, _check_frozen, _check_drift, _check_spike]:
        finding = check_fn(point)
        if finding is not None:
            findings.append(finding)

    range_finding = _check_range(point, sensor_type)
    if range_finding is not None:
        findings.append(range_finding)

    consistency_finding = _check_consistency(point, same_type_points)
    if consistency_finding is not None:
        findings.append(consistency_finding)

    # Compute health score
    total_penalty = sum(f.penalty for f in findings)
    health_score = max(0, 100 - total_penalty)

    # Determine status — offline takes priority regardless of score
    has_offline = any(f.finding_type == FindingType.MISSING_DATA and f.severity == "critical"
                      for f in findings)
    if has_offline:
        status = SensorStatus.OFFLINE
    elif health_score >= 80:
        status = SensorStatus.HEALTHY
    elif health_score >= 50:
        status = SensorStatus.WARNING
    else:
        status = SensorStatus.FAULT

    # Build recommendation
    recommendation = _build_recommendation(findings, point_name)

    return SensorHealthReport(
        point_id=point_id,
        point_name=point_name,
        health_score=health_score,
        status=status,
        findings=findings,
        recommendation=recommendation,
    )


def _build_recommendation(findings: list[InspectionFinding], point_name: str) -> str:
    """Generate a human-readable recommendation based on findings."""
    if not findings:
        return f"{point_name}: no issues detected"

    critical = [f for f in findings if f.severity == "critical"]
    warnings = [f for f in findings if f.severity == "warning"]

    parts: list[str] = []
    if critical:
        types = {f.finding_type.value for f in critical}
        if "frozen" in types:
            parts.append("verify sensor wiring and replace if stuck")
        if "range_violation" in types:
            parts.append("check sensor calibration — reading outside physical bounds")
        if "drift" in types:
            parts.append("recalibrate sensor — significant drift from baseline")
        if "missing_data" in types:
            parts.append("check sensor connection — no current reading")
    if warnings:
        types = {f.finding_type.value for f in warnings}
        if "inconsistency" in types:
            parts.append("compare with portable reference instrument")
        if "spike" in types:
            parts.append("monitor for recurring spikes")
        if "drift" in types and "drift" not in {f.finding_type.value for f in critical}:
            parts.append("schedule recalibration")

    return f"{point_name}: " + "; ".join(parts) if parts else f"{point_name}: monitor"


def _group_by_sensor_type(point_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group points by inferred sensor type for consistency checks."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for point in point_data:
        name = str(point.get("dis", point.get("id", "")))
        sensor_type = _infer_sensor_type(name)
        key = sensor_type or "unknown"
        groups.setdefault(key, []).append(point)
    return groups


# ── Inspection Engine ──


class InspectionEngine(BaseEngine):
    """Virtual inspection engine.

    Scores sensor health (0-100), detects zero-drift, frozen values,
    range violations, and performs consistency checks across related
    sensor groups.

    Input payload keys:
        - equip_id (str): Equipment ref (optional, for context)
        - grid (dict): Normalized point data with curVal/hisAvg/hisMin/hisMax
    """

    @property
    def name(self) -> str:
        return "inspect"

    @property
    def description(self) -> str:
        return "Sensor health scoring, drift detection, and consistency checks"

    @property
    def actions(self) -> set[str]:
        return {"inspect"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"InspectEngine does not support action: {action}")

        return self._inspect(payload)

    def _inspect(self, payload: dict[str, Any]) -> EngineResult:
        """Run virtual inspection on the provided sensor data."""
        # Extract point data
        grid_data = payload.get("grid", {})
        point_data: list[dict[str, Any]]
        if isinstance(grid_data, dict):
            point_data = grid_data.get("rows", [])
        elif isinstance(grid_data, list):
            point_data = grid_data
        else:
            point_data = []

        if not point_data:
            result = InspectionResult(
                summary="No sensor data provided for inspection.",
            )
            return EngineResult(
                status="ok",
                confidence=0.0,
                message=result.summary,
                data=result.model_dump(),
            )

        # Group by sensor type for consistency checks
        type_groups = _group_by_sensor_type(point_data)

        # Assess each sensor
        reports: list[SensorHealthReport] = []
        for point in point_data:
            name = str(point.get("dis", point.get("id", "")))
            sensor_type = _infer_sensor_type(name) or "unknown"
            same_type = type_groups.get(sensor_type, [])
            report = _assess_sensor(point, same_type)
            reports.append(report)

        # Compute aggregates
        healthy = sum(1 for r in reports if r.status == SensorStatus.HEALTHY)
        warning = sum(1 for r in reports if r.status == SensorStatus.WARNING)
        fault = sum(1 for r in reports if r.status == SensorStatus.FAULT)
        offline = sum(1 for r in reports if r.status == SensorStatus.OFFLINE)
        avg_score = sum(r.health_score for r in reports) / len(reports)

        # Build summary
        total = len(reports)
        fault_names = [r.point_name for r in reports if r.status in (SensorStatus.FAULT, SensorStatus.OFFLINE)]
        warning_names = [r.point_name for r in reports if r.status == SensorStatus.WARNING]

        summary_parts = [f"Inspected {total} sensors: {healthy} healthy"]
        if warning > 0:
            summary_parts.append(f"{warning} warning ({', '.join(warning_names[:3])})")
        if fault + offline > 0:
            summary_parts.append(f"{fault + offline} fault/offline ({', '.join(fault_names[:3])})")
        summary_parts.append(f"Average health: {avg_score:.0f}/100")

        result = InspectionResult(
            sensor_reports=reports,
            aggregate_score=round(avg_score, 1),
            healthy_count=healthy,
            warning_count=warning,
            fault_count=fault,
            offline_count=offline,
            summary=". ".join(summary_parts) + ".",
        )

        # Confidence based on data quality
        has_history = sum(1 for p in point_data if p.get("hisAvg") is not None)
        history_ratio = has_history / total
        confidence = 0.5 + history_ratio * 0.4 + min(total * 0.01, 0.1)
        confidence = min(round(confidence, 2), 0.95)

        return EngineResult(
            status="ok",
            confidence=confidence,
            message=result.summary,
            data=result.model_dump(),
        )


# Backward-compatible alias
InspectEngine = InspectionEngine
