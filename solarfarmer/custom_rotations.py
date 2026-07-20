"""Import custom tracker rotation schedules from SolarFarmer CSV files.

CSV files use separate timestamp columns followed by one column per tracker
rotation ID::

    Year,Month,Day,Hour,Minute,Second,Tracker0,Tracker1
    2025,1,1,8,0,0,-1.5,-1.5

The ``Second`` column is optional. ``Azimuth`` and ``Zenith`` columns from
older SolarFarmer exports are ignored. Rotation values are decimal degrees and
are converted to the integer centidegrees required by the protobuf format.
"""

from __future__ import annotations

import csv
import json
import math
import warnings
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models.energy_calculation_inputs import EnergyCalculationInputs
from .models.trackers_conditions_dataset import TrackerCondition, TrackersConditionsDataset

__all__ = [
    "RotationSignConventionWarning",
    "check_compatible_time_resolutions",
    "check_weather_covers_rotation_period",
    "csv_to_protobuf",
    "from_csv",
    "validate_tracker_rotation_ids",
]


_REQUIRED_TIMESTAMP_COLUMNS = ("year", "month", "day", "hour", "minute")
_OPTIONAL_TIMESTAMP_COLUMNS = {"second"}
_IGNORED_COLUMNS = {"azimuth", "zenith"}
_MAX_ROTATION_CENTIDEGREES = 8990


class RotationSignConventionWarning(UserWarning):
    """Warn when a CSV appears to use the opposite tracker angle convention."""


def from_csv(
    path: str | Path,
    *,
    offset_from_utc: float = 0.0,
    rotations_are_at_middle_of_period: bool = False,
    flip_sign: bool = False,
    energy_calculation_inputs: EnergyCalculationInputs | Mapping[str, Any] | Path | str | None = None,
) -> TrackersConditionsDataset:
    """Read a custom tracker rotation CSV file into a validated dataset.

    Parameters
    ----------
    path : str or Path
        CSV file with ``Year, Month, Day, Hour, Minute[, Second]`` columns
        followed by one or more tracker rotation columns. Header matching is
        case-insensitive; legacy ``Azimuth`` and ``Zenith`` columns are ignored.
    offset_from_utc : float, default 0.0
        Fixed UTC offset in hours used for all CSV timestamps. Fixed offsets do
        not apply daylight-saving time.
    rotations_are_at_middle_of_period : bool, default False
        Whether each rotation value represents the middle rather than the start
        of its period.
    flip_sign : bool, default False
        Negate all input angles before conversion. Use when a schedule uses
        positive morning and negative afternoon rotations.
    energy_calculation_inputs : EnergyCalculationInputs, mapping, or path, optional
        Parsed calculation inputs, a mapping using either API camel-case or
        Python snake-case keys, or a path to a JSON file containing the
        calculation inputs. Used to verify that CSV tracker rotation IDs
        match the plant's tracker IDs.

    Returns
    -------
    TrackersConditionsDataset
        Dataset ready for :meth:`TrackersConditionsDataset.to_protobuf_file`.

    Raises
    ------
    ValueError
        If headers, timestamps, rotation values, or the inferred time cadence
        are invalid.
    """
    tz = _timezone_from_offset(offset_from_utc)
    csv_path = Path(path)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        tracker_ids = _parse_headers(reader.fieldnames)
        rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV must contain at least two timestamped data rows to infer a period")

    conditions: list[TrackerCondition] = []
    timestamps: list[datetime] = []
    morning_values: list[float] = []
    afternoon_values: list[float] = []

    for line_number, row in enumerate(rows, start=2):
        if None in row:
            raise ValueError(f"row {line_number} contains more values than its header")
        if all(value is None or not value.strip() for value in row.values()):
            continue

        timestamp = _parse_timestamp(row, line_number, tz)
        rotations = [
            _parse_rotation(row[tracker_id], line_number, tracker_id, flip_sign)
            for tracker_id in tracker_ids
        ]
        timestamps.append(timestamp)
        if timestamp.hour < 12:
            morning_values.extend(rotations)
        else:
            afternoon_values.extend(rotations)
        conditions.append(
            TrackerCondition(
                period_in_minutes=1.0,
                start_of_period=timestamp,
                tracker_rotations_array_values=[_to_centidegrees(value) for value in rotations],
            )
        )

    if len(conditions) < 2:
        raise ValueError("CSV must contain at least two non-empty data rows to infer a period")

    period_in_minutes = _infer_period_in_minutes(timestamps)
    conditions = [
        condition.model_copy(update={"period_in_minutes": period_in_minutes})
        for condition in conditions
    ]

    if not flip_sign and _uses_opposite_sign_convention(morning_values, afternoon_values):
        warnings.warn(
            "Rotation angles appear positive in the morning and negative in the afternoon. "
            "SolarFarmer expects negative morning and positive afternoon rotations; "
            "pass flip_sign=True to reverse the schedule.",
            RotationSignConventionWarning,
            stacklevel=2,
        )

    dataset = TrackersConditionsDataset(
        data=conditions,
        offset_from_utc=offset_from_utc,
        rotations_are_at_middle_of_period=rotations_are_at_middle_of_period,
        tracker_rotation_ids=tracker_ids,
    )
    if energy_calculation_inputs is not None:
        validate_tracker_rotation_ids(dataset, energy_calculation_inputs)
    return dataset


