import io
import logging
from unittest.mock import MagicMock, patch

import pytest

import solarfarmer
from solarfarmer.api import Response, SolarFarmerAPIError
from solarfarmer.endpoint_modelchains import (
    _handle_successful_response,
    _log_api_failure,
    _resolve_request_payload,
    modelchain_async_call,
    modelchain_call,
    process_and_map_results,
    run_energy_calculation,
)


class TestResolveRequestPayload:
    """Unit tests for _resolve_request_payload."""

    @patch("solarfarmer.endpoint_modelchains.parse_files_from_folder")
    @patch("solarfarmer.endpoint_modelchains.path_exists", return_value=True)
    def test_folder_path_delegates_to_parse_files_from_folder(
        self, mock_path_exists, mock_parse_folder
    ):
        mock_parse_folder.return_value = ('{"pvPlant":{}}', [("tmyFile", io.BytesIO())])
        content, files = _resolve_request_payload(
            inputs_folder_path="/some/folder",
            energy_calculation_inputs_file_path=None,
            meteorological_data_file_path=None,
            horizon_file_path=None,
            pan_file_paths=None,
            ond_file_paths=None,
            plant_builder=None,
        )
        mock_parse_folder.assert_called_once()
        assert content == '{"pvPlant":{}}'
        assert len(files) == 1

    @patch("solarfarmer.endpoint_modelchains.path_exists", return_value=False)
    def test_folder_path_not_found_raises(self, mock_path_exists):
        with pytest.raises(FileNotFoundError, match="does not exist"):
            _resolve_request_payload(
                inputs_folder_path="/missing/folder",
                energy_calculation_inputs_file_path=None,
                meteorological_data_file_path=None,
                horizon_file_path=None,
                pan_file_paths=None,
                ond_file_paths=None,
                plant_builder=None,
            )

    @patch("solarfarmer.endpoint_modelchains.parse_files_from_paths")
    def test_individual_paths_delegates_to_parse_files_from_paths(self, mock_parse_paths):
        mock_parse_paths.return_value = ('{"pvPlant":{}}', [])
        content, files = _resolve_request_payload(
            inputs_folder_path=None,
            energy_calculation_inputs_file_path="/path/to/inputs.json",
            meteorological_data_file_path="/path/to/met.dat",
            horizon_file_path=None,
            pan_file_paths=["/path/to/mod.PAN"],
            ond_file_paths=["/path/to/inv.OND"],
            plant_builder=None,
        )
        mock_parse_paths.assert_called_once_with(
            "/path/to/met.dat",
            None,
            ["/path/to/mod.PAN"],
            ["/path/to/inv.OND"],
            "/path/to/inputs.json",
        )
        assert content == '{"pvPlant":{}}'

    @patch("solarfarmer.endpoint_modelchains.parse_files_from_paths")
    def test_plant_builder_string(self, mock_parse_paths):
        mock_parse_paths.return_value = ("", [])
        payload_json = '{"pvPlant":{"racks":[]}}'
        content, files = _resolve_request_payload(
            inputs_folder_path=None,
            energy_calculation_inputs_file_path=None,
            meteorological_data_file_path=None,
            horizon_file_path=None,
            pan_file_paths=None,
            ond_file_paths=None,
            plant_builder=payload_json,
        )
        assert content == payload_json

    @patch("solarfarmer.endpoint_modelchains.parse_files_from_paths")
    def test_plant_builder_model_instance(self, mock_parse_paths):
        mock_parse_paths.return_value = ("", [])
        mock_model = MagicMock()
        mock_model.model_dump_json.return_value = '{"pvPlant":{}}'
        # Make isinstance check work for SolarFarmerBaseModel
        from solarfarmer.models._base import SolarFarmerBaseModel

        mock_model.__class__ = type("FakeModel", (SolarFarmerBaseModel,), {})
        content, _ = _resolve_request_payload(
            inputs_folder_path=None,
            energy_calculation_inputs_file_path=None,
            meteorological_data_file_path=None,
            horizon_file_path=None,
            pan_file_paths=None,
            ond_file_paths=None,
            plant_builder=mock_model,
        )
        mock_model.model_dump_json.assert_called_once_with(by_alias=True, exclude_none=True)
        assert content == '{"pvPlant":{}}'

    def test_no_inputs_raises_value_error(self):
        with pytest.raises(ValueError, match="No inputs provided"):
            _resolve_request_payload(
                inputs_folder_path=None,
                energy_calculation_inputs_file_path=None,
                meteorological_data_file_path=None,
                horizon_file_path=None,
                pan_file_paths=None,
                ond_file_paths=None,
                plant_builder=None,
            )


