from __future__ import annotations

import copy as copy_module
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ...logging import get_logger
from ..auxiliary_losses import AuxiliaryLosses
from ..energy_calculation_inputs import EnergyCalculationInputs
from ..energy_calculation_options import EnergyCalculationOptions
from ..energy_calculation_results import CalculationResults
from ..enums import (
    DiffuseModel,
    TransformerLossModelTypes,
)
from ..inverter import Inverter
from ..layout import Layout
from ..location import Location
from ..monthly_albedo import MonthlyAlbedo
from ..mounting_type_specification import MountingTypeSpecification
from ..pan_supplements import PanFileSupplements
from ..pv_plant import PVPlant
from ..tracker_system import TrackerSystem
from ..transformer import Transformer
from ..transformer_specification import TransformerSpecification
from .plant_defaults import (
    BIFACIAL_DICT,
    CONSTANT_HEAT_COEFFICIENT,
    CONVECTIVE_HEAT_COEFFICIENT,
    FRAME_BOTTOM_WIDTH,
    HEIGHT_FROM_GROUND_FIXED,
    HEIGHT_FROM_GROUND_TRACKER,
    IS_BACKTRACKING,
    MODULE_MISMATCH_FACTOR,
    NUMBER_OF_MODULES_HIGH,
    OHMIC_DICT,
    STRINGS_IN_BACK_ROW,
    STRINGS_IN_FRONT_ROW,
    STRINGS_IN_ISOLATED_ROW,
    STRINGS_IN_LEFT_ROW,
    STRINGS_IN_RIGHT_ROW,
    TERRAIN_AZIMUTH,
    TERRAIN_SLOPE,
    TRANSFORMER_COUNT,
    TRANSFORMER_DICT,
    TRANSFORMER_NAME,
    TRANSFORMER_SPEC_ID,
    Y_GAP,
    InverterType,
    MountingType,
    OrientationType,
)
from .plant_utils import (
    calculate_module_parameters,
    get_inverter_mppt,
    read_ond_file,
    read_pan_file,
)

_logger = get_logger("models.pvsystem")

PathLike = str | Path


