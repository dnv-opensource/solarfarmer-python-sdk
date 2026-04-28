"""SolarFarmer TSV weather file format specification.

:data:`TSV_COLUMNS` documents the SolarFarmer tab-separated values (TSV)
meteorological file format: required and optional columns, units, valid
ranges, missing-value sentinel, and accepted header aliases.

Example (tab-separated, from SF-Core test data)::

    DateTime                GHI       DHI       Temp    Water   Pressure  Albedo  Soiling
    2011-02-02T13:40+00:00  1023.212  1175.619  23.123  1.4102  997       0.2     0.01
    2011-02-02T13:50+00:00  1026.319  1175.092  23.322  2.0391  997       0.2     0.02
    2011-02-02T14:00+00:00   871.987  1008.851  23.764  8.9167  1004      0.2     0.03

Timestamp format: ``YYYY-MM-DDThh:mm+OO:OO`` — mandatory UTC offset,
``T`` separator required, no seconds (e.g. ``2011-02-02T13:40+00:00``).

TMY Data Warning
~~~~~~~~~~~~~~~~
Typical Meteorological Year (TMY) datasets (e.g., from NSRDB PSM or PVGIS)
contain timestamps drawn from different source years.  When writing a TSV file
from TMY data, **remap all timestamps to a single calendar year** (e.g., 1990)
before export; otherwise the shuffled years will be detected as non-sequential
and the SDK will raise a ``ValueError``.

Multi-year and sub-year TSV files with **chronologically ordered** timestamps
are fully supported — only non-sequential (shuffled) years are rejected.

pvlib Column Mapping
~~~~~~~~~~~~~~~~~~~~
When converting a ``pvlib`` DataFrame to SolarFarmer TSV format, map the
pvlib variable names to SolarFarmer column names as shown below.  pvlib does
not standardise units across data sources — verify that your source's units
match SolarFarmer requirements (see :data:`TSV_COLUMNS` for the full spec):

==============  ===========
pvlib column    SF column
==============  ===========
``ghi``         ``GHI``
``dhi``         ``DHI``
``temp_air``    ``TAmb``
``wind_speed``  ``WS``
``pressure``    ``Pressure``
==============  ===========

For example, NSRDB PSM provides pressure in Pa and must be converted to
mbar (÷ 100); other sources may already be in mbar.  Use
``pressure_pa_to_mbar=True`` in :func:`from_dataframe` when your source
delivers pressure in Pa.

Minimal conversion example (NSRDB PSM, pressure in Pa)::

    import pandas as pd

    rename = {"ghi": "GHI", "dhi": "DHI", "temp_air": "TAmb",
              "wind_speed": "WS", "pressure": "Pressure"}
    df = pvlib_df.rename(columns=rename)
    df["Pressure"] = df["Pressure"] / 100          # Pa → mbar (NSRDB PSM)
    df.index = df.index.map(
        lambda t: t.replace(year=1990).strftime("%Y-%m-%dT%H:%M+00:00")
    )
    df.index.name = "DateTime"
    df.to_csv("weather.tsv", sep="\\t")

Solcast Column Mapping
~~~~~~~~~~~~~~~~~~~~~~
When converting a Solcast DataFrame to SolarFarmer TSV format, the following
column mapping and unit conversions are applied automatically by
:func:`from_solcast`.

Solcast ``period_end`` timestamps are shifted to period-beginning by
subtracting the inferred time resolution (e.g. −30 min for 30-min data).
``precipitable_water`` is in kg/m² (equivalent to mm) and is divided by 10
to obtain cm as required by SolarFarmer.  ``surface_pressure`` is already in
hPa which equals mbar, so no pressure conversion is needed.

Only columns that are present in the DataFrame are mapped; ``period_end``,
``air_temp``, and ``ghi`` are the most commonly available columns but the
others are all optional.  The ``gti`` (plane-of-array irradiance) column is
not mapped; SolarFarmer derives POA irradiance internally from GHI/DHI.

=======================  ===========  =====================================
Solcast column           SF column    Unit conversion
=======================  ===========  =====================================
``ghi``                  ``GHI``      W/m² → W/m² (none)
``dhi``                  ``DHI``      W/m² → W/m² (none)
``air_temp``             ``TAmb``     °C → °C (none)
``wind_speed_10m``       ``WS``       m/s → m/s (none)
``surface_pressure``     ``Pressure`` hPa → mbar (hPa = mbar, none)
``precipitable_water``   ``Water``    kg/m² → cm (÷ 10)
``relative_humidity``    ``RH``       % → % (none)
``albedo``               ``Albedo``   fraction → fraction (none)
``hsu_loss_fraction``    ``Soiling``  fraction → fraction (none)
``kimber_loss_fraction`` ``Soiling``  fraction → fraction (none)
``soiling``              ``Soiling``  fraction → fraction (none)
=======================  ===========  =====================================

.. note::
   Only one soiling column should be present in the DataFrame. If multiple
   are provided, the last one wins after column renaming.
"""

