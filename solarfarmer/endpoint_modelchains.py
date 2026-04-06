import pathlib
import time
from datetime import datetime
from typing import IO, Any

from .api import Client, Response, SolarFarmerAPIError, build_api_url
from .config import (
    MODELCHAIN_ASYNC_ENDPOINT_URL,
    MODELCHAIN_ASYNC_TIMEOUT_CONNECTION,
    MODELCHAIN_ENDPOINT_URL,
    MODELCHAIN_TIMEOUT,
)
from .endpoint_modelchains_utils import (
    check_for_3d_files,
    extract_poll_frequency,
    format_timedelta,
    get_plant_info_string,
    lowercase_keys_in_dict,
    parse_files_from_folder,
    parse_files_from_paths,
    path_exists,
    summarize_custom_status_string,
)
from .logging import get_logger
from .models import CalculationResults, ModelChainResponse
from .models._base import SolarFarmerBaseModel

_logger = get_logger("endpoint.modelchains")


def _validate_spec_ids_match_files(
    request_content: str,
    files: list[tuple[str, IO[bytes]]],
) -> None:
    """
    Validate that module and inverter spec IDs in the payload match uploaded file stems.

    The SolarFarmer API resolves ``moduleSpecificationID`` and ``inverterSpecID``
    by matching them against the filename stems of uploaded PAN and OND files
    (i.e. filename without extension). A mismatch causes a KeyNotFoundException
    on the server. This check catches the error client-side before the HTTP call.

    Parameters
    ----------
    request_content : str
        JSON-serialized API payload.
    files : list of tuple[str, IO[bytes]]
        Multipart upload files as ``(field_name, file_handle)`` pairs.

    Raises
    ------
    ValueError
        If a spec ID in the payload has no matching uploaded file.
    """
    import json

    pan_stems = {
        pathlib.Path(f.name).stem
        for field, f in files
        if field == "panFiles" and hasattr(f, "name")
    }
    ond_stems = {
        pathlib.Path(f.name).stem
        for field, f in files
        if field == "ondFiles" and hasattr(f, "name")
    }

    # Nothing to validate if no PAN/OND files were uploaded (e.g. inline payload)
    if not pan_stems and not ond_stems:
        return

    payload = json.loads(request_content)
    pv_plant = payload.get("pvPlant", {})

    for transformer in pv_plant.get("transformers", []):
        for inverter in transformer.get("inverters", []):
            if ond_stems:
                inv_id = inverter.get("inverterSpecID")
                if inv_id and inv_id not in ond_stems:
                    raise ValueError(
                        f"Inverter references spec ID '{inv_id}' but no matching OND file "
                        f"was uploaded. Available stems: {sorted(ond_stems)}"
                    )
            for layout in inverter.get("layouts") or []:
                if pan_stems:
                    mod_id = layout.get("moduleSpecificationID")
                    if mod_id and mod_id not in pan_stems:
                        raise ValueError(
                            f"Layout references module spec '{mod_id}' but no matching PAN file "
                            f"was uploaded. Available stems: {sorted(pan_stems)}"
                        )


