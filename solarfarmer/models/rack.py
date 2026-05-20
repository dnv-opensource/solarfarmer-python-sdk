from pydantic import Field

from ._base import SolarFarmerBaseModel
from .quad_double import QuadDouble


class Rack(SolarFarmerBaseModel):
    """A fixed-tilt rack in a 3D plant layout.

    Represents a single physical rack structure placed in the 3D scene,
    identified by an integer ID and referencing a mounting type. The rack
    geometry is described by a quadrilateral (``quad``) in world coordinates.

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
        3D quadrilateral defining the four corner vertices of the rack surface
    """

    id: int
    mounting_type_id: str = Field(..., alias="mountingTypeID", min_length=1)
    pitch_to_back: float | None = None
    pitch_to_front: float | None = None
    quad: QuadDouble
