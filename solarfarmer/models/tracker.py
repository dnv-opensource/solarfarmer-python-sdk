from pydantic import Field

from ._base import SolarFarmerBaseModel
from .vector3double import Vector3Double


class Tracker(SolarFarmerBaseModel):
    """A single-axis tracker in a 3D plant layout.

    Represents one physical tracker structure placed in the 3D scene.
    The tracker axis is defined by its north and south end-points; the
    mounting type and tracker system determine the rotation behaviour.

    Attributes
    ----------
    id : int
        Unique integer identifier for this tracker within the layout
    mounting_type_id : str
        Reference to a mounting type specification. Must match a key in
        ``PVPlant.mounting_type_specifications``
    north_point : Vector3Double
        3D coordinates of the northern end of the tracker axis
    pitch_to_left : float or None
        Pitch to the adjacent tracker to the left of this one, in metres.
        ``None`` if this tracker has no left neighbour
    pitch_to_right : float or None
        Pitch to the adjacent tracker to the right of this one, in metres.
        ``None`` if this tracker has no right neighbour
    south_point : Vector3Double
        3D coordinates of the southern end of the tracker axis
    tracker_rotation_id : str or None
        Reference to the tracker rotation specification that governs how
        this tracker rotates throughout the day. ``None`` when no custom
        rotation schedule is assigned (the server default is used)
    tracker_system_id : str or None
        Reference to a tracker system specification. Must match a key in
        ``PVPlant.tracker_systems``. ``None`` for fixed-tilt systems
    """

    id: int
    mounting_type_id: str = Field(..., alias="mountingTypeID", min_length=1)
    north_point: Vector3Double
    pitch_to_left: float | None = None
    pitch_to_right: float | None = None
    south_point: Vector3Double
    tracker_rotation_id: str | None = Field(None, alias="trackerRotationID")
    tracker_system_id: str | None = Field(None, alias="trackerSystemID")
