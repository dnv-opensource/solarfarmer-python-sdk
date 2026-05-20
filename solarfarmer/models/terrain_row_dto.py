from pydantic import Field

from ._base import SolarFarmerBaseModel
from .terrain_row_start_end_columns_dto import TerrainRowStartEndColumnsDto


class TerrainRowDto(SolarFarmerBaseModel):
    """A single row in a simple terrain grid, with its active column ranges.

    Each row of the terrain grid may contain one or more contiguous spans
    of active (valid) columns; each span is described by a
    :class:`TerrainRowStartEndColumnsDto`.

    Attributes
    ----------
    start_end_columns : list[TerrainRowStartEndColumnsDto]
        Active column ranges within this terrain row
    """

    start_end_columns: list[TerrainRowStartEndColumnsDto] = Field(default_factory=list)
