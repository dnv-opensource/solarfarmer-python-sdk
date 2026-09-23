from __future__ import annotations

import gzip
import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from ._base import SolarFarmerBaseModel

# ---------------------------------------------------------------------------
# Protobuf / .NET conversion helpers
# ---------------------------------------------------------------------------

# Number of 100-ns ticks that elapsed from .NET epoch (0001-01-01T00:00:00)
# to the Unix epoch (1970-01-01T00:00:00 UTC).
_DOTNET_EPOCH_TICKS: int = 621_355_968_000_000_000

# File naming patterns for protobuf gzip files:
#   single : TrackersConditionsDatasetDto_Protobuf.gz
#   multi  : TrackersConditionsDatasetDto_Protobuf001of003.gz
_PROTO_SINGLE_RE = re.compile(
    r"^TrackersConditionsDatasetDto_Protobuf\.gz$",
    re.IGNORECASE,
)
_PROTO_MULTI_RE = re.compile(
    r"^TrackersConditionsDatasetDto_Protobuf(\d+)of(\d+)\.gz$",
    re.IGNORECASE,
)


def _dotnet_ticks_to_datetime(item1: int, item2: int) -> datetime:
    """Convert a .NET ``DateTimeOffset`` encoded as ticks to a Python datetime.

    Parameters
    ----------
    item1 : int
        Local DateTime ticks (100-ns intervals since 0001-01-01T00:00:00).
    item2 : int
        UTC-offset ticks (100-ns intervals; positive = east of Greenwich).

    Returns
    -------
    datetime
        Timezone-aware Python :class:`~datetime.datetime`.
    """
    tz = timezone(timedelta(microseconds=item2 // 10))
    local_us = (item1 - _DOTNET_EPOCH_TICKS) // 10
    return datetime(1970, 1, 1, tzinfo=tz) + timedelta(microseconds=local_us)


def _datetime_to_dotnet_ticks(dt: datetime) -> tuple[int, int]:
    """Convert a Python datetime to a .NET ``DateTimeOffset`` ticks pair.

    Parameters
    ----------
    dt : datetime
        Timezone-aware or naive datetime. Naive datetimes are treated as UTC.

    Returns
    -------
    tuple[int, int]
        ``(item1, item2)`` where *item1* is local DateTime ticks and *item2*
        is the UTC-offset in 100-ns ticks.
    """
    utc_offset: timedelta = (
        (dt.utcoffset() or timedelta(0)) if dt.tzinfo is not None else timedelta(0)
    )
    item2 = int(utc_offset.total_seconds() * 10_000_000)  # seconds → 100-ns ticks

    naive_local = dt.replace(tzinfo=None)
    local_us = int((naive_local - datetime(1970, 1, 1)) / timedelta(microseconds=1))
    item1 = local_us * 10 + _DOTNET_EPOCH_TICKS  # µs → 100-ns ticks + .NET epoch offset

    return item1, item2


class TrackerCondition(SolarFarmerBaseModel):
    """Tracker system conditions for a specific time step.

    Each instance describes the rotation angles of all trackers for one
    timestep. The rotations can be expressed either as a single shared
    value (when every tracker has the same angle) or as an array of
    per-tracker values.

    Attributes
    ----------
    period_in_minutes : float
        Duration of the time period in minutes, starting from
        ``start_of_period``.
    start_of_period : datetime
        Start of the time period this record relates to. Timezone-aware
        (ISO 8601 offset notation recommended, e.g.
        ``"2020-01-01T00:00:00+00:00"``).
    tracker_rotations_array_values : list[int]
        Per-tracker rotation angles encoded as integers (value × 100,
        i.e. a rotation of 12.34° is stored as ``1234``). Each value must
        be in the range ``[-8990, 8990]`` (i.e. -89.90° to +89.90°).
        Empty when all trackers share the same rotation angle — use
        ``tracker_rotation_unique_value`` instead.
    tracker_rotation_unique_value : int or None
        Shared rotation angle (encoded as integer × 100) used when all
        trackers have the same rotation. Must be in ``[-8990, 8990]``
        (i.e. -89.90° to +89.90°).
        ``None`` when trackers have different rotation angles (use
        ``tracker_rotations_array_values``).
    """

    period_in_minutes: float
    start_of_period: datetime
    tracker_rotations_array_values: list[int] = Field(default_factory=list)
    tracker_rotation_unique_value: int | None = Field(None, ge=-8990, le=8990)

    @field_validator("tracker_rotations_array_values")
    @classmethod
    def _array_values_in_range(cls, v: list[int]) -> list[int]:
        if any(x < -8990 or x > 8990 for x in v):
            raise ValueError(
                "all values must be in the range [-8990, 8990] (i.e. -89.90° to +89.90°)"
            )
        return v

    @model_validator(mode="after")
    def _check_rotation_invariant(self) -> TrackerCondition:
        if self.tracker_rotations_array_values and self.tracker_rotation_unique_value is not None:
            raise ValueError(
                "Provide either tracker_rotations_array_values or tracker_rotation_unique_value, "
                "not both. Use tracker_rotation_unique_value when all trackers share the same "
                "angle and tracker_rotations_array_values when they differ."
            )
        return self


class TrackersConditionsDataset(SolarFarmerBaseModel):
    """Custom tracker rotation schedules dataset.

    Contains a time series of tracker rotation conditions used to drive
    ``TrackerAlgorithm.CUSTOM_ROTATIONS`` simulations. Passed as the
    ``trackers_conditions_dataset`` field of :class:`EnergyCalculationInputs`.

    Attributes
    ----------
    data : list[TrackerCondition]
        Time-ordered list of tracker conditions, one per time step.
    offset_from_utc : float
        Hourly UTC offset of the timestamps in ``data``. Positive values
        indicate time zones east of Greenwich (e.g. ``+1`` for CET).
    rotations_are_at_middle_of_period : bool
        ``True`` if the rotation values represent the middle of each
        time period; ``False`` (default) if they represent the start.
    tracker_rotation_ids : list[str]
        Ordered list of tracker rotation IDs. The position of each ID
        corresponds to the index into each
        :attr:`TrackerCondition.tracker_rotations_array_values` array.
    """

    data: list[TrackerCondition] = Field(default_factory=list)
    offset_from_utc: float = 0.0
    rotations_are_at_middle_of_period: bool = False
    tracker_rotation_ids: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Protobuf I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_protobuf_file(cls, path: Path | str) -> TrackersConditionsDataset:
        """Deserialize a single gzip-compressed protobuf file.

        Parameters
        ----------
        path : Path or str
            Path to a ``*.gz`` file containing a serialized
            ``TrackersConditionsDatasetDto`` protobuf message.

        Returns
        -------
        TrackersConditionsDataset
        """
        from solarfarmer.models._proto.trackers_conditions_dataset_pb2 import (  # noqa: PLC0415
            TrackersConditionsDatasetDto,
        )

        with gzip.open(Path(path), "rb") as fh:
            raw = fh.read()
        dto = TrackersConditionsDatasetDto()
        dto.ParseFromString(raw)
        return _dto_to_dataset(dto)

    @classmethod
    def from_protobuf_files(cls, paths: Iterable[Path | str]) -> TrackersConditionsDataset:
        """Deserialize and merge multiple gzip-compressed protobuf files.

        Metadata (``offset_from_utc``, ``rotations_are_at_middle_of_period``,
        ``tracker_rotation_ids``) is taken from the **first** file; subsequent
        files contribute additional :class:`TrackerCondition` records.

        Parameters
        ----------
        paths : Iterable[Path or str]
            Paths to ``*.gz`` files, in order.

        Returns
        -------
        TrackersConditionsDataset
        """
        sorted_paths = [Path(p) for p in paths]
        if not sorted_paths:
            raise ValueError("at least one path must be provided")

        datasets = [cls.from_protobuf_file(p) for p in sorted_paths]
        first = datasets[0]
        combined_data = [record for ds in datasets for record in ds.data]
        return cls(
            data=combined_data,
            offset_from_utc=first.offset_from_utc,
            rotations_are_at_middle_of_period=first.rotations_are_at_middle_of_period,
            tracker_rotation_ids=first.tracker_rotation_ids,
        )

    @classmethod
    def from_protobuf_dir(cls, directory: Path | str) -> TrackersConditionsDataset:
        """Deserialize protobuf file(s) auto-discovered in a directory.

        Looks for files matching the SolarFarmer naming convention:

        * **Single file**: ``TrackersConditionsDatasetDto_Protobuf.gz``
        * **Multi-part files**: ``TrackersConditionsDatasetDto_Protobuf001of003.gz``,
          ``…002of003.gz``, etc. (sorted by part number)

        Parameters
        ----------
        directory : Path or str
            Directory to search.

        Returns
        -------
        TrackersConditionsDataset

        Raises
        ------
        FileNotFoundError
            If no matching protobuf files are found.
        """
        base = Path(directory)
        files = list(base.iterdir()) if base.is_dir() else []

        # Check for single-file pattern first
        single = [f for f in files if _PROTO_SINGLE_RE.match(f.name)]
        if single:
            return cls.from_protobuf_file(single[0])

        # Fall back to multi-part pattern, sorted by part number
        multi: list[tuple[int, Path]] = []
        for f in files:
            m = _PROTO_MULTI_RE.match(f.name)
            if m:
                multi.append((int(m.group(1)), f))
        if multi:
            multi.sort(key=lambda t: t[0])
            return cls.from_protobuf_files(p for _, p in multi)

        raise FileNotFoundError(
            f"No TrackersConditionsDatasetDto_Protobuf*.gz files found in {base}"
        )

    def to_protobuf_file(self, path: Path | str) -> None:
        """Serialize to a gzip-compressed protobuf file.

        Parameters
        ----------
        path : Path or str
            Destination path. The file is written (or overwritten) atomically
            using gzip compression.
        """
        from solarfarmer.models._proto.trackers_conditions_dataset_pb2 import (  # noqa: PLC0415
            TrackersConditionsDatasetDto,
        )

        dto = _dataset_to_dto(self, TrackersConditionsDatasetDto)
        raw = dto.SerializeToString()
        with gzip.open(Path(path), "wb") as fh:
            fh.write(raw)


# ---------------------------------------------------------------------------
# Private DTO ↔ domain-model conversion helpers
# (defined after the classes so forward references resolve naturally)
# ---------------------------------------------------------------------------


def _dto_to_dataset(dto: object) -> TrackersConditionsDataset:
    """Convert a ``TrackersConditionsDatasetDto`` protobuf message to the domain model."""
    n = len(dto.start_of_period)  # type: ignore[union-attr]

    # period_in_minutes: prefer per-record array; fall back to scalar field
    raw_periods = list(dto.period_in_minutes)  # type: ignore[union-attr]
    if len(raw_periods) == n:
        periods: list[float] = raw_periods
    elif dto.HasField("period_in_minutes_for_all_records"):  # type: ignore[union-attr]
        periods = [dto.period_in_minutes_for_all_records] * n  # type: ignore[union-attr]
    elif n == 0:
        periods = []
    else:
        raise ValueError(
            "period_in_minutes data is missing or inconsistent with start_of_period count"
        )

    arr_wrappers = list(dto.tracker_rotations_array_values)  # type: ignore[union-attr]
    uni_wrappers = list(dto.tracker_rotation_unique_value)  # type: ignore[union-attr]

    data: list[TrackerCondition] = []
    for i in range(n):
        start = _dotnet_ticks_to_datetime(
            dto.start_of_period[i].item1,  # type: ignore[union-attr]
            dto.start_of_period[i].item2,  # type: ignore[union-attr]
        )
        arr_values = list(arr_wrappers[i].values) if i < len(arr_wrappers) else []
        unique_val: int | None = None
        if i < len(uni_wrappers) and uni_wrappers[i].HasField("value"):
            unique_val = uni_wrappers[i].value

        data.append(
            TrackerCondition(
                period_in_minutes=float(periods[i]),
                start_of_period=start,
                tracker_rotations_array_values=arr_values,
                tracker_rotation_unique_value=unique_val,
            )
        )

    return TrackersConditionsDataset(
        data=data,
        offset_from_utc=float(dto.offset_from_utc),  # type: ignore[union-attr]
        rotations_are_at_middle_of_period=bool(dto.rotations_are_at_middle_of_period),  # type: ignore[union-attr]
        tracker_rotation_ids=list(dto.tracker_rotation_ids),  # type: ignore[union-attr]
    )


def _dataset_to_dto(dataset: TrackersConditionsDataset, dto_cls: type) -> object:
    """Convert a :class:`TrackersConditionsDataset` to a ``TrackersConditionsDatasetDto``."""
    from solarfarmer.models._proto.trackers_conditions_dataset_pb2 import (  # noqa: PLC0415
        LongTuple,
        NullableShortWrapper,
        ShortArrayWrapper,
    )

    start_of_period = []
    period_in_minutes: list[float] = []
    arr_wrappers = []
    uni_wrappers = []

    for condition in dataset.data:
        item1, item2 = _datetime_to_dotnet_ticks(condition.start_of_period)
        start_of_period.append(LongTuple(item1=item1, item2=item2))
        period_in_minutes.append(condition.period_in_minutes)

        if condition.tracker_rotations_array_values:
            arr_wrappers.append(ShortArrayWrapper(values=condition.tracker_rotations_array_values))
            uni_wrappers.append(NullableShortWrapper())  # absent → null
        else:
            arr_wrappers.append(ShortArrayWrapper())  # empty array
            if condition.tracker_rotation_unique_value is not None:
                uni_wrappers.append(
                    NullableShortWrapper(value=condition.tracker_rotation_unique_value)
                )
            else:
                uni_wrappers.append(NullableShortWrapper())  # absent → null

    return dto_cls(
        offset_from_utc=dataset.offset_from_utc,
        rotations_are_at_middle_of_period=dataset.rotations_are_at_middle_of_period,
        tracker_rotation_ids=dataset.tracker_rotation_ids,
        start_of_period=start_of_period,
        period_in_minutes=period_in_minutes,
        tracker_rotations_array_values=arr_wrappers,
        tracker_rotation_unique_value=uni_wrappers,
    )
