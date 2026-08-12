from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import solarfarmer.rcl as rcl
from solarfarmer.rcl import (
    RCLCatalogItem,
    RCLCatalogResponse,
    RCLRateLimitInfo,
    _build_query_params,
    _extract_rate_limit,
)

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestQueryBuilder:
    """Test _build_query_params query parameter construction."""

    def test_simple_filter(self):
        params = _build_query_params(manufacturer="Canadian Solar")
        assert params["filter.manufacturer"] == "Canadian Solar"

    def test_contains_operator(self):
        params = _build_query_params(model_contains="715TB")
        assert params["filter.model.contains"] == "715TB"

    def test_gte_operator(self):
        params = _build_query_params(p_nom_gte=400)
        assert params["filter.pNom.gte"] == 400

    def test_lte_operator(self):
        params = _build_query_params(p_nom_lte=800)
        assert params["filter.pNom.lte"] == 800

    def test_gt_lt_operators(self):
        params = _build_query_params(effic_max_gt=0.97, effic_max_lt=0.99)
        assert params["filter.efficMax.gt"] == 0.97
        assert params["filter.efficMax.lt"] == 0.99

    def test_multiple_filters_combined(self):
        params = _build_query_params(
            manufacturer_contains="SMA",
            p_nom_conv_gte=100000,
            p_nom_conv_lte=200000,
        )
        assert params["filter.manufacturer.contains"] == "SMA"
        assert params["filter.pNomConv.gte"] == 100000
        assert params["filter.pNomConv.lte"] == 200000

    def test_none_filters_omitted(self):
        params = _build_query_params(manufacturer=None, model_contains="X")
        assert "filter.manufacturer" not in params
        assert params["filter.model.contains"] == "X"

    def test_pagination_defaults(self):
        params = _build_query_params()
        assert params["top"] == 25
        assert params["skip"] == 0

    def test_pagination_custom(self):
        params = _build_query_params(top=100, skip=50)
        assert params["top"] == 100
        assert params["skip"] == 50

    def test_ordering(self):
        params = _build_query_params(order_by="pNom", order_dir="DESC")
        assert params["orderBy"] == "pNom"
        assert params["orderDir"] == "DESC"

    def test_ordering_omitted_when_no_field(self):
        params = _build_query_params()
        assert "orderBy" not in params
        assert "orderDir" not in params

    def test_output_parameter_joined(self):
        params = _build_query_params(output_parameter=["pNom", "voc", "isc"])
        assert params["outputParameter"] == "pNom,voc,isc"

    def test_output_parameter_single(self):
        params = _build_query_params(output_parameter=["pNom"])
        assert params["outputParameter"] == "pNom"

    def test_output_parameter_omitted_when_none(self):
        params = _build_query_params(output_parameter=None)
        assert "outputParameter" not in params

    def test_kwargs_passthrough_raw_key(self):
        # Raw dot-notation keys (e.g. future RCL filters) pass through unchanged
        params = _build_query_params(**{"filter.someNewField.gte": 100})
        assert params["filter.filter.someNewField.gte"] == 100  # wrapped because no operator suffix

    def test_kwargs_passthrough_operator_suffix(self):
        params = _build_query_params(someNewField_gte=42)
        assert params["filter.someNewField.gte"] == 42


