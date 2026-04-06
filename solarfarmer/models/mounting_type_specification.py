from pydantic import Field, field_validator

from ._base import SolarFarmerBaseModel


class MountingTypeSpecification(SolarFarmerBaseModel):
    """Physical and thermal properties of a mounting structure.

    Attributes
    ----------
    is_tracker : bool
        Whether this mounting type is a single-axis tracker
    number_of_modules_high : int
        Number of modules stacked vertically on the rack
    modules_are_landscape : bool
        Whether modules are mounted in landscape orientation
    rack_height : float
        Height of the rack structure in meters, range [0, 100]. Must satisfy::

            rack_height >= frame_bottom_width
                         + (module_side × number_of_modules_high)
                         + ((y_spacing_between_modules - module_side) × (number_of_modules_high - 1))
                         + frame_top_width

        where ``module_side`` is the module length (if portrait) or width (if landscape)
        as defined in the PAN file. Note: ``y_spacing_between_modules`` is the edge-to-edge
        pitch (not gap), so ``(y_spacing_between_modules - module_side)`` gives the actual
        gap. Violating this constraint causes a validation error.
    y_spacing_between_modules : float
        Edge-to-edge distance from the bottom of one module to the bottom of the
        module above it, in metres, range [0, 5]. This is the **pitch**, not the gap.
        For portrait orientation, this equals module length + gap. For landscape,
        module width + gap. If ``number_of_modules_high = 1``, this parameter is ignored.
    frame_bottom_width : float
        Frame width at the bottom edge in metres, range [0, 0.5]
    constant_heat_transfer_coefficient : float
        Constant (Uc) component of the thermal model in W/(m²·K)
    convective_heat_transfer_coefficient : float
        Wind-dependent (Uv) component of the thermal model in W/(m²·K)/(m/s)
    monthly_soiling_loss : list[float]
        Twelve monthly soiling loss fractions, each in [0, 1]
    number_of_modules_long : int or None
        Number of modules along the rack length (3D only)
    x_spacing_between_modules : float or None
        Edge-to-edge distance from the left edge of one module to the left edge
        of the neighboring module in the same row, in metres, range [0, 5].
        This is the **pitch**, not the gap. For portrait, equals module width + gap.
        For landscape, module length + gap. Required for 3D calculations only.
    frame_top_width : float or None
        Frame width at the top edge in metres, range [0, 0.5]
    frame_end_width : float or None
        Frame width at the side edges in metres, range [0, 0.5]
    tilt : float or None
        Fixed tilt angle in degrees, range [0, 90] (fixed-tilt only)
    height_of_lowest_edge_from_ground : float or None
        Lowest module edge height in metres, range [0, 5] (fixed-tilt only)
    height_of_tracker_center_from_ground : float or None
        Tracker rotation axis height in metres (trackers only)
    transmission_factor : float or None
        Bifacial rear-side transmission factor, range [0, 1]. **Required**
        when the module PAN file has a non-zero ``BifacialityFactor``.
        Omitting this field for bifacial modules causes a validation error.
    bifacial_shade_loss_factor : float or None
        Bifacial rear-side shade loss, range [0, 1]. **Required** when
        the module PAN file has a non-zero ``BifacialityFactor``.
        Omitting this field for bifacial modules causes a validation error.
    bifacial_mismatch_loss_factor : float or None
        Bifacial rear-side mismatch loss, range [0, 1]. **Required** when
        the module PAN file has a non-zero ``BifacialityFactor``.
        Omitting this field for bifacial modules causes a validation error.
    """

    is_tracker: bool
    number_of_modules_high: int = Field(..., ge=1)
    modules_are_landscape: bool
    rack_height: float = Field(..., ge=0, le=100)
    y_spacing_between_modules: float = Field(..., ge=0, le=5)
    frame_bottom_width: float = Field(..., ge=0, le=0.5)
    constant_heat_transfer_coefficient: float
    convective_heat_transfer_coefficient: float
    monthly_soiling_loss: list[float] = Field(default_factory=list)
    number_of_modules_long: int | None = None
    x_spacing_between_modules: float | None = Field(None, ge=0, le=5)
    frame_top_width: float | None = Field(None, ge=0, le=0.5)
    frame_end_width: float | None = Field(None, ge=0, le=0.5)
    tilt: float | None = Field(None, ge=0, le=90)
    height_of_lowest_edge_from_ground: float | None = Field(None, ge=0, le=5)
    height_of_tracker_center_from_ground: float | None = None
    transmission_factor: float | None = Field(None, ge=0, le=1)
    bifacial_shade_loss_factor: float | None = Field(None, ge=0, le=1)
    bifacial_mismatch_loss_factor: float | None = Field(None, ge=0, le=1)

    @field_validator("monthly_soiling_loss")
    @classmethod
    def _validate_monthly_soiling(cls, v: list[float]) -> list[float]:
        """Ensure exactly 12 values in [0, 1]."""
        if len(v) != 0 and len(v) != 12:
            raise ValueError(f"monthly_soiling_loss must have exactly 12 values, got {len(v)}")
        if any(not 0 <= x <= 1 for x in v):
            raise ValueError("each monthly_soiling_loss value must be between 0 and 1")
        return v
