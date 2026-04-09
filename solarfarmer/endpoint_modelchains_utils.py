import json
import pathlib
from contextlib import ExitStack
from datetime import timedelta
from math import floor
from typing import IO, Any

from .config import MODELCHAIN_ASYNC_POLL_TIME
from .logging import get_logger
from .weather import validate_tsv_timestamps

_logger = get_logger("endpoint.modelchains.utils")


def get_file_paths_in_folder(sample_data_folder: str | pathlib.Path, pattern: str) -> list[str]:
    """
    Get file paths in the specified folder using a file filter pattern.

    Wildcard patterns (e.g., '*.dat') use case-insensitive matching,
    while specific filenames are matched as-is using glob patterns.

    Parameters
    ----------
    sample_data_folder : str or pathlib.Path
        Path to the folder to search in
    pattern : str
        File filter pattern. Wildcard patterns starting with '*' match
        extensions case-insensitively (e.g., '*.dat' matches 'file.DAT',
        'data.dat', etc.). Other patterns use standard glob matching

    Returns
    -------
    List[str]
        List of matching file paths as strings
    """
    folder = pathlib.Path(sample_data_folder)

    # Handle wildcard extension patterns with case-insensitive matching
    if pattern.startswith("*"):
        extension = pattern[1:].lower()
        return [
            str(file_path)
            for file_path in folder.iterdir()
            if file_path.is_file() and file_path.suffix.lower() == extension
        ]

    # For specific filenames, use glob for pattern matching
    return [str(p) for p in folder.glob(pattern)]


def get_files(sample_data_folder: str | pathlib.Path) -> list[tuple[str, IO[bytes]]]:
    """
    Get the relevant input files for the energy calculation from a folder.

    Scans the specified folder for meteorological data files (DAT, TSV, CSV,
    or protobuf GZ), PAN module files, OND inverter files, and a HOR horizon
    file. Exactly one meteorological file must be present.

    Parameters
    ----------
    sample_data_folder : str or pathlib.Path
        Path to the folder to scan for input files

    Returns
    -------
    list of tuple[str, IO[bytes]]
        List of ``(field_name, file_handle)`` tuples ready for multipart upload.
        File handles are opened in binary read mode. The caller is responsible
        for closing them after use

    Raises
    ------
    RuntimeError
        If more than one file of a given type is found, or if more than one
        meteorological file is found across all supported formats
    """
    files = []
    stack = ExitStack()
    try:
        # Look for a DAT file and add the first one if there
        dat_file_paths = get_file_paths_in_folder(sample_data_folder, "*.DAT")
        if len(dat_file_paths) > 1:
            raise RuntimeError(
                f"\n\tOnly 1 DAT file is supported. There are {len(dat_file_paths)} DAT files."
            )
        if dat_file_paths:
            _logger.debug("tmyFile = %s", dat_file_paths[0])
            fh = pathlib.Path(dat_file_paths[0]).open("rb")
            stack.callback(fh.close)
            files.append(("tmyFile", fh))

        # Look for a Meteorological file with TSV and add the first one if there
        tsv_file_paths = get_file_paths_in_folder(sample_data_folder, "*.tsv")
        if len(tsv_file_paths) > 1:
            raise RuntimeError(
                f"\n\tOnly 1 TSV file is supported. There are {len(tsv_file_paths)} TSV files."
            )
        if tsv_file_paths:
            _logger.debug("tmyFile = %s", tsv_file_paths[0])
            validate_tsv_timestamps(tsv_file_paths[0])
            fh = pathlib.Path(tsv_file_paths[0]).open("rb")
            stack.callback(fh.close)
            files.append(("tmyFile", fh))

        # Look for a met file with CSV extension, assume it is PVsyst standard format (for now)
        # and add the first one if there
        csv_file_paths = get_file_paths_in_folder(sample_data_folder, "*.csv")
        if len(csv_file_paths) > 1:
            raise RuntimeError(
                f"\n\tOnly 1 CSV file is supported. There are {len(csv_file_paths)} CSV files."
            )
        if csv_file_paths:
            _logger.debug("pvSystStandardFormatFile = %s", csv_file_paths[0])
            fh = pathlib.Path(csv_file_paths[0]).open("rb")
            stack.callback(fh.close)
            files.append(("pvSystStandardFormatFile", fh))

        # Look for a MeteorologicalConditionsDatasetDto_Protobuf.gz file
        metDataTransferFile_file_paths = get_file_paths_in_folder(
            sample_data_folder, "MeteorologicalConditionsDatasetDto_Protobuf.gz"
        )
        if len(metDataTransferFile_file_paths) > 0:
            _logger.debug("metDataTransferFile = %s", metDataTransferFile_file_paths[0])
            fh = pathlib.Path(metDataTransferFile_file_paths[0]).open("rb")
            stack.callback(fh.close)
            files.append(("metDataTransferFile", fh))

        if len(files) > 1:
            raise RuntimeError(
                "\nThe folder contains more than one file that define the meteorological data."
                " Only a single meteorological file is supported."
            )

        # Look for PAN files in the folder and add them
        pan_file_paths = get_file_paths_in_folder(sample_data_folder, "*.PAN")
        for pan_file_path in pan_file_paths:
            _logger.debug("panFiles = %s", pan_file_path)
            fh = pathlib.Path(pan_file_path).open("rb")
            stack.callback(fh.close)
            files.append(("panFiles", fh))

        # Look for OND files in the folder and add them
        ond_file_paths = get_file_paths_in_folder(sample_data_folder, "*.OND")
        for ond_file_path in ond_file_paths:
            _logger.debug("ondFiles = %s", ond_file_path)
            fh = pathlib.Path(ond_file_path).open("rb")
            stack.callback(fh.close)
            files.append(("ondFiles", fh))

        # Look for a HOR file and add the first one if there
        hor_file_paths = get_file_paths_in_folder(sample_data_folder, "*.HOR")
        if len(hor_file_paths) > 1:
            raise RuntimeError(
                f"\n\tOnly 1 HOR file is supported. There are {len(hor_file_paths)} HOR files."
            )
        if hor_file_paths:
            _logger.debug("horFile = %s", hor_file_paths[0])
            fh = pathlib.Path(hor_file_paths[0]).open("rb")
            stack.callback(fh.close)
            files.append(("horFile", fh))

        return files
    except Exception:
        stack.close()
        raise


