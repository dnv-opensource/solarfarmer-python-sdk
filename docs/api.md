---
title: API Reference
description: Complete reference for the solarfarmer Python SDK
---

# API Reference

The SolarFarmer Python SDK is the official Python client for the SolarFarmer energy calculation service. This page documents all publicly exported functions and classes.

---

## Overview

The SolarFarmer SDK is organized into the following main categories:

### Core Functions & Classes

- [**Endpoint Functions**](#endpoint-functions): Core functions for making API calls
- [**Main Classes**](#main-classes): Key data models for calculations and plant design
- [**Weather Utilities**](#weather-utilities): Convert DataFrames to SolarFarmer weather files (requires `pandas`)

### Configuration & Design

- [**Plant Configuration Classes**](#plant-configuration-classes): Location, layout, and inverter specifications
- [**Module and Equipment Specifications**](#module-and-equipment-specifications): Mounting types, trackers, and component files
- [**Enums**](#enums): PVSystem configuration enums (`MountingType`, `InverterType`, `OrientationType`)

### Advanced Options

- [**Advanced System Configuration**](#advanced-system-configuration): Transformers, grid limits, and auxiliary losses
- [**Additional Configuration Classes**](#additional-configuration-classes): Albedo and other environmental factors

---

## Endpoint Functions

These are the primary functions for interacting with the SolarFarmer API.

### `run_energy_calculation()`

::: solarfarmer.endpoint_modelchains.run_energy_calculation
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `about()`

::: solarfarmer.endpoint_about.about
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `service()`

::: solarfarmer.endpoint_service.service
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `terminate_calculation()`

::: solarfarmer.endpoint_terminate_async.terminate_calculation
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

---

## Weather Utilities

!!! note
    These functions require `pandas`. Install with `pip install 'dnv-solarfarmer[all]'`.

### `from_dataframe()`

::: solarfarmer.weather.from_dataframe
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `from_pvlib()`

::: solarfarmer.weather.from_pvlib
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `check_sequential_year_timestamps()`

::: solarfarmer.weather.check_sequential_year_timestamps
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### `TSV_COLUMNS`

Data dictionary describing the SolarFarmer TSV weather file format: required and optional columns, units, valid ranges, aliases, and the missing-value sentinel. See the [`weather` module docstring](../api.md) for full details.

---

## Main Classes

The core classes handle the complete workflow from plant design to results analysis:

- [**PVSystem**](#pvsystem): Main class for constructing approximated PV plant designs from high-level specifications (location, capacity, equipment). Infers layout geometry and losses using simplified assumptions; results are suitable for screening, not detailed design
- [**EnergyCalculationInputs**](#energycalculationinputs): Root Pydantic model composing all inputs for a calculation run
- [**PVPlant**](#pvplant): Pydantic model describing the PV plant structure (transformers, mounting specs, etc.)
- [**ModelChainResponse**](#modelchainresponse): Container for raw API response data from energy calculations
- [**CalculationResults**](#calculationresults): Analysis tools for exploring and visualizing energy yield results

### PVSystem

::: solarfarmer.PVSystem
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### EnergyCalculationInputs

::: solarfarmer.EnergyCalculationInputs
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### PVPlant

::: solarfarmer.PVPlant
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### ModelChainResponse

::: solarfarmer.ModelChainResponse
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

### CalculationResults

::: solarfarmer.CalculationResults
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

---

## Plant Configuration Classes

### Location

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.Location.html){ target="_blank" .external }

### Layout

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.Layout.html){ target="_blank" .external }

### Inverter

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.Inverter.html){ target="_blank" .external }

### EnergyCalculationOptions

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.EnergyCalculationOptions.html){ target="_blank" .external }

---

## Module and Equipment Specifications

### MountingTypeSpecification

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.MountingTypeSpecification.html){ target="_blank" .external }

### TrackerSystem

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.TrackerSystem.html){ target="_blank" .external }

### PanFileSupplements

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.PanFileSupplements.html){ target="_blank" .external }

### OndFileSupplements

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.OndFileSupplements.html){ target="_blank" .external }

---

## Advanced System Configuration

### Transformer

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.Transformer.html){ target="_blank" .external }

### TransformerSpecification

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.TransformerSpecification.html){ target="_blank" .external }

### TransformerLossModelTypes

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.TransformerLossModelTypes.html){ target="_blank" .external }

### AuxiliaryLosses

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.AuxiliaryLosses.html){ target="_blank" .external }

---

## Additional Configuration Classes

### MonthlyAlbedo

[View in SolarFarmer API Reference](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/webApiRef/SolarFarmerApi.Client.MonthlyAlbedo.html){ target="_blank" .external }

---

## Enums

These enums are used with `PVSystem` to configure mounting, inverter, and module orientation.
They are available at the top level: `sf.MountingType`, `sf.InverterType`, `sf.OrientationType`.

| Enum | Values | Used by |
|---|---|---|
| `MountingType` | `FIXED`, `TRACKER` | `PVSystem.mounting` |
| `InverterType` | `CENTRAL`, `STRING` | `PVSystem.inverter_type` |
| `OrientationType` | `PORTRAIT`, `LANDSCAPE` | `PVSystem.module_orientation` |

---

## Version Information

::: solarfarmer.__version__
    options:
      extra:
        show_root_toc_entry: false
        show_root_members: true

---

## Configuration

The SDK can be configured using environment variables:

- `SF_API_KEY`: Your SolarFarmer API authentication key (imported from environment)
- `SF_API_URL`: Override the default SolarFarmer API URL

You can also pass these values directly as keyword arguments to the endpoint functions.
