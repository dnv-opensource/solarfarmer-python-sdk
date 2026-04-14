# Frequently Asked Questions (FAQ)

## Where do I get an API key and how do I use it?

Your API key is required for:

- [`run_energy_calculation()`](api.md#run_energy_calculation) - Running energy calculations
- [`about()`](api.md#about) - Querying API information
- [`service()`](api.md#service) - Accessing service endpoints

**Getting your API key:** See the [API Key documentation](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/ApiKey.html) or contact [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com) for further support.

---

## Why do SolarFarmer Desktop and PVSystem produce different results?

SolarFarmer Desktop has detailed spatial information about row positions and can identify which strings are in front/back rows (fixed-tilt) or left/right rows (trackers). This allows more accurate shading calculations for edge-positioned strings.

The [`PVSystem`](api.md#pvsystem) class, used as part of *Workflow 2: Design Plants with high-level metadata*, takes a conservative approach and treats all the strings as if these were positioned in middle-position rows (i.e. always subject to row-to-row or mutual shading), resulting in more uniform (but slightly different) shading estimates.

---

## Can I import SDK-generated JSON into SolarFarmer Desktop?

Yes! Use the **"Import from API JSON"** feature in SolarFarmer Desktop. See the [Import from API JSON documentation](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/HintsAndTips/APIJSON/ImportFromAPIJSON.html) for details.

---

## What are the current limitations?

**PVSystem Class:**

- Supports only one PV module type (defined by a single PAN file)
- Supports only one inverter type (defined by a single OND file)
- Uses simplified row positioning (all strings in middle-row assumption)

For information about upcoming features or requests, contact [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com).

---

## Why do I get an `ImportError` when calling `from_dataframe()` or `from_pvlib()`?

These weather conversion functions require `pandas`, which is an optional dependency. Install it with:

```bash
pip install "dnv-solarfarmer[all]"
```

The core SDK (payload construction, API calls, annual/monthly summary data) works without pandas. Only the weather file conversion utilities and timeseries result parsing need it. See the [Weather Utilities reference](api.md#weather-utilities) for details.

---

## My TMY weather file gives a 400 error with no useful message. What's wrong?

TMY (Typical Meteorological Year) datasets from NSRDB, PVGIS, or similar sources contain timestamps from multiple source years. SolarFarmer requires all timestamps in a TSV file to belong to a single calendar year.

Use [`sf.from_pvlib()`](api.md#from_pvlib) or [`sf.from_dataframe(year=1990)`](api.md#from_dataframe) to remap timestamps automatically. The SDK also calls [`check_sequential_year_timestamps()`](api.md#check_sequential_year_timestamps) before upload to catch this early.
