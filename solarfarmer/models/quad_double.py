import math

from ._base import SolarFarmerBaseModel
from .vector3double import Vector3Double


def _difference(a: Vector3Double, b: Vector3Double) -> tuple[float, float, float]:
    return (a.x - b.x, a.y - b.y, a.z - b.z)


class QuadDouble(SolarFarmerBaseModel):
    """A quadrilateral in 3D space defined by four corner vertices.

    Represents the surface of a fixed-tilt rack. Coordinates are in metres with
    x pointing east, y pointing north and z up, as in the projected coordinates
    of the ModelChainAsync API examples.

    The corner order determines which face is the front of the modules. Seen
    from in front of the modules, start at the low corner on the left and go up
    the slope first::

        P2 ---------------- P3      high edge
         |                  |
        P1 ---------------- P4      low edge

    ``P1 -> P2`` runs up the slope (the rack depth) and ``P1 -> P4`` runs along
    the row (the rack width). For a south-facing rack the order is SW-low,
    NW-high, NE-high, SE-low, which is clockwise when seen from above. With this
    order, ``(P4 - P1) x (P2 - P1)`` points out of the front face
    (:attr:`front_normal`).

    The reverse order also passes schema validation, but gives badly wrong
    energy, consistent with the calculation treating the back of the modules as
    the front. :class:`~solarfarmer.models.Rack` warns when a quad's front face
    points below the horizon.

    Attributes
    ----------
    p1 : Vector3Double
        Low corner at the start of the row (lower left, seen from the front)
    p2 : Vector3Double
        High corner directly up the slope from ``p1``
    p3 : Vector3Double
        High corner at the end of the row
    p4 : Vector3Double
        Low corner at the end of the row, directly down the slope from ``p3``
    """

    p1: Vector3Double
    p2: Vector3Double
    p3: Vector3Double
    p4: Vector3Double

    @property
    def width(self) -> float:
        """Length of the ``P1 -> P4`` edge, along the row, in metres."""
        return math.hypot(*_difference(self.p4, self.p1))

    @property
    def depth(self) -> float:
        """Length of the ``P1 -> P2`` edge, up the slope, in metres."""
        return math.hypot(*_difference(self.p2, self.p1))

    @property
    def front_normal(self) -> tuple[float, float, float]:
        """Unit vector pointing out of the front face, ``(P4 - P1) x (P2 - P1)`` normalized.

        Raises
        ------
        ValueError
            If ``P1``, ``P2`` and ``P4`` are collinear, so the quad has no area
        """
        ax, ay, az = _difference(self.p4, self.p1)
        bx, by, bz = _difference(self.p2, self.p1)
        normal = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
        length = math.hypot(*normal)
        if length < 1e-12:
            raise ValueError("Quad corners P1, P2 and P4 are collinear, so the quad has no area")
        return (normal[0] / length, normal[1] / length, normal[2] / length)

    @property
    def tilt(self) -> float:
        """Angle of the front face from horizontal, in degrees.

        0 means facing straight up, 90 means vertical, and more than 90 means
        the front face points below the horizon.
        """
        return math.degrees(math.acos(max(-1.0, min(1.0, self.front_normal[2]))))

    @property
    def azimuth(self) -> float:
        """Direction the front face points, in degrees clockwise from north (the y axis).

        North is 0, east 90, south 180 and west 270. Not meaningful for a
        horizontal quad.
        """
        nx, ny, _ = self.front_normal
        return math.degrees(math.atan2(nx, ny)) % 360.0
