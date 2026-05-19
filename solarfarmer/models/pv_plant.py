from __future__ import annotations

from typing import Any

from pydantic import model_validator

from ._base import SolarFarmerBaseModel
from .auxiliary_losses import AuxiliaryLosses
from .indexed_object3d import IndexedObject3D
from .mounting_type_specification import MountingTypeSpecification
from .rack import Rack
from .simple_terrain import SimpleTerrain
from .tracker import Tracker
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
        Maximum power that can be exported from the transformers, in Watts (W).
        Example: 17.6 MW → ``grid_connection_limit=17600000``
    tracker_systems : dict[str, TrackerSystem] or None
        Tracker system specs keyed by ID. Required when layouts use trackers
    transformer_specifications : dict[str, TransformerSpecification] or None
        Transformer specs keyed by ID. Required by the API when the AC
        model is enabled (the default). Omitting this field causes an
        HTTP 400 error. The key must match ``Transformer.transformer_spec_id``.
    auxiliary_losses : AuxiliaryLosses or None
        Plant-level auxiliary losses
    racks : list[Rack] or None
        Fixed-tilt rack objects for 3D calculations. Not required for 2D
    shading_objects : list[IndexedObject3D] or None
        3D shading obstacles (buildings, terrain features, etc.). Used for
        3D calculations; ignored for 2D
    simple_terrain : SimpleTerrain or None
        Ground surface terrain model for 3D calculations. Ignored for 2D
    trackers : list[Tracker] or None
        Single-axis tracker objects for 3D calculations. Not required for 2D
    inverter_specifications : dict[str, Any] or None
        Inverter specifications keyed by spec ID. Not required when the
        inverter spec is populated from OND files
    module_specifications : dict[str, Any] or None
        Module specifications keyed by spec ID. Not required when the
        module spec is populated from PAN files
    optimizer_specifications : dict[str, Any] or None
        Power optimizer specifications keyed by spec ID. Not required when
        the optimizer spec is populated from DCO files
    """

    transformers: list[Transformer]
    mounting_type_specifications: dict[str, MountingTypeSpecification]
    grid_connection_limit: float | None = None
    tracker_systems: dict[str, TrackerSystem] | None = None
    transformer_specifications: dict[str, TransformerSpecification] | None = None
    auxiliary_losses: AuxiliaryLosses | None = None
    racks: list[Rack] | None = None
    shading_objects: list[IndexedObject3D] | None = None
    simple_terrain: SimpleTerrain | None = None
    trackers: list[Tracker] | None = None
    inverter_specifications: dict[str, Any] | None = None
    module_specifications: dict[str, Any] | None = None
    optimizer_specifications: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check_transformer_spec_references(self) -> PVPlant:
        """Validate that referenced transformer spec IDs exist in transformer_specifications."""
        for i, transformer in enumerate(self.transformers):
            spec_id = transformer.transformer_spec_id
            if spec_id is None:
                continue
            if (
                self.transformer_specifications is None
                or spec_id not in self.transformer_specifications
            ):
                available = sorted(self.transformer_specifications or {})
                raise ValueError(
                    f"Transformer {i} references spec ID '{spec_id}' which is "
                    f"not in transformer_specifications. Available: {available}"
                )
        return self
