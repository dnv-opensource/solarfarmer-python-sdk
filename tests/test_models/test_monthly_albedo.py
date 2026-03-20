import json

import pytest
from pydantic import ValidationError

from solarfarmer.models import MonthlyAlbedo


class TestMonthlyAlbedoValidation:
    def test_valid_12_values(self) -> None:
        albedo = MonthlyAlbedo(values=[0.2] * 12)
        assert len(albedo.values) == 12

    def test_wrong_length(self) -> None:
        with pytest.raises(ValidationError):
            MonthlyAlbedo(values=[0.2] * 6)

    def test_value_below_zero(self) -> None:
        values = [0.2] * 11 + [-0.1]
        with pytest.raises(ValidationError, match="between 0 and 1"):
            MonthlyAlbedo(values=values)

    def test_value_above_one(self) -> None:
        values = [0.2] * 11 + [1.5]
        with pytest.raises(ValidationError, match="between 0 and 1"):
            MonthlyAlbedo(values=values)

    def test_empty_list(self) -> None:
        with pytest.raises(ValidationError):
            MonthlyAlbedo(values=[])

    def test_from_list_factory(self) -> None:
        albedo = MonthlyAlbedo.from_list([0.3] * 12)
        assert albedo.values == [0.3] * 12


class TestMonthlyAlbedoSerialization:
    """MonthlyAlbedo serializes as a bare list, not an object."""

    def test_model_dump_is_list(self) -> None:
        albedo = MonthlyAlbedo(values=[0.2] * 12)
        result = albedo.model_dump()
        assert isinstance(result, list)
        assert len(result) == 12

    def test_model_dump_json_is_array(self) -> None:
        albedo = MonthlyAlbedo(values=[0.2] * 12)
        json_str = albedo.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert parsed == [0.2] * 12

    def test_round_trip_via_list(self) -> None:
        original = MonthlyAlbedo(
            values=[0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
        )
        dumped = original.model_dump()
        rebuilt = MonthlyAlbedo.from_list(dumped)
        assert rebuilt == original