def _resolve_request_payload(
    inputs_folder_path: str | pathlib.Path | None,
    energy_calculation_inputs_file_path: str | None,
    meteorological_data_file_path: str | None,
    horizon_file_path: str | None,
    pan_file_paths: list[str] | None,
    ond_file_paths: list[str] | None,
    plant_builder: str | SolarFarmerBaseModel | None,
) -> tuple[str, list[tuple[str, IO[bytes]]]]:
    """
    Resolve the API request payload and associated input files.

    Determines which input strategy was requested (folder, individual file
    paths, or a plant-builder object) and returns the JSON request body
    together with any binary files needed for the multipart upload.

    Parameters
    ----------
    inputs_folder_path : str or pathlib.Path or None
        Path to a folder containing all required inputs
    energy_calculation_inputs_file_path : str or None
        Explicit path to an ``EnergyCalculationInputs.json`` file
    meteorological_data_file_path : str or None
        Path to a solar resource / meteorological data file
    horizon_file_path : str or None
        Path to a horizon file
    pan_file_paths : list of str or None
        Paths to PAN module specification files
    ond_file_paths : list of str or None
        Paths to OND inverter files
    plant_builder : str or SolarFarmerBaseModel or None
        Pre-built payload as a model instance or JSON string

    Returns
    -------
    tuple[str, list[tuple[str, IO[bytes]]]]
        ``(request_content, files)`` where ``request_content`` is the
        JSON-serialized payload and ``files`` is a list of
        ``(field_name, file_handle)`` tuples for multipart upload

    Raises
    ------
    FileNotFoundError
        If ``inputs_folder_path`` is provided but does not exist
    ValueError
        If none of the three input strategies is provided
    """
    if inputs_folder_path is not None:
        # Option 1: the payload files are available in a folder
        if path_exists(inputs_folder_path):
            _logger.debug("Reading API files from: %s", inputs_folder_path)
            request_content, files = parse_files_from_folder(
                pathlib.Path(inputs_folder_path), energy_calculation_inputs_file_path
            )
        else:
            raise FileNotFoundError(f"Error: Path does not exist -> {inputs_folder_path}")
    elif energy_calculation_inputs_file_path is not None:
        # Option 2: the payload files are defined individually (in different folders)
        request_content, files = parse_files_from_paths(
            meteorological_data_file_path,
            horizon_file_path,
            pan_file_paths,
            ond_file_paths,
            energy_calculation_inputs_file_path,
        )
    elif plant_builder is not None:
        # Option 3: use the data from plant builder
        request_content, files = parse_files_from_paths(
            meteorological_data_file_path,
            horizon_file_path,
            pan_file_paths,
            ond_file_paths,
            energy_calculation_inputs_file_path=None,
            parse_energy_calc_inputs=False,
        )
        # Ensure the request is a JSON string
        if isinstance(plant_builder, SolarFarmerBaseModel):
            request_content = plant_builder.model_dump_json(by_alias=True, exclude_none=True)
        else:
            request_content = plant_builder
    else:
        raise ValueError(
            "No inputs provided. Supply one of: 'inputs_folder_path', "
            "'energy_calculation_inputs_file_path', or 'plant_builder'."
        )

    return request_content, files


def _handle_successful_response(
    response: Response,
    elapsed_time: float,
    project_id: str | None,
    inputs_folder_path: str | pathlib.Path | None,
    energy_calculation_inputs_file_path: str | None,
    outputs_folder_path: str | pathlib.Path | None,
    save_outputs: bool,
    print_summary: bool,
) -> CalculationResults | None:
    """
    Interpret a successful API response and return calculation results.

    Checks for async termination, extracts the ``runtimeStatus``, and
    either maps the response to a ``CalculationResults`` object (on
    ``"Completed"``) or logs relevant error information and returns None.

    Parameters
    ----------
    response : Response
        A successful API response (``response.success`` is True)
    elapsed_time : float
        Wall-clock seconds elapsed during the API call
    project_id : str or None
        Project identifier for result mapping
    inputs_folder_path : str or pathlib.Path or None
        Original inputs folder, forwarded to ``process_and_map_results``
    energy_calculation_inputs_file_path : str or None
        Original JSON inputs path, forwarded to ``process_and_map_results``
    outputs_folder_path : str or pathlib.Path or None
        Target folder for saved outputs
    save_outputs : bool
        Whether to persist outputs to disk
    print_summary : bool
        Whether to print a results summary

    Returns
    -------
    CalculationResults or None
        The mapped results on success, or None if the run was terminated,
        cancelled, or failed
    """
    # GET + "Terminated" on the async endpoint means the user cancelled
    if (
        response.method == "GET"
        and "modelchainasync" in response.url.lower()
        and response.data["runtimeStatus"] == "Terminated"
    ):
        _logger.info("Calculation terminated after %.1f seconds.", elapsed_time)
        return None

    # Extract runtime status (sync calls don't include one)
    runtime_status = response.data.get("runtimeStatus", "Completed")

    if runtime_status == "Completed":
        _logger.info(
            "SUCCESS: Calculation returned successfully (time taken: %.1f seconds)",
            elapsed_time,
        )
        return process_and_map_results(
            response.data,
            project_id,
            inputs_folder_path,
            energy_calculation_inputs_file_path,
            outputs_folder_path,
            save_outputs,
            print_summary,
        )

    # Non-completed status: Terminated, Cancelled, Failed, etc.
    output_message = response.data.get("output", None)
    if output_message is not None:
        _logger.error(
            "API CALL FAILED: Runtime status = %s. Reason given = %s (after %.1f seconds)",
            runtime_status,
            output_message,
            elapsed_time,
        )
    else:
        _logger.error(
            "API CALL FAILED: Runtime status = %s (after %.1f seconds)",
            runtime_status,
            elapsed_time,
        )
    # "Terminated" means the user explicitly cancelled via terminate_calculation() — not an error.
    # All other non-Completed statuses (Failed, Canceled, Unknown) are unexpected failures.
    if runtime_status == "Terminated":
        return None
    message = f"Async calculation ended with status '{runtime_status}'"
    if output_message:
        message += f": {output_message}"
    raise SolarFarmerAPIError(status_code=200, message=message)


