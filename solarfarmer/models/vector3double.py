from ._base import SolarFarmerBaseModel


class Vector3Double(SolarFarmerBaseModel):
    """A 3D point or vector with double-precision floating-point coordinates.

    Attributes
    ----------
    x : float
        X coordinate in metres
    y : float
        Y coordinate in metres
    z : float
        Z coordinate in metres
    """

    x: float
    y: float
    z: float
