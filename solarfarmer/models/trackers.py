from pydantic import Field

from ._base import SolarFarmerBaseModel
from .tracker import Tracker


class Trackers(SolarFarmerBaseModel):
    """A collection of single-axis trackers in a 3D plant layout.

    Attributes
    ----------
    trackers : list[Tracker]
        The individual tracker objects making up this collection
    """

    trackers: list[Tracker] = Field(default_factory=list)