@dataclass
class PVSystem:
    """
    This is the main class to define a PV System using basic metadata and design characteristics.
    It is also a calculation entrypoint for the defined plant. It has multiple properties that
    can be set or left as default, depending on the level of detail available to the user.
    The class is designed to be flexible and user-friendly, with sensible defaults and validation
    to ensure that the provided data is consistent and complete for the API calculation.

    .. note::
       ``PVSystem`` generates an approximated plant design from high-level specifications.
       It infers layout geometry, string sizing, and loss parameters using simplified
       assumptions (e.g., uniform mid-row shading). Results are suitable for early-stage
       energy yield screening but do not represent a fully detailed design.

    Basic Metadata
    --------------
    name: str | None
        Name of the plant/project. Optional.

    Location Metadata
    -----------------
    latitude : float | None
        Plant latitude in degrees (-90 .. 90).
    longitude : float | None
        Plant longitude in degrees (-180 .. 180).
    altitude : float | 0.0
        Plant altitude in meters above sea level.
    timezone : str
        IANA timezone name (e.g., 'UTC', 'Europe/Amsterdam'). Default is 'UTC'.

    Plant Definition
    ----------------
    dc_capacity_MW : float
        Plant DC capacity in MW (default 10.0).
    ac_capacity_MW : float
        Plant AC capacity in MW (default 10.0).
    grid_limit_MW : float
        Grid capacity limit for the plant connection in MW (default 10.0).
    gcr : float
        Ground coverage ratio (default 0.5). Define either gcr or pitch, not both.
    pitch : float
        Array pitch in meters (default 10.0). Define either gcr or pitch, not both.
    tilt : float
        Array tilt in degrees. For fixed-tilt mounting, the default is the latitude rounded to degrees.
        For trackers, this is the used as the maximum rotation angle (60 degrees if not specified).
    azimuth : float
        Array azimuth in degrees (default 180, i.e., south-facing).
    mounting: str
        Mounting configuration: 'Fixed' for fixed-tilt or 'Tracker' for single-axis trackers.
        Available as ``solarfarmer.MountingType`` enum (e.g., ``sf.MountingType.FIXED``).
    flush_mount : bool
        If True, indicates flush-mounted arrays (default is False).
    bifacial: bool
        If True, indicates bifacial modules (default is False).
    inverter_type: str
        Inverter type: 'Central' or 'String' (default is 'Central').
        Affects the default DC and AC ohmic losses used, which can be overridden via
        `dc_ohmic_loss` and `ac_ohmic_loss`.
    transformer_stages: int
        Number of transformer stages. 0 for ideal behaviour or 1 for one stage (default is 1).

    Auxiliary Files
    ---------------
    pan_files : dict[str, Path]
        Mapping of module names to PAN file paths.
    ond_files : dict[str, Path]
        Mapping of inverter names to OND file paths.
    weather_file : Path | None
        Path to a weather file (string or Path accepted via property).
    horizon_file : Path | None
        Path to a horizon file (string or Path accepted via property).

    Other Effects and Settings
    --------------------------
    mounting_height: Optional[float] = None
        Mounting height in meters. It refers to the minimum height from ground for fixed-tilt
         and axis-tube height for single-axis trackers (default is 1.5 m).
    modules_across: Optional[int] = None
        Number of modules across in the mounting configuration
        (default is 1 for both trackers and fixed-tilt).
    string_length: Optional[int] = None
        Number of modules in series per string
        (default is calculated from the module and inverter provided).
    dc_ohmic_loss: Optional[float] = None
        DC ohmic loss (per unit) (default depends on inverter type).
    ac_ohmic_loss: Optional[float] = None
        AC ohmic loss (per unit) (default depends on inverter type).
    module_mismatch: Optional[float] = None
        Module mismatch loss (per unit) (default is 0.005).
    module_quality_factor: Optional[float] = None
        Module quality factor (per unit) (default is 0.0, i.e., no quality loss).
    lid_loss: Optional[float] = None
        Loss due to light-induced degradation (LID) (per unit) (default is 0.0, i.e., no LID loss).
    module_iam_model_override: Optional[IAMModelTypeForOverride] = None
        Override for the module IAM model used in the calculation (default is None,
        which will use the values from the module's PAN file).
    constant_heat_coefficient : Optional[float] = None
        Constant heat transfer coefficient (Uc).
    convective_heat_coefficient : Optional[float] = None
        Convective heat transfer coefficient (Uv).
    soiling_loss : Optional[List[float]] = None
        Monthly soiling loss (per unit), 12 values in [0,1]. If set with 1 value, it's expanded to 12.
    albedo: Optional[List[float]] = None
        Monthly albedo (per unit), 12 values in [0,1]. If set with 1 value, it's expanded to 12.
    transformer_fixed_loss : Optional[float] = None
        Transformer fixed loss (per unit).
    transformer_variable_loss : Optional[float] = None
        Transformer variable loss (per unit).
    bifacial_transmission : Optional[float] = None
        Bifacial transmission gain (per unit). Applicable only if `bifacial` is True.
    bifacial_shade_loss : Optional[float] = None
        Bifacial shade loss (per unit). Applicable only if `bifacial` is True.
    bifacial_mismatch_loss : Optional[float] = None
        Bifacial mismatch loss (per unit). Applicable only if `bifacial` is True.
    aux_loss_fixed_factor: Optional[float] = None
        Simple loss as a fraction of AC output (per unit).
    aux_loss_power: Optional[float] = None
        Constant power loss in Watts.
    aux_loss_apply_at_night: Optional[bool] = None
        Whether to apply the simple loss factor during night hours (True or False).
    horizon_elevation_angles : Optional[List[float]] = None
        List of horizon elevation angles (degrees).
    horizon_azimuth_angles : Optional[List[float]] = None
        List of horizon azimuth angles (degrees) with the convention
        0 to 359 degrees, clockwise from North (North (0°), East (90°),
        South (180°), West (270°)).
    generate_pvsyst_format_timeseries : bool
        If True, generates PVsyst format timeseries output (default is True).
    generate_loss_tree_timeseries : bool
        If True, generates loss tree timeseries output (default is True).
    enable_spectral_modeling : bool
        If True, enables spectral modeling in the calculation (default is False).

    Methods
    -------
    - horizon(elevation_angles, azimuth_angles)
    - run_energy_calculation(force_async_call=False)
    - describe(verbose=False)
    - to_file(path)
    - from_file(path)
    - make_copy()
    - payload_to_file(path)

    Notes
    -----
    - All setters accept `str` or `Path` for paths; stored internally as `Path`.
    """

    # Basic metadata
    name: str | None = None

    # Location metadata
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = 0.0
    timezone: str = "UTC"

    # Files (stored as Path internally)
    _weather_file: Path | None = field(default=None, repr=False)
    _horizon_file: Path | None = field(default=None, repr=False)

    # Horizon angles
    horizon_elevation_angles: list[float] | None = field(default_factory=list)
    horizon_azimuth_angles: list[float] | None = field(default_factory=list)

    # Plant definition
    dc_capacity_MW: float = 10.0
    ac_capacity_MW: float = 10.0
    grid_limit_MW: float = 10.0
    gcr: float = 0.5
    pitch: float | None = None  # If None, calculated from gcr and module dimensions
    tilt: float | None = None  # Default is latitude rounded to degrees
    azimuth: float = 180.0
    mounting: MountingType = MountingType.FIXED
    flush_mount: bool = False
    bifacial: bool = False
    inverter_type: InverterType | None = InverterType.CENTRAL
    transformer_stages: int = 1

    # Effects and settings
    mounting_height: float | None = None  # Changed from: mounting_height: float
    modules_across: int | None = None
    module_orientation: OrientationType = OrientationType.PORTRAIT
    string_length: int | None = None  # Estimated from module and inverter provided
    dc_ohmic_loss: float | None = None  # Default depends on inverter type
    ac_ohmic_loss: float | None = None  # Default depends on inverter type
    module_mismatch: float | None = MODULE_MISMATCH_FACTOR
    module_quality_factor: float | None = 0.0
    lid_loss: float | None = 0.0
    module_iam_model_override: str | None = None
    constant_heat_coefficient: float | None = CONSTANT_HEAT_COEFFICIENT
    convective_heat_coefficient: float | None = CONVECTIVE_HEAT_COEFFICIENT
    transformer_fixed_loss: float | None = None  # Default depends on transformer stages
    transformer_variable_loss: float | None = None  # Default depends on transformer stages
    bifacial_transmission: float | None = None  # Default depends on bifacial flag
    bifacial_shade_loss: float | None = None  # Default depends on bifacial flag
    bifacial_mismatch_loss: float | None = None  # Default depends on bifacial flag
    aux_loss_fixed_factor: float | None = None
    aux_loss_power: float | None = None
    aux_loss_apply_at_night: bool | None = None
    horizon_elevation_angles: list[float] | None = None
    horizon_azimuth_angles: list[float] | None = None
    generate_pvsyst_format_timeseries: bool = True
    generate_loss_tree_timeseries: bool = True
    enable_spectral_modeling: bool = False

    # Auxiliary files
    _pan_files: dict[str, Path] = field(default_factory=dict, repr=False)
    _ond_files: dict[str, Path] = field(default_factory=dict, repr=False)

    # Results
    results: CalculationResults = None

    # payload dictionary
    payload: dict[str, Any] = None

    # design summary dictionary
    design_summary: dict[str, Any] = None

    # Backing fields for soiling_loss and albedo with default values
    _soiling_loss: list[float] = field(default_factory=lambda: [0.0] * 12)
    _albedo: list[float] = field(default_factory=lambda: [0.2] * 12)

    def _to_float_list_1d(self, values: Iterable, *, name: str) -> list[float]:
        """
        Convert an iterable (list/tuple/np.array) into a flat list[float].
        Raises TypeError for non-iterable or nested structures.
        """
        try:
            # Handle numpy arrays if present without importing: rely on duck-typing
            lst = list(values)
        except TypeError as err:
            raise TypeError(f"{name} must be an iterable of numeric values.") from err
        # Basic flattening guard (reject nested lists)
        for v in lst:
            if isinstance(v, (list, tuple)):
                raise TypeError(f"{name} must be 1D; nested sequences are not allowed.")
        return [float(v) for v in lst]

    def _validate_0_1(self, arr: Sequence[float], *, name: str) -> None:
        for v in arr:
            if v < 0.0 or v > 1.0:
                raise ValueError(f"{name} values must be in [0, 1], got {v}.")

    def _ensure_len_12(self, arr: Sequence[float], *, name: str) -> None:
        if len(arr) != 12:
            raise ValueError(f"{name} must have exactly 12 values (monthly). Got {len(arr)}.")

    # -----------------------------
    # Properties: file paths
    # -----------------------------
    @property
    def weather_file(self) -> Path | None:
        """Path to a meteorological data file (TSV, Meteonorm .dat, or PVsyst CSV).

        .. warning::
           TMY (Typical Meteorological Year) data from sources like NSRDB or
           PVGIS contains timestamps from multiple source years. When using TSV
           format, all timestamps must belong to a single contiguous calendar
           year. Remap mixed-year TMY timestamps to one year (e.g., 1990)
           before submission; otherwise the API will return a 400 error.

        See Also
        --------
        EnergyCalculationOptions.calculation_year : Controls year handling
            for Meteonorm and PVsyst TMY formats.
        """
        return self._weather_file

    @weather_file.setter
    def weather_file(self, value: PathLike | None) -> None:
        self._weather_file = None if value is None else Path(value)

    @property
    def horizon_file(self) -> Path | None:
        return self._horizon_file

    @horizon_file.setter
    def horizon_file(self, value: PathLike | None) -> None:
        self._horizon_file = None if value is None else Path(value)

    # -----------------------------
    # Properties: soiling and albedo
    # -----------------------------
    @property
    def soiling_loss(self) -> list[float]:
        """Monthly soiling loss (per unit), 12 values in [0,1]."""
        return list(self._soiling_loss)

    @soiling_loss.setter
    def soiling_loss(self, values: Iterable) -> None:
        """
        Accepts list/tuple/array of 12 values in [0,1] (per unit).
        Example: [0.1, 0.1, ..., 0.1]
        """
        arr = self._to_float_list_1d(values, name="soiling_loss")
        if len(arr) == 1:
            # Expand single value to 12 months
            self._validate_0_1(arr, name="soiling_loss")
            expanded = [arr[0]] * 12
            self._soiling_loss = expanded
            return
        self._ensure_len_12(arr, name="soiling_loss")
        self._validate_0_1(arr, name="soiling_loss")
        self._soiling_loss = arr

    @property
    def albedo(self) -> list[float]:
        """Monthly albedo (per unit), 12 values in [0,1].
        If set with 1 value, it's expanded to 12."""
        return list(self._albedo)

    @albedo.setter
    def albedo(self, values: Iterable) -> None:
        """
        Accepts:
        - single value in [0,1] -> expanded to 12,
        - or list/tuple/array with 12 values in [0,1].
        """
        arr = self._to_float_list_1d(values, name="albedo")
        if len(arr) == 1:
            # Expand single value to 12 months
            self._validate_0_1(arr, name="albedo")
            expanded = [arr[0]] * 12
            self._albedo = expanded
            return

        # Otherwise must be length-12
        self._ensure_len_12(arr, name="albedo")
        self._validate_0_1(arr, name="albedo")
        self._albedo = arr

    # -----------------------------
    # User-facing methods
    # -----------------------------
    def horizon(
        self,
        elevation_angles: Sequence[float] | None = None,
        azimuth_angles: Sequence[float] | None = None,
    ) -> PVSystem:
        """
        Set horizon angles.

        Parameters
        ----------
        elevation_angles : Sequence[float] | None
            Elevation angles (deg). If None, leaves unchanged.
        azimuth_angles : Sequence[float] | None
            Azimuth angles (deg). If None, leaves unchanged.

        Returns
        -------
        self : PVSystem (enables method-chaining)
        """
        if elevation_angles is not None:
            self.horizon_elevation_angles = [float(x) for x in elevation_angles]
        if azimuth_angles is not None:
            self.horizon_azimuth_angles = [float(x) for x in azimuth_angles]
        # Basic length consistency check here; deeper validation can happen in run_calculation
        if elevation_angles is not None or azimuth_angles is not None:
            if len(self.horizon_elevation_angles) != len(self.horizon_azimuth_angles):
                raise ValueError("Horizon arrays must have the same length")
        return self

    @property
    def pan_files(self) -> dict[str, Path]:
        """Mapping of module names to PAN file paths."""
        return dict(self._pan_files)

    @pan_files.setter
    def pan_files(self, mapping: Mapping[str, PathLike]) -> None:
        """Set PAN files, replacing any existing mappings.

        Parameters
        ----------
        mapping : dict[str, str|Path]
            Mapping 'Name of Module' -> file path (string or Path).
            Keys are user-facing labels only. The spec ID sent to the API
            is derived from the filename via ``Path.stem`` (everything
            before the last dot), not from the dict key.
        """
        self._pan_files.clear()
        for name, p in mapping.items():
            key = str(name).strip()
            if not key:
                raise ValueError("Module name cannot be empty")
            self._pan_files[key] = Path(p)

    def add_pan_files(self, mapping: Mapping[str, PathLike]) -> PVSystem:
        """Add PAN files without clearing existing mappings (supports method chaining).

        Parameters
        ----------
        mapping : dict[str, str|Path]
            Mapping 'Name of Module' -> file path (string or Path).

        Returns
        -------
        self : PVSystem
        """
        for name, p in mapping.items():
            key = str(name).strip()
            if not key:
                raise ValueError("Module name cannot be empty")
            self._pan_files[key] = Path(p)
        return self

    @property
    def ond_files(self) -> dict[str, Path]:
        """Mapping of inverter names to OND file paths."""
        return dict(self._ond_files)

    @ond_files.setter
    def ond_files(self, mapping: Mapping[str, PathLike]) -> None:
        """Set OND files, replacing any existing mappings.

        Parameters
        ----------
        mapping : dict[str, str|Path]
            Mapping 'Name of Inverter' -> file path (string or Path).
            Keys are user-facing labels only. The spec ID sent to the API
            is derived from the filename via ``Path.stem`` (everything
            before the last dot), not from the dict key.
        """
        self._ond_files.clear()
        for name, p in mapping.items():
            key = str(name).strip()
            if not key:
                raise ValueError("Inverter name cannot be empty")
            self._ond_files[key] = Path(p)

    def add_ond_files(self, mapping: Mapping[str, PathLike]) -> PVSystem:
        """Add OND files without clearing existing mappings (supports method chaining).

        Parameters
        ----------
        mapping : dict[str, str|Path]
            Mapping 'Name of Inverter' -> file path (string or Path).

        Returns
        -------
        self : PVSystem
        """
        for name, p in mapping.items():
            key = str(name).strip()
            if not key:
                raise ValueError("Inverter name cannot be empty")
            self._ond_files[key] = Path(p)
        return self

    @property
    def pan_file_map(self) -> dict[str, Path]:
        """A (shallow) copy of module -> PAN file mapping."""
        return dict(self._pan_files)

    @property
    def ond_file_map(self) -> dict[str, Path]:
        """A (shallow) copy of inverter -> OND file mapping."""
        return dict(self._ond_files)

    def __post_init__(self) -> None:
        """Post-initialization processing and validation."""

        # Convert string values to enums if necessary
        # (useful when loading JSON via `from_file()`)
        if isinstance(self.mounting, str):
            self.mounting = MountingType(self.mounting)
        if isinstance(self.module_orientation, str):
            self.module_orientation = OrientationType(self.module_orientation)
        if isinstance(self.inverter_type, str):
            self.inverter_type = InverterType(self.inverter_type)

        # Initialize mounting_height based on mounting type if not explicitly set
        if self.mounting == MountingType.FIXED:
            if self.mounting_height is None or not hasattr(self, "mounting_height"):
                self.mounting_height = HEIGHT_FROM_GROUND_FIXED
        elif self.mounting == MountingType.TRACKER:
            if self.mounting_height is None or not hasattr(self, "mounting_height"):
                self.mounting_height = HEIGHT_FROM_GROUND_TRACKER
        else:
            raise ValueError(
                f"Invalid mounting type: '{self.mounting}'. "
                f"Must be one of: {', '.join([e.value for e in MountingType])}"
            )

        # Initialize modules_across with default if not set
        if self.modules_across is None:
            self.modules_across = NUMBER_OF_MODULES_HIGH

        # Validate modules_across
        if not isinstance(self.modules_across, int) or self.modules_across <= 0:
            raise ValueError(
                f"modules_across must be a positive integer, got {self.modules_across}."
            )

        # Initialize and validate inverter_type
        if self.inverter_type is None:
            self.inverter_type = InverterType(
                InverterType.CENTRAL
            )  # Default to 'Central' if not set

        try:
            (
                self.inverter_type.value
                if isinstance(self.inverter_type, InverterType)
                else self.inverter_type
            )
        except (AttributeError, ValueError) as err:
            raise ValueError(
                f"Invalid inverter_type: '{self.inverter_type}'. "
                f"Must be one of: {', '.join([e.value for e in InverterType])}"
            ) from err

        # Initialize dc_ohmic_loss and ac_ohmic_loss based on inverter_type
        if self.dc_ohmic_loss is None:
            self.dc_ohmic_loss = OHMIC_DICT[self.inverter_type.value]["dc"]

        if self.ac_ohmic_loss is None:
            self.ac_ohmic_loss = OHMIC_DICT[self.inverter_type.value]["ac"]

        # Initialize bifacial parameters based on bifacial flag and mounting type
        if self.bifacial:
            bifacial_params = BIFACIAL_DICT[True][self.mounting.value]
        else:
            bifacial_params = BIFACIAL_DICT[False]

        if self.bifacial_transmission is None:
            self.bifacial_transmission = bifacial_params["transmission"]

        if self.bifacial_shade_loss is None:
            self.bifacial_shade_loss = bifacial_params["shade"]

        if self.bifacial_mismatch_loss is None:
            self.bifacial_mismatch_loss = bifacial_params["mismatch"]

        # Initialize and validate transformer_stages
        valid_transformer_stages = {0, 1}
        if self.transformer_stages not in valid_transformer_stages:
            raise ValueError(
                f"Invalid transformer_stages: {self.transformer_stages}. "
                f"Must be one of: {sorted(valid_transformer_stages)}"
            )

        # Map transformer_stages to TRANSFORMER_DICT keys and initialize losses
        transformer_key_map = {0: "Ideal", 1: "FixedType1"}
        transformer_type = transformer_key_map[self.transformer_stages]
        transformer_params = TRANSFORMER_DICT[transformer_type]

        if self.transformer_fixed_loss is None:
            self.transformer_fixed_loss = transformer_params["fixed"]

        if self.transformer_variable_loss is None:
            self.transformer_variable_loss = transformer_params["variable"]

        # Validate location
        if self.latitude is not None and not (-90.0 <= float(self.latitude) <= 90.0):
            raise ValueError("latitude must be within [-90, 90] degrees")
        if self.longitude is not None and not (-180.0 <= float(self.longitude) <= 180.0):
            raise ValueError("longitude must be within [-180, 180] degrees")

        # Validate plant
        if self.ac_capacity_MW <= 0:
            raise ValueError("ac_capacity_MW must be > 0 MW")
        if self.dc_capacity_MW <= 0:
            raise ValueError("dc_capacity_MW must be > 0 MW")

        # Validate horizon
        if self.horizon_elevation_angles is not None and self.horizon_azimuth_angles is not None:
            if len(self.horizon_elevation_angles) != len(self.horizon_azimuth_angles):
                raise ValueError("Horizon arrays must have the same length")
            for v in self.horizon_elevation_angles + self.horizon_azimuth_angles:
                if v is None:
                    raise ValueError("Horizon angles must not contain None")

    def make_copy(self) -> PVSystem:
        """Create a deep copy of the PVSystem instance with results cleared.

        Creates a new PVSystem instance with all fields copied from the current instance.
        The results field is explicitly set to None, and the name is prefixed with "Copy of".
        This ensures a clean state for new calculations and distinguishes the copy.

        Returns
        -------
        PVSystem
            A new PVSystem instance with identical configuration, results = None,
            and name prefixed with "Copy of".

        Examples
        --------
        >>> original_plant = PVSystem(name="Plant1", dc_capacity_MW=5.0)
        >>> original_plant.results = some_calculation_results
        >>> copy_plant = original_plant.make_copy()
        >>> copy_plant.results is None
        True
        >>> copy_plant.name
        'Copy of Plant1'
        """

        # Convert dataclass to dictionary
        plant_dict = asdict(self)

        # Explicitly clear results in the copy
        plant_dict["results"] = None

        # Deep copy mutable fields to avoid shared references
        mutable_fields = [
            "horizon_elevation_angles",
            "horizon_azimuth_angles",
            "_soiling_loss",
            "_albedo",
            "_pan_files",
            "_ond_files",
        ]
        for key in mutable_fields:
            if plant_dict.get(key) is not None:
                plant_dict[key] = copy_module.deepcopy(plant_dict[key])

        # Prefix name with "Copy of"
        original_name = plant_dict.get("name", "Unnamed")
        plant_dict["name"] = f"Copy of {original_name}"

        # Create and return new PVSystem instance
        return PVSystem(**plant_dict)

    def describe(self, verbose=False) -> None:
        """Print a comprehensive summary of all PV plant configuration properties.

        Displays all settings organized by category: metadata, location, capacity,
        array configuration, mounting, inverter/transformer, losses, and files.
        """
        print("\n" + "=" * 70)
        print("PV PLANT SUMMARY")
        print("=" * 70)

        # Basic Metadata
        print("\n--- BASIC METADATA ---")
        print(f"Name: {self.name}")
        print(f"Results Available: {self.results is not None}")

        # Location
        print("\n--- LOCATION ---")
        print(f"Latitude: {self.latitude}°")
        print(f"Longitude: {self.longitude}°")
        print(f"Altitude: {self.altitude} m")
        print(f"Timezone: {self.timezone}")

        # Capacity
        print("\n--- CAPACITY ---")
        print(f"DC Capacity: {self.dc_capacity_MW} MW")
        print(f"AC Capacity: {self.ac_capacity_MW} MW")
        print(f"Grid Limit: {self.grid_limit_MW} MW")

        # Array Configuration
        print("\n--- ARRAY CONFIGURATION ---")
        print(f"GCR (Ground Coverage Ratio): {self.gcr}")
        print(f"Pitch: {self.pitch} m")
        print(f"Tilt: {self.tilt}°")
        print(f"Azimuth: {self.azimuth}°")

        # Mounting & Orientation
        print("\n--- MOUNTING & ORIENTATION ---")
        print(f"Mounting Type: {self.mounting}")
        print(f"Module Orientation: {self.module_orientation}")
        print(f"Modules Across: {self.modules_across}")
        if verbose:
            print(f"Mounting Height: {self.mounting_height} m")
            print(f"Flush Mount: {self.flush_mount}")

        # Bifacial
        print("\n--- BIFACIAL PARAMETERS ---")
        print(f"Bifacial Modules: {self.bifacial}")
        if verbose:
            print(f"  - Transmission Factor: {self.bifacial_transmission}")
            print(f"  - Shade Loss Factor: {self.bifacial_shade_loss}")
            print(f"  - Mismatch Loss Factor: {self.bifacial_mismatch_loss}")

        # Inverter & Transformer
        print("\n--- INVERTER & TRANSFORMER ---")
        print(f"Inverter Type: {self.inverter_type}")
        if verbose:
            print(f"String Length: {self.string_length} modules")
        print(
            f"Transformer Stages: {self.transformer_stages} (0=Ideal/NoLoss, 1=MV/HV transformer)"
        )

        if verbose:
            # Losses
            print("\n--- LOSSES ---")
            print(f"DC Ohmic Loss: {self.dc_ohmic_loss} (per unit)")
            print(f"AC Ohmic Loss: {self.ac_ohmic_loss} (per unit)")
            print(f"Module Mismatch Loss: {self.module_mismatch} (per unit)")
            print(f"Module Quality Factor: {self.module_quality_factor} (per unit)")
            print(f"LID Loss: {self.lid_loss} (per unit)")
            print(f"Transformer Fixed Loss: {self.transformer_fixed_loss} (per unit)")
            print(f"Transformer Variable Loss: {self.transformer_variable_loss} (per unit)")
            print(f"Auxiliary Loss (Fixed Factor): {self.aux_loss_fixed_factor} (per unit)")
            print(f"Auxiliary Loss (Power): {self.aux_loss_power} W")
            print(f"Auxiliary Loss Applied at Night: {self.aux_loss_apply_at_night}")

            # Heat Coefficients
            print("\n--- HEAT TRANSFER COEFFICIENTS ---")
            print(f"Constant Heat Coefficient (Uc): {self.constant_heat_coefficient}")
            print(f"Convective Heat Coefficient (Uv): {self.convective_heat_coefficient}")

            # Monthly Losses
            print("\n--- MONTHLY LOSSES ---")
            print(f"Soiling Loss (monthly): {self.soiling_loss}")
            print(f"Albedo (monthly): {self.albedo}")

            # Horizon
            print("\n--- HORIZON ---")
            print(
                f"Horizon Elevation Angles: {self.horizon_elevation_angles if self.horizon_elevation_angles else 'None'}"
            )
            print(
                f"Horizon Azimuth Angles: {self.horizon_azimuth_angles if self.horizon_azimuth_angles else 'None'}"
            )

            # Modeling Options
            print("\n--- MODELING OPTIONS ---")
            print(f"Enable Spectral Modeling: {self.enable_spectral_modeling}")
            print(f"Module IAM Model Override: {self.module_iam_model_override}")

            # Output Options
            print("\n--- OUTPUT OPTIONS ---")
            print(f"Generate PVsyst Format Timeseries: {self.generate_pvsyst_format_timeseries}")
            print(f"Generate Loss Tree Timeseries: {self.generate_loss_tree_timeseries}")

        # Files
        print("\n--- AUXILIARY FILES ---")
        weather_file_str = str(self.weather_file) if self.weather_file else "Not set"
        horizon_file_str = str(self.horizon_file) if self.horizon_file else "Not set"
        print(f"Weather File: {weather_file_str}")
        print(f"Horizon File: {horizon_file_str}")
        pan_count = len(self._pan_files) if self._pan_files is not None else 0
        ond_count = len(self._ond_files) if self._ond_files is not None else 0
        print(f"Registered PAN Files: {pan_count}")
        if pan_count > 0:
            for name in self._pan_files.keys():
                print(f"  - {name}: {self._pan_files[name]}")
        print(f"Registered OND Files: {ond_count}")
        if ond_count > 0:
            for name in self._ond_files.keys():
                print(f"  - {name}: {self._ond_files[name]}")

        print("\n" + "=" * 70 + "\n")

        return None

    def to_file(self, file_path: PathLike) -> None:
        """Save the PVSystem configuration to a JSON file.

        Parameters
        ----------
        file_path : str | Path
            Path to the output JSON file where the PVSystem configuration will be saved.

        Returns
        -------
        None
            The method saves the configuration to the specified file and does not return anything.

        Notes
        -----
        - The output JSON file will contain all the configuration properties of the PVSystem instance,
          including metadata, location, plant definition, effects, and auxiliary files.
        - The results field is not included in the saved configuration, as it is typically generated
          after running the energy calculation and may contain complex data structures.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist

        # Convert PVSystem to dictionary and exclude results for saving
        plant_dict = asdict(self)
        plant_dict.pop("results", None)  # Remove results from saved config

        # Convert Path objects to strings for JSON compatibility
        for key in ("_weather_file", "_horizon_file"):
            if plant_dict.get(key) is not None:
                plant_dict[key] = str(plant_dict[key])
        for key in ("_pan_files", "_ond_files"):
            if plant_dict.get(key):
                plant_dict[key] = {k: str(v) for k, v in plant_dict[key].items()}

        with path.open("w") as f:
            json.dump(plant_dict, f, indent=4)

        _logger.debug("PVSystem configuration saved to %s", path)
        return None

    @classmethod
    def from_file(cls, file_path: PathLike) -> PVSystem:
        """Load PVSystem configuration from a JSON file and create a PVSystem instance.

        Parameters
        ----------
        file_path : str | Path
            Path to the input JSON file containing the PVSystem configuration.

        Returns
        -------
        PVSystem
            A new PVSystem instance initialized with the configuration loaded from the file.

        Notes
        -----
        - The input JSON file should contain all necessary configuration properties for the PVSystem.
        - The method reads the JSON file, converts it to a dictionary, and then initializes a new PVSystem instance.
        - If the JSON file is missing required fields or contains invalid data, an error may be raised during initialization.
        """
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"No such file: {path}")

        with path.open() as f:
            plant_dict = json.load(f)

        # Reconstruct Path objects from serialized strings
        for key in ("_weather_file", "_horizon_file"):
            if plant_dict.get(key) is not None:
                plant_dict[key] = Path(plant_dict[key])
        for key in ("_pan_files", "_ond_files"):
            if plant_dict.get(key):
                plant_dict[key] = {k: Path(v) for k, v in plant_dict[key].items()}

        # Create PVSystem instance from loaded dictionary
        return cls(**plant_dict)

    def payload_to_file(self, file_path: PathLike) -> None:
        """Save the constructed payload (EnergyCalculationInputs JSON) to a file.

        Parameters
        ----------
        file_path : str | Path
            Path to the output JSON file where the payload will be saved.

        Returns
        -------
        None
            The method saves the payload to the specified file and does not return anything.

        Notes
        -----
        - This method constructs the payload using the current PVSystem configuration and saves it as JSON.
        - The payload is what is sent to the SolarFarmer API for energy calculation.
        - If the payload has already been constructed and stored in self.payload, it will save that instead of reconstructing.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist

        if self.payload is None:
            payload_dict = construct_plant(self)
        else:
            payload_dict = self.payload

        with path.open("w", encoding="utf-8") as f:
            # If payload is a string (JSON), write directly; if dict, use json.dump
            if isinstance(payload_dict, str):
                f.write(payload_dict)
            else:
                json.dump(payload_dict, f, indent=4)

        _logger.debug("PVSystem payload saved to %s", path)
        return None

    def produce_payload(self) -> dict[str, Any]:
        """Construct and return the payload dictionary for the SolarFarmer API based on the current PVSystem configuration.

        Returns
        -------
        dict[str, Any]
            A dictionary representing the payload to be sent to the SolarFarmer API for energy calculation.

        Notes
        -----
        - This method constructs the payload using the current configuration of the PVSystem instance.
        - The payload includes all necessary information about the plant design, location, losses, and other parameters required by the API.
        - If the payload has already been constructed and stored in self.payload, it will return that instead of reconstructing.
        """
        if self.payload is None:
            payload = construct_plant(self)
            self.payload = payload  # Cache the constructed payload for future use
            return payload
        else:
            return self.payload

    def run_energy_calculation(
        self,
        project_id=None,
        print_summary=True,
        outputs_folder_path=None,
        save_outputs=True,
        force_async_call=False,
        api_version="latest",
        **kwargs,
    ) -> CalculationResults | None:
        """
        Runs the SolarFArmer API calculation for the defined PV plant.

        Parameters
        ----------
        project_id : str, optional
            Identifier for the project, used to group related runs and for
            billing.
        print_summary: bool, default=True
            If True, it will print out the summary of the energy calculation results.
        outputs_folder_path: str, optional
            Path to a folder that will contain all the requested outputs from
            the energy calculation. If the path does not exist, it will be
            created. If the path is not provided, an output folder named
            ``sf_outputs_<TIMESTAMP>`` will be created in the same directory
            than ``inputs_folder_path`` or ``energy_calculation_inputs_file_path``.
        save_outputs: bool, default=True
            If True, it will save the results from the API call in the
            ``outputs_folder_path`` or in a newly created folder ``sf_outputs_<TIMESTAMP>``.
        api_version : str, default="latest"
            API version selector. Accepted values:
            - None          : returns `base_url` as-is
            - 'latest'      : uses the 'latest' version path
            - 'vX'          : where X is a positive integer, e.g., 'v6'
        force_async_call : bool, default=False
            If True, forces the use of the asynchronous ModelChain endpoint
            even when the synchronous endpoint could be used.
        **kwargs : dict
            Additional keyword arguments passed to the underlying request
            logic (e.g., ``api_key``, ``time_out``, ``async_poll_time``, or other metadata).

        Returns
        -------
        CalculationResults or None
            The calculation results on success, or None if the async calculation
            was terminated by the user. Results are also stored in ``self.results``.

        Raises
        ------
        SolarFarmerAPIError
            If the API returns a non-2xx response or the async calculation fails.
        """
        from ...endpoint_modelchains import run_energy_calculation

        # Build the JSON payload from the PVSystem configuration
        if self.payload is None:
            builder = construct_plant(self)
        else:
            builder = self.payload

        # Make API call via modelchain function
        results = run_energy_calculation(
            project_id=project_id,
            meteorological_data_file_path=self.weather_file,
            horizon_file_path=self.horizon_file,
            ond_file_paths=list(self.ond_files.values()),
            pan_file_paths=list(self.pan_files.values()),
            print_summary=print_summary,
            outputs_folder_path=outputs_folder_path,
            save_outputs=save_outputs,
            api_version=api_version,
            force_async_call=force_async_call,
            plant_builder=builder,
            **kwargs,
        )

        # Store API results
        self.results = results

        return self.results


