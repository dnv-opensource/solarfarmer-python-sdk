import math
import warnings

from pydantic import Field

from ._base import SolarFarmerBaseModel
from .quad_double import QuadDouble

_MAX_LISTED_RACK_IDS = 10


class RackOrientationWarning(UserWarning):
    """Warn when racks' corner order puts their front face below the horizon."""


class Rack(SolarFarmerBaseModel):
    """A fixed-tilt rack in a 3D plant layout.

    Represents a single physical rack structure placed in the 3D scene,
    identified by an integer ID and referencing a mounting type. The rack
    geometry is described by a quadrilateral (``quad``) in world coordinates.

    The order of the ``quad`` corners determines which face is the front of
    the modules, and which end holds module index 0; see
    :class:`~solarfarmer.models.QuadDouble`.
    :class:`~solarfarmer.models.PVPlant` and :class:`~solarfarmer.models.Racks`
    check all of their racks and issue one :class:`RackOrientationWarning`
    listing any whose front face points below the horizon, which almost always
    means the corners are in the reverse order.

    Attributes
    ----------
    id : int
        Unique integer identifier for this rack within the layout
    mounting_type_id : str
        Reference to a mounting type specification. Must match a key in
        ``PVPlant.mounting_type_specifications``
    pitch_to_back : float or None
        Row-to-row pitch to the adjacent rack behind this one, in metres.
        ``None`` if this rack has no neighbour behind it (e.g. last row)
    pitch_to_front : float or None
        Row-to-row pitch to the adjacent rack in front of this one, in metres.
        ``None`` if this rack has no neighbour in front of it (e.g. first row)
    quad : QuadDouble
        3D quadrilateral defining the four corner vertices of the rack surface,
        in the order described in :class:`~solarfarmer.models.QuadDouble`
    """

    id: int
    mounting_type_id: str = Field(..., alias="mountingTypeID", min_length=1)
    pitch_to_back: float | None = None
    pitch_to_front: float | None = None
    quad: QuadDouble


def _warn_on_reversed_racks(racks: list[Rack] | None) -> None:
    """Issue one warning for racks whose front face points below the horizon or that have no area.

    Called from the model validators of collections of racks. Checking the whole
    collection in one pass, with one warning, keeps large layouts fast and their
    output readable; a per-rack warning would print once for every rack.
    """
    if not racks:
        return

    facing_down: list[int] = []
    no_area: list[int] = []
    for rack in racks:
        nx, ny, nz = rack.quad._unscaled_normal()
        length_squared = nx * nx + ny * ny + nz * nz
        if length_squared < 1e-24:
            no_area.append(rack.id)
        elif nz < -1e-9 * math.sqrt(length_squared):
            facing_down.append(rack.id)

    def describe(rack_ids: list[int]) -> str:
        listed = ", ".join(str(i) for i in rack_ids[:_MAX_LISTED_RACK_IDS])
        more = len(rack_ids) - _MAX_LISTED_RACK_IDS
        listed += f" and {more} more" if more > 0 else ""
        return f"{len(rack_ids)} of {len(racks)} racks (IDs {listed})"

    # warn -> this function -> model validator -> pydantic entry point -> caller
    if facing_down:
        warnings.warn(
            f"{describe(facing_down)} have a front face pointing below the horizon, so the "
            "calculation would treat the back of their modules as the front. Their corners "
            "are probably in the reverse order; for a south-facing rack use P1 SW-low, "
            "P2 NW-high, P3 NE-high, P4 SE-low. QuadDouble.tilt shows how a rack is read.",
            RackOrientationWarning,
            stacklevel=4,
        )
    if no_area:
        warnings.warn(
            f"{describe(no_area)} have a quad with no area: corners P1, P2 and P4 are collinear.",
            RackOrientationWarning,
            stacklevel=4,
        )
