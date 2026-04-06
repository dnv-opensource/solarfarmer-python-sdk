import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import solarfarmer.api as api_module
from solarfarmer.api import (
    Client,
    Response,
    _extract_message,
    _is_jwt_expired,
    _parse_error_body,
    build_api_url,
    detect_portal_fallback,
    map_http_error_to_message,
)
from solarfarmer.config import (
    BASE_API_URL,
    GENERAL_TIMEOUT,
    MODELCHAIN_ASYNC_TIMEOUT_CONNECTION,
    MODELCHAIN_TIMEOUT,
    SF_PORTAL_URL,
)

BASE_URL = "https://solarfarmer.dnv.com/latest/api"
FAKE_KEY = "fake-api-key-for-testing"


@pytest.fixture
def client(monkeypatch):
    """A Client pointed at the About endpoint with a patched API token."""
    monkeypatch.setattr(api_module, "API_TOKEN", FAKE_KEY)
    return Client(base_url=BASE_URL, endpoint="About", response_type=Response)


@pytest.fixture
def mock_http_response():
    """A MagicMock that mimics a successful requests.Response (200 JSON)."""
    m = MagicMock()
    m.ok = True
    m.status_code = 200
    m.url = f"{BASE_URL}/About"
    m.text = '{"version": "1.0"}'
    m.json.return_value = {"version": "1.0"}
    return m


class TestParseErrorBody:
    def test_valid_json_returns_dict(self):
        assert _parse_error_body('{"message": "oops"}') == {"message": "oops"}

    def test_non_json_returns_empty_dict(self):
        assert _parse_error_body("Not JSON at all") == {}

    def test_empty_string_returns_empty_dict(self):
        assert _parse_error_body("") == {}


class TestExtractMessage:
    @pytest.mark.parametrize(
        "payload, expected",
        [
            ({"message": "direct message"}, "direct message"),
            ({"error": {"message": "nested error"}}, "nested error"),
            ({"response_status": {"message": "status message"}}, "status message"),
            ({}, None),
            ({"message": 42}, None),  # non-string message ignored
            ({"error": {"message": 99}}, None),  # non-string nested message ignored
        ],
        ids=[
            "top_level_message",
            "nested_error_message",
            "response_status_message",
            "empty_payload",
            "non_string_top_level",
            "non_string_nested",
        ],
    )
    def test_extract_message(self, payload, expected):
        assert _extract_message(payload) == expected


class TestIsJwtExpired:
    @pytest.mark.parametrize(
        "text",
        ["jwt is expired", "TOKEN EXPIRED", "token is expired", "your Token Is Expired now"],
        ids=["jwt_phrase", "token_expired_upper", "token_is_expired", "mixed_case"],
    )
    def test_expired_phrase_in_text(self, text):
        assert _is_jwt_expired(text, {}) is True

    def test_expired_in_payload_message(self):
        payload = {"message": "The token has expired"}
        assert _is_jwt_expired("unauthorized", payload) is True

    @pytest.mark.parametrize(
        "text, payload",
        [
            ("invalid credentials", {}),
            ("", {"message": "bad request"}),
            ("something else", {"error": {"message": "forbidden"}}),
        ],
        ids=["clean_text_no_payload", "empty_text_irrelevant_payload", "unrelated_error"],
    )
    def test_not_expired(self, text, payload):
        assert _is_jwt_expired(text, payload) is False


class TestMapHttpErrorToMessage:
    @pytest.mark.parametrize(
        "status, text, payload, expected_substring",
        [
            # 400 — default and provider override
            (400, "", {}, "400"),
            (400, "", {"message": "Missing field X"}, "Missing field X"),
            # 401 — expired and plain invalid
            (401, "jwt is expired", {}, SF_PORTAL_URL),
            (401, "unauthorized", {}, "invalid or missing"),
            # 403
            (403, "", {}, "403"),
            # 404
            (404, "", {}, "404"),
            # 409 — default and provider override
            (409, "", {}, "409"),
            (409, "", {"message": "Already exists"}, "Already exists"),
            # 422 — default and provider override
            (422, "", {}, "422"),
            (422, "", {"message": "Bad value"}, "Bad value"),
            # 429 — without and with retry_after
            (429, "", {}, "429"),
            (429, "", {"retry_after": 30}, "30 seconds"),
            # 5xx
            (500, "", {}, "Server error"),
            (503, "", {}, "Server error"),
            # Unknown code with provider message
            (418, "", {"message": "I'm a teapot"}, "I'm a teapot"),
            # Unknown code no payload — snippet from body
            (418, "Unexpected response body", {}, "Unexpected response body"),
            # Unknown code empty body
            (418, "", {}, "Unknown error"),
        ],
        ids=[
            "400_default",
            "400_provider_msg",
            "401_expired",
            "401_invalid",
            "403",
            "404",
            "409_default",
            "409_provider_msg",
            "422_default",
            "422_provider_msg",
            "429_no_retry",
            "429_with_retry",
            "500",
            "503",
            "418_provider_msg",
            "418_body_snippet",
            "418_empty",
        ],
    )
    def test_message_contains(self, status, text, payload, expected_substring):
        msg = map_http_error_to_message(status, text, payload)
        assert expected_substring in msg


