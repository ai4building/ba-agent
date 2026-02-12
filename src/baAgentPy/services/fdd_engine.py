"""FDD (Fault Detection & Diagnostics) — fault pattern recognition and root cause analysis.

Handles:
    - diagnose: analyze alarm context and identify root cause

Design (from DESIGN.md §3.2 & §4.1):
    - Fault pattern recognition via correlation analysis (local vs global)
    - Root cause analysis (RCA) traces along Haystack topology chain
    - Confidence scoring based on pattern match strength and sensor correlation
    - Rule-based engine (Phase 3); LLM-augmented reasoning in later phase
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class FaultSeverity(str, Enum):
    """Alarm severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FaultCategory(str, Enum):
    """High-level fault classification."""
    SENSOR = "sensor"           # Sensor malfunction / drift
    MECHANICAL = "mechanical"   # Mechanical component failure
    CONTROL = "control"         # Control loop / PID issue
    CAPACITY = "capacity"       # Insufficient capacity
    ENERGY = "energy"           # Energy anomaly
    UNKNOWN = "unknown"


class AlarmContext(BaseModel):
    """Input context for an alarm to be diagnosed."""
    alarm_point_id: str = Field(description="Ref ID of the alarming point")
    alarm_message: str = Field(default="", description="Alarm description text")
    equip_id: str = Field(default="", description="Equipment ref the alarm belongs to")
    point_data: list[dict[str, Any]] = Field(default_factory=list, description="Related point readings (from Grid)")
    severity: FaultSeverity = Field(default=FaultSeverity.MEDIUM)


class RcaStep(BaseModel):
    """One step in the root cause analysis chain."""
    point_id: str
    point_name: str
    observation: str
    is_abnormal: bool


class DiagnosisResult(BaseModel):
    """Complete diagnosis output."""
    fault_category: FaultCategory
    root_cause: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: FaultSeverity
    rca_chain: list[RcaStep] = Field(default_factory=list, description="Topology trace steps")
    affected_equipment: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ── Fault Pattern Library ──


class FaultPattern(BaseModel):
    """A predefined fault signature to match against sensor data."""
    name: str
    category: FaultCategory
    description: str
    conditions: list[str] = Field(description="List of condition keys to check")
    root_cause_template: str
    recommendations: list[str]
    base_confidence: float = 0.75


