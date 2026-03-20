from pydantic import Field

from ._base import SolarFarmerBaseModel


class Layout(SolarFarmerBaseModel):
    """A group of identical module strings sharing the same configuration.

    Defines the physical and electrical arrangement of modules connected
    to one or more inverter inputs.

    Attributes
    ----------
    layout_count : int
        Number of identical copies of this layout, >= 1
    module_specification_id : str
        Reference to a module specification (PAN file key)
    mounting_type_id : str
        Reference to a mounting type specification
    is_trackers : bool
        Whether this layout uses single-axis trackers
    azimuth : float
        Array azimuth in degrees, range [-360, 360]
    pitch : float
        Row-to-row pitch in metres
    total_number_of_strings : int
        Total number of strings in this layout, >= 1
    string_length : int
        Number of modules per string, >= 1
    inverter_input : list[int]
        Inverter MPPT input indices this layout connects to
    dc_ohmic_connector_loss : float
        DC wiring ohmic loss as a fraction, range [0, 1]
    module_mismatch_loss : float
        Module mismatch loss as a fraction, range [0, 0.1]
    name : str or None
        Optional descriptive name
    tracker_system_id : str or None
        Reference to a tracker system, required when ``is_trackers`` is True
    number_of_strings_in_front_row : int
        Number of strings in the front row (fixed-tilt only)
    number_of_strings_in_back_row : int
        Number of strings in the back row (fixed-tilt only)
    number_of_strings_in_right_row : int
        Number of strings in the right row (trackers only)
    number_of_strings_in_left_row : int
        Number of strings in the left row (trackers only)
    number_of_strings_in_isolated_row : int
        Number of strings with no near-shading neighbors
    terrain_azimuth : float
        Terrain slope azimuth in degrees
    terrain_slope : float
        Terrain slope angle in degrees
    module_quality_factor : float or None
        Module quality factor override, negative implies loss, range [-0.4, 0.1]
    """

    layout_count: int = Field(..., ge=1)
    module_specification_id: str = Field(..., alias="moduleSpecificationID", min_length=1)
    mounting_type_id: str = Field(..., alias="mountingTypeID", min_length=1)
    is_trackers: bool
    azimuth: float = Field(..., ge=-360, le=360)
    pitch: float
    total_number_of_strings: int = Field(..., ge=1)
    string_length: int = Field(..., ge=1)
    inverter_input: list[int] = Field(default_factory=list)
    dc_ohmic_connector_loss: float = Field(0.0, ge=0, le=1)
    module_mismatch_loss: float = Field(0.0, ge=0, le=0.1)
    name: str | None = None
    tracker_system_id: str | None = Field(None, alias="trackerSystemID")
    number_of_strings_in_front_row: int = 0
    number_of_strings_in_back_row: int = 0
    number_of_strings_in_right_row: int = 0
    number_of_strings_in_left_row: int = 0
    number_of_strings_in_isolated_row: int = 0
    terrain_azimuth: float = 0.0
    terrain_slope: float = 0.0
    module_quality_factor: float | None = Field(None, ge=-0.4, le=0.1)
