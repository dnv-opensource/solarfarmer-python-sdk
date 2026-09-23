"""Tests for TrackersConditionsDataset protobuf serialization / deserialization."""

from __future__ import annotations

import gzip
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from solarfarmer.models.trackers_conditions_dataset import (  # noqa: PLC2701
    TrackerCondition,
    TrackersConditionsDataset,
    _datetime_to_dotnet_ticks,
    _dotnet_ticks_to_datetime,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_dataset(
    n: int = 3,
    *,
    use_array: bool = False,
    tz_offset_hours: float = 0.0,
) -> TrackersConditionsDataset:
    """Build a small TrackersConditionsDataset for testing."""
    tz = timezone(timedelta(hours=tz_offset_hours))
    rotation_ids = [f"ID_{i}" for i in range(3)]

    data = []
    for i in range(n):
        start = datetime(2020, 1, 1, i, 0, 0, tzinfo=tz)
        if use_array:
            data.append(
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=start,
                    tracker_rotations_array_values=[-1570 + i * 100, 0, 200 - i * 50],
                )
            )
        else:
            data.append(
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=start,
                    tracker_rotation_unique_value=i * 100 - 100,  # -100, 0, 100
                )
            )

    return TrackersConditionsDataset(
        data=data,
        offset_from_utc=tz_offset_hours,
        rotations_are_at_middle_of_period=False,
        tracker_rotation_ids=rotation_ids,
    )


# ---------------------------------------------------------------------------
# datetime ↔ .NET ticks conversion
# ---------------------------------------------------------------------------


class TestDotnetTicksConversion:
    def test_utc_roundtrip(self) -> None:
        dt = datetime(2020, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        item1, item2 = _datetime_to_dotnet_ticks(dt)
        result = _dotnet_ticks_to_datetime(item1, item2)
        assert result == dt

    def test_positive_offset_roundtrip(self) -> None:
        tz = timezone(timedelta(hours=5, minutes=30))  # India Standard Time
        dt = datetime(2021, 3, 14, 9, 0, 0, tzinfo=tz)
        item1, item2 = _datetime_to_dotnet_ticks(dt)
        result = _dotnet_ticks_to_datetime(item1, item2)
        assert result == dt

    def test_negative_offset_roundtrip(self) -> None:
        tz = timezone(timedelta(hours=-5))  # UTC-5
        dt = datetime(2022, 12, 31, 23, 59, 59, tzinfo=tz)
        item1, item2 = _datetime_to_dotnet_ticks(dt)
        result = _dotnet_ticks_to_datetime(item1, item2)
        assert result == dt

    def test_naive_datetime_treated_as_utc(self) -> None:
        naive = datetime(2020, 1, 1, 0, 0, 0)
        item1, item2 = _datetime_to_dotnet_ticks(naive)
        assert item2 == 0  # UTC offset = 0
        result = _dotnet_ticks_to_datetime(item1, item2)
        assert result == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_zero_offset_item2(self) -> None:
        _, item2 = _datetime_to_dotnet_ticks(datetime(2020, 1, 1, tzinfo=timezone.utc))
        assert item2 == 0

    def test_one_hour_offset_item2(self) -> None:
        tz = timezone(timedelta(hours=1))
        _, item2 = _datetime_to_dotnet_ticks(datetime(2020, 1, 1, tzinfo=tz))
        assert item2 == 36_000_000_000  # 1h in 100-ns ticks


# ---------------------------------------------------------------------------
# Protobuf round-trip via bytes
# ---------------------------------------------------------------------------


class TestProtobufRoundTrip:
    def test_unique_value_roundtrip(self) -> None:
        ds = _make_dataset(n=4, use_array=False)
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            loaded = TrackersConditionsDataset.from_protobuf_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)

        assert loaded.offset_from_utc == ds.offset_from_utc
        assert loaded.rotations_are_at_middle_of_period == ds.rotations_are_at_middle_of_period
        assert loaded.tracker_rotation_ids == ds.tracker_rotation_ids
        assert len(loaded.data) == len(ds.data)
        for orig, back in zip(ds.data, loaded.data, strict=True):
            assert back.period_in_minutes == orig.period_in_minutes
            assert back.start_of_period == orig.start_of_period
            assert back.tracker_rotation_unique_value == orig.tracker_rotation_unique_value
            assert back.tracker_rotations_array_values == []

    def test_array_values_roundtrip(self) -> None:
        ds = _make_dataset(n=3, use_array=True)
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            loaded = TrackersConditionsDataset.from_protobuf_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)

        for orig, back in zip(ds.data, loaded.data, strict=True):
            assert back.tracker_rotations_array_values == orig.tracker_rotations_array_values
            assert back.tracker_rotation_unique_value is None

    def test_null_vs_zero_unique_value_preserved(self) -> None:
        """NullableShortWrapper presence tracking must survive the wire round-trip."""
        ds = TrackersConditionsDataset(
            data=[
                TrackerCondition(
                    period_in_minutes=60.0,
                    start_of_period=datetime(2020, 1, 1, 0, tzinfo=timezone.utc),
                    tracker_rotation_unique_value=0,  # explicitly zero — must survive
                ),
                TrackerCondition(
                    period_in_minutes=60.0,
                    start_of_period=datetime(2020, 1, 1, 1, tzinfo=timezone.utc),
                    # unique_value absent → null
                ),
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            loaded = TrackersConditionsDataset.from_protobuf_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)

        assert loaded.data[0].tracker_rotation_unique_value == 0  # zero preserved
        assert loaded.data[1].tracker_rotation_unique_value is None  # null preserved

    def test_offset_from_utc_preserved(self) -> None:
        ds = _make_dataset(n=2, tz_offset_hours=5.5)
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            loaded = TrackersConditionsDataset.from_protobuf_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        assert loaded.offset_from_utc == pytest.approx(5.5)

    def test_rotations_are_at_middle_of_period_preserved(self) -> None:
        ds = TrackersConditionsDataset(
            data=[
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=datetime(2020, 1, 1, tzinfo=timezone.utc),
                    tracker_rotation_unique_value=100,
                )
            ],
            rotations_are_at_middle_of_period=True,
        )
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            loaded = TrackersConditionsDataset.from_protobuf_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        assert loaded.rotations_are_at_middle_of_period is True


