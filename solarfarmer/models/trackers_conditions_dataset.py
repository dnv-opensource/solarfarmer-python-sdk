from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from ._base import SolarFarmerBaseModel


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