# Common HVAC fault patterns (rule-based knowledge base)
_FAULT_PATTERNS: list[FaultPattern] = [
    FaultPattern(
        name="supply_air_temp_high",
        category=FaultCategory.MECHANICAL,
        description="Supply air temperature exceeds setpoint significantly",
        conditions=["sat_high", "cooling_valve_open"],
        root_cause_template="Cooling coil performance degraded — possible fouling, low refrigerant charge, or compressor issue",
        recommendations=[
            "Check cooling coil differential pressure",
            "Verify refrigerant charge levels",
            "Inspect compressor operation",
        ],
    ),
    FaultPattern(
        name="vav_low_airflow",
        category=FaultCategory.MECHANICAL,
        description="VAV box airflow below minimum despite demand",
        conditions=["airflow_low", "damper_open"],
        root_cause_template="VAV airflow insufficient — possible AHU supply fan issue or duct obstruction",
        recommendations=[
            "Check AHU supply fan VFD status",
            "Inspect VAV damper actuator",
            "Check for duct obstructions",
        ],
    ),
    FaultPattern(
        name="sensor_drift",
        category=FaultCategory.SENSOR,
        description="Sensor reading inconsistent with correlated sensors",
        conditions=["reading_deviation", "stable_neighbors"],
        root_cause_template="Sensor drift detected — reading deviates from physically correlated sensors",
        recommendations=[
            "Recalibrate sensor",
            "Compare with portable reference instrument",
            "Schedule sensor replacement if drift persists",
        ],
    ),
    FaultPattern(
        name="hunting_oscillation",
        category=FaultCategory.CONTROL,
        description="Control output oscillating rapidly around setpoint",
        conditions=["oscillation_detected", "pid_output_swing"],
        root_cause_template="PID control loop hunting — tuning parameters likely incorrect",
        recommendations=[
            "Review PID gains (reduce proportional or increase integral)",
            "Check for oversized actuator or valve",
            "Verify sensor response time",
        ],
    ),
    FaultPattern(
        name="simultaneous_heating_cooling",
        category=FaultCategory.ENERGY,
        description="Heating and cooling operating simultaneously",
        conditions=["heating_active", "cooling_active"],
        root_cause_template="Simultaneous heating and cooling — control deadband too narrow or conflicting setpoints",
        recommendations=[
            "Widen deadband between heating and cooling setpoints",
            "Check for schedule conflicts",
            "Verify economizer lockout settings",
        ],
    ),
    FaultPattern(
        name="high_discharge_pressure",
        category=FaultCategory.MECHANICAL,
        description="Chiller discharge pressure exceeds normal range",
        conditions=["discharge_pressure_high"],
        root_cause_template="Condenser heat rejection insufficient — possible cooling tower fan failure or condenser fouling",
        recommendations=[
            "Inspect cooling tower fan belt and motor",
            "Check condenser tube fouling",
            "Verify condenser water flow rate",
        ],
    ),
    FaultPattern(
        name="frozen_sensor",
        category=FaultCategory.SENSOR,
        description="Sensor output unchanged for abnormal duration",
        conditions=["value_frozen"],
        root_cause_template="Sensor output frozen — possible wiring issue, failed sensor, or disconnected input",
        recommendations=[
            "Verify sensor wiring continuity",
            "Check controller input channel",
            "Replace sensor if wiring is intact",
        ],
    ),
]


# ── Condition Evaluators ──


def _evaluate_conditions(point_data: list[dict[str, Any]]) -> set[str]:
    """Evaluate which fault conditions are present in the point data.

    Analyzes the normalized point data rows and returns a set of
    condition keys that are currently active.
    """
    active: set[str] = set()

    for point in point_data:
        cur_val = point.get("curVal")
        name = str(point.get("dis", point.get("id", ""))).lower()
        his_avg = point.get("hisAvg")
        his_min = point.get("hisMin")
        his_max = point.get("hisMax")

        if cur_val is None:
            continue

        if not isinstance(cur_val, (int, float)):
            continue

        # Supply air temperature checks
        if _name_matches(name, ["supply", "sat", "discharge"]) and _name_matches(name, ["temp"]):
            if cur_val > 18.0:  # >18°C supply air is likely too high for cooling
                active.add("sat_high")

        # Airflow checks
        if _name_matches(name, ["airflow", "cfm", "flow"]):
            if cur_val < 50.0:  # Very low airflow
                active.add("airflow_low")

        # Damper / valve position checks
        if _name_matches(name, ["damper"]):
            if cur_val > 80.0:  # Damper >80% open
                active.add("damper_open")

        if _name_matches(name, ["cooling", "clg"]) and _name_matches(name, ["valve", "vlv"]):
            if cur_val > 50.0:
                active.add("cooling_valve_open")

        # Heating / cooling active
        if _name_matches(name, ["heating", "htg"]) and _name_matches(name, ["cmd", "output", "valve"]):
            if cur_val > 10.0:
                active.add("heating_active")

        if _name_matches(name, ["cooling", "clg"]) and _name_matches(name, ["cmd", "output", "valve"]):
            if cur_val > 10.0:
                active.add("cooling_active")

        # Discharge pressure
        if _name_matches(name, ["discharge", "cond"]) and _name_matches(name, ["press"]):
            if cur_val > 1200.0:  # kPa
                active.add("discharge_pressure_high")

        # Frozen sensor (check via history stats)
        if his_min is not None and his_max is not None:
            if isinstance(his_min, (int, float)) and isinstance(his_max, (int, float)):
                if his_max - his_min < 0.01 and his_max != 0:
                    active.add("value_frozen")

        # Reading deviation from historical average
        if his_avg is not None and isinstance(his_avg, (int, float)):
            deviation = abs(cur_val - his_avg)
            if his_avg != 0 and deviation / abs(his_avg) > 0.3:
                active.add("reading_deviation")

        # Oscillation detection (large range relative to average)
        if (his_min is not None and his_max is not None and his_avg is not None
                and isinstance(his_min, (int, float)) and isinstance(his_max, (int, float))
                and isinstance(his_avg, (int, float)) and his_avg != 0):
            swing = his_max - his_min
            if swing / abs(his_avg) > 0.5:
                active.add("oscillation_detected")

        # PID output swing
        if _name_matches(name, ["pid", "output", "cmd"]):
            if (his_min is not None and his_max is not None
                    and isinstance(his_min, (int, float)) and isinstance(his_max, (int, float))):
                if his_max - his_min > 40.0:
                    active.add("pid_output_swing")

    # Infer stable neighbors (if most sensors have low deviation, a deviating one stands out)
    deviation_count = sum(1 for p in point_data
                         if p.get("hisAvg") is not None
                         and p.get("curVal") is not None
                         and isinstance(p.get("hisAvg"), (int, float))
                         and isinstance(p.get("curVal"), (int, float))
                         and abs(p["curVal"] - p["hisAvg"]) / max(abs(p["hisAvg"]), 0.01) < 0.1)
    if deviation_count >= 2 and "reading_deviation" in active:
        active.add("stable_neighbors")

    return active


