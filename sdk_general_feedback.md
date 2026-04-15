# SolarFarmer Python SDK — General Usability Feedback

## Context

This document captures non-weather-file observations from building a batch
energy-yield runner on top of `dnv-solarfarmer>=0.2.0rc1`.  Weather file
feedback is covered separately in `sdk_weather_file_feedback.md`.

The implementation was driven by an AI coding agent (Claude) working
interactively with a human engineer.  Both perspectives inform the
observations below.

---

## 1  Error reporting from the API

### 1.1  `run_energy_calculation` returns `None` on failure

When the API returns an HTTP 400 or other error, `run_energy_calculation()`
returns `None` with no exception raised and no error message surfaced to the
caller.  The HTTP response body often contains useful validation messages,
but these are swallowed.

**How debugging actually worked in practice:**

1. `run_energy_calculation()` returned `None`.  No exception, no stderr, no
   log output — nothing to indicate what went wrong.
2. To make progress, we had to enable the SDK's logger at `ERROR` level.
   This revealed HTTP 400 status codes with some error detail — but only
   the subset that `_log_api_failure` manages to extract (see §1.3 below).
3. For errors where the logged detail was just `"Something went wrong."`,
   we had to monkey-patch the HTTP client to intercept raw responses.
4. The error bodies contained clear, actionable validation messages — e.g.
   *"The rack height specified in Mounting Type Specifications 'sat_mount'
   is smaller than the module specifications"* and *"The mounting
   specification is missing one or several of the required bifacial
   properties."*  These were immediately fixable once visible.

The API's validation layer is doing good work — the messages it produces are
specific and actionable.  The problem is entirely on the SDK side: those
messages are discarded and the caller gets `None`.

**Suggestion:** On non-2xx responses, raise a dedicated exception (e.g.
`SolarFarmerAPIError`) that includes the status code, error message, and
the full `ProblemDetails` body.  The `Response` object already contains all
of this information (`code`, `exception`, `problem_details_json`) — it just
needs to be surfaced to the caller rather than logged and discarded.

This is the highest-impact change in this document — every issue described
in §§2–4 and §§7–8 below was ultimately diagnosed through the API's own
error messages, but only after manually bypassing the SDK to read them.

### 1.2  `PVSystem.run_energy_calculation` return type mismatch

`PVSystem.run_energy_calculation()` has a return annotation of `-> None`
and always executes `return None`, storing the result in `self.results`
instead.  However, its docstring says:

> Returns: CalculationResults

This should either return the result (matching the docstring) or the
docstring should be corrected and the `self.results` pattern documented.
Returning `None` while the docstring promises `CalculationResults` will
mislead both human developers and AI agents.

### 1.3  `_log_api_failure` silently swallows parsing errors

`_log_api_failure` (in `endpoint_modelchains.py`) wraps its detail-
extraction logic in a bare `except Exception: pass`.  This means that if
`problem_details_json` isn't in the expected shape, the error detail is
silently lost — the developer sees only the generic `Failure message` line,
not the title, errors, or detail fields.

This is compounded by a type mismatch: `Response.problem_details_json` is
annotated as `str | None`, but `Client._make_request` assigns it the return
value of `response.json()` (a `dict`) on success, or `""` (empty string) on
failure.  When it's an empty string, `json_response.get("errors")` raises
`AttributeError`, which is caught and silently discarded.

**Suggestion:** Fix the type annotation to `dict | None`, handle the empty-
string fallback as `None`, and replace the bare `except` with specific
exception handling (or at least log the parsing error at `DEBUG` level).

---

## 2  Spec ID ↔ filename coupling

The `moduleSpecificationID` and `inverterSpecID` fields in `Layout` and
`Inverter` must exactly match the **filename stems** (without extension) of
the uploaded PAN/OND files.  For example, uploading
`Trina_TSM-DEG19C.20-550_APP.PAN` means the spec ID must be
`Trina_TSM-DEG19C.20-550_APP`.

This coupling is not documented in the field docstrings or in
`run_energy_calculation`.  A developer's natural instinct is to use a
descriptive ID (e.g. `trina_550`), which produces an opaque validation error.

