"""
Utility functions that are used in the processing of the inputs
and creation of the SDK PVSystem class.
"""

import pathlib
from typing import Any

from .plant_defaults import DEFAULT_MUVOC_PCT, MIN_TEMP_VOC


def is_blank(parameter: str) -> bool:
    """Check if a string parameter is empty.

    Parameters
    ----------
    parameter : str
        The string to check for emptiness.

    Returns
    -------
    bool
        True if the string is empty, False otherwise.
    """
    if parameter == "":
        return True
    return False


def read_pan_file(pan_file: str, components_dir: str) -> dict[str, str]:
    """Read a PAN (module specification) file and parse its contents.

    Parameters
    ----------
    pan_file : str
        The name of the PAN file to read.
    components_dir : str
        The directory path where the PAN file is located.

    Returns
    -------
    Dict[str, str]
        A dictionary containing key-value pairs parsed from the PAN file,
        where keys and values are strings.
    """
    pan_dict = {}
    pan_file_path = pathlib.Path(components_dir) / pan_file
    with pan_file_path.open(errors="ignore") as f:
        for line in f:
            data = line.strip().split("=")
            try:
                key, value = data[0], data[1]
                pan_dict[key] = value
            except IndexError:
                pass
        return pan_dict


def read_ond_file(ond_file: str, components_dir: str) -> dict[str, str]:
    """Read an OND (inverter specification) file and parse its contents.

    Parameters
    ----------
    ond_file : str
        The name of the OND file to read.
    components_dir : str
        The directory path where the OND file is located.

    Returns
    -------
    Dict[str, str]
        A dictionary containing key-value pairs parsed from the OND file,
        where keys and values are strings.
    """
    ond_dict = {}
    ond_file_path = pathlib.Path(components_dir) / ond_file
    with ond_file_path.open(errors="ignore") as f:
        for line in f:
            data = line.strip().split("=")
            try:
                key, value = data[0], data[1]
                ond_dict[key] = value
            except IndexError:
                pass
        return ond_dict


def get_inverter_mppt(inverter_info: dict[str, Any]) -> int:
    """Extract the number of MPPTs from inverter specification data.

    Parameters
    ----------
    inverter_info : Dict[str, Any]
        A dictionary containing inverter information with a nested 'data' key.

    Returns
    -------
    int
        The number of MPPTs (Maximum Power Point Trackers) for the inverter.
        Defaults to 1 if not found in the specification.
    """
    try:
        inverter_mppt = int(inverter_info["data"]["NbMPPT"])
    except KeyError:
        inverter_mppt = 1
    return int(inverter_mppt)


def calculate_module_parameters(pan_info: dict[str, Any]) -> dict[str, Any]:
    """Calculate and add module parameters derived from PAN file data.

    Computes temperature-dependent module voltage parameters (Voc at minimum
    temperature) and adds them to the pan_info dictionary along with the
    module specification ID.

    Parameters
    ----------
    pan_info : Dict[str, Any]
        A dictionary containing parsed PAN file data with a nested 'data' key.

    Returns
    -------
    Dict[str, Any]
        The updated pan_info dictionary with added keys:
        - 'module_voc_at_min_temp': Module open-circuit voltage at minimum temperature
        - 'module_spec_id': Module specification identifier
    """
    pan_dict = pan_info["data"]
    # get module Voc
    module_voc = float(pan_dict["Voc"])
    # get module muVoc
    module_muvoc = get_module_muvoc(pan_dict)
    # get module muVoc at minimum temperature
    module_voc_at_min_temp = calculate_voc_at_min_temp(
        module_voc=module_voc, module_muvoc=module_muvoc, min_temp_voc=MIN_TEMP_VOC
    )
    # Add to dictionary
    pan_info["module_voc_at_min_temp"] = module_voc_at_min_temp
    pan_info["module_spec_id"] = pan_info["name"]
    return pan_info


def get_module_muvoc(pan_dict: dict[str, str]) -> float:
    """Calculate the temperature coefficient for module open-circuit voltage.

    Parameters
    ----------
    pan_dict : Dict[str, str]
        A dictionary containing parsed PAN file data with voltage specifications.

    Returns
    -------
    float
        The temperature coefficient (muVoc) in volts per degree Celsius.
        If Voc is not specified, reads from muVocSpec; otherwise calculates
        as percentage of Voc using DEFAULT_MUVOC_PCT constant.
    """
    module_voc = float(pan_dict["Voc"])
    if not module_voc:
        module_muvoc = float(pan_dict["muVocSpec"]) / 1000
    else:
        module_muvoc = module_voc * DEFAULT_MUVOC_PCT
    return module_muvoc


def calculate_voc_at_min_temp(module_voc: float, module_muvoc: float, min_temp_voc: float) -> float:
    """Calculate module open-circuit voltage at minimum site temperature.

    Uses the temperature coefficient to adjust voltage from standard test
    conditions (25°C) to the minimum expected site temperature.

    Parameters
    ----------
    module_voc : float
        Module open-circuit voltage at standard test conditions (25°C), in volts.
    module_muvoc : float
        Temperature coefficient for Voc, in volts per degree Celsius.
    min_temp_voc : float
        Minimum site temperature in degrees Celsius.

    Returns
    -------
    float
        Module open-circuit voltage at minimum temperature, in volts.
    """
    module_voc_at_min_temp = module_voc + (module_muvoc * (min_temp_voc - 25))
    return module_voc_at_min_temp
