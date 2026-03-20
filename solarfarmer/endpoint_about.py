from .api import Client, Response, build_api_url
from .config import ABOUT_ENDPOINT_URL, GENERAL_TIMEOUT
from .logging import get_logger

_logger = get_logger("endpoint.about")


def about(version: str | None = None, **kwargs) -> dict:
    """
    Makes a call to SolarFarmer About endpoint.
    This endpoint requests the versions of the libraries
    used by the current SolarFarmer Web API server.

    Parameters
    ----------
    version : str, optional
        SolarFarmer API version selector. Accepted values:
                - None          : it will use the latest version available
                - 'latest'      : uses the 'latest' version path
                - 'vX'          : where X is a positive integer, e.g., 'v5'
    **kwargs
        Additional keyword arguments.
    """
    response = about_call(version, **kwargs)
    about_details = {}
    if response.success:
        _logger.debug("GET Request: %s", response.url)
        _logger.debug("Full JSON response: %s", response.data)
        try:
            _logger.info("SF-Core version: %s", response.data["solarFarmerCoreVersion"])
            _logger.info("SF-API version: %s", response.data["solarFarmerApiVersion"])
        except Exception:
            _logger.error("Error: %s", response.data.get("error", "Unknown error"))
        about_details = response.data
    else:
        _logger.error("API request %s failed.", response.url)
        _logger.error("%s", response.exception)
    return about_details


def about_call(version: str | None = None, **kwargs) -> Response:
    """
    Helper of the GET call to the About endpoint.
    """
    base_url = build_api_url(version)

    client = Client(
        base_url=base_url,
        endpoint=ABOUT_ENDPOINT_URL,
        response_type=Response,
        timeout=GENERAL_TIMEOUT,
    )

    return client.get({**kwargs})
