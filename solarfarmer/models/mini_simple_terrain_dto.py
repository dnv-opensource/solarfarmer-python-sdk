from pydantic import Field

from ._base import SolarFarmerBaseModel
from .terrain_row_dto import TerrainRowDto
from .vector3double import Vector3Double


class MiniSimpleTerrainDto(SolarFarmerBaseModel):
    """A single terrain tile in a simple terrain representation.

    Describes one rectangular patch of terrain as a regular grid of
    vertices. The grid dimensions are given by ``num_vertices_across``
    (columns) and ``num_vertices_down`` (rows); the actual 3D positions
    are stored in ``vertices`` in row-major order.

    The ``terrain_rows`` list mirrors the row structure and records which
    column ranges within each row are active (contain valid data).

    Attributes
    ----------
    num_vertices_across : int
        Number of vertices along the horizontal (column) axis of the grid
    num_vertices_down : int
        Number of vertices along the vertical (row) axis of the grid
    terrain_rows : list[TerrainRowDto]
        Per-row active column ranges, one entry per row of the grid
    vertices : list[Vector3Double]
        3D vertex positions in row-major order (``num_vertices_down`` ×
        ``num_vertices_across`` entries)
    """

    num_vertices_across: int = Field(..., ge=0)
    num_vertices_down: int = Field(..., ge=0)
    terrain_rows: list[TerrainRowDto] = Field(default_factory=list)
    vertices: list[Vector3Double] = Field(default_factory=list)
