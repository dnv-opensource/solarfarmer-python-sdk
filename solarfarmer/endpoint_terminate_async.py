from http import HTTPStatus

from .api import Client, Response, build_api_url
from .config import GENERAL_TIMEOUT, TERMINATE_ASYNC_ENDPOINT_URL
from .logging import get_logger

_logger = get_logger("endpoint.terminate")


def terminate_calculation(
    instance_id: str, reason: str | None = None, api_version: str = "latest", **kwargs
) -> Response:
    """
    Use the ``TerminateModelChainAsync`` endpoint to terminate a running
    calculation that was initiated with a call to the ``ModelChainAsync`` endpoint.

     Parameters
    ----------
    instance_id : str
        The instance ID returned from the POST request to the
        ``ModelChainAsync`` endpoint that you wish to terminate.
    reason : str, optional
        Reason for terminating the calculation.

    api_version : str, default="latest"
        API version selector. Accepted values:
        - None          : returns `base_url` as-is
        - 'latest'      : uses the 'latest' version path
        - 'vX'          : where X is a positive integer, e.g., 'v5'
    """

    # Build the URL and create Client
    base_url = build_api_url(api_version)
    endpoint_url = TERMINATE_ASYNC_ENDPOINT_URL
    client = Client(
        base_url=base_url,
        endpoint=endpoint_url,
        response_type=Response,
        timeout=GENERAL_TIMEOUT,
    )

    # Set the POST request
    response = client.post(
        {"instanceId": instance_id, "reason": reason, **kwargs}, request_content=None, files=None
    )

    if response.success:
        _logger.info(
            "Termination request sent successfully. Status code %d (%s) returned.",
            response.code,
            HTTPStatus(response.code).name,
        )
    else:
        _logger.error("API request to %s Endpoint failed.", TERMINATE_ASYNC_ENDPOINT_URL)

    return response