def construct_plant(pvplant: PVSystem) -> str:
    """Constructs the PV system JSON payload using data
    in the PVSystem class and other default values.
    Returns a JSON string ready to be sent to the SolarFarmer API.
    """

    # Location
    location = Location(
        longitude=pvplant.longitude, latitude=pvplant.latitude, altitude=pvplant.altitude
    )

    # PV plant
    pv_plant, pan_file_supplements = design_plant(pvplant=pvplant)

    # Energy calculation options
    has_horizon = bool(pvplant.horizon_elevation_angles)
    calculation_options = EnergyCalculationOptions(
        diffuse_model=DiffuseModel.PEREZ,
        include_horizon=has_horizon,
    )
    # update non-default energy calculation options
    calculation_options.return_loss_tree_time_series_results = pvplant.generate_loss_tree_timeseries
    calculation_options.return_pv_syst_format_time_series_results = (
        pvplant.generate_pvsyst_format_timeseries
    )
    calculation_options.apply_spectral_mismatch_modifier = pvplant.enable_spectral_modeling

    # Build the full inputs model
    inputs = EnergyCalculationInputs(
        location=location,
        pv_plant=pv_plant,
        monthly_albedo=MonthlyAlbedo(values=pvplant.albedo),
        energy_calculation_options=calculation_options,
        horizon_azimuths=pvplant.horizon_azimuth_angles or None,
        horizon_angles=pvplant.horizon_elevation_angles or None,
        pan_file_supplements=pan_file_supplements or None,
    )

    # TODO: Integrate OND file supplements into payload construction

    return inputs.model_dump_json(by_alias=True, exclude_none=True)