from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from .config import PANDAS_INSTALL_MSG

__all__ = [
    "TSV_COLUMNS",
    "check_sequential_year_timestamps",
    "from_dataframe",
    "from_pvlib",
    "from_solcast",
    "from_src",
    "shift_period_end_to_beginning",
]


def check_sequential_year_timestamps(file_path: str | pathlib.Path) -> None:
    """Check that timestamp years in a TSV weather file are chronologically ordered.

    Allows single-year, sub-year, and multi-year continuous data.  Rejects
    files whose years go *backwards* — the hallmark of unprocessed TMY data
    that mixes months from different source years.

    Parameters
    ----------
    file_path : str or Path
        Path to the TSV weather file.

    Raises
    ------
    ValueError
        If any timestamp year is earlier than the preceding timestamp year
        (i.e., years are not non-decreasing).
    """
    path = pathlib.Path(file_path)
    year_pattern = re.compile(r"^(\d{4})-")
    prev_year: int | None = None

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = year_pattern.match(line)
            if m:
                year = int(m.group(1))
                if prev_year is not None and year < prev_year:
                    raise ValueError(
                        f"TSV weather file contains non-sequential years: "
                        f"year {year} follows year {prev_year}. This usually "
                        f"indicates unprocessed TMY data with months from "
                        f"different source years. Remap all timestamps to a "
                        f"single year (e.g., 1990) before submission."
                    )
                prev_year = year


PVLIB_COLUMN_MAP: dict[str, str] = {
    "ghi": "GHI",
    "dhi": "DHI",
    "temp_air": "TAmb",
    "wind_speed": "WS",
    "pressure": "Pressure",
}

SRC_COLUMN_MAP: dict[str, str] = {
    "GHI": "GHI",
    "DHI": "DHI",
    "Tamb": "TAmb",
    "Wspd": "WS",
}

SOLCAST_COLUMN_MAP: dict[str, str] = {
    "ghi": "GHI",
    "dhi": "DHI",
    "air_temp": "TAmb",
    "wind_speed_10m": "WS",
    "surface_pressure": "Pressure",
    "precipitable_water": "Water",
    "relative_humidity": "RH",
    "albedo": "Albedo",
    "hsu_loss_fraction": "Soiling",
    "kimber_loss_fraction": "Soiling",
    "soiling": "Soiling",
}