class TestDetectPortalFallback:
    @pytest.mark.parametrize(
        "content",
        [
            "<!DOCTYPE html><html><body></body></html>",
            "<!doctype html PUBLIC><html>",
            "<html lang='en'><head></head></html>",
            "   <html>content</html>",
            "<head><title>Portal</title></head>",
            "<div>some text</div></body>",
        ],
        ids=[
            "doctype_html",
            "doctype_public",
            "html_with_lang",
            "leading_whitespace",
            "head_tag",
            "closing_body",
        ],
    )
    def test_html_triggers_fallback(self, content):
        result = detect_portal_fallback(content)
        parsed = json.loads(result)
        assert "error" in parsed
        assert "unrecognized service" in parsed["error"]

    @pytest.mark.parametrize(
        "content, expected",
        [
            ('{"key": "value"}', '{"key": "value"}'),
            ("   ", "{}"),
            ("", "{}"),
            ("\n\t", "{}"),
        ],
        ids=["valid_json", "whitespace_only", "empty_string", "newline_tab"],
    )
    def test_non_html_passes_through(self, content, expected):
        assert detect_portal_fallback(content) == expected


class TestBuildApiUrl:
    @pytest.mark.parametrize(
        "version, expected",
        [
            (None, BASE_API_URL),
            ("latest", BASE_API_URL),
            ("v1", f"{SF_PORTAL_URL}/v1/api"),
            ("v5", f"{SF_PORTAL_URL}/v5/api"),
            ("v10", f"{SF_PORTAL_URL}/v10/api"),
        ],
        ids=["none", "latest", "v1", "v5", "v10"],
    )
    def test_valid_versions(self, version, expected):
        assert build_api_url(version) == expected

    @pytest.mark.parametrize(
        "version",
        ["v0", "V5", "5", "v", "v1.2", "v-1", "version5", ""],
        ids=["v0", "uppercase_V", "no_prefix", "v_only", "decimal", "negative", "word", "empty"],
    )
    def test_invalid_version_raises(self, version):
        with pytest.raises(ValueError, match="Invalid version"):
            build_api_url(version)


