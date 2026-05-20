from pydantic import Field

from ._base import SolarFarmerBaseModel
from .indexed_object3d import IndexedObject3D


class ShadingObjects(SolarFarmerBaseModel):
    """A collection of 3D shading obstacles in the plant scene.

    Holds all near-shading objects (buildings, terrain features, etc.)
    that cast shadows onto the PV plant.

    Attributes
    ----------
    objects : list[IndexedObject3D]
        The individual 3D shading objects in this collection
    """

    objects: list[IndexedObject3D] = Field(default_factory=list)
