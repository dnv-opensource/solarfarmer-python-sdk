---
title: Home
description: SolarFarmer Python SDK
---

# Welcome to SolarFarmer API
A Python SDK that wraps the [DNV SolarFarmer API](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html) to help you run cloud-based energy calculations and manage API payloads in a user-friendly way.

[New to SolarFarmer? Discover it here!](https://www.dnv.com/software/services/solarfarmer/){ .md-button .md-button-primary target="_blank" .external }

Embed SolarFarmer's API into your workflow. Typical use-cases of the package include:

* Build SolarFarmer API JSON payloads for 2D energy calculations
* Run 2D and 3D energy calculations from existing API payload files
* Manage and visualize simulation results
* Iterate over API payloads to explore design variations and optimization scenarios

## Install

Install from PyPI using your favorite package manager, for example:

```bash
pip install dnv-solarfarmer
```

!!! tip
    For full functionality install **all**: `pip install "dnv-solarfarmer[all]"`

!!! note
    This package is periodically updated to remain compatible with the latest SolarFarmer API releases.

## Getting Started

!!! warning
    A commercial API key is required to run calculations with SolarFarmer's cloud energy yield engine.

    Start by [acquiring your SolarFarmer web API token](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/ApiKey.html){ target="_blank" .external }. For more details, see the [SolarFarmer web API introduction page](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html){ target="_blank" .external }.

    Once you have your API key, provide it to the SDK using either the **SF_API_KEY** environment variable or pass it directly as the `api_key` argument when calling the energy calculation function or other endpoints.

Choose your workflow: load existing API files, build plant configurations from scratch, or integrate custom data models to run the SolarFarmer energy calculation in the cloud. For example,

Calling the energy calculation model with all the API inputs in a folder:

```py
import solarfarmer as sf

# API key (optional, it could be an environment variable 'SF_API_KEY')
api_key = "Your SolarFarmer API key here"
project_id = "my_project"

# One folder with all the calculation inputs (JSON, PAN, OND, met data)
folder_with_inputs = r"C:\user_name\data\inputs_solarFarmer_api_call"

# Make the call to the API
results = sf.run_energy_calculation(inputs_folder_path=folder_with_inputs,
                                    project_id=project_id,
                                    api_key=api_key)
```

[Explore Getting Started Guide](getting-started/index.md){ .md-button .md-button-primary target="_blank" .external }

!!! tip
    The package comes with sample files for both the 2D and 3D energy calculations, which are used in the tutorials.

    Alternatively, you can get additional sample files from the [API step-by-step tutorials](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/Tutorials/Tutorials.html) or export your own from [SolarFarmer's desktop application](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/HintsAndTips/APIJSON/ImportFromAPIJSON.html).

## Contributing & License

Suggestions and code contributions are welcome on [GitHub](https://github.com/dnv-opensource/solarfarmer-python-sdk).
This repository is licensed under the Apache License, Version 2.0 (see [LICENSE](license.md)).

For technical support, contact [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com).
