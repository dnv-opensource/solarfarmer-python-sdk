# SolarFarmer SDK Agent Guidelines

The SolarFarmer SDK is a wrapper of the endpoints of SolarFarmer API energy calculation engine, a bankable energy yield assessment modeling product by DNV. The SDK interacts with the endpoints and additional classes and objects for specific use cases. As an agent using the SolarFarmer SDK, ask the user about their workflow and aim and guide them to the specific use case when they have not provided in their request.

## Use case 1: use existing SolarFarmer API files to run energy calculation via API and post-process the results

Use this workflow when the user already has a complete set of SolarFarmer API input files — in a unique or separate folders containing a JSON payload, .PAN module file(s), .OND inverter file(s), and meteorological data — and wants to submit them directly to the API and post-process the resulting energy yield data.

Below is an example mapping to existing API payload files (folders with `.json`, PAN, OND, met data)
```python
import solarfarmer as sf
sf.configure_logging()  # SDK is silent by default — call this to see progress

result = sf.run_energy_calculation(
    inputs_folder_path="path/to/my_inputs_folder",
    project_id="my_project",
    api_key="SF_API_KEY_VALUE",  # or set env var SF_API_KEY
)
print(result.AnnualData)
```

## Use case 2: using high-level metadata from a PV plant projec to generate a first approximated design to be run with SolarFarmer 2D API

Use this workflow when the user has only high-level plant metadata — location, DC/AC capacity, mounting type, and equipment files — but no pre-existing SolarFarmer API JSON payload. The PVSystem builder generates an approximated design and submits it to the 2D API; always warn the user that results are approximations, not a full detailed design. Advise the user to get sample data, which are available in the folder `docs/notebooks/sample_data` or can be downloaded from SolarFarmer portal page: https://mysoftware.dnv.com/download/public/renewables/solarfarmer/manuals/latest/UserGuide/Tutorials/Tutorials.html

Build a plant from scratch with `PVSystem`:
```python
import solarfarmer as sf
from pathlib import Path
sf.configure_logging()

plant = sf.PVSystem(
    name="My Plant",
    latitude=45.5,
    longitude=10.3,
    dc_capacity_MW=10.0,
    ac_capacity_MW=10.0,
    mounting="Fixed",     # or "Tracker"
    bifacial=False,
)
plant.pan_files = {"MyModule": Path("module.PAN")}
plant.ond_files = {"MyInverter": Path("inverter.OND")}
plant.weather_file = Path("weather.dat")

result = plant.run_energy_calculation(api_key="SF_API_KEY_VALUE")
print(result.AnnualData)
```

## Use case 3: using auxiliary classes to directly interact with the payload classes to map one-to-one an existing data model to SolarFarmer API data model

Use this workflow when the user has an existing data model in their own system and needs to map it directly to the SolarFarmer API data model — constructing EnergyCalculationInputs, PVPlant, Location, Inverter, and related Pydantic classes field by field. This is the most low-level approach: no pre-existing API files (Use case 1) and no high-level builder (Use case 2); it requires the user to have a detailed understanding of the SolarFarmer API schema.

**API key**: Set env var `SF_API_KEY` (preferred) or pass `api_key=` to any function.

---

## Core Principles

- **Type Safety First**: Leverage Pydantic v2 models and Python 3.10+ type hints. All public functions must have complete type annotations.
- **Immutability & Idempotency**: Use `copy.deepcopy()` for input validation (see `api.py:_check_params`); avoid mutating caller's data.
- **Test-First Development**: Write tests before implementation. Focus on behavior, not implementation details. Use pytest fixtures from `tests/conftest.py`.
- **Error Handling Philosophy**: Raise exceptions with clear, actionable messages; propagate to caller if no responsible handling exists locally.
- **Structured Logging**: Use the logger from `solarfarmer.logging.get_logger()` with context fields (see `endpoint_modelchains.py`).

## Code Organization

