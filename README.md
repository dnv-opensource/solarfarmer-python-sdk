# SolarFarmer Python SDK

[![PyPI version](https://img.shields.io/pypi/v/dnv-solarfarmer)](https://pypi.org/project/dnv-solarfarmer/)
[![Python versions](https://img.shields.io/pypi/pyversions/dnv-solarfarmer)](https://pypi.org/project/dnv-solarfarmer/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![CI](https://github.com/dnv-opensource/solarfarmer-python-sdk/actions/workflows/test.yml/badge.svg)](https://github.com/dnv-opensource/solarfarmer-python-sdk/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-online-teal)](https://dnv-opensource.github.io/solarfarmer-python-sdk/)

The official Python SDK for [DNV SolarFarmer](https://www.dnv.com/software/services/solarfarmer/), a bankable solar PV calculation engine. Use it to build validated API payloads, run cloud-based 2D and 3D energy calculations, and analyse simulation results — all from Python.

## Key Features

- **API-faithful data models** that closely mirror the SolarFarmer API schema, with serialization conveniences (snake_case Python fields serialized to the correct camelCase JSON automatically) to reduce integration friction
- **Two plant-building approaches:** a bottom-up route using `EnergyCalculationInputs`, `PVPlant`, and component classes (`Inverter`, `Layout`, `Transformer`, etc.) for full control over the plant topology; and a `PVSystem` convenience class that accepts high-level parameters (capacity, tilt, GCR, equipment files) and constructs the payload automatically, suited to indicative simulations where exhaustive detail is not required
- **`CalculationResults` encapsulation** — the API response is wrapped in a `CalculationResults` object that provides structured access to annual and monthly energy metrics, loss trees, PVsyst-format time-series, and detailed time-series output without manual JSON parsing
- **ModelChain and ModelChainAsync endpoint support** — the SDK dispatches to the synchronous `ModelChain` endpoint or the asynchronous `ModelChainAsync` endpoint as appropriate, and handles polling automatically for long-running jobs
- **Async job management** — poll, monitor, and terminate async calculations via `terminate_calculation()`

## Requirements

- Python >= 3.10 (tested on 3.10, 3.11, 3.12, 3.13)
- A SolarFarmer API key (commercial licence required) — see [API Key](#api-key)

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
pip install "dnv-solarfarmer[notebooks]"  # JupyterLab and notebook support
pip install "dnv-solarfarmer[all]"         # full installation including pandas and matplotlib
pip install "dnv-solarfarmer[dev]"         # linting and testing tools (for contributors)
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
| `SF_API_KEY` | *(none — required for calculations)* | API authentication token |
| `SF_API_URL` | `https://solarfarmer.dnv.com/latest/api` | Override the base API URL for custom deployments |

## Getting Started

The SDK is built around three workflows suited to different use cases:

| Workflow | Best for | Primary entry point |
|---|---|---|
| 1. Load existing files | Users with pre-built API payloads from the SolarFarmer desktop app or a previous export | `sf.run_energy_calculation(inputs_folder_path=...)` |
| 2. PVSystem builder | Solar engineers designing new plants programmatically with automatic payload generation | `sf.PVSystem(...)` then `plant.run_energy_calculation()` |
| 3. Custom integration | Developers mapping internal databases or proprietary formats to the SolarFarmer API | `sf.EnergyCalculationInputs(location=..., pv_plant=..., ...)` |

See the [Getting Started guide](https://dnv-opensource.github.io/solarfarmer-python-sdk/getting-started/) for full per-workflow walkthroughs, and the [example notebooks](https://dnv-opensource.github.io/solarfarmer-python-sdk/notebooks/Example_EnergyCalculations/) for runnable end-to-end examples.

## Documentation

Full documentation including API reference, workflow guides, and notebook tutorials:

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
