from pydantic import Field

from ._base import SolarFarmerBaseModel
from .vector3double import Vector3Double


class IndexedObject3D(SolarFarmerBaseModel):
    """A 3D object defined by an indexed mesh of vertices and face indices.

    Represents a shading obstacle or building in the 3D scene. The mesh is
    described by a set of 3D vertices plus face connectivity expressed as
    lists of vertex indices — either quadrilateral faces (``quad_indices``)
    or triangular faces (``triangle_indices``).

    Attributes
    ----------
    is_building : bool
        Whether the object should be treated as a building (affects shading
        and irradiance modelling assumptions). Defaults to ``False`` when
        omitted from the server payload
    name : str or None
        Descriptive name for this object in the 3D scene. May be ``None``
        when the server omits it
    quad_indices : list[list[int]]
        Face connectivity for quadrilateral faces. Each inner list contains
        four vertex indices referencing entries in ``vertices``
    triangle_indices : list[list[int]]
        Face connectivity for triangular faces. Each inner list contains
        three vertex indices referencing entries in ``vertices``
    vertices : list[Vector3Double]
        3D vertex positions shared by both quad and triangle faces
    """

    is_building: bool = False
    name: str | None = None
    quad_indices: list[list[int]] = Field(default_factory=list)
    triangle_indices: list[list[int]] = Field(default_factory=list)
    vertices: list[Vector3Double] = Field(default_factory=list)