def design_plant(pvplant: PVSystem) -> tuple[PVPlant, dict[str, PanFileSupplements]]:
    """Design the PV system section of the API SolarFarmer data model."""

    # Estimate inverters (containing layouts) and tranformers based on the PVSystem data and defaults
    (
        inverters,
        are_modules_landscape,
        rack_height,
        y_spacing,
        transformer_rating_MW,
        mounting_type_id,
        tracker_system_id,
        adjusted_dc_capacity_MW,
        adjusted_ac_capacity_MW,
        number_inverters,
        number_modules,
        string_length,
        total_strings,
        pan_file_supplements,
    ) = generate_layout_and_inverters(plant=pvplant)

    transformer = Transformer(
        name=TRANSFORMER_NAME,
        transformer_count=TRANSFORMER_COUNT,
        transformer_spec_id=TRANSFORMER_SPEC_ID,
        inverters=inverters,
    )

    # Produce mounting specifications
    mounting_specs = generate_mounting_specs(
        mounting_type_id=mounting_type_id,
        plant=pvplant,
        are_modules_landscape=are_modules_landscape,
        rack_height=rack_height,
        y_spacing=y_spacing,
    )

    # Produce tracker specifications (dict[str, TrackerSystem] | None)
    tracker_systems = generate_tracker_systems(plant=pvplant, tracker_system_id=tracker_system_id)

    # Produce transformer specifications
    transformer_specs = generate_transformer_specs(
        plant=pvplant, transformer_rating=transformer_rating_MW
    )

    # Produce the auxiliary losses
    auxiliary_losses = AuxiliaryLosses(
        simple_loss_factor=pvplant.aux_loss_fixed_factor,
        apply_simple_loss_factor_at_night=pvplant.aux_loss_apply_at_night,
        simple_loss_power=pvplant.aux_loss_power,
    )
    if not auxiliary_losses.model_dump(exclude_none=True):
        auxiliary_losses = None

    # Assemble PVPlant model
    pv_plant = PVPlant(
        transformers=[transformer],
        grid_connection_limit=pvplant.grid_limit_MW * 1e6,  # Convert MW to W
        mounting_type_specifications=mounting_specs,
        tracker_systems=tracker_systems,
        transformer_specifications=transformer_specs,
        auxiliary_losses=auxiliary_losses,
    )

    pvplant.design_summary = produce_design_summary(
        pvplant,
        adjusted_dc_capacity_MW,
        adjusted_ac_capacity_MW,
        number_inverters,
        number_modules,
        string_length,
        total_strings,
        plot=True,
    )

    # Override the final DC and AC capacity in the plant definition
    # with the adjusted values based on the inverter and layout design
    pvplant.dc_capacity_MW = adjusted_dc_capacity_MW
    pvplant.ac_capacity_MW = adjusted_ac_capacity_MW

    return pv_plant, pan_file_supplements


