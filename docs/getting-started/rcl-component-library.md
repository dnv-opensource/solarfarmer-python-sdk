---
title: Renewable Component Library (RCL)
description: Search and download PV modules and inverters from DNV's curated component database
---

# Renewable Component Library (RCL)

**Best for:** Users who need validated PAN/OND equipment files for energy calculations.

**Scenario:** You want to find and download PV module or inverter files from DNV's curated component database without sourcing files manually.

---

## Overview

The Renewable Component Library (RCL) provides access to a catalog of validated PV modules (PAN files) and inverters (OND files). The SDK includes functions to search, filter, and download equipment files directly from the RCL API.

!!! warning "Monthly Download Limit"
    RCL downloads are rate-limited. Each file download counts against your monthly quota. Use `get_rate_limit_status()` to check your remaining downloads before bulk operations.

---

## Prerequisites

- SolarFarmer API key (same `SF_API_KEY` as for energy calculations)
- Active subscription with RCL access

```python
import solarfarmer as sf
sf.configure_logging()
api_key = os.getenv("SF_API_KEY")
```

---

## Searching the Catalog

### List Modules

Search for PV modules using manufacturer, model, power, and other filters:

```python
# Basic search - first 10 modules
result = sf.rcl.list_modules(top=10)
print(f"Found {result['total']} modules total")

# Filtered search with ordering
result = sf.rcl.list_modules(
    manufacturer_contains="Canadian",
    p_nom_gte=600,
    order_by="pNom",
    order_dir="DESC",
    top=10,
    api_key=api_key
)

# Access items as dicts
for item in result["items"]:
    print(f"{item['manufacturer']} {item['model']}: {item.get('pNom')}W")
```

#### Common Module Filters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `manufacturer` | Exact manufacturer match | `"Canadian Solar Inc."` |
| `manufacturer_contains` | Manufacturer contains substring | `"Canadian"` |
| `model` | Exact model match | `"CS7N-715TB-AG"` |
| `model_contains` | Model contains substring | `"715TB"` |
| `p_nom_gte` | Minimum nominal power (W) | `600` |
| `p_nom_lte` | Maximum nominal power (W) | `800` |
| `bifaciality_factor_gte` | Minimum bifaciality factor | `0.7` |
| `technol` | Technology type | `"mtSi"` |
| `lifecycle_status` | Lifecycle status | `"active"` |

### List Inverters

Search for inverters using similar filters:

```python
result = sf.rcl.list_inverters(
    manufacturer_contains="Sungrow",
    p_nom_conv_gte=100,  # Min 100 kW rated power
    effic_max_gte=98.5,  # Min 98.5% efficiency
    top=10,
)

for item in result["items"]:
    print(f"{item['manufacturer']} {item['model']}: {item.get('pNomConv')} kW")
```

#### Common Inverter Filters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `manufacturer` | Exact manufacturer match | `"Sungrow"` |
| `manufacturer_contains` | Manufacturer contains substring | `"Sungrow"` |
| `model` | Exact model match | `"SG250HX"` |
| `model_contains` | Model contains substring | `"HX"` |
| `p_nom_conv_gte` | Min rated AC power (kW) | `100` |
| `effic_max_gte` | Min max efficiency (%) | `98.5` |
| `v_mpp_min_lte` | Max lower MPPT voltage (V) | `500` |
| `v_mpp_max_gte` | Min upper MPPT voltage (V) | `1100` |
| `nb_mppt_gte` | Min number of MPPTs | `12` |

### Reducing Response Size

Use `output_parameter` to request only specific fields:

```python
result = sf.rcl.list_modules(
    manufacturer_contains="LONGi",
    output_parameter=["pNom", "bifacialityFactor", "technol"],
    top=20,
)
```

<details>
<summary>Available Fields for output_parameter</summary>

- <strong>Module:</strong> `manufacturer`, `model`, `pNom`, `isc`, `voc`, `imp`, `vmp`, `muPmpReq`, `nCelS`, `nCelP`, `bifacialityFactor`, `technol`, `lifecycleStatus` <br>
- <strong>Inverter</strong> `manufacturer`, `model`, `pNomConv`, `pMaxOut`, `efficMax`, `efficEuro`, `vMppMin`, `vMppMax`, `vAbsMax`, `nbMppt`, `transfo`