def csv_to_protobuf(
    csv_path: str | Path,
    output_path: str | Path,
    max_timesteps_per_file: int = 40_000,
    **kwargs: Any,
) -> TrackersConditionsDataset:
    """Convert a custom rotations CSV file directly to a protobuf gzip file.

    Parameters
    ----------
    csv_path : str or Path
        Source CSV path accepted by :func:`from_csv`.
    output_path : str or Path
        Destination path for the gzip-compressed protobuf output. When the
        dataset contains more than *max_timesteps_per_file* timesteps this
        path is used as the base name and multiple files are written with the
        ``{part:03d}of{total:03d}`` suffix (e.g.
        ``TrackersConditionsDatasetDto_Protobuf001of002.gz``).
    max_timesteps_per_file : int, default 40_000
        Maximum timesteps per protobuf file. Passed to
        :meth:`TrackersConditionsDataset.to_protobuf_file`.
    **kwargs
        Keyword arguments accepted by :func:`from_csv`.

    Returns
    -------
    TrackersConditionsDataset
        The validated dataset that was serialized.
    """
    dataset = from_csv(csv_path, **kwargs)
    dataset.to_protobuf_file(output_path, max_timesteps_per_file=max_timesteps_per_file)
    return dataset


def validate_tracker_rotation_ids(
    dataset: TrackersConditionsDataset,
    energy_calculation_inputs: EnergyCalculationInputs | Mapping[str, Any] | Path | str,
) -> None:
    """Validate that dataset rotation IDs match tracker IDs in calculation inputs.

    Comparisons are case-insensitive, but IDs remain unchanged in the dataset.

    Parameters
    ----------
    dataset : TrackersConditionsDataset
        Dataset whose ``tracker_rotation_ids`` are validated.
    energy_calculation_inputs : EnergyCalculationInputs, mapping, or path
        Parsed calculation inputs, a mapping using either API camel-case or
        Python snake-case keys, or a path to a JSON file containing the
        calculation inputs.

    Raises
    ------
    ValueError
        If the payload has no trackers or the two ID sets differ.
    """
    inputs = _coerce_energy_calculation_inputs(energy_calculation_inputs)
    payload_ids = _tracker_rotation_ids_from_inputs(inputs)
    dataset_ids = {
        rotation_id.casefold(): rotation_id for rotation_id in dataset.tracker_rotation_ids
    }

    missing_from_payload = sorted(
        rotation_id for key, rotation_id in dataset_ids.items() if key not in payload_ids
    )
    missing_from_csv = sorted(
        rotation_id for key, rotation_id in payload_ids.items() if key not in dataset_ids
    )
    if missing_from_payload or missing_from_csv:
        details: list[str] = []
        if missing_from_payload:
            details.append(f"CSV IDs not found in calculation inputs: {missing_from_payload}")
        if missing_from_csv:
            details.append(f"calculation-input IDs missing from CSV: {missing_from_csv}")
        raise ValueError("Tracker rotation IDs do not match: " + "; ".join(details))

def check_weather_covers_rotation_period(
    weather_timestamps: Sequence[datetime],
    dataset: TrackersConditionsDataset,
) -> None:
    """Verify that weather timestamps span the full rotation dataset period.

    The tracker rotation timestamps define the simulation period. If weather
    data does not cover the full rotation period, the simulation will be
    truncated to the overlapping window.

    Weather and rotation timestamps must use the same reference time (both
    timezone-aware with the same UTC offset, or both timezone-naive).

    Parameters
    ----------
    weather_timestamps : Sequence[datetime]
        Timestamps from the weather file, in any order.
    dataset : TrackersConditionsDataset
        Rotation dataset whose first and last timestamps define the simulation
        window.

    Raises
    ------
    ValueError
        If *weather_timestamps* is empty or does not fully cover the rotation
        period.
    """
    if not dataset.data:
        return

    rotation_start = dataset.data[0].start_of_period
    rotation_end = dataset.data[-1].start_of_period

    if not weather_timestamps:
        raise ValueError(
            f"weather_timestamps is empty; cannot verify coverage of rotation period "
            f"{rotation_start} \u2013 {rotation_end}"
        )

    weather_start = min(weather_timestamps)
    weather_end = max(weather_timestamps)

    errors: list[str] = []
    if weather_start > rotation_start:
        errors.append(
            f"weather starts at {weather_start} which is after "
            f"the first rotation timestamp {rotation_start}"
        )
    if weather_end < rotation_end:
        errors.append(
            f"weather ends at {weather_end} which is before "
            f"the last rotation timestamp {rotation_end}"
        )
    if errors:
        raise ValueError(
            "Weather data does not fully cover the rotation period: " + "; ".join(errors)
        )


