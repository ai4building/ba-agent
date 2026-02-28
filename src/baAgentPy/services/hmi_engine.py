"""HMI auto-generation — automated UI/logic layout from device topology.

Handles:
    - hmi: generate HMI layout JSON from device topology

Design (from DESIGN.md §3.3 & §Phase 6):
    - Equipment type classification → template selection
    - Widget placement on a grid-based canvas
    - Data bindings: map equipment points to appropriate widget types
    - Page/navigation structure for multi-equipment facilities
    - Rule-based engine (Phase 6); AI-assisted layout refinement in later phase
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from baAgentPy.services.base import BaseEngine, EngineResult


# ── Data Models ──


class EquipType(str, Enum):
    """Equipment type classification for template selection."""
    AHU = "ahu"
    VAV = "vav"
    CHILLER = "chiller"
    BOILER = "boiler"
    FCU = "fcu"
    PUMP = "pump"
    COOLING_TOWER = "cooling_tower"
    GENERIC = "generic"


class WidgetType(str, Enum):
    """HMI widget types."""
    GAUGE = "gauge"                 # Circular gauge for analog values
    TREND = "trend"                 # Time-series trend chart
    STATUS = "status"               # On/off status indicator
    SETPOINT = "setpoint"           # Editable setpoint control
    ALARM_BADGE = "alarm_badge"     # Alarm indicator with count
    LABEL = "label"                 # Static text label
    VALVE_GRAPHIC = "valve_graphic" # Valve position graphic
    FAN_GRAPHIC = "fan_graphic"     # Fan speed/status graphic


class Widget(BaseModel):
    """A single HMI widget in the layout."""
    widget_id: str
    widget_type: WidgetType
    label: str
    x: int = Field(description="Grid column position (0-based)")
    y: int = Field(description="Grid row position (0-based)")
    width: int = Field(default=1, description="Grid columns spanned")
    height: int = Field(default=1, description="Grid rows spanned")
    binding: WidgetBinding | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class WidgetBinding(BaseModel):
    """Data binding for a widget."""
    point_id: str = Field(description="Haystack point ref")
    point_name: str = Field(default="")
    property: str = Field(default="curVal", description="Point property to display")
    writable: bool = Field(default=False, description="Whether the widget can write to this point")


class HmiPage(BaseModel):
    """A single page in the HMI layout."""
    page_id: str
    title: str
    equip_id: str = Field(default="")
    equip_type: EquipType = EquipType.GENERIC
    widgets: list[Widget] = Field(default_factory=list)
    grid_columns: int = Field(default=4, description="Number of columns in the layout grid")
    grid_rows: int = Field(default=6, description="Number of rows in the layout grid")


class HmiLayout(BaseModel):
    """Complete HMI layout output."""
    pages: list[HmiPage] = Field(default_factory=list)
    navigation: list[dict[str, str]] = Field(default_factory=list, description="Nav links between pages")
    total_widgets: int = 0
    total_pages: int = 0
    summary: str = Field(default="")


# ── Equipment Classification ──


def _classify_equip(name: str, points: list[dict[str, Any]]) -> EquipType:
    """Classify equipment type from its name and point names."""
    name_lower = name.lower()

    if any(kw in name_lower for kw in ["ahu", "air handling", "空调机组", "空调箱"]):
        return EquipType.AHU
    if any(kw in name_lower for kw in ["vav", "变风量"]):
        return EquipType.VAV
    if any(kw in name_lower for kw in ["chiller", "冷机", "冷水机"]):
        return EquipType.CHILLER
    if any(kw in name_lower for kw in ["boiler", "锅炉"]):
        return EquipType.BOILER
    if any(kw in name_lower for kw in ["fcu", "fan coil", "风机盘管"]):
        return EquipType.FCU
    if any(kw in name_lower for kw in ["pump", "水泵"]):
        return EquipType.PUMP
    if any(kw in name_lower for kw in ["cooling tower", "冷却塔"]):
        return EquipType.COOLING_TOWER

    # Infer from point names
    point_names = " ".join(str(p.get("dis", "")) for p in points).lower()
    if "supply air" in point_names or "return air" in point_names or "fan speed" in point_names:
        return EquipType.AHU
    if "damper" in point_names and "airflow" in point_names:
        return EquipType.VAV
    if "chw" in point_names or "condenser" in point_names:
        return EquipType.CHILLER

    return EquipType.GENERIC


# ── Point-to-Widget Mapping ──


def _classify_point_widget(name: str, cur_val: Any) -> tuple[WidgetType, dict[str, Any]]:
    """Determine the best widget type for a given point based on its name and value."""
    name_lower = name.lower()

    # Temperature points → gauge
    if any(kw in name_lower for kw in ["temp", "温度"]):
        is_setpoint = any(kw in name_lower for kw in ["setpoint", "sp", "设定"])
        if is_setpoint:
            return WidgetType.SETPOINT, {"min": 5, "max": 35, "unit": "°C"}
        return WidgetType.GAUGE, {"min": -10, "max": 50, "unit": "°C"}

    # Valve positions → valve graphic
    if any(kw in name_lower for kw in ["valve", "vlv", "阀"]):
        return WidgetType.VALVE_GRAPHIC, {"min": 0, "max": 100, "unit": "%"}

    # Status/command → status indicator (checked before fan/pump to handle "Fan Status")
    if any(kw in name_lower for kw in ["status", "enable", "run", "cmd", "alarm", "状态", "运行"]):
        return WidgetType.STATUS, {}

    # Fan/pump speed → fan graphic
    if any(kw in name_lower for kw in ["fan", "pump", "speed", "vfd", "风机", "水泵"]):
        return WidgetType.FAN_GRAPHIC, {"min": 0, "max": 100, "unit": "%"}

    # Damper → valve graphic (similar behavior)
    if any(kw in name_lower for kw in ["damper", "风阀"]):
        return WidgetType.VALVE_GRAPHIC, {"min": 0, "max": 100, "unit": "%"}

    # Pressure → gauge
    if any(kw in name_lower for kw in ["press", "压力"]):
        return WidgetType.GAUGE, {"min": 0, "max": 2000, "unit": "Pa"}

    # Flow → gauge
    if any(kw in name_lower for kw in ["flow", "cfm", "风量"]):
        return WidgetType.GAUGE, {"min": 0, "max": 5000, "unit": "CFM"}

    # Humidity → gauge
    if any(kw in name_lower for kw in ["humid", "rh", "湿度"]):
        return WidgetType.GAUGE, {"min": 0, "max": 100, "unit": "%RH"}

    # CO2 → gauge
    if any(kw in name_lower for kw in ["co2", "二氧化碳"]):
        return WidgetType.GAUGE, {"min": 0, "max": 5000, "unit": "ppm"}

    # Power/energy → gauge
    if any(kw in name_lower for kw in ["power", "kw", "energy", "功率"]):
        return WidgetType.GAUGE, {"min": 0, "max": 500, "unit": "kW"}

    # Default → gauge
    if isinstance(cur_val, (int, float)):
        return WidgetType.GAUGE, {"unit": ""}

    return WidgetType.LABEL, {}


# ── Layout Generation ──


def _generate_page(
    equip_id: str,
    equip_name: str,
    equip_type: EquipType,
    points: list[dict[str, Any]],
    page_index: int,
) -> HmiPage:
    """Generate an HMI page for a single equipment."""
    widgets: list[Widget] = []
    col = 0
    row = 0
    grid_cols = 4

    # Title label at top
    widgets.append(Widget(
        widget_id=f"w_{page_index}_title",
        widget_type=WidgetType.LABEL,
        label=equip_name,
        x=0, y=0, width=grid_cols, height=1,
        config={"font_size": 18, "style": "header"},
    ))
    row = 1

    # Alarm badge
    widgets.append(Widget(
        widget_id=f"w_{page_index}_alarm",
        widget_type=WidgetType.ALARM_BADGE,
        label="Alarms",
        x=grid_cols - 1, y=0, width=1, height=1,
        config={"equip_ref": equip_id},
    ))

    # Generate widgets for each point
    for i, point in enumerate(points):
        point_id = str(point.get("id", ""))
        point_name = str(point.get("dis", point_id))
        cur_val = point.get("curVal")

        widget_type, config = _classify_point_widget(point_name, cur_val)

        # Determine if writable
        writable = widget_type == WidgetType.SETPOINT

        binding = WidgetBinding(
            point_id=point_id,
            point_name=point_name,
            property="curVal",
            writable=writable,
        )

        # Calculate grid position
        widget_width = 2 if widget_type == WidgetType.TREND else 1
        if col + widget_width > grid_cols:
            col = 0
            row += 1

        widgets.append(Widget(
            widget_id=f"w_{page_index}_{i}",
            widget_type=widget_type,
            label=_short_label(point_name, equip_name),
            x=col,
            y=row,
            width=widget_width,
            height=1,
            binding=binding,
            config=config,
        ))

        col += widget_width
        if col >= grid_cols:
            col = 0
            row += 1

    # Add a trend widget for key points (temperature sensors)
    key_points = [p for p in points if any(kw in str(p.get("dis", "")).lower()
                  for kw in ["temp", "温度"])]
    if key_points:
        if col > 0:
            col = 0
            row += 1
        trend_bindings = [
            {"point_id": str(p.get("id", "")), "point_name": str(p.get("dis", ""))}
            for p in key_points[:4]  # Max 4 traces
        ]
        widgets.append(Widget(
            widget_id=f"w_{page_index}_trend",
            widget_type=WidgetType.TREND,
            label="Temperature Trends",
            x=0, y=row, width=grid_cols, height=2,
            config={"traces": trend_bindings, "range": "past24h"},
        ))
        row += 2

    return HmiPage(
        page_id=f"page_{page_index}",
        title=equip_name,
        equip_id=equip_id,
        equip_type=equip_type,
        widgets=widgets,
        grid_columns=grid_cols,
        grid_rows=row + 1,
    )


def _short_label(point_name: str, equip_name: str) -> str:
    """Create a short widget label by removing the equipment name prefix."""
    # Remove equip name from point name for brevity
    label = point_name
    for prefix in [equip_name, equip_name.split("-")[0] if "-" in equip_name else ""]:
        if prefix and label.lower().startswith(prefix.lower()):
            label = label[len(prefix):].lstrip(" -_")
    return label or point_name


# ── HMI Engine ──


class HmiLayoutEngine(BaseEngine):
    """HMI auto-generation engine.

    Takes device topology as input and generates HMI layout JSON,
    including widget placement, data bindings, and navigation structure.

    Input payload keys:
        - equipment (list[dict]): List of equipment with their points.
          Each entry: {"equip_id": str, "equip_name": str, "points": list[dict]}
          Points have: {"id": str, "dis": str, "curVal": Any, ...}
        - grid (dict): Alternative — flat point data grid (auto-grouped by equipRef)
    """

    @property
    def name(self) -> str:
        return "hmi"

    @property
    def description(self) -> str:
        return "Automated HMI layout generation from device topology"

    @property
    def actions(self) -> set[str]:
        return {"hmi"}

    def execute(self, action: str, payload: dict[str, Any]) -> EngineResult:
        if not self.can_handle(action):
            raise ValueError(f"HmiEngine does not support action: {action}")

        return self._generate_hmi(payload)

    def _generate_hmi(self, payload: dict[str, Any]) -> EngineResult:
        """Generate HMI layout from equipment topology."""
        # Extract equipment list
        equipment_list = self._extract_equipment(payload)

        if not equipment_list:
            layout = HmiLayout(summary="No equipment data provided for HMI generation.")
            return EngineResult(
                status="ok",
                confidence=0.0,
                message=layout.summary,
                data=layout.model_dump(),
            )

        # Generate pages
        pages: list[HmiPage] = []
        for i, equip in enumerate(equipment_list):
            equip_id = equip.get("equip_id", "")
            equip_name = equip.get("equip_name", equip_id or f"Equipment-{i + 1}")
            points = equip.get("points", [])
            equip_type = _classify_equip(equip_name, points)

            page = _generate_page(equip_id, equip_name, equip_type, points, i)
            pages.append(page)

        # Build navigation
        navigation = [
            {"page_id": p.page_id, "title": p.title, "equip_type": p.equip_type.value}
            for p in pages
        ]

        total_widgets = sum(len(p.widgets) for p in pages)
        total_pages = len(pages)

        equip_types = {p.equip_type.value for p in pages}
        summary = (
            f"Generated HMI layout: {total_pages} page(s), {total_widgets} widget(s). "
            f"Equipment types: {', '.join(sorted(equip_types))}."
        )

        layout = HmiLayout(
            pages=pages,
            navigation=navigation,
            total_widgets=total_widgets,
            total_pages=total_pages,
            summary=summary,
        )

        # Confidence based on data quality
        confidence = self._compute_confidence(equipment_list, total_widgets)

        return EngineResult(
            status="ok",
            confidence=confidence,
            message=layout.summary,
            data=layout.model_dump(),
        )

    @staticmethod
    def _extract_equipment(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract equipment list from payload (structured or grid-based)."""
        # Direct equipment list
        if "equipment" in payload:
            equip = payload["equipment"]
            if isinstance(equip, list):
                return equip

        # Grid-based: group points by equipRef
        grid_data = payload.get("grid", {})
        point_data: list[dict[str, Any]]
        if isinstance(grid_data, dict):
            point_data = grid_data.get("rows", [])
        elif isinstance(grid_data, list):
            point_data = grid_data
        else:
            return []

        if not point_data:
            return []

        # Group by equipRef
        groups: dict[str, list[dict[str, Any]]] = {}
        for point in point_data:
            equip_ref = str(point.get("equipRef", point.get("equip_id", "default")))
            groups.setdefault(equip_ref, []).append(point)

        return [
            {
                "equip_id": equip_ref,
                "equip_name": equip_ref,
                "points": points,
            }
            for equip_ref, points in groups.items()
        ]

    @staticmethod
    def _compute_confidence(
        equipment_list: list[dict[str, Any]],
        total_widgets: int,
    ) -> float:
        """Compute confidence based on input data quality."""
        if not equipment_list:
            return 0.0

        # More points with proper names = higher confidence
        total_points = sum(len(e.get("points", [])) for e in equipment_list)
        named_points = sum(
            1 for e in equipment_list
            for p in e.get("points", [])
            if p.get("dis")
        )
        name_ratio = named_points / total_points if total_points > 0 else 0

        base = 0.5
        base += name_ratio * 0.3       # Up to +0.30 for named points
        base += min(total_widgets * 0.01, 0.15)  # Up to +0.15 for widget count

        return min(round(base, 2), 0.95)


# Backward-compatible alias
HmiEngine = HmiLayoutEngine
