from pydantic import field_validator

from ._base import SolarFarmerBaseModel
from .enums import InverterOverPowerShutdownMode


class OndFileSupplements(SolarFarmerBaseModel):
    """Overrides and supplements for inverter parameters from an OND file.

    Attributes
    ----------
    inverter_over_power_shutdown_mode : InverterOverPowerShutdownMode
        How the inverter handles over-power conditions
    dc_voltage_derate_voltages : list[float] or None
        DC voltage values for the voltage derate profile. All values >= 0
    dc_voltage_derate_output : list[float] or None
        Output power values for the voltage derate profile. All values >= 0
    """

    inverter_over_power_shutdown_mode: InverterOverPowerShutdownMode = (
        InverterOverPowerShutdownMode.USE_MAXIMUM_MPPT_VOLTAGE
    )
    dc_voltage_derate_voltages: list[float] | None = None
    dc_voltage_derate_output: list[float] | None = None

    @field_validator("dc_voltage_derate_voltages", "dc_voltage_derate_output")
    @classmethod
    def _values_non_negative(cls, v: list[float] | None) -> list[float] | None:
        """Ensure all values are non-negative."""
        if v is not None and any(x < 0 for x in v):
            raise ValueError("all values must be >= 0")
        return v
