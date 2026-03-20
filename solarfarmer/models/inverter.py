from __future__ import annotations

from typing import Any

from pydantic import Field

from ._base import SolarFarmerBaseModel
from .layout import Layout


class Inverter(SolarFarmerBaseModel):
    """An inverter with its connected layouts.

    Attributes
    ----------
    inverter_spec_id : str
        Reference to an inverter specification (OND file key)
    inverter_count : int
        Number of identical inverters, >= 1
    layouts : list[Layout] or None
        Layouts connected to this inverter (2D calculations)
    inverter_inputs : list[Any] or None
        Inverter inputs for 3D calculations
    ac_wiring_ohmic_loss : float
        AC wiring ohmic loss as a fraction, range [0, 1]
    name : str or None
        Optional descriptive name
    """

    inverter_spec_id: str = Field(..., alias="inverterSpecID", min_length=1)
    inverter_count: int = Field(..., ge=1)
    layouts: list[Layout] | None = None
    inverter_inputs: list[Any] | None = None
    ac_wiring_ohmic_loss: float = Field(0.0, ge=0, le=1)
    name: str | None = None
