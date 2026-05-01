from __future__ import annotations

import calendar
import io
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

from tabulate import tabulate

from ..config import (
    ANNUAL_MONTHLY_RESULTS_FILENAME,
    CALCULATION_ATTRIBUTES_FILENAME,
    DETAILED_TIMESERIES_FILENAME,
    LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME,
    LOSS_TREE_TIMESERIES_FILENAME,
    PANDAS_INSTALL_MSG,
    PVSYST_TIMESERIES_DATAFRAME_FILENAME,
    PVSYST_TIMESERIES_FILENAME,
)
from ..endpoint_modelchains_utils import path_exists
from ..logging import get_logger
from .model_chain_response import ModelChainResponse

_logger = get_logger("models.results")

try:
    import pandas as pd

    _PANDAS = True
except ImportError:
    _PANDAS = False

# Constants for accessing the results data
ANNUAL_ENERGY_YIELD_RESULTS_KEY = "energyYieldResults"
ANNUAL_EFFECTS_KEY = "annualEffects"
MONTHLY_ENERGY_YIELD_RESULTS_KEY = "monthlyEnergyYieldResults"
MONTHLY_EFFECTS_KEY = "monthlyEffects"

ANNUAL_RECORD_COUNT = "recordCount"
ANNUAL_PERCENT_COMPLETE = "percentComplete"
ANNUAL_AVERAGE_TEMPERATURE = "averageTemperature"
ANNUAL_GHI = "ghi"
ANNUAL_GI = "gi"
ANNUAL_GI_WITH_HORIZON = "giWithHorizon"
ANNUAL_GAIN_ON_TILTED_PLANE = "gainOnTiltedPlane"
ANNUAL_GLOBAL_EFFECTIVE_IRRADIANCE = "globalEffectiveIrradiance"
ANNUAL_MODULE_POWER = "modulePower"
ANNUAL_MODULE_POWER_AT_STC = "modulePowerAtSTC"
ANNUAL_NOMINAL_ENERGY = "nominalEnergy"
ANNUAL_PDC = "pdc"
ANNUAL_PAC = "pac"
ANNUAL_PERFORMANCE_RATIO = "performanceRatio"
ANNUAL_PERFORMANCE_RATIO_BIFACIAL = "performanceRatioBifacial"
ANNUAL_NET_ENERGY = "netEnergy"
ANNUAL_ENERGY_YIELD = "energyYield"

EFFECT_HORIZON = "horizon"
EFFECT_NEAR_SHADING_IRRADIANCE = "nearShadingIrradiance"
EFFECT_SOILING = "soiling"
EFFECT_ANGULAR = "angular"
EFFECT_SPECTRAL = "spectral"
EFFECT_BACK_IRRADIANCE_GAIN = "backIrradianceGain"
EFFECT_BIFACIAL_ANGULAR = "bifacialAngular"
EFFECT_BIFACIAL_SHADING = "bifacialShading"
EFFECT_BIFACIAL_TRANSMISSION = "bifacialTransmission"
EFFECT_BACK_NEAR_SHADING_IRRADIANCE = "backNearShadingIrradiance"
EFFECT_MODELING = "modeling"
EFFECT_MODELING_CORRECTION = "modelingCorrection"
EFFECT_TEMPERATURE = "temperature"
EFFECT_IRRADIANCE = "irradiance"
EFFECT_BIFACIALITY_FACTOR = "bifacialityFactor"
EFFECT_BACK_IRRADIANCE_MISMATCH = "backIrradianceMismatch"
EFFECT_POWER_BINNING = "powerBinning"
EFFECT_LIGHT_INDUCED_DEGRADATION = "lightInducedDegradation"
EFFECT_MODULE_QUALITY = "moduleQuality"
EFFECT_MODULE_MISMATCH = "moduleMismatch"
EFFECT_OPTIMIZERS_OPERATIONAL_INPUT_LIMITS = "optimizersOperationalInputLimits"
EFFECT_OPTIMIZERS_EFFICIENCY = "optimizersEfficiency"
EFFECT_OPTIMIZERS_OPERATIONAL_OUTPUT_LIMITS = "optimizersOperationalOutputLimits"
EFFECT_ELECTRICAL_MISMATCH = "electricalMismatch"
EFFECT_OHMIC_DC = "ohmicDc"
EFFECT_INVERTER_MIN_DC_VOLTAGE = "inverterMinDcVoltage"
EFFECT_INVERTER_MAX_DC_CURRENT = "inverterMaxDcCurrent"
EFFECT_INVERTER_MAX_DC_VOLTAGE = "inverterMaxDcVoltage"
EFFECT_INVERTER_MIN_DC_POWER = "inverterMinDcPower"
EFFECT_INVERTER_EFFICIENCY = "inverterEfficiency"
EFFECT_INVERTER_MAX_AC_POWER = "inverterMaxAcPower"
EFFECT_INVERTER_OVER_POWER_SHUTDOWN = "inverterOverPowerShutdown"
EFFECT_INVERTER_TARE = "inverterTare"
EFFECT_AUXILIARIES = "auxiliaries"
EFFECT_OHMIC_AC = "ohmicAc"
EFFECT_TRANSFORMER = "transformer"
EFFECT_SYSTEM_AVAILABILITY = "systemAvailability"
EFFECT_GRID_LIMIT = "gridLimit"
EFFECT_GRID_AVAILABILITY = "gridAvailability"