def generate_layout_and_inverters(
    plant: PVSystem,
) -> tuple[list[Inverter], bool, float, float, float, str, str, float, float, dict[str, Any]]:
    """Generate inverters with layouts based on the PVSystem data and defaults."""

    # Read OND file
    inverter_info = get_inverter_info_from_ond(plant=plant)
    inverter_mppts = get_inverter_mppt(inverter_info)

    # Read PAN file
    pan_info = get_module_info_from_pan(plant=plant)
    pan_info = calculate_module_parameters(pan_info=pan_info)
    bifaciality_factor = get_bifaciality_factor(pan_info=pan_info, plant=plant)

    # Get mounting parameters
    mounting_type_id, tracker_system_id = get_mounting_id(mounting=plant.mounting)
    modules_are_landscape = check_modules_are_landscape(plant=plant)
    rack_height = calculate_rack_height(plant=plant, pan_info=pan_info)
    y_spacing = calculate_y_spacing(plant=plant, pan_info=pan_info)
    pitch = calculate_pitch(plant=plant, rack_height=rack_height)

    # Get component numbers
    number_inverters, adjusted_ac_capacity_MW = calculate_number_of_inverters(
        plant=plant, inverter_info=inverter_info
    )
    number_modules = calculate_number_of_modules(plant=plant, module_info=pan_info)
    string_length = calculate_string_length(
        plant=plant, inverter_info=inverter_info, module_info=pan_info
    )

    # Estimate inverter string configuration
    inverter_string_dict, adjusted_dc_capacity_MW = calculate_inverter_dict(
        number_inverters=number_inverters,
        number_modules=number_modules,
        string_length=string_length,
        module_capacity=float(pan_info["data"]["PNom"]),
    )
    total_strings = sum(
        [
            inverter_string_dict[i]["inverter_count"] * inverter_string_dict[i]["string_length"]
            for i in inverter_string_dict
        ]
    )

    # Set transformer rating based on adjusted AC capacity
    transformer_rating_MW = calculate_transformers(adjusted_ac_capacity=adjusted_ac_capacity_MW)

    # Calculate inverter definitions
    inverters_definition = generate_inverter_objects(
        plant=plant,
        inverter_info=inverter_info,
        inverter_string_dict=inverter_string_dict,
        inverter_mppts=inverter_mppts,
        pan_info=pan_info,
        pitch=pitch,
        mounting_type_id=mounting_type_id,
        tracker_system_id=tracker_system_id,
    )

    # Assemble the PAN file supplements
    pan_file_supplements = generate_pan_file_supplements(
        plant=plant, module_info=pan_info, bifaciality_factor=bifaciality_factor
    )

    return (
        inverters_definition,
        modules_are_landscape,
        rack_height,
        y_spacing,
        transformer_rating_MW,
        mounting_type_id,
        tracker_system_id,
        adjusted_dc_capacity_MW,
        adjusted_ac_capacity_MW,
        number_inverters,
        number_modules,
        string_length,
        total_strings,
        pan_file_supplements,
    )


