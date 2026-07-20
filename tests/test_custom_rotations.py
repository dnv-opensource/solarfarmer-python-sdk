"""Tests for custom tracker rotations CSV parsing and protobuf export."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from solarfarmer.custom_rotations import (
    RotationSignConventionWarning,
    check_compatible_time_resolutions,
    check_weather_covers_rotation_period,
    csv_to_protobuf,
    from_csv,
    from_csv_folder,
    validate_tracker_rotation_ids,
)
from solarfarmer.models import (
    DiffuseModel,
    EnergyCalculationInputs,
    EnergyCalculationOptions,
    Location,
    MonthlyAlbedo,
    PVPlant,
    Tracker,
    TrackerCondition,
    TrackersConditionsDataset,
    Vector3Double,
)


def _write_csv(tmp_path, content: str):
    path = tmp_path / "rotations.csv"
    path.write_text(content, encoding="utf-8")
    return path


def _make_dataset_with_timestamps(
    timestamps: list[datetime], period_minutes: float = 5.0
) -> TrackersConditionsDataset:
    """Create a minimal TrackersConditionsDataset with given timestamps."""
    conditions = [
        TrackerCondition(
            period_in_minutes=period_minutes,
            start_of_period=ts,
            tracker_rotations_array_values=[-100],
        )
        for ts in timestamps
    ]
    return TrackersConditionsDataset(data=conditions, tracker_rotation_ids=["T0"])


class TestFromCsv:
    def test_parses_rotations_and_ignores_legacy_columns(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Second,Azimuth,Zenith,North,South",
                    "2025,4,1,8,0,0,120,45,-1.25,-2.50",
                    "2025,4,1,8,5,0,121,46,-3.50,-4.75",
                    "2025,4,1,8,10,0,122,47,-5.00,-6.25",
                ]
            ),
        )

        dataset = from_csv(
            path,
            offset_from_utc=5.5,
            rotations_are_at_middle_of_period=True,
        )

        assert dataset.tracker_rotation_ids == ["North", "South"]
        assert dataset.offset_from_utc == 5.5
        assert dataset.rotations_are_at_middle_of_period is True
        assert dataset.data[0].start_of_period.tzinfo == timezone(timedelta(hours=5.5))
        assert [condition.period_in_minutes for condition in dataset.data] == [5.0, 5.0, 5.0]
        assert dataset.data[0].tracker_rotations_array_values == [-125, -250]
        assert dataset.data[1].tracker_rotations_array_values == [-350, -475]

    def test_accepts_csv_without_second_column(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Row_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,10,-2",
                ]
            ),
        )

        dataset = from_csv(path)

        assert dataset.data[0].start_of_period.second == 0
        assert dataset.data[0].period_in_minutes == 10.0

    def test_daytime_only_gap_uses_base_period(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,-2",
                    "2025,4,1,17,0,3",
                ]
            ),
        )

        dataset = from_csv(path)

        assert [condition.period_in_minutes for condition in dataset.data] == [5.0, 5.0, 5.0]

    @pytest.mark.parametrize("offset_from_utc", [-12, 14])
    def test_accepts_civil_timezone_boundaries(self, tmp_path, offset_from_utc) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,-2",
                ]
            ),
        )

        dataset = from_csv(path, offset_from_utc=offset_from_utc)

        assert dataset.offset_from_utc == offset_from_utc

    def test_rejects_offset_before_civil_timezone_range(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,-2",
                ]
            ),
        )

        with pytest.raises(ValueError, match=r"\[-12, 14\]"):
            from_csv(path, offset_from_utc=-12.5)

    def test_reversed_sign_warns_and_flip_sign_corrects(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,9,0,15",
                    "2025,4,1,9,5,20",
                    "2025,4,1,13,0,-15",
                    "2025,4,1,13,5,-20",
                ]
            ),
        )

        with pytest.warns(RotationSignConventionWarning, match="flip_sign=True"):
            from_csv(path)

        dataset = from_csv(path, flip_sign=True)
        assert dataset.data[0].tracker_rotations_array_values == [-1500]
        assert dataset.data[-1].tracker_rotations_array_values == [2000]

    @pytest.mark.parametrize(
        ("header", "rows", "match"),
        [
            (
                "Year,Month,Day,Hour,Second,Tracker_A",
                ["2025,4,1,8,0,-1", "2025,4,1,8,5,-2"],
                "required timestamp",
            ),
            (
                "Year,Month,Day,Hour,Minute,Tracker_A,tracker_a",
                ["2025,4,1,8,0,-1,-2", "2025,4,1,8,5,-2,-3"],
                "duplicate case-insensitive",
            ),
            (
                "Year,Month,Day,Hour,Minute,Tracker_A",
                ["2025,4,1,8,0,not-a-number", "2025,4,1,8,5,-2"],
                "must be numeric",
            ),
        ],
    )
    def test_rejects_invalid_csv(self, tmp_path, header, rows, match) -> None:
        path = _write_csv(tmp_path, "\n".join([header, *rows]))

        with pytest.raises(ValueError, match=match):
            from_csv(path)

    def test_rejects_duplicate_timestamps(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,0,-2",
                ]
            ),
        )

        with pytest.raises(ValueError, match="strictly increasing"):
            from_csv(path)

    def test_rejects_decreasing_timestamps(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,5,-1",
                    "2025,4,1,8,0,-2",
                ]
            ),
        )

        with pytest.raises(ValueError, match="strictly increasing"):
            from_csv(path)

    @pytest.mark.parametrize("rotation", [89.90, -89.90])
    def test_allows_rotation_at_boundary(self, tmp_path, rotation) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    f"2025,4,1,8,0,{rotation}",
                    "2025,4,1,8,5,0",
                ]
            ),
        )

        dataset = from_csv(path)

        assert abs(dataset.data[0].tracker_rotations_array_values[0]) == 8990

    @pytest.mark.parametrize("rotation", [89.91, -89.91])
    def test_rejects_rotation_above_boundary(self, tmp_path, rotation) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    f"2025,4,1,8,0,{rotation}",
                    "2025,4,1,8,5,0",
                ]
            ),
        )

        with pytest.raises(ValueError, match=r"\[-89.90, 89.90\]"):
            from_csv(path)


class TestPayloadValidation:
    def test_matches_payload_ids_case_insensitively(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,North,South",
                    "2025,4,1,8,0,-1,-2",
                    "2025,4,1,8,5,-2,-3",
                ]
            ),
        )
        payload = {
            "pvPlant": {
                "trackers": [
                    {"trackerRotationID": "NORTH"},
                    {"trackerRotationID": "south"},
                ]
            }
        }

        dataset = from_csv(path, energy_calculation_inputs=payload)
        validate_tracker_rotation_ids(dataset, payload)

    def test_rejects_payload_id_mismatch(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,North",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,-2",
                ]
            ),
        )
        payload = {"pvPlant": {"trackers": [{"trackerRotationID": "South"}]}}

        with pytest.raises(ValueError, match="do not match"):
            from_csv(path, energy_calculation_inputs=payload)

    def test_accepts_energy_calculation_inputs_model(self, tmp_path) -> None:
        path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Group_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,-2",
                ]
            ),
        )
        point = Vector3Double(x=0, y=0, z=0)
        tracker = Tracker(
            id=1,
            mounting_type_id="mt",
            north_point=point,
            south_point=point,
            tracker_rotation_id="Group_A",
            tracker_system_id="ts",
        )
        inputs = EnergyCalculationInputs(
            location=Location(latitude=0, longitude=0),
            pv_plant=PVPlant(
                transformers=[],
                mounting_type_specifications={},
                trackers=[tracker],
            ),
            monthly_albedo=MonthlyAlbedo(values=[0.2] * 12),
            energy_calculation_options=EnergyCalculationOptions(
                diffuse_model=DiffuseModel.PEREZ,
                include_horizon=False,
            ),
        )

        dataset = from_csv(path, energy_calculation_inputs=inputs)

        assert dataset.tracker_rotation_ids == ["Group_A"]

    def test_accepts_json_file_path(self, tmp_path) -> None:
        csv_path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,North,South",
                    "2025,4,1,8,0,-1,-2",
                    "2025,4,1,8,5,-2,-3",
                ]
            ),
        )
        payload = {
            "pvPlant": {
                "trackers": [
                    {"trackerRotationID": "North"},
                    {"trackerRotationID": "South"},
                ]
            }
        }
        json_path = tmp_path / "inputs.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")

        dataset = from_csv(csv_path, energy_calculation_inputs=json_path)

        assert dataset.tracker_rotation_ids == ["North", "South"]


class TestProtobufExport:
    def test_writes_readable_protobuf(self, tmp_path) -> None:
        csv_path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1.25",
                    "2025,4,1,8,5,2.50",
                ]
            ),
        )
        output_path = tmp_path / "TrackersConditionsDatasetDto_Protobuf.gz"

        dataset = csv_to_protobuf(csv_path, output_path)
        loaded = TrackersConditionsDataset.from_protobuf_file(output_path)

        assert output_path.exists()
        assert loaded == dataset

    def test_single_file_returns_one_path(self, tmp_path) -> None:
        csv_path = _write_csv(
            tmp_path,
            "\n".join(
                [
                    "Year,Month,Day,Hour,Minute,Tracker_A",
                    "2025,4,1,8,0,-1",
                    "2025,4,1,8,5,2",
                ]
            ),
        )
        dataset = from_csv(csv_path)
        output_path = tmp_path / "TrackersConditionsDatasetDto_Protobuf.gz"

        written = dataset.to_protobuf_file(output_path)

        assert written == [output_path]
        assert output_path.exists()

    def test_splits_into_multiple_files_when_limit_exceeded(self, tmp_path) -> None:
        # 5 rows split into files of 2 → 3 files
        rows = [f"2025,4,1,{8 + i // 12},{(i * 5) % 60},{-i}" for i in range(5)]
        csv_path = _write_csv(
            tmp_path,
            "\n".join(["Year,Month,Day,Hour,Minute,Tracker_A", *rows]),
        )
        dataset = from_csv(csv_path)
        output_path = tmp_path / "TrackersConditionsDatasetDto_Protobuf.gz"

        written = dataset.to_protobuf_file(output_path, max_timesteps_per_file=2)

        assert len(written) == 3
        assert written[0].name == "TrackersConditionsDatasetDto_Protobuf001of003.gz"
        assert written[1].name == "TrackersConditionsDatasetDto_Protobuf002of003.gz"
        assert written[2].name == "TrackersConditionsDatasetDto_Protobuf003of003.gz"
        assert all(p.exists() for p in written)

        # round-trip: merge all files and compare to the original dataset
        merged = TrackersConditionsDataset.from_protobuf_files(written)
        assert merged.data == dataset.data
        assert merged.tracker_rotation_ids == dataset.tracker_rotation_ids

    def test_splits_evenly_when_divisible(self, tmp_path) -> None:
        rows = [f"2025,4,1,{8 + i // 12},{(i * 5) % 60},{-i}" for i in range(4)]
        csv_path = _write_csv(
            tmp_path,
            "\n".join(["Year,Month,Day,Hour,Minute,Tracker_A", *rows]),
        )
        dataset = from_csv(csv_path)
        output_path = tmp_path / "TrackersConditionsDatasetDto_Protobuf.gz"

        written = dataset.to_protobuf_file(output_path, max_timesteps_per_file=2)

        assert len(written) == 2
        assert written[0].name == "TrackersConditionsDatasetDto_Protobuf001of002.gz"
        assert written[1].name == "TrackersConditionsDatasetDto_Protobuf002of002.gz"

    def test_rejects_nonpositive_max_timesteps(self, tmp_path) -> None:
        csv_path = _write_csv(
            tmp_path,
            "\n".join(
                ["Year,Month,Day,Hour,Minute,Tracker_A", "2025,4,1,8,0,-1", "2025,4,1,8,5,2"]
            ),
        )
        dataset = from_csv(csv_path)

        with pytest.raises(ValueError, match="greater than 0"):
            dataset.to_protobuf_file(tmp_path / "out.gz", max_timesteps_per_file=0)


class TestWeatherChecks:
    def test_coverage_passes_when_weather_spans_rotation(self) -> None:
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        ts_weather = [datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 1, 23, 55)]
        dataset = _make_dataset_with_timestamps(ts_rotation)

        check_weather_covers_rotation_period(ts_weather, dataset)

    def test_coverage_fails_when_weather_starts_late(self) -> None:
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        ts_weather = [datetime(2025, 1, 1, 8, 5), datetime(2025, 1, 1, 23, 55)]
        dataset = _make_dataset_with_timestamps(ts_rotation)

        with pytest.raises(ValueError, match="starts at"):
            check_weather_covers_rotation_period(ts_weather, dataset)

    def test_coverage_fails_when_weather_ends_early(self) -> None:
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        ts_weather = [datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 1, 8, 0)]
        dataset = _make_dataset_with_timestamps(ts_rotation)

        with pytest.raises(ValueError, match="ends at"):
            check_weather_covers_rotation_period(ts_weather, dataset)

    def test_coverage_passes_for_empty_dataset(self) -> None:
        check_weather_covers_rotation_period([datetime(2025, 1, 1)], TrackersConditionsDataset())

    def test_coverage_raises_for_empty_weather_timestamps(self) -> None:
        dataset = _make_dataset_with_timestamps(
            [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        )

        with pytest.raises(ValueError, match="empty"):
            check_weather_covers_rotation_period([], dataset)

    def test_resolution_passes_for_same_period(self) -> None:
        ts = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        dataset = _make_dataset_with_timestamps(ts, period_minutes=5.0)

        check_compatible_time_resolutions(ts, dataset)

    def test_resolution_passes_for_coarser_weather(self) -> None:
        # 60-minute weather, 5-minute rotation
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        ts_weather = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 9, 0)]
        dataset = _make_dataset_with_timestamps(ts_rotation, period_minutes=5.0)

        check_compatible_time_resolutions(ts_weather, dataset)

    def test_resolution_passes_for_finer_weather(self) -> None:
        # 5-minute weather, 60-minute rotation
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 9, 0)]
        ts_weather = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        dataset = _make_dataset_with_timestamps(ts_rotation, period_minutes=60.0)

        check_compatible_time_resolutions(ts_weather, dataset)

    def test_resolution_fails_for_incompatible_periods(self) -> None:
        # 7-minute weather, 5-minute rotation → not a whole multiple
        ts_rotation = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        ts_weather = [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 7)]
        dataset = _make_dataset_with_timestamps(ts_rotation, period_minutes=5.0)

        with pytest.raises(ValueError, match="Incompatible"):
            check_compatible_time_resolutions(ts_weather, dataset)

    def test_resolution_passes_for_empty_dataset(self) -> None:
        ts_weather = [datetime(2025, 1, 1), datetime(2025, 1, 1, 0, 5)]

        check_compatible_time_resolutions(ts_weather, TrackersConditionsDataset())

    def test_resolution_raises_for_insufficient_weather_timestamps(self) -> None:
        dataset = _make_dataset_with_timestamps(
            [datetime(2025, 1, 1, 8, 0), datetime(2025, 1, 1, 8, 5)]
        )

        with pytest.raises(ValueError, match="at least two"):
            check_compatible_time_resolutions([datetime(2025, 1, 1)], dataset)


class TestFromCsvFolder:
    """from_csv_folder merges multiple CSV files from a directory."""

    _JAN = "\n".join(
        [
            "Year,Month,Day,Hour,Minute,T0,T1",
            "2025,1,1,8,0,-1.0,-2.0",
            "2025,1,1,8,5,-1.5,-2.5",
            "2025,1,1,8,10,-2.0,-3.0",
        ]
    )
    _FEB = "\n".join(
        [
            "Year,Month,Day,Hour,Minute,T0,T1",
            "2025,2,1,8,0,-3.0,-4.0",
            "2025,2,1,8,5,-3.5,-4.5",
            "2025,2,1,8,10,-4.0,-5.0",
        ]
    )

    def test_merges_two_files(self, tmp_path) -> None:
        (tmp_path / "jan.csv").write_text(self._JAN, encoding="utf-8")
        (tmp_path / "feb.csv").write_text(self._FEB, encoding="utf-8")

        dataset = from_csv_folder(tmp_path)

        assert len(dataset.data) == 6
        assert dataset.tracker_rotation_ids == ["T0", "T1"]

    def test_files_sorted_chronologically_not_by_name(self, tmp_path) -> None:
        # Name the February file so it sorts alphabetically before January.
        (tmp_path / "aaa_feb.csv").write_text(self._FEB, encoding="utf-8")
        (tmp_path / "zzz_jan.csv").write_text(self._JAN, encoding="utf-8")

        dataset = from_csv_folder(tmp_path)

        # January data must come first regardless of filename order.
        first_ts = dataset.data[0].start_of_period
        assert first_ts == datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)
        assert len(dataset.data) == 6

    def test_single_file_folder(self, tmp_path) -> None:
        (tmp_path / "only.csv").write_text(self._JAN, encoding="utf-8")

        dataset = from_csv_folder(tmp_path)

        assert len(dataset.data) == 3

    def test_empty_folder_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="No CSV files found"):
            from_csv_folder(tmp_path)

    def test_mismatched_tracker_ids_raises(self, tmp_path) -> None:
        different_ids = "\n".join(
            [
                "Year,Month,Day,Hour,Minute,T0,T9",
                "2025,2,1,8,0,-3.0,-4.0",
                "2025,2,1,8,5,-3.5,-4.5",
            ]
        )
        (tmp_path / "jan.csv").write_text(self._JAN, encoding="utf-8")
        (tmp_path / "feb.csv").write_text(different_ids, encoding="utf-8")

        with pytest.raises(ValueError, match="different tracker-ID columns"):
            from_csv_folder(tmp_path)

    def test_mismatched_column_order_raises(self, tmp_path) -> None:
        reversed_order = "\n".join(
            [
                "Year,Month,Day,Hour,Minute,T1,T0",
                "2025,2,1,8,0,-3.0,-4.0",
                "2025,2,1,8,5,-3.5,-4.5",
            ]
        )
        (tmp_path / "jan.csv").write_text(self._JAN, encoding="utf-8")
        (tmp_path / "feb.csv").write_text(reversed_order, encoding="utf-8")

        with pytest.raises(ValueError, match="different tracker-ID columns"):
            from_csv_folder(tmp_path)

    def test_overlapping_timestamps_raises(self, tmp_path) -> None:
        overlap = "\n".join(
            [
                "Year,Month,Day,Hour,Minute,T0,T1",
                # Starts at the same timestamp as the last row of _JAN.
                "2025,1,1,8,10,-3.0,-4.0",
                "2025,1,1,8,15,-3.5,-4.5",
            ]
        )
        (tmp_path / "jan.csv").write_text(self._JAN, encoding="utf-8")
        (tmp_path / "overlap.csv").write_text(overlap, encoding="utf-8")

        with pytest.raises(ValueError, match="overlap"):
            from_csv_folder(tmp_path)

    def test_kwargs_forwarded(self, tmp_path) -> None:
        (tmp_path / "jan.csv").write_text(self._JAN, encoding="utf-8")
        (tmp_path / "feb.csv").write_text(self._FEB, encoding="utf-8")

        dataset = from_csv_folder(tmp_path, flip_sign=True)

        # All centidegree values should be positive (signs flipped).
        for condition in dataset.data:
            for value in condition.tracker_rotations_array_values:
                assert value > 0
