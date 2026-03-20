from pydantic import ConfigDict, Field

from ._base import SolarFarmerBaseModel
from .enums import (
    DiffuseModel,
    HorizonType,
    MissingMetDataMethod,
    OrderColumnsPvSystFormatTimeSeries,
)


class EnergyCalculationOptions(SolarFarmerBaseModel):
    """Options controlling the SolarFarmer energy calculation model chain.

    This model is mutable (not frozen) to allow incremental configuration.

    Attributes
    ----------
    diffuse_model : DiffuseModel
        Diffuse transposition model. Required
    include_horizon : bool
        Whether to include horizon shading. Required
    calculation_year : int
        Year to use for the calculation
    default_wind_speed : float
        Wind speed (m/s) when met data has no wind
    calculate_dhi : bool
        Whether to calculate DHI from GHI
    apply_diffuse_to_horizon : bool or None
        Apply diffuse irradiance to the horizon model. Engine default is True
    horizon_type : HorizonType or None
        Azimuth convention of the horizon file
    treat_circumsolar_as_direct : bool
        Treat circumsolar radiation as direct beam
    use_most_shaded_cell_for_diffuse : bool
        Use the most shaded cell for diffuse shading loss
    model_back_row_separately : bool
        Model back-row shading separately from front rows
    apply_iam : bool
        Apply incidence angle modifier
    apply_spectral_mismatch_modifier : bool
        Apply spectral mismatch correction
    include_module_performance : bool
        Include module IV curve performance model
    include_cell_temperature_model : bool
        Include cell temperature model
    include_soiling_loss_in_temperature_model : bool
        Account for soiling when calculating cell temperature
    use_iam_for_temperature_model : bool
        Use IAM-modified irradiance for temperature calculation
    include_array_iv : bool
        Include array-level IV curve calculation
    include_inverter_model : bool
        Include inverter efficiency model
    include_ac_model : bool
        Include AC loss model
    system_availability_loss : float or None
        System availability loss as a fraction
    grid_availability_loss : float
        Grid availability loss as a fraction
    add_tare_loss_to_inverter_efficiency_model : bool
        Add inverter tare (standby) loss
    ignore_low_power_point_in_efficiency_data : bool
        Ignore the lowest power point in inverter efficiency curves
    solar_measurement_plane_azimuth : float
        Azimuth of the solar measurement reference plane
    solar_measurement_plane_tilt : float
        Tilt of the solar measurement reference plane
    solar_zenith_angle_limit : float or None
        Maximum solar zenith angle in degrees, range [75, 89.9]
    missing_met_data_handling : MissingMetDataMethod or None
        How to handle missing meteorological data
    return_pv_syst_format_time_series_results : bool
        Return PVsyst-format time-series results
    return_detailed_time_series_results : bool
        Return detailed time-series results
    return_loss_tree_time_series_results : bool
        Return loss-tree time-series results
    desired_variables_for_pv_syst_format_time_series : list[str] or None
        Specific variables to include in PVsyst-format output
    choice_columns_order_pv_syst_format_time_series : OrderColumnsPvSystFormatTimeSeries or None
        Column ordering for PVsyst-format output
    use_albedo_from_met_data_when_available : bool or None
        Use albedo from met data when available. Engine default is True
    use_soiling_from_met_data_when_available : bool or None
        Use soiling from met data when available. Engine default is True
    module_mismatch_bin_width : float or None
        Bin width for module mismatch deduplication. Advanced setting
    connector_resistance_bin_width : float or None
        Bin width for connector resistance deduplication. Advanced setting
    irradiance_bin_width : float or None
        Bin width for irradiance deduplication in W/m². Advanced setting
    temperature_bin_width : float or None
        Bin width for temperature deduplication in °C. Advanced setting
    iv_curve_size : int or None
        Number of points in IV curve approximation. Advanced setting
    weight_current_for_mqf_effects : float or None
        Weight for current when applying module quality factor. Advanced setting
        Sum with ``weight_voltage_for_mqf_effects`` must equal 1.0.
    weight_voltage_for_mqf_effects : float or None
        Weight for voltage when applying module quality factor. Advanced setting
        Sum with ``weight_current_for_mqf_effects`` must equal 1.0
    """

    model_config = ConfigDict(frozen=False)

    # --- Required fields ---
    diffuse_model: DiffuseModel
    include_horizon: bool

    # --- General options ---
    calculation_year: int = 1990
    default_wind_speed: float = 0.0
    calculate_dhi: bool = Field(False, alias="calculateDHI")

    # --- Horizon options ---
    apply_diffuse_to_horizon: bool | None = None
    horizon_type: HorizonType | None = None

    # --- Irradiance model options ---
    treat_circumsolar_as_direct: bool = True
    use_most_shaded_cell_for_diffuse: bool = False
    model_back_row_separately: bool = True
    apply_iam: bool = Field(True, alias="applyIAM")
    apply_spectral_mismatch_modifier: bool = False

    # --- Module and temperature model options ---
    include_module_performance: bool = True
    include_cell_temperature_model: bool = True
    include_soiling_loss_in_temperature_model: bool = True
    use_iam_for_temperature_model: bool = Field(True, alias="useIAMForTemperatureModel")

    # --- Electrical model options ---
    include_array_iv: bool = Field(True, alias="includeArrayIV")
    include_inverter_model: bool = True
    include_ac_model: bool = Field(True, alias="includeACModel")

    # --- Loss factors ---
    system_availability_loss: float | None = 0.0
    grid_availability_loss: float = 0.0
    add_tare_loss_to_inverter_efficiency_model: bool = False
    ignore_low_power_point_in_efficiency_data: bool = False

    # --- Solar measurement reference ---
    solar_measurement_plane_azimuth: float = 0.0
    solar_measurement_plane_tilt: float = 0.0
    solar_zenith_angle_limit: float | None = Field(88.0, ge=75.0, le=89.9)

    # --- Missing data handling ---
    missing_met_data_handling: MissingMetDataMethod | None = None

    # --- Time-series output options ---
    return_pv_syst_format_time_series_results: bool = True
    return_detailed_time_series_results: bool = False
    return_loss_tree_time_series_results: bool = False
    desired_variables_for_pv_syst_format_time_series: list[str] | None = Field(default_factory=list)
    choice_columns_order_pv_syst_format_time_series: OrderColumnsPvSystFormatTimeSeries | None = (
        None
    )

    # --- Met data source options ---
    use_albedo_from_met_data_when_available: bool | None = None
    use_soiling_from_met_data_when_available: bool | None = None

    # --- Advanced tuning parameters ---
    module_mismatch_bin_width: float | None = None
    connector_resistance_bin_width: float | None = None
    irradiance_bin_width: float | None = None
    temperature_bin_width: float | None = None
    iv_curve_size: int | None = None
    weight_current_for_mqf_effects: float | None = None
    weight_voltage_for_mqf_effects: float | None = None