def generate_inverter_objects(
    plant: PVSystem,
    inverter_info: dict,
    inverter_string_dict: dict[int, dict[str, int]],
    inverter_mppts: int,
    pan_info: dict,
    pitch: float,
    mounting_type_id: str,
    tracker_system_id: str,
) -> list[Inverter]:
    """Generate a list of Inverter objects based on the inverter string dictionary and block range."""
    inverter_block_range = calculate_inverter_block_range(inverter_string_dict=inverter_string_dict)
    inverters = []
    for i in inverter_block_range:
        inverter = Inverter(
            name=f"Inverter_{i}",
            inverter_spec_id=inverter_info["ond_filename"],
            inverter_count=inverter_string_dict[i]["inverter_count"],
            layouts=calculate_layout_objects(
                plant=plant,
                inverter_mppts=inverter_mppts,
                inverter_string_dict=inverter_string_dict,
                inverter_index=i,
                pan_info=pan_info,
                pitch=pitch,
                mounting_type_id=mounting_type_id,
                tracker_system_id=tracker_system_id,
            ),
            ac_wiring_ohmic_loss=plant.ac_ohmic_loss,
        )
        inverters.append(inverter)
    return inverters


def calculate_layout_objects(
    plant: PVSystem,
    inverter_mppts: int,
    inverter_string_dict: dict[int, dict[str, int]],
    inverter_index: int,
    pan_info: dict,
    pitch: float,
    mounting_type_id: str,
    tracker_system_id: str,
) -> list[Layout]:
    """Calculate the layout block range based on the number of MPPTs in the inverter."""
    layout_block_range = list(range(inverter_mppts))
    layouts = []
    for layout_index in layout_block_range:
        number_of_strings = calculate_strings_per_mppt(
            inverter_string_dict=inverter_string_dict,
            inverter_index=inverter_index,
            inverter_mppts=inverter_mppts,
            layout_index=layout_index,
        )

        # Prevent building a block without strings
        if number_of_strings == 0:
            continue

        # For flush mount, the orientation is set to the plane in the layout;
        # the tilt is set to zero in the mounting specification.
        if plant.flush_mount and plant.mounting == MountingType.FIXED:
            terrain_azimuth = plant.azimuth
            terrain_slope = plant.tilt
            number_strings_isolated = number_of_strings
        else:
            terrain_azimuth = TERRAIN_AZIMUTH
            terrain_slope = TERRAIN_SLOPE
            number_strings_isolated = STRINGS_IN_ISOLATED_ROW

        layout = Layout(
            name="layout_1",
            layout_count=1,
            inverter_input=[layout_index],
            module_specification_id=pan_info["pan_filename"],
            mounting_type_id=mounting_type_id,
            tracker_system_id=tracker_system_id,
            is_trackers=plant.mounting == MountingType.TRACKER,
            azimuth=plant.azimuth,
            pitch=pitch,
            total_number_of_strings=number_of_strings,
            string_length=inverter_string_dict[inverter_index]["string_length"],
            number_of_strings_in_front_row=STRINGS_IN_FRONT_ROW,
            number_of_strings_in_back_row=STRINGS_IN_BACK_ROW,
            number_of_strings_in_right_row=STRINGS_IN_RIGHT_ROW,
            number_of_strings_in_left_row=STRINGS_IN_LEFT_ROW,
            number_of_strings_in_isolated_row=number_strings_isolated,
            dc_ohmic_connector_loss=plant.dc_ohmic_loss,
            module_mismatch_loss=plant.module_mismatch,
            terrain_azimuth=terrain_azimuth,
            terrain_slope=terrain_slope,
            module_quality_factor=plant.module_quality_factor,
        )

        layouts.append(layout)

    return layouts


