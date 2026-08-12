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
from typing import TypedDict

import requests

from .api import RCLClient, SolarFarmerAPIError
from .config import RCL_RATE_LIMIT_WARNING_THRESHOLD
from .logging import get_logger

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
    "RCLCatalogItem",
    "RCLCatalogResponse",
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

    @property
    def is_low(self) -> bool:
        """``True`` if remaining downloads are below the warning threshold."""
        return self.remaining < (self.limit * RCL_RATE_LIMIT_WARNING_THRESHOLD)

    def __str__(self) -> str:
        return f"{self.remaining}/{self.limit} downloads remaining (resets {self.reset_datetime})"


@dataclass
class RCLCatalogItem:
    """Typed wrapper for an RCL catalog item providing IDE-friendly attribute access.

    This class wraps the raw dict returned by the RCL API, providing typed
    properties with consistent snake_case naming. The original dict is accessible
    via the ``raw`` attribute for fields not explicitly mapped.

    Attributes
    ----------
    raw : dict
        The original API response dict with all fields.

    Properties (always available)
    -----------------------------
    file_uuid : str
        Unique identifier for downloading the file. Aliases: ``fileUuid``.
    filename : str
        Original filename (e.g., ``"CS7N-715TB-AG.PAN"``).
    manufacturer : str
        Equipment manufacturer name.
    model : str
        Equipment model name.
    component_id : str
        RCL component identifier. Aliases: ``componentId``.

    Properties (modules, if requested)
    ----------------------------------
    p_nom : float | None
        Nominal power in watts. Aliases: ``pNom``.
    bifaciality_factor : float | None
        Bifaciality factor (0-1). Aliases: ``bifacialityFactor``.
    technol : str | None
        Technology type (e.g., ``"monoSi"``).

    Properties (inverters, if requested)
    ------------------------------------
    p_nom_conv : float | None
        Rated AC power in kW. Aliases: ``pNomConv``.
    effic_max : float | None
        Maximum efficiency. Aliases: ``efficMax``.
    v_mpp_min : float | None
        Minimum MPPT voltage in V. Aliases: ``vMppMin``.
    v_mpp_max : float | None
        Maximum MPPT voltage in V. Aliases: ``vMppMax``.
    nb_mppt : int | None
        Number of MPPT inputs. Aliases: ``nbMppt``.

    Examples
    --------
    >>> result = sf.rcl.list_modules(manufacturer_contains="Canadian", top=1)
    >>> item = RCLCatalogItem(result["items"][0])
    >>> print(item.file_uuid)      # IDE autocomplete works
    >>> print(item.manufacturer)
    >>> content = sf.rcl.download_file(item.file_uuid, item.filename)
    """

    raw: dict

    # --- Always available ---

    @property
    def file_uuid(self) -> str:
        """File UUID for downloading. Aliases: ``fileUuid``."""
        return self.raw.get("fileUuid", "")

    @property
    def fileUuid(self) -> str:
        """Alias for :attr:`file_uuid` (camelCase)."""
        return self.file_uuid

    @property
    def filename(self) -> str:
        """Original filename (e.g., ``"module.PAN"``)."""
        return self.raw.get("filename", "")

    @property
    def manufacturer(self) -> str:
        """Equipment manufacturer name."""
        return self.raw.get("manufacturer", "")

    @property
    def model(self) -> str:
        """Equipment model name."""
        return self.raw.get("model", "")

    @property
    def component_id(self) -> str:
        """RCL component identifier. Aliases: ``componentId``."""
        return self.raw.get("componentId", "")

    @property
    def componentId(self) -> str:
        """Alias for :attr:`component_id` (camelCase)."""
        return self.component_id

    # --- Module fields ---

    @property
    def p_nom(self) -> float | None:
        """Nominal power in watts. Aliases: ``pNom``."""
        return self.raw.get("pNom")

    @property
    def pNom(self) -> float | None:
        """Alias for :attr:`p_nom` (camelCase)."""
        return self.p_nom

    @property
    def bifaciality_factor(self) -> float | None:
        """Bifaciality factor (0-1). Aliases: ``bifacialityFactor``."""
        return self.raw.get("bifacialityFactor")

    @property
    def bifacialityFactor(self) -> float | None:
        """Alias for :attr:`bifaciality_factor` (camelCase)."""
        return self.bifaciality_factor

    @property
    def technol(self) -> str | None:
        """Technology type (e.g., ``"monoSi"``)."""
        return self.raw.get("technol")

    # --- Inverter fields ---

    @property
    def p_nom_conv(self) -> float | None:
        """Rated AC power in kW. Aliases: ``pNomConv``."""
        return self.raw.get("pNomConv")

    @property
    def pNomConv(self) -> float | None:
        """Alias for :attr:`p_nom_conv` (camelCase)."""
        return self.p_nom_conv

    @property
    def effic_max(self) -> float | None:
        """Maximum efficiency. Aliases: ``efficMax``."""
        return self.raw.get("efficMax")

    @property
    def efficMax(self) -> float | None:
        """Alias for :attr:`effic_max` (camelCase)."""
        return self.effic_max

    @property
    def v_mpp_min(self) -> float | None:
        """Minimum MPPT voltage in V. Aliases: ``vMppMin``."""
        return self.raw.get("vMppMin")

    @property
    def vMppMin(self) -> float | None:
        """Alias for :attr:`v_mpp_min` (camelCase)."""
        return self.v_mpp_min

    @property
    def v_mpp_max(self) -> float | None:
        """Maximum MPPT voltage in V. Aliases: ``vMppMax``."""
        return self.raw.get("vMppMax")

    @property
    def vMppMax(self) -> float | None:
        """Alias for :attr:`v_mpp_max` (camelCase)."""
        return self.v_mpp_max

    @property
    def nb_mppt(self) -> int | None:
        """Number of MPPT inputs. Aliases: ``nbMppt``."""
        return self.raw.get("nbMppt")

    @property
    def nbMppt(self) -> int | None:
        """Alias for :attr:`nb_mppt` (camelCase)."""
        return self.nb_mppt

    # --- Dict-like access ---

    def __getitem__(self, key: str) -> object:
        """Allow dict-style access: ``item["fileUuid"]``."""
        return self.raw[key]

    def get(self, key: str, default: object = None) -> object:
        """Allow dict-style get: ``item.get("pNom")``."""
        return self.raw.get(key, default)

    def __contains__(self, key: str) -> bool:
        """Allow ``"fileUuid" in item``."""
        return key in self.raw

    def keys(self):
        """Return dict keys."""
        return self.raw.keys()

    def values(self):
        """Return dict values."""
        return self.raw.values()

    def items(self):
        """Return dict items."""
        return self.raw.items()