**Suggestion:** Document the filename-stem convention in the
`moduleSpecificationID` and `inverterSpecID` field docstrings.  Alternatively,
the SDK could infer spec IDs from filenames when the user doesn't explicitly
set them, or validate the match client-side before uploading.

---

## 3  Bifacial module auto-detection

When a PAN file contains a non-zero `BifacialityFactor`, the API requires
three additional properties on the `MountingTypeSpecification`:

- `transmissionFactor`
- `bifacialShadeLossFactor`
- `bifacialMismatchLossFactor`

If these are omitted, the API returns a validation error.  However:

1. The SDK does not document this dependency between PAN file contents and
   mounting spec fields.
2. The `MountingTypeSpecification` model does not indicate which fields
   become required for bifacial modules.
3. There is no client-side validation or warning.

**Suggestion:** Add a note in the `MountingTypeSpecification` docstring
explaining that these three fields are required when the module is bifacial.
The PAN file's `BifacialityFactor` value could also be mentioned as the
trigger.

---

## 4  Rack height validation

The `rackHeight` field on `MountingTypeSpecification` must be strictly
greater than the physical height of the module (as specified in the PAN file).
For a portrait-oriented single module high, this means `rackHeight` >
module long dimension (e.g. 2.384 m for the Trina TSM-DEG19C.20-550).

Setting `rackHeight` equal to the module height triggers:
*"The rack height specified in Mounting Type Specifications 'sat_mount' is
smaller than the module specifications."*

This is reasonable validation, but the relationship between `rackHeight`,
`numberOfModulesHigh`, `modulesAreLandscape`, and the PAN file's physical
dimensions is not documented.  A formula or note in the docstring would help:

```
Minimum rackHeight = numberOfModulesHigh × module_dimension
                     + (numberOfModulesHigh - 1) × ySpacingBetweenModules
where module_dimension = module height if portrait, width if landscape
```

---

## 5  `MonthlyAlbedo` constructor

The `MonthlyAlbedo` model accepts a `values` parameter (a list of 12 floats),
not a `monthlyAlbedo` parameter.  This is discoverable via `help()` but the
parameter name is unintuitive — a developer might expect `monthlyAlbedo` or
`albedo_values` given the class name.

Minor point, but mentioning it because an AI agent tried `monthlyAlbedo=`
first (matching the class name pattern) and had to fall back to inspecting
the signature.

---

## 6  `EnergyCalculationOptions.calculationYear`

This field defaults to `1990`.  For TMY data (which contains mixed years by
definition), the relationship between `calculationYear` and the timestamps
in the weather file is unclear.  Does the API remap all timestamps to this
year?  Does it filter?  Does it ignore the year in TMY timestamps?

**Suggestion:** A one-line docstring note explaining how `calculationYear`
interacts with TMY data would prevent confusion.

---

## 7  `gridConnectionLimit` units: docstring says MW, API expects Watts

The `PVPlant.grid_connection_limit` field docstring reads:

> Maximum power that can be exported from the transformers in MW

However, the API expects this value in **Watts**.  Setting
`gridConnectionLimit=17.6` (intending 17.6 MW) causes the API to return
an opaque HTTP 400 with `"detail": "Something went wrong."` — no
indication that the value is being interpreted as 17.6 W.

The `PVSystem` builder correctly converts with `grid_limit_MW * 1e6`
(line 1111 of `pvsystem.py`), confirming the API expects Watts.

**Suggestion:** Fix the docstring to say "in Watts" (or "in W"), not "in
MW".

---

## 8  `TransformerSpecification` is required but marked optional

Both `Transformer.transformer_spec_id` (type `str | None`) and
`PVPlant.transformer_specifications` (type `dict | None`) are marked as
optional in the Pydantic models.  Their docstrings give no indication
that the API requires them:

- `Transformer.transformer_spec_id`: *"Reference to a transformer
  specification"*
- `PVPlant.transformer_specifications`: *"Transformer specs keyed by ID"*

Omitting both fields causes the API to return HTTP 400 with
`"detail": "Something went wrong."` — the same opaque error as the
grid-limit issue.  There is no validation error message indicating
what's missing.

The `PVSystem` builder always creates a `NoLoadAndOhmic` transformer
specification, confirming it's required in practice.

