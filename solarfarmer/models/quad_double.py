from ._base import SolarFarmerBaseModel
from .vector3double import Vector3Double


class QuadDouble(SolarFarmerBaseModel):
    """A quadrilateral in 3D space defined by four corner vertices.

    Represents the footprint or boundary of a rack or similar planar object,
    where the four points define the corners of a quadrilateral face.

    Attributes
    ----------
    p1 : Vector3Double
        First corner vertex of the quadrilateral
    p2 : Vector3Double
        Second corner vertex of the quadrilateral
    p3 : Vector3Double
        Third corner vertex of the quadrilateral
    p4 : Vector3Double
        Fourth corner vertex of the quadrilateral
    """

    p1: Vector3Double
    p2: Vector3Double
    p3: Vector3Double
    p4: Vector3Double