def _log_api_failure(response: Response, elapsed_time: float) -> None:
    """
    Log details of a failed API response.

    Extracts and logs the URL, exception message, and any
    ``ProblemDetails`` JSON body (title, errors, detail) from the
    response.

    Parameters
    ----------
    response : Response
        A failed API response (``response.success`` is False).
    elapsed_time : float
        Wall-clock seconds elapsed during the API call.
    """
    _logger.error(
        "API CALL FAILED: API request %s failed (after %.1f seconds)",
        response.url,
        elapsed_time,
    )
    _logger.error("Failure message: %s", response.exception)
    json_response = response.problem_details_json
    if json_response is None:
        return
    if "title" in json_response:
        _logger.error("Title: %s", json_response["title"])
    errors = json_response.get("errors")
    if errors is not None:
        _logger.error("Errors:")
        for _errorKey, error_list in errors.items():
            for error in error_list:
                _logger.error(" - %s", error)
    detail = json_response.get("detail")
    if detail is not None:
        _logger.error("Detail: %s", detail)


def run_energy_calculation(
    inputs_folder_path: str | pathlib.Path | None = None,
    project_id: str | None = None,
    energy_calculation_inputs_file_path: str | None = None,
    meteorological_data_file_path: str | None = None,
    horizon_file_path: str | None = None,
    ond_file_paths: list[str] | None = None,
    pan_file_paths: list[str] | None = None,
    print_summary: bool = True,
    outputs_folder_path: str | pathlib.Path | None = None,
    save_outputs: bool = True,
    force_async_call: bool = False,
    api_version: str | None = "latest",
    plant_builder: str | SolarFarmerBaseModel | None = None,
    api_key: str | None = None,
    api_url: str | None = None,
    time_out: int | None = None,
    async_poll_time: float | None = None,
    **kwargs: Any,
) -> CalculationResults | None:
    """
    Runs the energy calculation by making a call to SolarFarmer
    ``ModelChain`` or ``ModelChainAsync`` endpoints.
    These endpoints perform the energy calculation of the SolarFarmer
    model. The ``ModelChain`` endpoint is used for 2D (simple
    shading model) calculations, while the ``ModelChainAsync`` endpoint is
    generally used for multi-year 2D calculations and 3D (full shading
    model) calculations.

    Parameters
    ----------
    inputs_folder_path : str or pathlib.Path, optional
        Path to a folder containing all required inputs. If provided,
        the function may resolve inputs (e.g., OND, PAN, horizon file,
        meteorological file, and calculation inputs) from this folder.
    project_id : str, optional
        Identifier for the project, used to group related runs and for
        billing
    energy_calculation_inputs_file_path : str, optional
        Path to an ``EnergyCalculationInputs.json`` file
        (as exported from the SolarFarmer desktop application)
    meteorological_data_file_path : str, optional
        Path to a solar resource file. Accepts Meteonorm `.dat`, TSV, a
        SolarFarmer desktop export (e.g.,
        ``MeteorologicalConditionsDatasetDto_Protobuf.gz``), or PVsyst
        standard format `.csv` files
    horizon_file_path : str, optional
        Path to a horizon file
    ond_file_paths : list of str, optional
        One or more paths to OND inverter files. At least one OND file
        is required if not provided via ``modelchain_payload`` or ``folder_path``
    pan_file_paths : list of str, optional
        One or more paths to PAN module specification files. At least
        one PAN file is required if not provided via ``modelchain_payload``
        or ``folder_path``
    print_summary : bool, optional
        If True, it will print out the summary of the energy calculation results.
        Default is True
    outputs_folder_path : str or pathlib.Path, optional
        Path to a folder that will contain all the requested outputs from
        the energy calculation. If the path does not exist, it will be
        created. If the path is not provided, an output folder named
        ``sf_outputs_<TIMESTAMP>`` will be created in the same directory
        than ``inputs_folder_path`` or ``energy_calculation_inputs_file_path``
    save_outputs : bool, optional
        If True, it will save the results from the API call in the
        ``outputs_folder_path`` or in a newly created folder ``sf_outputs_<TIMESTAMP>``.
        Default is True
    api_version : str or None, optional
        API version selector. Accepted values:
        - None          : returns `base_url` as-is
        - 'latest'      : uses the 'latest' version path
        - 'vX'          : where X is a positive integer, e.g., 'v6'
        Default is 'latest'
    force_async_call : bool, optional
        If True, forces the use of the asynchronous ModelChain endpoint
        even when the synchronous endpoint could be used.
        Default is False
    plant_builder : str or SolarFarmerBaseModel, optional
        The API payload. Accepts a ``SolarFarmerBaseModel`` instance (e.g.
        ``EnergyCalculationInputs``) or a pre-serialized JSON string
    api_key : str, optional
        SolarFarmer API key. If not provided, the ``SF_API_KEY`` environment
        variable is used
    api_url : str or None, optional
        If provided, this URL will be used as the base URL for the API call,
        overriding the default URL. When ``api_url`` is provided, ``api_version``
        is ignored. This is a per-call override of the ``SF_API_URL`` environment
        variable (see ``config.BASE_API_URL``). Must be a valid ``http`` or
        ``https`` URL.
    time_out : int, optional
        Request timeout in seconds, overriding the endpoint default
    async_poll_time : float, optional
        Polling interval in seconds between status checks for asynchronous
        calculations. Defaults to ``MODELCHAIN_ASYNC_POLL_TIME``
    **kwargs : Any
        Additional query parameters forwarded verbatim to the API request

    Returns
    -------
    CalculationResults or None
        An instance of CalculationResults with the API results for the project,
        or None if the calculation was terminated or cancelled

    Raises
    ------
    SolarFarmerAPIError
        If the API returns a non-2xx response. The exception carries
        ``status_code``, ``message``, and the full ``problem_details`` body.
    """

    # Fold explicit API params into kwargs for the downstream request functions
    if api_key is not None:
        kwargs["api_key"] = api_key
    if time_out is not None:
        kwargs["time_out"] = time_out
    if async_poll_time is not None:
        kwargs["async_poll_time"] = async_poll_time

    # 1. Resolve the request payload and input files
    files: list[tuple[str, IO[bytes]]] = []
    try:
        request_content, files = _resolve_request_payload(
            inputs_folder_path,
            energy_calculation_inputs_file_path,
            meteorological_data_file_path,
            horizon_file_path,
            pan_file_paths,
            ond_file_paths,
            plant_builder,
        )

        # 2. Dispatch to the appropriate endpoint
        _validate_spec_ids_match_files(request_content, files)
        are_files_3d = check_for_3d_files(request_content)
        start_time = time.time()
        if force_async_call or are_files_3d:
            endpoint_url = MODELCHAIN_ASYNC_ENDPOINT_URL
            response = modelchain_async_call(
                endpoint_url, api_version, api_url, request_content, files, project_id, **kwargs
            )
        else:
            endpoint_url = MODELCHAIN_ENDPOINT_URL
            response = modelchain_call(
                endpoint_url, api_version, api_url, request_content, files, project_id, **kwargs
            )
    finally:
        for _, fh in files:
            fh.close()

    # 3. Interpret the response
    elapsed_time = time.time() - start_time
    if response.success:
        return _handle_successful_response(
            response,
            elapsed_time,
            project_id,
            inputs_folder_path,
            energy_calculation_inputs_file_path,
            outputs_folder_path,
            save_outputs,
            print_summary,
        )
    else:
        _log_api_failure(response, elapsed_time)
        raise SolarFarmerAPIError(
            status_code=response.code,
            message=response.exception or "API request failed",
            problem_details=response.problem_details_json,
        )