class RCLCatalogResponse(TypedDict):
    """Paginated response from an RCL catalog query.

    Keys
    ----
    items : list[dict]
        Raw item dicts returned by the API. Fields vary by query and user
        permissions. Common fields include ``componentId``, ``fileUuid``,
        ``filename``, ``manufacturer``, ``model``.
    total : int
        Total number of records matching the query (before pagination).
    skip : int
        Number of records skipped (pagination offset used).
    top : int
        Page size used in the request.
    rate_limit : RCLRateLimitInfo or None
        Rate limit status parsed from response headers, or ``None`` if headers
        were absent or unparseable.
    """

    items: list[dict]
    total: int
    skip: int
    top: int
    rate_limit: RCLRateLimitInfo | None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_rate_limit(response: requests.Response) -> RCLRateLimitInfo | None:
    """
    Parse rate limit headers from an RCL response and warn if quota is low.

    Parameters
    ----------
    response : requests.Response
        A completed HTTP response from the RCL API.

    Returns
    -------
    RCLRateLimitInfo or None
        Parsed rate limit info, or ``None`` if headers are missing or invalid.
    """
    try:
        info = RCLRateLimitInfo(
            remaining=int(response.headers.get("X-RateLimit-Remaining", 0)),
            limit=int(response.headers.get("X-RateLimit-Limit", 0)),
            reset_timestamp=int(response.headers.get("X-RateLimit-Reset", 0)),
        )
        if info.is_low:
            _logger.warning(
                "RCL download quota low: %d/%d remaining (%.1f%% used). Resets %s",
                info.remaining,
                info.limit,
                info.usage_percent,
                info.reset_datetime,
            )
        return info
    except (TypeError, ValueError):
        return None


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
) -> RCLCatalogResponse:
    """Execute an RCL catalog GET request and return a typed response dict."""
    client = RCLClient()
    response = client.get(endpoint, params=query_params, api_key=api_key)

    if not response.ok:
        raise SolarFarmerAPIError(
            response.status_code,
            f"RCL catalog request failed: HTTP {response.status_code}",
        )

    data = response.json()
    rate_limit = _extract_rate_limit(response)

    return RCLCatalogResponse(
        items=data.get("items", []),
        total=data.get("total", 0),
        skip=data.get("skip", query_params.get("skip", 0)),
        top=data.get("top", query_params.get("top", 25)),
        rate_limit=rate_limit,
    )


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
) -> RCLCatalogResponse:
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
    RCLCatalogResponse
        Dict with keys ``items``, ``total``, ``skip``, ``top``, ``rate_limit``.

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
) -> RCLCatalogResponse:
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
        Minimum rated AC power (W).
    p_nom_conv_lte : float, optional
        Maximum rated AC power (W).
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
    RCLCatalogResponse
        Dict with keys ``items``, ``total``, ``skip``, ``top``, ``rate_limit``.

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
    ...     p_nom_conv_gte=100000,
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
    use_cache: bool = True,
    api_key: str | None = None,
) -> bytes:
    """
    Download a PAN or OND file from the Renewable Component Library.

    If the file already exists at the target location and ``use_cache=True``,
    the local file is returned without making an API call (saving your quota).

    .. warning::
        Each download counts against your monthly quota. Check
        :func:`get_rate_limit_status` before bulk downloads.

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
    use_cache : bool
        If ``True`` (default) and the file already exists at the target path,
        return its contents without downloading. Set to ``False`` to force
        re-download.
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
    # Determine destination path for cache check
    if file_path is not None:
        dest = Path(file_path)
    elif directory_path is not None:
        dest = Path(directory_path) / filename
    elif save_to_file:
        dest = Path.cwd() / filename
    else:
        dest = None

    # Check local cache
    if use_cache and dest is not None and dest.exists():
        _logger.info("Using cached file: %s (skipping download)", dest)
        return dest.read_bytes()

    # Download from API
    client = RCLClient()
    response = client.get(f"catalog/{file_uuid}", api_key=api_key)

    if not response.ok:
        raise SolarFarmerAPIError(
            response.status_code,
            f"RCL file download failed: HTTP {response.status_code}",
        )

    content = response.content
    _extract_rate_limit(response)

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
    >>> if status.is_low:
    ...     print("Warning: running low on downloads!")
    """
    client = RCLClient()
    response = client.get("catalog/modules", params={"top": 0}, api_key=api_key)

    if not response.ok:
        raise SolarFarmerAPIError(
            response.status_code,
            f"RCL rate limit check failed: HTTP {response.status_code}",
        )

    rate_limit = _extract_rate_limit(response)
    if rate_limit is None:
        raise SolarFarmerAPIError(500, "Could not parse rate limit headers from RCL response")
    return rate_limit
