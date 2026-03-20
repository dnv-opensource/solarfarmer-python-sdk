from .api import Client, Response
from .config import BASE_API_URL, GENERAL_TIMEOUT, SERVICE_ENDPOINT_URL
from .logging import get_logger

_logger = get_logger("endpoint.service")


def service(**kwargs) -> dict:
    """
    Makes a call to SolarFarmer Service endpoint.
    This endpoint requests the services (their names as strings)
    available to the user whose API token is being used.
    """
    response = service_call(**kwargs)
    service_info = {}
    if response.success:
        if "services" in response.data:
            services = response.data["services"]
            service_info = services
            _logger.info("%d SolarFarmer service(s) returned:", len(services))
            for svc in services:
                _logger.info("  %s", svc)
        else:
            _logger.warning("No services returned")
            _logger.debug("output_response = %s", response.data)
    else:
        _logger.error("API request %s failed.", response.url)
        _logger.error("%s", response.exception)
    return service_info


def service_call(**kwargs) -> Response:
    """
    Helper of the GET call to the Service endpoint.
    """
    client = Client(
        base_url=BASE_API_URL,
        endpoint=SERVICE_ENDPOINT_URL,
        response_type=Response,
        timeout=GENERAL_TIMEOUT,
    )

    return client.get({**kwargs})