def modelchain_call(
    endpoint_url: str,
    api_version: str,
    api_url: str | None,
    request_content: str,
    files: list[tuple[str, IO[bytes]]],
    project_id: str,
    **kwargs,
) -> Response:
    """
    Submit a synchronous POST request to the ModelChain (2D) endpoint.

    Parameters
    ----------
    endpoint_url : str
        Relative endpoint path for the ModelChain API.
    api_version : str
        API version string passed to ``build_api_url``.
    api_url : str | None
        If provided, this URL will be used as the base URL for the API call,
        overriding the default URL built by ``build_api_url``.
    request_content : str
        JSON-serialized energy calculation inputs payload.
    files : list of tuple[str, IO[bytes]]
        Multipart file tuples of the form ``(field_name, file_handle)``.
        Handles are owned by the caller; this function does not close them.
    project_id : str
        Project identifier forwarded as a query parameter.
    **kwargs : dict
        Additional parameters forwarded to the HTTP client.

    Returns
    -------
    Response
        The API response object
    """
    # Build the URL and create Client
    base_url = api_url if api_url is not None else build_api_url(api_version)
    client = Client(
        base_url=base_url,
        endpoint=endpoint_url,
        response_type=Response,
        timeout=MODELCHAIN_TIMEOUT,
    )

    # Print start time
    start_time = datetime.now()
    _logger.info(
        "Making API call to ModelChain (2D) endpoint: %s\nStart time = %s",
        client.url,
        start_time.strftime("%d-%m-%Y %H:%M:%S"),
    )

    # Set the POST request
    response = client.post(
        {"projectId": project_id, **kwargs}, request_content=request_content, files=files
    )

    return response


