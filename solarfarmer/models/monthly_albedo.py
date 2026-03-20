from pydantic import Field, field_validator, model_serializer, model_validator

from ._base import SolarFarmerBaseModel


class MonthlyAlbedo(SolarFarmerBaseModel):
    """Twelve monthly ground albedo values.

    Serializes as a bare JSON array to match the SolarFarmer API schema where
    ``monthlyAlbedo`` is ``List<double>``.

    Attributes
    ----------
    values : list[float]
        Exactly 12 albedo values (Jan-Dec), each within [0, 1]
    """

    values: list[float] = Field(..., min_length=12, max_length=12)

    @model_validator(mode="before")
    @classmethod
    def _coerce_from_list(cls, data: object) -> object:
        """Accept a bare list during JSON deserialization.

        The model serializes as a bare JSON array via ``_serialize_as_list``.
        This validator allows Pydantic to reconstruct the model from that same
        representation when deserializing saved payloads.
        """
        if isinstance(data, list):
            return {"values": data}
        return data

    @field_validator("values")
    @classmethod
    def _validate_range(cls, v: list[float]) -> list[float]:
        """Ensure each value is in [0, 1]."""
        if any(not 0 <= x <= 1 for x in v):
            raise ValueError("each monthly albedo value must be between 0 and 1")
        return v

    @model_serializer
    def _serialize_as_list(self) -> list[float]:
        """Serialize as a bare list to match the API schema."""
        return self.values

    @classmethod
    def from_list(cls, values: list[float]) -> "MonthlyAlbedo":
        """Create from a plain list of 12 floats.

        Parameters
        ----------
        values : list[float]
            Twelve monthly albedo values

        Returns
        -------
        MonthlyAlbedo
            Validated instance
        """
        return cls(values=values)