class TestHandleSuccessfulResponse:
    """Unit tests for _handle_successful_response."""

    @patch("solarfarmer.endpoint_modelchains.process_and_map_results")
    def test_completed_sync_response_returns_results(self, mock_process):
        mock_results = MagicMock()
        mock_process.return_value = mock_results
        response = Response(
            code=200,
            url="https://api.example.com/modelchain",
            data={"annualResults": []},
            success=True,
            method="POST",
        )
        result = _handle_successful_response(
            response, 1.5, "proj1", "/inputs", None, None, False, False
        )
        mock_process.assert_called_once_with(
            {"annualResults": []}, "proj1", "/inputs", None, None, False, False
        )
        assert result is mock_results

    @patch("solarfarmer.endpoint_modelchains.process_and_map_results")
    def test_completed_async_response_returns_results(self, mock_process):
        mock_results = MagicMock()
        mock_process.return_value = mock_results
        response = Response(
            code=200,
            url="https://api.example.com/modelchainasync",
            data={"runtimeStatus": "Completed", "output": {}},
            success=True,
            method="GET",
        )
        result = _handle_successful_response(
            response, 10.0, "proj1", None, None, None, False, False
        )
        mock_process.assert_called_once_with(
            {"runtimeStatus": "Completed", "output": {}}, "proj1", None, None, None, False, False
        )
        assert result is mock_results

    def test_terminated_async_returns_none(self):
        response = Response(
            code=200,
            url="https://api.example.com/modelchainasync",
            data={"runtimeStatus": "Terminated"},
            success=True,
            method="GET",
        )
        result = _handle_successful_response(response, 5.0, "proj1", None, None, None, False, False)
        assert result is None

    @pytest.mark.parametrize(
        "status,output",
        [
            ("Failed", "Out of memory"),
            ("Canceled", None),
            ("Unknown", None),
        ],
        ids=["failed_with_output", "canceled_no_output", "unknown"],
    )
    def test_non_completed_status_raises_and_logs(self, status, output, caplog):
        data: dict = {"runtimeStatus": status}
        if output is not None:
            data["output"] = output
        response = Response(
            code=200,
            url="https://api.example.com/modelchainasync",
            data=data,
            success=True,
            method="POST",
        )
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SolarFarmerAPIError) as exc_info:
                _handle_successful_response(
                    response, 3.0, "proj1", None, None, None, False, False
                )
        assert f"Runtime status = {status}" in caplog.text
        assert status in str(exc_info.value)
        if output:
            assert output in str(exc_info.value)

    def test_terminated_via_post_returns_none_and_logs(self, caplog):
        """Terminated via POST (e.g. polled after user cancel) returns None, does not raise."""
        response = Response(
            code=200,
            url="https://api.example.com/modelchainasync",
            data={"runtimeStatus": "Terminated", "output": "Manual stop"},
            success=True,
            method="POST",
        )
        with caplog.at_level(logging.ERROR):
            result = _handle_successful_response(
                response, 3.0, "proj1", None, None, None, False, False
            )
        assert result is None
        assert "Runtime status = Terminated" in caplog.text

    def test_terminated_guard_requires_async_url(self):
        """GET + Terminated on a sync URL must NOT trigger the early-exit guard."""
        response = Response(
            code=200,
            url="https://api.example.com/modelchain",  # no "modelchainasync" in URL
            data={"runtimeStatus": "Terminated"},
            success=True,
            method="GET",
        )
        with patch("solarfarmer.endpoint_modelchains.process_and_map_results") as mock_p:
            result = _handle_successful_response(
                response, 5.0, "proj1", None, None, None, False, False
            )
        assert result is None
        mock_p.assert_not_called()


class TestLogApiFailure:
    """Unit tests for _log_api_failure."""

    def test_logs_url_and_exception(self, caplog):
        response = Response(
            code=500,
            url="https://api.example.com/modelchain",
            data=None,
            success=False,
            method="POST",
            exception="Internal Server Error",
        )
        with caplog.at_level(logging.ERROR):
            _log_api_failure(response, 2.0)
        assert "api.example.com/modelchain" in caplog.text
        assert "Internal Server Error" in caplog.text

    @pytest.mark.parametrize(
        "problem_details,expected_in_log",
        [
            ({"title": "Validation Error"}, ["Validation Error"]),
            ({"detail": "field X is required"}, ["field X is required"]),
            (
                {
                    "title": "Bad input",
                    "errors": {"field1": ["must be positive"]},
                    "detail": "see above",
                },
                ["Bad input", "must be positive", "see above"],
            ),
            ({}, []),
            (None, []),
        ],
        ids=["title_only", "detail_only", "full_problem_details", "empty_dict", "none"],
    )
    def test_problem_details_variants(self, problem_details, expected_in_log, caplog):
        response = Response(
            code=400,
            url="https://api.example.com/modelchain",
            data=None,
            success=False,
            method="POST",
            exception="Bad Request",
            problem_details_json=problem_details,
        )
        with caplog.at_level(logging.ERROR):
            _log_api_failure(response, 1.0)
        for expected in expected_in_log:
            assert expected in caplog.text


