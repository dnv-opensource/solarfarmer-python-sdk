from pydantic import Field

from ._base import SolarFarmerBaseModel
from .rack import Rack


class Racks(SolarFarmerBaseModel):
    """A collection of fixed-tilt racks in a 3D plant layout.

    Attributes
    ----------
    racks : list[Rack]
        The individual rack objects making up this collection
    """

    racks: list[Rack] = Field(default_factory=list)
