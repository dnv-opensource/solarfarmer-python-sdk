# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-09-24

### Added

- `PVSystem.tracker_max_rotation_angle` — dedicated field for the maximum tracker rotation angle in degrees (default 60°). Only applies when `mounting='Tracker'`. Replaces the previous (confusing) use of `PVSystem.tilt` for this purpose.
- Pydantic models for the 3D API data model: `Rack`, `Racks`, `Tracker` (3D), `Trackers`, `InverterInput`, `ModuleString`, `SimpleTerrain`, `ShadingObjects`, and supporting geometry types (`QuadDouble`, `Vector3Double`, `IndexedObject3D`, `ModuleIndexRange`, `MiniSimpleTerrainDto`, `TerrainRowDto`, `TerrainRowStartEndColumnsDto`). These enable full composition of 3D plant layouts, including power optimizer support via `InverterInput`.
- `PVSystem.recalculate_modeling_correction_factor` field to control whether the modeling correction factor is recalculated during energy yield assessment (default `True`).
- `from_solcast` added to the Weather Utilities section of the API reference documentation.
- `TrackerAlgorithm` enum to define custom rotation strategies for tracker systems, enabling flexible rotation calculation methods beyond predefined algorithms.
- `TrackersConditionsDataset` class with Protobuf serialization support for storing and transmitting tracker rotation conditions and custom rotation data.
- `TrackerRotationID` field in the `Layout` class to support custom tracker rotation workflows.
- `dc_ohmic_connector_loss` and related DC loss resistance fields in the `Layout` class for detailed power loss modeling in tracker systems.
- CSV export functionality for tracker-specific results, providing detailed rotation and performance data for each tracker row.
- `custom_rotations` module for importing custom tracker rotation schedules from CSV files with functions `from_csv()`, `from_csv_folder()`, and `csv_to_protobuf()` to load and validate rotation data.
- Public API exports: `from_custom_rotations_csv()` and `custom_rotations_csv_to_protobuf()` for programmatic CSV rotation ingestion.
- Utilities for validating the compatibility of custom rotations and plant layout: tracker rotation IDs, checking time resolution compatibility, and verifying weather data coverage for rotation periods.

### Changed

- `PVSystem.tilt` is now fixed-tilt only. For tracker systems, set `tracker_max_rotation_angle` instead. Previously, `tilt` was silently used as the tracker rotation bound, which caused confusion.

### Fixed

- Documentation examples corrected: GCR spacing value for tracker systems in quick-start example now consistently use 0.35.
- Documentation clarified: albedo parameter in workflow-2 now shows explicit list format `[0.2] * 12` for clarity.
- API error message updated to reference latest supported API version (v7) in validation documentation.

## [0.5.0] - 2026-06-29

### Changed

- `PVSystem.lid_loss` default changed from `0.0` to `None`. When `None`, the LIDLoss value is read from the PAN file. If you relied on the old default to override the PAN file, set `plant.lid_loss = 0.0` explicitly.

### Fixed

- `PVSystem.lid_loss` now correctly overrides the PAN file's `LIDLoss` value when explicitly set (previously the PAN file always took precedence).

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