class TestRunEnergyCalculation:
    """Unit tests for run_energy_calculation orchestration behavior."""

    @patch("solarfarmer.endpoint_modelchains._handle_successful_response")
    @patch("solarfarmer.endpoint_modelchains.modelchain_async_call")
    @patch("solarfarmer.endpoint_modelchains.modelchain_call")
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files", return_value=False)
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    def test_sync_endpoint_and_forwarded_kwargs(
        self,
        mock_resolve_payload,
        _mock_check_for_3d,
        mock_modelchain_call,
        mock_modelchain_async_call,
        mock_handle_success,
    ):
        file_handle = io.BytesIO(b"fake")
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [("panFile", file_handle)])
        mock_modelchain_call.return_value = Response(
            code=200, url="https://api.example.com/modelchain", data={}, success=True, method="POST"
        )
        expected_result = MagicMock()
        mock_handle_success.return_value = expected_result

        result = run_energy_calculation(
            inputs_folder_path="/tmp/input-folder",
            project_id="project-1",
            api_key="abc123",
            time_out=42,
            async_poll_time=1.5,
        )

        assert result is expected_result
        mock_modelchain_call.assert_called_once()
        assert mock_modelchain_call.call_args.kwargs["api_key"] == "abc123"
        assert mock_modelchain_call.call_args.kwargs["time_out"] == 42
        assert mock_modelchain_call.call_args.kwargs["async_poll_time"] == 1.5
        mock_modelchain_async_call.assert_not_called()
        assert file_handle.closed

    @pytest.mark.parametrize(
        "force_async_call,is_3d",
        [
            (True, False),
            (False, True),
            (True, True),
        ],
    )
    @patch("solarfarmer.endpoint_modelchains.modelchain_async_call")
    @patch("solarfarmer.endpoint_modelchains.modelchain_call")
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files")
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    @patch("solarfarmer.endpoint_modelchains._handle_successful_response", return_value=None)
    def test_async_endpoint_selection(
        self,
        _mock_handle_success,
        mock_resolve_payload,
        mock_check_for_3d,
        mock_modelchain_call,
        mock_modelchain_async_call,
        force_async_call,
        is_3d,
    ):
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [])
        mock_check_for_3d.return_value = is_3d
        mock_modelchain_async_call.return_value = Response(
            code=200,
            url="https://api.example.com/modelchainasync",
            data={"runtimeStatus": "Completed"},
            success=True,
            method="GET",
        )

        run_energy_calculation(
            inputs_folder_path="/tmp/input-folder",
            project_id="project-1",
            force_async_call=force_async_call,
        )

        mock_modelchain_async_call.assert_called_once()
        mock_modelchain_call.assert_not_called()

    @patch("solarfarmer.endpoint_modelchains._log_api_failure")
    @patch("solarfarmer.endpoint_modelchains.modelchain_call")
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files", return_value=False)
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    def test_failed_response_logs_and_raises(self, mock_resolve_payload, _mock_check_for_3d, mock_modelchain_call, mock_log_failure):
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [])
        mock_modelchain_call.return_value = Response(
            code=500,
            url="https://api.example.com/modelchain",
            data=None,
            success=False,
            method="POST",
            exception="Server error",
        )

        with pytest.raises(SolarFarmerAPIError) as exc_info:
            run_energy_calculation(
                inputs_folder_path="/tmp/input-folder", project_id="project-1"
            )

        mock_log_failure.assert_called_once()
        assert exc_info.value.status_code == 500
        assert exc_info.value.message == "Server error"

    @patch("solarfarmer.endpoint_modelchains._log_api_failure")
    @patch("solarfarmer.endpoint_modelchains.modelchain_call")
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files", return_value=False)
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    def test_failed_response_carries_problem_details(
        self, mock_resolve_payload, _mock_check_for_3d, mock_modelchain_call, _mock_log_failure
    ):
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [])
        problem_details = {"title": "Validation failed", "detail": "rack height too small"}
        mock_modelchain_call.return_value = Response(
            code=400,
            url="https://api.example.com/modelchain",
            data=None,
            success=False,
            method="POST",
            exception="Bad Request",
            problem_details_json=problem_details,
        )

        with pytest.raises(SolarFarmerAPIError) as exc_info:
            run_energy_calculation(
                inputs_folder_path="/tmp/input-folder", project_id="project-1"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.problem_details == problem_details
        assert "rack height too small" in str(exc_info.value)

    @patch("solarfarmer.endpoint_modelchains.modelchain_call", side_effect=RuntimeError("boom"))
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files", return_value=False)
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    def test_files_closed_when_dispatch_raises(
        self, mock_resolve_payload, _mock_check_for_3d, _mock_modelchain_call
    ):
        file_handle = io.BytesIO(b"fake")
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [("panFile", file_handle)])

        with pytest.raises(RuntimeError, match="boom"):
            run_energy_calculation(inputs_folder_path="/tmp/input-folder", project_id="project-1")

        assert file_handle.closed

    @patch("solarfarmer.endpoint_modelchains.modelchain_call")
    @patch("solarfarmer.endpoint_modelchains.check_for_3d_files", return_value=False)
    @patch("solarfarmer.endpoint_modelchains._resolve_request_payload")
    def test_none_params_not_folded_into_kwargs(
        self, mock_resolve_payload, _mock_check_for_3d, mock_modelchain_call
    ):
        mock_resolve_payload.return_value = ('{"pvPlant":{}}', [])
        mock_modelchain_call.return_value = Response(
            code=500,
            url="https://api.example.com/modelchain",
            data=None,
            success=False,
            method="POST",
            exception="error",
        )
        with pytest.raises(SolarFarmerAPIError):
            run_energy_calculation(
                inputs_folder_path="/tmp/input-folder",
                api_key=None,
                time_out=None,
                async_poll_time=None,
            )
        kwargs_passed = mock_modelchain_call.call_args.kwargs
        assert "api_key" not in kwargs_passed
        assert "time_out" not in kwargs_passed
        assert "async_poll_time" not in kwargs_passed