def generate_mounting_specs(
    mounting_type_id: str,
    plant: PVSystem,
    are_modules_landscape: bool,
    rack_height: float,
    y_spacing: float,
) -> dict[str, MountingTypeSpecification]:
    """Generate mounting type specifications for tracker or fixed-tilt systems.
    Creates MountingTypeSpecification instances with all parameters available
    for customization. Parameters can be set after instantiation as needed."""

    is_tracker = plant.mounting == MountingType.TRACKER

    # Create mounting specification
    if is_tracker:
        # For trackers case
        mounting_spec = MountingTypeSpecification(
            is_tracker=is_tracker,
            number_of_modules_high=plant.modules_across,
            modules_are_landscape=are_modules_landscape,
            rack_height=rack_height,
            y_spacing_between_modules=y_spacing,
            frame_bottom_width=FRAME_BOTTOM_WIDTH,
            constant_heat_transfer_coefficient=plant.constant_heat_coefficient,
            convective_heat_transfer_coefficient=plant.convective_heat_coefficient,
            number_of_modules_long=None,
            x_spacing_between_modules=None,
            frame_top_width=None,
            frame_end_width=None,
            monthly_soiling_loss=plant.soiling_loss,
            tilt=None,
            height_of_lowest_edge_from_ground=None,
            height_of_tracker_center_from_ground=plant.mounting_height,
            transmission_factor=plant.bifacial_transmission,
            bifacial_shade_loss_factor=plant.bifacial_shade_loss,
            bifacial_mismatch_loss_factor=plant.bifacial_mismatch_loss,
        )
    else:
        # For flush mount, the tilt is set to zero,
        # the orientation is set to the plane in the layout
        if plant.flush_mount:
            height_from_ground = 0.1  # A small height of 10 cm
            tilt_angle = 0.0
        else:
            height_from_ground = plant.mounting_height
            tilt_angle = plant.tilt if plant.tilt is not None else round(plant.latitude)

        # Fixed-tilt case
        mounting_spec = MountingTypeSpecification(
            is_tracker=is_tracker,
            number_of_modules_high=plant.modules_across,
            modules_are_landscape=are_modules_landscape,
            rack_height=rack_height,
            y_spacing_between_modules=y_spacing,
            frame_bottom_width=FRAME_BOTTOM_WIDTH,
            constant_heat_transfer_coefficient=plant.constant_heat_coefficient,
            convective_heat_transfer_coefficient=plant.convective_heat_coefficient,
            number_of_modules_long=None,
            x_spacing_between_modules=None,
            frame_top_width=None,
            frame_end_width=None,
            monthly_soiling_loss=plant.soiling_loss,
            tilt=tilt_angle,
            height_of_lowest_edge_from_ground=height_from_ground,
            height_of_tracker_center_from_ground=None,
            transmission_factor=plant.bifacial_transmission,
            bifacial_shade_loss_factor=plant.bifacial_shade_loss,
            bifacial_mismatch_loss_factor=plant.bifacial_mismatch_loss,
        )

    return {mounting_type_id: mounting_spec}


def generate_tracker_systems(
    plant: PVSystem, tracker_system_id: str | None = None
) -> dict[str, TrackerSystem] | None:
    """Generate tracker system specifications.
    Creates TrackerSystem instances with all parameters available
    for customization. Parameters can be set after instantiation as needed."""

    is_tracker = plant.mounting == MountingType.TRACKER

    if is_tracker:
        tracker_system = TrackerSystem(
            system_plane_azimuth=0.0,
            system_plane_tilt=0.0,
            tracker_azimuth=plant.azimuth,
            east_west_gcr=plant.gcr,
            rotation_min_deg=-plant.tilt if plant.tilt is not None else -60.0,
            rotation_max_deg=plant.tilt if plant.tilt is not None else 60.0,
            is_backtracking=IS_BACKTRACKING,
            use_slope_aware_backtracking=False,
        )
        key = tracker_system_id if tracker_system_id is not None else "Layout Region 1"
        return {key: tracker_system}
    else:
        return None


def generate_transformer_specs(
    plant: PVSystem, transformer_rating: float
) -> dict[str, TransformerSpecification]:
    """Generate transformer specifications based on PVSystem data.
    Creates TransformerSpecification instances with all parameters available
    for customization. Parameters can be set after instantiation as needed."""
    transformer_specs = {}
    transformer_specs[TRANSFORMER_SPEC_ID] = TransformerSpecification(
        model_type=TransformerLossModelTypes.NO_LOAD_AND_OHMIC,
        rated_power=transformer_rating * 1e6,  # Convert MW to W
        no_load_loss=plant.transformer_fixed_loss * transformer_rating * 1e6,
        full_load_ohmic_loss=plant.transformer_variable_loss * transformer_rating * 1e6,
    )

    return transformer_specs


def generate_pan_file_supplements(
    plant: PVSystem, module_info: dict, bifaciality_factor: float
) -> dict[str, Any]:
    """Generate PAN file supplements based on the PVSystem data and module information."""
    # LID loss value is taken from the PAN file if available, otherwise from the PVSystem default
    try:
        lid_loss = float(module_info["data"]["LIDLoss"]) / 100  # Convert percentage to per unit
    except KeyError:
        lid_loss = plant.lid_loss

    pan_file_supplements = {}
    pan_file_supplements[module_info["pan_filename"]] = PanFileSupplements(
        module_quality_factor=plant.module_quality_factor,
        lid_loss=lid_loss,
        bifaciality_factor=bifaciality_factor,
        iam_model_type_override=plant.module_iam_model_override,
    )

    return pan_file_supplements


# ------------------------------------------------------------------------------
# Helpers to calculate data for the SolarFarmer API data model
# ------------------------------------------------------------------------------


def get_mounting_id(mounting: MountingType) -> tuple[str, str]:
    """Checks if the system is fixed or tracking. Returns mounting ID."""
    # Get values from PV plant object dictionary.
    if mounting == MountingType.FIXED:
        mounting_type_id = "Fixed-Tilt Rack Template 1"
        tracker_system_id = None
    elif mounting == MountingType.TRACKER:
        mounting_type_id = "Tracker Template Specification 1"
        tracker_system_id = "Layout Region 1"
    return mounting_type_id, tracker_system_id


def check_modules_are_landscape(plant: PVSystem) -> bool:
    """Checks if the modules are landscape or portrait. Returns boolean."""
    if plant.module_orientation == OrientationType.LANDSCAPE:
        return True
    else:
        return False


def calculate_rack_height(plant: PVSystem, pan_info: dict) -> float:
    """Calculates the height of the rack in the slanted direction."""

    # Get values from PV plant object and pan info.
    module_configuration = plant.module_orientation
    number_of_modules_high = plant.modules_across
    module_width = float(pan_info["data"]["Width"])
    module_height = float(pan_info["data"]["Height"])
    y_gap = Y_GAP

    if module_configuration == OrientationType.LANDSCAPE:
        rack_height = number_of_modules_high * module_width + (number_of_modules_high - 1) * y_gap
    elif module_configuration == OrientationType.PORTRAIT:
        rack_height = number_of_modules_high * module_height + (number_of_modules_high - 1) * y_gap
    return rack_height


def calculate_strings_per_mppt(
    inverter_string_dict: dict[int, dict[str, int]],
    inverter_index: int,
    inverter_mppts: int,
    layout_index: int,
) -> int:
    """Calculates the number of strings for each MPPT based on the total number of strings"""

    number_of_strings = inverter_string_dict[inverter_index]["number_of_strings"]
    number_of_mppts = inverter_mppts

    # Calculate number of strings for each mppt
    min_strings = number_of_strings // number_of_mppts
    rem_strings = number_of_strings % number_of_mppts
    max_strings = min_strings + 1
    if layout_index < rem_strings:
        number_of_strings = max_strings
    else:
        number_of_strings = min_strings
    return number_of_strings


def calculate_y_spacing(plant: PVSystem, pan_info: dict) -> float:
    """Calculates the y-spacing of the modules in the rack."""

    # Get values from PV plant object and pan info.
    module_configuration = plant.module_orientation
    number_of_modules_high = plant.modules_across
    module_width = float(pan_info["data"]["Width"])
    module_height = float(pan_info["data"]["Height"])
    y_gap = Y_GAP

    if number_of_modules_high == 1:
        y_spacing = 0
    elif number_of_modules_high > 1:
        if module_configuration == OrientationType.LANDSCAPE:
            y_spacing = module_width + y_gap
        elif module_configuration == OrientationType.PORTRAIT:
            y_spacing = module_height + y_gap
    return y_spacing


def calculate_pitch(plant: PVSystem, rack_height: float) -> float:
    """Calculates pitch and GCR based on provided inputs.

    Three scenarios are handled:
    1. Only GCR is provided (pitch is None): Calculate pitch from GCR
    2. Only pitch is provided: Calculate and update GCR from pitch
    3. Both are provided: Pitch takes priority; GCR is recalculated from pitch

    The relationship between pitch, GCR, and rack_height is:
    pitch = rack_height / gcr, or equivalently, gcr = rack_height / pitch

    Parameters
    ----------
    plant : PVSystem
        PV plant object containing gcr and pitch attributes
    rack_height : float
        Height of the rack in the slanted direction

    Returns
    -------
    float
        Calculated or provided pitch value
    """
    gcr = plant.gcr
    pitch = plant.pitch

    if pitch is not None:
        # Pitch is explicitly provided, use it and recalculate GCR
        plant.gcr = rack_height / pitch
        return pitch
    else:
        # Pitch not provided, calculate it from GCR
        pitch = rack_height / gcr
        return pitch


