# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-05-07

### Features

- `sf.from_solcast()`, `sf.from_pvlib()`, and `sf.from_dataframe()` converters to transform solar resource data from Solcast, pvlib and pandas DataFrames into SolarFarmer's TSV meteorological format.
- `PVSystem.print_design_summary` flag to control whether the design summary is printed when producing the API payload from the PVSystem class.
- Exposed the bifacial performance ratio in the performance summary returned after running energy calculations.

### Bug fixes

- Removed the `Content-Type` HTML header from API client, as it is handled by the `requests` library, resolving failures in Google Colab and other shared environments.

## [0.2.0] - 2026-04-28

- Initial release of the SolarFarmer Python SDK.
