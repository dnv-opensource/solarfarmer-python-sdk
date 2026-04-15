# SolarFarmer Python SDK — Weather File Discoverability Feedback

## Context

This document captures observations from building a batch energy-yield runner
on top of `dnv-solarfarmer>=0.2.0rc1`.  The task involved constructing
`EnergyCalculationInputs` payloads for 14 project variants and sourcing
NSRDB PSM4 TMY weather data formatted for the SolarFarmer API.

An AI coding agent (Claude) drove the implementation.  The agent's workflow —
calling `help()`, reading docstrings, inspecting signatures — mirrors how
human developers explore an unfamiliar SDK, and exposes where the discoverable
documentation runs short.  The recommendations below target both audiences;
agents (especially lower-capability ones) are more sensitive to these gaps
because they cannot fall back on domain intuition the way a human might.

---

## 1  What the SDK tells you about weather files today

The table below is the **complete set** of weather-file guidance reachable
from `help()` / docstrings without leaving the REPL:

| Symbol | Documentation |
|--------|---------------|
| `MeteoFileFormat` enum | `"Meteorological file format."` — four values (`dat`, `tsv`, `PvSystStandardFormat`, `ProtobufGz`), no per-value descriptions |
| `EnergyCalculationInputsWithFiles.meteo_file_path_or_contents` | `"Meteorological file path or inline contents"` |
| `EnergyCalculationInputsWithFiles.meteo_file_format` | `"Format of the meteorological file"` |
| `run_energy_calculation(meteorological_data_file_path=...)` | `"Accepts Meteonorm .dat, TSV, a SolarFarmer desktop export (e.g., MeteorologicalConditionsDatasetDto_Protobuf.gz), or PVsyst standard format .csv files"` |
| `parse_files_from_paths()` | `"Accepted extensions are .tsv, .dat, .csv (PVsyst format), and .gz (protobuf transfer file)"` |
| `MissingMetDataMethod` enum | `FAIL_ON_VALIDATION`, `REMOVE_TIMESTAMP` — no documentation of what constitutes "missing" data |

None of these locations specify column names, column ordering, expected units,
timestamp format, timezone convention, or missing-data sentinel values.

---

## 2  What a developer actually needs to produce a valid weather file

To write the TSV conversion function (`fetch_tmy._to_sf_tsv()`), the
following had to be sourced from the **web-hosted user guide** — not from the
SDK:

| Requirement | What we hard-coded | SDK source |
|-------------|-------------------|------------|
| Column names | `GHI`, `DHI`, `TAmb`, `WS`, `Pressure`, `PW`, `RH` | None |
| Column header aliases | API also accepts e.g. `Glob`/`SolarTotal` for GHI, `diff`/`diffuse`/`DIF` for DHI, `Temp`/`T` for temperature, `Wind`/`WindSpeed` for wind, `Water` for PW, `AP` for pressure, `Humidity` for RH — discovered only by reading API source code (`ReadMetDataFromTSV.cs`) | None |
| Column order matters | Yes — required columns first, optional after | None |
| Timestamp format | `YYYY-MM-DDThh:mm+OO:OO` — **not** `YYYY-MM-DD HH:MM:SS` (see §2.1 below) | None |
| Timezone convention | UTC offset embedded in each timestamp; local standard time with offset | None |
| Units: irradiance | W/m² | None |
| Units: temperature | °C | None |
| Units: wind speed | m/s | None |
| Units: pressure | mbar (not Pa, not hPa) | None |
| Units: precipitable water | cm | None |
| Units: relative humidity | % | None |
| Missing-data sentinel | `9999` or `-9999` | None |
| Value ranges | GHI 0–1300, DHI 0–1000, TAmb −35–60, WS 0–50, Pressure 750–1100, RH 0–100 | None |

And TSV is only one of the four format families the API accepts.  The same
information gap exists for `.dat` (Meteonorm), `.csv` (PVsyst standard
format, NREL SAM, NSRDB TMY3, SolarAnywhere, SolarGIS, Solcast, Vaisala),
and `.gz` (protobuf).  The web user guide lists **11 top-level format
variants**; the SDK enum exposes 4 multipart field types that cover them.

### 2.1  Timestamp format details

The exact timestamp format required by the TSV parser is:

    YYYY-MM-DDThh:mm+OO:OO

Key requirements:

- `T` separator between date and time (not a space)
- No seconds component
- Mandatory UTC offset (e.g. `-06:00`, `+00:00`) — `Z` notation is not
  accepted, and omitting the offset is not accepted
