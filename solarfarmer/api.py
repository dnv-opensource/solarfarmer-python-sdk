import copy
import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from .__version__ import __version__
from .config import (
    API_TOKEN,
    BASE_API_URL,
    GENERAL_TIMEOUT,
    SF_PORTAL_URL,
)


@dataclass
class Response:
    """Class to handle API response from the SolarFarmer API"""

    code: int
    url: str
    data: Any | None
    success: bool
    method: str
    exception: str | None = None
    problem_details_json: dict | None = None

    def __repr__(self) -> str:
        return f"status code={self.code}, url={self.url}, method={self.method}"


class SolarFarmerAPIError(Exception):
    """Raised when the SolarFarmer API returns a non-2xx response.

    Attributes
    ----------
    status_code : int
        HTTP status code returned by the API.
    message : str
        Human-readable error message extracted from the response.
    problem_details : dict or None
        Full ProblemDetails JSON body from the API, if available.
        May contain ``title``, ``detail``, and ``errors`` fields.

    Examples
    --------
    >>> import solarfarmer as sf
    >>> try:
    ...     result = sf.run_energy_calculation(inputs_folder_path="my_inputs/")
    ... except sf.SolarFarmerAPIError as e:
    ...     logger.error("API error %s: %s", e.status_code, e)
    ...     raise
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        problem_details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.problem_details = problem_details

    def __str__(self) -> str:
        base = f"HTTP {self.status_code}: {self.message}"
        if self.problem_details:
            detail = self.problem_details.get("detail")
            if detail:
                base += f" — {detail}"
        return base


class Client:
    """Handles all API requests for the different endpoints."""

    def __init__(
        self,
        base_url: str,
        endpoint: str,
        response_type: Response,
        timeout: int = GENERAL_TIMEOUT,
    ) -> None:
        """
        Parameters
        ----------
        base_url : str
            The base URL to the SolarFarmer API
        endpoint : str
            One of the SolarFarmer API endpoints (``About``, ``Service``,
            ``ModelChain``, ``ModelChainAsync``, ``TerminateModelChainAsync``)
        response_type : Response
            The ``Response`` class (or a compatible subclass) used to
            construct response objects from API call results
        timeout : int, optional
            Default timeout in seconds for requests made by this client.
            Can be overridden per-request via a ``time_out`` key in params.
            Defaults to ``GENERAL_TIMEOUT``.
        """
        self.base_url = base_url
        self.endpoint = endpoint
        self.response_class = response_type
        self.timeout = timeout
        self.url = self.make_url()

    @staticmethod
    def _check_params(params: dict) -> tuple[dict, str]:
        """
        Run basic checks on the parameters passed to the HTTP request.

        Parameters
        ----------
        params : dict
            Request parameters. May contain an optional ``api_key`` entry

        Returns
        -------
        tuple[dict, str]
            A copy of ``params`` (with ``api_key`` removed if present) and
            the resolved API key string

        Raises
        ------
        AssertionError
            If ``params`` is not a ``dict``
        ValueError
            If no API key is found or the key is too short
        """
        assert isinstance(params, dict), "parameters needs to be a dict"
        params = copy.deepcopy(params)

        key = params.pop("api_key", API_TOKEN)

        if key is None:
            raise ValueError(
                "no API key provided. Either set it as an environment "
                "variable `SF_API_KEY`, or provide `api_key` "
                "as an argument. Visit https://solarfarmer.dnv.com/ to get an API key."
            )

        if len(key) <= 1:
            raise ValueError("API key is too short.")

        return params, key

    def _get_timeout(self, params: dict) -> int:
        """
        Determine the timeout in seconds for an API call.

        Parameters
        ----------
        params : dict
            Request parameters. A ``time_out`` key overrides the instance default.

        Returns
        -------
        int
            Timeout in seconds
        """
        if "time_out" in params:
            # per-request override
            return params["time_out"]
        return self.timeout

    def make_url(self) -> str:
        """Compose the full URL from ``base_url`` and ``endpoint``."""
        return "/".join([self.base_url, self.endpoint])

    def get(self, params: dict) -> Response:
        """
        Make a GET request.

        Parameters
        ----------
        params : dict
            Parameters passed in the GET request

        Returns
        -------
        Response
            The API response object
        """
        return self._make_request(params, request_content=None, files=None, method="GET")

    def post(self, params: dict, request_content: str, files: list) -> Response:
        """
        Make a POST request.

        Parameters
        ----------
        params : dict
            Parameters passed in the POST request
        request_content : str
            Contents for the request body
        files : list
            Files for the request (PAN, ONE, met data, HOR)

        Returns
        -------
        Response
            The API response object
        """
        return self._make_request(params, request_content, files, method="POST")

    def _make_request(
        self, params: dict, request_content: str, files: list, method: str
    ) -> Response:
        """
        Make an HTTP request with the specified method.

        Parameters
        ----------
        params : dict
            Parameters passed in the request
        request_content : str
            Request body content (used for POST requests)
        files : list
            Files to attach (used for POST requests)
        method : str
            HTTP method to use (e.g., ``"GET"``, ``"POST"``)

        Returns
        -------
        Response
            The API response object
        """
        params, key = self._check_params(params)
        timeout = self._get_timeout(params)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "solarfarmer-api-sdk/" + __version__,
        }

        try:
            if method.upper() == "POST":
                # POST requests: endpoints ModelChain, ModelChainAsync or TerminateAsync
                response = requests.post(
                    self.url,
                    headers=headers,
                    params=params,
                    data={"request": request_content},
                    files=files,
                    timeout=timeout,
                )
            else:
                # GET requests: endpoints About, Service or ModelChainAsync (for the status)
                response = requests.request(
                    method=method.upper(),
                    url=self.url,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                )

            if response.ok:
                body = detect_portal_fallback(response.text)

                return self.response_class(
                    code=response.status_code,
                    url=response.url,
                    data=json.loads(body),
                    success=True,
                    exception=None,
                    method=method.upper(),
                )

            elif response.status_code >= 400:
                # Raise for HTTP errors (4xx/5xx)
                text = response.text

                message = map_http_error_to_message(
                    response.status_code, text, _parse_error_body(text)
                )

                # Try and extract JSON body if possible, it may contain a ProblemDetails object
                try:
                    problem_details_json = response.json()
                except Exception:
                    problem_details_json = None

                return self.response_class(
                    code=response.status_code,
                    url=response.url,
                    data=None,
                    exception=message,
                    success=False,
                    method=method.upper(),
                    problem_details_json=problem_details_json,
                )

        except (requests.exceptions.RequestException, ValueError) as e:
            # Network-level failures: connection errors, timeouts, etc.
            return self.response_class(
                code=0,
                url=self.url,
                data=None,
                exception=f"Network error: {e}",
                success=False,
                method=method.upper(),
            )


def _parse_error_body(text: str) -> dict[str, Any]:
    """
    Parse a JSON error body into a dictionary.

    Parameters
    ----------
    text : str
        Raw response text

    Returns
    -------
    dict[str, Any]
        Parsed JSON body, or an empty dict if parsing fails
    """
    try:
        return json.loads(text)
    except Exception:
        return {}


def _extract_message(payload: dict[str, Any]) -> str | None:
    """
    Extract a human-readable message from common error payload shapes.

    Supported shapes: ``{"message": "..."}``,
    ``{"error": {"message": "..."}}``, and
    ``{"response_status": {"message": "..."}}``.

    Parameters
    ----------
    payload : dict[str, Any]
        Parsed error response body

    Returns
    -------
    str or None
        The extracted message string, or ``None`` if not found
    """
    if not payload:
        return None
    if isinstance(payload.get("message"), str):
        return payload["message"]
    err = payload.get("error")
    if isinstance(err, dict) and isinstance(err.get("message"), str):
        return err["message"]
    rs = payload.get("response_status")
    if isinstance(rs, dict) and isinstance(rs.get("message"), str):
        return rs["message"]
    return None


def _is_jwt_expired(text: str, payload: dict[str, Any]) -> bool:
    """
    Heuristically detect whether a response indicates an expired or invalid token.

    Parameters
    ----------
    text : str
        Raw response text (case-insensitive search applied)
    payload : dict[str, Any]
        Parsed error response body

    Returns
    -------
    bool
        ``True`` if the response appears to indicate a token expiry
    """
    t = text.lower()
    if "jwt is expired" in t or "token expired" in t or "token is expired" in t:
        return True
    msg = _extract_message(payload)
    if msg and ("expired" in msg.lower() or "token" in msg.lower() and "expire" in msg.lower()):
        return True
    return False


def map_http_error_to_message(status: int, text: str, payload: dict[str, Any]) -> str:
    """
    Map an HTTP status code and response body to a user-friendly error message.

    Parameters
    ----------
    status : int
        HTTP status code
    text : str
        Raw response body text
    payload : dict[str, Any]
        Parsed response body used to extract structured error messages

    Returns
    -------
    str
        A human-readable error message with guidance
    """
    # Provider message if present
    provider_msg = _extract_message(payload)

    if status == 400:
        return (
            provider_msg
            or "Response code 400 (Bad Request). Check required parameters or payload format."
        )
    if status == 401:
        if _is_jwt_expired(text, payload):
            return (
                "Response code 401 (Unauthorized). Your token has expired. "
                "Regenerate your API token in the SolarFarmer portal: " + SF_PORTAL_URL
            )
        return "Response code 401 (Unauthorized). Your credentials are invalid or missing."
    if status == 403:
        return (
            "Response code 403 (Forbidden). "
            "Your credentials are valid, but you lack permission for this resource."
        )
    if status == 404:
        return "Response code 404 (Not Found). The endpoint or resource does not exist."
    if status == 409:
        return (
            provider_msg
            or "Response code 409 (Conflict). The resource state conflicts with your request."
        )
    if status == 422:
        return (
            provider_msg
            or "Response code 422 (Unprocessable Entity). Validation failed for the supplied data."
        )
    if status == 429:
        retry_after = payload.get("retry_after") or payload.get(
            "retry-after"
        )  # if the server echoes it
        tail = f" Retry after {retry_after} seconds." if retry_after else ""
        return "Response code 429 (Too Many Requests). You are being rate limited." + tail
    if 500 <= status < 600:
        return "Server error on the provider side. Please retry later or contact support if persistent."

    # Fallback includes server message if present
    if provider_msg:
        return f"HTTP {status}. {provider_msg}"

    # Last resort: first 200 chars of body
    lines = (text or "").strip().splitlines()
    snippet = lines[0][:200] if lines else ""
    return f"HTTP {status}. {snippet or 'Unknown error.'}"


def detect_portal_fallback(content: str) -> str:
    """
    Identify HTML portal fallback in a successful API response and return
    a standardized error message; otherwise return the original text.

    The function detects typical HTML document markers (e.g., the
    doctype, <html> tag) that indicate an endpoint URL resolved to a
    web portal instead of an API service (common when the path/version
    is unrecognized). In that case, it returns a JSON-formatted string
    with a single 'error' key. If no HTML markers are found, it returns
    the input text unchanged. An empty or whitespace-only string is
    normalised to ``"{}"``.

    Parameters
    ----------
    content : str
        Decoded response body text

    Returns
    -------
    str
        If HTML fallback is detected:
            '{"error": "the API call was successful but it used an '
            'unrecognized service or inexistent API version. '
            'Please review the endpoint or version used."}'
        If ``content`` is empty or whitespace: ``"{}"``.
        Otherwise, ``content`` unchanged

    """
    # Normalize to text
    probe = content.lstrip().lower()

    # Heuristics: typical HTML markers that indicate a portal page
    looks_like_html = (
        probe.startswith("<!doctype html")
        or probe.startswith("<html")
        or bool(re.search(r"<html\b", probe))
        or bool(re.search(r"<head\b", probe))
        or bool(re.search(r"</body\s*>", probe))
    )

    if looks_like_html:
        return json.dumps(
            {
                "error": (
                    "the API call was successful but it used an "
                    "unrecognized service or inexistent API version. "
                    "Please review the endpoint or version used."
                )
            }
        )
    else:
        if not str(content).strip():
            # Handles empty string or whitespace,
            # it could be the case with the 'TerminateModelChainAsync' endpoint
            content = "{}"

        return content


def build_api_url(version: str | None = None) -> str:
    """
    Build the API URL based on an optional version.

    If `version` is None, it will consider the latest version.
    The version must be either 'latest' or of the form 'vX' where X
    is a positive integer (e.g., 'v4', 'v5').
    Any other format raises a ValueError.
    The final URL takes the form: `https://solarfarmer.dnv.com/<VERSION>/api`.

    Parameters
    ----------
    version : str, optional
        API version selector. Accepted values:
        - None          : uses the 'latest' version path (same as ``'latest'``)
        - 'latest'      : uses the 'latest' version path
        - 'vX'          : where X is a positive integer, e.g., 'v5'

    Returns
    -------
    str
        The constructed URL.

    Raises
    ------
    ValueError
        If `version` is not None and not in the allowed formats.

    """

    # None -> return base url
    if version is None or version == "latest":
        return BASE_API_URL

    base = SF_PORTAL_URL.rstrip("/")

    # Validate allowed forms
    if re.fullmatch(r"v[1-9]\d*", version):
        return f"{base}/{version}/api"

    raise ValueError(f"Invalid version '{version}'. Must be 'latest' or 'vX' (e.g., 'v5').")