class TestCheckParams:
    def test_api_key_in_params_extracted_and_removed(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", None)
        params, key = Client._check_params({"api_key": "my-key", "foo": "bar"})
        assert key == "my-key"
        assert "api_key" not in params
        assert params == {"foo": "bar"}

    def test_api_key_from_env_token(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", "env-key")
        params, key = Client._check_params({"foo": "bar"})
        assert key == "env-key"
        assert params == {"foo": "bar"}

    def test_original_dict_not_mutated(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", None)
        original = {"api_key": "valid-key", "x": 1}
        Client._check_params(original)
        assert "api_key" in original  # deep copy — original untouched

    def test_no_key_raises(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", None)
        with pytest.raises(ValueError, match="no API key provided"):
            Client._check_params({})

    def test_short_key_raises(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", None)
        with pytest.raises(ValueError, match="API key is too short"):
            Client._check_params({"api_key": "x"})

    def test_non_dict_raises(self):
        with pytest.raises(AssertionError, match="parameters needs to be a dict"):
            Client._check_params("not a dict")


class TestGetTimeout:
    def test_default_timeout_is_general(self):
        c = Client(base_url=BASE_URL, endpoint="About", response_type=Response)
        assert c._get_timeout({}) == GENERAL_TIMEOUT

    @pytest.mark.parametrize(
        "timeout",
        [GENERAL_TIMEOUT, MODELCHAIN_TIMEOUT, MODELCHAIN_ASYNC_TIMEOUT_CONNECTION],
        ids=["general", "modelchain", "modelchain_async"],
    )
    def test_constructor_timeout_used(self, timeout):
        c = Client(base_url=BASE_URL, endpoint="About", response_type=Response, timeout=timeout)
        assert c._get_timeout({}) == timeout

    def test_user_override_takes_precedence(self):
        c = Client(
            base_url=BASE_URL, endpoint="About", response_type=Response, timeout=GENERAL_TIMEOUT
        )
        assert c._get_timeout({"time_out": 999}) == 999


class TestMakeUrl:
    def test_url_composed_correctly(self):
        c = Client(base_url="https://example.com/api", endpoint="About", response_type=Response)
        assert c.url == "https://example.com/api/About"


class TestMakeRequestGet:
    def test_200_returns_success_response(self, client, mock_http_response):
        with patch("solarfarmer.api.requests.request", return_value=mock_http_response) as mock_req:
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is True
        assert resp.code == 200
        assert resp.data == {"version": "1.0"}
        assert resp.method == "GET"
        mock_req.assert_called_once()
        _, kwargs = mock_req.call_args
        assert kwargs["timeout"] == GENERAL_TIMEOUT

    def test_200_html_portal_fallback(self, client):
        html_response = MagicMock()
        html_response.ok = True
        html_response.status_code = 200
        html_response.url = f"{BASE_URL}/About"
        html_response.text = "<!DOCTYPE html><html><body>Portal</body></html>"

        with patch("solarfarmer.api.requests.request", return_value=html_response):
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is True
        assert "error" in resp.data
        assert "unrecognized service" in resp.data["error"]

    @pytest.mark.parametrize(
        "status_code, text, expected_in_msg",
        [
            (401, "unauthorized", "invalid or missing"),
            (401, "jwt is expired", SF_PORTAL_URL),
            (403, "", "403"),
            (404, "", "404"),
            (500, "", "Server error"),
        ],
        ids=["401_invalid", "401_expired", "403", "404", "500"],
    )
    def test_error_status_returns_failure(self, client, status_code, text, expected_in_msg):
        error_response = MagicMock()
        error_response.ok = False
        error_response.status_code = status_code
        error_response.url = f"{BASE_URL}/About"
        error_response.text = text
        error_response.json.return_value = {}

        with patch("solarfarmer.api.requests.request", return_value=error_response):
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is False
        assert resp.code == status_code
        assert resp.data is None
        assert expected_in_msg in resp.exception

    def test_connection_error_returns_failure(self, client):
        with patch(
            "solarfarmer.api.requests.request",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is False
        assert resp.code == 0
        assert "Network error" in resp.exception

    def test_timeout_error_returns_failure(self, client):
        with patch(
            "solarfarmer.api.requests.request",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is False
        assert resp.code == 0
        assert "Network error" in resp.exception

    def test_400_non_json_body_sets_problem_details_to_none(self, client):
        error_response = MagicMock()
        error_response.ok = False
        error_response.status_code = 400
        error_response.url = f"{BASE_URL}/About"
        error_response.text = "Bad Request"
        error_response.json.side_effect = ValueError("No JSON")

        with patch("solarfarmer.api.requests.request", return_value=error_response):
            resp = client.get({"api_key": FAKE_KEY})

        assert resp.success is False
        assert resp.problem_details_json is None


class TestMakeRequestPost:
    def test_200_post_returns_success_response(self, monkeypatch, mock_http_response):
        monkeypatch.setattr(api_module, "API_TOKEN", FAKE_KEY)
        c = Client(
            base_url=BASE_URL,
            endpoint="ModelChain",
            response_type=Response,
            timeout=MODELCHAIN_TIMEOUT,
        )

        with patch("solarfarmer.api.requests.post", return_value=mock_http_response) as mock_post:
            resp = c.post({"api_key": FAKE_KEY}, request_content='{"x":1}', files=None)

        assert resp.success is True
        assert resp.code == 200
        assert resp.method == "POST"
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == MODELCHAIN_TIMEOUT

    def test_400_post_with_provider_message(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", FAKE_KEY)
        c = Client(
            base_url=BASE_URL,
            endpoint="ModelChain",
            response_type=Response,
            timeout=MODELCHAIN_TIMEOUT,
        )

        error_response = MagicMock()
        error_response.ok = False
        error_response.status_code = 400
        error_response.url = f"{BASE_URL}/ModelChain"
        error_response.text = '{"message": "Invalid panel count"}'
        error_response.json.return_value = {"message": "Invalid panel count"}

        with patch("solarfarmer.api.requests.post", return_value=error_response):
            resp = c.post({"api_key": FAKE_KEY}, request_content="{}", files=None)

        assert resp.success is False
        assert "Invalid panel count" in resp.exception

    def test_400_non_json_body_sets_problem_details_to_none(self, monkeypatch):
        monkeypatch.setattr(api_module, "API_TOKEN", FAKE_KEY)
        c = Client(
            base_url=BASE_URL,
            endpoint="ModelChain",
            response_type=Response,
            timeout=MODELCHAIN_TIMEOUT,
        )

        error_response = MagicMock()
        error_response.ok = False
        error_response.status_code = 400
        error_response.url = f"{BASE_URL}/ModelChain"
        error_response.text = "Bad Request"
        error_response.json.side_effect = ValueError("No JSON")

        with patch("solarfarmer.api.requests.post", return_value=error_response):
            resp = c.post({"api_key": FAKE_KEY}, request_content="{}", files=None)

        assert resp.success is False
        assert resp.problem_details_json is None