- The API parses timestamps via `DateTimeOffset.ParseExact` with format
  `yyyy-MM-dd'T'HH:mmzzz`

The line-detection regex in the TSV parser (`ReadMetDataFromTSV.cs`) requires
the `T` separator — timestamps without it are not recognized as data lines,
causing the file to appear empty.

**Example valid timestamps:**
```
2001-01-01T00:00-06:00
2001-06-15T12:30+00:00
2019-12-31T23:00-07:00
```

### 2.2  Accepted column header aliases

The TSV parser accepts multiple names for each variable.  These aliases are
defined in `ReadMetDataFromTSV.cs` but not documented in the SDK:

| Variable | Accepted headers |
|----------|-----------------|
| GHI | `GHI`, `ghi`, `Glob`, `SolarTotal` |
| DHI | `DHI`, `diff`, `diffuse`, `DIF` |
| Temperature | `Temp`, `T`, `TAmb` |
| Wind speed | `WS`, `Wind`, `Speed`, `WindSpeed` |
| Precipitable water | `Water`, `PW` |
| Air pressure | `Pressure`, `AP`, `pressure` |
| Relative humidity | `Humidity`, `RH`, `humidity` |
| Albedo | `Surface Albedo`, `Albedo`, `albedo` |
| Soiling | `SL`, `Soiling`, `SoilingLoss`, `Slg` |
| Date/time | `Date`, `DateTime`, `Time` |

Exposing these alias lists in the SDK (e.g. as a dict constant) would let
both humans and agents validate their header names before uploading.

---

## 3  Files that bypass the Pydantic layer

The weather file is not the only input that passes through the SDK as an
opaque path or byte stream.  The full inventory:

| File type | SDK treatment | Pydantic-modelled? | Notes |
|-----------|---------------|-------------------|-------|
| **Weather** (`.dat`, `.tsv`, `.csv`, `.gz`) | `str` path → opened as `rb` → uploaded as multipart `tmyFile` / `pvSystStandardFormatFile` / `metDataTransferFile` | **No** | No column/unit/format schema in SDK |
| **PAN** (module spec) | `str` path → opened as `rb` → uploaded as multipart `panFiles` | **No** — but `PanFileSupplements` models overrides (quality factor, LID, IAM, bifaciality) | PAN format is a PVsyst standard; modelling it is out of scope |
| **OND** (inverter spec) | `str` path → opened as `rb` → uploaded as multipart `ondFiles` | **No** — but `OndFileSupplements` models overrides (over-power mode, voltage derate) | OND format is a PVsyst standard; same reasoning |
| **HOR** (horizon profile) | `str` path → opened as `rb` → uploaded as multipart `horFile` | **Partially** — `EnergyCalculationInputs` has `horizon_azimuths` / `horizon_angles` list fields; `HorizonType` enum describes azimuth conventions | Inline numeric arrays are modelled; the file format is not |

The PAN and OND file formats are owned by PVsyst and widely standardised
across solar modelling tools.  Documenting their internal structure in this
SDK would be out of scope — the SDK's role is to pass them through to the API
unchanged, and the `*Supplements` models appropriately handle the subset of
parameters the user may want to override.

The horizon file is partially covered: if you have the data as arrays, you
can bypass the file entirely via the `horizon_azimuths` / `horizon_angles`
fields.  The `HorizonType` enum documents the azimuth conventions clearly.

**The weather file is the outlier** — not because it's the only file that
bypasses Pydantic, but because:

1. It's the only one whose format is **defined by SolarFarmer itself** (the
   TSV variant in particular).
2. It's the only one where the **user commonly needs to generate or convert**
   the file rather than use an existing one from a data provider.
3. Its format details (columns, units, timestamp handling) are already
   documented in the web user guide — they just aren't surfaced in the SDK.

---

## 4  Recommendations

### 4.1  Enrich the `MeteoFileFormat` enum (minimal cost, immediate impact)

Add per-value docstrings and a link to the full specification:

```python
class MeteoFileFormat(str, Enum):
    """Meteorological file format.

    The API accepts weather data in several formats.  The SDK maps file
    extensions to the correct multipart upload field automatically:

    - ``.dat`` and ``.tsv`` → ``tmyFile``
    - ``.csv`` (PVsyst standard) → ``pvSystStandardFormatFile``
    - ``.gz`` (protobuf) → ``metDataTransferFile``

    For TSV format details (column names, units, timestamp convention),
    see the user guide:
    https://mysoftware.dnv.com/.../DefineClimate/SolarResources.html
    """

    DAT = "dat"
    """Meteonorm PVsyst Hourly TMY format."""
    TSV = "tsv"
    """SolarFarmer tab-separated values — see class docstring for column spec."""
    PVSYST_STANDARD_FORMAT = "PvSystStandardFormat"
    """PVsyst standard CSV export format."""
    PROTOBUF_GZ = "ProtobufGz"
    """SolarFarmer desktop binary transfer format (protobuf, gzip-compressed)."""
```

