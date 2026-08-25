"""
RCL (Renewable Component Library) — catalog search and file download functions.

Provides access to PV module (PAN) and inverter (OND) files hosted in the
DNV Renewable Component Library, using the same ``SF_API_KEY`` as the main
SolarFarmer API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from .api import RCLClient, SolarFarmerAPIError, _parse_error_body, map_http_error_to_message
from .logging import get_logger

if TYPE_CHECKING:
    # Only needed for type hints - keeps the `requests` import specific to api.py
    import requests

_logger = get_logger(__name__)

# Map snake_case Python params to camelCase API field names
_FIELD_MAP = {
    "p_nom": "pNom",
    "bifaciality_factor": "bifacialityFactor",
    "p_nom_conv": "pNomConv",
    "effic_max": "efficMax",
    "v_mpp_min": "vMppMin",
    "v_mpp_max": "vMppMax",
    "nb_mppt": "nbMppt",
    "lifecycle_status": "lifecycleStatus",
}

__all__ = [
    "RCLRateLimitInfo",
    "RCLModuleItemDict",
    "RCLInverterItemDict",
    "RCLModuleCatalogResponse",
    "RCLInverterCatalogResponse",
    "list_modules",
    "list_inverters",
    "download_file",
    "get_rate_limit_status",
]


# ---------------------------------------------------------------------------
# Response types
# ---------------------------------------------------------------------------


@dataclass
class RCLRateLimitInfo:
    """Rate limit information parsed from RCL API response headers.

    Attributes
    ----------
    remaining : int
        Number of downloads remaining in the current period.
    limit : int
        Total download allowance for the current period.
    reset_timestamp : int
        Unix timestamp when the quota resets.
    """

    remaining: int
    limit: int
    reset_timestamp: int

    @property
    def reset_datetime(self) -> datetime:
        """Reset time as a UTC-aware datetime."""
        return datetime.fromtimestamp(self.reset_timestamp, tz=timezone.utc)

    @property
    def usage_percent(self) -> float:
        """Percentage of the limit already consumed."""
        if self.limit == 0:
            return 100.0
        return ((self.limit - self.remaining) / self.limit) * 100

    def __str__(self) -> str:
        return f"{self.remaining}/{self.limit} downloads remaining (resets {self.reset_datetime})"


class RCLModuleItemDict(TypedDict, total=False):
    """Shape of a PV module item returned by ``list_modules()``.

    All keys are optional since ``output_parameter`` may request only a
    subset of fields. Items are plain ``dict`` instances at runtime; this
    ``TypedDict`` exists purely to give IDEs/type checkers autocomplete and
    key-name checking - no wrapping or conversion is performed.
    """

    componentId: str
    fileUuid: str
    filename: str
    manufacturer: str
    model: str
    pNom: float
    isc: float
    voc: float
    imp: float
    vmp: float
    muPmpReq: float
    nCelS: int
    nCelP: int
    bifacialityFactor: float
    technol: str
    lifecycleStatus: str


class RCLInverterItemDict(TypedDict, total=False):
    """Shape of an inverter item returned by ``list_inverters()``.

    All keys are optional since ``output_parameter`` may request only a
    subset of fields. Items are plain ``dict`` instances at runtime; this
    ``TypedDict`` exists purely to give IDEs/type checkers autocomplete and
    key-name checking - no wrapping or conversion is performed.
    """

    componentId: str
    fileUuid: str
    filename: str
    manufacturer: str
    model: str
    pNomConv: float
    pMaxOut: float
    efficMax: float
    efficEuro: float
    vMppMin: float
    vMppMax: float
    vAbsMax: float
    nbMppt: int
    transfo: str
    lifecycleStatus: str


class _RCLCatalogResponseBase(TypedDict):
    """Shared keys for paginated RCL catalog responses."""

    total: int
    skip: int
    top: int
    rate_limit: RCLRateLimitInfo | None


class RCLModuleCatalogResponse(_RCLCatalogResponseBase):
    """Paginated response from ``list_modules()``."""

    items: list[RCLModuleItemDict]


class RCLInverterCatalogResponse(_RCLCatalogResponseBase):
    """Paginated response from ``list_inverters()``."""

    items: list[RCLInverterItemDict]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_rate_limit(response: requests.Response) -> RCLRateLimitInfo:
    """
    Parse rate limit headers from an RCL response and log the current quota.

    Parameters
    ----------
    response : requests.Response
        A completed HTTP response from the RCL API.

    Returns
    -------
    RCLRateLimitInfo
        Parsed rate limit info.

    Raises
    ------
    SolarFarmerAPIError
        If any rate-limit header is missing or cannot be parsed as an integer.
    """
    required_headers = ("X-RateLimit-Remaining", "X-RateLimit-Limit", "X-RateLimit-Reset")
    missing = [h for h in required_headers if h not in response.headers]
    if missing:
        raise SolarFarmerAPIError(
            response.status_code,
            f"RCL response is missing rate-limit header(s): {', '.join(missing)}",
        )

    try:
        info = RCLRateLimitInfo(
            remaining=int(response.headers["X-RateLimit-Remaining"]),
            limit=int(response.headers["X-RateLimit-Limit"]),
            reset_timestamp=int(response.headers["X-RateLimit-Reset"]),
        )
    except (TypeError, ValueError) as err:
        raise SolarFarmerAPIError(
            response.status_code,
            f"RCL response has invalid rate-limit header value(s): {dict(response.headers)}",
        ) from err

    _logger.info(
        "RCL download quota: %d remaining (%.1f%% used). Resets %s",
        info.remaining,
        info.usage_percent,
        info.reset_datetime,
    )
    return info


def _raise_for_status(response: requests.Response) -> None:
    """
    Raise a ``SolarFarmerAPIError`` carrying the API's own error message.

    Mirrors the message/problem-details extraction done in
    ``Client._make_request`` so RCL errors read the same as other endpoints
    instead of a generic "HTTP <code>" string.

    Parameters
    ----------
    response : requests.Response
        A non-OK HTTP response from the RCL API.

    Raises
    ------
    SolarFarmerAPIError
        Always - this function only runs when the response is not OK.
    """
    text = response.text
    message = map_http_error_to_message(response.status_code, text, _parse_error_body(text))
    try:
        problem_details_json = response.json()
    except Exception:
        problem_details_json = None
    raise SolarFarmerAPIError(response.status_code, message, problem_details_json)


def _build_query_params(
    top: int = 25,
    skip: int = 0,
    order_by: str | None = None,
    order_dir: str = "ASC",
    output_parameter: list[str] | None = None,
    **filters: object,
) -> dict:
    """
    Build a query-parameter dict for an RCL catalog request.

    Filter keyword arguments use the pattern ``field=value``,
    ``field_contains=value``, ``field_gte=value``, etc., which are
    converted to the dot-notation form expected by the RCL API
    (e.g. ``filter.pNom.gte=400``).

    Parameters
    ----------
    top : int
        Page size. Default 25.
    skip : int
        Pagination offset. Default 0.
    order_by : str, optional
        Field name to sort by.
    order_dir : str
        Sort direction: ``"ASC"`` or ``"DESC"``. Default ``"ASC"``.
    output_parameter : list[str], optional
        Specific fields to return, reducing response payload size.
    **filters
        Filter keyword arguments. Supported operator suffixes:
        ``contains``, ``gt``, ``gte``, ``lt``, ``lte``. A bare field name
        (no suffix) is treated as an equality filter.

    Returns
    -------
    dict
        Query parameters dict ready to pass to ``requests``.
    """
    params: dict = {"top": top, "skip": skip}

    if order_by:
        params["orderBy"] = order_by
        params["orderDir"] = order_dir

    if output_parameter:
        params["outputParameter"] = ",".join(output_parameter)

    _operators = {"contains", "gt", "gte", "lt", "lte"}
    for key, value in filters.items():
        if value is None:
            continue
        if "." in key:
            # Raw dot-notation key (e.g. "filter.someNewField.gte") - a snake_case
            # Python identifier can never contain a literal dot, so this can only be
            # a pre-formatted key passed through **kwargs. Use it unchanged.
            params[key] = value
            continue
        parts = key.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in _operators:
            field, op = parts
            # Convert snake_case field to camelCase for API
            api_field = _FIELD_MAP.get(field, field)
            params[f"filter.{api_field}.{op}"] = value
        else:
            # Equality filter - also map field name
            api_field = _FIELD_MAP.get(key, key)
            params[f"filter.{api_field}"] = value

    return params


def _catalog_request(
    endpoint: str,
    query_params: dict,
    api_key: str | None,
) -> dict:
    """Execute an RCL catalog GET request and return a response dict.

    Returns a plain ``dict`` shaped like ``RCLModuleCatalogResponse`` or
    ``RCLInverterCatalogResponse`` depending on ``endpoint`` - callers narrow
    to the specific type via their own return annotation.
    """
    client = RCLClient()
    response = client.get(endpoint, params=query_params, api_key=api_key)

    if not response.ok:
        _raise_for_status(response)

    data = response.json()
    try:
        rate_limit = _extract_rate_limit(response)
    except SolarFarmerAPIError as err:
        # Rate-limit metadata is secondary to the catalog data itself - don't
        # fail the whole search over it, but don't hide the problem either.
        _logger.warning("Could not read RCL rate-limit headers: %s", err)
        rate_limit = None

    return {
        "items": data.get("items", []),
        "total": data.get("total", 0),
        "skip": data.get("skip", query_params.get("skip", 0)),
        "top": data.get("top", query_params.get("top", 25)),
        "rate_limit": rate_limit,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_modules(
    *,
    api_key: str | None = None,
    top: int = 25,
    skip: int = 0,
    order_by: str | None = None,
    order_dir: str = "ASC",
    output_parameter: list[str] | None = None,
    manufacturer: str | None = None,
    manufacturer_contains: str | None = None,
    model: str | None = None,
    model_contains: str | None = None,
    p_nom_gte: float | None = None,
    p_nom_lte: float | None = None,
    bifaciality_factor_gte: float | None = None,
    technol: str | None = None,
    lifecycle_status: str | None = None,
    verbose: bool = True,
    **kwargs: object,
) -> RCLModuleCatalogResponse:
    """
    List PV modules from the Renewable Component Library.

    Parameters
    ----------
    api_key : str, optional
        API token. Defaults to the ``SF_API_KEY`` environment variable.
    top : int
        Page size (maximum 10000). Default 25.
    skip : int
        Pagination offset. Default 0.
    order_by : str, optional
        Field to sort by (e.g. ``"pNom"``, ``"manufacturer"``).
    order_dir : str
        Sort direction: ``"ASC"`` or ``"DESC"``. Default ``"ASC"``.
    output_parameter : list[str], optional
        Fields to include in the response. Reduces payload size.
    manufacturer : str, optional
        Exact manufacturer name match.
    manufacturer_contains : str, optional
        Manufacturer name contains substring.
    model : str, optional
        Exact model name match.
    model_contains : str, optional
        Model name contains substring.
    p_nom_gte : float, optional
        Minimum nominal power (W).
    p_nom_lte : float, optional
        Maximum nominal power (W).
    bifaciality_factor_gte : float, optional
        Minimum bifaciality factor (use to filter for bifacial modules).
    technol : str, optional
        Technology type (e.g. ``"monoSi"``).
    lifecycle_status : str, optional
        Lifecycle status (e.g. ``"active"``).
    verbose : bool
        If ``True`` (default), prints a summary line after the request
        (e.g. ``"INFO: 42 modules found, retrieved 10."``). Set to ``False`` to suppress.
    **kwargs
        Additional filter parameters for forward compatibility.
        Use ``field_operator=value`` syntax or raw ``filter.field.op=value`` keys.

    Returns
    -------
    RCLModuleCatalogResponse
        Dict with keys ``items`` (list of module dicts, camelCase keys such as
        ``pNom``/``bifacialityFactor``), ``total``, ``skip``, ``top``, ``rate_limit``.

    Raises
    ------
    SolarFarmerAPIError
        If the API returns a non-2xx response.
    ValueError
        If no API key is found.

    Examples
    --------
    >>> result = sf.rcl.list_modules(
    ...     manufacturer_contains="Canadian",
    ...     p_nom_gte=600,
    ...     output_parameter=["pNom", "bifacialityFactor"],
    ...     top=10,
    ...     order_by="pNom",
    ...     order_dir="DESC",
    ... )
    >>> for item in result["items"]:
    ...     print(f"{item['manufacturer']} {item['model']}: {item.get('pNom')}W")
    """
    params = _build_query_params(
        top=top,
        skip=skip,
        order_by=order_by,
        order_dir=order_dir,
        output_parameter=output_parameter,
        manufacturer=manufacturer,
        manufacturer_contains=manufacturer_contains,
        model=model,
        model_contains=model_contains,
        p_nom_gte=p_nom_gte,
        p_nom_lte=p_nom_lte,
        bifaciality_factor_gte=bifaciality_factor_gte,
        technol=technol,
        lifecycle_status=lifecycle_status,
        **kwargs,
    )
    result = _catalog_request("catalog/modules", params, api_key)
    if verbose:
        print(f"INFO: {result['total']} modules found, retrieved {len(result['items'])}.")
    return result


def list_inverters(
    *,
    api_key: str | None = None,
    top: int = 25,
    skip: int = 0,
    order_by: str | None = None,
    order_dir: str = "ASC",
    output_parameter: list[str] | None = None,
    manufacturer: str | None = None,
    manufacturer_contains: str | None = None,
    model: str | None = None,
    model_contains: str | None = None,
    p_nom_conv_gte: float | None = None,
    p_nom_conv_lte: float | None = None,
    effic_max_gte: float | None = None,
    v_mpp_min_lte: float | None = None,
    v_mpp_max_gte: float | None = None,
    nb_mppt_gte: int | None = None,
    transfo: str | None = None,
    lifecycle_status: str | None = None,
    verbose: bool = True,
    **kwargs: object,
) -> RCLInverterCatalogResponse:
    """
    List inverters from the Renewable Component Library.

    Parameters
    ----------
    api_key : str, optional
        API token. Defaults to the ``SF_API_KEY`` environment variable.
    top : int
        Page size (maximum 10000). Default 25.
    skip : int
        Pagination offset. Default 0.
    order_by : str, optional
        Field to sort by (e.g. ``"pNomConv"``, ``"manufacturer"``).
    order_dir : str
        Sort direction: ``"ASC"`` or ``"DESC"``. Default ``"ASC"``.
    output_parameter : list[str], optional
        Fields to include in the response. Reduces payload size.
    manufacturer : str, optional
        Exact manufacturer name match.
    manufacturer_contains : str, optional
        Manufacturer name contains substring.
    model : str, optional
        Exact model name match.
    model_contains : str, optional
        Model name contains substring.
    p_nom_conv_gte : float, optional
        Minimum rated AC power (kW).
    p_nom_conv_lte : float, optional
        Maximum rated AC power (kW).
    effic_max_gte : float, optional
        Minimum maximum efficiency (fraction, e.g. ``0.98``).
    v_mpp_min_lte : float, optional
        Maximum lower MPPT voltage bound (V).
    v_mpp_max_gte : float, optional
        Minimum upper MPPT voltage bound (V).
    nb_mppt_gte : int, optional
        Minimum number of MPPT inputs.
    transfo : str, optional
        Transformer type (e.g. ``"transformerless"``).
    lifecycle_status : str, optional
        Lifecycle status (e.g. ``"active"``).
    verbose : bool
        If ``True`` (default), prints a summary line after the request
        (e.g. ``"INFO: 42 inverters found, retrieved 10."``). Set to ``False`` to suppress.
    **kwargs
        Additional filter parameters for forward compatibility.

    Returns
    -------
    RCLInverterCatalogResponse
        Dict with keys ``items`` (list of inverter dicts, camelCase keys such as
        ``pNomConv``/``efficMax``), ``total``, ``skip``, ``top``, ``rate_limit``.

    Raises
    ------
    SolarFarmerAPIError
        If the API returns a non-2xx response.
    ValueError
        If no API key is found.

    Examples
    --------
    >>> result = sf.rcl.list_inverters(
    ...     manufacturer_contains="SMA",
    ...     p_nom_conv_gte=100,
    ...     nb_mppt_gte=2,
    ...     top=10,
    ... )
    >>> for item in result["items"]:
    ...     print(f"{item['manufacturer']} {item['model']}")
    """
    params = _build_query_params(
        top=top,
        skip=skip,
        order_by=order_by,
        order_dir=order_dir,
        output_parameter=output_parameter,
        manufacturer=manufacturer,
        manufacturer_contains=manufacturer_contains,
        model=model,
        model_contains=model_contains,
        p_nom_conv_gte=p_nom_conv_gte,
        p_nom_conv_lte=p_nom_conv_lte,
        effic_max_gte=effic_max_gte,
        v_mpp_min_lte=v_mpp_min_lte,
        v_mpp_max_gte=v_mpp_max_gte,
        nb_mppt_gte=nb_mppt_gte,
        transfo=transfo,
        lifecycle_status=lifecycle_status,
        **kwargs,
    )
    result = _catalog_request("catalog/inverters", params, api_key)
    if verbose:
        print(f"INFO: {result['total']} inverters found, retrieved {len(result['items'])}.")
    return result


def download_file(
    file_uuid: str,
    filename: str,
    *,
    save_to_file: bool = True,
    directory_path: str | Path | None = None,
    file_path: str | Path | None = None,
    api_key: str | None = None,
) -> bytes:
    """
    Download a PAN or OND file from the Renewable Component Library.

    .. warning::
        Each call consumes one download against your monthly quota, even if
        the file was already downloaded before. Check
        :func:`get_rate_limit_status` before bulk downloads, and avoid calling
        this function more than once for the same file (e.g. by checking
        whether the destination path already exists yourself).

    Parameters
    ----------
    file_uuid : str
        The ``fileUuid`` value from a catalog query result item.
    filename : str
        Original filename (used when saving to a directory).
    save_to_file : bool
        Whether to write the content to disk. Default ``True``.
    directory_path : str or Path, optional
        Directory in which to save the file using ``filename``.
        Defaults to the current working directory when ``save_to_file=True``
        and ``file_path`` is not given.
    file_path : str or Path, optional
        Full destination path including filename. Overrides ``directory_path``.
    api_key : str, optional
        API token. Defaults to the ``SF_API_KEY`` environment variable.

    Returns
    -------
    bytes
        Raw file content, regardless of whether it was saved to disk.

    Raises
    ------
    SolarFarmerAPIError
        If the API returns a non-2xx response.
    ValueError
        If no API key is found.

    Examples
    --------
    >>> item = result["items"][0]
    >>> content = sf.rcl.download_file(
    ...     item["fileUuid"],
    ...     item["filename"],
    ...     directory_path="./equipment/",
    ... )
    """
    if file_path is not None:
        dest = Path(file_path)
    elif directory_path is not None:
        dest = Path(directory_path) / filename
    elif save_to_file:
        dest = Path.cwd() / filename
    else:
        dest = None

    client = RCLClient()
    response = client.get(f"catalog/{file_uuid}", api_key=api_key)

    if not response.ok:
        _raise_for_status(response)

    content = response.content
    try:
        _extract_rate_limit(response)
    except SolarFarmerAPIError as err:
        # The file was downloaded successfully - don't fail the download
        # just because the quota headers couldn't be read.
        _logger.warning("Could not read RCL rate-limit headers: %s", err)

    if save_to_file and dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        _logger.info("Saved RCL file to %s", dest)

    return content


def get_rate_limit_status(api_key: str | None = None) -> RCLRateLimitInfo:
    """
    Return current RCL rate limit status without consuming a download.

    Uses ``GET /catalog/modules?top=0``, which returns an empty page but
    includes the rate-limit headers.

    Parameters
    ----------
    api_key : str, optional
        API token. Defaults to the ``SF_API_KEY`` environment variable.

    Returns
    -------
    RCLRateLimitInfo
        Current rate limit status.

    Raises
    ------
    SolarFarmerAPIError
        If the API returns a non-2xx response or rate limit headers are missing.
    ValueError
        If no API key is found.

    Examples
    --------
    >>> status = sf.rcl.get_rate_limit_status()
    >>> print(f"{status.remaining}/{status.limit} downloads remaining")
    >>> print(f"Resets: {status.reset_datetime}")
    >>> if status.usage_percent > 80:
    ...     print("Warning: running low on downloads!")
    """
    client = RCLClient()
    response = client.get("catalog/modules", params={"top": 0}, api_key=api_key)

    if not response.ok:
        _raise_for_status(response)

    return _extract_rate_limit(response)
