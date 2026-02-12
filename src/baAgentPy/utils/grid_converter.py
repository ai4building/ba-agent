"""Grid ↔ Python data conversion utilities.

hxPy automatically marshals Haystack Grid ↔ pandas DataFrame.
This module provides additional helpers for:
- Normalizing DataFrames received from hxPy (cleaning NaN, typing)
- Packaging Python results back into dicts that hxPy converts to Grids
- Handling Haystack-specific semantics (Ref, Number with units, Marker)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from baAgentPy.main import ServiceResponse


# Haystack marker sentinel — hxPy represents Marker tags as this value
MARKER = "\u2713"  # ✓


class GridConverter:
    """Converts between hxPy DataFrames and BA-Agent internal formats."""

    # ── DataFrame → internal dict ──

    def normalize_dataframe(self, df: pd.DataFrame) -> dict[str, Any]:
        """Normalize a DataFrame received from hxPy into a clean dict.

        Replaces NaN with None, converts numpy types to Python natives,
        and extracts column metadata.

        Args:
            df: DataFrame auto-converted from Haystack Grid by hxPy.

        Returns:
            Dict with 'columns', 'rows', and 'meta' keys.
        """
        columns = list(df.columns)
        rows = _dataframe_to_rows(df)
        meta: dict[str, Any] = {}

        # Extract DataFrame attrs if hxPy attached Grid meta
        if hasattr(df, "attrs") and df.attrs:
            meta = {str(k): _to_python_native(v) for k, v in df.attrs.items()}

        return {"columns": columns, "rows": rows, "meta": meta}

    # ── Internal dict → hxPy-compatible return ──

    def response_to_grid_dict(self, response: ServiceResponse) -> dict[str, Any]:
        """Convert a ServiceResponse to a dict that hxPy returns as a Grid.

        hxPy converts Python dicts to single-row Grids. For multi-row results,
        the 'result' field can contain a list of dicts (each becomes a Grid row).

        Args:
            response: The ServiceResponse to convert.

        Returns:
            Dict with flat keys suitable for hxPy Grid conversion.
        """
        out: dict[str, Any] = {
            "ok": response.ok,
            "action": response.action,
        }

        if response.error is not None:
            out["error"] = response.error

        # Flatten result into top-level keys with 'r_' prefix to avoid collision
        for key, value in response.result.items():
            out[f"r_{key}"] = _serialize_value(value)

        return out

    def rows_to_grid_dicts(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert a list of result rows into hxPy-compatible dicts.

        Each dict in the list becomes a row in the returned Grid.

        Args:
            rows: List of row dicts.

        Returns:
            List of dicts with values serialized for hxPy.
        """
        return [{k: _serialize_value(v) for k, v in row.items()} for row in rows]

    # ── Haystack type helpers ──

    @staticmethod
    def is_marker(value: Any) -> bool:
        """Check if a value represents a Haystack Marker."""
        return value == MARKER or value is True

    @staticmethod
    def parse_ref(value: Any) -> str | None:
        """Extract the ID string from a Haystack Ref value.

        hxPy represents Refs as strings like '@p:abc123' or 'r:abc123'.

        Args:
            value: The value to parse.

        Returns:
            The ref ID string, or None if not a ref.
        """
        if not isinstance(value, str):
            return None
        if value.startswith(("@", "r:")):
            return value.lstrip("@").removeprefix("r:")
        return None

    @staticmethod
    def parse_number_unit(value: Any) -> tuple[float, str | None]:
        """Parse a Haystack Number with unit.

        hxPy may represent these as 'n:72.5 °F' or plain float.

        Args:
            value: The value to parse.

        Returns:
            Tuple of (numeric_value, unit_string_or_None).
        """
        if isinstance(value, (int, float)):
            return float(value), None
        if isinstance(value, str) and value.startswith("n:"):
            parts = value[2:].split(" ", 1)
            num = float(parts[0])
            unit = parts[1] if len(parts) > 1 else None
            return num, unit
        return float(value), None


# ── Module-level helpers ──

def _dataframe_to_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame to list of dicts, replacing NaN with None."""
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        clean_row: dict[str, Any] = {
            str(col): _to_python_native(val)
            for col, val in row.items()
        }
        rows.append(clean_row)
    return rows


def _to_python_native(value: Any) -> Any:
    """Convert numpy/pandas types to Python native types."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def _serialize_value(value: Any) -> Any:
    """Serialize a Python value for hxPy Grid return."""
    if isinstance(value, dict):
        return str(value)
    if isinstance(value, list):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return str(_dataframe_to_rows(value))
    return _to_python_native(value)
