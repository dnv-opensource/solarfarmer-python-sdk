from pydantic import Field, model_validator

from ._base import SolarFarmerBaseModel
from .rack import Rack, _warn_on_reversed_racks


class Racks(SolarFarmerBaseModel):
    """A collection of fixed-tilt racks in a 3D plant layout.

    Issues one :class:`~solarfarmer.models.RackOrientationWarning` listing any
    racks whose front face points below the horizon.

    Attributes
    ----------
    racks : list[Rack]
        The individual rack objects making up this collection
    """

    racks: list[Rack] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_rack_orientation(self) -> "Racks":
        """Warn once about racks whose front face points below the horizon."""
        _warn_on_reversed_racks(self.racks)
        return self