def from_dataframe(
    df: pd.DataFrame,
    output_path: str | pathlib.Path,
    *,
    column_map: dict[str, str] | None = None,
    year: int | None = None,
    pressure_pa_to_mbar: bool = False,
) -> pathlib.Path:
    """Write a DataFrame to a SolarFarmer TSV weather file.

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[all]'``.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a DatetimeIndex and meteorological columns.
    output_path : str or Path
        Destination file path.
    column_map : dict[str, str], optional
        DataFrame column names → SolarFarmer TSV column names.
        Columns not in the map are passed through unchanged.
    year : int, optional
        Remap all timestamps to this calendar year (needed for TMY data).
    pressure_pa_to_mbar : bool, default False
        Divide the ``Pressure`` column by 100 (Pa → mbar) after renaming.

    Returns
    -------
    pathlib.Path

    Raises
    ------
    ValueError
        If the DataFrame has no DatetimeIndex.
    ImportError
        If pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(PANDAS_INSTALL_MSG) from None

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "DataFrame must have a DatetimeIndex. "
            "Use df.set_index(pd.to_datetime(df['timestamp'])) or similar."
        )

    out = df.copy()

    if column_map:
        out = out.rename(columns=column_map)

    if pressure_pa_to_mbar and "Pressure" in out.columns:
        out["Pressure"] = out["Pressure"] / 100

    if year is not None:
        out.index = out.index.map(lambda t: t.replace(year=year))

    out.index = out.index.map(lambda t: t.isoformat(timespec="minutes"))
    out.index.name = "DateTime"

    path = pathlib.Path(output_path)
    out.to_csv(path, sep="\t")
    return path


def from_pvlib(
    df: pd.DataFrame,
    output_path: str | pathlib.Path,
    *,
    year: int = 1990,
) -> pathlib.Path:
    """Convert a pvlib DataFrame to a SolarFarmer TSV weather file.

    Wrapper around :func:`from_dataframe` with the standard pvlib column
    mapping and Pa → mbar pressure conversion.

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[all]'``.

    Parameters
    ----------
    df : pandas.DataFrame
        pvlib-style DataFrame (columns ``ghi``, ``dhi``, ``temp_air``,
        ``wind_speed``, ``pressure``) with a DatetimeIndex.  pvlib does not
        standardise units across data sources, so check that the units from
        your source match what SolarFarmer expects (see :data:`TSV_COLUMNS`).
        This function applies ``pressure_pa_to_mbar=True``, dividing the
        ``Pressure`` column by 100 (Pa → mbar).  NSRDB PSM delivers pressure
        in Pa so this conversion is correct for that source; if your source
        already provides pressure in mbar, call :func:`from_dataframe`
        directly with ``pressure_pa_to_mbar=False``.
    output_path : str or Path
        Destination file path.
    year : int, default 1990
        Remap all timestamps to this calendar year.

    Returns
    -------
    pathlib.Path
    """
    return from_dataframe(
        df,
        output_path,
        column_map=PVLIB_COLUMN_MAP,
        year=year,
        pressure_pa_to_mbar=True,
    )


def from_src(
    weather_hourly: list[dict],
    output_path: str | pathlib.Path,
    *,
    year: int | None = None,
) -> pathlib.Path:
    """Convert a DNV Solar Resource Compass (SRC) hourly dataset to a SolarFarmer TSV file.

    Accepts the ``weather_hourly`` list returned by
    `WCompare` endpoint of DNV Solar Resource Compass API and writes a
    SolarFarmer-compatible TSV weather file.

    SRC ``Timestamp`` values represent ``period_end``; SolarFarmer expects
    ``period_beginning``.  The time resolution is inferred automatically and
    subtracted from every timestamp via :func:`shift_period_end_to_beginning`.

    The ``Timestamp`` field (e.g. ``"2059-01-01 01:00:00-07:00"``) is parsed
    into a timezone-aware DatetimeIndex.  Column names are mapped as follows:

    =========  ===========
    SRC column SF column
    =========  ===========
    ``GHI``    ``GHI``
    ``DHI``    ``DHI``
    ``Tamb``   ``TAmb``
    ``Wspd``   ``WS``
    =========  ===========

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[all]'``.

    Parameters
    ----------
    weather_hourly : list[dict]
        The ``weather_hourly`` attribute of the
        `WCompare` endpoint response of DNV Solar Resource Compass API.  
        Each dict must contain a ``Timestamp`` key and
        any subset of ``GHI``, ``DHI``, ``Tamb``, ``Wspd``.
    output_path : str or Path
        Destination file path.
    year : int, optional
        Remap all timestamps to this calendar year.  Use ``year=1990`` when
        the TMY source years are not chronologically sequential.

    Returns
    -------
    pathlib.Path

    Raises
    ------
    ValueError
        If ``weather_hourly`` is empty or contains no ``Timestamp`` key.
    ImportError
        If pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(PANDAS_INSTALL_MSG) from None

    if not weather_hourly:
        raise ValueError("weather_hourly is empty; nothing to write.")

    df = pd.DataFrame(weather_hourly)

    if "Timestamp" not in df.columns:
        raise ValueError(
            "weather_hourly records must contain a 'Timestamp' key. "
            "Check that the WcompareResult (Solar Resource Compass API) was populated correctly."
        )

    df.index = pd.to_datetime(df["Timestamp"], utc=False)
    df.index.name = "DateTime"
    df = df.drop(columns=["Timestamp"])

    # SRC Timestamps are period_end; SolarFarmer expects period_beginning.
    df = shift_period_end_to_beginning(df)

    return from_dataframe(
        df,
        output_path,
        column_map=SRC_COLUMN_MAP,
        year=year,
    )


