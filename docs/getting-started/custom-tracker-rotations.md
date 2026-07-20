---
title: Custom Tracker Rotations
description: Convert and validate custom tracker rotation CSV schedules
---

# Custom Tracker Rotations

Use a CSV schedule to create the gzip-compressed protobuf file required for
custom tracker rotations in a SolarFarmer 3D calculation.

## Convert a CSV Schedule

```python
import solarfarmer as sf

dataset = sf.custom_rotations.from_csv(
    "tracker_rotations.csv",
    offset_from_utc=1.0,
    rotations_are_at_middle_of_period=False,
)
written = dataset.to_protobuf_file("TrackersConditionsDatasetDto_Protobuf.gz")
```

`to_protobuf_file` returns a list of the paths it wrote. Datasets with up to
40,000 timesteps produce a single file (`TrackersConditionsDatasetDto_Protobuf.gz`).
Larger datasets are split automatically into numbered parts:

```
TrackersConditionsDatasetDto_Protobuf001of002.gz
TrackersConditionsDatasetDto_Protobuf002of002.gz
```

You can override the split threshold:

```python
dataset.to_protobuf_file("TrackersConditionsDatasetDto_Protobuf.gz", max_timesteps_per_file=20_000)
```

For a one-step conversion, use:

```python
import solarfarmer as sf

sf.custom_rotations.csv_to_protobuf(
    "tracker_rotations.csv",
    "TrackersConditionsDatasetDto_Protobuf.gz",
    offset_from_utc=1.0,
)
```

Place the resulting file(s) beside the calculation JSON and other input files.
`run_energy_calculation(inputs_folder_path=...)` discovers both the single-file
and the multi-part naming patterns automatically.

## CSV Format

The CSV has separate local timestamp fields followed by one column for each
tracker rotation ID:

```text
Year,Month,Day,Hour,Minute,Second,Tracker0,Tracker1
2025,1,1,8,0,0,-1.5,-1.5
2025,1,1,8,5,0,-3.0,-3.0
```

`Year`, `Month`, `Day`, `Hour`, and `Minute` are required. `Second` is
optional. `Azimuth` and `Zenith` are accepted only for compatibility with old
exports and are ignored. Tracker rotation IDs are matched case-insensitively,
so the CSV cannot contain both `Group1` and `group1`.

The importer validates calendar timestamps, numeric finite angles, the valid
range from -89.90 to 89.90 degrees, duplicate headers, and strictly increasing
timestamps. It infers the base period from the timestamps; a larger gap is
allowed when a CSV contains daytime rotations only, and every output record
uses the inferred base period.

Timestamps use the fixed `offset_from_utc` supplied to the importer. No
daylight-saving-time adjustment is applied.

## Rotation Direction

SolarFarmer expects negative angles in the morning and positive angles in the
afternoon. If a schedule clearly has the opposite convention, the importer
emits a warning. Reverse it explicitly when needed:

```python
dataset = sf.custom_rotations.from_csv(
    "tracker_rotations.csv",
    offset_from_utc=1.0,
    flip_sign=True,
)
```

## Validate Against Calculation Inputs

When the calculation payload is available, check that the CSV tracker IDs
match the `trackerRotationID` values in its `pvPlant.trackers` collection.
Pass the JSON file path directly — the SDK loads and parses it automatically:

```python
from pathlib import Path
import solarfarmer as sf

dataset = sf.custom_rotations.from_csv(
    "tracker_rotations.csv",
    offset_from_utc=1.0,
    energy_calculation_inputs=Path("EnergyCalculationInputs.json"),
)
```

You can also pass a pre-loaded dict or `EnergyCalculationInputs` object instead
of a path. The check is optional because a CSV can be prepared before the full
payload is available. IDs are compared case-insensitively but the original CSV
spelling is preserved in the generated protobuf file.

## Things to Verify Before Running

The following checks are not enforced by the SDK but are worth confirming
before submitting a calculation.

**Rotation timestamps use the same fixed UTC offset as the weather file.**
The importer applies a fixed `offset_from_utc` to all timestamps; DST
transitions are not applied. Use the same offset you supplied to the weather
file converter.

**The weather data covers the full simulation period.**
The tracker rotation timestamps define the simulation period. If a full-year
weather file is provided but the rotation data covers only three months,
SolarFarmer will simulate those three months only. Verify that weather data
is available for every timestamp in the rotation schedule.

```python
# weather_timestamps: list of datetime objects from your weather source
# (e.g. df.index.to_pydatetime() for a pandas DataFrame)
sf.custom_rotations.check_weather_covers_rotation_period(weather_timestamps, dataset)
```

**The weather and rotation time resolutions are compatible.**
Both files may share the same resolution (e.g. 5-minute weather and
5-minute rotations) or use proportional resolutions (e.g. hourly weather
and 5-minute rotations). In the latter case SolarFarmer interpolates the
weather data to match the rotation timestamps. Be aware that interpolated
irradiance values may differ slightly from the original data.

```python
sf.custom_rotations.check_compatible_time_resolutions(weather_timestamps, dataset)
```