"""Energy optimization — load prediction and dynamic PID setpoint tuning.

Handles:
    - optimize: analyze equipment energy profile and generate optimized setpoints

Design (from DESIGN.md §3.3 & §4.2):
    - Load profile analysis using historical trends (degree-day regression)
    - PID setpoint optimization for HVAC equipment (SAT, CHW, static pressure)
    - Energy savings estimation with confidence scoring
    - Shadow Mode output (recommendations only — no direct writes at Priority 16)
    - Rule-based engine (Phase 4); ML-augmented digital twin in later phase
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class OptimizationTarget(str, Enum):
    """What to optimize for."""
    ENERGY = "energy"          # Minimize energy consumption
    COMFORT = "comfort"        # Maximize comfort (minimal deviation)
    BALANCED = "balanced"      # Trade-off between energy and comfort


class SetpointType(str, Enum):
    """Type of setpoint being optimized."""
    SUPPLY_AIR_TEMP = "supply_air_temp"
    CHILLED_WATER_TEMP = "chilled_water_temp"
    STATIC_PRESSURE = "static_pressure"
    ZONE_TEMP = "zone_temp"
    DISCHARGE_AIR_TEMP = "discharge_air_temp"


class SetpointRecommendation(BaseModel):
    """A single setpoint adjustment recommendation."""
    point_id: str = Field(default="", description="Haystack ref of the setpoint point")
    point_name: str = Field(description="Human-readable point name")
    setpoint_type: SetpointType
    current_value: float
    recommended_value: float
    unit: str = Field(default="")
    savings_pct: float = Field(default=0.0, description="Estimated energy saving percentage")
    reason: str = Field(description="Explanation for this recommendation")


class LoadProfile(BaseModel):
    """Summary of the equipment's energy load profile."""
    avg_load_pct: float = Field(description="Average load percentage (0-100)")
    peak_load_pct: float = Field(description="Peak load percentage (0-100)")
    off_hours_load_pct: float = Field(default=0.0, description="Off-hours load percentage")
    load_trend: str = Field(default="stable", description="trending up, down, or stable")


class OptimizationResult(BaseModel):
    """Complete energy optimization output."""
    target: OptimizationTarget
    equipment_id: str
    equipment_name: str
    load_profile: LoadProfile
    setpoint_recommendations: list[SetpointRecommendation] = Field(default_factory=list)
    estimated_savings_pct: float = Field(default=0.0, description="Overall energy saving estimate %")
    estimated_savings_kwh: float = Field(default=0.0, description="Estimated kWh savings per day")
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)


# ── Analysis Functions ──


def _classify_point(name: str) -> str | None:
    """Classify a point by its name into a known category.

    Returns a category string or None if unclassified.
    """
    name_lower = name.lower()

    # CHW must be checked before SAT (both match "supply" + "temp")
    if _name_matches(name_lower, ["chw", "chilled"]) and _name_matches(name_lower, ["temp"]):
        return "chilled_water_temp"
    if _name_matches(name_lower, ["supply", "sat", "discharge"]) and _name_matches(name_lower, ["temp"]):
        return "supply_air_temp"
    if _name_matches(name_lower, ["static", "duct"]) and _name_matches(name_lower, ["press"]):
        return "static_pressure"
    if _name_matches(name_lower, ["zone", "room", "space"]) and _name_matches(name_lower, ["temp"]):
        return "zone_temp"
    if _name_matches(name_lower, ["cooling", "clg"]) and _name_matches(name_lower, ["valve", "vlv", "cmd"]):
        return "cooling_output"
    if _name_matches(name_lower, ["heating", "htg"]) and _name_matches(name_lower, ["valve", "vlv", "cmd"]):
        return "heating_output"
    if _name_matches(name_lower, ["fan"]) and _name_matches(name_lower, ["speed", "vfd", "freq"]):
        return "fan_speed"
    if _name_matches(name_lower, ["power", "kw", "kwh", "energy"]):
        return "power"
    if _name_matches(name_lower, ["oat", "outdoor", "outside"]) and _name_matches(name_lower, ["temp"]):
        return "outdoor_temp"
    if _name_matches(name_lower, ["return", "rat"]) and _name_matches(name_lower, ["temp"]):
        return "return_air_temp"
    if _name_matches(name_lower, ["damper"]) and _name_matches(name_lower, ["pos", "cmd", "outdoor", "oa"]):
        return "oa_damper"

    return None


