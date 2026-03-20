"""
Data model for the response of the energy calculation results in the SolarFarmer API.

This module defines the `ModelChainResponse` class used to parse the
API response containing the energy calculation results.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelChainResponse:
    """
    Container for ModelChain and ModelChainAsync API results.

    This class provides methods to parse and validate raw JSON responses from the
    SolarFarmer API energy calculation endpoints.

    Attributes
    ----------
    Name : str | None
        The name or identifier of the project for this calculation.
        Typically provided by the user via the `project_id` parameter.
        None if no project identifier was specified.
    AnnualEnergyYieldResults : list[dict[str, Any]] | None
        List of annual energy yield results and loss effects, one entry per simulated year.
        Each dict contains 'year', 'energyYieldResults', 'annualEffects', and
        'monthlyEnergyYieldResults'. None if not returned by the API.
    InputsDerivedFileContents : dict[str, Any] | None
        Parsed JSON object containing derived input data and metadata used during
        the energy calculation. Includes processed system parameters, site info, etc.
        None if not returned by the API.
    LossTree : dict[str, Any] | None
        Hierarchical loss tree structure showing the calculation chain and loss categories.
        None if not requested or returned by the API.
    LossTreeResults : str | None
        Tab-separated values (TSV) text containing timestamped loss tree results.
        Aggregated energy values (kWh) for the whole site at each calculation timestamp.
        None if not returned by the API.
    PvSystFormatResultsFile : str | None
        Comma-separated values (CSV) text in PVsyst-compatible format containing
        timeseries results for the whole site. None if not returned by the API.
    ResultsFile : str | None
        Tab-separated values (TSV) text containing detailed timeseries results.
        Additional intermediate modeling data useful for debugging and analysis.
        None if not returned by the API.
    SystemAttributes : dict[str, Any] | None
        System-level attributes and metadata about the PV plant configuration
        used in the calculation (e.g., total DC capacity, inverter count).
        None if not returned by the API.
    TotalModuleArea : float | None
        Total PV module area in square meters (m²) for the entire plant.
        None if not returned by the API.
    """

    Name: str | None = None
    AnnualEnergyYieldResults: list[dict[str, Any]] | None = None
    InputsDerivedFileContents: dict[str, Any] | None = None
    LossTree: dict[str, Any] | None = None
    LossTreeResults: str | None = None
    PvSystFormatResultsFile: str | None = None
    ResultsFile: str | None = None
    SystemAttributes: dict[str, Any] | None = None
    TotalModuleArea: float | None = None

    def __repr__(self) -> str:
        """
        Developer-friendly string representation for debugging.

        Returns
        -------
        str
            A detailed representation showing which fields are populated.
        """
        fields = [
            f"Name={self.Name!r}",
            f"AnnualEnergyYieldResults={'present' if self.AnnualEnergyYieldResults else 'None'}",
            f"InputsDerivedFileContents={'present' if self.InputsDerivedFileContents else 'None'}",
            f"LossTree={'present' if self.LossTree else 'None'}",
            f"LossTreeResults={'present' if self.LossTreeResults else 'None'}",
            f"PvSystFormatResultsFile={'present' if self.PvSystFormatResultsFile else 'None'}",
            f"ResultsFile={'present' if self.ResultsFile else 'None'}",
            f"SystemAttributes={'present' if self.SystemAttributes else 'None'}",
            f"TotalModuleArea={self.TotalModuleArea}",
        ]
        return f"ModelChainResponse({', '.join(fields)})"

    @classmethod
    def from_response(cls, data: dict, project_id: str | None = None) -> ModelChainResponse:
        """
        Build ModelChainResponse from a parsed API JSON response.

        This method validates the input and delegates to `from_dict()` for
        field extraction. It does NOT handle async-specific unwrapping
        (e.g., extracting 'output' from async responses) - that logic is handled
        separately in the endpoint layer.

        Parameters
        ----------
        data : dict
            Parsed JSON dictionary returned by the SolarFarmer API.
            Must be a dict at the top level.
        project_id : str | None, optional
            The project ID or name to associate with this response.
            If None, the Name field will be None.

        Returns
        -------
        ModelChainResponse
            Populated response container with validated fields.

        Raises
        ------
        ValueError
            If `data` is not a dictionary (e.g., list or string at top level).

        Examples
        --------
        >>> data = api_client.post(endpoint="/ModelChain", ...)
        >>> response = ModelChainResponse.from_response(data, project_id="MyProject")
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a JSON object (dict) at top level, got {type(data).__name__}. "
                "Ensure the API response is properly formatted."
            )

        return cls.from_dict(data, project_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any], project_id: str | None = None) -> ModelChainResponse:
        """
        Build ModelChainResponse from a parsed JSON dictionary.

        This method extracts known fields from the API response and applies
        defensive parsing to avoid crashes from missing or malformed data.

        Parameters
        ----------
        data : dict
            Parsed JSON dictionary containing energy calculation results.
        project_id : str | None, optional
            The project ID or name to associate with this response.

        Returns
        -------
        ModelChainResponse
            Populated response container. Missing fields default to None.

        Notes
        -----
        - All fields are optional; missing keys result in None values.
        - The `inputsDerivedFileContents` field is expected to be a JSON string
          and is automatically parsed. If parsing fails or the field is missing,
          it defaults to None with a warning.
        - Field names match the exact API response keys (camelCase).

        Examples
        --------
        >>> data = {"annualEnergyYieldResults": [...], "systemAttributes": {...}}
        >>> response = ModelChainResponse.from_dict(data, "MyProject")
        """
        # Defensive parsing for inputsDerivedFileContents (JSON string → dict)
        inputs_derived = None
        raw_inputs_derived = data.get("inputsDerivedFileContents")
        if raw_inputs_derived is not None:
            if isinstance(raw_inputs_derived, str):
                try:
                    inputs_derived = json.loads(raw_inputs_derived)
                except json.JSONDecodeError as e:
                    warnings.warn(
                        f"Failed to parse 'inputsDerivedFileContents' as JSON: {e}. "
                        "This field will be set to None.",
                        stacklevel=2,
                    )
                    inputs_derived = None
            elif isinstance(raw_inputs_derived, dict):
                # API might return dict directly instead of JSON string
                inputs_derived = raw_inputs_derived
            else:
                warnings.warn(
                    f"'inputsDerivedFileContents' has unexpected type {type(raw_inputs_derived).__name__}. "
                    "Expected str or dict. This field will be set to None.",
                    stacklevel=2,
                )

        return cls(
            Name=project_id,
            AnnualEnergyYieldResults=data.get("annualEnergyYieldResults"),
            InputsDerivedFileContents=inputs_derived,
            LossTree=data.get("lossTree"),
            LossTreeResults=data.get("lossTreeResults"),
            PvSystFormatResultsFile=data.get("pvSystFormatResultsFile"),
            ResultsFile=data.get("resultsFile"),
            SystemAttributes=data.get("systemAttributes"),
            TotalModuleArea=data.get("totalModuleArea"),
        )