This is a documentation-only change; no new code, no API surface change.

### 4.2  Add a TSV format specification as a module-level docstring or constants

The TSV format is SolarFarmer's own.  A module (e.g.
`solarfarmer.models.weather` or constants in `solarfarmer.config`) could
expose the spec as discoverable Python objects:

```python
# solarfarmer/models/weather.py

TSV_COLUMNS = {
    "required": [
        {"name": "DateTime", "unit": None,    "format": "YYYY-MM-DDThh:mm+OO:OO", "note": "ISO 8601 with mandatory UTC offset, no seconds, T separator"},
        {"name": "GHI",      "unit": "W/m²",  "range": (0, 1300), "aliases": ["ghi", "Glob", "SolarTotal"]},
        {"name": "TAmb",     "unit": "°C",    "range": (-35, 60), "aliases": ["Temp", "T"]},
    ],
    "optional": [
        {"name": "DHI",      "unit": "W/m²",  "range": (0, 1000), "aliases": ["diff", "diffuse", "DIF"], "note": "omit only if unavailable; engine can decompose from GHI (calculateDHI=True) but measured DHI is strongly preferred for accuracy"},
        {"name": "WS",       "unit": "m/s",   "range": (0, 50),   "aliases": ["Wind", "Speed", "WindSpeed"]},
        {"name": "Pressure", "unit": "mbar",  "range": (750, 1100), "aliases": ["AP", "pressure"]},
        {"name": "PW",       "unit": "cm",    "range": (0, 100),  "aliases": ["Water"]},
        {"name": "RH",       "unit": "%",     "range": (0, 100),  "aliases": ["Humidity", "humidity"]},
        {"name": "Albedo",   "unit": "—",     "range": (0, 1),    "aliases": ["Surface Albedo", "albedo"]},
        {"name": "Soiling",  "unit": "—",     "range": (0, 1),    "aliases": ["SL", "SoilingLoss", "Slg"]},
    ],
    "missing_value_sentinel": 9999,
    "delimiter": "\t",
}
```

This doubles as documentation and as a machine-readable contract that tools
(and AI agents) can consume programmatically.  No Pydantic model overhead, no
validation logic — just a discoverable data structure.

### 4.3  Cross-reference weather-dependent options

Several fields in `EnergyCalculationOptions` have implicit dependencies on
the weather file contents, but nothing connects them:

| Option | Dependency | Current documentation |
|--------|-----------|----------------------|
| `calculate_dhi` | If `True`, DHI column is not required in the weather file — but providing measured DHI is **strongly preferred** for accuracy; the engine's GHI→DHI decomposition is a fallback, not a replacement for source data | `"Whether to calculate DHI from GHI"` — no mention of weather file or accuracy trade-off |
| `missing_met_data_handling` | Controls behaviour when weather data contains sentinel values (`9999`) | `"Behaviour when required meteorological variables have missing data"` — no mention of what "missing" means in the file |
| `use_albedo_from_met_data_when_available` | Reads `Albedo` column from weather file if present | Field exists but no cross-reference to weather column name |
| `use_soiling_from_met_data_when_available` | Reads `Soiling` column from weather file if present | Same |
| `calculation_year` | **Only** processes weather file rows whose timestamp year matches this value (default 1990).  TMY files with mixed years (NSRDB, PVGIS, etc.) will have most rows silently discarded. | `"Year to use for the calculation"` — no mention of the filtering behaviour or its interaction with TMY data |

Adding a one-line cross-reference in each field's docstring (e.g.
*"When True, the DHI column may be omitted from the weather file"*) would
close the gap without adding code.

The `calculation_year` / TMY interaction is particularly dangerous because
it fails silently — the API returns results (not an error), but those
results are based on a fraction of the intended data.  See
`sdk_general_feedback.md` §10 for a detailed description of the problem
and suggestions.

### 4.4  `write_tsv()` with a companion pvlib column-name mapping (medium effort, high value)

pvlib's `map_variables=True` convention — supported in **30+ reader
functions** — normalizes every data source to a standard set of column names
(`ghi`, `dhi`, `temp_air`, `wind_speed`, `pressure`, `precipitable_water`,
`relative_humidity`, `albedo`, …).  Any DataFrame from pvlib has these names
regardless of whether the source was NSRDB, Solcast, SolarGIS, ERA5, PVGIS,
SolarAnywhere, or a local TMY3/EPW file.