def read_calculation_inputs_from_folder(
    inputs_folder_path: str | pathlib.Path,
    energy_calculation_inputs_file_path: str | None,
) -> str:
    """
    Read the energy calculation inputs from a JSON file and return serialized JSON.

    If an explicit file path is provided it is used directly; otherwise the
    function searches ``inputs_folder_path`` for a single ``*.json`` file.

    Parameters
    ----------
    inputs_folder_path : str or pathlib.Path
        Folder to search when ``energy_calculation_inputs_file_path`` is None
    energy_calculation_inputs_file_path : str or None
        Explicit path to the ``EnergyCalculationInputs.json`` file. When
        provided, ``inputs_folder_path`` is ignored

    Returns
    -------
    str
        JSON-serialized string of the energy calculation inputs

    Raises
    ------
    RuntimeError
        If more than one JSON file is found in the folder, or if no JSON
        file is found
    """

    # When the JSON is given, it is read
    if energy_calculation_inputs_file_path is not None:
        energy_calc_inputs_path = pathlib.Path(energy_calculation_inputs_file_path)
        _logger.debug("jsonFile = %s", energy_calc_inputs_path)
        with energy_calc_inputs_path.open("rb") as file:
            energy_calc_inputs = json.load(file)
            return json.dumps(energy_calc_inputs)

    # When the JSON is not given, a *.json is searched in the subfolder
    json_file_paths = get_file_paths_in_folder(inputs_folder_path, "*.json")
    if len(json_file_paths) > 1:
        raise RuntimeError(
            "\n\tOnly one JSON file is supported. There are "
            f"{len(json_file_paths)} JSON files in the folder."
        )
    if json_file_paths:
        energy_calc_inputs_path = pathlib.Path(json_file_paths[0])
        _logger.debug("jsonFile = %s", energy_calc_inputs_path)
        with energy_calc_inputs_path.open("rb") as file:
            energy_calc_inputs = json.load(file)
            return json.dumps(energy_calc_inputs)
    else:
        raise RuntimeError("\n\tThe energy calculation JSON file is missing.")