def check_compatible_time_resolutions(
    weather_timestamps: Sequence[datetime],
    dataset: TrackersConditionsDataset,
) -> None:
    """Verify that the weather and rotation time resolutions are compatible.

    Compatible means one period is a whole multiple of the other (e.g. hourly
    weather with 5-minute rotations, or both at the same resolution). When the
    resolutions differ, SolarFarmer interpolates the coarser dataset to match
    the finer one.

    Parameters
    ----------
    weather_timestamps : Sequence[datetime]
        Timestamps from the weather file, in ascending order. At least two
        timestamps are required to infer the period. When using a pandas
        DataFrame, pass ``df.index.to_pydatetime()``.
    dataset : TrackersConditionsDataset
        Rotation dataset whose ``period_in_minutes`` is checked against the
        inferred weather period.

    Raises
    ------
    ValueError
        If fewer than two weather timestamps are supplied, the weather
        timestamps are not strictly increasing, or the resolutions are not
        compatible.
    """
    if not dataset.data:
        return

    if len(weather_timestamps) < 2:
        raise ValueError(
            "at least two weather timestamps are required to infer the resolution"
        )

    sorted_ts = sorted(weather_timestamps)
    weather_deltas_s = [
        int((later - earlier).total_seconds())
        for earlier, later in zip(sorted_ts, sorted_ts[1:], strict=False)
    ]
    weather_period_s = min(weather_deltas_s)
    if weather_period_s <= 0:
        raise ValueError("weather timestamps must be strictly increasing")

    rotation_period_s = round(dataset.data[0].period_in_minutes * 60)

    longer = max(weather_period_s, rotation_period_s)
    shorter = min(weather_period_s, rotation_period_s)

    if longer % shorter != 0:
        weather_min = weather_period_s / 60
        rotation_min = dataset.data[0].period_in_minutes
        raise ValueError(
            f"Incompatible time resolutions: weather period is {weather_min:g} min, "
            f"rotation period is {rotation_min:g} min. "
            "One must be a whole multiple of the other."
        )

def _parse_headers(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        raise ValueError("CSV must contain a header row")

    normalized_headers: dict[str, str] = {}
    for header in fieldnames:
        if header is None or not header.strip():
            raise ValueError("CSV contains an empty column header")
        cleaned = header.strip()
        normalized = cleaned.casefold()
        if normalized in normalized_headers:
            raise ValueError(
                f"CSV contains duplicate case-insensitive headers: "
                f"'{normalized_headers[normalized]}' and '{cleaned}'"
            )
        normalized_headers[normalized] = cleaned

    missing = [
        name.title() for name in _REQUIRED_TIMESTAMP_COLUMNS if name not in normalized_headers
    ]
    if missing:
        raise ValueError(f"CSV is missing required timestamp columns: {missing}")

    excluded = {
        *_REQUIRED_TIMESTAMP_COLUMNS,
        *_OPTIONAL_TIMESTAMP_COLUMNS,
        *_IGNORED_COLUMNS,
    }
    tracker_ids = [
        header.strip() for header in fieldnames if header.strip().casefold() not in excluded
    ]
    if not tracker_ids:
        raise ValueError("CSV must contain at least one tracker rotation column")
    return tracker_ids


def _parse_timestamp(row: Mapping[str, str | None], line_number: int, tz: timezone) -> datetime:
    normalized = {key.strip().casefold(): value for key, value in row.items() if key is not None}
    parts: dict[str, int] = {}
    for name in _REQUIRED_TIMESTAMP_COLUMNS:
        parts[name] = _parse_integer(normalized.get(name), line_number, name.title())
    parts["second"] = _parse_integer(normalized.get("second", "0"), line_number, "Second")
    try:
        return datetime(tzinfo=tz, **parts)
    except ValueError as exc:
        raise ValueError(f"row {line_number} has an invalid timestamp: {exc}") from None


def _parse_integer(value: str | None, line_number: int, column: str) -> int:
    if value is None or not value.strip():
        raise ValueError(f"row {line_number}, column '{column}' must be an integer")
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"row {line_number}, column '{column}' must be an integer") from None