@dataclass
class CalculationResults:
    """
    Container for ModelChain and ModelChainAsync API results.

    Attributes
    ----------
    ModelChainResponse : ModelChainResponse
        The API ModelChainResponse object
    AnnualData : dictionary
        Annual energy yield performance and effects.
    MonthlyData : dictionary
        Monthly energy yield performance and effects.
    CalculationAttributes : dictionary
        Several system attributes and metadata from the energy calculation.
    LossTreeTimeseries : pd.DataFrame or None
        The loss tree timeseries results. Aggregated energy values (kWh)
        for the whole site in each timestamp using the modeling
        chain of the SolarFarmer performance model.
    PVsystTimeseries : pd.DataFrame or None
        The PVsyst-style timeseries results. For the whole site in each timestamp
        of the energy calculation.
    DetailedTimeseries : pd.DataFrame or None
        The detailed timeseries results. Additional data from the modeling chain of
        SolarFarmer performance model. Useful for debugging.
    Name: str or None
        Name of project. It is populated with the ``project_id`` property if availabe.

    Examples
    --------
    Retrieve key performance metrics for the first project year:

    >>> perf = results.get_performance(project_year=1)
    >>> print(f"Net energy:         {perf['net_energy']:.2f} MWh/year")
    >>> print(f"Performance ratio:  {perf['performance_ratio']:.3f}")
    >>> print(f"Specific yield:     {perf['energy_yield']:.1f} kWh/kWp")

    Print a summary table:

    >>> results.describe()

    Access monthly or annual DataFrames:

    >>> annual_df  = results.get_annual_results_table()
    >>> monthly_df = results.get_monthly_results_table()
    """

    ModelChainResponse: ModelChainResponse
    AnnualData: list[dict[str, Any]]
    MonthlyData: list[dict[str, Any]]
    CalculationAttributes: dict[str, Any]
    LossTreeTimeseries: pd.DataFrame | None = None
    PVsystTimeseries: pd.DataFrame | None = None
    DetailedTimeseries: pd.DataFrame | None = None
    Name: str | None = None

    # ----- Convenience properties for common metrics (year 1) -----

    @property
    def net_energy_MWh(self) -> float:
        """Net energy production for year 1 in MWh/year."""
        return self.get_performance(project_year=1).get("net_energy", float("nan"))

    @property
    def performance_ratio(self) -> float:
        """Performance ratio for year 1 (0–1)."""
        return self.get_performance(project_year=1).get("performance_ratio", float("nan"))

    @property
    def energy_yield_kWh_per_kWp(self) -> float:
        """Specific energy yield for year 1 in kWh/kWp."""
        return self.get_performance(project_year=1).get("energy_yield", float("nan"))

    def __repr__(self) -> str:
        """Return a concise string representation of the CalculationResults."""
        num_years = len(self.AnnualData) if self.AnnualData else 0
        return f"CalculationResults(name={self.Name!r}, years={num_years})"

    @classmethod
    def from_modelchain_response(
        cls,
        modelchain_response: ModelChainResponse,
        outputs_folder_path: str,
        save_outputs: bool,
        print_summary: bool,
    ) -> CalculationResults:
        """
        Build a CalculationResults instance from a ModelChainResponse.

        Parameters
        ----------
        modelchain_response : ModelChainResponse
            The ModelChainResponse object from the API call.
        outputs_folder_path: str
            The path of the output folder, where the results will be written.
        save_outputs: bool
            If True, it will save the results from the API call in the
            'outputs_folder_path'.
        print_summary: bool
            If True, it will print out the summary of the energy calculation results.

        Returns
        -------
        CalculationResults
            Populated results container in ready-to-use formats.
        """

        # Handle and deal with the different properties of the ModelChainResults
        annual_data, monthly_data = _handle_annual_energy_yield_results(
            modelchain_response, outputs_folder_path, save_outputs
        )

        calculation_attributes = _handle_system_attributes(
            modelchain_response, outputs_folder_path, save_outputs
        )

        losstree_timeseries = _handle_losstree_results(
            modelchain_response, outputs_folder_path, save_outputs
        )

        pvsyst_timeseries = _handle_pvsyst_results(
            modelchain_response, outputs_folder_path, save_outputs
        )

        detailed_timeseries = _handle_timeseries_results(
            modelchain_response, outputs_folder_path, save_outputs
        )

        calculation_results = cls(
            ModelChainResponse=modelchain_response,
            AnnualData=annual_data,
            MonthlyData=monthly_data,
            CalculationAttributes=calculation_attributes,
            LossTreeTimeseries=losstree_timeseries,
            PVsystTimeseries=pvsyst_timeseries,
            DetailedTimeseries=detailed_timeseries,
            Name=modelchain_response.Name,
        )

        if print_summary:
            calculation_results.describe()

        return calculation_results

    @classmethod
    def from_folder(cls, output_folder_path: str) -> CalculationResults:
        """
        Load CalculationResults from JSON files in a directory.

        Reads API energy calculation results from multiple JSON files
        in the specified output directory.

        Parameters
        ----------
        output_folder_path : str
            The path of the output folder, where the results will be read from.

        Returns
        -------
        CalculationResults
            Populated results container in ready-to-use formats
            (e.g, DataFrames and dictionaries).

        """
        output_folder_path = Path(output_folder_path)

        if path_exists(output_folder_path) is False:
            raise FileNotFoundError(f"The folder {output_folder_path} does not exist.")

        _logger.debug("Importing SolarFarmer result files from %s", output_folder_path)

        # Annual and Monthly data
        annual_monthly_file_path = output_folder_path / ANNUAL_MONTHLY_RESULTS_FILENAME
        if path_exists(annual_monthly_file_path) is False:
            raise FileNotFoundError(f"The file {annual_monthly_file_path} could not be found.")
        else:
            # Open and read the JSON file
            with annual_monthly_file_path.open() as file:
                annual_monthly_data = json.load(file)

            annual_data, monthly_data = _separate_annual_monthly_data(annual_monthly_data)
            _logger.debug("%s was imported successfully.", ANNUAL_MONTHLY_RESULTS_FILENAME)

        # System attributes
        system_attributes_file_path = output_folder_path / CALCULATION_ATTRIBUTES_FILENAME
        if path_exists(system_attributes_file_path) is False:
            raise FileNotFoundError(f"The file {system_attributes_file_path} could not be found.")

        else:
            # Open and read the JSON file
            with system_attributes_file_path.open() as file:
                calculation_attributes = json.load(file)

            _logger.debug("%s was imported successfully.", CALCULATION_ATTRIBUTES_FILENAME)

        # Loss tree timeseries
        if path_exists(output_folder_path / LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME):
            loss_tree_file_path = output_folder_path / LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME
            losstree_timeseries = _read_dataframe_pandas_safe(
                loss_tree_file_path, "\t", LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME
            )
        else:
            loss_tree_file_path = output_folder_path / LOSS_TREE_TIMESERIES_FILENAME
            losstree_timeseries = _read_dataframe_pandas_safe(
                loss_tree_file_path, "\t", LOSS_TREE_TIMESERIES_FILENAME, skip_rows=[0, 1]
            )

        # PVsyst timeseries
        if path_exists(output_folder_path / PVSYST_TIMESERIES_DATAFRAME_FILENAME):
            pvsyst_file_path = output_folder_path / PVSYST_TIMESERIES_DATAFRAME_FILENAME
            pvsyst_timeseries = _read_dataframe_pandas_safe(
                pvsyst_file_path, ";", PVSYST_TIMESERIES_DATAFRAME_FILENAME
            )
        else:
            pvsyst_file_path = output_folder_path / PVSYST_TIMESERIES_FILENAME
            pvsyst_timeseries = _read_dataframe_pandas_safe(
                pvsyst_file_path,
                ";",
                PVSYST_TIMESERIES_FILENAME,
                skip_rows=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12],
            )

        # Detailed timeseries
        detailed_timeseries_file_path = output_folder_path / DETAILED_TIMESERIES_FILENAME
        detailed_timeseries = _read_dataframe_pandas_safe(
            detailed_timeseries_file_path, "\t", DETAILED_TIMESERIES_FILENAME
        )

        return cls(
            ModelChainResponse=None,
            AnnualData=annual_data,
            MonthlyData=monthly_data,
            CalculationAttributes=calculation_attributes,
            LossTreeTimeseries=losstree_timeseries,
            PVsystTimeseries=pvsyst_timeseries,
            DetailedTimeseries=detailed_timeseries,
            Name=None,
        )

    def to_folder(self, output_folder_path: str) -> None:
        """
        Write energy calculation results to files in a directory.

        Writes the energy calculation results to multiple files
        (*.json, *.csv, *.tsv) in the specified output directory.

        Parameters
        ----------
        output_folder_path : str
            The path of the output folder, where the results will be written.
        """

        output_folder_path = Path(output_folder_path)
        response_exists = self.ModelChainResponse is not None

        # Annual and monthly data
        if response_exists:
            annual_results_list = self.ModelChainResponse.AnnualEnergyYieldResults
        else:
            # Form the annual and monthly results from the AnnualData and MonthlyData properties
            annual_results_list = []
            for item1, item2 in zip(self.AnnualData, self.MonthlyData, strict=False):
                annual_results_list.append(
                    {
                        "year": item1.get("year"),
                        "annualEffects": item1.get("annualEffects"),
                        "energyYieldResults": item1.get("energyYieldResults"),
                        "monthlyEnergyYieldResults": item2.get("monthlyEnergyYieldResults"),
                    }
                )

        if annual_results_list is not None:
            # Save the json results to file
            _save_content(
                annual_results_list,
                output_folder_path / ANNUAL_MONTHLY_RESULTS_FILENAME,
                json_indent=2,
                type_file="annual energy yield results",
            )
        else:
            _logger.warning(
                "Could not export the file %s due to missing data.", ANNUAL_MONTHLY_RESULTS_FILENAME
            )

        # System attributes and derived data
        if response_exists:
            calculation_attributes = {
                "systemAttributes": self.ModelChainResponse.SystemAttributes,
                "inputDerivedData": self.ModelChainResponse.InputsDerivedFileContents,
                "totalModuleArea": self.ModelChainResponse.TotalModuleArea,
            }
        else:
            calculation_attributes = self.CalculationAttributes

        _save_content(
            calculation_attributes,
            output_folder_path / CALCULATION_ATTRIBUTES_FILENAME,
            json_indent=2,
            type_file="calculation attributes",
        )

        # Loss tree timeseries
        if response_exists:
            loss_tree_results_text = self.ModelChainResponse.LossTreeResults
            if loss_tree_results_text is not None and len(loss_tree_results_text) > 0:
                _save_content(
                    loss_tree_results_text,
                    output_folder_path / LOSS_TREE_TIMESERIES_FILENAME,
                    type_file="loss tree results",
                )
            else:
                _logger.warning(
                    "Could not export the file %s due to missing data.",
                    LOSS_TREE_TIMESERIES_FILENAME,
                )
        else:
            loss_tree_dataframe = self.LossTreeTimeseries
            if loss_tree_dataframe is None or len(loss_tree_dataframe) == 0:
                _logger.warning(
                    "Could not export the file %s due to missing data.",
                    LOSS_TREE_TIMESERIES_FILENAME,
                )
            else:
                loss_tree_file_path = output_folder_path / LOSS_TREE_TIMESERIES_DATAFRAME_FILENAME
                loss_tree_dataframe.to_csv(loss_tree_file_path, sep="\t")
                _logger.debug(
                    "Saved loss tree results file to %s (exported from DataFrame, metadata may be missing)",
                    loss_tree_file_path,
                )

        # PVsyst timeseries
        if response_exists:
            pvsyst_results_text = self.ModelChainResponse.PvSystFormatResultsFile
            if pvsyst_results_text is not None and len(pvsyst_results_text) > 0:
                _save_content(
                    pvsyst_results_text,
                    output_folder_path / PVSYST_TIMESERIES_FILENAME,
                    type_file="PVsyst results",
                )
            else:
                _logger.warning(
                    "Could not export the file %s due to missing data.", PVSYST_TIMESERIES_FILENAME
                )
        else:
            pvsyst_dataframe = self.PVsystTimeseries
            if pvsyst_dataframe is None or len(pvsyst_dataframe) == 0:
                _logger.warning(
                    "Could not export the file %s due to missing data.", PVSYST_TIMESERIES_FILENAME
                )
            else:
                pvsyst_file_path = Path(output_folder_path) / PVSYST_TIMESERIES_DATAFRAME_FILENAME
                pvsyst_dataframe.to_csv(pvsyst_file_path, sep=";")
                _logger.debug(
                    "Saved PVsyst results file to %s (exported from DataFrame, metadata may be missing)",
                    pvsyst_file_path,
                )

        # Detailed timeseries
        if response_exists:
            timeseries_results_text = self.ModelChainResponse.ResultsFile
            if timeseries_results_text is not None and len(timeseries_results_text) > 0:
                _save_content(
                    timeseries_results_text,
                    output_folder_path / DETAILED_TIMESERIES_FILENAME,
                    type_file="timeseries results",
                )
            else:
                _logger.warning(
                    "Could not export the file %s due to missing data.",
                    DETAILED_TIMESERIES_FILENAME,
                )
        else:
            timeseries_dataframe = self.DetailedTimeseries
            if timeseries_dataframe is None or len(timeseries_dataframe) == 0:
                _logger.warning(
                    "Could not export the file %s due to missing data.",
                    DETAILED_TIMESERIES_FILENAME,
                )
            else:
                detailed_timeseries_file_path = (
                    Path(output_folder_path) / DETAILED_TIMESERIES_FILENAME
                )
                timeseries_dataframe.to_csv(detailed_timeseries_file_path, sep="\t")
                _logger.debug(
                    "Saved timeseries results file to %s (exported from DataFrame, metadata may be missing)",
                    detailed_timeseries_file_path,
                )

        _logger.info("Results written out to %s", output_folder_path)

        return

    def info(self) -> None:
        """
        Print the available data attributes in this results instance.
        """
        data = self.get_info()
        print("The results object contains the following data:")
        print(f"Name: {data['name']}")
        print(f"Annual data included: {data['has_annual_data']}")
        print(f"Monthly data included: {data['has_monthly_data']}")
        print(f"Calculation attributes included: {data['has_calculation_attributes']}")
        print(f"Loss tree timeseries included: {data['has_loss_tree_timeseries']}")
        print(f"PVsyst timeseries included: {data['has_pvsyst_timeseries']}")
        print(f"Detailed timeseries included: {data['has_detailed_timeseries']}")
        return

    def describe(self, project_year: int = 1) -> None:
        """
        Print project summary and key energy performance metrics.

        Parameters
        ----------
        project_year : int, optional
            The project year to display the key energy performance metrics.
        """
        # Project attributes
        calculation_attributes = self.CalculationAttributes
        if calculation_attributes is not None:
            latitude = calculation_attributes["systemAttributes"]["location"]["latitude"]
            longitude = calculation_attributes["systemAttributes"]["location"]["longitude"]
            altitude = calculation_attributes["systemAttributes"]["location"]["altitude"]
            print("-" * 55 + "\n\t\tGeneral site data:\n" + "-" * 55)
            print(f"Project name = {self.Name}")
            print(
                f"Location (latitude, longitude, altitude) = {latitude:.5f}\u00b0, {longitude:.5f}\u00b0, {altitude:.1f} m"
            )
            print(
                f"2D/3D = {'3D' if calculation_attributes['systemAttributes']['is3D'] else '2D'} calculation"
            )
            print(f"Mounting type = {calculation_attributes['systemAttributes']['mounting']}")
            print(
                f"AC capacity of system = {calculation_attributes['systemAttributes']['acCapacityInMegawatts']} MW"
            )
            print(
                f"DC capacity of system = {calculation_attributes['systemAttributes']['dcCapacityInMegawatts']} MW"
            )
            print(
                f"Run in SolarFarmer API version {calculation_attributes['systemAttributes']['solarFarmerApiVersion']}"
            )
        else:
            print("Could not find project attributes.")

        # Display energy performance metrics
        self.performance(project_year=project_year)

        return

    def performance(self, project_year: int = 1) -> None:
        """
        Print key energy performance metrics for the specified project year.

        Parameters
        ----------
        project_year : int, optional
            The project year to display the key energy performance metrics (starts in 1).
        """
        data = self.get_performance(project_year)

        if not data:
            return

        table_annual_results = [
            [
                "Average annual temperature",
                f"{data['average_temperature']:.2f}\N{DEGREE SIGN}C",
            ],
            [
                "Horizontal irradiation",
                f"{data['horizontal_irradiation']:.2f} kWh/m\u00b2",
            ],
            [
                "Irradiation on tilted plane",
                f"{data['irradiation_on_tilted_plane']:.2f} kWh/m\u00b2",
            ],
            [
                "Effective irradiation on tilted plane",
                f"{data['effective_irradiation']:.2f} kWh/m\u00b2",
            ],
            [
                "Energy yield",
                f"{data['energy_yield']:.2f} kWh/kWp",
            ],
            [
                "Net energy",
                f"{data['net_energy']:.2f} MWh/year",
            ],
            [
                "Performance Ratio",
                f"{data['performance_ratio']:.4f}",
            ],
        ]
        print(
            "-" * 55
            + "\n"
            + " " * 4
            + f"Annual Performance Summary (project year {data['project_year']}, {data['calendar_year']})"
        )
        print(tabulate(table_annual_results))

    def calculation_attributes(self) -> dict[str, Any] | None:
        """
        Return calculation attributes and derived system data.

        Returns
        -------
        dict[str, Any] | None
            Metadata and derived inputs used during the energy calculation,
            or None if not available.
        """
        return self.CalculationAttributes

    def loss_tree_timeseries(self) -> pd.DataFrame | None:
        """
        Return the loss tree timeseries results.

        Returns
        -------
        pd.DataFrame | None
            Main native SolarFarmer results timeseries, or None if not available.
        """
        return self.LossTreeTimeseries

    def pvsyst_timeseries(self) -> pd.DataFrame | None:
        """
        Return the PVsyst-style timeseries results.

        Returns
        -------
        pd.DataFrame | None
            Timeseries formatted similarly to PVsyst, or None if not available.
        """
        return self.PVsystTimeseries

    def detailed_timeseries(self) -> pd.DataFrame | None:
        """
        Return the detailed timeseries results.

        Returns
        -------
        pd.DataFrame | None
            Secondary timeseries containing additional intermediate calculation
            steps, useful for diagnostics, or None if not available.
        """
        return self.DetailedTimeseries

    def get_info(self) -> dict[str, bool | str]:
        """
        Returns metadata about what data is available in this results instance.

        Returns
        -------
        dict[str, bool | str]
            Dictionary with keys:
            - 'name': Project name
            - 'has_annual_data': Whether annual data is available
            - 'has_monthly_data': Whether monthly data is available
            - 'has_calculation_attributes': Whether calculation attributes are available
            - 'has_loss_tree_timeseries': Whether loss tree timeseries is available
            - 'has_pvsyst_timeseries': Whether PVsyst timeseries is available
            - 'has_detailed_timeseries': Whether detailed timeseries is available

        Examples
        --------
        >>> info = results.get_info()
        >>> if info['has_monthly_data']:
        ...     monthly_data = results.get_monthly_results_table()
        """
        return {
            "name": self.Name,
            "has_annual_data": self.AnnualData is not None,
            "has_monthly_data": self.MonthlyData is not None,
            "has_calculation_attributes": self.CalculationAttributes is not None,
            "has_loss_tree_timeseries": self.LossTreeTimeseries is not None,
            "has_pvsyst_timeseries": self.PVsystTimeseries is not None,
            "has_detailed_timeseries": self.DetailedTimeseries is not None,
        }

    def get_performance(self, project_year: int = 1) -> dict[str, int | float]:
        """
        Returns key energy performance metrics for the specified project year.

        Parameters
        ----------
        project_year : int, optional
            The project year (1-based index). Default is 1.

        Returns
        -------
        dict[str, int | float]
            Dictionary with keys:
            - 'project_year': The project year (1-based)
            - 'calendar_year': The calendar year
            - 'average_temperature': Average annual temperature (°C)
            - 'horizontal_irradiation': Global horizontal irradiation (kWh/m²)
            - 'irradiation_on_tilted_plane': Irradiation on tilted plane (kWh/m²)
            - 'effective_irradiation': Effective irradiation on tilted plane (kWh/m²)
            - 'energy_yield': Specific energy yield (kWh/kWp)
            - 'net_energy': Net energy production (MWh/year)
            - 'performance_ratio': Performance ratio (0-1)

        Examples
        --------
        >>> perf = results.get_performance(project_year=1)
        >>> print(f"Net energy: {perf['net_energy']:.2f} MWh/year")
        >>> # Multi-year comparison
        >>> import pandas as pd
        >>> df = pd.DataFrame([results.get_performance(y) for y in range(1, 11)])
        >>> df.plot(x='calendar_year', y='energy_yield')
        """
        if not self.AnnualData:
            _logger.warning("get_performance: No annual data available.")
            return {}

        project_year_index = project_year - 1

        if project_year_index < 0 or project_year_index >= len(self.AnnualData):
            _logger.warning(
                "get_performance: project_year %d is out of range (1–%d).",
                project_year,
                len(self.AnnualData),
            )
            return {}

        annual_results = self.AnnualData[project_year_index]
        yield_results = annual_results[ANNUAL_ENERGY_YIELD_RESULTS_KEY]
        return {
            "project_year": project_year_index + 1,
            "calendar_year": annual_results["year"],
            "average_temperature": yield_results[ANNUAL_AVERAGE_TEMPERATURE],
            "horizontal_irradiation": yield_results[ANNUAL_GHI],
            "irradiation_on_tilted_plane": yield_results[ANNUAL_GI],
            "effective_irradiation": yield_results[ANNUAL_GLOBAL_EFFECTIVE_IRRADIANCE],
            "energy_yield": yield_results[ANNUAL_ENERGY_YIELD],
            "net_energy": yield_results[ANNUAL_NET_ENERGY],
            "performance_ratio": yield_results[ANNUAL_PERFORMANCE_RATIO],
        }

    def get_annual_results_table(
        self,
        include_energy_results: bool = True,
        include_effects: bool = True,
        project_years: list[int] | None = None,
    ) -> dict[str, list[dict[str, int | float]]]:
        """
        Returns annual energy yield results and/or annual effects as structured data.

        Parameters
        ----------
        include_energy_results : bool, optional
            If True, includes energy yield results in the output. Default is True.
        include_effects : bool, optional
            If True, includes annual effects in the output. Default is True.
        project_years : list[int], optional
            List of project years to include (1-based indices) or actual calendar years.
            If None, includes all years. Examples: [1, 3] or [1994, 1996].

        Returns
        -------
        dict[str, list[dict[str, int | float]]]
            Dictionary with keys 'energy_results' and/or 'effects'.
            Each value is a list of dictionaries, one per year.

        Examples
        --------
        >>> data = results.get_annual_results_table(project_years=[1, 2, 3])
        >>> import pandas as pd
        >>> energy_df = pd.DataFrame(data['energy_results'])
        >>> effects_df = pd.DataFrame(data['effects'])
        >>> # Export to Excel
        >>> with pd.ExcelWriter('results.xlsx') as writer:
        ...     energy_df.to_excel(writer, sheet_name='Energy')
        ...     effects_df.to_excel(writer, sheet_name='Effects')
        """
        if not self.AnnualData:
            _logger.warning("get_annual_results_table: No annual data available.")
            return {}

        if not include_energy_results and not include_effects:
            _logger.warning(
                "get_annual_results_table: Please set 'include_energy_results' or "
                "'include_effects' to True to retrieve data."
            )
            return {}

        project_year_indices = self._resolve_year_indices(self.AnnualData, project_years)
        output = {}

        if include_energy_results:
            energy_results = []
            for idx in project_year_indices:
                year_data = self.AnnualData[idx]
                yield_results = year_data[ANNUAL_ENERGY_YIELD_RESULTS_KEY]
                energy_results.append(
                    {
                        "project_year": idx + 1,
                        "calendar_year": year_data["year"],
                        "record_count": yield_results.get(ANNUAL_RECORD_COUNT),
                        "percent_complete": yield_results.get(ANNUAL_PERCENT_COMPLETE),
                        "average_temperature": yield_results.get(ANNUAL_AVERAGE_TEMPERATURE),
                        "ghi": yield_results.get(ANNUAL_GHI),
                        "gi": yield_results.get(ANNUAL_GI),
                        "gi_with_horizon": yield_results.get(ANNUAL_GI_WITH_HORIZON),
                        "gain_on_tilted_plane": yield_results.get(ANNUAL_GAIN_ON_TILTED_PLANE),
                        "global_effective_irradiance": yield_results.get(
                            ANNUAL_GLOBAL_EFFECTIVE_IRRADIANCE
                        ),
                        "module_power": yield_results.get(ANNUAL_MODULE_POWER),
                        "module_power_at_stc": yield_results.get(ANNUAL_MODULE_POWER_AT_STC),
                        "nominal_energy": yield_results.get(ANNUAL_NOMINAL_ENERGY),
                        "pdc": yield_results.get(ANNUAL_PDC),
                        "pac": yield_results.get(ANNUAL_PAC),
                        "performance_ratio": yield_results.get(ANNUAL_PERFORMANCE_RATIO),
                        "performance_ratio_bifacial": yield_results.get(
                            ANNUAL_PERFORMANCE_RATIO_BIFACIAL
                        ),
                        "net_energy": yield_results.get(ANNUAL_NET_ENERGY),
                        "energy_yield": yield_results.get(ANNUAL_ENERGY_YIELD),
                    }
                )
            output["energy_results"] = energy_results

        if include_effects:
            effects = []
            for idx in project_year_indices:
                year_data = self.AnnualData[idx]
                annual_effects = year_data[ANNUAL_EFFECTS_KEY]
                effects.append(
                    {
                        "project_year": idx + 1,
                        "calendar_year": year_data["year"],
                        "horizon": annual_effects.get(EFFECT_HORIZON, 0),
                        "near_shading_irradiance": annual_effects.get(
                            EFFECT_NEAR_SHADING_IRRADIANCE, 0
                        ),
                        "soiling": annual_effects.get(EFFECT_SOILING, 0),
                        "angular": annual_effects.get(EFFECT_ANGULAR, 0),
                        "spectral": annual_effects.get(EFFECT_SPECTRAL, 0),
                        "back_irradiance_gain": annual_effects.get(EFFECT_BACK_IRRADIANCE_GAIN, 0),
                        "bifacial_angular": annual_effects.get(EFFECT_BIFACIAL_ANGULAR, 0),
                        "bifacial_shading": annual_effects.get(EFFECT_BIFACIAL_SHADING, 0),
                        "bifacial_transmission": annual_effects.get(
                            EFFECT_BIFACIAL_TRANSMISSION, 0
                        ),
                        "back_near_shading_irradiance": annual_effects.get(
                            EFFECT_BACK_NEAR_SHADING_IRRADIANCE, 0
                        ),
                        "modeling": annual_effects.get(EFFECT_MODELING, 0),
                        "modeling_correction": annual_effects.get(EFFECT_MODELING_CORRECTION, 0),
                        "temperature": annual_effects.get(EFFECT_TEMPERATURE, 0),
                        "irradiance": annual_effects.get(EFFECT_IRRADIANCE, 0),
                        "bifaciality_factor": annual_effects.get(EFFECT_BIFACIALITY_FACTOR, 0),
                        "back_irradiance_mismatch": annual_effects.get(
                            EFFECT_BACK_IRRADIANCE_MISMATCH, 0
                        ),
                        "power_binning": annual_effects.get(EFFECT_POWER_BINNING, 0),
                        "light_induced_degradation": annual_effects.get(
                            EFFECT_LIGHT_INDUCED_DEGRADATION, 0
                        ),
                        "module_quality": annual_effects.get(EFFECT_MODULE_QUALITY, 0),
                        "module_mismatch": annual_effects.get(EFFECT_MODULE_MISMATCH, 0),
                        "optimizers_operational_input_limits": annual_effects.get(
                            EFFECT_OPTIMIZERS_OPERATIONAL_INPUT_LIMITS, 0
                        ),
                        "optimizers_efficiency": annual_effects.get(
                            EFFECT_OPTIMIZERS_EFFICIENCY, 0
                        ),
                        "optimizers_operational_output_limits": annual_effects.get(
                            EFFECT_OPTIMIZERS_OPERATIONAL_OUTPUT_LIMITS, 0
                        ),
                        "electrical_mismatch": annual_effects.get(EFFECT_ELECTRICAL_MISMATCH, 0),
                        "ohmic_dc": annual_effects.get(EFFECT_OHMIC_DC, 0),
                        "inverter_min_dc_voltage": annual_effects.get(
                            EFFECT_INVERTER_MIN_DC_VOLTAGE, 0
                        ),
                        "inverter_max_dc_current": annual_effects.get(
                            EFFECT_INVERTER_MAX_DC_CURRENT, 0
                        ),
                        "inverter_max_dc_voltage": annual_effects.get(
                            EFFECT_INVERTER_MAX_DC_VOLTAGE, 0
                        ),
                        "inverter_min_dc_power": annual_effects.get(
                            EFFECT_INVERTER_MIN_DC_POWER, 0
                        ),
                        "inverter_efficiency": annual_effects.get(EFFECT_INVERTER_EFFICIENCY, 0),
                        "inverter_max_ac_power": annual_effects.get(
                            EFFECT_INVERTER_MAX_AC_POWER, 0
                        ),
                        "inverter_over_power_shutdown": annual_effects.get(
                            EFFECT_INVERTER_OVER_POWER_SHUTDOWN, 0
                        ),
                        "inverter_tare": annual_effects.get(EFFECT_INVERTER_TARE, 0),
                        "auxiliaries": annual_effects.get(EFFECT_AUXILIARIES, 0),
                        "ohmic_ac": annual_effects.get(EFFECT_OHMIC_AC, 0),
                        "transformer": annual_effects.get(EFFECT_TRANSFORMER, 0),
                        "system_availability": annual_effects.get(EFFECT_SYSTEM_AVAILABILITY, 0),
                        "grid_limit": annual_effects.get(EFFECT_GRID_LIMIT, 0),
                        "grid_availability": annual_effects.get(EFFECT_GRID_AVAILABILITY, 0),
                    }
                )
            output["effects"] = effects

        return output

    def get_monthly_results_table(
        self,
        include_energy_results: bool = True,
        include_effects: bool = True,
        project_years: list[int] | None = None,
    ) -> dict[str, list[dict[str, int | float | str]]]:
        """
        Returns monthly energy yield results and/or monthly effects as structured data.

        Parameters
        ----------
        include_energy_results : bool, optional
            If True, includes energy yield results in the output. Default is True.
        include_effects : bool, optional
            If True, includes monthly effects in the output. Default is True.
        project_years : list[int], optional
            List of project years to include (1-based indices) or actual calendar years.
            If None, includes all years. Examples: [1, 3] or [1994, 1996].

        Returns
        -------
        dict[str, list[dict[str, int | float | str]]]
            Dictionary with keys 'energy_results' and/or 'effects'.
            Each value is a flat list of dictionaries (one per month across all years).
            Total rows = num_years * 12.

        Examples
        --------
        >>> data = results.get_monthly_results_table(project_years=[1, 2])
        >>> import pandas as pd
        >>> monthly_df = pd.DataFrame(data['energy_results'])
        >>> # Filter summer months
        >>> summer = monthly_df[monthly_df['month'].isin([6, 7, 8])]
        >>> # Group by month across years
        >>> monthly_df.groupby('month')['energy_yield'].mean()
        """
        if not self.MonthlyData:
            _logger.warning("get_monthly_results_table: No monthly data available.")
            return {}

        if not include_energy_results and not include_effects:
            _logger.warning(
                "get_monthly_results_table: Please set 'include_energy_results' or "
                "'include_effects' to True to retrieve data."
            )
            return {}

        project_year_indices = self._resolve_year_indices(self.MonthlyData, project_years)
        output = {}

        if include_energy_results:
            energy_results = []
            for idx in project_year_indices:
                year_data = self.MonthlyData[idx]
                calendar_year = year_data["year"]
                monthly_results = year_data[MONTHLY_ENERGY_YIELD_RESULTS_KEY]

                for month_data in monthly_results:
                    month_num = month_data.get("month", 0)
                    yield_results = month_data.get(ANNUAL_ENERGY_YIELD_RESULTS_KEY, {})
                    energy_results.append(
                        {
                            "project_year": idx + 1,
                            "calendar_year": calendar_year,
                            "month": month_num,
                            "month_name": calendar.month_abbr[month_num]
                            if 1 <= month_num <= 12
                            else "",
                            "record_count": yield_results.get(ANNUAL_RECORD_COUNT),
                            "percent_complete": yield_results.get(ANNUAL_PERCENT_COMPLETE),
                            "average_temperature": yield_results.get(ANNUAL_AVERAGE_TEMPERATURE),
                            "ghi": yield_results.get(ANNUAL_GHI),
                            "gi": yield_results.get(ANNUAL_GI),
                            "gi_with_horizon": yield_results.get(ANNUAL_GI_WITH_HORIZON),
                            "gain_on_tilted_plane": yield_results.get(ANNUAL_GAIN_ON_TILTED_PLANE),
                            "global_effective_irradiance": yield_results.get(
                                ANNUAL_GLOBAL_EFFECTIVE_IRRADIANCE
                            ),
                            "module_power": yield_results.get(ANNUAL_MODULE_POWER),
                            "module_power_at_stc": yield_results.get(ANNUAL_MODULE_POWER_AT_STC),
                            "nominal_energy": yield_results.get(ANNUAL_NOMINAL_ENERGY),
                            "pdc": yield_results.get(ANNUAL_PDC),
                            "pac": yield_results.get(ANNUAL_PAC),
                            "performance_ratio": yield_results.get(ANNUAL_PERFORMANCE_RATIO),
                            "performance_ratio_bifacial": yield_results.get(
                                ANNUAL_PERFORMANCE_RATIO_BIFACIAL
                            ),
                            "net_energy": yield_results.get(ANNUAL_NET_ENERGY),
                            "energy_yield": yield_results.get(ANNUAL_ENERGY_YIELD),
                        }
                    )
            output["energy_results"] = energy_results

        if include_effects:
            effects = []
            for idx in project_year_indices:
                year_data = self.MonthlyData[idx]
                calendar_year = year_data["year"]
                monthly_results_for_effects = year_data[MONTHLY_ENERGY_YIELD_RESULTS_KEY]

                for month_data in monthly_results_for_effects:
                    month_num = month_data.get("month", 0)
                    month_effects = month_data.get(MONTHLY_EFFECTS_KEY, {})
                    effects.append(
                        {
                            "project_year": idx + 1,
                            "calendar_year": calendar_year,
                            "month": month_num,
                            "month_name": calendar.month_abbr[month_num]
                            if 1 <= month_num <= 12
                            else "",
                            "horizon": month_effects.get(EFFECT_HORIZON, 0),
                            "near_shading_irradiance": month_effects.get(
                                EFFECT_NEAR_SHADING_IRRADIANCE, 0
                            ),
                            "soiling": month_effects.get(EFFECT_SOILING, 0),
                            "angular": month_effects.get(EFFECT_ANGULAR, 0),
                            "spectral": month_effects.get(EFFECT_SPECTRAL, 0),
                            "back_irradiance_gain": month_effects.get(
                                EFFECT_BACK_IRRADIANCE_GAIN, 0
                            ),
                            "bifacial_angular": month_effects.get(EFFECT_BIFACIAL_ANGULAR, 0),
                            "bifacial_shading": month_effects.get(EFFECT_BIFACIAL_SHADING, 0),
                            "bifacial_transmission": month_effects.get(
                                EFFECT_BIFACIAL_TRANSMISSION, 0
                            ),
                            "back_near_shading_irradiance": month_effects.get(
                                EFFECT_BACK_NEAR_SHADING_IRRADIANCE, 0
                            ),
                            "modeling": month_effects.get(EFFECT_MODELING, 0),
                            "modeling_correction": month_effects.get(EFFECT_MODELING_CORRECTION, 0),
                            "temperature": month_effects.get(EFFECT_TEMPERATURE, 0),
                            "irradiance": month_effects.get(EFFECT_IRRADIANCE, 0),
                            "bifaciality_factor": month_effects.get(EFFECT_BIFACIALITY_FACTOR, 0),
                            "back_irradiance_mismatch": month_effects.get(
                                EFFECT_BACK_IRRADIANCE_MISMATCH, 0
                            ),
                            "power_binning": month_effects.get(EFFECT_POWER_BINNING, 0),
                            "light_induced_degradation": month_effects.get(
                                EFFECT_LIGHT_INDUCED_DEGRADATION, 0
                            ),
                            "module_quality": month_effects.get(EFFECT_MODULE_QUALITY, 0),
                            "module_mismatch": month_effects.get(EFFECT_MODULE_MISMATCH, 0),
                            "optimizers_operational_input_limits": month_effects.get(
                                EFFECT_OPTIMIZERS_OPERATIONAL_INPUT_LIMITS, 0
                            ),
                            "optimizers_efficiency": month_effects.get(
                                EFFECT_OPTIMIZERS_EFFICIENCY, 0
                            ),
                            "optimizers_operational_output_limits": month_effects.get(
                                EFFECT_OPTIMIZERS_OPERATIONAL_OUTPUT_LIMITS, 0
                            ),
                            "electrical_mismatch": month_effects.get(EFFECT_ELECTRICAL_MISMATCH, 0),
                            "ohmic_dc": month_effects.get(EFFECT_OHMIC_DC, 0),
                            "inverter_min_dc_voltage": month_effects.get(
                                EFFECT_INVERTER_MIN_DC_VOLTAGE, 0
                            ),
                            "inverter_max_dc_current": month_effects.get(
                                EFFECT_INVERTER_MAX_DC_CURRENT, 0
                            ),
                            "inverter_max_dc_voltage": month_effects.get(
                                EFFECT_INVERTER_MAX_DC_VOLTAGE, 0
                            ),
                            "inverter_min_dc_power": month_effects.get(
                                EFFECT_INVERTER_MIN_DC_POWER, 0
                            ),
                            "inverter_efficiency": month_effects.get(EFFECT_INVERTER_EFFICIENCY, 0),
                            "inverter_max_ac_power": month_effects.get(
                                EFFECT_INVERTER_MAX_AC_POWER, 0
                            ),
                            "inverter_over_power_shutdown": month_effects.get(
                                EFFECT_INVERTER_OVER_POWER_SHUTDOWN, 0
                            ),
                            "inverter_tare": month_effects.get(EFFECT_INVERTER_TARE, 0),
                            "auxiliaries": month_effects.get(EFFECT_AUXILIARIES, 0),
                            "ohmic_ac": month_effects.get(EFFECT_OHMIC_AC, 0),
                            "transformer": month_effects.get(EFFECT_TRANSFORMER, 0),
                            "system_availability": month_effects.get(EFFECT_SYSTEM_AVAILABILITY, 0),
                            "grid_limit": month_effects.get(EFFECT_GRID_LIMIT, 0),
                            "grid_availability": month_effects.get(EFFECT_GRID_AVAILABILITY, 0),
                        }
                    )
            output["effects"] = effects

        return output

    def print_annual_results(
        self,
        show_energy_results: bool = True,
        show_effects: bool = True,
        project_years: list[int] | None = None,
        years_per_table: int = 5,
    ) -> None:
        """
        Displays the annual energy yield results in a tabular format, one column for each year of results.
        Also displays the annual effects in a tabular format, one column for each year of results.

        Parameters
        ----------
        show_energy_results: bool, optional
            If ``True``, it will display the annual energy yield results.
        show_effects: bool, optional
            If ``True``, it will display the annual effects.
        project_years: list[int], optional
            List of project years to display. If None, it will display all the years available in the results.
            The project years start with index 1 (e.g., project_years=[1, 3] will display the results for the first and third year of the project).
            Alternatively you can also specify the actual year (e.g., 1994, 1995, etc.) if you prefer (e.g., project_years=[1994, 1996] will display the results for the years 1994 and 1996).
        years_per_table: int, optional
            Number of years to display per table (one column per year). If there are more years in the results than the specified number of years per table,
            it will display multiple tables until all the years are displayed.
        """
        # Get structured data using get_annual_results_table()
        data = self.get_annual_results_table(
            include_energy_results=show_energy_results,
            include_effects=show_effects,
            project_years=project_years,
        )

        if not data:
            return

        # Determine number of years to display
        num_years = len(data.get("energy_results", data.get("effects", [])))
        num_tables = (num_years + years_per_table - 1) // years_per_table

        # Display annual results table if required
        if "energy_results" in data:
            energy_results = data["energy_results"]
            for table_idx in range(num_tables):
                start_idx = table_idx * years_per_table
                end_idx = min(start_idx + years_per_table, num_years)
                years_subset = energy_results[start_idx:end_idx]

                # Build table headers (years)
                headers = ["Property", "Units"] + [
                    f"Year {year['project_year']}\n({year['calendar_year']})"
                    for year in years_subset
                ]

                # Build table rows
                rows = [
                    ["Energy yield", "kWh/kWp"]
                    + [f"{year['energy_yield']:,.2f}" for year in years_subset],
                    ["Net energy", "MWh/year"]
                    + [f"{year['net_energy']:,.2f}" for year in years_subset],
                    ["Production DC", "kWh"] + [f"{year['pdc']:,.2f}" for year in years_subset],
                    ["Production AC", "kWh"] + [f"{year['pac']:,.2f}" for year in years_subset],
                    ["Performance Ratio", "%"]
                    + [f"{100 * year['performance_ratio']:,.2f}" for year in years_subset],
                    ["Performance Ratio Bifacial", "%"]
                    + [f"{100 * year['performance_ratio_bifacial']:,.2f}" for year in years_subset],
                    ["Average annual temperature", "°C"]
                    + [f"{year['average_temperature']:,.2f}" for year in years_subset],
                    ["Horizontal irradiation", "kWh/m²"]
                    + [f"{year['ghi']:,.2f}" for year in years_subset],
                    ["Irradiation on tilted plane", "kWh/m²"]
                    + [f"{year['gi']:,.2f}" for year in years_subset],
                    ["GI with horizon", "kWh/m²"]
                    + [f"{year['gi_with_horizon']:,.2f}" for year in years_subset],
                    ["Global effective irradiance", "kWh/m²"]
                    + [f"{year['global_effective_irradiance']:,.2f}" for year in years_subset],
                    ["Gain on tilted plane", "%"]
                    + [f"{100 * year['gain_on_tilted_plane']:,.2f}" for year in years_subset],
                ]

                # Set column alignment: left for Property and Units, right for year data
                colalign = ["left", "left"] + ["right"] * len(years_subset)

                num_hyphens = 30 + 10 * len(years_subset)
                print("-" * num_hyphens)
                years_header = [
                    f"{year['project_year']} ({year['calendar_year']})" for year in years_subset
                ]
                print(f"Annual Results Summary (Years: {', '.join(years_header)})")
                print("-" * num_hyphens)
                print(tabulate(rows, headers=headers, colalign=colalign))

        # Display annual effects table if required
        if "effects" in data:
            effects = data["effects"]
            for table_idx in range(num_tables):
                start_idx = table_idx * years_per_table
                end_idx = min(start_idx + years_per_table, num_years)
                years_subset = effects[start_idx:end_idx]

                # Build table headers (years)
                headers = ["Effect (%)"] + [
                    f"Year {year['project_year']}\n({year['calendar_year']})"
                    for year in years_subset
                ]

                # Build table rows for effects (convert to percentages)
                effect_rows = [
                    ["Horizon"] + [f"{100 * year['horizon']:.2f}" for year in years_subset],
                    ["Near shading irradiance"]
                    + [f"{100 * year['near_shading_irradiance']:.2f}" for year in years_subset],
                    ["Soiling"] + [f"{100 * year['soiling']:.2f}" for year in years_subset],
                    ["Angular"] + [f"{100 * year['angular']:.2f}" for year in years_subset],
                    ["Spectral"] + [f"{100 * year['spectral']:.2f}" for year in years_subset],
                    ["Back irradiance gain"]
                    + [f"{100 * year['back_irradiance_gain']:.2f}" for year in years_subset],
                    ["Bifacial angular"]
                    + [f"{100 * year['bifacial_angular']:.2f}" for year in years_subset],
                    ["Bifacial shading"]
                    + [f"{100 * year['bifacial_shading']:.2f}" for year in years_subset],
                    ["Bifacial transmission"]
                    + [f"{100 * year['bifacial_transmission']:.2f}" for year in years_subset],
                    ["Back near shading irradiance"]
                    + [
                        f"{100 * year['back_near_shading_irradiance']:.2f}" for year in years_subset
                    ],
                    ["Modeling"] + [f"{100 * year['modeling']:.2f}" for year in years_subset],
                    ["Modeling correction"]
                    + [f"{100 * year['modeling_correction']:.2f}" for year in years_subset],
                    ["Temperature"] + [f"{100 * year['temperature']:.2f}" for year in years_subset],
                    ["Irradiance"] + [f"{100 * year['irradiance']:.2f}" for year in years_subset],
                    ["Bifaciality factor"]
                    + [f"{100 * year['bifaciality_factor']:.2f}" for year in years_subset],
                    ["Back irradiance mismatch"]
                    + [f"{100 * year['back_irradiance_mismatch']:.2f}" for year in years_subset],
                    ["Power binning"]
                    + [f"{100 * year['power_binning']:.2f}" for year in years_subset],
                    ["Light induced degradation"]
                    + [f"{100 * year['light_induced_degradation']:.2f}" for year in years_subset],
                    ["Module quality"]
                    + [f"{100 * year['module_quality']:.2f}" for year in years_subset],
                    ["Module mismatch"]
                    + [f"{100 * year['module_mismatch']:.2f}" for year in years_subset],
                    ["Optimizers operational input limits"]
                    + [
                        f"{100 * year['optimizers_operational_input_limits']:.2f}"
                        for year in years_subset
                    ],
                    ["Optimizers efficiency"]
                    + [f"{100 * year['optimizers_efficiency']:.2f}" for year in years_subset],
                    ["Optimizers operational output limits"]
                    + [
                        f"{100 * year['optimizers_operational_output_limits']:.2f}"
                        for year in years_subset
                    ],
                    ["Electrical mismatch"]
                    + [f"{100 * year['electrical_mismatch']:.2f}" for year in years_subset],
                    ["Ohmic DC"] + [f"{100 * year['ohmic_dc']:.2f}" for year in years_subset],
                    ["Inverter min DC voltage"]
                    + [f"{100 * year['inverter_min_dc_voltage']:.2f}" for year in years_subset],
                    ["Inverter max DC current"]
                    + [f"{100 * year['inverter_max_dc_current']:.2f}" for year in years_subset],
                    ["Inverter max DC voltage"]
                    + [f"{100 * year['inverter_max_dc_voltage']:.2f}" for year in years_subset],
                    ["Inverter min DC power"]
                    + [f"{100 * year['inverter_min_dc_power']:.2f}" for year in years_subset],
                    ["Inverter efficiency"]
                    + [f"{100 * year['inverter_efficiency']:.2f}" for year in years_subset],
                    ["Inverter max AC power"]
                    + [f"{100 * year['inverter_max_ac_power']:.2f}" for year in years_subset],
                    ["Inverter over power shutdown"]
                    + [
                        f"{100 * year['inverter_over_power_shutdown']:.2f}" for year in years_subset
                    ],
                    ["Inverter tare"]
                    + [f"{100 * year['inverter_tare']:.2f}" for year in years_subset],
                    ["Auxiliaries"] + [f"{100 * year['auxiliaries']:.2f}" for year in years_subset],
                    ["Ohmic AC"] + [f"{100 * year['ohmic_ac']:.2f}" for year in years_subset],
                    ["Transformer"] + [f"{100 * year['transformer']:.2f}" for year in years_subset],
                    ["System availability"]
                    + [f"{100 * year['system_availability']:.2f}" for year in years_subset],
                    ["Grid limit"] + [f"{100 * year['grid_limit']:.2f}" for year in years_subset],
                    ["Grid availability"]
                    + [f"{100 * year['grid_availability']:.2f}" for year in years_subset],
                ]

                # Set column alignment: left for Effect, right for year data
                colalign_effects = ["left"] + ["right"] * len(years_subset)

                num_hyphens = 30 + 10 * len(years_subset)
                print("-" * num_hyphens)
                years_header = [
                    f"{year['project_year']} ({year['calendar_year']})" for year in years_subset
                ]
                print(f"Annual Effects Summary (Years: {', '.join(years_header)})")
                print("-" * num_hyphens)
                print(
                    tabulate(
                        effect_rows, headers=headers, floatfmt=".2f", colalign=colalign_effects
                    )
                )

        return

    def print_monthly_results(
        self,
        show_energy_results: bool = True,
        show_effects: bool = True,
        project_years: list[int] | None = None,
    ) -> None:
        """
        Displays the monthly energy yield results in a tabular format, one column for each month of results.
        Also displays the monthly effects in a tabular format, one column for each month of results.

        Parameters
        ----------
        show_energy_results: bool, optional
            If ``True``, it will display the annual energy yield results.
        show_effects: bool, optional
            If ``True``, it will display the annual effects.
        project_years: list[int], optional
            List of project years to display. If None, it will display all the years available in the results.
            The project years start with index 1 (e.g., project_years=[1, 3] will display the results for the first and third year of the project).
            Alternatively you can also specify the actual year (e.g., 1994, 1995, etc.) if you prefer (e.g., project_years=[1994, 1996] will display the results for the years 1994 and 1996).
        """
        # Get structured data using get_monthly_results_table()
        data = self.get_monthly_results_table(
            include_energy_results=show_energy_results,
            include_effects=show_effects,
            project_years=project_years,
        )

        if not data:
            return

        num_hyphens = 39

        # Group results by year for display (since data is flat list)
        if "energy_results" in data or "effects" in data:
            # Get unique years from whichever dataset is available
            sample_data = data.get("energy_results", data.get("effects", []))
            unique_years = {}
            for row in sample_data:
                year_key = (row["project_year"], row["calendar_year"])
                if year_key not in unique_years:
                    unique_years[year_key] = []

            # Display results for each year
            for project_year, calendar_year in sorted(unique_years.keys()):
                # Display energy results table if required
                if "energy_results" in data:
                    # Filter data for this year
                    year_energy = [
                        row
                        for row in data["energy_results"]
                        if row["project_year"] == project_year
                        and row["calendar_year"] == calendar_year
                    ]

                    if year_energy:
                        # Build table headers (months)
                        headers = ["Property", "Units"] + [row["month_name"] for row in year_energy]

                        # Build table rows
                        rows = [
                            ["Energy yield", "kWh/kWp"]
                            + [f"{row['energy_yield']:,.2f}" for row in year_energy],
                            ["Net energy", "MWh/year"]
                            + [f"{row['net_energy']:,.2f}" for row in year_energy],
                            ["Production DC", "kWh"]
                            + [f"{row['pdc']:,.2f}" for row in year_energy],
                            ["Production AC", "kWh"]
                            + [f"{row['pac']:,.2f}" for row in year_energy],
                            ["Performance Ratio", "%"]
                            + [f"{100 * row['performance_ratio']:.2f}" for row in year_energy],
                            ["Performance Ratio Bifacial", "%"]
                            + [
                                f"{100 * row['performance_ratio_bifacial']:.2f}"
                                for row in year_energy
                            ],
                            ["Average temperature", "°C"]
                            + [f"{row['average_temperature']:,.2f}" for row in year_energy],
                            ["Horizontal irradiation", "kWh/m²"]
                            + [f"{row['ghi']:,.2f}" for row in year_energy],
                            ["Irradiation on tilted plane", "kWh/m²"]
                            + [f"{row['gi']:,.2f}" for row in year_energy],
                            ["GI with horizon", "kWh/m²"]
                            + [f"{row['gi_with_horizon']:,.2f}" for row in year_energy],
                            ["Global effective irradiance", "kWh/m²"]
                            + [f"{row['global_effective_irradiance']:,.2f}" for row in year_energy],
                            ["Gain on tilted plane", "%"]
                            + [f"{100 * row['gain_on_tilted_plane']:,.2f}" for row in year_energy],
                        ]

                        # Set column alignment: left for Property and Units, right for month data
                        colalign = ["left", "left"] + ["right"] * len(year_energy)

                        print("-" * num_hyphens)
                        print(f"Monthly Results Summary - Year {project_year} ({calendar_year})")
                        print("-" * num_hyphens)
                        print(tabulate(rows, headers=headers, floatfmt=".2f", colalign=colalign))

                # Display effects table if required
                if "effects" in data:
                    # Filter data for this year
                    year_effects = [
                        row
                        for row in data["effects"]
                        if row["project_year"] == project_year
                        and row["calendar_year"] == calendar_year
                    ]

                    if year_effects:
                        # Build table headers (months)
                        headers_effects = ["Effect (%)"] + [
                            row["month_name"] for row in year_effects
                        ]

                        # Build table rows for effects (convert to percentages)
                        effect_rows = [
                            ["Horizon"] + [f"{100 * row['horizon']:.2f}" for row in year_effects],
                            ["Near shading irradiance"]
                            + [
                                f"{100 * row['near_shading_irradiance']:.2f}"
                                for row in year_effects
                            ],
                            ["Soiling"] + [f"{100 * row['soiling']:.2f}" for row in year_effects],
                            ["Angular"] + [f"{100 * row['angular']:.2f}" for row in year_effects],
                            ["Spectral"] + [f"{100 * row['spectral']:.2f}" for row in year_effects],
                            ["Back irradiance gain"]
                            + [f"{100 * row['back_irradiance_gain']:.2f}" for row in year_effects],
                            ["Bifacial angular"]
                            + [f"{100 * row['bifacial_angular']:.2f}" for row in year_effects],
                            ["Bifacial shading"]
                            + [f"{100 * row['bifacial_shading']:.2f}" for row in year_effects],
                            ["Bifacial transmission"]
                            + [f"{100 * row['bifacial_transmission']:.2f}" for row in year_effects],
                            ["Back near shading irradiance"]
                            + [
                                f"{100 * row['back_near_shading_irradiance']:.2f}"
                                for row in year_effects
                            ],
                            ["Modeling"] + [f"{100 * row['modeling']:.2f}" for row in year_effects],
                            ["Modeling correction"]
                            + [f"{100 * row['modeling_correction']:.2f}" for row in year_effects],
                            ["Temperature"]
                            + [f"{100 * row['temperature']:.2f}" for row in year_effects],
                            ["Irradiance"]
                            + [f"{100 * row['irradiance']:.2f}" for row in year_effects],
                            ["Bifaciality factor"]
                            + [f"{100 * row['bifaciality_factor']:.2f}" for row in year_effects],
                            ["Back irradiance mismatch"]
                            + [
                                f"{100 * row['back_irradiance_mismatch']:.2f}"
                                for row in year_effects
                            ],
                            ["Power binning"]
                            + [f"{100 * row['power_binning']:.2f}" for row in year_effects],
                            ["Light induced degradation"]
                            + [
                                f"{100 * row['light_induced_degradation']:.2f}"
                                for row in year_effects
                            ],
                            ["Module quality"]
                            + [f"{100 * row['module_quality']:.2f}" for row in year_effects],
                            ["Module mismatch"]
                            + [f"{100 * row['module_mismatch']:.2f}" for row in year_effects],
                            ["Optimizers operational input limits"]
                            + [
                                f"{100 * row['optimizers_operational_input_limits']:.2f}"
                                for row in year_effects
                            ],
                            ["Optimizers efficiency"]
                            + [f"{100 * row['optimizers_efficiency']:.2f}" for row in year_effects],
                            ["Optimizers operational output limits"]
                            + [
                                f"{100 * row['optimizers_operational_output_limits']:.2f}"
                                for row in year_effects
                            ],
                            ["Electrical mismatch"]
                            + [f"{100 * row['electrical_mismatch']:.2f}" for row in year_effects],
                            ["Ohmic DC"] + [f"{100 * row['ohmic_dc']:.2f}" for row in year_effects],
                            ["Inverter min DC voltage"]
                            + [
                                f"{100 * row['inverter_min_dc_voltage']:.2f}"
                                for row in year_effects
                            ],
                            ["Inverter max DC current"]
                            + [
                                f"{100 * row['inverter_max_dc_current']:.2f}"
                                for row in year_effects
                            ],
                            ["Inverter max DC voltage"]
                            + [
                                f"{100 * row['inverter_max_dc_voltage']:.2f}"
                                for row in year_effects
                            ],
                            ["Inverter min DC power"]
                            + [f"{100 * row['inverter_min_dc_power']:.2f}" for row in year_effects],
                            ["Inverter efficiency"]
                            + [f"{100 * row['inverter_efficiency']:.2f}" for row in year_effects],
                            ["Inverter max AC power"]
                            + [f"{100 * row['inverter_max_ac_power']:.2f}" for row in year_effects],
                            ["Inverter over power shutdown"]
                            + [
                                f"{100 * row['inverter_over_power_shutdown']:.2f}"
                                for row in year_effects
                            ],
                            ["Inverter tare"]
                            + [f"{100 * row['inverter_tare']:.2f}" for row in year_effects],
                            ["Auxiliaries"]
                            + [f"{100 * row['auxiliaries']:.2f}" for row in year_effects],
                            ["Ohmic AC"] + [f"{100 * row['ohmic_ac']:.2f}" for row in year_effects],
                            ["Transformer"]
                            + [f"{100 * row['transformer']:.2f}" for row in year_effects],
                            ["System availability"]
                            + [f"{100 * row['system_availability']:.2f}" for row in year_effects],
                            ["Grid limit"]
                            + [f"{100 * row['grid_limit']:.2f}" for row in year_effects],
                            ["Grid availability"]
                            + [f"{100 * row['grid_availability']:.2f}" for row in year_effects],
                        ]

                        # Set column alignment: left for Effect, right for month data
                        colalign_effects = ["left"] + ["right"] * len(year_effects)

                        print("-" * num_hyphens)
                        print(f"Monthly Effects Summary - Year {project_year} ({calendar_year})")
                        print("-" * num_hyphens)
                        print(
                            tabulate(
                                effect_rows,
                                headers=headers_effects,
                                floatfmt=".2f",
                                colalign=colalign_effects,
                            )
                        )

        return

    def _resolve_year_indices(
        self, data: list[dict[str, Any]], project_years: list[int] | None
    ) -> list[int]:
        """
        Resolve user-provided project_years parameter to a list of indices.

        Handles three input cases:
        1. None → return indices for all years
        2. List of actual years (e.g., [1994, 1996]) → convert to indices
        3. List of project years (e.g., [1, 3]) → convert to indices

        Parameters
        ----------
        data : list[dict[str, Any]]
            The annual or monthly data list containing year information.
        project_years : list[int] | None
            User-specified years or project year indices.

        Returns
        -------
        list[int]
            List of indices corresponding to the resolved years.
        """
        if project_years is None:
            return list(range(len(data)))

        # If the input is a list of actual years (e.g., 1994, 1996)
        if all(isinstance(year, int) and year > 1000 for year in project_years):
            available_years = [year_data["year"] for year_data in data]
            indices = []
            for year in project_years:
                if year in available_years:
                    index = available_years.index(year)
                    indices.append(index)
                else:
                    _logger.warning("Year %d not found in the results. It will be skipped.", year)
            if not indices:
                _logger.warning(
                    "None of the specified years were found in the results. Displaying all years instead."
                )
                return list(range(len(data)))
            return indices

        # If the input is a list of project years (starting in 1)
        if all(isinstance(year, int) and year > 0 for year in project_years):
            indices = [year - 1 for year in project_years if 0 < year <= len(data)]
            if not indices:
                _logger.warning(
                    "None of the specified project years were valid. Displaying all years instead."
                )
                return list(range(len(data)))
            return indices

        # Invalid input
        _logger.warning(
            "Invalid input for project_years. It should be a list of integers representing "
            "either actual years or project years (starting in 1). Displaying all years instead."
        )
        return list(range(len(data)))