**Suggestion:** Either:
1. Change the field types from `Optional` to required, or add a
   client-side validator on `PVPlant` that raises a clear error when
   a transformer references a spec ID not present in
   `transformer_specifications`.
2. At minimum, update the docstrings to say these fields are
   required by the API despite being structurally optional in the model.

---

## 9  `PVSystem` builder uses PAN-internal module name, not filename stem

The `PVSystem` builder reads the module name from inside the PAN file
content (e.g. `Trina_TSM-DEG19C` from the PVsyst model identifier) and
uses it as the `moduleSpecificationID`.  However, the API requires this
ID to match the **filename stem** of the uploaded PAN file (e.g.
`Trina_TSM-DEG19C.20-550_APP`).

This means `PVSystem.run_energy_calculation()` fails with:

> *The given key 'Trina_TSM-DEG19C' was not present in the dictionary.*

The workaround is to rename the PAN file so its stem matches the internal
model name, but this is fragile and non-obvious.

**Suggestion:** The builder should use the filename stem (from the
`pan_files` dict key or the file path) as the spec ID, not the PAN file's
internal model identifier.

---

## 10  `calculationYear` silently discards TMY data from non-matching years

`EnergyCalculationOptions.calculationYear` defaults to `1990`.  When the
weather file contains TMY data with mixed years (as produced by NSRDB,
PVGIS, and other TMY generators), the API processes **only** rows whose
timestamp year matches `calculationYear`.  For NSRDB PSM4 TMY data, which
uses different years per month (e.g. Jan=2000, Feb=2003, …), this results
in partial-year calculations with dramatically wrong results — and no
warning or error.

In our case, the API silently processed 744 hours (January 2000 only)
instead of 8760, producing −9.18 kWh/kWp and a Performance Ratio of
−0.12.  There was no error message indicating that 92% of the data was
discarded.

**Workaround:** Remap all TMY timestamps to year 1990 before writing the
weather file.

**Suggestion:**
1. Document the interaction between `calculationYear` and TMY timestamps
   prominently — this is not a minor detail, it determines whether the
   calculation produces valid results.
2. Consider adding a warning when the number of processed timesteps is
   significantly less than expected (e.g. <8000 for hourly data).
3. Consider a `TMY` mode or `auto` setting for `calculationYear` that
   either ignores the year component or remaps automatically.

---

## 11  Summary of priorities

| # | Issue | Effort | Impact |
|---|-------|--------|--------|
| 1.1 | Raise exception on API failure instead of returning `None` | Small–Medium | **Critical** — affects every misconfiguration scenario |
| 1.3 | Fix `_log_api_failure` type mismatch and bare `except` | Trivial | **Critical** — causes silent loss of error details |
| 1.2 | Fix `PVSystem.run_energy_calculation` return type | Trivial | Medium — docstring contradicts code |
| 7 | Fix `gridConnectionLimit` docstring (MW → W) | Trivial | **Critical** — causes opaque failure with no diagnostic |
| 8 | Document or require `TransformerSpecification` | Trivial–Small | **High** — another opaque 400 error |
| 10 | Document/fix `calculationYear` + TMY year handling | Small | **High** — silently produces wrong results |
| 9 | Fix `PVSystem` module spec ID (PAN name vs filename) | Small | **High** — `PVSystem` builder fails on common PAN filenames |
| 2 | Document spec ID ↔ filename stem convention | Trivial | High — prevents a common first-use error |
| 3 | Document bifacial mounting property requirements | Trivial | High — prevents a non-obvious validation failure |
| 4 | Document rack height formula / constraints | Trivial | Medium — the error message is helpful but prevention is better |
| 5 | `MonthlyAlbedo` parameter naming | Trivial | Low — minor discoverability improvement |
| 6 | Document `calculationYear` + TMY interaction | Trivial | Medium — subsumed by §10 above |

Items 7, 8, and 10 were the **actual blockers** that prevented a working
API call.  Items 7 and 8 both produce the same opaque `"Something went
wrong."` error, making them indistinguishable without intercepting raw HTTP
responses.  Item 10 produces silently wrong results with no error at all —
arguably worse than a failure.