def from_solcast(
    df: pd.DataFrame,
    output_path: str | pathlib.Path,
) -> pathlib.Path:
    """Convert a Solcast DataFrame to a SolarFarmer TSV weather file.

    Wrapper around :func:`from_dataframe` with the standard Solcast column
    mapping.  Two automatic conversions are applied before writing:

    * **Timestamp shift**: Solcast timestamps represent ``period_end``;
      SolarFarmer expects ``period_beginning``.  The time resolution is
      inferred from the minimum consecutive time difference and subtracted
      from every timestamp.
    * **Precipitable water**: Solcast ``precipitable_water`` is in kg/m²
      (equivalent to mm); SolarFarmer expects cm, so the column is divided
      by 10.

    ``surface_pressure`` is already in hPa which equals mbar, so no pressure
    conversion is needed.

    Only columns that are present in the DataFrame are mapped; the minimum
    required columns are ``period_end`` (as the index), ``air_temp``, and
    ``ghi``.  All other columns (``dhi``, ``wind_speed_10m``,
    ``surface_pressure``, ``precipitable_water``, ``relative_humidity``,
    ``albedo``, ``hsu_loss_fraction``, ``kimber_loss_fraction``, ``soiling``)
    are optional and mapped when present.

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[all]'``.

    Parameters
    ----------
    df : pandas.DataFrame
        Solcast-style DataFrame with a DatetimeIndex (``period_end``) and
        any subset of columns: ``ghi``, ``dhi``, ``air_temp``,
        ``wind_speed_10m``, ``surface_pressure``, ``precipitable_water``,
        ``relative_humidity``, ``albedo``, ``hsu_loss_fraction``,
        ``kimber_loss_fraction``, ``soiling``.  Unmapped columns are removed.
        Only one soiling column should be present; if multiple are provided,
        the last one wins after column renaming.
    output_path : str or Path
        Destination file path.

    Returns
    -------
    pathlib.Path

    Raises
    ------
    ValueError
        If the DataFrame has no DatetimeIndex.
    ImportError
        If pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(PANDAS_INSTALL_MSG) from None

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "DataFrame must have a DatetimeIndex. "
            "Use df.set_index(pd.to_datetime(df['period_end'])) or similar."
        )

    out = df.copy()

    # Solcast timestamps are period_end; SolarFarmer expects period_beginning.
    out = shift_period_end_to_beginning(out)

    # Drop columns that have no SolarFarmer equivalent (e.g. gti, any other custom fields).
    out = out[[c for c in out.columns if c in SOLCAST_COLUMN_MAP]]

    # precipitable_water: Solcast provides kg/m² (= mm); SolarFarmer expects cm.
    if "precipitable_water" in out.columns:
        out["precipitable_water"] = out["precipitable_water"] / 10

    return from_dataframe(
        out,
        output_path,
        column_map=SOLCAST_COLUMN_MAP,
        pressure_pa_to_mbar=False,  # Solcast surface_pressure is hPa = mbar
    )


def shift_period_end_to_beginning(df: pd.DataFrame) -> pd.DataFrame:
    """Shift DatetimeIndex from period_end to period_beginning.

    Infers the time resolution from the minimum consecutive time difference
    and subtracts it from all timestamps. Useful for converters where the
    source data provides period_end timestamps but the target format expects
    period_beginning.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a DatetimeIndex representing period_end timestamps.

    Returns
    -------
    pandas.DataFrame
        DataFrame with DatetimeIndex shifted to period_beginning.

    Raises
    ------
    ValueError
        If the DataFrame has no DatetimeIndex.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(PANDAS_INSTALL_MSG) from None

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "DataFrame must have a DatetimeIndex. "
            "Use df.set_index(pd.to_datetime(df['period_end'])) or similar."
        )

    out = df.copy()
    time_deltas = out.index.to_series().diff().dropna()
    inferred_timedelta = time_deltas.median()
    out.index = out.index - inferred_timedelta
    return out


