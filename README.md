# SolarFarmer Python SDK

[![PyPI version](https://img.shields.io/pypi/v/dnv-solarfarmer)](https://pypi.org/project/dnv-solarfarmer/)
[![Python versions](https://img.shields.io/pypi/pyversions/dnv-solarfarmer)](https://pypi.org/project/dnv-solarfarmer/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![CI](https://github.com/dnv-opensource/solarfarmer-python-sdk/actions/workflows/test.yml/badge.svg)](https://github.com/dnv-opensource/solarfarmer-python-sdk/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-online-teal)](https://dnv-opensource.github.io/solarfarmer-python-sdk/)

The official Python SDK for [SolarFarmer](https://www.dnv.com/software/services/solarfarmer/), a bankable solar PV design and energy yield assessment software from DNV. This SDK provides a typed Python interface that simplifies calling SolarFarmer APIs: build payloads, run 2D and 3D energy calculations, and process results programmatically.

## Key Features

- **Data models that mirror the API schema.** Pydantic classes with field validation catch payload errors locally before the API call. Field descriptions and type hints improve discoverability.
- **Two plant-building paths.** Full control via `EnergyCalculationInputs` and component classes, or quick screening via `PVSystem` from high-level specs (DC and AC capacities, tilt, GCR)
- **Structured results.** `CalculationResults` gives direct access to annual/monthly metrics, loss trees, and time series without parsing raw JSON.
- **Automatic endpoint handling.** One function call runs 2D or 3D calculations. The SDK selects the right endpoint, polls async jobs, and supports cancellation via `terminate_calculation()`.

## Requirements

- Python >= 3.10 (tested on 3.10, 3.11, 3.12, 3.13)
- A SolarFarmer API key (commercial licence required; see [API Key](#api-key))

## Installation

Install from PyPI:

```bash
pip install dnv-solarfarmer
```

The package is imported as `solarfarmer` regardless of the distribution name:

```python
import solarfarmer as sf
```

Install with optional extras:

```bash
pip install "dnv-solarfarmer[weather]"    # pandas for weather file conversion and DataFrame results
pip install "dnv-solarfarmer[notebooks]"  # JupyterLab and notebook support
pip install "dnv-solarfarmer[all]"        # full installation including pandas and matplotlib
pip install "dnv-solarfarmer[dev]"        # linting and testing tools (for contributors)
```

Install from source:

```bash
git clone https://github.com/dnv-opensource/solarfarmer-python-sdk
cd solarfarmer-python-sdk
pip install -e .
```

## API Key

A SolarFarmer API key is required to run energy calculations. Obtain one from the [SolarFarmer portal](https://solarfarmer.dnv.com/). For setup instructions, see the [API key documentation](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/ApiKey.html).

Set your key as an environment variable (recommended):

```bash
export SF_API_KEY="your_api_key_here"
```

Alternatively, pass it directly as the `api_key` parameter to any function that calls the API.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `SF_API_KEY` | *(none; required for calculations)* | API authentication token |
| `SF_API_URL` | `https://solarfarmer.dnv.com/latest/api` | Override the base API URL for custom deployments |

## Optional Dependencies

The core SDK (`pydantic`, `requests`, `tabulate`) does not depend on `pandas`.
Install the `weather` extra for DataFrame-based features:

```bash
pip install "dnv-solarfarmer[weather]"
```

This unlocks `sf.from_dataframe()` and `sf.from_pvlib()` for writing weather files from DataFrames, and enables `CalculationResults` to parse timeseries outputs into DataFrames. Without pandas, those functions raise `ImportError` or return `None`. All other SDK features work without it.

## Getting Started

The SDK supports three workflows for different use cases:

| Workflow | Best for | Entry point |
|---|---|---|
| 1. Load existing files | Users with pre-built API payloads from the SolarFarmer desktop app or a previous export | `sf.run_energy_calculation(inputs_folder_path=...)` |
| 2. PVSystem builder | Quick screening from high-level specs (capacity, tilt, equipment files). The design is approximate: string sizing and inverter count are inferred, so DC/AC capacity may not match the target exactly. | `plant = sf.PVSystem(...)` then `plant.run_energy_calculation()` |
| 3. Custom integration | Developers mapping internal databases or proprietary formats to the SolarFarmer API | `params = sf.EnergyCalculationInputs(...)` then `sf.run_energy_calculation(plant_builder=params)` |

See the [Getting Started guide](https://dnv-opensource.github.io/solarfarmer-python-sdk/getting-started/) for full per-workflow walkthroughs, and the [example notebooks](https://dnv-opensource.github.io/solarfarmer-python-sdk/notebooks/Example_EnergyCalculations/) for runnable end-to-end examples.

## Documentation

Full documentation (API reference, workflow guides, notebook tutorials):

**https://dnv-opensource.github.io/solarfarmer-python-sdk/**

To build and serve the documentation locally:

```bash
pip install "dnv-solarfarmer[docs]"
zensical serve -o                          # build, serve, and open in browser (port 8000)
zensical serve -o -a localhost:8080        # use a different port
```

`zensical serve` builds the docs and starts a local server in one step. The `-o` flag opens the page automatically in your default browser.

## Contributing

Fork the repository, create a branch, and submit a pull request to `main`. To set up a development environment:

```bash
git clone https://github.com/dnv-opensource/solarfarmer-python-sdk
cd solarfarmer-python-sdk
pip install -e ".[dev]"
```

- **Linting and formatting:** `ruff check solarfarmer/ tests/` and `ruff format solarfarmer/ tests/`
- **Tests:** `pytest tests/ -v`

All contributions should include tests for new functionality. For feature proposals or questions, contact [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com). See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Getting Technical Support

- **SDK documentation:** https://dnv-opensource.github.io/solarfarmer-python-sdk/
- **SolarFarmer API documentation:** https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html
- **Issue tracker:** https://github.com/dnv-opensource/solarfarmer-python-sdk/issues
- **Email:** [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com)

## License

Apache License, Version 2.0 — see [LICENSE](LICENSE).