def modelchain_async_call(
    endpoint_url: str,
    api_version: str,
    api_url: str | None,
    request_content: str,
    files: list[tuple[str, IO[bytes]]],
    project_id: str,
    **kwargs,
) -> Response:
    """
    Submit a POST to the ModelChainAsync endpoint and poll until completion.

    Initiates the asynchronous calculation with a POST request, retrieves the
    instance ID from the response, then polls the GET endpoint at a configurable
    interval until the job reaches a terminal state.

    Parameters
    ----------
    endpoint_url : str
        Relative endpoint path for the ModelChainAsync API.
    api_version : str
        API version string passed to ``build_api_url``.
    api_url : str | None
        If provided, this URL will be used as the base URL for the API call,
        overriding the default URL built by ``build_api_url``.
    request_content : str
        JSON-serialized energy calculation inputs payload.
    files : list of tuple[str, IO[bytes]]
        Multipart file tuples of the form ``(field_name, file_handle)``.
        Handles are owned by the caller; this function does not close them.
    project_id : str
        Project identifier forwarded as a query parameter.
    **kwargs : dict
        Additional parameters forwarded to the HTTP client. The special key
        ``async_poll_time`` sets the polling interval in seconds and is
        consumed before forwarding.

    Returns
    -------
    Response
        The final GET response when ``runtimeStatus`` reaches a terminal state,
        or the POST response if it fails or an exception occurs during polling
    """

    poll_frequency, kwargs = extract_poll_frequency(**kwargs)

    # Build the URL and create Client
    base_url = api_url if api_url is not None else build_api_url(api_version)
    client = Client(
        base_url=base_url,
        endpoint=endpoint_url,
        response_type=Response,
        timeout=MODELCHAIN_ASYNC_TIMEOUT_CONNECTION,
    )

    # Print start time
    start_time = datetime.now()
    _logger.info(
        "Making API call to ModelChainAsync (3D) endpoint: %s\nStart time = %s",
        client.url,
        start_time.strftime("%d-%m-%Y %H:%M:%S"),
    )

    # Initiate the POST request
    response_from_post = client.post(
        {"projectId": project_id, **kwargs}, request_content=request_content, files=files
    )

    # Return failed POST call if it is the case
    if response_from_post.success is False:
        return response_from_post

    # Retrieve the Instance ID from the response from the POST request
    instance_id = response_from_post.data["id"]
    _logger.info("Instance ID returned = %s", instance_id)

    # Send the GET request in a loop, giving the instance ID,
    # retrieving the status of the calculation
    seconds_per_poll_check = poll_frequency
    iteration_number = 1
    is_finished = False
    was_successful = False
    have_written_plant_info = False
    while not is_finished:
        try:
            response_from_get = client.get(params={"InstanceId": instance_id, **kwargs})

            if response_from_get.success:
                json_response_text = response_from_get.data
                custom_status_string = "Custom status not received"
                progress_string = "No progress returned"
                if "customStatus" in json_response_text:
                    custom_status = json_response_text["customStatus"]
                    if custom_status is not None:
                        if "PlantInfo" in custom_status:
                            if not have_written_plant_info:
                                plant_info = custom_status["PlantInfo"]
                                if plant_info is not None:
                                    _logger.info("%s", get_plant_info_string(plant_info))
                                    have_written_plant_info = True
                                else:
                                    _logger.debug("Plant info not received this time")
                        custom_status_string = custom_status["Status"]
                        if "CalculationProgress" in custom_status:
                            calculation_progress = custom_status["CalculationProgress"]
                            shading_progress = 0
                            overall_progress = 0
                            model_chain_progress = 0
                            if calculation_progress is not None:
                                calculation_progress = lowercase_keys_in_dict(calculation_progress)
                                if (
                                    "shadingprogress" in calculation_progress
                                    and "modelchainprogress" in calculation_progress
                                    and "overallprogress" in calculation_progress
                                ):
                                    shading_progress = float(
                                        calculation_progress["shadingprogress"]
                                    )
                                    model_chain_progress = float(
                                        calculation_progress["modelchainprogress"]
                                    )
                                    overall_progress = float(
                                        calculation_progress["overallprogress"]
                                    )
                                    progress_string = f"[Shading: {shading_progress * 100.0:.1f}%, ModelChain: {model_chain_progress * 100.0:.1f}%, Overall: {overall_progress * 100.0:.1f}%]"
                                else:
                                    # no recognized progress keys - just log the string
                                    _logger.debug("Unrecognized progress: %s", calculation_progress)
                            parts = [
                                f"Shading: {shading_progress * 100.0:.1f}%",
                                f"ModelChain: {model_chain_progress * 100.0:.1f}%",
                                f"Overall: {overall_progress * 100.0:.1f}%",
                            ]
                            progress_string = "[" + ", ".join(parts) + "]"
                else:
                    custom_status_string = "Custom status not received"

                runtime_status = json_response_text["runtimeStatus"]

                # Estimate current run time
                time_since_start = datetime.now() - start_time

                summarized_custom_status = summarize_custom_status_string(custom_status_string)

                # Log status
                _logger.info(
                    "%2d: Time: %s \tRun status: %s \tCustom status: %s  %s",
                    iteration_number,
                    format_timedelta(time_since_start, "{hours_total}:{minutes2}:{seconds2}"),
                    runtime_status,
                    summarized_custom_status,
                    progress_string,
                )

                if runtime_status == "Completed":
                    is_finished = True
                    was_successful = True
                elif (
                    runtime_status == "Failed"
                    or runtime_status == "Canceled"
                    or runtime_status == "Terminated"
                    or runtime_status == "Unknown"
                ):
                    is_finished = True
                    was_successful = False
            else:
                _logger.error("API request %s failed.", client.base_url)
                is_finished = True
                was_successful = False
                return response_from_get

        except Exception:
            _logger.exception("Exception thrown in the script")
            return response_from_post

        # wait as for the poll frequency
        time.sleep(seconds_per_poll_check)
        iteration_number += 1

    if was_successful:
        return response_from_get

    else:
        if runtime_status == "Terminated":
            reason_string = json_response_text["output"]
            _logger.error("The calculation was terminated. Reason given = %s", reason_string)
        else:
            _logger.error("The calculation was not successful. Runtime status = %s", runtime_status)
        return response_from_get


