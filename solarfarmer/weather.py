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
contain timestamps drawn from different source years. When writing a TSV file,
**all timestamps must belong to a single contiguous calendar year**. Remap
mixed-year timestamps to one year (e.g., 1990) before export; otherwise the
SolarFarmer API will return an HTTP 400 error with no field-level detail.

pvlib Column Mapping
~~~~~~~~~~~~~~~~~~~~
When converting a ``pvlib`` DataFrame to SolarFarmer TSV format, use the
following column name mapping and note the unit for Pressure:

==============  ===========  ==========================
pvlib column    SF column    Notes
==============  ===========  ==========================
``ghi``         ``GHI``      W/m²
``dhi``         ``DHI``      W/m²
``temp_air``    ``TAmb``     °C
``wind_speed``  ``WS``       m/s
``pressure``    ``Pressure`` **Convert Pa → mbar** (÷ 100)
==============  ===========  ==========================

Minimal conversion example::

    import pandas as pd

    rename = {"ghi": "GHI", "dhi": "DHI", "temp_air": "TAmb",
              "wind_speed": "WS", "pressure": "Pressure"}
    df = pvlib_df.rename(columns=rename)
    df["Pressure"] = df["Pressure"] / 100          # Pa → mbar
    df.index = df.index.map(
        lambda t: t.replace(year=1990).strftime("%Y-%m-%dT%H:%M+00:00")
    )
    df.index.name = "DateTime"
    df.to_csv("weather.tsv", sep="\\t")
"""

from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

_PANDAS_INSTALL_MSG = (
    "pandas is required for this function. Install it with: pip install 'dnv-solarfarmer[weather]'"
)

__all__ = ["TSV_COLUMNS", "check_single_year_timestamps", "from_dataframe", "from_pvlib"]


def check_single_year_timestamps(file_path: str | pathlib.Path) -> None:
    """Check that all timestamps in a TSV weather file belong to a single year.

    Parameters
    ----------
    file_path : str or Path
        Path to the TSV weather file.

    Raises
    ------
    ValueError
        If timestamps span more than one calendar year.
    """
    path = pathlib.Path(file_path)
    year_pattern = re.compile(r"^(\d{4})-")
    years: set[str] = set()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = year_pattern.match(line)
            if m:
                years.add(m.group(1))

    if len(years) > 1:
        sorted_years = sorted(years)
        raise ValueError(
            f"TSV weather file contains timestamps from multiple years: "
            f"{sorted_years}. SolarFarmer requires all timestamps to belong "
            f"to a single contiguous calendar year. Remap timestamps to one "
            f"year (e.g., 1990) before submission."
        )


PVLIB_COLUMN_MAP: dict[str, str] = {
    "ghi": "GHI",
    "dhi": "DHI",
    "temp_air": "TAmb",
    "wind_speed": "WS",
    "pressure": "Pressure",
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

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[weather]'``.

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
        raise ImportError(_PANDAS_INSTALL_MSG) from None

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

    out.index = out.index.map(
        lambda t: t.strftime("%Y-%m-%dT%H:%M") + t.strftime("%z")[:3] + ":" + t.strftime("%z")[3:]
    )
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

    .. note:: Requires ``pandas``. Install with ``pip install 'dnv-solarfarmer[weather]'``.

    Parameters
    ----------
    df : pandas.DataFrame
        pvlib-style DataFrame (``ghi``, ``dhi``, ``temp_air``,
        ``wind_speed``, ``pressure``) with a DatetimeIndex.
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
