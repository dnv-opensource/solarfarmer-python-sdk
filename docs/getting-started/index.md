---
title: Getting Started
description: Choose your workflow to start using SolarFarmer SDK
---

# Getting Started with the SolarFarmer Python SDK

The SolarFarmer SDK supports three distinct user workflows. Choose the one that matches your use case and expertise level.

!!! warning

    A commercial API key is required to run calculations with SolarFarmer's cloud energy yield engine.

    Start by [acquiring your SolarFarmer web API token](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/ApiKey.html){ target="_blank" .external }. For more details, see the [SolarFarmer web API introduction page](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html){ target="_blank" .external }.

    Once you have your API key, provide it to the SDK using either the **SF_API_KEY** environment variable or pass it directly as the `api_key` argument when calling the energy calculation function.

!!! tip "Optional: pandas for weather conversion and timeseries results"

    The core SDK works without pandas. To use `sf.from_dataframe()`, `sf.from_pvlib()`,
    or to parse timeseries results as DataFrames, install the `all` extra:

    ```bash
    pip install "dnv-solarfarmer[all]"
    ```

## Choose Your Path

### [Workflow 1: Load and Execute Existing API Files](workflow-1-existing-api-files.md)

**For:** Solar data analysts and engineers with existing SolarFarmer API JSON files

**Goal:** Run energy calculations using available pre-configured payloads

**Key Classes and Functions:**

- `run_energy_calculation()` - Execute the calculation with existing files
- `CalculationResults` - Access and analyze results (returned directly by `run_energy_calculation()`)

**Time to First Result:** 5 minutes

!!! example
    You have a folder with `EnergyCalcInputs.json`, `module.PAN`, `inverter.OND`, and weather data.

    Load them and run a calculation immediately.

---

### [Workflow 2: Design Plants with PVSystem](workflow-2-pvplant-builder.md)

**For:** Solar engineers and designers creating new plant configurations

**Goal:** Define high-level plant specifications and automatically construct API payloads

**Key Classes:**

- `PVSystem` - Define plant configuration (location, capacity, equipment, etc.)
- `CalculationResults` - Access and analyze results (available via `plant.results` after calculation)

**Time to First Result:** 10-15 minutes

!!! example
    Specify your plant: location (lat/lon), DC and AC capacities, inverter type, mounting configuration.
    `PVSystem` handles the payload construction and you run the calculation.

Results from `PVSystem` are approximations based on simplified layout assumptions — see [FAQ](../faq.md) for details.

---

### [Workflow 3: Advanced Integration and Custom Data Models](workflow-3-plantbuilder-advanced.md)

**For:** Software developers integrating SolarFarmer into custom applications

**Goal:** Manually build and customize API payloads for complex workflows

**Key Classes:**

- `EnergyCalculationInputs` - Compose and serialize the complete API payload
- `PVPlant` - Describe the PV plant structure
- Component classes (`Inverter`, `Layout`, `Transformer`, etc.)
- Data model mapping and workflow orchestration

**Prerequisites:** Familiarity with SolarFarmer's API structure and data model.

**Time to First Result:** 30+ minutes (depends on workflow complexity)

!!! example
    Map your proprietary plant database to SolarFarmer objects, build custom workflows,
    or integrate with other simulation tools.

---

## Integrated Class Examples

Once you know your workflow, see how the classes work together in real-world scenarios.

[View Quick Start Examples](quick-start-examples.md){ .md-button }

---

## Need Help Deciding?

| I want to... | Go to Workflow |
|---|---|
| Run calculations on existing API files | [Workflow 1](workflow-1-existing-api-files.md) |
| Design a new plant from scratch | [Workflow 2](workflow-2-pvplant-builder.md) |
| Integrate SolarFarmer into my software | [Workflow 3](workflow-3-plantbuilder-advanced.md) |
| See real code examples | [Quick Start Examples](quick-start-examples.md) |

---

## Next Steps

1. **Select your workflow** from the list above
2. **Follow the guide** step-by-step
3. **Explore the examples** to see classes in action
4. **Look into the [End-to-End Examples](end-to-end-examples.md)** to dive deeper into the classes
5. **Refer to API documentation** for detailed class references