The SDK could ship a writer function alongside a provided mapping constant:

```python
# Provided as a convenience constant (not a default — user data may have
# arbitrary column names).  Covers the pvlib `map_variables=True` convention.
PVLIB_TO_SF_TSV = {
    "ghi":                 "GHI",
    "dhi":                 "DHI",
    "temp_air":            "TAmb",
    "wind_speed":          "WS",
    "pressure":            "Pressure",   # pvlib: mbar; SF: mbar ✓
    "precipitable_water":  "PW",
    "relative_humidity":   "RH",
    "albedo":              "Albedo",
}

def write_tsv(
    df: pd.DataFrame,
    path: str | Path,
    *,
    column_map: dict[str, str],
    missing_value: float = 9999,
) -> None:
    """Write a SolarFarmer-compatible TSV weather file.

    Parameters
    ----------
    df : DataFrame
        Must have a DatetimeIndex.  Column names are mapped using
        ``column_map``; unrecognised columns are dropped.
    path : str or Path
        Output file path (.tsv).
    column_map : dict
        Mapping from DataFrame column names to SolarFarmer TSV column
        names.  Keys are the source column names; values must be valid
        TSV headers (see ``TSV_COLUMNS``).
    missing_value : float
        Sentinel value for NaN.  Default is 9999.

    See Also
    --------
    PVLIB_TO_SF_TSV : Pre-built mapping for DataFrames from any pvlib
        reader called with ``map_variables=True``.

    Examples
    --------
    >>> import pvlib.iotools
    >>> from solarfarmer.weather import write_tsv, PVLIB_TO_SF_TSV
    >>> df, meta = pvlib.iotools.get_nsrdb_psm4_tmy(lat, lon, api_key, email)
    >>> write_tsv(df, "site.tsv", column_map=PVLIB_TO_SF_TSV)
    """
```

Making `column_map` a required argument (with no default) avoids the
assumption that user data will always match pvlib conventions — many datasets
arrive from non-pvlib sources with arbitrary column names.  The
`PVLIB_TO_SF_TSV` constant is there for users who *do* work in the pvlib
ecosystem, and the `See Also` / `Examples` in the docstring make it
discoverable for both humans and agents without hard-wiring it into the
function signature.

The `PVLIB_TO_SF_TSV` dict also documents the relationship between the two
ecosystems in a machine-readable way — an AI agent inspecting the constant
immediately understands both the pvlib input names and the SolarFarmer output
names.

### 4.5  Example data: documentation snippets over bundled files

Bundling full 8760-row weather files would expand the 864 KB package by
several MB — a ~10× size increase for data that is used only at documentation
time.  Alternatives that provide the same discoverability without bloating the
distribution:

1. **Inline docstring examples** showing 3–5 rows of a valid TSV:

   ```
   DateTime	GHI	DHI	TAmb	WS
   2001-01-01T00:00-06:00	0.0	0.0	-5.20	3.40
   2001-01-01T01:00-06:00	0.0	0.0	-5.80	2.90
   2001-01-01T06:00-06:00	12.3	8.1	-4.10	3.10
   ```

2. **Links to a companion `solarfarmer-examples` repository or
   documentation site** for full-size files.

Option 1 is nearly free and solves the AI-agent use case directly (the agent
reads docstrings, sees the format, and can produce a conformant file without
any external fetch).

---

## 5  Summary of priorities

| # | Change | Effort | Impact | Scope |
|---|--------|--------|--------|-------|
| 1 | Enrich `MeteoFileFormat` enum docstrings + doc link | Trivial | High for discoverability | Docs only |
| 2 | TSV column spec as module-level constants | Small | High for both humans and agents | New module, no API change |
| 3 | Cross-reference weather-dependent fields in `EnergyCalculationOptions` — especially `calculationYear` + TMY | Trivial | **High** — `calculationYear` silently discards non-matching years | Docstring edits |
| 4 | `write_tsv()` helper + `PVLIB_TO_SF_TSV` mapping constant | Medium | High — eliminates the #1 user-written boilerplate; mapping constant bridges pvlib ecosystem | New public function + constant |
| 5 | Inline docstring example (3–5 TSV rows) | Trivial | High for agents, good for humans | Docs only |

Recommendations 1, 3, and 5 are pure documentation changes that could ship in
a patch release.  Recommendation 2 provides the machine-readable contract that
makes the SDK self-describing for weather data.  Recommendation 4 is the
functional complement to the existing file-reading utilities.
