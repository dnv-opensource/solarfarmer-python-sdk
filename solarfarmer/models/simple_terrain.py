from pydantic import Field

from ._base import SolarFarmerBaseModel
from .mini_simple_terrain_dto import MiniSimpleTerrainDto


class SimpleTerrain(SolarFarmerBaseModel):
    """A simple terrain representation composed of one or more terrain tiles.

    Aggregates multiple :class:`MiniSimpleTerrainDto` tiles that together
    describe the ground surface beneath and around a 3D PV plant layout.

    Attributes
    ----------
    mini_simple_terrains : list[MiniSimpleTerrainDto]
        Individual terrain tiles that make up the full terrain surface
    """

    mini_simple_terrains: list[MiniSimpleTerrainDto] = Field(default_factory=list)
