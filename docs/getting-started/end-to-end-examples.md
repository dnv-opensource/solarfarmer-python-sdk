---
title: End-to-End Examples
description: Tutorials exploring specific API features and capabilities
---

# End-to-End Examples

These examples provide detailed explorations of specific API features and workflows. Use them to deepen your understanding of SolarFarmer capabilities beyond the Quick Start Examples.

## Quick Reference

| Example | Purpose | Workflow | Audience |
|---------|---------|----------|----------|
| [Using the About and Service Endpoints](#using-the-about-and-service-endpoints) | Understand API capabilities and system information | All | Everyone |
| [Running 2D and 3D Calculations](#running-2d-and-3d-calculations) | Learn the functionality when working with synchronous and asynchronous energy calculations | Workflow 1 | Loading and working with existing calculations |
| [Creating Plants with PVSystem](#creating-plants-with-pvsystem) | Master plant design with the PVSystem class | Workflow 2 | Designing new plants |
| [Creating Plants with EnergyCalculationInputs](#creating-plants-with-energycalculationinputs) | Build flexible plant configurations with Pydantic model payloads | Workflow 3 | Advanced integration and batch processing |
| [Terminating Asynchronous Calculations](#terminating-asynchronous-calculations) | Manage long-running 3D calculations | Workflow 3 | Advanced integration and async 3D workflows |

---

## Using the About and Service Endpoints

**Notebook:** [Example_About_Service_endpoints.ipynb](https://github.com/dnv-opensource/solarfarmer-python-sdk/blob/main/docs/notebooks/Example_About_Service_endpoints.ipynb){ target="_blank" .external }

**Topics Covered:**

- Querying API capabilities and version information
- Understanding service status, typical API key errors and SolarFarmer features

**Use this when:** You need to verify API compatibility, check available features, or understand system capabilities before running calculations.

---

## Running 2D and 3D Calculations

**Notebook:** [Example_EnergyCalculations.ipynb](https://github.com/dnv-opensource/solarfarmer-python-sdk/blob/main/docs/notebooks/Example_EnergyCalculations.ipynb){ target="_blank" .external }

**Topics Covered:**

- 2D synchronous calculations with the ModelChain endpoint
- 3D asynchronous calculations with the ModelChainAsync endpoint
- Accessing and comparing results between approaches
- Handling calculation responses and error cases

**Use this when:** You're working with [Workflow 1 (existing API files)](./workflow-1-existing-api-files.md) and want to understand different calculation methods and their results in detail.

---

## Creating Plants with PVSystem

**Notebook:** [Example_PVSystem.ipynb](https://github.com/dnv-opensource/solarfarmer-python-sdk/blob/main/docs/notebooks/Example_PVSystem.ipynb){ target="_blank" .external }

**Topics Covered:**

- Building plant designs from scratch
- Configuring modules, inverters, and mounting systems
- Setting up weather data and location information
- Advanced plant parameters (bifacial modules, trackers, soiling patterns)

**Use this when:** You're following [Workflow 2 (PVSystem design)](./workflow-2-pvplant-builder.md) and need detailed guidance on plant configuration options and best practices.

---

## Creating Plants with EnergyCalculationInputs

**Notebook:** [Example_Compose_Plant.ipynb](https://github.com/dnv-opensource/solarfarmer-python-sdk/blob/main/docs/notebooks/Example_Compose_Plant.ipynb){ target="_blank" .external }

**Topics Covered:**

- Building structured JSON payloads with `EnergyCalculationInputs` and `PVPlant`
- Flexible plant configuration through composable Pydantic models
- Integrating with custom databases and data models
- Preparing payloads for batch processing

**Use this when:** You're following [Workflow 3 (advanced integration)](./workflow-3-plantbuilder-advanced.md) and integrating SolarFarmer with your own systems or processing multiple projects.

---

## Terminating Asynchronous Calculations

**Notebook:** [Example_TerminateAsync_endpoint.ipynb](https://github.com/dnv-opensource/solarfarmer-python-sdk/blob/main/docs/notebooks/Example_TerminateAsync_endpoint.ipynb){ target="_blank" .external }

**Topics Covered:**

- Managing long-running 3D calculations
- Cancelling asynchronous jobs safely
- Monitoring calculation status

**Use this when:** You're following [Workflow 3 (advanced integration)](./workflow-3-plantbuilder-advanced.md) and need to manage multiple asynchronous calculations or cancel long-running jobs.

---

## Learning Path

**Foundation (Optional but Recommended):**

Review [Using the About and Service Endpoints](#using-the-about-and-service-endpoints) to understand API capabilities

**Then Choose Your Workflow:**

<table style="border-collapse: collapse; width: 100%;">
  <tr style="background-color: #f5f5f5;">
    <th style="border: 1px solid #ddd; padding: 12px; text-align: left;"><strong>Workflow 1:<br>Existing Files</strong></th>
    <th style="border: 1px solid #ddd; padding: 12px; text-align: left;"><strong>Workflow 2:<br>Design Plants</strong></th>
    <th style="border: 1px solid #ddd; padding: 12px; text-align: left;"><strong>Workflow 3:<br>Advanced Integration</strong></th>
  </tr>
  <tr>
    <td style="border: 1px solid #ddd; padding: 12px; vertical-align: top;">Start with <a href="./quick-start-examples.md#example-1-quick-load-and-analyze-workflow-1">Quick Start Example 1</a><br><br>Deepen with <a href="#running-2d-and-3d-calculations">Running 2D and 3D Calculations</a><br><br>Explore <a href="./workflow-1-existing-api-files.md">Workflow 1 Docs</a></td>
    <td style="border: 1px solid #ddd; padding: 12px; vertical-align: top;">Start with <a href="./quick-start-examples.md#example-2-design-optimization-workflow-2">Quick Start Examples 2-5</a><br><br>Master design with <a href="#creating-plants-with-pvsystem">Creating Plants with PVSystem</a><br><br>Explore <a href="./workflow-2-pvplant-builder.md">Workflow 2 Docs</a></td>
    <td style="border: 1px solid #ddd; padding: 12px; vertical-align: top;">Start with <a href="./quick-start-examples.md#example-6-custom-data-model-integration-workflow-3">Quick Start Example 6</a><br><br>Build payloads with <a href="#creating-plants-with-energycalculationinputs">Creating Plants with EnergyCalculationInputs</a><br><br>Manage async with <a href="#terminating-asynchronous-calculations">Terminating Async Calculations</a><br><br>Explore <a href="./workflow-3-plantbuilder-advanced.md">Workflow 3 Docs</a></td>
  </tr>
</table>

---

## Back to Quick Start

If you prefer a hands-on approach with complete workflows, see the [Quick Start Examples](./quick-start-examples.md) for ready-to-run code covering real-world scenarios.

---

## Next Steps

- Review the [API Reference](../api.md) for detailed class and function documentation
- Explore the [Getting Started Workflows](./index.md) for step-by-step guidance
- Browse [SolarFarmer Desktop](https://www.dnv.com/software/services/solarfarmer/) for visual plant design
- Contact support: solarfarmer@dnv.com