def _name_matches(name: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the point name."""
    return any(kw in name for kw in keywords)


def _build_rca_chain(point_data: list[dict[str, Any]], active_conditions: set[str]) -> list[RcaStep]:
    """Build an RCA trace from the point data, flagging abnormal readings."""
    chain: list[RcaStep] = []
    for point in point_data:
        cur_val = point.get("curVal")
        name = str(point.get("dis", point.get("id", "")))
        point_id = str(point.get("id", ""))
        his_avg = point.get("hisAvg")

        is_abnormal = False
        observation = f"Current: {cur_val}"

        if (cur_val is not None and his_avg is not None
                and isinstance(cur_val, (int, float)) and isinstance(his_avg, (int, float))
                and his_avg != 0):
            deviation_pct = abs(cur_val - his_avg) / abs(his_avg) * 100
            if deviation_pct > 20:
                is_abnormal = True
                observation = f"Current: {cur_val} (deviates {deviation_pct:.0f}% from avg {his_avg})"
            else:
                observation = f"Current: {cur_val} (normal, avg {his_avg})"

        chain.append(RcaStep(
            point_id=point_id,
            point_name=name,
            observation=observation,
            is_abnormal=is_abnormal,
        ))

    return chain


# ── FDD Engine ──


class FddEngine(BaseEngine):
    """Fault Detection & Diagnostics engine.

    Analyzes alarm data, correlates related sensor readings, and performs
    root cause analysis (RCA) with confidence scoring.

    Input payload keys:
        - alarm_id (str): ID of the alarming point
        - alarm_message (str): Alarm description
        - equip_id (str): Equipment ref
        - grid (dict): Normalized point data from GridConverter
          (with 'rows' containing curVal, hisAvg, hisMin, hisMax, etc.)
    """

    @property
    def name(self) -> str:
        return "fdd"

    @property
    def description(self) -> str:
        return "Fault detection and root cause analysis for building alarms"

    @property
    def actions(self) -> set[str]:
        return {"diagnose"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"FddEngine does not support action: {action}")

        return self._diagnose(payload)

    def _diagnose(self, payload: dict[str, Any]) -> EngineResult:
        """Run fault diagnosis on the provided alarm context."""
        # Extract context
        alarm_id = str(payload.get("alarm_id", "unknown"))
        alarm_message = str(payload.get("alarm_message", ""))
        equip_id = str(payload.get("equip_id", ""))

        # Get point data from normalized grid
        grid_data = payload.get("grid", {})
        point_data: list[dict[str, Any]]
        if isinstance(grid_data, dict):
            point_data = grid_data.get("rows", [])
        elif isinstance(grid_data, list):
            point_data = grid_data
        else:
            point_data = []

        # Evaluate active fault conditions
        active_conditions = _evaluate_conditions(point_data)

        # Match against fault patterns
        diagnosis = self._match_patterns(
            active_conditions=active_conditions,
            point_data=point_data,
            alarm_id=alarm_id,
            alarm_message=alarm_message,
            equip_id=equip_id,
        )

        return EngineResult(
            status="ok",
            confidence=diagnosis.confidence,
            message=diagnosis.explanation,
            data=diagnosis.model_dump(),
        )

    def _match_patterns(
        self,
        active_conditions: set[str],
        point_data: list[dict[str, Any]],
        alarm_id: str,
        alarm_message: str,
        equip_id: str,
    ) -> DiagnosisResult:
        """Match active conditions against the fault pattern library."""
        best_match: FaultPattern | None = None
        best_score = 0.0

        for pattern in _FAULT_PATTERNS:
            matched = set(pattern.conditions) & active_conditions
            if not matched:
                continue

            # Score: fraction of conditions met × base confidence
            score = len(matched) / len(pattern.conditions) * pattern.base_confidence

            # Bonus for alarm message keyword match
            if alarm_message:
                msg_lower = alarm_message.lower()
                if any(kw in msg_lower for kw in pattern.description.lower().split()):
                    score = min(score + 0.1, 0.99)

            if score > best_score:
                best_score = score
                best_match = pattern

        # Build RCA chain
        rca_chain = _build_rca_chain(point_data, active_conditions)
        abnormal_points = [s.point_name for s in rca_chain if s.is_abnormal]

        if best_match is not None:
            return DiagnosisResult(
                fault_category=best_match.category,
                root_cause=best_match.root_cause_template,
                explanation=(
                    f"Alarm on {alarm_id}: {best_match.description}. "
                    f"{best_match.root_cause_template}. "
                    f"Conditions matched: {sorted(set(best_match.conditions) & active_conditions)}."
                ),
                confidence=round(best_score, 2),
                severity=self._infer_severity(best_score, best_match.category),
                rca_chain=rca_chain,
                affected_equipment=[equip_id] if equip_id else [],
                recommendations=best_match.recommendations,
            )

        # No pattern matched — return low-confidence unknown diagnosis
        return DiagnosisResult(
            fault_category=FaultCategory.UNKNOWN,
            root_cause="No known fault pattern matched the observed conditions",
            explanation=(
                f"Alarm on {alarm_id}: unable to match a known fault pattern. "
                f"Active conditions: {sorted(active_conditions) if active_conditions else 'none'}. "
                f"Abnormal points: {abnormal_points if abnormal_points else 'none'}. "
                f"Manual investigation recommended."
            ),
            confidence=0.2 if active_conditions else 0.0,
            severity=FaultSeverity.INFO,
            rca_chain=rca_chain,
            affected_equipment=[equip_id] if equip_id else [],
            recommendations=["Manual investigation required — no known pattern matched"],
        )

    @staticmethod
    def _infer_severity(confidence: float, category: FaultCategory) -> FaultSeverity:
        """Infer fault severity from confidence and category."""
        if category == FaultCategory.MECHANICAL and confidence > 0.6:
            return FaultSeverity.HIGH
        if confidence > 0.8:
            return FaultSeverity.HIGH
        if confidence > 0.5:
            return FaultSeverity.MEDIUM
        return FaultSeverity.LOW