def calculate_number_of_inverters(plant: PVSystem, inverter_info: dict) -> tuple[int, float]:
    """Calculates the number of inverters based on system and inverter AC
    capacity. Number of inverters is rounded up. Assume one inverter if the AC
    capacity is smaller than the inverter capacity.
    """
    # Get values from project dictionary.
    ac_capacity = plant.ac_capacity_MW * 1e6  # convert MW to W
    inverter_capacity = float(inverter_info["data"]["PMaxOUT"]) * 1e3  # convert kW to W

    # Calculate number of inverters
    if ac_capacity < inverter_capacity:
        number_of_inverters = 1
    elif ac_capacity >= inverter_capacity:
        # Check if ac_capacity is multiple of inverter_capacity, else round up.
        if (ac_capacity % inverter_capacity) == 0:
            number_of_inverters = ac_capacity // inverter_capacity
        elif (ac_capacity % inverter_capacity) != 0:
            number_of_inverters = ac_capacity // inverter_capacity + 1

    # Calculate simulated AC capacity based on number of inverters.
    adjusted_ac_capacity_MW = inverter_capacity * number_of_inverters / 1e6  # convert W back to MW
    return number_of_inverters, adjusted_ac_capacity_MW


def calculate_number_of_modules(plant: PVSystem, module_info: dict) -> int:
    """Calculates the number of modules based on system and module DC capacity.
    Number of modules is rounded down.
    """
    # Get values from project dictionary.
    dc_capacity = float(plant.dc_capacity_MW) * 1e6  # convert MW to W
    module_capacity = float(module_info["data"]["PNom"])  # already in W
    # Calculate number of modules
    number_of_modules = dc_capacity // module_capacity
    return number_of_modules


def calculate_string_length(plant: PVSystem, inverter_info: dict, module_info: dict) -> int:
    """If string length is not defined, returns the maximum number of modules
    per string based on module Voc and inverter VMPPmax.
    """
    # Get values from project dictionary.
    inverter_vmpp = float(inverter_info["data"]["VMPPMax"])
    module_voc_at_min_temp = float(module_info["module_voc_at_min_temp"])
    string_length = plant.string_length
    # Calculate string length
    max_string_length = int(inverter_vmpp // module_voc_at_min_temp)
    # Check if string length is within bounds.
    if string_length is None:
        string_length = max_string_length
    elif string_length > max_string_length:
        string_length = max_string_length
    return string_length


def calculate_inverter_dict(
    number_inverters: int, number_modules: int, string_length: int, module_capacity: float
) -> dict[int, dict[str, int]]:
    """Calculates the number of strings per inverter. Strings are balanced
    across two inverter blocks.
    """
    # Validate input
    if number_inverters < 2:
        raise ValueError("There needs to be at least 2 inverters in a simulation")

    # Calculate number of strings from number of modules and string length
    number_of_strings = int(number_modules // string_length)
    # Calculate number of inverters in block 1 using modulo operator.
    # Remainder goes to block 2
    inverter_1_count = int(number_of_strings % number_inverters)
    inverter_2_count = int(number_inverters - inverter_1_count)
    # Calculate number of strings per inverter from number of strings
    # and number of inverters
    inverter_2_strings = int(number_of_strings // number_inverters)
    inverter_1_strings = int(inverter_2_strings + 1)

    # Recalculate dc capacity based on simulation model.
    adjusted_dc_capacity_MW = module_capacity * string_length * number_of_strings / 1e6

    # Store inverter parameters in a dictionary.
    inverter_dict = {
        1: {
            "inverter_count": inverter_1_count,
            "number_of_strings": inverter_1_strings,
            "string_length": string_length,
        },
        2: {
            "inverter_count": inverter_2_count,
            "number_of_strings": inverter_2_strings,
            "string_length": string_length,
        },
    }

    return inverter_dict, adjusted_dc_capacity_MW


def calculate_transformers(adjusted_ac_capacity: float) -> float:
    """Calculate transformer rating and loss factors."""
    # For simplicity, we use a single transformer with a rating equal to the adjusted AC
    return adjusted_ac_capacity


def get_bifaciality_factor(pan_info: dict, plant: PVSystem) -> float:
    # Function
    if plant.bifacial:
        try:
            bifaciality_factor = float(pan_info["data"]["BifacialityFactor"])
        except KeyError:
            bifaciality_factor = 0
    else:
        bifaciality_factor = 0
    return bifaciality_factor


def get_inverter_info_from_ond(plant: PVSystem) -> dict[str, Any]:
    """Read OND files and extract inverter information."""

    inverter_info = {}

    for inverter_name, ond_file_path in plant.ond_file_map.items():
        # Extract directory and filename from the Path object
        components_dir = str(ond_file_path.parent)
        ond_filename = ond_file_path.name

        # Read the OND file
        ond_dict = read_ond_file(ond_filename, components_dir)

        # Store the data indexed by inverter name
        inverter_info[inverter_name] = {
            "name": inverter_name,
            "ond_filename": Path(ond_filename).stem,  # Use filename without extension as spec ID
            "path": ond_file_path,
            "data": ond_dict,
        }

    # Currently only interested in a single inverter, so return the first one found.
    # Future extensions could handle multiple inverters for the PV plant creation.
    return next(iter(inverter_info.values()))


def get_module_info_from_pan(plant: PVSystem) -> dict[str, Any]:
    """Read PAN files and extract module information."""

    module_info = {}

    for module_name, pan_file_path in plant.pan_file_map.items():
        # Extract directory and filename from the Path object
        components_dir = str(pan_file_path.parent)
        pan_filename = pan_file_path.name

        # Read the PAN file
        pan_dict = read_pan_file(pan_filename, components_dir)

        # Store the data indexed by module name
        module_info[module_name] = {
            "name": module_name,
            "path": pan_file_path,
            "pan_filename": Path(pan_filename).stem,  # Use filename without extension as spec ID
            "data": pan_dict,
        }

    # Currently only interested in a single module, so return the first one found.
    # Future extensions could handle multiple modules for the PV plant creation.
    return next(iter(module_info.values()))


def calculate_inverter_block_range(inverter_string_dict: dict[int, int]) -> list[int]:
    """Calculate the inverter block range based on the number of inverters per
    inverter case. It will generally be either 1 or 2 blocks depending on
    whether there are inverters in both blocks."""
    block_range = []
    for i in range(1, len(inverter_string_dict) + 1):
        if inverter_string_dict[i]["inverter_count"] != 0:
            block_range.append(i)
    return block_range


def produce_design_summary(
    plant: PVSystem,
    adjusted_dc_capacity_MW: float,
    adjusted_ac_capacity_MW: float,
    number_inverters: int,
    number_modules: int,
    string_length: int,
    total_strings: int,
    plot: bool = False,
) -> dict[str, Any]:
    """Produce a summary of the plant design based on the PVSystem configuration and the resulting layout and inverter design.

    Parameters
    ----------
    plant : PVSystem
        The PV system configuration.
    adjusted_dc_capacity_MW : float
        Design/simulated DC capacity in MW.
    adjusted_ac_capacity_MW : float
        Design/simulated AC capacity in MW.
    number_inverters : int
        Number of inverters in the design.
    number_modules : int
        Total number of modules in the design.
    string_length : int
        Number of modules per string.
    total_strings : int
        Total number of strings in the design.
    plot : bool, default=False
        If True, prints the design summary information.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing the design summary with target and design values.
    """
    design_summary = {
        "target_dc_capacity_MW": plant.dc_capacity_MW,
        "target_ac_capacity_MW": plant.ac_capacity_MW,
        "design_dc_capacity_MW": adjusted_dc_capacity_MW,
        "design_ac_capacity_MW": adjusted_ac_capacity_MW,
        "number_inverters": number_inverters,
        "number_modules": number_modules,
        "string_length": string_length,
        "total_strings": total_strings,
    }

    if plot:
        print("\n" + "=" * 45)
        print("DESIGN SUMMARY")
        print("=" * 45)
        print("\nCapacity Summary:")
        print(f"  Target (input) DC Capacity: {plant.dc_capacity_MW} MW")
        print(f"  Design (output for simulation) DC Capacity: {adjusted_dc_capacity_MW:.3f} MW")
        print(f"  Target (input) AC Capacity: {plant.ac_capacity_MW} MW")
        print(f"  Design (output for simulation) AC Capacity: {adjusted_ac_capacity_MW:.3f} MW")
        print("\nLayout Configuration:")
        print(f"  Number of Inverters: {int(number_inverters)}")
        print(f"  Number of Modules: {int(number_modules)}")
        print(f"  String Length: {int(string_length)}")
        print(f"  Total Strings: {int(total_strings)}")
        print("=" * 45 + "\n")

    return design_summary
