from pydantic import Field

from ._base import SolarFarmerBaseModel


class Location(SolarFarmerBaseModel):
    """Geographic coordinates and altitude of the solar plant site.

    Attributes
    ----------
    longitude : float
        Longitude in degrees, range [-180, 180]
    latitude : float
        Latitude in degrees, range [-90, 90]
    altitude : float
        Altitude in meters above sea level, range [-450, 10000]
    """

    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    altitude: float = Field(0.0, ge=-450, le=10000)