@pytest.mark.integration
class TestModelChainEndpoint:
    """Test cases for the ModelChain endpoint."""

    def test_energy_calculation_with_bern_2d_inputs_success(self, api_key, bern_2d_racks_inputs):
        """Test energy calculation with Bern 2D racks sample data."""
        result = solarfarmer.run_energy_calculation(
            inputs_folder_path=bern_2d_racks_inputs,
            project_id="test_sdk_bern_2d",
            print_summary=False,
            save_outputs=False,
            api_key=api_key,
        )

        # Verify that we get a valid CalculationResults object
        assert result is not None
        assert isinstance(result, solarfarmer.CalculationResults)

        # Verify that ModelChainResponse is populated
        assert result.ModelChainResponse is not None
        assert isinstance(result.ModelChainResponse, solarfarmer.ModelChainResponse)

        # Verify key properties are populated
        assert result.ModelChainResponse.AnnualEnergyYieldResults is not None
        assert result.ModelChainResponse.SystemAttributes is not None

        # Verify that annual data is populated
        assert result.AnnualData is not None
        assert isinstance(result.AnnualData, list)
        assert len(result.AnnualData) > 0

        # Verify that monthly data is populated
        assert result.MonthlyData is not None
        assert isinstance(result.MonthlyData, list)
        assert len(result.MonthlyData) > 0

        # Verify that calculation attributes are populated
        assert result.CalculationAttributes is not None
        assert isinstance(result.CalculationAttributes, dict)

        # Verify spot checks in annual data and results match expected structure
        # Verify annual data has energyYieldResults with netEnergy
        annual_data = result.AnnualData
        first_year = annual_data[0]
        assert "energyYieldResults" in first_year
        energy_yield = first_year["energyYieldResults"]
        assert "netEnergy" in energy_yield

        # Verify netEnergy is a number
        net_energy = energy_yield["netEnergy"]
        assert isinstance(net_energy, (int, float))
        assert net_energy > 0