def _parse_rotation(value: str | None, line_number: int, tracker_id: str, flip_sign: bool) -> float:
    if value is None or not value.strip():
        raise ValueError(f"row {line_number}, tracker '{tracker_id}' must have a rotation value")
    try:
        rotation = float(value)
    except ValueError:
        raise ValueError(
            f"row {line_number}, tracker '{tracker_id}' rotation must be numeric"
        ) from None
    if not math.isfinite(rotation):
        raise ValueError(f"row {line_number}, tracker '{tracker_id}' rotation must be finite")
    if flip_sign:
        rotation = -rotation
    if abs(rotation) > _MAX_ROTATION_CENTIDEGREES / 100:
        raise ValueError(
            f"row {line_number}, tracker '{tracker_id}' rotation must be in [-89.90, 89.90] degrees"
        )
    return rotation


def _to_centidegrees(rotation: float) -> int:
    try:
        return int((Decimal(str(rotation)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        raise ValueError("rotation cannot be represented as centidegrees") from None


def _infer_period_in_minutes(timestamps: list[datetime]) -> float:
    deltas = [
        int((later - earlier).total_seconds())
        for earlier, later in zip(timestamps, timestamps[1:], strict=False)
    ]
    if any(delta <= 0 for delta in deltas):
        raise ValueError("CSV timestamps must be strictly increasing without duplicates")

    cadence_seconds = min(deltas)
    if any(delta % cadence_seconds for delta in deltas):
        raise ValueError(
            "CSV timestamps must use a consistent cadence; larger daytime-only gaps must be "
            "whole multiples of the inferred period"
        )
    return cadence_seconds / 60


def _timezone_from_offset(offset_from_utc: float) -> timezone:
    if not math.isfinite(offset_from_utc) or not -12 <= offset_from_utc <= 14:
        raise ValueError("offset_from_utc must be a finite value in the range [-12, 14]")
    return timezone(timedelta(hours=offset_from_utc))


def _uses_opposite_sign_convention(
    morning_values: list[float], afternoon_values: list[float]
) -> bool:
    morning_nonzero = [value for value in morning_values if value != 0]
    afternoon_nonzero = [value for value in afternoon_values if value != 0]
    if not morning_nonzero or not afternoon_nonzero:
        return False

    morning_positive = sum(value > 0 for value in morning_nonzero) / len(morning_nonzero)
    afternoon_negative = sum(value < 0 for value in afternoon_nonzero) / len(afternoon_nonzero)
    return morning_positive >= 0.75 and afternoon_negative >= 0.75


def _coerce_energy_calculation_inputs(
    energy_calculation_inputs: EnergyCalculationInputs | Mapping[str, Any] | Path | str,
) -> EnergyCalculationInputs | Mapping[str, Any]:
    """Load calculation inputs from a JSON file path if needed.

    If *energy_calculation_inputs* is a :class:`~pathlib.Path` or :class:`str`,
    it is treated as a path to a JSON file and parsed into a mapping.
    Otherwise the value is returned unchanged.
    """
    if isinstance(energy_calculation_inputs, (str, Path)):
        path = Path(energy_calculation_inputs)
        try:
            data: Mapping[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValueError(
                f"Could not read energy_calculation_inputs from '{path}': {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse '{path}' as JSON: {exc}") from exc
        if not isinstance(data, Mapping):
            raise ValueError(
                f"Expected a JSON object in '{path}', got {type(data).__name__}"
            )
        return data
    return energy_calculation_inputs


def _tracker_rotation_ids_from_inputs(
    energy_calculation_inputs: EnergyCalculationInputs | Mapping[str, Any],
) -> dict[str, str]:
    if isinstance(energy_calculation_inputs, EnergyCalculationInputs):
        trackers = energy_calculation_inputs.pv_plant.trackers or []
        ids = [tracker.tracker_rotation_id for tracker in trackers]
    else:
        plant = energy_calculation_inputs.get("pvPlant") or energy_calculation_inputs.get(
            "pv_plant"
        )
        if not isinstance(plant, Mapping):
            raise ValueError("calculation inputs must contain a pvPlant/pv_plant mapping")
        trackers = plant.get("trackers") or []
        if not isinstance(trackers, list):
            raise ValueError("calculation inputs pvPlant.trackers must be a list")
        ids = []
        for index, tracker in enumerate(trackers):
            if not isinstance(tracker, Mapping):
                raise ValueError(f"calculation inputs tracker {index} must be a mapping")
            rotation_id = tracker.get("trackerRotationID") or tracker.get("tracker_rotation_id")
            if not isinstance(rotation_id, str) or not rotation_id.strip():
                raise ValueError(
                    f"calculation inputs tracker {index} must define trackerRotationID/tracker_rotation_id"
                )
            ids.append(rotation_id)

    if not ids:
        raise ValueError("calculation inputs do not define any tracker rotation IDs")
    normalized_ids: dict[str, str] = {}
    for rotation_id in ids:
        normalized = rotation_id.casefold()
        normalized_ids.setdefault(normalized, rotation_id)
    return normalized_ids