</details>

### Pagination

For large result sets, use `top` and `skip` for pagination:

```python
all_items = []
skip = 0
page_size = 100

while True:
    result = sf.rcl.list_modules(
        manufacturer_contains="Trina",
        top=page_size,
        skip=skip,
    )
    all_items.extend(result["items"])
    
    if len(result["items"]) < page_size:
        break  # Last page
    skip += page_size

print(f"Retrieved {len(all_items)} modules")
```

---

## Rate Limit Management

### Check Your Status (Zero-Cost)

Check remaining downloads without consuming quota:

```python
status = sf.rcl.get_rate_limit_status()
print(f"{status.remaining}/{status.limit} downloads remaining")
print(f"Resets: {status.reset_datetime}")

if status.usage_percent > 80:
    print("⚠️ Running low on downloads!")
```

### Rate Limit from Responses

Every catalog response includes rate limit info:

```python
result = sf.rcl.list_modules(top=5)
if result["rate_limit"]:
    print(f"Remaining: {result['rate_limit'].remaining}")
```

---

## Downloading Files

!!! warning "Each Download Counts"
    Each call to `download_file()` consumes one credit from your monthly quota,
    even if you already downloaded the same file before. The SDK does not cache
    files locally. If you want to avoid re-downloading, check whether the
    destination path already exists yourself before calling `download_file()`.

### Save to Directory

```python
# Search for a specific module by manufacturer and model
result = sf.rcl.list_modules(
    manufacturer="Canadian Solar",        # Exact manufacturer name
    model="CS7N-715TB-AG",                # Exact model name
    top=1,                                # Only need one result
)

# Get the first (and only) result item
item = result["items"][0]

# Download the PAN file to a directory
# - Uses original filename from the catalog
content = sf.rcl.download_file(
    item["fileUuid"],         # Unique file identifier from catalog
    item["filename"],         # Original filename (e.g., "CS7N-715TB-AG.PAN")
    directory_path="./equipment/modules/"  # Where to save
)
print(f"Saved: {item['filename']} ({len(content)} bytes)")
```

### Save with Custom Filename

```python
content = sf.rcl.download_file(
    item["fileUuid"],
    item["filename"],
    file_path="./my_module.PAN"  # Custom path overrides directory_path
)
```

### Memory Only (No Save)

```python
content = sf.rcl.download_file(
    item["fileUuid"],
    item["filename"],
    save_to_file=False,  # Don't write to disk
)
# content is bytes - process in memory
```

### Avoiding Duplicate Downloads

Since the SDK does not cache files, check the destination yourself if you want
to skip files you already have:

```python
from pathlib import Path

dest = Path("./equipment/") / item["filename"]
if not dest.exists():
    sf.rcl.download_file(item["fileUuid"], item["filename"], directory_path="./equipment/")
```

---

## Typed Catalog Items (IDE Support)

Catalog items are plain `dict`s with the API's original camelCase keys — there is no wrapper class to instantiate. `list_modules()` and `list_inverters()` are typed to return `RCLModuleCatalogResponse`/`RCLInverterCatalogResponse`, whose `items` list is typed as `RCLModuleItemDict`/`RCLInverterItemDict`. This gives IDE autocomplete and key-name checking directly on the returned dicts, with no extra step:

```python
result = sf.rcl.list_modules(manufacturer_contains="Canadian", top=1)

item = result["items"][0]

print(item["fileUuid"])
print(item["manufacturer"])
print(item["model"])
print(item.get("pNom"))              # Module power (W)
print(item.get("bifacialityFactor"))

# Use with download_file:
content = sf.rcl.download_file(item["fileUuid"], item["filename"])
```

---

## Integration with PVSystem

The `PVSystem` class provides methods to search RCL and automatically assign equipment files.

### Set Module from RCL