def parse_files_from_folder(
    inputs_folder_path: str | pathlib.Path,
    energy_calculation_inputs_file_path: str | None,
) -> tuple[str, list[tuple[str, IO[bytes]]]]:
    """
    Parse all input files for the ModelChain or ModelChainAsync call from a folder.

    Parameters
    ----------
    inputs_folder_path : str or pathlib.Path
        Folder containing the input files (PAN, OND, meteorological data,
        and optionally a JSON inputs file)
    energy_calculation_inputs_file_path : str or None
        Explicit path to the ``EnergyCalculationInputs.json`` file. When
        None, a ``*.json`` file is searched for in ``inputs_folder_path``

    Returns
    -------
    tuple[str, list of tuple[str, IO[bytes]]]
        A ``(request_content, files)`` pair where ``request_content`` is the
        serialized JSON inputs string and ``files`` is a list of
        ``(field_name, file_handle)`` tuples for multipart upload
    """
    # Get the files (PAN, OND and met data) from the input folder path
    files = get_files(inputs_folder_path)
    stack = ExitStack()
    for _, fh in files:
        stack.callback(fh.close)
    try:
        # Get the JSON energy calculation inputs from the input folder path
        request_content = read_calculation_inputs_from_folder(
            inputs_folder_path, energy_calculation_inputs_file_path
        )
        return request_content, files
    except Exception:
        stack.close()
        raise


def parse_files_from_paths(
    meteorological_data_file_path: str,
    horizon_file_path: str | None,
    pan_file_paths: list[str],
    ond_file_paths: list[str],
    energy_calculation_inputs_file_path: str | None,
    parse_energy_calc_inputs: bool = True,
) -> tuple[str, list[tuple[str, IO[bytes]]]]:
    """
    Parse input files for the ModelChain or ModelChainAsync call from explicit paths.

    Parameters
    ----------
    meteorological_data_file_path : str
        Path to the meteorological data file. Accepted extensions are
        ``.tsv``, ``.dat``, ``.csv`` (PVsyst format), and ``.gz``
        (protobuf transfer file)
    horizon_file_path : str or None
        Path to a HOR horizon file, or None if not used
    pan_file_paths : list of str
        Paths to one or more PAN module specification files
    ond_file_paths : list of str
        Paths to one or more OND inverter files
    energy_calculation_inputs_file_path : str or None
        Path to the ``EnergyCalculationInputs.json`` file. Ignored when
        ``parse_energy_calc_inputs`` is False
    parse_energy_calc_inputs : bool, default True
        If False, the JSON inputs file is not read and an empty string is
        returned as the request content

    Returns
    -------
    tuple[str, list of tuple[str, IO[bytes]]]
        A ``(request_content, files)`` pair where ``request_content`` is the
        serialized JSON inputs string and ``files`` is a list of
        ``(field_name, file_handle)`` tuples for multipart upload

    Raises
    ------
    ImportError
        If the meteorological file has an unrecognized extension
    FileNotFoundError
        If any specified file path does not exist, or if PAN/OND paths are None
    """
    files = []
    stack = ExitStack()
    try:
        _logger.debug("Reading files from multiple paths")

        # Process the met data
        extension_met_data = pathlib.Path(meteorological_data_file_path).suffix.lower()

        if extension_met_data in (".tsv", ".dat"):
            validate_tsv_timestamps(meteorological_data_file_path)
            fh = pathlib.Path(meteorological_data_file_path).open("rb")
            stack.callback(fh.close)
            files.append(("tmyFile", fh))
        elif extension_met_data == ".csv":
            fh = pathlib.Path(meteorological_data_file_path).open("rb")
            stack.callback(fh.close)
            files.append(("pvSystStandardFormatFile", fh))
        elif extension_met_data == ".gz":
            fh = pathlib.Path(meteorological_data_file_path).open("rb")
            stack.callback(fh.close)
            files.append(("metDataTransferFile", fh))
        else:
            raise ValueError(
                f"Error: Meteorological data file has an unrecognized extension -> {extension_met_data}. "
                "Accepted are *.tsv, *.csv, *.dat, or *.gz."
            )

        _logger.debug("metFile = %s", meteorological_data_file_path)

        # Add the horizon file when provided
        if horizon_file_path is not None:
            if path_exists(horizon_file_path):
                _logger.debug("horizonFile = %s", horizon_file_path)
                fh = pathlib.Path(horizon_file_path).open("rb")
                stack.callback(fh.close)
                files.append(("horFile", fh))
            else:
                raise FileNotFoundError(f"Error: Path does not exist -> {horizon_file_path}")

        # Add any PAN files
        if pan_file_paths is None:
            raise FileNotFoundError("Error: Paths for PAN files were expected and are not defined.")
        else:
            for pan_file_path in pan_file_paths:
                if path_exists(pan_file_path):
                    _logger.debug("panFiles = %s", pan_file_path)
                    fh = pathlib.Path(pan_file_path).open("rb")
                    stack.callback(fh.close)
                    files.append(("panFiles", fh))
                else:
                    raise FileNotFoundError(f"Error: Path does not exist -> {pan_file_path}")

        # Add any OND files
        if ond_file_paths is None:
            raise FileNotFoundError("Error: Paths for OND files were expected and are not defined.")
        else:
            for ond_file_path in ond_file_paths:
                if path_exists(ond_file_path):
                    _logger.debug("ondFiles = %s", ond_file_path)
                    fh = pathlib.Path(ond_file_path).open("rb")
                    stack.callback(fh.close)
                    files.append(("ondFiles", fh))
                else:
                    raise FileNotFoundError(f"Error: Path does not exist -> {ond_file_path}")

        if parse_energy_calc_inputs:
            # Get the JSON energy calculation inputs from the input folder path
            with pathlib.Path(energy_calculation_inputs_file_path).open("rb") as file:
                _logger.debug("jsonFile = %s", energy_calculation_inputs_file_path)
                energy_calc_inputs = json.load(file)
                request_content = json.dumps(energy_calc_inputs)
        else:
            request_content = ""

        return request_content, files
    except Exception:
        stack.close()
        raise


