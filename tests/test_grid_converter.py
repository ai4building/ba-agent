"""Tests for GridConverter — Grid ↔ Python data conversion."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from baAgentPy.utils.grid_converter import MARKER, GridConverter


@pytest.fixture
def converter() -> GridConverter:
    return GridConverter()


# ── normalize_dataframe ──


class TestNormalizeDataframe:
    def test_basic_conversion(self, converter: GridConverter) -> None:
        df = pd.DataFrame({
            "id": ["@p:1", "@p:2"],
            "dis": ["Zone Temp", "Supply Temp"],
            "curVal": [72.5, 55.0],
        })
        result = converter.normalize_dataframe(df)

        assert result["columns"] == ["id", "dis", "curVal"]
        assert len(result["rows"]) == 2
        assert result["rows"][0]["id"] == "@p:1"
        assert result["rows"][0]["curVal"] == 72.5

    def test_nan_replaced_with_none(self, converter: GridConverter) -> None:
        df = pd.DataFrame({
            "id": ["@p:1"],
            "curVal": [float("nan")],
        })
        result = converter.normalize_dataframe(df)
        assert result["rows"][0]["curVal"] is None

    def test_numpy_types_converted(self, converter: GridConverter) -> None:
        df = pd.DataFrame({
            "count": np.array([42], dtype=np.int64),
            "temp": np.array([72.5], dtype=np.float64),
            "active": np.array([True], dtype=np.bool_),
        })
        result = converter.normalize_dataframe(df)
        row = result["rows"][0]

        assert isinstance(row["count"], int)
        assert isinstance(row["temp"], float)
        assert isinstance(row["active"], bool)

    def test_empty_dataframe(self, converter: GridConverter) -> None:
        df = pd.DataFrame()
        result = converter.normalize_dataframe(df)
        assert result["columns"] == []
        assert result["rows"] == []

    def test_attrs_extracted_as_meta(self, converter: GridConverter) -> None:
        df = pd.DataFrame({"id": ["@p:1"]})
        df.attrs["ver"] = "3.0"
        result = converter.normalize_dataframe(df)
        assert result["meta"]["ver"] == "3.0"


# ── response_to_grid_dict ──


class TestResponseToGridDict:
    def test_success_response(self, converter: GridConverter) -> None:
        from baAgentPy.main import ServiceResponse

        resp = ServiceResponse(
            ok=True,
            action="diagnose",
            result={"status": "ok", "confidence": 0.95},
        )
        out = converter.response_to_grid_dict(resp)

        assert out["ok"] is True
        assert out["action"] == "diagnose"
        assert "error" not in out
        assert out["r_status"] == "ok"
        assert out["r_confidence"] == 0.95

    def test_error_response(self, converter: GridConverter) -> None:
        from baAgentPy.main import ServiceResponse

        resp = ServiceResponse(
            ok=False,
            action="optimize",
            error="Service unavailable",
        )
        out = converter.response_to_grid_dict(resp)

        assert out["ok"] is False
        assert out["error"] == "Service unavailable"


# ── rows_to_grid_dicts ──


class TestRowsToGridDicts:
    def test_basic_rows(self, converter: GridConverter) -> None:
        rows = [
            {"id": "@p:1", "score": 95},
            {"id": "@p:2", "score": 72},
        ]
        result = converter.rows_to_grid_dicts(rows)
        assert len(result) == 2
        assert result[0]["score"] == 95

    def test_numpy_values_in_rows(self, converter: GridConverter) -> None:
        rows = [{"val": np.float64(3.14)}]
        result = converter.rows_to_grid_dicts(rows)
        assert isinstance(result[0]["val"], float)


# ── Haystack type helpers ──


class TestHaystackTypeHelpers:
    def test_is_marker_checkmark(self) -> None:
        assert GridConverter.is_marker(MARKER) is True

    def test_is_marker_true(self) -> None:
        assert GridConverter.is_marker(True) is True

    def test_is_marker_false(self) -> None:
        assert GridConverter.is_marker(False) is False
        assert GridConverter.is_marker("other") is False

    def test_parse_ref_at_prefix(self) -> None:
        assert GridConverter.parse_ref("@p:abc123") == "p:abc123"

    def test_parse_ref_r_prefix(self) -> None:
        assert GridConverter.parse_ref("r:abc123") == "abc123"

    def test_parse_ref_not_a_ref(self) -> None:
        assert GridConverter.parse_ref("hello") is None
        assert GridConverter.parse_ref(42) is None

    def test_parse_number_unit_plain_float(self) -> None:
        val, unit = GridConverter.parse_number_unit(72.5)
        assert val == 72.5
        assert unit is None

    def test_parse_number_unit_with_unit(self) -> None:
        val, unit = GridConverter.parse_number_unit("n:72.5 °F")
        assert val == 72.5
        assert unit == "°F"

    def test_parse_number_unit_no_unit(self) -> None:
        val, unit = GridConverter.parse_number_unit("n:42")
        assert val == 42.0
        assert unit is None
