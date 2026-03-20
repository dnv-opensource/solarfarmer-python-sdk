from enum import Enum


class DiffuseModel(str, Enum):
    """Diffuse transposition model for converting horizontal to tilted irradiance."""

    ISOTROPIC = "Isotropic"
    HAY = "Hay"
    PEREZ = "Perez"
    PEREZ_EMULATE_PVSYST = "PerezEmulatePVsyst"


class MissingMetDataMethod(str, Enum):
    """Behaviour when required meteorological variables have missing data."""

    FAIL_ON_VALIDATION = "FailOnValidation"
    REMOVE_TIMESTAMP = "RemoveTimestamp"


class HorizonType(str, Enum):
    """Azimuth convention of the horizon file.

    Different data providers use different azimuth conventions.
    This controls how horizon azimuths are interpreted.
    """

    FROM_NORTH_CLOCKWISE = "FromNorthClockWise"
    FROM_NORTH_COUNTERCLOCKWISE = "FromNorthCounterClockwise"
    FROM_SOUTH_COUNTERCLOCKWISE = "FromSouthCounterClockWise"
    PVSYST_HEMISPHERE_AWARE = "PVsystHemisphereAware"


class OrderColumnsPvSystFormatTimeSeries(str, Enum):
    """Column ordering for PVsyst-format time-series output."""

    ALPHABETIC = "Alphabetic"
    CALCULATION = "Calculation"


class TransformerLossModelTypes(str, Enum):
    """Transformer loss model type."""

    SIMPLE_LOSS_FACTOR = "SimpleLossFactor"
    NO_LOAD_AND_OHMIC = "NoLoadAndOhmic"


class InverterOverPowerShutdownMode(str, Enum):
    """Inverter behaviour when over-power shutdown conditions occur."""

    USE_MAXIMUM_MPPT_VOLTAGE = "UseMaximumMpptVoltage"
    USE_VOLTAGE_DERATE_PROFILE = "UseVoltageDerateProfile"


class IAMModelTypeForOverride(str, Enum):
    """IAM model types available for overriding the PAN file default."""

    FRESNEL_NORMAL = "FresnelNormal"
    PVSYST_FRESNEL_AR = "PvsystFresnelAR"
    PVEL_FRESNEL_AR = "PvelFresnelAR"
    CIEMAT = "Ciemat"
    CUSTOM = "Custom"


class MeteoFileFormat(str, Enum):
    """Meteorological file format."""

    DAT = "dat"
    TSV = "tsv"
    PVSYST_STANDARD_FORMAT = "PvSystStandardFormat"
    PROTOBUF_GZ = "ProtobufGz"