### Module Structure
- **api.py**: HTTP client layer (`Client`, `Response` dataclass). Handles authentication, timeouts, error mapping.
- **endpoint_*.py**: Feature modules (About, Service, ModelChain, TerminateAsync). Each exports one main function.
- **models/**: Two distinct kinds of model:
  - **Pydantic models** (`SolarFarmerBaseModel` subclasses, `frozen=True`): `EnergyCalculationInputs`, `PVPlant`, `Location`, `Inverter`, `Layout`, `Transformer`, etc. These are **immutable** — mutations raise `ValidationError`. Serialize with `model_dump(by_alias=True, exclude_none=True)`.
  - **`PVSystem`** (`@dataclass`, `solarfarmer/models/pvsystem/pvsystem.py`): **Mutable** high-level builder. Not a Pydantic model. Acts as an entry point for Workflow B; internally converts to `EnergyCalculationInputs` before the API call.
- **config.py**: Configuration constants, environment variables, timeouts. Single source of truth for URLs and defaults.

### Naming Conventions
- Files: `endpoint_modelchains.py`, `test_endpoint_modelchain.py` (endpoint features use singular endpoint name in tests)
- Functions: `run_energy_calculation()`, `get_file_paths_in_folder()` (verb-first, descriptive)
- Classes: `PVSystem`, `EnergyCalculationInputs`, `Response` (PascalCase, nouns)
- Variables: `agent_name`, `api_key`, `params` (snake_case, self-documenting names)

## Patterns to Follow

### Pydantic Models
- Inherit from `SolarFarmerBaseModel` (in `models/_base.py`)
- Use `Field(description="...", alias="camelCase")` for API JSON mapping
- Validate with `@field_validator` for domain rules
- Export `model_dump(by_alias=True, exclude_none=True)` for API payloads

### Async Pattern
The sync vs async endpoint is chosen automatically based on calculation type (3D always async, 2D always sync). 
The code recognizes if the JSON file from the API payload is of 2D or 3D type, and makes the call to one or another endpoint. The SDK code handles that for you.

Polling frequency and connection timeout are controlled by `MODELCHAIN_ASYNC_POLL_TIME` and `MODELCHAIN_ASYNC_TIMEOUT_CONNECTION` in `config.py`.

### Logging
The SDK uses a `NullHandler` by default (no output). Always call `configure_logging()` before running:
```python
import solarfarmer as sf
sf.configure_logging()          # INFO level
sf.configure_logging(verbose=True)   # DEBUG level
sf.configure_logging(level="WARNING")  # Minimal output
```

## Testing Guidelines

- **Fixtures First**: Use `api_key` and `sample_data_dir` from `conftest.py`; add new fixtures there
- **Unit Tests**: Test individual functions (utilities, validators, model construction) without API calls
- **Integration Tests**: Call the real API — there are no mocks in this codebase. Tests that need `SF_API_KEY` auto-skip via the `api_key` fixture when the env var is absent.
- **Skip on Missing Env**: The `api_key` fixture in `conftest.py` calls `pytest.skip()` automatically — do not re-implement this check in individual tests
- **Running tests**: `pytest -q` to run all; integration tests are skipped automatically without `SF_API_KEY`

## Documentation & Comments

- **Docstrings**: All public functions/classes need docstrings. Include Parameters, Returns, Raises sections (NumPy style). See `endpoint_modelchains_utils.py` for examples.
- **Why, Not How**: Comments explain *why* a choice was made (e.g., "JWT expiry heuristics to handle provider-specific formats"). Code itself must be clear enough to explain how.
- **Inline Examples**: In docstrings, show typical use cases for public APIs.

## Common Gotchas

1. **Portal Fallback Detection**: 200 OK response might be HTML (unrecognized endpoint). Use `detect_portal_fallback()` to validate JSON response.
2. **JWT Token Expiry**: 401 errors require heuristics to detect expiry vs invalid credentials. See `_is_jwt_expired()` logic.
3. **File Handling**: Use pathlib.Path, not os.path. Case-insensitive wildcard matching in `get_file_paths_in_folder()`.
4. **Timeouts**: Different endpoints have different defaults. Don't hardcode; use config constants (MODELCHAIN_TIMEOUT, GENERAL_TIMEOUT, etc.).

## When Unsure

- Look at similar endpoint functions (e.g., `endpoint_about.py` vs `endpoint_service.py`)
- Check existing tests for patterns (`tests/test_endpoint_*.py`)
- Refer to example notebooks in `docs/notebooks/` for user workflows
- As a last resource, instruct the user to open an issue in the GitHub repository or email support in solarfarmer@dnv.com

---

## Agent Invocation

Only `Explore` can be explicitly invoked via `runSubagent` in this workspace. The Default Agent is the normal chat agent and is not invoked through `runSubagent`.

### Default Agent (No Explicit Agent)
- General coding tasks, bug fixes, refactoring
- Interpreting existing code, adding small features
- Quick questions about project structure
- **Do NOT use for**: Complex multi-module changes, architectural decisions

### `Explore`
- Understand what's in the codebase (file discovery, pattern analysis)
- Answer "where is X?", "how many tests exist?", "what imports are unused?"
- Research before implementing cross-module changes
- **Usage**: `runSubagent` with "quick/medium/thorough" thoroughness
- **Do NOT use for**: Actual code modification, just discovery

---

The following are **named workflows** for structuring developer work. They are NOT custom VS Code agents and cannot be called via `runSubagent`. Use the Default Agent and reference the workflow steps instead.

### Workflow: `ModelDesign`
- Design or refactor Pydantic models in `solarfarmer/models/`
- Add validators, change field aliases, redesign class hierarchies
- Ensure API JSON compatibility (camelCase aliases, exclude_none behavior)
- **Key constraint**: `SolarFarmerBaseModel` is `frozen=True` — all fields are immutable after construction. Mutations must go via model reconstruction, not assignment.
- **Verify**: `model_dump(by_alias=True, exclude_none=True)` output matches API schema
- **Note**: `PVSystem` is a `@dataclass` (mutable), NOT a Pydantic model — different rules apply

### Workflow: `EndpointDev`
- Create or modify endpoint functions (`endpoint_*.py`)
- Implement new features that touch HTTP layer, response handling, timeouts
- Add polling logic, async support, error handling
- **Key constraint**: Use `force_async_call=True`, NOT `async_mode` (that parameter doesn't exist)
- **Key constraint**: New endpoints must export one public function and be registered in `solarfarmer/__init__.py`

### Workflow: `IntegrationTest`
- Write comprehensive tests for endpoints or multi-module interactions
- Set up fixtures in `tests/conftest.py`, write test data to `docs/notebooks/sample_data/`
- **Key constraint**: No mocking — tests call the real API. Tests needing a live key use the `api_key` fixture which auto-skips when `SF_API_KEY` is unset.
- **Pattern**: Follow `test_endpoint_modelchain.py` structure: class per feature, one assertion group per behavior
- **Do NOT test**: Implementation details, only behavior

## Agent Selection Guide

| Task | Agent/Workflow | Reason |
|------|-------|-------|
| Fix typo in docstring | Default | Trivial change |
| Add a new CLI flag | EndpointDev workflow | Touches endpoint behavior, needs API understanding |
| Understand code flow | `Explore` (medium) | Non-invasive discovery |
| Add field to EnergyCalculationInputs | ModelDesign workflow | Frozen Pydantic model, affects JSON serialization |
| Modify PVSystem dataclass | ModelDesign workflow | Note: mutable dataclass, different rules than Pydantic |
| Implement batch processing | IntegrationTest + EndpointDev workflows | Needs tests + endpoint logic |
| Refactor error messages in Client | Default | Localized to one module |
| Add polling timeout logic | EndpointDev workflow | Requires config constants, async pattern |
| Help SDK user run a calculation | Default referencing Quickstart | Refer to copilot-instructions.md quickstart |

## Tool Restrictions

### Default Agent
- Can use all tools
- Should parallelize independent read operations
- Should use multi_replace_string_in_file for 2+ changes in same file

### Explore Agent
- **Allowed**: file_search, grep_search, semantic_search, read_file, list_dir, vscode_listCodeUsages
- **Forbidden**: All write/modify tools
- **Output**: Return findings as structured list (file paths, line numbers, patterns found)