def extract_poll_frequency(**kwargs) -> tuple[float, dict]:
    """
    Extract the async poll frequency from keyword arguments.

    Removes ``async_poll_time`` from ``kwargs`` if present and returns it
    as the poll frequency; otherwise returns the default from config.

    Parameters
    ----------
    **kwargs : dict
        Arbitrary keyword arguments. ``async_poll_time`` is consumed if present

    Returns
    -------
    tuple[float, dict]
        A ``(poll_frequency, remaining_kwargs)`` pair where ``poll_frequency``
        is the interval in seconds between status poll requests and
        ``remaining_kwargs`` is the input dict with ``async_poll_time`` removed
    """
    if "async_poll_time" in kwargs:
        poll_frequency = kwargs["async_poll_time"]
        del kwargs["async_poll_time"]
    else:
        poll_frequency = MODELCHAIN_ASYNC_POLL_TIME

    return poll_frequency, kwargs


def lowercase_keys_in_dict(obj: Any) -> Any:
    """
    Recursively convert all dictionary keys to lowercase.

    Standardizes key access when the input may have mixed capitalisation
    across different API versions.

    Parameters
    ----------
    obj : Any
        A dict, list of dicts, or any other value. Dicts are recursed into;
        lists are recursed element-wise; all other types are returned as-is

    Returns
    -------
    Any
        A new object with the same structure as ``obj`` but all dict keys
        lowercased
    """
    if isinstance(obj, dict):
        return {k.lower(): lowercase_keys_in_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [lowercase_keys_in_dict(i) for i in obj]
    return obj


def check_for_3d_files(request_content: str) -> bool:
    """
    Determine whether a request payload describes a 3D plant configuration.

    Inspects the serialized JSON for the presence of racks or trackers
    (3D indicators) and the absence of 2D layouts to decide which API
    endpoint should be used for the calculation.

    Parameters
    ----------
    request_content : str
        JSON-serialized energy calculation inputs payload

    Returns
    -------
    bool
        True if the payload describes a 3D plant (racks or trackers present,
        no 2D layouts); False otherwise
    """
    is_3d_file = False

    data = json.loads(request_content)
    data = lowercase_keys_in_dict(data)

    pv_plant = data["pvplant"]

    # Check for number of layout (only available in 2D calcs)
    try:
        layouts = len(pv_plant["transformers"][0]["inverters"][0]["layouts"])
    except Exception:
        layouts = 0
    # Check for number of racks or trackers (only available in 3D calcs)
    try:
        racks = bool(pv_plant["racks"])
    except Exception:
        racks = False
    try:
        trackers = bool(pv_plant["trackers"])
    except Exception:
        trackers = False

    if not layouts and (racks or trackers):
        is_3d_file = True

    return is_3d_file


def path_exists(path: str) -> bool:
    """
    Check if a given path exists.

    Parameters
    ----------
    path : str
        Path to a file or directory

    Returns
    -------
    bool
        True if the path exists, False otherwise
    """
    return pathlib.Path(path).exists()


def get_plant_info_string(plant_info: dict) -> str:
    """
    Format plant configuration metadata as a human-readable summary string.

    Parameters
    ----------
    plant_info : dict
        Plant information dictionary as returned by the API ``customStatus``
        payload. Keys are matched case-insensitively

    Returns
    -------
    str
        A formatted string such as ``"Plant stats: 3D Trackers, AC = 5.0 MW"``
        or ``"Plant stats: 2D Racks, AC = 2.5 MW (4 2D layouts)"``
    """
    # Make all keys in plant_info lowercase to avoid issues with different capitalisation in different versions of the API
    plant_info = lowercase_keys_in_dict(plant_info)

    is_plant_3D = plant_info["isplant3d"]
    is_trackers = plant_info["isplanttrackers"]
    number_of_2D_layouts = plant_info["numberof2dlayouts"]
    ac_capacity_in_mw = plant_info["accapacityofplantinmw"]
    output_string = "Plant stats: "
    if is_plant_3D:
        output_string += "3D"
    else:
        output_string += "2D"

    if is_trackers:
        output_string += " Trackers"
    else:
        output_string += " Racks"

    output_string += ", AC = " + str(ac_capacity_in_mw) + " MW"

    if not is_plant_3D:
        output_string += (
            " ("
            + str(number_of_2D_layouts)
            + " 2D layout"
            + ("s" if number_of_2D_layouts > 1 else "")
            + ")"
        )

    return output_string


def extract_part(part_name: str, custom_status_string: str) -> list[str] | None:
    """
    Extract completed and total task counts for a named part of an async calculation.

    Parameters
    ----------
    part_name : str
        Name of the calculation part to find, e.g. ``"Shading"``,
        ``"ModelChain"``, or ``"Post chunking"``
    custom_status_string : str
        The raw ``customStatus`` string returned by the API, containing
        dot-separated progress segments

    Returns
    -------
    list of str or None
        A two-element list ``[tasks_completed, tasks_total]`` if the part is
        found, or None if the part is absent or the string cannot be parsed
    """
    try:
        part_name = part_name + ": "
        parts = custom_status_string.split(".")
        for part in parts:
            part = part.strip()
            if part.startswith(part_name):
                tasks_part = part.split(part_name)[1]
                tasks_completed = tasks_part.split("/")[0].strip()
                tasks_total = tasks_part.split("/")[1].strip()
                return [tasks_completed, tasks_total]
        return None
    except Exception:
        return None


def summarize_custom_status_string(custom_status_string: str | None) -> str | None:
    """
    Summarize a v6 API async status string into a user-friendly progress message.

    v5-style or empty strings are returned unchanged. v6 strings containing
    ``"chunk"`` are parsed and condensed into a short human-readable phrase
    describing the current stage and progress.

    Parameters
    ----------
    custom_status_string : str or None
        The raw ``customStatus.Status`` string from the API polling response

    Returns
    -------
    str or None
        A concise progress message, or the original string if it cannot be
        parsed, or None if the input is None
    """
    if custom_status_string is None or "chunk" not in custom_status_string:
        # v5 style status string or empty
        return custom_status_string

    # Example custom status strings:
    #   "Running 0 chunks. Shading: 0/unknown tasks complete. ModelChain: 0/unknown tasks complete. Post chunking: 0/unknown tasks complete."
    #   "Running 1 chunks. Shading: 36/60 tasks complete. ModelChain: 0/46 tasks complete. Post chunking: 0/unknown tasks complete."
    #   "Running 1 chunks. Shading: 60/60 tasks complete. ModelChain: 4/46 tasks complete. Post chunking: 0/unknown tasks complete."
    #   "Running 1 chunks. Shading: 60/60 tasks complete. ModelChain: 46/46 tasks complete. Post chunking: 41/46 tasks complete."
    try:
        custom_status_string = custom_status_string.replace(" tasks complete", "")
        parts = custom_status_string.split(". ")
        running_part = parts[0] if parts else ""

        # extract the number of chunks from the running_part
        number_of_chunks = 0
        if running_part.startswith("Running "):
            try:
                number_of_chunks = int(running_part.split(" ")[1])
            except ValueError:
                number_of_chunks = 0

        if number_of_chunks == 0:
            return "Calculation pending..."

        shading_parts = extract_part("Shading", custom_status_string)
        model_chain_parts = extract_part("ModelChain", custom_status_string)
        post_chunking_parts = extract_part("Post chunking", custom_status_string)

        if (shading_parts is None) or (model_chain_parts is None) or (post_chunking_parts is None):
            return custom_status_string
        if (
            (len(shading_parts) != 2)
            or (len(model_chain_parts) != 2)
            or (len(post_chunking_parts) != 2)
        ):
            return custom_status_string

        if shading_parts[1] == "unknown":
            return "Calculation pending..."

        if shading_parts[0] != shading_parts[1]:
            return f"Running shading pre-processing ({shading_parts[0]}/{shading_parts[1]} tasks complete)"

        if model_chain_parts[1] == "unknown":
            return "Model chain calculation pending..."
        if model_chain_parts[0] != model_chain_parts[1]:
            return f"Running model chain calculation ({model_chain_parts[0]}/{model_chain_parts[1]} tasks complete)"

        if post_chunking_parts[1] == "unknown":
            return "Post-processing pending..."
        if post_chunking_parts[0] != post_chunking_parts[1]:
            return f"Running post-processing ({post_chunking_parts[0]}/{post_chunking_parts[1]} tasks complete)"

        return "Finishing up."

    except Exception:
        return custom_status_string


def format_timedelta(
    value: float | timedelta,
    time_format: str = "{days} days, {hours2}:{minutes2}:{seconds2}",
) -> str:
    """
    Format a duration value as a string using a named-placeholder template.

    Parameters
    ----------
    value : float or timedelta
        Duration to format. A ``timedelta`` is decomposed via its ``.seconds``
        and ``.days`` attributes; a numeric value is treated as total seconds
    time_format : str, default "{days} days, {hours2}:{minutes2}:{seconds2}"
        Format string with named placeholders. Available keys are:
        ``seconds``, ``seconds2``, ``minutes``, ``minutes2``, ``hours``,
        ``hours2``, ``days``, ``years``, ``seconds_total``, ``minutes_total``,
        ``hours_total``, ``days_total``, ``years_total``. Keys suffixed with
        ``2`` are zero-padded to two digits

    Returns
    -------
    str
        The formatted duration string
    """
    if hasattr(value, "seconds"):
        seconds = value.seconds + value.days * 24 * 3600
    else:
        seconds = int(value)

    seconds_total = seconds

    minutes = int(floor(seconds / 60))
    minutes_total = minutes
    seconds -= minutes * 60

    hours = int(floor(minutes / 60))
    hours_total = hours
    minutes -= hours * 60

    days = int(floor(hours / 24))
    days_total = days
    hours -= days * 24

    years = int(floor(days / 365))
    years_total = years
    days -= years * 365

    return time_format.format(
        **{
            "seconds": seconds,
            "seconds2": str(seconds).zfill(2),
            "minutes": minutes,
            "minutes2": str(minutes).zfill(2),
            "hours": hours,
            "hours2": str(hours).zfill(2),
            "days": days,
            "years": years,
            "seconds_total": seconds_total,
            "minutes_total": minutes_total,
            "hours_total": hours_total,
            "days_total": days_total,
            "years_total": years_total,
        }
    )