def process_and_map_results(
    data: dict[str, Any],
    project_id: str,
    inputs_folder_path: str | None,
    energy_calculation_inputs_file_path: str | None,
    outputs_folder_path: str | None,
    save_outputs: bool,
    print_summary: bool,
) -> CalculationResults:
    """
    Process the API response and map them to a ``CalculationResults`` object.

    This function accepts the API response payload (already parsed into a
    dictionary), ensures an outputs folder is available when requested,
    converts the response into a ``ModelChainResponse``, and then maps it
    to a ``CalculationResults`` domain object. When ``save_outputs`` is
    True, it creates (or reuses) an outputs subfolder, either from the
    provided ``outputs_folder_path`` or by deriving a timestamped folder
    name under the inputs location. Optionally prints a summary of
    the energy yield results of the energy calculation.

    Parameters
    ----------
    data : Dict[str, Any]
        Parsed JSON response from the ModelChain API. This should contain
        the fields required by ``ModelChainResponse.from_response``
    project_id : str
        The project ID given by the user for this API calculation
    inputs_folder_path: str
        Folder with the input data. It will be used to create the
        outputs subfolder when ``outputs_folder_path`` is not provided
    outputs_folder_path : str
        Target folder where outputs will be written when ``save_outputs``
        is True. If None and ``save_outputs`` is True, a timestamped
        subfolder will be created based on the inputs context (see Notes).
        When ``save_outputs`` is False, this value is ignored
    save_outputs : bool
        Whether to persist derived artifacts (e.g., files, figures) to
        disk. If True, the outputs folder is created as needed
    print_summary : bool
        If True, prints a short summary of the mapped results

    Returns
    -------
    CalculationResults
        A results object produced from the API response via
        ``ModelChainResponse.from_response`` and
        ``CalculationResults.from_modelchain_response``

    Raises
    ------
    ValueError
        If ``data`` is missing required fields for mapping
    OSError
        If the outputs folder cannot be created (e.g., permissions)
    FileNotFoundError
        If a derived path depends on an inputs location that does not
        exist (only when ``save_outputs`` is True and no explicit
        ``outputs_folder_path`` is provided)

    Notes
    -----
    - When ``save_outputs`` is True and ``outputs_folder_path`` is None,
      a subfolder named ``sf_outputs_YYYYMMDD_HHMMSS`` is created either
      under ``inputs_folder_path`` (if available) or alongside the input
      JSON file (``energy_calculation_inputs_file_path``)
    - ``ModelChainResponse.from_response`` is expected to validate and
      normalize ``data``; ensure the API payload adheres to the expected
      schema before calling this function

    """
    if save_outputs:
        # First, make sure the subfolder for the outputs exists, creating it if not
        if outputs_folder_path is not None:
            # Subfolder path created, creating it if not
            outputs_folder_path = pathlib.Path(outputs_folder_path)
            outputs_folder_path.mkdir(parents=True, exist_ok=True)
        else:
            output_subfolder = "sf_outputs_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            if inputs_folder_path is not None:
                # Define it in inputs folder
                outputs_folder_path = pathlib.Path(inputs_folder_path) / output_subfolder
            elif energy_calculation_inputs_file_path is not None:
                # Define it in the location of the input JSON file
                outputs_folder_path = (
                    pathlib.Path(energy_calculation_inputs_file_path).parent / output_subfolder
                )
            else:
                # No context to define the outputs folder, just create it in the current location
                outputs_folder_path = pathlib.Path(output_subfolder)
            # Create the outputs folder
            outputs_folder_path.mkdir(parents=True, exist_ok=True)
    else:
        outputs_folder_path = None

    # Handle async response unwrapping if needed
    # Async (3D) calculations return {instanceId, runtimeStatus, output, ...}
    # while sync calculations return the results directly
    if data.get("instanceId") is not None and data.get("runtimeStatus") == "Completed":
        # Extract the actual results from the 'output' field
        data = data.get("output", {})

    # Map API response to ModelChainResponse container
    response_results = ModelChainResponse.from_response(data, project_id)

    # Convert ModelChainResponse object to CalculationResults object
    results = CalculationResults.from_modelchain_response(
        response_results, outputs_folder_path, save_outputs, print_summary
    )

    return results