class TestProcessAndMapResults:
    """Unit tests for process_and_map_results."""

    @patch("solarfarmer.endpoint_modelchains.CalculationResults")
    @patch("solarfarmer.endpoint_modelchains.ModelChainResponse")
    def test_maps_data_to_calculation_results(self, mock_mcr_cls, mock_cr_cls):
        """process_and_map_results delegates to ModelChainResponse and CalculationResults."""
        mock_response = MagicMock()
        mock_mcr_cls.from_response.return_value = mock_response
        mock_results = MagicMock()
        mock_cr_cls.from_modelchain_response.return_value = mock_results

        result = process_and_map_results(
            {"annualResults": []}, "proj1", None, None, None, False, False
        )

        mock_mcr_cls.from_response.assert_called_once_with({"annualResults": []}, "proj1")
        assert result is mock_results

    @patch("solarfarmer.endpoint_modelchains.CalculationResults")
    @patch("solarfarmer.endpoint_modelchains.ModelChainResponse")
    def test_async_completed_data_is_unwrapped(self, mock_mcr_cls, mock_cr_cls):
        """Async wrapper (instanceId + runtimeStatus='Completed') is stripped before mapping."""
        mock_mcr_cls.from_response.return_value = MagicMock()
        mock_cr_cls.from_modelchain_response.return_value = MagicMock()

        async_data = {
            "instanceId": "abc-123",
            "runtimeStatus": "Completed",
            "output": {"annualResults": [{"year": 2024}]},
        }
        process_and_map_results(async_data, "proj1", None, None, None, False, False)

        mock_mcr_cls.from_response.assert_called_once_with(
            {"annualResults": [{"year": 2024}]}, "proj1"
        )

    @patch("solarfarmer.endpoint_modelchains.CalculationResults")
    @patch("solarfarmer.endpoint_modelchains.ModelChainResponse")
    def test_save_outputs_false_skips_dir_creation(self, mock_mcr_cls, mock_cr_cls, tmp_path):
        """When save_outputs=False, no output subfolder is created under inputs_folder_path."""
        mock_mcr_cls.from_response.return_value = MagicMock()
        mock_cr_cls.from_modelchain_response.return_value = MagicMock()

        process_and_map_results({}, "proj1", str(tmp_path), None, None, False, False)

        assert list(tmp_path.iterdir()) == []

    @patch("solarfarmer.endpoint_modelchains.CalculationResults")
    @patch("solarfarmer.endpoint_modelchains.ModelChainResponse")
    def test_save_outputs_true_explicit_folder_is_created(
        self, mock_mcr_cls, mock_cr_cls, tmp_path
    ):
        """When save_outputs=True with an explicit outputs_folder_path, that folder is created."""
        mock_mcr_cls.from_response.return_value = MagicMock()
        mock_cr_cls.from_modelchain_response.return_value = MagicMock()

        explicit_dir = tmp_path / "my_outputs"
        assert not explicit_dir.exists()

        process_and_map_results({}, "proj1", None, None, str(explicit_dir), True, False)

        assert explicit_dir.exists()


class TestModelchainCall:
    """Unit tests for modelchain_call URL selection."""

    @patch("solarfarmer.endpoint_modelchains.Client")
    @patch("solarfarmer.endpoint_modelchains.build_api_url")
    def test_custom_api_url_bypasses_build_api_url(self, mock_build_url, mock_client_cls):
        """When api_url is provided, build_api_url is not called and Client receives the custom URL."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.post.return_value = Response(
            code=200,
            url="https://custom.example.com/api/ModelChain",
            data={},
            success=True,
            method="POST",
        )

        modelchain_call(
            endpoint_url="ModelChain",
            api_version="latest",
            api_url="https://custom.example.com/api",
            request_content='{"pvPlant":{}}',
            files=[],
            project_id="proj-1",
        )

        mock_build_url.assert_not_called()
        mock_client_cls.assert_called_once()
        assert mock_client_cls.call_args.kwargs["base_url"] == "https://custom.example.com/api"


class TestModelchainAsyncCall:
    """Unit tests for modelchain_async_call URL selection."""

    @patch("solarfarmer.endpoint_modelchains.Client")
    @patch("solarfarmer.endpoint_modelchains.build_api_url")
    def test_custom_api_url_bypasses_build_api_url(self, mock_build_url, mock_client_cls):
        """When api_url is provided, build_api_url is not called and Client receives the custom URL."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        # Return a failed POST so the function exits before polling
        mock_client.post.return_value = Response(
            code=500,
            url="https://custom.example.com/api/ModelChainAsync",
            data={},
            success=False,
            method="POST",
        )

        modelchain_async_call(
            endpoint_url="ModelChainAsync",
            api_version="latest",
            api_url="https://custom.example.com/api",
            request_content='{"pvPlant":{}}',
            files=[],
            project_id="proj-1",
        )

        mock_build_url.assert_not_called()
        mock_client_cls.assert_called_once()
        assert mock_client_cls.call_args.kwargs["base_url"] == "https://custom.example.com/api"
