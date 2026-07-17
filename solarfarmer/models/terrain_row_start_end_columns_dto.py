from ._base import SolarFarmerBaseModel


class TerrainRowStartEndColumnsDto(SolarFarmerBaseModel):
    """Column index range for a single active segment within a terrain row.

    Defines a contiguous horizontal span of terrain grid cells that are
    active (i.e. contain valid height data) within one row of a simple
    terrain grid.

    Attributes
    ----------
    start_column_index : int
        Zero-based index of the first active column in the row
    end_column_index : int
        Zero-based index of the last active column in the row (inclusive)
    """

    start_column_index: int
    end_column_index: int
