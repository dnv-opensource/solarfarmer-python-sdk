from __future__ import annotations

from pydantic import Field

from ._base import SolarFarmerBaseModel
from .enums import PowerOptimizerOperationType
from .module_string import ModuleString


class InverterInput(SolarFarmerBaseModel):
    """An inverter input instance. Used for 3D calculations only.

    Defines the set of module strings connected to a single MPPT input of an
    inverter, together with the DC wiring losses and optional power optimizer
    configuration.

    Attributes
    ----------
    module_specification_id : str
        Reference to the PV module specification used by all strings on this
        input. Must match a key in ``PVPlant.module_specifications`` (or the
        stem of a PAN file uploaded alongside the payload)
    module_strings : list[ModuleString]
        All module strings attached to this inverter input
    dc_ohmic_connector_loss : float
        DC cabling loss as a fraction of DC output power at STC, range [0, 1].
        Converted internally to a connector resistance so the simulated loss
        will vary with irradiance rather than being a fixed percentage
    module_mismatch_loss : float
        Simple fractional loss to account for module mismatch, range [0, 0.1].
        A value of ``0.01`` represents a 1 % loss
    dc_ohmic_connector_resistance : float or None
        DC cabling resistance in ohms (Ω). Alternative to
        ``dc_ohmic_connector_loss``: when non-null this value is used directly
        and ``dc_ohmic_connector_loss`` is ignored
    module_quality_factor : float or None
        Fractional adjustment for other modelling corrections, range [-0.4, 0.1].
        A positive value implies a gain; negative implies a loss
    optimizer_specification_id : str or None
        Reference to the DC power optimizer specification. Must match a key in
        ``PVPlant.optimizer_specifications`` when power optimizers are present
    optimizers_per_module : PowerOptimizerOperationType or None
        Number and connection configuration of power optimizers per module.
        Required when ``optimizer_specification_id`` is provided
    fixed_voltage_from_inverter : float or None
        Fixed DC bus voltage (V) assumed at the inverter output when power
        optimizers are in place
    """

    module_specification_id: str = Field(..., alias="moduleSpecificationID", min_length=1)
    module_strings: list[ModuleString] = Field(default_factory=list)
    dc_ohmic_connector_loss: float = Field(0.0, ge=0, le=1)
    module_mismatch_loss: float = Field(0.0, ge=0, le=0.1)
    dc_ohmic_connector_resistance: float | None = Field(None, ge=0)
    module_quality_factor: float | None = Field(None, ge=-0.4, le=0.1)
    optimizer_specification_id: str | None = Field(None, alias="optimizerSpecificationID")
    optimizers_per_module: PowerOptimizerOperationType | None = None
    fixed_voltage_from_inverter: float | None = Field(None, ge=0)