TSV_COLUMNS: dict = {
    "required": [
        {
            "name": "DateTime",
            "unit": None,
            "format": "YYYY-MM-DDThh:mm+OO:OO",
            "note": "ISO 8601 with mandatory UTC offset; T separator required; no seconds. Must be the first column.",
            "aliases": ["Date", "DateTime", "Time"],
        },
        {
            "name": "GHI",
            "unit": "W/m²",
            "range": (0, 1300),
            "note": "Required unless POA is provided instead.",
            "aliases": ["GHI", "ghi", "Glob", "SolarTotal"],
        },
        {
            "name": "TAmb",
            "unit": "°C",
            "range": (-35, 60),
            "aliases": ["TAmb", "Temp", "T"],
        },
    ],
    "optional": [
        {
            "name": "DHI",
            "unit": "W/m²",
            "range": (0, 1000),
            "note": (
                "May be omitted only when EnergyCalculationOptions.calculate_dhi=True; "
                "measured DHI is strongly preferred over engine decomposition."
            ),
            "aliases": ["DHI", "diff", "diffuse", "DIF"],
        },
        {
            "name": "WS",
            "unit": "m/s",
            "range": (0, 50),
            "aliases": ["WS", "Wind", "Speed", "WindSpeed"],
        },
        {
            "name": "Pressure",
            "unit": "mbar",
            "range": (750, 1100),
            "note": "Millibar — not Pa, not hPa.",
            "aliases": ["Pressure", "AP", "pressure"],
        },
        {
            "name": "Water",
            "unit": "cm",
            "range": (0, 100),
            "aliases": ["Water", "PW"],
        },
        {
            "name": "RH",
            "unit": "%",
            "range": (0, 100),
            "aliases": ["RH", "Humidity", "humidity"],
        },
        {
            "name": "Albedo",
            "unit": None,
            "range": (0, 1),
            "note": "Used when EnergyCalculationOptions.use_albedo_from_met_data_when_available=True.",
            "aliases": ["Albedo", "Surface Albedo", "albedo"],
        },
        {
            "name": "Soiling",
            "unit": None,
            "range": (0, 1),
            "note": "Used when EnergyCalculationOptions.use_soiling_from_met_data_when_available=True.",
            "aliases": ["Soiling", "SL", "SoilingLoss", "Slg"],
        },
    ],
    "delimiter": "\t",
    "missing_value_sentinel": 9999,
}
