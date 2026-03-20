from __future__ import annotations

from ._base import SolarFarmerBaseModel
from .energy_calculation_options import EnergyCalculationOptions
from .enums import MeteoFileFormat
from .location import Location
from .monthly_albedo import MonthlyAlbedo
from .ond_supplements import OndFileSupplements
from .pan_supplements import PanFileSupplements
from .pv_plant import PVPlant


class EnergyCalculationInputs(SolarFarmerBaseModel):
    """Complete input specification for a SolarFarmer energy calculation.

    Compose all sub-models here and serialize with ``model_dump(by_alias=True)`` to
    produce the ``energyCalculationInputs`` JSON payload.

    Attributes
    ----------
    location : Location
        Geographic location of the plant
    pv_plant : PVPlant
        Electrical topology of the PV plant
    monthly_albedo : MonthlyAlbedo
        Twelve monthly albedo values (Jan-Dec), each within [0, 1]
    energy_calculation_options : EnergyCalculationOptions
        Model chain configuration options
    horizon_azimuths : list[float] or None
        Horizon profile azimuth angles in degrees
    horizon_angles : list[float] or None
        Horizon profile elevation angles in degrees
    pan_file_supplements : dict[str, PanFileSupplements] or None
        PAN file overrides keyed by module spec ID
    ond_file_supplements : dict[str, OndFileSupplements] or None
        OND file overrides keyed by inverter spec ID
    """

    location: Location
    pv_plant: PVPlant
    monthly_albedo: MonthlyAlbedo
    energy_calculation_options: EnergyCalculationOptions
    horizon_azimuths: list[float] | None = None
    horizon_angles: list[float] | None = None
    pan_file_supplements: dict[str, PanFileSupplements] | None = None
    ond_file_supplements: dict[str, OndFileSupplements] | None = None


class EnergyCalculationInputsWithFiles(SolarFarmerBaseModel):
    """Wrapper that pairs calculation inputs with file contents.

    Used when sending the full payload (inputs + binary files) to the
    SolarFarmer API. File contents are passed as strings (base64 or raw
    text depending on format).

    Attributes
    ----------
    energy_calculation_inputs : EnergyCalculationInputs
        The core calculation inputs
    meteo_file_path_or_contents : str or None
        Meteorological file path or inline contents
    solar_position_path_or_contents : str or None
        Solar position file path or inline contents
    meteo_file_format : MeteoFileFormat or None
        Format of the meteorological file
    hor_file_path_or_contents : str or None
        Horizon file path or inline contents
    pan_file_paths_or_contents : dict[str, str] or None
        PAN file contents keyed by module spec ID
    ond_file_paths_or_contents : dict[str, str] or None
        OND file contents keyed by inverter spec ID
    dco_file_paths_or_contents : dict[str, str] or None
        DCO file contents keyed by optimizer spec ID
    """

    energy_calculation_inputs: EnergyCalculationInputs
    meteo_file_path_or_contents: str | None = None
    solar_position_path_or_contents: str | None = None
    meteo_file_format: MeteoFileFormat | None = None
    hor_file_path_or_contents: str | None = None
    pan_file_paths_or_contents: dict[str, str] | None = None
    ond_file_paths_or_contents: dict[str, str] | None = None
    dco_file_paths_or_contents: dict[str, str] | None = None
