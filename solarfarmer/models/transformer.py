from __future__ import annotations

from pydantic import Field

from ._base import SolarFarmerBaseModel
from .inverter import Inverter


class Transformer(SolarFarmerBaseModel):
    """A transformer aggregating one or more inverters.

    Attributes
    ----------
    transformer_count : int
        Number of identical transformers, >= 1
    inverters : list[Inverter]
        Inverters connected to this transformer
    name : str or None
        Optional descriptive name
    transformer_spec_id : str or None
        Reference to a transformer specification
    """

    transformer_count: int = Field(1, ge=1)
    inverters: list[Inverter] = Field(default_factory=list)
    name: str | None = None
    transformer_spec_id: str | None = Field(None, alias="transformerSpecID", min_length=1)
