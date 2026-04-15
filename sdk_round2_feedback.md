# SolarFarmer Python SDK — Feedback from Agent-Driven Integration Test

**Date:** 2025-04-07
**SDK version:** git commit `4f13c6e` (github.com/dnv-opensource/solarfarmer-python-sdk)
**Test:** ~20 MW bifacial plants (tracker + fixed tilt) at 7 NOAA SURFRAD locations using PSM4 TMY data via pvlib

## Context

An AI coding agent was given a one-paragraph prompt to build and run SolarFarmer energy calculations for all SURFRAD sites. This document summarizes the friction points encountered, ranked by debugging cost, with suggested improvements.

---

## Immediate (docs + bug fixes)

### 1. PAN/OND Filename Parsing Inconsistency — Bug Fix

**Problem:** `pvsystem.py:1737` (PAN) and `pvsystem.py:1710` (OND) use `filename.split(".")[0]` to derive spec IDs, producing `Trina_TSM-DEG19C` from `Trina_TSM-DEG19C.20-550_APP.PAN`. But the client-side validation in `endpoint_modelchains.py:58` uses `Path(f.name).stem`, producing `Trina_TSM-DEG19C.20-550_APP`. These don't match, causing a `ValueError` before the API call is even made. Both PAN and OND paths are affected.

**Cost:** ~25% of debugging time. Required source-diving into both files to understand the mismatch. Workaround was copying the PAN file with periods replaced by underscores.

**Fix:** Use `Path.stem` (or `rsplit(".", 1)[0]`) consistently in both locations.

### 2. TMY Year Requirement Not Discoverable from `PVSystem` Workflow — Docs

**Problem:** TMY data from NSRDB contains timestamps from multiple source years (e.g. 2003, 2005, 2010, 2016). Submitting this as a TSV file to the API returns HTTP 400 with `{"detail": "Something went wrong."}` — no indication that timestamps are the issue.

**Existing documentation:** The `calculation_year` docstring in `EnergyCalculationOptions` correctly warns about TMY mixed-year data and the need to remap timestamps. However, `PVSystem` users never interact with `EnergyCalculationOptions` directly, and the `calculation_year` docs state that for TSV format the value is "Ignored — timestamps in the file are used as-is", which could be read as implying raw TMY timestamps are acceptable. The agent found `weather.py` and `PVSystem` docs but had no reason to look at `EnergyCalculationOptions`.

**Cost:** ~40% of debugging time. Required ~15 rounds of payload inspection, monkey-patching the response handler, and trial-and-error before discovering the root cause.

**Fix:**

- Add a note to the `PVSystem.weather_file` property docstring warning that TMY data with mixed source years must be remapped to a single calendar year. Reference `EnergyCalculationOptions.calculation_year` for details.
- Add a brief note to the `weather.py` module docstring (not in `TSV_COLUMNS`, which is a format spec — the year issue is TMY-specific, not a general format constraint).

### 3. Weather Format Conversion — Docs

**Problem:** Converting pvlib DataFrames to SolarFarmer TSV format requires knowing: column name mapping, datetime format (`YYYY-MM-DDThh:mm+OO:OO`), tab delimiter, year normalization, and pressure units. This information is spread across `weather.py` and internal source code.

**Cost:** ~20% of debugging time.

**Fix:**

- Add a pvlib-to-SolarFarmer column mapping reference to the `weather.py` module docstring (e.g. `temp_air` → `TAmb`, `wind_speed` → `WS`, `pressure` → `Pressure`).
- Add a minimal conversion code example in `weather.py` or the `PVSystem` class docstring.

### 4. `MountingType` Import Path — Docs

**Problem:** `sf.MountingType` raises `AttributeError`. Must import from `solarfarmer.models.pvsystem.pvsystem`.

**Cost:** ~5%.

**Fix:** Document the import path in the `PVSystem` class docstring, since `mounting` is a required parameter.

### 5. PAN/OND Dict Key Semantics — Docs

**Problem:** `PVSystem.pan_files` accepts `dict[str, Path]`, but the dict keys are ignored — spec IDs are derived from filenames via `filename.split(".")[0]`. The dict interface implies the keys are meaningful.

**Cost:** ~5%.

**Fix:** Document in the `pan_files` and `ond_files` property docstrings that keys are not used as spec IDs.

### 6. `CalculationResults` Usage — Docs

**Problem:** No `results.net_energy_MWh` property. Must use `results.get_performance()['net_energy']`.

**Cost:** ~5%.

**Fix:** Add a usage example in the `CalculationResults` class docstring showing `get_performance()` and available keys.

---

## Future Improvements

- **Server-side validation:** Return field-level error details instead of generic `{"detail": "Something went wrong."}` for 400 responses. This is the single highest-impact improvement but is an API-side change.
- **Client-side TMY validation:** Detect non-contiguous years in TSV weather files before upload and raise a clear `ValueError` with remediation guidance.
- **Weather conversion utility:** `sf.weather.from_pvlib(df)` or `sf.weather.from_dataframe(df)` to handle column renaming, timestamp formatting, and year normalization for TMY data.
- **Top-level enum exports:** Export `MountingType`, `InverterType`, `OrientationType` from `solarfarmer.__init__`.
- **`pan_files` / `ond_files` as list:** Accept `list[Path]` in addition to `dict[str, Path]`, since the keys are unused.
- **Convenience properties on `CalculationResults`:** `net_energy_MWh`, `performance_ratio`, `energy_yield_kWh_per_kWp`.

---

## Summary of Estimated Debugging Cost

| Issue | Relative Cost | Category |
|---|---|---|
| TMY year requirement not discoverable | ~40% | Docs |
| PAN filename `split(".")` vs `Path.stem` | ~25% | Bug fix |
| Weather format conversion | ~20% | Docs |
| Missing enum import path | ~5% | Docs |
| Dict key confusion | ~5% | Docs |
| No convenience accessors | ~5% | Docs |
