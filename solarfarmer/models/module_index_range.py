from pydantic import Field

from ._base import SolarFarmerBaseModel


class ModuleIndexRange(SolarFarmerBaseModel):
    """A range of indices denoting where modules are placed on a rack or tracker.

    Used in 3D calculations to map a contiguous sequence of modules on a
    mounting structure to a string. Multiple ranges may be chained in order
    to build up a full string across more than one rack.

    Attributes
    ----------
    mounting_id : int
        The rack or tracker ID this module index range refers to. Must match
        an ``id`` in ``PVPlant.racks`` or ``PVPlant.trackers``
    start_x : int
        First index (inclusive) of this range of modules along the length of
        a row on the mount. May be larger than ``end_x`` when the string runs
        in the reverse direction along the rack
    end_x : int
        Last index (inclusive) of this range of modules along the length of
        a row on the mount. May be smaller than ``start_x``
    y : int
        Row index on the mount where the range is located (0 = bottom edge)
    """

    mounting_id: int = Field(..., alias="mountingID")
    start_x: int
    end_x: int
    y: int
