"""Semantic modeling engine — BACnet/Modbus point name parsing and Haystack 4 tag assignment.

Handles:
    - tag: parse point names and assign Haystack 4 tags
    - model: full modeling pipeline (parse → match → generate AXON script)

Replaces the stub TaggingEngine with a complete implementation:
    - PointNameParser: regex-based BACnet/Modbus point name → semantic tokens
    - HaystackTagMapper: semantic tokens → Haystack 4 tag sets with confidence
    - AxonScriptGenerator: tag assignments → `diff(readById(@id), {tags}).commit` scripts
    - ModelingEngine: orchestrates the pipeline
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class ParsedPoint(BaseModel):
    """Result of parsing a single point name."""
    raw_name: str
    equip_type: str = Field(default="", description="Detected equipment type (e.g., AHU, VAV, FCU)")
    equip_id: str = Field(default="", description="Equipment instance identifier (e.g., AHU-01)")
    point_features: tuple[str, ...] = Field(default_factory=tuple, description="Semantic feature tokens")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TagMatch(BaseModel):
    """Result of mapping semantic features to Haystack 4 tags."""
    tags: dict[str, Any] = Field(default_factory=dict, description="Haystack 4 tag dict")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Match confidence")
    template_name: str = Field(default="", description="Name of the matched template")


class ModeledPoint(BaseModel):
    """A fully modeled point with parsed name, matched tags, and AXON script."""
    point_id: str
    raw_name: str
    parsed: ParsedPoint
    tag_match: TagMatch
    axon_script: str = Field(default="")


class ModelingResult(BaseModel):
    """Complete modeling output for a batch of points."""
    modeled_points: list[ModeledPoint] = Field(default_factory=list)
    total_points: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    avg_confidence: float = 0.0
    axon_batch_script: str = Field(default="")
    summary: str = Field(default="")


# ── Equipment Type Patterns ──

_EQUIP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(AHU|Air.?Hand)", re.IGNORECASE), "AHU"),
    (re.compile(r"(VAV)", re.IGNORECASE), "VAV"),
    (re.compile(r"(FCU|Fan.?Coil)", re.IGNORECASE), "FCU"),
    (re.compile(r"(CHWP|CHW.?Pump|Chilled.?Water.?Pump)", re.IGNORECASE), "CHWP"),
    (re.compile(r"(CWP|Cond.?Water.?Pump)", re.IGNORECASE), "CWP"),
    (re.compile(r"(CT|Cooling.?Tower)", re.IGNORECASE), "CT"),
    (re.compile(r"(Boiler)", re.IGNORECASE), "Boiler"),
    (re.compile(r"(Chiller|CH)", re.IGNORECASE), "Chiller"),
    (re.compile(r"(HWP|Hot.?Water.?Pump)", re.IGNORECASE), "HWP"),
    (re.compile(r"(MAU|Make.?Up.?Air)", re.IGNORECASE), "MAU"),
    (re.compile(r"(RTU|Roof.?Top)", re.IGNORECASE), "RTU"),
    (re.compile(r"(EF|Exhaust.?Fan)", re.IGNORECASE), "EF"),
    (re.compile(r"(SF|Supply.?Fan)", re.IGNORECASE), "SF"),
    (re.compile(r"(RF|Return.?Fan)", re.IGNORECASE), "RF"),
    (re.compile(r"(PAU|Primary.?Air)", re.IGNORECASE), "PAU"),
]

# Equipment ID extraction: matches patterns like AHU-01, VAV_301, FCU.2
_EQUIP_ID_RE = re.compile(
    r"((?:AHU|VAV|FCU|CHWP|CWP|CT|Boiler|Chiller|CH|HWP|MAU|RTU|EF|SF|RF|PAU)"
    r"[-_.]?\d+[A-Za-z]?)",
    re.IGNORECASE,
)


# ── Point Feature Patterns ──

_FEATURE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Temperature
    (re.compile(r"\bSAT\b|Supply.?Air.?Temp", re.IGNORECASE), "supply_air_temp"),
    (re.compile(r"\bRAT\b|Return.?Air.?Temp", re.IGNORECASE), "return_air_temp"),
    (re.compile(r"\bDAT\b|Discharge.?Air.?Temp", re.IGNORECASE), "discharge_air_temp"),
    (re.compile(r"\bMAT\b|Mixed.?Air.?Temp", re.IGNORECASE), "mixed_air_temp"),
    (re.compile(r"\bOAT\b|Outdoor.?Air.?Temp|Outside.?Air.?Temp", re.IGNORECASE), "outdoor_air_temp"),
    (re.compile(r"Zn.?Temp|Zone.?Temp|Room.?Temp|Space.?Temp", re.IGNORECASE), "zone_temp"),
    (re.compile(r"\bCHW.?(?:S|Supply).?T(?:emp)?\b|Chilled.?Water.?Supply.?Temp", re.IGNORECASE), "chw_supply_temp"),
    (re.compile(r"\bCHW.?(?:R|Return).?T(?:emp)?\b|Chilled.?Water.?Return.?Temp", re.IGNORECASE), "chw_return_temp"),
    (re.compile(r"\bHHW.?(?:S|Supply).?T(?:emp)?\b|Hot.?Water.?Supply.?Temp", re.IGNORECASE), "hhw_supply_temp"),
    (re.compile(r"\bHHW.?(?:R|Return).?T(?:emp)?\b|Hot.?Water.?Return.?Temp", re.IGNORECASE), "hhw_return_temp"),
    # Status / Command
    (re.compile(r"\bStatus\b|\bSts\b|Run.?Status", re.IGNORECASE), "status"),
    (re.compile(r"\bCmd\b|\bCommand\b|Start.?Cmd|Enable", re.IGNORECASE), "cmd"),
    (re.compile(r"\bAlarm\b|\bAlm\b|Fault", re.IGNORECASE), "alarm"),
    # Speed / VFD
    (re.compile(r"Fan.?Spd|Fan.?Speed|\bVFD\b|Freq", re.IGNORECASE), "fan_speed"),
    # Valve / Damper
    (re.compile(r"Vlv.?Pos|Valve.?Pos|Cooling.?Vlv|Heating.?Vlv|Clg.?Vlv|Htg.?Vlv", re.IGNORECASE), "valve_pos"),
    (re.compile(r"Damper.?Pos|Dmp.?Pos|\bOA.?Dmp\b", re.IGNORECASE), "damper_pos"),
    # Pressure
    (re.compile(r"Static.?Press|Duct.?Press|\bSP\b(?!.*Temp)", re.IGNORECASE), "static_pressure"),
    (re.compile(r"Diff.?Press|\bDP\b", re.IGNORECASE), "diff_pressure"),
    # Flow
    (re.compile(r"Air.?Flow|\bCFM\b|Flow.?Rate", re.IGNORECASE), "airflow"),
    (re.compile(r"Water.?Flow|\bGPM\b", re.IGNORECASE), "water_flow"),
    # Humidity
    (re.compile(r"Humidity|\bRH\b", re.IGNORECASE), "humidity"),
    # CO2
    (re.compile(r"\bCO2\b", re.IGNORECASE), "co2"),
    # Power / Energy
    (re.compile(r"\bkW\b|Power", re.IGNORECASE), "power"),
    (re.compile(r"\bkWh\b|Energy.?Meter", re.IGNORECASE), "energy"),
    # Setpoint
    (re.compile(r"Setpoint|\bSP\b.*Temp|\bSp\b", re.IGNORECASE), "setpoint"),
]


# ── Haystack 4 Tag Templates ──

# Maps feature key → (marker tags, valued tags)
# marker tags: list of Haystack marker tags to add
# valued tags: dict of tag → value pairs
_HAYSTACK_TEMPLATES: dict[str, tuple[str, list[str], dict[str, str]]] = {
    "supply_air_temp": (
        "Supply Air Temp Sensor",
        ["air", "temp", "sensor", "supply", "discharge", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "return_air_temp": (
        "Return Air Temp Sensor",
        ["air", "temp", "sensor", "return", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "discharge_air_temp": (
        "Discharge Air Temp Sensor",
        ["air", "temp", "sensor", "discharge", "leaving", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "mixed_air_temp": (
        "Mixed Air Temp Sensor",
        ["air", "temp", "sensor", "mixed", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "outdoor_air_temp": (
        "Outside Air Temp Sensor",
        ["air", "temp", "sensor", "outside", "weather", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "zone_temp": (
        "Zone Air Temp Sensor",
        ["air", "temp", "sensor", "zone", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "chw_supply_temp": (
        "CHW Supply Temp Sensor",
        ["chilled", "water", "temp", "sensor", "supply", "leaving", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "chw_return_temp": (
        "CHW Return Temp Sensor",
        ["chilled", "water", "temp", "sensor", "return", "entering", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "hhw_supply_temp": (
        "HHW Supply Temp Sensor",
        ["hot", "water", "temp", "sensor", "supply", "leaving", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "hhw_return_temp": (
        "HHW Return Temp Sensor",
        ["hot", "water", "temp", "sensor", "return", "entering", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
    "status": (
        "Run Status",
        ["run", "sensor", "point"],
        {"kind": "Bool"},
    ),
    "cmd": (
        "Run Command",
        ["run", "cmd", "point"],
        {"kind": "Bool"},
    ),
    "alarm": (
        "Alarm",
        ["alarm", "sensor", "point"],
        {"kind": "Bool"},
    ),
    "fan_speed": (
        "Fan Speed",
        ["fan", "speed", "sensor", "point"],
        {"kind": "Number", "unit": "%"},
    ),
    "valve_pos": (
        "Valve Position",
        ["valve", "cmd", "point"],
        {"kind": "Number", "unit": "%"},
    ),
    "damper_pos": (
        "Damper Position",
        ["damper", "cmd", "point"],
        {"kind": "Number", "unit": "%"},
    ),
    "static_pressure": (
        "Static Pressure Sensor",
        ["air", "pressure", "sensor", "point"],
        {"kind": "Number", "unit": "Pa"},
    ),
    "diff_pressure": (
        "Differential Pressure Sensor",
        ["pressure", "sensor", "point"],
        {"kind": "Number", "unit": "Pa"},
    ),
    "airflow": (
        "Air Flow Sensor",
        ["air", "flow", "sensor", "point"],
        {"kind": "Number", "unit": "m³/h"},
    ),
    "water_flow": (
        "Water Flow Sensor",
        ["water", "flow", "sensor", "point"],
        {"kind": "Number", "unit": "L/s"},
    ),
    "humidity": (
        "Humidity Sensor",
        ["air", "humidity", "sensor", "point"],
        {"kind": "Number", "unit": "%RH"},
    ),
    "co2": (
        "CO2 Sensor",
        ["air", "co2", "sensor", "point"],
        {"kind": "Number", "unit": "ppm"},
    ),
    "power": (
        "Elec Power Sensor",
        ["elec", "power", "sensor", "point"],
        {"kind": "Number", "unit": "kW"},
    ),
    "energy": (
        "Elec Energy Sensor",
        ["elec", "energy", "sensor", "point"],
        {"kind": "Number", "unit": "kWh"},
    ),
    "setpoint": (
        "Temp Setpoint",
        ["temp", "sp", "point"],
        {"kind": "Number", "unit": "°C"},
    ),
}


# ── PointNameParser ──


class PointNameParser:
    """Parse BACnet/Modbus point names into semantic tokens.

    Supports multiple naming conventions:
        - Tridium/Niagara: AHU-01.SAT, AHU-01.FanSpd
        - Siemens: B1_FL12_VAV301_ZnTemp
        - Johnson/Metasys: AHU1:SAT, AHU1/SupplyAirTemp
        - Generic: AHU-01 Supply Air Temp
    """

    @staticmethod
    def parse(name: str) -> ParsedPoint:
        """Parse a point name into semantic components."""
        # Normalize separators for matching
        normalized = name.replace(".", " ").replace("/", " ").replace(":", " ").replace("_", " ")

        # Extract equipment type
        equip_type = ""
        for pattern, etype in _EQUIP_PATTERNS:
            if pattern.search(name):
                equip_type = etype
                break

        # Extract equipment ID
        equip_id = ""
        id_match = _EQUIP_ID_RE.search(name)
        if id_match:
            equip_id = id_match.group(1)

        # Extract point features
        features: list[str] = []
        for pattern, feature in _FEATURE_PATTERNS:
            if pattern.search(normalized) or pattern.search(name):
                features.append(feature)

        # Calculate confidence
        confidence = 0.0
        if equip_type:
            confidence += 0.3
        if features:
            confidence += min(len(features) * 0.3, 0.6)
        if equip_id:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        return ParsedPoint(
            raw_name=name,
            equip_type=equip_type,
            equip_id=equip_id,
            point_features=tuple(features),
            confidence=round(confidence, 2),
        )


# ── HaystackTagMapper ──


class HaystackTagMapper:
    """Map parsed semantic features to Haystack 4 tag sets."""

    @staticmethod
    def match(parsed: ParsedPoint) -> TagMatch:
        """Find the best Haystack 4 tag template for the parsed features."""
        if not parsed.point_features:
            return TagMatch()

        best_template = ""
        best_score = 0.0
        best_tags: dict[str, Any] = {}

        for feature in parsed.point_features:
            template = _HAYSTACK_TEMPLATES.get(feature)
            if template is None:
                continue

            template_name, marker_tags, valued_tags = template

            # Score based on feature specificity
            score = 0.5 + min(len(marker_tags) * 0.05, 0.3)

            # Boost if equipment type is known
            if parsed.equip_type:
                score += 0.1

            score = min(score, 1.0)

            if score > best_score:
                best_score = score
                best_template = template_name
                best_tags = {}
                for tag in marker_tags:
                    best_tags[tag] = True  # Marker tag
                best_tags.update(valued_tags)

                # Add equipment type tag if known
                equip_tag = _equip_type_to_tag(parsed.equip_type)
                if equip_tag:
                    best_tags[equip_tag] = True

        return TagMatch(
            tags=best_tags,
            score=round(best_score, 2),
            template_name=best_template,
        )


def _equip_type_to_tag(equip_type: str) -> str:
    """Convert equipment type to Haystack marker tag."""
    mapping = {
        "AHU": "ahu",
        "VAV": "vav",
        "FCU": "fcu",
        "CHWP": "chilled-water-pump",
        "CWP": "condenser-water-pump",
        "CT": "coolingTower",
        "Boiler": "boiler",
        "Chiller": "chiller",
        "HWP": "hot-water-pump",
        "MAU": "mau",
        "RTU": "rtu",
        "EF": "exhaust-fan",
        "SF": "supply-fan",
        "RF": "return-fan",
        "PAU": "primaryAir",
    }
    return mapping.get(equip_type, "")


# ── AxonScriptGenerator ──


class AxonScriptGenerator:
    """Generate AXON scripts for batch tag assignment."""

    @staticmethod
    def generate_diff(point_id: str, tags: dict[str, Any]) -> str:
        """Generate a single diff().commit AXON statement.

        Example output:
            diff(readById(@p:123), {air, temp, sensor, point, kind:"Number", unit:"°C"}).commit
        """
        if not tags:
            return ""

        tag_parts: list[str] = []
        for key, value in sorted(tags.items()):
            if value is True:
                tag_parts.append(key)
            elif isinstance(value, str):
                tag_parts.append(f'{key}:"{value}"')
            elif isinstance(value, (int, float)):
                tag_parts.append(f"{key}:{value}")

        tags_str = ", ".join(tag_parts)
        return f"diff(readById({point_id}), {{{tags_str}}}).commit"

    @staticmethod
    def generate_batch(assignments: list[tuple[str, dict[str, Any]]]) -> str:
        """Generate a batch AXON script for multiple point tag assignments."""
        lines: list[str] = []
        for point_id, tags in assignments:
            script = AxonScriptGenerator.generate_diff(point_id, tags)
            if script:
                lines.append(script)
        return "\n".join(lines)


# ── ModelingEngine ──


class ModelingEngine(BaseEngine):
    """Semantic modeling engine for EPC engineering deployment.

    Parses BACnet/Modbus point names, matches against Haystack 4 semantic model,
    and generates AXON diff/commit scripts for Folio database population.

    Input payload keys:
        - points (list[dict]): Point records with at least 'id' and 'dis' (display name).
          Optional: 'curVal', 'equipRef', etc.
    """

    def __init__(self) -> None:
        self._parser = PointNameParser()
        self._mapper = HaystackTagMapper()
        self._generator = AxonScriptGenerator()

    @property
    def name(self) -> str:
        return "modeling"

    @property
    def description(self) -> str:
        return "BACnet/Modbus point name parsing and Haystack 4 semantic tag assignment"

    @property
    def actions(self) -> set[str]:
        return {"tag", "model"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"ModelingEngine does not support action: {action}")

        return self._model(payload)

    def _model(self, payload: dict[str, Any]) -> EngineResult:
        """Run the full modeling pipeline on provided points."""
        # Extract points from payload
        points = payload.get("points", [])
        if not isinstance(points, list):
            points = []

        # Also accept grid format
        if not points:
            grid_data = payload.get("grid", {})
            if isinstance(grid_data, dict):
                points = grid_data.get("rows", [])
            elif isinstance(grid_data, list):
                points = grid_data

        if not points:
            return EngineResult(
                status="ok",
                confidence=0.0,
                message="No point data provided for modeling.",
                data=ModelingResult(summary="No point data provided for modeling.").model_dump(),
            )

        # Process each point
        modeled: list[ModeledPoint] = []
        assignments: list[tuple[str, dict[str, Any]]] = []
        matched_count = 0
        total_confidence = 0.0

        for point in points:
            point_id = str(point.get("id", ""))
            point_name = str(point.get("dis", point.get("name", point_id)))

            # Parse
            parsed = self._parser.parse(point_name)

            # Match tags
            tag_match = self._mapper.match(parsed)

            # Generate AXON script
            axon_script = ""
            if tag_match.tags and point_id:
                axon_script = self._generator.generate_diff(point_id, tag_match.tags)
                assignments.append((point_id, tag_match.tags))

            if tag_match.score > 0:
                matched_count += 1

            total_confidence += tag_match.score

            modeled.append(ModeledPoint(
                point_id=point_id,
                raw_name=point_name,
                parsed=parsed,
                tag_match=tag_match,
                axon_script=axon_script,
            ))

        # Build batch script
        batch_script = self._generator.generate_batch(assignments)

        # Summary
        total = len(modeled)
        unmatched = total - matched_count
        avg_conf = total_confidence / total if total > 0 else 0.0

        summary = (
            f"Modeled {total} points: {matched_count} matched, {unmatched} unmatched. "
            f"Average confidence: {avg_conf:.2f}."
        )

        result = ModelingResult(
            modeled_points=modeled,
            total_points=total,
            matched_count=matched_count,
            unmatched_count=unmatched,
            avg_confidence=round(avg_conf, 2),
            axon_batch_script=batch_script,
            summary=summary,
        )

        return EngineResult(
            status="ok",
            confidence=round(avg_conf, 2),
            message=summary,
            data=result.model_dump(),
        )


# Backward-compatible alias
TaggingEngine = ModelingEngine
