---
title: Quick Start Examples
description: Real-world examples showing how classes interact in complete workflows
---

# Quick Start Examples

Below are complete, runnable examples demonstrating real-world use cases. Each example shows how the core classes work together.

## Quick Reference

| # | Example | Purpose | Workflow | Time |
|---|---|---|---|---|
| 1 | [Quick Load & Analyze](#example-1-quick-load-and-analyze-workflow-1) | Load existing calculation and view results | Workflow 1 | 5 min |
| 2 | [Design Optimization](#example-2-design-optimization-workflow-2) | Design plant, optimize tilt angle | Workflow 2 | 10 min |
| 3 | [Bifacial Analysis](#example-3-bifacial-module-analysis-workflow-2) | Compare monofacial vs bifacial modules | Workflow 2 | 10 min |
| 4 | [Tracker Comparison](#example-4-tracker-vs-fixed-analysis-workflow-2) | Compare single-axis tracker vs fixed-tilt | Workflow 2 | 10 min |
| 5 | [Soiling Impact](#example-5-soiling-impact-analysis-workflow-2) | Analyze soiling effects by climate | Workflow 2 | 10 min |
| 6 | [Custom Integration](#example-6-custom-data-model-integration-workflow-3) | Map database to SolarFarmer, batch process | Workflow 3 | 15 min |

---

## Example 1: Quick Load and Analyze (Workflow 1)

**Scenario:** You have an existing SolarFarmer calculation and want to load and analyze results.

**Classes Used:**

[`run_energy_calculation()`](../api.md#endpoint-functions) → [`ModelChainResponse`](../api.md#modelchainresponse) → [`CalculationResults`](../api.md#calculationresults)

```python
import solarfarmer as sf
import pandas as pd

# Load and run calculation
results = sf.run_energy_calculation(
    inputs_folder_path=r"C:\data\my_project\inputs",
    project_id="quick_analysis",
    api_key="your_key",
    save_outputs=True
)

# Access results
annual_data = results.AnnualData[0]
net_energy = annual_data['energyYieldResults']['netEnergy']
performance_ratio = annual_data['energyYieldResults']['performanceRatio']

print(f"Net Energy: {net_energy:.1f} MWh")
print(f"Performance Ratio: {performance_ratio:.1%}")

# Get loss tree time-series results
loss_tree_timeseries = results.loss_tree_timeseries

# Print summary
results.print_annual_results()
```

**Files Required:**

- `inputs/EnergyCalcInputs.json`
- `inputs/module.PAN`
- `inputs/inverter.OND`
- `inputs/weather_data.csv`

---

## Example 2: Design Optimization (Workflow 2)

**Scenario:** Design a 5 MW plant and optimize tilt angle for maximum yield.

**Classes Used:**

[`PVSystem`](../api.md#pvsystem) → [`run_energy_calculation()`](../api.md#endpoint-functions) → [`CalculationResults`](../api.md#calculationresults)

```python
from solarfarmer import PVSystem
import pandas as pd

# Define base plant
base_plant = PVSystem(
    name="5MW Design Study",
    latitude=40.0,
    longitude=-75.0,
    altitude=100,
    timezone="America/New_York",
    dc_capacity_MW=5.0,
    ac_capacity_MW=4.5,
    mounting="Fixed",
    azimuth=180.0,  # South-facing
    gcr=0.4
)

# Add equipment files
base_plant.add_pan_files({
    "MyModule": Path("data/module.PAN")
})

base_plant.add_ond_files({
    "MyInverter": Path("data/inverter.OND")
})

base_plant.weather_file = Path("data/weather.csv")

# Optimize tilt angle
tilt_angles = [15, 20, 25, 30, 35, 40]
results_list = []

for tilt in tilt_angles:
    # Create variation
    plant_variant = base_plant.make_copy()
    plant_variant.name = f"Tilt {tilt}°"
    plant_variant.tilt = tilt

    # Run calculation
    plant_variant.run_energy_calculation(
        project_id=f"tilt_{tilt}",
        api_key="your_key",
        print_summary=False
    )

    # Collect results
    annual_data = plant_variant.results.AnnualData[0]
    results_list.append({
        'tilt': tilt,
        'net_energy_mwh': annual_data['energyYieldResults']['netEnergy'],
        'performance_ratio': annual_data['energyYieldResults']['performanceRatio'],
        'design_summary': plant_variant.design_summary
    })

# Find optimal tilt
df_results = pd.DataFrame(results_list)
optimal_row = df_results.loc[df_results['net_energy_mwh'].idxmax()]

print("Optimization Results:")
print(df_results.to_string())

tilt = optimal_row['tilt']
energy = optimal_row['net_energy_mwh']
print(f"\nOptimal Tilt: {tilt}° with {energy:.1f} MWh/year")
```

**Output:**
```
Optimization Results:
   tilt  net_energy_mwh  performance_ratio
0    15       2250.5              0.812
1    20       2310.2              0.827
2    25       2345.8              0.835  ← Optimal
3    30       2340.2              0.833
4    35       2310.5              0.827
5    40       2255.3              0.814

Optimal Tilt: 25° with 2345.8 MWh/year
```

---

## Example 3: Bifacial Module Analysis (Workflow 2)

**Scenario:** Compare monofacial vs bifacial modules for a fixed-tilt plant.

**Classes Used:**

[`PVSystem`](../api.md#pvsystem) → [`run_energy_calculation()`](../api.md#endpoint-functions) → [`CalculationResults`](../api.md#calculationresults)

```python
from solarfarmer import PVSystem
import pandas as pd

# Base configuration
def create_base_plant(bifacial: bool = False) -> PVSystem:
    plant = PVSystem(
        name=f"Bifacial Study - {'Yes' if bifacial else 'No'}",
        latitude=40.0,
        longitude=-75.0,
        dc_capacity_MW=5.0,
        ac_capacity_MW=4.5,
        mounting="Fixed",
        tilt=25.0,
        azimuth=180.0,
        bifacial=bifacial,
        gcr=0.35,
        mounting_height=1.0
    )

    # Parameters differ for bifacial
    if bifacial:
        plant.bifacial_transmission = 0.05
        plant.bifacial_shade_loss = 0.15
        plant.bifacial_mismatch_loss = 0.01

    plant.add_pan_files({"Module": Path("data/module.PAN")})
    plant.add_ond_files({"Inverter": Path("data/inverter.OND")})
    plant.weather_file = Path("data/weather.csv")

    return plant

# Run comparison
configurations = {
    'monofacial': create_base_plant(bifacial=False),
    'bifacial': create_base_plant(bifacial=True)
}

results = {}
for config_name, plant in configurations.items():
    plant.run_energy_calculation(
        project_id=f"bifacial_{config_name}",
        api_key="your_key"
    )

    annual_data = plant.results.AnnualData[0]
    results[config_name] = {
        'net_energy_mwh': annual_data['energyYieldResults']['netEnergy'],
        'performance_ratio': annual_data['energyYieldResults']['performanceRatio'],
        'design': plant.design_summary
    }

# Compare
mono_energy = results['monofacial']['net_energy_mwh']
bi_energy = results['bifacial']['net_energy_mwh']
improvement = (bi_energy - mono_energy) / mono_energy * 100

print(f"Monofacial: {mono_energy:.1f} MWh/year")
print(f"Bifacial:   {bi_energy:.1f} MWh/year")
print(f"Improvement: {improvement:.1f}%")
```

---

## Example 4: Tracker vs Fixed Analysis (Workflow 2)

**Scenario:** Compare single-axis tracker vs fixed-tilt for the same location.

**Classes Used:**

[`PVSystem`](../api.md#pvsystem) → [`run_energy_calculation()`](../api.md#endpoint-functions) → [`CalculationResults`](../api.md#calculationresults)

```python
from solarfarmer import PVSystem
import pandas as pd

def create_plant(mounting_type: str) -> PVSystem:
    plant = PVSystem(
        name=f"Comparison - {mounting_type}",
        latitude=35.0,  # Good tracker location
        longitude=-106.0,
        dc_capacity_MW=5.0,
        ac_capacity_MW=4.5,
        mounting=mounting_type,
        azimuth=180.0,
    )

    if mounting_type == "Fixed":
        plant.tilt = 35.0  # Optimal for this latitude
        plant.gcr = 0.35
    else:  # Tracker
        plant.tilt = 60.0  # Max rotation angle
        plant.gcr = 0.3   # Trackers need wider spacing

    plant.add_pan_files({"Module": Path("data/module.PAN")})
    plant.add_ond_files({"Inverter": Path("data/inverter.OND")})
    plant.weather_file = Path("data/weather.csv")
    return plant

# Compare
mounting_types = ["Fixed", "Tracker"]
comparison_results = []

for mounting in mounting_types:
    plant = create_plant(mounting)
    plant.run_energy_calculation(
        project_id=f"mounting_{mounting}",
        api_key="your_key"
    )

    annual_data = plant.results.AnnualData[0]
    comparison_results.append({
        'mounting': mounting,
        'net_energy_mwh': annual_data['energyYieldResults']['netEnergy'],
        'performance_ratio': annual_data['energyYieldResults']['performanceRatio']
    })

df = pd.DataFrame(comparison_results)
print(df.to_string(index=False))

# Cost-benefit analysis
fixed_pr = df[df['mounting'] == 'Fixed']['performance_ratio'].values[0]
tracker_pr = df[df['mounting'] == 'Tracker']['performance_ratio'].values[0]
pr_improvement = (tracker_pr / fixed_pr - 1) * 100

print(f"\nPerformance ratio improvement: {pr_improvement:.1f}%")
```

---

## Example 5: Soiling Impact Analysis (Workflow 2)

**Scenario:** Analyze how soiling affects annual yield in different climates.

**Classes Used:**

[`PVSystem`](../api.md#pvsystem) → [`run_energy_calculation()`](../api.md#endpoint-functions) → [`CalculationResults`](../api.md#calculationresults)

```python
from solarfarmer import PVSystem
import pandas as pd

# Soiling patterns: desert vs temperate
SOILING_PATTERNS = {
    'clean_desert': [0.05, 0.05, 0.06, 0.08, 0.10, 0.12,
                     0.12, 0.10, 0.08, 0.06, 0.05, 0.04],
    'temperate': [0.08, 0.08, 0.07, 0.06, 0.05, 0.04,
                  0.04, 0.05, 0.06, 0.07, 0.08, 0.09],
    'dusty': [0.15, 0.15, 0.14, 0.12, 0.10, 0.08,
              0.08, 0.10, 0.12, 0.14, 0.15, 0.16]
}

results = []

for pattern_name, soiling_values in SOILING_PATTERNS.items():
    plant = PVSystem(
        name=f"Soiling Analysis - {pattern_name}",
        latitude=40.0,
        longitude=-75.0,
        dc_capacity_MW=5.0,
        ac_capacity_MW=4.5,
        soiling_loss=soiling_values
    )

    plant.add_pan_files({"Module": Path("data/module.PAN")})
    plant.add_ond_files({"Inverter": Path("data/inverter.OND")})
    plant.weather_file = Path("data/weather.csv")

    plant.run_energy_calculation(
        project_id=f"soiling_{pattern_name}",
        api_key="your_key"
    )

    # Calculate annual soiling loss
    avg_soiling = sum(soiling_values) / len(soiling_values)
    annual_data = plant.results.AnnualData[0]
    results.append({
        'pattern': pattern_name,
        'avg_soiling': avg_soiling,
        'net_energy_mwh': annual_data['energyYieldResults']['netEnergy'],
        'performance_ratio': annual_data['energyYieldResults']['performanceRatio']
    })

df = pd.DataFrame(results)
clean_energy = df[df['pattern'] == 'clean_desert']['net_energy_mwh'].values[0]
df['energy_loss_%'] = (1 - df['net_energy_mwh'] / clean_energy) * 100

print(df[['pattern', 'avg_soiling', 'energy_loss_%']].to_string())
```

---

## Example 6: Custom Data Model Integration (Workflow 3)

**Scenario:** Map your internal project database to SolarFarmer and batch process multiple projects.

**Classes Used:**

[`EnergyCalculationInputs`](../api.md#energycalculationinputs) + [`PVPlant`](../api.md#pvplant) + [`Location`](../api.md#location)

```python
from solarfarmer import (
    EnergyCalculationInputs, PVPlant, Location,
    Inverter, Layout, Transformer, MountingTypeSpecification,
    EnergyCalculationOptions, DiffuseModel, MonthlyAlbedo,
)
from pathlib import Path
import solarfarmer as sf

class ProjectFromDatabase:
    """Simulates your internal project database"""

    @staticmethod
    def get_projects() -> list:
        return [
            {
                'project_id': 'proj_001',
                'name': 'Desert Project',
                'latitude': 32.0,
                'longitude': -111.0,
                'capacity_mw': 10.0,
                'modules': 25000,
                'tilt': 20,
            },
            {
                'project_id': 'proj_002',
                'name': 'Temperate Project',
                'latitude': 40.0,
                'longitude': -75.0,
                'capacity_mw': 5.0,
                'modules': 12500,
                'tilt': 30,
            },
        ]

def convert_project_to_inputs(project: dict) -> EnergyCalculationInputs:
    """Convert a database project to a SolarFarmer EnergyCalculationInputs object"""

    location = Location(
        latitude=project['latitude'],
        longitude=project['longitude'],
        altitude=100.0,
    )

    # Build layout, inverter, transformer (simplified)
    layout = Layout(
        name="Layout 1",
        layout_count=1,
        inverter_input=[0],
        module_specification_id="mymodule",
        mounting_type_id="Fixed-Tilt",
        total_number_of_strings=100,
        string_length=25,
        azimuth=180.0,
        tilt=float(project['tilt']),
    )
    inverter = Inverter(
        name="Inverter_1",
        inverter_spec_id="myinverter",
        inverter_count=1,
        layouts=[layout],
    )
    transformer = Transformer(
        name="Transformer1",
        transformer_count=1,
        transformer_spec_id="transformer_spec_1",
        inverters=[inverter],
    )
    pv_plant = PVPlant(
        transformers=[transformer],
        mounting_type_specifications={
            "Fixed-Tilt": MountingTypeSpecification(
                is_tracker=False,
                number_of_modules_high=1,
                tilt=float(project['tilt']),
                height_of_lowest_edge_from_ground=1.5,
            )
        },
    )

    return EnergyCalculationInputs(
        location=location,
        monthly_albedo=MonthlyAlbedo.from_list([0.2] * 12),
        pv_plant=pv_plant,
        energy_calculation_options=EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
        ),
    )

# Process all projects
projects = ProjectFromDatabase.get_projects()

for project in projects:
    inputs = convert_project_to_inputs(project)
    payload_json = inputs.model_dump_json(by_alias=True, exclude_none=True)

    # Optionally save to file
    output_file = f"payloads/{project['project_id']}_payload.json"
    Path(output_file).parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(payload_json)

    print(f"✓ Generated payload for {project['name']}")

print(f"\nGenerated {len(projects)} payloads for batch submission")
```

---

## Learning Path

**Quick Start Learning:**

1. **Start here:** [Example 1](#example-1-quick-load-and-analyze-workflow-1) (5 min) - Load existing calculations
2. **Next:** [Example 2](#example-2-design-optimization-workflow-2) (10 min) - Design a plant from scratch
3. **Deepen:** [Example 3](#example-3-bifacial-module-analysis-workflow-2), [Example 4](#example-4-tracker-vs-fixed-analysis-workflow-2) and [Example 5](#example-5-soiling-impact-analysis-workflow-2) - Compare configurations
4. **Advanced:** [Example 6](#example-6-custom-data-model-integration-workflow-3) - Integrate your own data model

**Complementary In-Depth Learning:**

As you progress through the quick-start examples, reference the [End-to-End Examples](end-to-end-examples.md) to deepen your understanding of specific API features and capabilities.

---

## Troubleshooting Examples

| Error | Solution |
|---|---|
| `FileNotFoundError` | Ensure weather file and equipment files exist at specified paths |
| `API Key Error` | Set `SF_API_KEY` environment variable or pass `api_key` parameter |

---

## Next Steps

- Review the [API Reference](../api.md) for detailed class documentation
- Explore the End-to-End Examples in the Example Notebooks section for advanced techniques and specific feature deep-dives
- Browse [SolarFarmer Desktop](https://www.dnv.com/software/services/solarfarmer/) for visual plant design
- Contact support: solarfarmer@dnv.com