# ---------------------------------------------------------------------------
# from_protobuf_files — multi-file merge
# ---------------------------------------------------------------------------


class TestFromProtobufFiles:
    def test_multi_file_combines_records(self) -> None:
        ds_a = _make_dataset(n=2, use_array=False)
        tz = timezone.utc
        ds_b = TrackersConditionsDataset(
            data=[
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=datetime(2020, 1, 1, 10, tzinfo=tz),
                    tracker_rotation_unique_value=500,
                )
            ],
            offset_from_utc=0.0,
            tracker_rotation_ids=ds_a.tracker_rotation_ids,
        )

        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "a.gz"
            p_b = Path(td) / "b.gz"
            ds_a.to_protobuf_file(p_a)
            ds_b.to_protobuf_file(p_b)

            merged = TrackersConditionsDataset.from_protobuf_files([p_a, p_b])

        assert len(merged.data) == len(ds_a.data) + len(ds_b.data)
        assert merged.offset_from_utc == ds_a.offset_from_utc
        assert merged.tracker_rotation_ids == ds_a.tracker_rotation_ids

    def test_empty_paths_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one path"):
            TrackersConditionsDataset.from_protobuf_files([])


# ---------------------------------------------------------------------------
# from_protobuf_dir — auto-discovery
# ---------------------------------------------------------------------------


class TestFromProtobufDir:
    def test_single_file_discovered(self) -> None:
        ds = _make_dataset(n=2)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "TrackersConditionsDatasetDto_Protobuf.gz"
            ds.to_protobuf_file(p)
            loaded = TrackersConditionsDataset.from_protobuf_dir(td)
        assert len(loaded.data) == len(ds.data)

    def test_multi_part_files_discovered_in_order(self) -> None:
        tz = timezone.utc
        ds1 = TrackersConditionsDataset(
            data=[
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=datetime(2020, 1, 1, 0, tzinfo=tz),
                    tracker_rotation_unique_value=100,
                )
            ]
        )
        ds2 = TrackersConditionsDataset(
            data=[
                TrackerCondition(
                    period_in_minutes=30.0,
                    start_of_period=datetime(2020, 1, 1, 1, tzinfo=tz),
                    tracker_rotation_unique_value=200,
                )
            ]
        )
        with tempfile.TemporaryDirectory() as td:
            # Write in reverse order to ensure sorting by part number works
            ds2.to_protobuf_file(Path(td) / "TrackersConditionsDatasetDto_Protobuf002of002.gz")
            ds1.to_protobuf_file(Path(td) / "TrackersConditionsDatasetDto_Protobuf001of002.gz")
            loaded = TrackersConditionsDataset.from_protobuf_dir(td)

        assert len(loaded.data) == 2
        assert loaded.data[0].tracker_rotation_unique_value == 100
        assert loaded.data[1].tracker_rotation_unique_value == 200

    def test_missing_files_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError, match="TrackersConditionsDatasetDto"):
                TrackersConditionsDataset.from_protobuf_dir(td)

    def test_output_file_is_valid_gzip(self) -> None:
        ds = _make_dataset(n=1)
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
            tmp = Path(f.name)
        try:
            ds.to_protobuf_file(tmp)
            with gzip.open(tmp, "rb") as fh:
                raw = fh.read()
            assert len(raw) > 0
        finally:
            tmp.unlink(missing_ok=True)
