import warnings

from pydantic import Field, model_validator

from ._base import SolarFarmerBaseModel
from .quad_double import QuadDouble


class RackOrientationWarning(UserWarning):
    """Warn when a rack's corner order puts its front face below the horizon."""


class Rack(SolarFarmerBaseModel):
    """A fixed-tilt rack in a 3D plant layout.

    Represents a single physical rack structure placed in the 3D scene,
    identified by an integer ID and referencing a mounting type. The rack
    geometry is described by a quadrilateral (``quad``) in world coordinates.

    The order of the ``quad`` corners determines which face is the front of
    the modules; see :class:`~solarfarmer.models.QuadDouble`. A rack whose front
    face points below the horizon almost always has its corners in the reverse
    order, so constructing one issues a :class:`RackOrientationWarning`.

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

    @model_validator(mode="after")
    def _warn_on_reversed_corners(self) -> "Rack":
        """Warn if the quad has no area or its front face points below the horizon."""
        # Warn rather than reorder: reordering corners would also change module indexing
        try:
            normal_z = self.quad.front_normal[2]
        except ValueError as e:
            warnings.warn(f"Rack {self.id}: {e}.", RackOrientationWarning, stacklevel=3)
            return self
        if normal_z < -1e-9:
            warnings.warn(
                f"Rack {self.id}: the front face of the quad points below the horizon "
                f"(tilt {self.quad.tilt:.1f} degrees), so the calculation would treat the "
                "back of the modules as the front. The corners are probably in the reverse "
                "order; for a south-facing rack use P1 SW-low, P2 NW-high, P3 NE-high, "
                "P4 SE-low.",
                RackOrientationWarning,
                stacklevel=3,
            )
        return self
