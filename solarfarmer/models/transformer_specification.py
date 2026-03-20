from pydantic import Field, model_validator

from ._base import SolarFarmerBaseModel
from .enums import TransformerLossModelTypes


class TransformerSpecification(SolarFarmerBaseModel):
    """Specification for transformer loss modelling.

    When ``model_type`` is ``SimpleLossFactor``, ``loss_factor`` is required.
    When ``model_type`` is ``NoLoadAndOhmic``, ``rated_power``,
    ``no_load_loss``, and ``full_load_ohmic_loss`` are required.

    Attributes
    ----------
    model_type : TransformerLossModelTypes
        The loss model to use
    loss_factor : float or None
        Simple loss factor as a fraction, range [0, 1]
    rated_power : float or None
        Rated power in watts, >= 0
    no_load_loss : float or None
        No-load (iron) loss in watts, >= 0
    full_load_ohmic_loss : float or None
        Full-load copper loss in watts, >= 0
    """

    model_type: TransformerLossModelTypes
    loss_factor: float | None = Field(None, ge=0, le=1)
    rated_power: float | None = Field(None, ge=0)
    no_load_loss: float | None = Field(None, ge=0)
    full_load_ohmic_loss: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _check_required_fields_for_model_type(self) -> "TransformerSpecification":
        """Validate that required fields are present for the chosen model type."""
        mt = self.model_type
        if mt == TransformerLossModelTypes.SIMPLE_LOSS_FACTOR:
            if self.loss_factor is None:
                raise ValueError("loss_factor is required when model_type is SimpleLossFactor")
        elif mt == TransformerLossModelTypes.NO_LOAD_AND_OHMIC:
            missing = [
                name
                for name in ("rated_power", "no_load_loss", "full_load_ohmic_loss")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"{', '.join(missing)} required when model_type is NoLoadAndOhmic")
        return self
