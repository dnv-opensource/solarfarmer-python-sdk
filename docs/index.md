---
title: Home
description: SolarFarmer Python SDK
---

# Welcome to SolarFarmer API
A Python SDK that wraps the [DNV SolarFarmer API](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html) to help you run cloud-based energy calculations and manage API payloads in a user-friendly way.

[New to SolarFarmer? Discover it here!](https://www.dnv.com/software/services/solarfarmer/){ .md-button .md-button-primary target="_blank" .external }

Embed SolarFarmer's API into your workflow, typical use-cases of the package include:

* Building SolarFarmer API JSON payloads for 2D energy calculations.
* Running 2D and 3D energy calculations from existing API payload files.
* Managing and visualizing simulation results.
* Iterating over API payloads to explore design variations and optimization scenarios.

!!! note
    This package is periodically updated to remain compatible with the latest SolarFarmer API releases.

## Install
From the directory run the following command:
```bash
pip install solarfarmer
```
!!! tip

    For full functionality install **all**: `pip install --user solarfarmer[all]`


## Usage
!!! warning

    A commercial API key is required to run calculations with SolarFarmer's cloud energy yield engine.

    Start by [acquiring your SolarFarmer web API token](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/ApiKey.html){ target="_blank" .external }. For more details, see the [SolarFarmer web API introduction page](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/WebApi/Introduction/introduction.html){ target="_blank" .external }.

    Once you have your API key, provide it to the SDK using either the **SF_API_KEY** environment variable or pass it directly as the `api_key` argument when calling the energy calculation function or other endpoints.


Calling the energy calculation model with all the API inputs in a folder:

```py
import solarfarmer as sf

# A project id (optional)
project_id="calculation example"

# API key (optional, it could be an environment variable 'SF_API_KEY')
api_key = "Your SolarFarmer API key here"

# One folder with all the calculation inputs (JSON, PAN, OND, met data)
folder_with_inputs = r"C:\user_name\data\inputs_solarFarmer_api_call"

# Make the call to the API
results = sf.run_energy_calculation(inputs_folder_path=folder_with_inputs,
                                    project_id=project_id,
                                    api_key=api_key)
```

## Getting Started

Choose your workflow: load existing API files, build plant configurations from scratch, or integrate custom data models to run the SolarFarmer energy calculation in the cloud.

[Explore Getting Started Guide](getting-started/index.md){ .md-button .md-button-primary target="_blank" .external }

!!! tip

    The package comes with sample files for both the 2D and 3D energy calculations, which are used in the tutorials.

    Alternatively, you can get additional sample files from the [API step-by-step tutorials](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/Tutorials/Tutorials.html) or export your own from [SolarFarmer's desktop application](https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/HintsAndTips/APIJSON/ImportFromAPIJSON.html).



## Docs
To build the documentation, run from the directory the commands:
```bash
zensical build
zensical serve
```
In a browser navigate to `localhost:8000` to see the documentation.

## Contributing & License
Suggestions and code contributions are welcome — please open a PR or Issue.
This repository is licensed under the Apache License, Version 2.0 (see [LICENSE](license.md)).

For technical support, contact [solarfarmer@dnv.com](mailto:solarfarmer@dnv.com).