```python
plant = sf.PVSystem(
    name="My Plant",
    latitude=35.0,
    longitude=-120.0,
    dc_capacity_MW=10.0,
    ac_capacity_MW=8.0,
    mounting="Fixed",
)

# Search and download if exactly one match
module = plant.set_module_from_rcl(
    manufacturer_contains="Canadian Solar",
    model_contains="CS7N-715TB-AG",
    directory_path="./equipment/"
)
print(f"Assigned: {module['filename']}")
print(plant.pan_files)  # {'CS7N-715TB-AG': Path('./equipment/...')}
```

### Set Inverter from RCL

```python
inverter = plant.set_inverter_from_rcl(
    manufacturer_contains="Sungrow",
    model_contains="SG250HX",
    directory_path="./equipment/"
)
print(f"Assigned: {inverter['filename']}")
```

### Handling Multiple Matches

By default (`strict=True`), the method raises a `ValueError` with suggestions when multiple results are found:

```python
try:
    plant.set_module_from_rcl(
        manufacturer_contains="Canadian Solar",
        model_contains="CS6w",  # Too broad
    )
except ValueError as e:
    print(e)
    # INFO: 20 modules found, retrieved 20.
    # 20 modules found. Narrow your search:

    #   1. Canadian Solar - CS6W-565TB-AG (565W bifacial)
    #      → Add: model="CS6W-565TB-AG" or p_nom=565 or bifaciality_factor_gte=0.7

    #   2. Canadian Solar - CS6W-570TB-AG (570W bifacial)
    #      → Add: model="CS6W-570TB-AG" or p_nom=570 or bifaciality_factor_gte=0.7
    #   ...
```

For exploratory use, set `strict=False` to print the message and return `None` instead of raising:

```python
# Returns None and prints suggestions (no exception)
result = plant.set_module_from_rcl(
    manufacturer_contains="Canadian Solar",
    model_contains="CS6W",
    strict=False,
)
if result is None:
    print("Refine your search criteria")
```

---

## Complete Example

```python
import solarfarmer as sf
from pathlib import Path

sf.configure_logging()

# 1. Check rate limit before downloading
status = sf.rcl.get_rate_limit_status()
print(f"Downloads available: {status.remaining}/{status.limit}")

if status.remaining < 5:
    print("Low on downloads - consider waiting until reset")
    print(f"Resets: {status.reset_datetime}")

# 2. Search for equipment
modules = sf.rcl.list_modules(
    manufacturer_contains="LONGi",
    p_nom_gte=550,
    bifaciality_factor_gte=0.7,
    output_parameter=["pNom", "bifacialityFactor"],
    top=5,
)
print(f"Found {modules['total']} matching modules")

inverters = sf.rcl.list_inverters(
    manufacturer_contains="Huawei",
    p_nom_conv_gte=200,
    top=5,
)
print(f"Found {inverters['total']} matching inverters")

# 3. Create plant and assign equipment
plant = sf.PVSystem(
    name="RCL Demo Plant",
    latitude=33.45,
    longitude=-112.07,
    dc_capacity_MW=50.0,
    ac_capacity_MW=40.0,
    mounting="Tracker",
)

# Direct assignment from specific search result
if modules["items"]:
    item = modules["items"][0]
    content = sf.rcl.download_file(
        item["fileUuid"],
        item["filename"],
        directory_path="./equipment/"
    )
    plant.pan_files = {item["model"]: Path(f"./equipment/{item['filename']}")}

# Or use the integrated method for automatic search + download
plant.set_inverter_from_rcl(
    manufacturer_contains="Huawei",
    model_contains="SUN2000-215KTL",
    directory_path="./equipment/"
)

# 4. Continue with energy calculation...
print(f"Plant configured with: {list(plant.pan_files.keys())}")
print(f"Inverter: {list(plant.ond_files.keys())}")
```

---

## API Reference

See the full API documentation for detailed parameter descriptions:

- [`sf.rcl.list_modules()`](../api.md#solarfarmer.rcl.list_modules)
- [`sf.rcl.list_inverters()`](../api.md#solarfarmer.rcl.list_inverters)
- [`sf.rcl.download_file()`](../api.md#solarfarmer.rcl.download_file)
- [`sf.rcl.get_rate_limit_status()`](../api.md#solarfarmer.rcl.get_rate_limit_status)
