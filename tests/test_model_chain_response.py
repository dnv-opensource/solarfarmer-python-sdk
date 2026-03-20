"""
Unit tests for ModelChainResponse.
Covers __repr__, from_response, and from_dict.
"""

import json
import warnings

import pytest

from solarfarmer.models.model_chain_response import ModelChainResponse


@pytest.fixture
def full_data():
    """A complete API response dict with all fields populated."""
    return {
        "annualEnergyYieldResults": [{"year": 2020, "energyYieldResults": {}}],
        "inputsDerivedFileContents": json.dumps({"key": "value"}),
        "lossTree": {"root": []},
        "lossTreeResults": "time\tenergy\n2020-01-01\t100",
        "pvSystFormatResultsFile": "col1,col2\n1,2",
        "resultsFile": "col1\tcol2\n1\t2",
        "systemAttributes": {"dcCapacity": 5000},
        "totalModuleArea": 1234.5,
    }


@pytest.fixture
def minimal_data():
    """API response dict with no optional fields."""
    return {}


@pytest.fixture
def full_response(full_data):
    return ModelChainResponse.from_dict(full_data, project_id="MyProject")


class TestModelChainResponseRepr:
    def test_present_fields_show_present(self, full_response):
        r = repr(full_response)
        assert "AnnualEnergyYieldResults=present" in r
        assert "InputsDerivedFileContents=present" in r
        assert "LossTree=present" in r
        assert "LossTreeResults=present" in r
        assert "PvSystFormatResultsFile=present" in r
        assert "ResultsFile=present" in r
        assert "SystemAttributes=present" in r

    def test_total_module_area_shown(self, full_response):
        assert "TotalModuleArea=1234.5" in repr(full_response)

    def test_none_fields_show_none(self, minimal_data):
        resp = ModelChainResponse.from_dict(minimal_data)
        r = repr(resp)
        assert "AnnualEnergyYieldResults=None" in r
        assert "InputsDerivedFileContents=None" in r

    def test_none_name(self, minimal_data):
        resp = ModelChainResponse.from_dict(minimal_data)
        assert "Name=None" in repr(resp)


class TestModelChainResponseFromResponse:
    def test_valid_dict_returns_instance(self, full_data):
        result = ModelChainResponse.from_response(full_data, project_id="Proj")
        assert isinstance(result, ModelChainResponse)
        assert result.Name == "Proj"

    def test_raises_value_error_for_list(self):
        with pytest.raises(ValueError, match="dict"):
            ModelChainResponse.from_response([{"key": "val"}])

    def test_raises_value_error_for_string(self):
        with pytest.raises(ValueError, match="dict"):
            ModelChainResponse.from_response("not a dict")

    def test_raises_value_error_for_none(self):
        with pytest.raises(ValueError):
            ModelChainResponse.from_response(None)

    def test_delegates_to_from_dict(self, full_data):
        """from_response should produce the same result as from_dict."""
        via_response = ModelChainResponse.from_response(full_data, project_id="P")
        via_dict = ModelChainResponse.from_dict(full_data, project_id="P")
        assert via_response == via_dict

    def test_no_project_id_gives_none_name(self, minimal_data):
        result = ModelChainResponse.from_response(minimal_data)
        assert result.Name is None


class TestModelChainResponseFromDict:
    def test_all_fields_populated(self, full_data):
        resp = ModelChainResponse.from_dict(full_data, project_id="P")
        assert resp.Name == "P"
        assert resp.AnnualEnergyYieldResults == full_data["annualEnergyYieldResults"]
        assert resp.InputsDerivedFileContents == {"key": "value"}
        assert resp.LossTree == full_data["lossTree"]
        assert resp.LossTreeResults == full_data["lossTreeResults"]
        assert resp.PvSystFormatResultsFile == full_data["pvSystFormatResultsFile"]
        assert resp.ResultsFile == full_data["resultsFile"]
        assert resp.SystemAttributes == full_data["systemAttributes"]
        assert resp.TotalModuleArea == full_data["totalModuleArea"]

    def test_empty_dict_gives_all_none(self, minimal_data):
        resp = ModelChainResponse.from_dict(minimal_data)
        assert resp.AnnualEnergyYieldResults is None
        assert resp.InputsDerivedFileContents is None
        assert resp.LossTree is None
        assert resp.LossTreeResults is None
        assert resp.PvSystFormatResultsFile is None
        assert resp.ResultsFile is None
        assert resp.SystemAttributes is None
        assert resp.TotalModuleArea is None

    def test_inputs_derived_as_json_string_parsed(self):
        data = {"inputsDerivedFileContents": json.dumps({"a": 1})}
        resp = ModelChainResponse.from_dict(data)
        assert resp.InputsDerivedFileContents == {"a": 1}

    def test_inputs_derived_as_dict_used_directly(self):
        data = {"inputsDerivedFileContents": {"a": 1}}
        resp = ModelChainResponse.from_dict(data)
        assert resp.InputsDerivedFileContents == {"a": 1}

    def test_inputs_derived_malformed_json_warns_and_returns_none(self):
        data = {"inputsDerivedFileContents": "not valid json {{{"}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            resp = ModelChainResponse.from_dict(data)
        assert resp.InputsDerivedFileContents is None
        assert any("inputsDerivedFileContents" in str(w.message) for w in caught)

    def test_inputs_derived_unexpected_type_warns_and_returns_none(self):
        data = {"inputsDerivedFileContents": 42}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            resp = ModelChainResponse.from_dict(data)
        assert resp.InputsDerivedFileContents is None
        assert any("inputsDerivedFileContents" in str(w.message) for w in caught)

    def test_inputs_derived_none_stays_none(self):
        data = {"inputsDerivedFileContents": None}
        resp = ModelChainResponse.from_dict(data)
        assert resp.InputsDerivedFileContents is None

    def test_project_id_sets_name(self):
        resp = ModelChainResponse.from_dict({}, project_id="SpecificName")
        assert resp.Name == "SpecificName"

    def test_no_project_id_name_is_none(self):
        resp = ModelChainResponse.from_dict({})
        assert resp.Name is None
