import logging
from unittest.mock import MagicMock, patch

from solarfarmer.api import Response
from solarfarmer.endpoint_terminate_async import terminate_calculation


def _ok_response(instance_id="inst-123") -> Response:
    return Response(
        code=200,
        url="http://mock/TerminateModelChainAsync",
        data={"instanceId": instance_id},
        success=True,
        method="POST",
    )


def _err_response() -> Response:
    return Response(
        code=400,
        url="http://mock/TerminateModelChainAsync",
        data=None,
        success=False,
        method="POST",
        exception="Bad Request",
    )


class TestTerminateCalculation:
    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_success_returns_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _ok_response()

        result = terminate_calculation("inst-123", api_key="test_key")

        assert result.success is True
        assert result.code == 200

    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_failure_returns_response(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _err_response()

        result = terminate_calculation("inst-999", api_key="test_key")

        assert result.success is False

    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_instance_id_and_reason_in_post_payload(self, mock_client_cls):
        """instanceId and reason are forwarded as POST body keys."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _ok_response()

        terminate_calculation("inst-abc", reason="user cancelled", api_key="test_key")

        post_kwargs = mock_client.post.call_args
        payload = post_kwargs[0][0]  # first positional arg is the params dict
        assert payload["instanceId"] == "inst-abc"
        assert payload["reason"] == "user cancelled"

    @patch("solarfarmer.endpoint_terminate_async.build_api_url")
    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_default_api_version_is_latest(self, mock_client_cls, mock_build_url):
        mock_build_url.return_value = "http://mock"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _ok_response()

        terminate_calculation("inst-123", api_key="test_key")

        mock_build_url.assert_called_once_with("latest")

    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_success_logs_info(self, mock_client_cls, caplog):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _ok_response()

        with caplog.at_level(logging.INFO, logger="solarfarmer"):
            terminate_calculation("inst-123", api_key="test_key")

        assert any("200" in r.message or "success" in r.message.lower() for r in caplog.records)

    @patch("solarfarmer.endpoint_terminate_async.Client")
    def test_failure_logs_error(self, mock_client_cls, caplog):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = _err_response()

        with caplog.at_level(logging.ERROR, logger="solarfarmer"):
            terminate_calculation("inst-999", api_key="test_key")

        assert any(r.levelno >= logging.ERROR for r in caplog.records)
