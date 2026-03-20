from pydantic import Field

from ._base import SolarFarmerBaseModel


class TrackerSystem(SolarFarmerBaseModel):
    """Configuration for a single-axis tracker system.

    Attributes
    ----------
    system_plane_azimuth : float
        Azimuth of the tracker system plane in degrees
    system_plane_tilt : float
        Tilt of the tracker system plane in degrees
    rotation_min_deg : float
        Minimum tracker rotation angle in degrees, range [-90, 0]
    rotation_max_deg : float
        Maximum tracker rotation angle in degrees, range [0, 90]
    tracker_azimuth : float or None
        Azimuth of the tracker axis in degrees
    east_west_gcr : float or None
        East-west ground coverage ratio
    is_backtracking : bool or None
        Whether backtracking is enabled. Default in the engine is True
    use_slope_aware_backtracking : bool or None
        Whether slope-aware backtracking is used. Default in the engine is True
    """

    system_plane_azimuth: float
    system_plane_tilt: float
    rotation_min_deg: float = Field(0.0, ge=-90, le=0)
    rotation_max_deg: float = Field(0.0, ge=0, le=90)
    tracker_azimuth: float | None = None
    east_west_gcr: float | None = None
    is_backtracking: bool | None = None
    use_slope_aware_backtracking: bool | None = None
