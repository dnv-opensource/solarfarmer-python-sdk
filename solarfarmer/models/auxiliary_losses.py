from ._base import SolarFarmerBaseModel


class AuxiliaryLosses(SolarFarmerBaseModel):
    """Auxiliary power consumption and losses.

    All fields are optional. Provide only the fields relevant to the
    chosen loss modelling approach.

    Attributes
    ----------
    simple_loss_factor : float or None
        Simple loss as a fraction of AC output
    apply_simple_loss_factor_at_night : bool or None
        Whether to apply the simple loss factor during night hours
    simple_loss_power : float or None
        Constant power loss in watts
    fixed_daytime : float or None
        Fixed daytime auxiliary consumption in watts
    threshold_for_fixed : float or None
        Irradiance threshold for fixed daytime losses in W/m²
    variable_daytime : float or None
        Variable daytime auxiliary consumption as a fraction
    threshold_for_variable : float or None
        Irradiance threshold for variable daytime losses in W/m²
    night_consumption : float or None
        Night-time auxiliary consumption in watts
    """

    simple_loss_factor: float | None = None
    apply_simple_loss_factor_at_night: bool | None = None
    simple_loss_power: float | None = None
    fixed_daytime: float | None = None
    threshold_for_fixed: float | None = None
    variable_daytime: float | None = None
    threshold_for_variable: float | None = None
    night_consumption: float | None = None