def _name_matches(name: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the name."""
    return any(kw in name for kw in keywords)


def _analyze_load_profile(classified: dict[str, list[dict[str, Any]]]) -> LoadProfile:
    """Analyze the equipment's energy load profile from classified point data."""
    # Use cooling/heating output and fan speed to estimate load
    load_indicators: list[float] = []
    peak_indicators: list[float] = []
    avg_indicators: list[float] = []

    for category in ["cooling_output", "heating_output", "fan_speed"]:
        for point in classified.get(category, []):
            cur_val = point.get("curVal")
            his_avg = point.get("hisAvg")
            his_max = point.get("hisMax")
            if isinstance(cur_val, (int, float)):
                load_indicators.append(cur_val)
            if isinstance(his_avg, (int, float)):
                avg_indicators.append(his_avg)
            if isinstance(his_max, (int, float)):
                peak_indicators.append(his_max)

    # Power data if available
    for point in classified.get("power", []):
        cur_val = point.get("curVal")
        his_avg = point.get("hisAvg")
        his_max = point.get("hisMax")
        if isinstance(cur_val, (int, float)):
            load_indicators.append(cur_val)
        if isinstance(his_avg, (int, float)):
            avg_indicators.append(his_avg)
        if isinstance(his_max, (int, float)):
            peak_indicators.append(his_max)

    avg_load = sum(avg_indicators) / len(avg_indicators) if avg_indicators else 50.0
    peak_load = max(peak_indicators) if peak_indicators else 80.0

    # Determine trend
    trend = "stable"
    if load_indicators and avg_indicators:
        current_avg = sum(load_indicators) / len(load_indicators)
        historical_avg = sum(avg_indicators) / len(avg_indicators)
        if historical_avg > 0:
            change_pct = (current_avg - historical_avg) / historical_avg * 100
            if change_pct > 10:
                trend = "increasing"
            elif change_pct < -10:
                trend = "decreasing"

    return LoadProfile(
        avg_load_pct=min(round(avg_load, 1), 100.0),
        peak_load_pct=min(round(peak_load, 1), 100.0),
        load_trend=trend,
    )


def _evaluate_sat_optimization(
    classified: dict[str, list[dict[str, Any]]],
    target: OptimizationTarget,
) -> list[SetpointRecommendation]:
    """Evaluate supply air temperature setpoint optimization opportunities."""
    recommendations: list[SetpointRecommendation] = []

    sat_points = classified.get("supply_air_temp", [])
    cooling_points = classified.get("cooling_output", [])

    for sat_point in sat_points:
        cur_sat = sat_point.get("curVal")
        if not isinstance(cur_sat, (int, float)):
            continue

        point_id = str(sat_point.get("id", ""))
        point_name = str(sat_point.get("dis", point_id))

        # Check if cooling output is low (room for SAT raise)
        avg_cooling = _avg_val(cooling_points, "curVal")

        if avg_cooling is not None and avg_cooling < 50.0:
            # Cooling valve not working hard — can raise SAT to save energy
            raise_amount = _calc_sat_raise(cur_sat, avg_cooling, target)
            if raise_amount > 0:
                new_sat = round(cur_sat + raise_amount, 1)
                savings = round(raise_amount * 3.0, 1)  # ~3% savings per °C SAT raise
                recommendations.append(SetpointRecommendation(
                    point_id=point_id,
                    point_name=point_name,
                    setpoint_type=SetpointType.SUPPLY_AIR_TEMP,
                    current_value=cur_sat,
                    recommended_value=new_sat,
                    unit="°C",
                    savings_pct=savings,
                    reason=f"Cooling output at {avg_cooling:.0f}% — room to raise SAT by {raise_amount:.1f}°C",
                ))
        elif avg_cooling is not None and avg_cooling > 85.0 and cur_sat > 10.0:
            # Cooling struggling — lower SAT slightly (comfort priority)
            if target in (OptimizationTarget.COMFORT, OptimizationTarget.BALANCED):
                lower_amount = min(1.0, cur_sat - 10.0)
                if lower_amount > 0:
                    new_sat = round(cur_sat - lower_amount, 1)
                    recommendations.append(SetpointRecommendation(
                        point_id=point_id,
                        point_name=point_name,
                        setpoint_type=SetpointType.SUPPLY_AIR_TEMP,
                        current_value=cur_sat,
                        recommended_value=new_sat,
                        unit="°C",
                        savings_pct=-2.0,  # Negative = costs more energy
                        reason=f"Cooling output at {avg_cooling:.0f}% — lower SAT to improve comfort",
                    ))

    return recommendations


def _evaluate_static_pressure_optimization(
    classified: dict[str, list[dict[str, Any]]],
    target: OptimizationTarget,
) -> list[SetpointRecommendation]:
    """Evaluate duct static pressure setpoint optimization."""
    recommendations: list[SetpointRecommendation] = []

    sp_points = classified.get("static_pressure", [])
    fan_points = classified.get("fan_speed", [])

    # Reduction aggressiveness depends on target
    max_reduction_pct = 0.20 if target == OptimizationTarget.ENERGY else 0.10
    if target == OptimizationTarget.COMFORT:
        max_reduction_pct = 0.05

    for sp_point in sp_points:
        cur_sp = sp_point.get("curVal")
        if not isinstance(cur_sp, (int, float)):
            continue

        point_id = str(sp_point.get("id", ""))
        point_name = str(sp_point.get("dis", point_id))

        avg_fan = _avg_val(fan_points, "curVal")

        if avg_fan is not None and avg_fan < 60.0 and cur_sp > 150.0:
            # Fan not working hard — can reduce static pressure
            reduction = round(min(cur_sp * max_reduction_pct, 75.0), 0)
            new_sp = round(cur_sp - reduction, 0)
            savings = round(reduction / cur_sp * 20.0, 1)  # Fan power ∝ (SP)^~2.5
            recommendations.append(SetpointRecommendation(
                point_id=point_id,
                point_name=point_name,
                setpoint_type=SetpointType.STATIC_PRESSURE,
                current_value=cur_sp,
                recommended_value=new_sp,
                unit="Pa",
                savings_pct=savings,
                reason=f"Fan speed at {avg_fan:.0f}% — reduce static pressure by {reduction:.0f} Pa",
            ))

    return recommendations


def _evaluate_chw_optimization(
    classified: dict[str, list[dict[str, Any]]],
    target: OptimizationTarget,
) -> list[SetpointRecommendation]:
    """Evaluate chilled water temperature setpoint optimization."""
    recommendations: list[SetpointRecommendation] = []

    chw_points = classified.get("chilled_water_temp", [])
    cooling_points = classified.get("cooling_output", [])

    for chw_point in chw_points:
        cur_chw = chw_point.get("curVal")
        if not isinstance(cur_chw, (int, float)):
            continue

        point_id = str(chw_point.get("id", ""))
        point_name = str(chw_point.get("dis", point_id))

        avg_cooling = _avg_val(cooling_points, "curVal")

        if avg_cooling is not None and avg_cooling < 60.0 and cur_chw < 10.0:
            # Cooling valves not fully open — can raise CHW temp
            raise_amount = _calc_chw_raise(cur_chw, avg_cooling, target)
            if raise_amount > 0:
                new_chw = round(cur_chw + raise_amount, 1)
                savings = round(raise_amount * 2.5, 1)  # ~2.5% per °C CHW raise
                recommendations.append(SetpointRecommendation(
                    point_id=point_id,
                    point_name=point_name,
                    setpoint_type=SetpointType.CHILLED_WATER_TEMP,
                    current_value=cur_chw,
                    recommended_value=new_chw,
                    unit="°C",
                    savings_pct=savings,
                    reason=f"Cooling output at {avg_cooling:.0f}% — raise CHW temp by {raise_amount:.1f}°C",
                ))

    return recommendations


def _calc_sat_raise(current_sat: float, cooling_pct: float, target: OptimizationTarget) -> float:
    """Calculate how much to raise SAT based on cooling load and optimization target."""
    headroom = max(0, 50.0 - cooling_pct) / 50.0  # 0..1 scale
    max_raise = 3.0 if target == OptimizationTarget.ENERGY else 1.5
    if target == OptimizationTarget.COMFORT:
        max_raise = 0.5
    raise_amount = round(headroom * max_raise, 1)
    # Don't raise above 16°C for cooling mode
    raise_amount = min(raise_amount, max(0, 16.0 - current_sat))
    return raise_amount


def _calc_chw_raise(current_chw: float, cooling_pct: float, target: OptimizationTarget) -> float:
    """Calculate how much to raise CHW temp based on cooling load."""
    headroom = max(0, 60.0 - cooling_pct) / 60.0
    max_raise = 2.0 if target == OptimizationTarget.ENERGY else 1.0
    if target == OptimizationTarget.COMFORT:
        max_raise = 0.5
    raise_amount = round(headroom * max_raise, 1)
    # Don't raise above 10°C
    raise_amount = min(raise_amount, max(0, 10.0 - current_chw))
    return raise_amount


def _avg_val(points: list[dict[str, Any]], key: str) -> float | None:
    """Compute average of a numeric field across points."""
    vals = [p[key] for p in points if isinstance(p.get(key), (int, float))]
    return sum(vals) / len(vals) if vals else None


def _estimate_daily_savings(
    recommendations: list[SetpointRecommendation],
    load_profile: LoadProfile,
    base_power_kw: float | None,
) -> float:
    """Estimate daily kWh savings from the recommendations."""
    if not recommendations:
        return 0.0

    total_savings_pct = sum(r.savings_pct for r in recommendations)
    # Clamp to reasonable range
    total_savings_pct = max(min(total_savings_pct, 30.0), -10.0)

    if base_power_kw is not None and base_power_kw > 0:
        # Use actual power reading
        daily_kwh = base_power_kw * 24 * (load_profile.avg_load_pct / 100.0)
        return round(daily_kwh * total_savings_pct / 100.0, 1)

    # Fallback: estimate from load profile
    estimated_kwh = load_profile.avg_load_pct * 2.4  # rough baseline
    return round(estimated_kwh * total_savings_pct / 100.0, 1)


def _generate_warnings(
    classified: dict[str, list[dict[str, Any]]],
    recommendations: list[SetpointRecommendation],
) -> list[str]:
    """Generate safety and quality warnings for the optimization result."""
    warnings: list[str] = []

    # Check for extreme outdoor temperature
    oat_points = classified.get("outdoor_temp", [])
    for p in oat_points:
        cur_val = p.get("curVal")
        if isinstance(cur_val, (int, float)):
            if cur_val > 38.0:
                warnings.append("Extreme outdoor temperature detected — optimization may be limited")
            elif cur_val < -10.0:
                warnings.append("Very cold outdoor conditions — heating optimizations may be limited")

    # Check if any recommendation exceeds comfort limits
    for rec in recommendations:
        if rec.setpoint_type == SetpointType.SUPPLY_AIR_TEMP and rec.recommended_value > 15.5:
            warnings.append(f"SAT recommendation ({rec.recommended_value}°C) is near upper comfort limit")
        if rec.setpoint_type == SetpointType.CHILLED_WATER_TEMP and rec.recommended_value > 9.5:
            warnings.append(f"CHW recommendation ({rec.recommended_value}°C) is near upper limit")

    return warnings


# ── Energy Optimization Engine ──


class OptimizationEngine(BaseEngine):
    """Energy optimization engine.

    Analyzes equipment operating data, identifies energy-saving opportunities,
    and generates optimized PID setpoint recommendations.

    Input payload keys:
        - equip_id (str): Equipment ref
        - equip_name (str): Equipment display name
        - target (str): Optimization target — "energy", "comfort", or "balanced"
        - grid (dict): Normalized point data with curVal/hisAvg/hisMin/hisMax
    """

    @property
    def name(self) -> str:
        return "energy"

    @property
    def description(self) -> str:
        return "Energy prediction and dynamic PID setpoint optimization"

    @property
    def actions(self) -> set[str]:
        return {"optimize"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"EnergyOptEngine does not support action: {action}")

        return self._optimize(payload)

    def _optimize(self, payload: dict[str, Any]) -> EngineResult:
        """Run energy optimization on the provided equipment data."""
        equip_id = str(payload.get("equip_id", ""))
        equip_name = str(payload.get("equip_name", equip_id or "Equipment"))
        target_str = str(payload.get("target", "balanced"))

        try:
            target = OptimizationTarget(target_str)
        except ValueError:
            target = OptimizationTarget.BALANCED

        # Extract point data from grid
        grid_data = payload.get("grid", {})
        point_data: list[dict[str, Any]]
        if isinstance(grid_data, dict):
            point_data = grid_data.get("rows", [])
        elif isinstance(grid_data, list):
            point_data = grid_data
        else:
            point_data = []

        # Classify points by type
        classified = self._classify_points(point_data)

        # Analyze load profile
        load_profile = _analyze_load_profile(classified)

        # Generate setpoint recommendations
        recommendations: list[SetpointRecommendation] = []
        recommendations.extend(_evaluate_sat_optimization(classified, target))
        recommendations.extend(_evaluate_static_pressure_optimization(classified, target))
        recommendations.extend(_evaluate_chw_optimization(classified, target))

        # Estimate savings
        base_power = _avg_val(classified.get("power", []), "curVal")
        total_savings_pct = sum(r.savings_pct for r in recommendations)
        total_savings_pct = max(min(total_savings_pct, 30.0), -10.0)
        daily_savings_kwh = _estimate_daily_savings(recommendations, load_profile, base_power)

        # Warnings
        warnings = _generate_warnings(classified, recommendations)

        # Confidence: based on data quality and recommendation count
        confidence = self._compute_confidence(point_data, classified, recommendations)

        # Build explanation
        if recommendations:
            rec_summary = "; ".join(
                f"{r.point_name}: {r.current_value} → {r.recommended_value} {r.unit}"
                for r in recommendations
            )
            explanation = (
                f"Energy optimization for {equip_name} (target: {target.value}). "
                f"Load profile: avg {load_profile.avg_load_pct}%, peak {load_profile.peak_load_pct}%, "
                f"trend {load_profile.load_trend}. "
                f"Recommendations: {rec_summary}. "
                f"Estimated savings: {total_savings_pct:.1f}% ({daily_savings_kwh:.1f} kWh/day)."
            )
        else:
            explanation = (
                f"Energy optimization for {equip_name}: no actionable setpoint adjustments found. "
                f"Equipment appears to be operating near optimal for current conditions."
            )

        result = OptimizationResult(
            target=target,
            equipment_id=equip_id,
            equipment_name=equip_name,
            load_profile=load_profile,
            setpoint_recommendations=recommendations,
            estimated_savings_pct=round(total_savings_pct, 1),
            estimated_savings_kwh=daily_savings_kwh,
            confidence=round(confidence, 2),
            explanation=explanation,
            warnings=warnings,
        )

        return EngineResult(
            status="ok",
            confidence=result.confidence,
            message=result.explanation,
            data=result.model_dump(),
        )

    @staticmethod
    def _classify_points(point_data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Classify all points into categories based on their names."""
        classified: dict[str, list[dict[str, Any]]] = {}
        for point in point_data:
            name = str(point.get("dis", point.get("id", "")))
            category = _classify_point(name)
            if category is not None:
                classified.setdefault(category, []).append(point)
        return classified

    @staticmethod
    def _compute_confidence(
        point_data: list[dict[str, Any]],
        classified: dict[str, list[dict[str, Any]]],
        recommendations: list[SetpointRecommendation],
    ) -> float:
        """Compute confidence score based on data quality."""
        if not point_data:
            return 0.0

        # Base confidence from data coverage
        total_points = len(point_data)
        classified_count = sum(len(v) for v in classified.values())
        coverage = classified_count / total_points if total_points > 0 else 0

        # History data availability
        has_history = sum(1 for p in point_data if p.get("hisAvg") is not None)
        history_ratio = has_history / total_points if total_points > 0 else 0

        # More recommendations with diverse types = higher confidence
        rec_types = {r.setpoint_type for r in recommendations}

        base = 0.4
        base += coverage * 0.25      # Up to +0.25 for point classification
        base += history_ratio * 0.2  # Up to +0.20 for history coverage
        base += min(len(rec_types) * 0.05, 0.15)  # Up to +0.15 for rec diversity

        return min(round(base, 2), 0.95)


# Backward-compatible alias
EnergyOptEngine = OptimizationEngine
