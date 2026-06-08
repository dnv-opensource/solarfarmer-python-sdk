# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-06-08

### Added

- `POA` (Plane of Array irradiance) as an optional column in the TSV meteorological file format. Either `GHI` or `POA` must now be provided; `GHI` is no longer strictly required. The `from_pvlib()` converter now maps pvlib columns `poa` and `gti` to the `POA` column.
- `plant_unavailability` and `grid_unavailability` fields to `PVSystem`, allowing availability losses to be specified as per-unit fractions (default `0.0`). These map to `system_availability_loss` and `grid_availability_loss` in the API calculation options.

### Fixed

- Missing SolarFarmer API step in the workflow-1 and workflow-2 documentation flowcharts.

## [0.3.0] - 2026-05-07

### Added

- `sf.from_solcast()`, `sf.from_pvlib()`, and `sf.from_dataframe()` converters to transform solar resource data from Solcast, pvlib and pandas DataFrames into SolarFarmer's TSV meteorological format.
- `PVSystem.print_design_summary` flag to control whether the design summary is printed when producing the API payload from the PVSystem class.
- Exposed the bifacial performance ratio in the performance summary returned after running energy calculations.

### Fixed

- Removed the `Content-Type` HTML header from API client, as it is handled by the `requests` library, resolving failures in Google Colab and other shared environments.

## [0.2.0] - 2026-04-28

- Initial release of the SolarFarmer Python SDK.
