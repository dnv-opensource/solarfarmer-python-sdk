from __future__ import annotations

from ._base import SolarFarmerBaseModel
from .auxiliary_losses import AuxiliaryLosses
from .mounting_type_specification import MountingTypeSpecification
from .tracker_system import TrackerSystem
from .transformer import Transformer
from .transformer_specification import TransformerSpecification


class PVPlant(SolarFarmerBaseModel):
    """Electrical topology of a photovoltaic plant.

    Composes transformers, inverters, layouts, and their associated
    specifications into the ``pvPlant`` section of the API payload.

    Attributes
    ----------
    transformers : list[Transformer]
        Transformers in the plant. At least one is required
    mounting_type_specifications : dict[str, MountingTypeSpecification]
        Mounting type specs keyed by ID
    grid_connection_limit : float or None
        Maximum power that can be exported from the transformers in MW
    tracker_systems : dict[str, TrackerSystem] or None
        Tracker system specs keyed by ID. Required when layouts use trackers
    transformer_specifications : dict[str, TransformerSpecification] or None
        Transformer specs keyed by ID
    auxiliary_losses : AuxiliaryLosses or None
        Plant-level auxiliary losses
    """

    transformers: list[Transformer]
    mounting_type_specifications: dict[str, MountingTypeSpecification]
    grid_connection_limit: float | None = None
    tracker_systems: dict[str, TrackerSystem] | None = None
    transformer_specifications: dict[str, TransformerSpecification] | None = None
    auxiliary_losses: AuxiliaryLosses | None = None
