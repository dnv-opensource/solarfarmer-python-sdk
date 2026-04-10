from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SolarFarmerBaseModel(BaseModel):
    """Base class for all SolarFarmer data models"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        use_enum_values=True,
        protected_namespaces=(),
    )
