from pydantic import Field

from ._base import SolarFarmerBaseModel
from .enums import IAMModelTypeForOverride


class PanFileSupplements(SolarFarmerBaseModel):
    """Overrides and supplements for module parameters from a PAN file.

    Attributes
    ----------
    modeling_correction_factor : float
        Module modelling correction factor, range [0.9, 1.1]
    recalculate_modeling_correction_factor : bool
        Whether SolarFarmer should recalculate the correction factor
    module_quality_factor : float
        Module quality factor, range [-0.4, 0.1]
    power_binning_effect : float or None
        Power binning effect, range [-0.1, 0.1]
    lid_loss : float or None
        Light-induced degradation loss, range [0, 0.1]
    bifaciality_factor : float or None
        Module bifaciality factor, range [0, 1]
    iam_model_type_override : IAMModelTypeForOverride or None
        Override the IAM model from the PAN file
    iam_ciemat_ar_parameter : float or None
        CIEMAT AR parameter, range [0.01, 0.3]
    band_gap_override : float or None
        Bandgap energy override in eV
    custom_profile_angles : list[float] or None
        Custom IAM profile incidence angles in degrees
    custom_profile_iam_values : list[float] or None
        Custom IAM profile values corresponding to ``custom_profile_angles``
    """

    modeling_correction_factor: float = Field(1.0, ge=0.9, le=1.1)
    recalculate_modeling_correction_factor: bool = True
    module_quality_factor: float = Field(0.0, ge=-0.4, le=0.1)
    power_binning_effect: float | None = Field(None, ge=-0.1, le=0.1)
    lid_loss: float | None = Field(None, ge=0, le=0.1)
    bifaciality_factor: float | None = Field(None, ge=0, le=1)
    iam_model_type_override: IAMModelTypeForOverride | None = None
    iam_ciemat_ar_parameter: float | None = Field(None, ge=0.01, le=0.3)
    band_gap_override: float | None = None
    custom_profile_angles: list[float] | None = None
    custom_profile_iam_values: list[float] | None = None