def _handle_annual_energy_yield_results(
    modelchain_response: ModelChainResponse,
    outputs_folder_path: str | Path,
    save_outputs: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract annual and monthly energy yield results from ModelChainResponse.

    Processes the response data and optionally saves to a JSON file.

    Parameters
    ----------
    modelchain_response : ModelChainResponse
        The ModelChainResponse object from the API call.
    outputs_folder_path: str
        The path of the output folder, where the results will be written.
    save_outputs: bool
        If True, it will save the results from the API call in the
        'outputs_folder_path'.

    Returns
    -------
    (annual_data, monthly_data): tuple
        'annual_data': list of annual energy yield and effects;
        'monthly_data': list of monthly energy yield and effects.
        Each element is one year of simulation, with each element holding
        the specific energy yield and loss tree effects for the period.
    """

    # Annual results list (collection, one for each year)
    annual_results_list = modelchain_response.AnnualEnergyYieldResults
    if annual_results_list is not None:
        if save_outputs:
            # Save the json results to file
            _save_content(
                annual_results_list,
                outputs_folder_path / ANNUAL_MONTHLY_RESULTS_FILENAME,
                json_indent=2,
                type_file="annual energy yield results",
            )

        annual_data, monthly_data = _separate_annual_monthly_data(annual_results_list)

        return annual_data, monthly_data

    else:
        _logger.debug("No annual energy yield results returned")
        return ([], [])


def _handle_system_attributes(
    modelchain_response: ModelChainResponse,
    outputs_folder_path: str | Path,
    save_outputs: bool,
) -> dict[str, Any]:
    """
    Extract system attributes and derived calculation data.

    Parameters
    ----------
    modelchain_response : ModelChainResponse
        The ModelChainResponse object from the API call.
    outputs_folder_path: str
        The path of the output folder, where the results will be written.
    save_outputs: bool
        If True, it will save the results from the API call in the
        'outputs_folder_path'.

    Returns
    -------
    calculation_attributes: dict[str, Any]
        The object contains the data from the system attributes,
        several inputs derived from the calculation and total module area.
    """
    # Assemble the system attributes and derived inputs
    calculation_attributes = {
        "systemAttributes": modelchain_response.SystemAttributes,
        "inputDerivedData": modelchain_response.InputsDerivedFileContents,
        "totalModuleArea": modelchain_response.TotalModuleArea,
    }

    if save_outputs:
        _save_content(
            calculation_attributes,
            outputs_folder_path / CALCULATION_ATTRIBUTES_FILENAME,
            json_indent=2,
            type_file="calculation attributes",
        )

    return calculation_attributes


def _handle_losstree_results(
    modelchain_response: ModelChainResponse,
    outputs_folder_path: str | Path,
    save_outputs: bool,
) -> pd.DataFrame | None:
    """
    Extract loss tree timeseries results from ModelChainResponse.

    Parameters
    ----------
    modelchain_response : ModelChainResponse
        The ModelChainResponse object from the API call.
    outputs_folder_path: str
        The path of the output folder, where the results will be written.
    save_outputs: bool
        If True, it will save the results from the API call in the
            'outputs_folder_path'.

    Returns
    -------
    pandas.DataFrame or None
        The loss tree timeseries as a DataFrame if pandas is installed; otherwise None.

    """
    # The Loss Tree Results
    loss_tree_results_text = modelchain_response.LossTreeResults

    if loss_tree_results_text is not None and len(loss_tree_results_text) > 0:
        if save_outputs:
            _save_content(
                loss_tree_results_text,
                outputs_folder_path / LOSS_TREE_TIMESERIES_FILENAME,
                type_file="loss tree results",
            )

        if _PANDAS:
            with io.StringIO(loss_tree_results_text) as g:
                data = pd.read_csv(g, sep="\t", skiprows=[0, 1])
                data["Start of period"] = pd.to_datetime(data["Start of period"])
                data.set_index("Start of period", inplace=True)
                data.sort_index(inplace=True)
            return data
        else:
            warnings.warn(
                PANDAS_INSTALL_MSG,
                stacklevel=2,
            )
            return None
    else:
        _logger.debug("No loss tree results returned.")
        return None


def _handle_pvsyst_results(
    modelchain_response: ModelChainResponse,
    outputs_folder_path: str | Path,
    save_outputs: bool,
) -> pd.DataFrame | None:
    """
    Extract PVsyst-style timeseries results from ModelChainResponse.

    Parameters
    ----------
    modelchain_response : ModelChainResponse
        The ModelChainResponse object from the API call.
    outputs_folder_path: str
        The path of the output folder, where the results will be written.
    save_outputs: bool
        If True, it will save the results from the API call in the
            'outputs_folder_path'.

    Returns
    -------
    pandas.DataFrame or None
        The pvsyst-style timeseries as a DataFrame if pandas is installed;
        otherwise None.

    """

    # The PVsyst format results file
    pvsyst_results_text = modelchain_response.PvSystFormatResultsFile

    if pvsyst_results_text is not None and len(pvsyst_results_text) > 0:
        if save_outputs:
            _save_content(
                pvsyst_results_text,
                outputs_folder_path / PVSYST_TIMESERIES_FILENAME,
                type_file="PVsyst results",
            )

        if _PANDAS:
            with io.StringIO(pvsyst_results_text) as g:
                data = pd.read_csv(g, sep=";", skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12])
            data["date"] = pd.to_datetime(data["date"], format="%d/%m/%y %H:%M", utc=True).dt.tz_localize(None)
            data.set_index("date", inplace=True)
            data.sort_index(inplace=True)
            return data
        else:
            warnings.warn(
                PANDAS_INSTALL_MSG,
                stacklevel=2,
            )
            return None
    else:
        _logger.debug("No PVsyst format file returned.")
        return None


def _handle_timeseries_results(
    modelchain_response: ModelChainResponse,
    outputs_folder_path: str | Path,
    save_outputs: bool,
) -> pd.DataFrame | None:
    """
    Extract detailed timeseries results from ModelChainResponse.

    Parameters
    ----------
    modelchain_response : ModelChainResponse
        The ModelChainResponse object from the API call.
    outputs_folder_path: str
        The path of the output folder, where the results will be written.
    save_outputs: bool
        If True, it will save the results from the API call in the
            'outputs_folder_path'.

    Returns
    -------
    list(pandas.DataFrame) or None
        List of detailed timeseries as a DataFrame if pandas is installed;
        otherwise None.

    """

    # Read the resultsFile into another pandas dataframe for analysis (not implemented here)
    timeseries_results_text = modelchain_response.ResultsFile
    if timeseries_results_text is not None and len(timeseries_results_text) > 0:
        if save_outputs:
            _save_content(
                timeseries_results_text,
                outputs_folder_path / DETAILED_TIMESERIES_FILENAME,
                type_file="timeseries results",
            )

        if _PANDAS:
            with io.StringIO(timeseries_results_text) as g:
                data = pd.read_csv(g, sep="\t")
            return data
        else:
            warnings.warn(
                PANDAS_INSTALL_MSG,
                stacklevel=2,
            )
            return None
    else:
        _logger.debug("No time series results returned")
        return None


def _save_content(
    content: str | bytes | dict | list,
    dest_path: str | Path,
    *,
    json_indent: int = 2,
    print_message: bool = True,
    type_file: str = "output",
) -> Path:
    """
    Save content to a file, handling JSON or plain text seamlessly.

    - If `content` is `dict` or `list`, it is JSON-serialized with indentation.
    - If `content` is `str`, it is written as-is (text).
    - If `content` is `bytes`, it is written in binary mode.

    Parameters
    ----------
    content : str | bytes | dict | list
        The data to write.
    dest_path : str | pathlib.Path
        Destination file path.
    json_indent : int, default=2
        Indentation used for JSON serialization (dict/list only).
    print_message : bool, default=True
        Whether to log a "Saved ..." message after writing.
    type_file : str, default="output"
        Label to use in the logged message (e.g., "annual results",
        "system attributes"). Used only when `print_message` is True.

    Returns
    -------
    pathlib.Path
        The path that was written.
    """
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, (dict, list)):
        text = json.dumps(content, indent=json_indent)
        path.write_text(text, encoding="utf-8")
    elif isinstance(content, bytes):
        path.write_bytes(content)
    else:
        # Treat everything else as text (e.g., str)
        path.write_text(str(content), encoding="utf-8")

    if print_message:
        _logger.debug("Saved %s file to %s", type_file, path)

    return path


def _separate_annual_monthly_data(
    annual_results_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Split annual energy yield results into separate annual and monthly data.

    Parameters
    ----------
    annual_results_list : list[dict[str, Any]]
        List of combined annual/monthly results from the API.

    Returns
    -------
    tuple[list[dict[str, Any]], list[dict[str, Any]]]
        Tuple of (annual_data, monthly_data) lists.
    """
    annual_data = []
    monthly_data = []
    for item in annual_results_list:
        # Extract year, annualEffects, energyYieldResults
        annual_data.append(
            {
                "year": item.get("year"),
                "annualEffects": item.get("annualEffects"),
                "energyYieldResults": item.get("energyYieldResults"),
            }
        )

        # Extract year and monthlyEnergyYieldResults
        monthly_data.append(
            {
                "year": item.get("year"),
                "monthlyEnergyYieldResults": item.get("monthlyEnergyYieldResults"),
            }
        )

    return annual_data, monthly_data


def _read_dataframe_pandas_safe(
    file_path: str | Path,
    separator_character: str,
    name_file: str,
    skip_rows: list[int] | None = None,
) -> pd.DataFrame | None:
    """
    Safely read a pandas DataFrame from a CSV file.

    Parameters
    ----------
    file_path : str | Path
        Path to the file to read.
    separator_character : str
        Character used to separate fields.
    name_file : str
        Name of the file for logging purposes.
    skip_rows : list[int] | None, optional
        Row indices to skip. Default is None.

    Returns
    -------
    pd.DataFrame | None
        Parsed DataFrame, or None if file doesn't exist or pandas unavailable.
    """
    if path_exists(file_path) is False:
        _logger.warning("The file %s could not be found.", file_path)
    else:
        if _PANDAS:
            dataframe = pd.read_csv(file_path, sep=separator_character, skiprows=skip_rows)
            _logger.debug("%s was imported successfully.", name_file)
            return dataframe
        else:
            warnings.warn(
                PANDAS_INSTALL_MSG,
                stacklevel=2,
            )
            return None
