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
"""

__all__ = ["TSV_COLUMNS"]

TSV_COLUMNS: dict = {
    # Required columns — parser raises FormatException if absent.
    # DateTime must be the first column; others may appear in any order.
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
    # Optional columns — omitting them is accepted.
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
    # Both 9999 and -9999 are treated as missing; 9999.0 / -9999.000 also accepted.
    # Behaviour on missing data is controlled by EnergyCalculationOptions.missing_met_data_handling.
    "missing_value_sentinel": 9999,
}