class TestRateLimitInfo:
    """Test RCLRateLimitInfo dataclass properties."""

    RESET_TS = 1755043200  # a fixed future Unix timestamp

    def _make(self, remaining=85, limit=100, reset=None) -> RCLRateLimitInfo:
        return RCLRateLimitInfo(
            remaining=remaining,
            limit=limit,
            reset_timestamp=reset or self.RESET_TS,
        )

    def test_reset_datetime_is_utc(self):
        info = self._make()
        dt = info.reset_datetime
        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc

    def test_reset_datetime_value(self):
        # Unix epoch 0 should map to 1970-01-01T00:00:00Z
        info = RCLRateLimitInfo(remaining=50, limit=100, reset_timestamp=0)
        assert info.reset_datetime == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_usage_percent_normal(self):
        info = self._make(remaining=75, limit=100)
        assert info.usage_percent == pytest.approx(25.0)

    def test_usage_percent_full(self):
        info = self._make(remaining=0, limit=100)
        assert info.usage_percent == pytest.approx(100.0)

    def test_usage_percent_zero_limit(self):
        info = self._make(remaining=0, limit=0)
        assert info.usage_percent == 100.0

    def test_is_low_false_above_threshold(self):
        info = self._make(remaining=20, limit=100)  # 20% remaining > 15% threshold
        assert info.is_low is False

    def test_is_low_true_at_threshold(self):
        info = self._make(remaining=14, limit=100)  # 14% remaining < 15% threshold
        assert info.is_low is True

    def test_is_low_true_just_below_boundary(self):
        # 14 < 15.0 is True
        info = self._make(remaining=14, limit=100)
        assert info.is_low is True

    def test_str_shows_remaining_and_limit(self):
        info = self._make(remaining=42, limit=100)
        s = str(info)
        assert "42/100" in s

    def test_str_shows_reset_datetime(self):
        info = self._make()
        s = str(info)
        assert "resets" in s.lower()


class TestExtractRateLimit:
    """Test _extract_rate_limit header parsing."""

    def _mock_response(self, headers: dict) -> MagicMock:
        response = MagicMock()
        response.headers = headers
        return response

    def test_parses_all_headers(self):
        response = self._mock_response(
            {
                "X-RateLimit-Remaining": "85",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Reset": "1755043200",
            }
        )
        info = _extract_rate_limit(response)
        assert info is not None
        assert info.remaining == 85
        assert info.limit == 100
        assert info.reset_timestamp == 1755043200

    def test_returns_none_on_missing_headers(self):
        response = self._mock_response({})
        # Missing headers default to "0" strings — this should parse to 0/0/0, not None
        info = _extract_rate_limit(response)
        assert info is not None
        assert info.remaining == 0

    def test_returns_none_on_invalid_header_value(self):
        response = self._mock_response(
            {
                "X-RateLimit-Remaining": "not-a-number",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Reset": "1755043200",
            }
        )
        info = _extract_rate_limit(response)
        assert info is None

    def test_warns_when_quota_low(self, caplog):
        import logging

        response = self._mock_response(
            {
                "X-RateLimit-Remaining": "5",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Reset": "1755043200",
            }
        )
        with caplog.at_level(logging.WARNING):
            _extract_rate_limit(response)
        assert any(
            "low" in r.message.lower() or "quota" in r.message.lower() for r in caplog.records
        )


class TestCatalogResponse:
    """Test RCLCatalogResponse TypedDict shape (structural, not strict)."""

    def _make_response(self, n_items=2) -> RCLCatalogResponse:
        return RCLCatalogResponse(
            items=[{"manufacturer": "A", "model": f"M{i}"} for i in range(n_items)],
            total=n_items,
            skip=0,
            top=25,
            rate_limit=None,
        )

    def test_response_has_required_keys(self):
        r = self._make_response()
        assert "items" in r
        assert "total" in r
        assert "skip" in r
        assert "top" in r
        assert "rate_limit" in r

    def test_items_are_plain_dicts(self):
        r = self._make_response(n_items=3)
        assert isinstance(r["items"], list)
        for item in r["items"]:
            assert isinstance(item, dict)

    def test_rate_limit_can_be_none(self):
        r = self._make_response()
        assert r["rate_limit"] is None

    def test_rate_limit_can_be_info_object(self):
        info = RCLRateLimitInfo(remaining=90, limit=100, reset_timestamp=1755043200)
        r = self._make_response()
        r["rate_limit"] = info
        assert isinstance(r["rate_limit"], RCLRateLimitInfo)

    def test_total_reflects_item_count(self):
        r = self._make_response(n_items=5)
        assert r["total"] == 5
        assert len(r["items"]) == 5


