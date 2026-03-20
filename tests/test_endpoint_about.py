import re
from unittest.mock import MagicMock, patch

import pytest

import solarfarmer
from solarfarmer.api import Response


@pytest.mark.integration
class TestAboutEndpoint:
    """Live-API integration tests for the About endpoint."""

    def test_about_latest_version_success(self, api_key):
        """Test calling about() without version returns success."""
        result = solarfarmer.about(api_key=api_key)

        assert result is not None
        assert isinstance(result, dict)
        assert "solarFarmerCoreVersion" in result
        assert "solarFarmerApiVersion" in result
        assert re.match(r"^\d+\.\d+", result["solarFarmerApiVersion"])

    def test_about_version_structure(self, api_key):
        """Test that about() returns proper version information structure."""
        result = solarfarmer.about(api_key=api_key)

        assert isinstance(result["solarFarmerCoreVersion"], str)
        assert isinstance(result["solarFarmerApiVersion"], str)
        assert len(result["solarFarmerCoreVersion"]) > 0
        assert len(result["solarFarmerApiVersion"]) > 0

    @pytest.mark.parametrize(
        "version,expected_version_prefix", [("v4", "4."), ("v5", "5."), ("v6", "6.")]
    )
    def test_about_all_versions_return_proper_structure(
        self, api_key, version, expected_version_prefix
    ):
        """All versions return proper structure and the correct API version prefix."""
        result = solarfarmer.about(version=version, api_key=api_key)

        assert result is not None
        assert isinstance(result, dict)
        assert "solarFarmerCoreVersion" in result
        assert "solarFarmerApiVersion" in result
        assert result["solarFarmerApiVersion"].startswith(expected_version_prefix)


class TestAboutEndpointUnit:
    """Unit tests for about() using a mocked HTTP Client."""

    def _ok_response(self, data=None) -> Response:
        data = data or {"solarFarmerCoreVersion": "1.2.3", "solarFarmerApiVersion": "6.0.0"}
        return Response(code=200, url="http://mock/About", data=data, success=True, method="GET")

    def _err_response(self) -> Response:
        return Response(
            code=401,
            url="http://mock/About",
            data={"error": "Unauthorized"},
            success=False,
            method="GET",
            exception="401 Unauthorized",
        )

    @patch("solarfarmer.endpoint_about.Client")
    def test_success_returns_response_data(self, mock_client_cls):
        """about() returns response.data on a successful call."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = self._ok_response()

        result = solarfarmer.about(api_key="test_key")

        assert result == {"solarFarmerCoreVersion": "1.2.3", "solarFarmerApiVersion": "6.0.0"}
        mock_client.get.assert_called_once()

    @patch("solarfarmer.endpoint_about.Client")
    def test_failure_returns_empty_dict(self, mock_client_cls):
        """about() returns {} when the API call fails."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = self._err_response()

        result = solarfarmer.about(api_key="test_key")

        assert result == {}

    @patch("solarfarmer.endpoint_about.build_api_url")
    @patch("solarfarmer.endpoint_about.Client")
    def test_version_forwarded_to_build_api_url(self, mock_client_cls, mock_build_url):
        """The version argument is forwarded to build_api_url."""
        mock_build_url.return_value = "http://mock/v5"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get.return_value = self._ok_response()

        solarfarmer.about(version="v5", api_key="test_key")

        mock_build_url.assert_called_once_with("v5")

    @patch("solarfarmer.endpoint_about.Client")
    def test_malformed_success_response_logs_error_and_returns_data(self, mock_client_cls, caplog):
        """about() logs an error and still returns data when version keys are absent."""
        import logging

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        malformed_data = {"unexpectedKey": "someValue"}
        mock_client.get.return_value = self._ok_response(data=malformed_data)

        with caplog.at_level(logging.ERROR, logger="solarfarmer"):
            result = solarfarmer.about(api_key="test_key")

        assert result == malformed_data
        assert any("Error" in record.message for record in caplog.records)
