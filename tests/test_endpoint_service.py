from unittest.mock import MagicMock, patch

import pytest

import solarfarmer
from solarfarmer.api import Response


@pytest.mark.integration
class TestServiceEndpoint:
    """Live-API integration tests for the Service endpoint."""

    def test_service_endpoint_returns_expected_services(self, api_key):
        """service() returns exactly ["ModelChain2D", "ModelChain3D"]."""
        result = solarfarmer.service(api_key=api_key)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(s, str) and s for s in result)
        assert result == ["ModelChain2D", "ModelChain3D"]


class TestServiceEndpointUnit:
    """Unit tests for service() using a mocked HTTP Client."""

    def _ok_response(self, services=None) -> Response:
        services = services if services is not None else ["ModelChain2D", "ModelChain3D"]
        return Response(
            code=200,
            url="http://mock/Service",
            data={"services": services},
            success=True,
            method="GET",
        )

    def _err_response(self) -> Response:
        return Response(
            code=500,
            url="http://mock/Service",
            data={},
            success=False,
            method="GET",
            exception="Internal Server Error",
        )

    @patch("solarfarmer.endpoint_service.Client")
    def test_success_returns_services_list(self, mock_client_cls):
        """service() returns the list from response.data['services']."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = self._ok_response()

        result = solarfarmer.service(api_key="test_key")

        assert result == ["ModelChain2D", "ModelChain3D"]
        mock_client.get.assert_called_once()

    @patch("solarfarmer.endpoint_service.Client")
    def test_missing_services_key_returns_empty_dict(self, mock_client_cls):
        """service() returns {} when 'services' key is absent from the response."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = Response(
            code=200, url="http://mock/Service", data={}, success=True, method="GET"
        )

        result = solarfarmer.service(api_key="test_key")

        assert result == {}

    @patch("solarfarmer.endpoint_service.Client")
    def test_failure_returns_empty_dict(self, mock_client_cls):
        """service() returns {} when the API call fails."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = self._err_response()

        result = solarfarmer.service(api_key="test_key")

        assert result == {}