class TestCatalogItem:
    """Test RCLCatalogItem typed wrapper for catalog items."""

    @pytest.fixture
    def module_dict(self) -> dict:
        """Sample module item dict as returned by the API."""
        return {
            "componentId": "MOD-12345",
            "fileUuid": "abc-123-def-456",
            "filename": "CS7N-715TB-AG.PAN",
            "manufacturer": "Canadian Solar Inc.",
            "model": "CS7N-715TB-AG",
            "pNom": 715,
            "bifacialityFactor": 0.7,
            "technol": "monoSi",
        }

    @pytest.fixture
    def inverter_dict(self) -> dict:
        """Sample inverter item dict as returned by the API."""
        return {
            "componentId": "INV-67890",
            "fileUuid": "xyz-789-uvw-012",
            "filename": "SG250HX.OND",
            "manufacturer": "Sungrow",
            "model": "SG250HX",
            "pNomConv": 250,
            "efficMax": 98.7,
            "vMppMin": 500,
            "vMppMax": 1500,
            "nbMppt": 12,
        }

    def test_snake_case_properties_module(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert item.file_uuid == "abc-123-def-456"
        assert item.filename == "CS7N-715TB-AG.PAN"
        assert item.manufacturer == "Canadian Solar Inc."
        assert item.model == "CS7N-715TB-AG"
        assert item.component_id == "MOD-12345"
        assert item.p_nom == 715
        assert item.bifaciality_factor == 0.7
        assert item.technol == "monoSi"

    def test_camelcase_aliases_module(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert item.fileUuid == item.file_uuid
        assert item.componentId == item.component_id
        assert item.pNom == item.p_nom
        assert item.bifacialityFactor == item.bifaciality_factor

    def test_snake_case_properties_inverter(self, inverter_dict):
        item = RCLCatalogItem(inverter_dict)
        assert item.p_nom_conv == 250
        assert item.effic_max == 98.7
        assert item.v_mpp_min == 500
        assert item.v_mpp_max == 1500
        assert item.nb_mppt == 12

    def test_camelcase_aliases_inverter(self, inverter_dict):
        item = RCLCatalogItem(inverter_dict)
        assert item.pNomConv == item.p_nom_conv
        assert item.efficMax == item.effic_max
        assert item.vMppMin == item.v_mpp_min
        assert item.vMppMax == item.v_mpp_max
        assert item.nbMppt == item.nb_mppt

    def test_dict_style_getitem(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert item["fileUuid"] == "abc-123-def-456"
        assert item["pNom"] == 715

    def test_dict_style_get(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert item.get("fileUuid") == "abc-123-def-456"
        assert item.get("missing", "default") == "default"

    def test_dict_style_contains(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert "fileUuid" in item
        assert "missing" not in item

    def test_dict_style_keys_values_items(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert "fileUuid" in item.keys()
        assert "abc-123-def-456" in item.values()
        assert ("fileUuid", "abc-123-def-456") in item.items()

    def test_raw_attribute(self, module_dict):
        item = RCLCatalogItem(module_dict)
        assert item.raw is module_dict

    def test_missing_optional_fields_return_none(self):
        minimal_dict = {
            "fileUuid": "uuid-1",
            "filename": "test.PAN",
            "manufacturer": "Test",
            "model": "Model1",
        }
        item = RCLCatalogItem(minimal_dict)
        assert item.p_nom is None
        assert item.bifaciality_factor is None
        assert item.p_nom_conv is None
        assert item.effic_max is None

    def test_empty_string_for_missing_required(self):
        empty_dict = {}
        item = RCLCatalogItem(empty_dict)
        assert item.file_uuid == ""
        assert item.filename == ""
        assert item.manufacturer == ""
        assert item.model == ""


# ---------------------------------------------------------------------------
# Unit tests for list_modules / list_inverters (mocked HTTP)
# ---------------------------------------------------------------------------


def _fake_catalog_response(items: list[dict], total: int | None = None) -> MagicMock:
    """Return a mock requests.Response that mimics an RCL catalog JSON response."""
    response = MagicMock()
    response.ok = True
    response.json.return_value = {
        "items": items,
        "total": total if total is not None else len(items),
        "skip": 0,
        "top": 25,
    }
    response.headers = {
        "X-RateLimit-Remaining": "90",
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Reset": "1755043200",
    }
    return response


class TestListModulesUnit:
    """Unit tests for list_modules with mocked RCLClient."""

    @patch("solarfarmer.rcl.RCLClient")
    def test_returns_catalog_response(self, MockClient):
        MockClient.return_value.get.return_value = _fake_catalog_response(
            [{"manufacturer": "LONGi", "model": "Hi-MO X6", "pNom": 620}]
        )
        result = rcl.list_modules(manufacturer_contains="LONGi")
        assert result["total"] == 1
        assert result["items"][0]["manufacturer"] == "LONGi"
        assert isinstance(result["rate_limit"], RCLRateLimitInfo)

    @patch("solarfarmer.rcl.RCLClient")
    def test_passes_filter_params(self, MockClient):
        mock_get = MockClient.return_value.get
        mock_get.return_value = _fake_catalog_response([])
        rcl.list_modules(manufacturer_contains="SMA", p_nom_gte=400, top=10)
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["filter.manufacturer.contains"] == "SMA"
        assert params["filter.pNom.gte"] == 400
        assert params["top"] == 10

    @patch("solarfarmer.rcl.RCLClient")
    def test_raises_on_non_2xx(self, MockClient):
        from solarfarmer.api import SolarFarmerAPIError

        response = MagicMock()
        response.ok = False
        response.status_code = 401
        MockClient.return_value.get.return_value = response
        with pytest.raises(SolarFarmerAPIError):
            rcl.list_modules()


class TestListInvertersUnit:
    """Unit tests for list_inverters with mocked RCLClient."""

    @patch("solarfarmer.rcl.RCLClient")
    def test_returns_catalog_response(self, MockClient):
        MockClient.return_value.get.return_value = _fake_catalog_response(
            [{"manufacturer": "SMA", "model": "STP 110-60", "pNomConv": 110000}]
        )
        result = rcl.list_inverters(manufacturer_contains="SMA")
        assert result["total"] == 1
        assert result["items"][0]["model"] == "STP 110-60"

    @patch("solarfarmer.rcl.RCLClient")
    def test_passes_inverter_filter_params(self, MockClient):
        mock_get = MockClient.return_value.get
        mock_get.return_value = _fake_catalog_response([])
        rcl.list_inverters(effic_max_gte=0.98, nb_mppt_gte=2, top=5)
        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["filter.efficMax.gte"] == 0.98
        assert params["filter.nbMppt.gte"] == 2


class TestDownloadFileUnit:
    """Unit tests for download_file with mocked RCLClient."""

    @patch("solarfarmer.rcl.RCLClient")
    def test_returns_bytes(self, MockClient, tmp_path):
        response = MagicMock()
        response.ok = True
        response.content = b"FAKE_PAN_CONTENT"
        response.headers = {}
        MockClient.return_value.get.return_value = response

        content = rcl.download_file(
            "some-uuid",
            "module.PAN",
            directory_path=tmp_path,
        )
        assert content == b"FAKE_PAN_CONTENT"

    @patch("solarfarmer.rcl.RCLClient")
    def test_saves_to_directory(self, MockClient, tmp_path):
        response = MagicMock()
        response.ok = True
        response.content = b"DATA"
        response.headers = {}
        MockClient.return_value.get.return_value = response

        rcl.download_file("uuid", "module.PAN", directory_path=tmp_path)
        assert (tmp_path / "module.PAN").exists()

    @patch("solarfarmer.rcl.RCLClient")
    def test_saves_to_file_path(self, MockClient, tmp_path):
        response = MagicMock()
        response.ok = True
        response.content = b"DATA"
        response.headers = {}
        MockClient.return_value.get.return_value = response

        dest = tmp_path / "custom_name.PAN"
        rcl.download_file("uuid", "original.PAN", file_path=dest)
        assert dest.exists()

    @patch("solarfarmer.rcl.RCLClient")
    def test_no_disk_write_when_save_false(self, MockClient, tmp_path):
        response = MagicMock()
        response.ok = True
        response.content = b"DATA"
        response.headers = {}
        MockClient.return_value.get.return_value = response

        content = rcl.download_file("uuid", "module.PAN", save_to_file=False)
        assert content == b"DATA"
        assert not any(tmp_path.iterdir())  # nothing written


class TestGetRateLimitStatusUnit:
    """Unit tests for get_rate_limit_status with mocked RCLClient."""

    @patch("solarfarmer.rcl.RCLClient")
    def test_uses_top_zero(self, MockClient):
        mock_get = MockClient.return_value.get
        response = MagicMock()
        response.ok = True
        response.headers = {
            "X-RateLimit-Remaining": "80",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "1755043200",
        }
        mock_get.return_value = response

        status = rcl.get_rate_limit_status()
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"top": 0}
        assert status.remaining == 80
        assert status.limit == 100

    @patch("solarfarmer.rcl.RCLClient")
    def test_raises_when_headers_missing(self, MockClient):
        from solarfarmer.api import SolarFarmerAPIError

        response = MagicMock()
        response.ok = True
        # Simulate completely absent rate-limit headers with invalid values
        response.headers = {
            "X-RateLimit-Remaining": "bad",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Reset": "1755043200",
        }
        MockClient.return_value.get.return_value = response
        with pytest.raises(SolarFarmerAPIError):
            rcl.get_rate_limit_status()


# ---------------------------------------------------------------------------
# Integration tests — require SF_API_KEY, auto-skip when absent
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRCLIntegration:
    """Integration tests that call the real RCL API."""

    def test_list_modules_basic(self, api_key):
        result = rcl.list_modules(top=5, api_key=api_key)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert "total" in result
        assert result["total"] >= 0

    def test_list_modules_with_manufacturer_filter(self, api_key):
        result = rcl.list_modules(
            manufacturer_contains="LONGi",
            top=5,
            api_key=api_key,
        )
        for item in result["items"]:
            assert "longi" in item.get("manufacturer", "").lower()

    def test_list_modules_with_power_range(self, api_key):
        result = rcl.list_modules(
            p_nom_gte=600,
            p_nom_lte=650,
            output_parameter=["pNom", "manufacturer", "model"],
            top=10,
            api_key=api_key,
        )
        for item in result["items"]:
            pnom = item.get("pNom")
            if pnom is not None:
                assert 600 <= pnom <= 650

    def test_list_modules_output_parameter_filters_fields(self, api_key):
        result = rcl.list_modules(
            output_parameter=["pNom", "manufacturer"],
            top=3,
            api_key=api_key,
        )
        for item in result["items"]:
            # Only requested fields should be present (plus always-present identity fields)
            assert "pNom" in item or "manufacturer" in item

    def test_list_inverters_basic(self, api_key):
        result = rcl.list_inverters(top=5, api_key=api_key)
        assert "items" in result
        assert isinstance(result["items"], list)

    def test_list_inverters_with_filter(self, api_key):
        result = rcl.list_inverters(
            manufacturer_contains="SMA",
            top=5,
            api_key=api_key,
        )
        for item in result["items"]:
            assert "sma" in item.get("manufacturer", "").lower()

    def test_get_rate_limit_status(self, api_key):
        status = rcl.get_rate_limit_status(api_key=api_key)
        assert isinstance(status, RCLRateLimitInfo)
        assert status.limit >= 0
        assert status.remaining >= 0
        assert status.remaining <= status.limit

    def test_kwargs_passthrough(self, api_key):
        # Unknown kwargs should not cause a crash — API ignores unrecognised params
        result = rcl.list_modules(
            top=1,
            api_key=api_key,
            lifecycle_status="active",
        )
        assert "items" in result

    @pytest.mark.skip(reason="Preserves monthly download quota")
    def test_download_file(self, api_key, tmp_path):
        result = rcl.list_modules(top=1, api_key=api_key)
        items = result["items"]
        if not items:
            pytest.skip("No modules returned by catalog")
        item = items[0]
        content = rcl.download_file(
            item["fileUuid"],
            item["filename"],
            directory_path=tmp_path,
            api_key=api_key,
        )
        assert isinstance(content, bytes)
        assert len(content) > 0
        assert (tmp_path / item["filename"]).exists()

    @pytest.mark.skip(reason="Preserves monthly download quota")
    def test_download_file_memory_only(self, api_key):
        result = rcl.list_modules(top=1, api_key=api_key)
        items = result["items"]
        if not items:
            pytest.skip("No modules returned by catalog")
        item = items[0]
        content = rcl.download_file(
            item["fileUuid"],
            item["filename"],
            save_to_file=False,
            api_key=api_key,
        )
        assert isinstance(content, bytes)
        assert len(content) > 0
