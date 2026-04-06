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
    """Meteorological file format.

    The SDK maps file extensions to the correct multipart upload field
    automatically:

    - ``.dat`` → ``tmyFile`` (Meteonorm hourly TMY)
    - ``.tsv`` → ``tmyFile`` (SolarFarmer tab-separated values)
    - ``.csv`` → ``pvSystStandardFormatFile`` (PVsyst standard format)
    - ``.gz``  → ``metDataTransferFile`` (SolarFarmer desktop binary export)

    For TSV column names, units, timestamp format, and accepted header aliases,
    see :data:`solarfarmer.weather.TSV_COLUMNS` or the user guide:
    https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/DefineClimate/SolarResources.html
    """

    DAT = "dat"
    """Meteonorm PVsyst Hourly TMY format (``.dat``)."""
    TSV = "tsv"
    """SolarFarmer tab-separated values format (``.tsv``).

    Tab-separated, one row per timestep. Timestamp format is
    ``YYYY-MM-DDThh:mm+OO:OO`` (ISO 8601, mandatory UTC offset,
    ``T`` separator required, no seconds component). Example::

        DateTime                GHI       DHI       Temp    Water   Pressure  Albedo  Soiling
        2011-02-02T13:40+00:00  1023.212  1175.619  23.123  1.4102  997       0.2     0.01
        2011-02-02T13:50+00:00  1026.319  1175.092  23.322  2.0391  997       0.2     0.02
        2011-02-02T14:00+00:00   871.987  1008.851  23.764  8.9167  1004      0.2     0.03

    See :data:`solarfarmer.weather.TSV_COLUMNS` for the full column
    specification including required/optional columns, units, ranges,
    and accepted header aliases.
    """
    PVSYST_STANDARD_FORMAT = "PvSystStandardFormat"
    """PVsyst standard CSV export format (``.csv``)."""
    PROTOBUF_GZ = "ProtobufGz"
    """SolarFarmer desktop binary transfer format (protobuf, gzip-compressed, ``.gz``)."""
