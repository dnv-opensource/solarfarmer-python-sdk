import json
import pathlib
from datetime import timedelta

import pytest

from solarfarmer.config import MODELCHAIN_ASYNC_POLL_TIME
from solarfarmer.endpoint_modelchains_utils import (
    check_for_3d_files,
    extract_part,
    extract_poll_frequency,
    format_timedelta,
    get_file_paths_in_folder,
    get_files,
    get_plant_info_string,
    lowercase_keys_in_dict,
    parse_files_from_folder,
    parse_files_from_paths,
    path_exists,
    read_calculation_inputs_from_folder,
    summarize_custom_status_string,
)


class TestGetFilePathsInFolder:
    """Tests for get_file_paths_in_folder function."""

    def test_wildcard_pattern_matches_files(self, tmp_path):
        """Test that wildcard patterns match files with matching extensions."""
        # Create test files
        (tmp_path / "data1.dat").touch()
        (tmp_path / "data2.dat").touch()
        (tmp_path / "config.json").touch()

        # Test *.dat pattern
        result = get_file_paths_in_folder(tmp_path, "*.dat")
        assert len(result) == 2
        assert all(path.endswith(".dat") for path in result)

    @pytest.mark.parametrize("pattern", ["*.PAN", "*.pan", "*.Pan"])
    def test_wildcard_pattern_case_insensitive(self, tmp_path, pattern):
        """Test that wildcard patterns are case-insensitive."""
        # Create files with different case extensions
        (tmp_path / "module.PAN").touch()
        (tmp_path / "module.pan").touch()
        (tmp_path / "inverter.OND").touch()

        # All patterns should match all case variations
        result = get_file_paths_in_folder(tmp_path, pattern)
        assert len(result) == 2

        # Verify the right files are matched
        filenames = [pathlib.Path(p).name for p in result]
        assert "module.PAN" in filenames
        assert "module.pan" in filenames
        assert "inverter.OND" not in filenames

    def test_specific_filename_pattern(self, tmp_path):
        """Test that non-wildcard patterns match specific filenames."""
        # Create test files
        (tmp_path / "specific_file.gz").touch()
        (tmp_path / "other_file.gz").touch()
        (tmp_path / "MeteorologicalConditionsDatasetDto_Protobuf.gz").touch()

        # Test specific filename pattern
        result = get_file_paths_in_folder(
            tmp_path, "MeteorologicalConditionsDatasetDto_Protobuf.gz"
        )
        assert len(result) == 1
        assert result[0].endswith("MeteorologicalConditionsDatasetDto_Protobuf.gz")

    @pytest.mark.parametrize(
        "pattern,expected_count",
        [
            ("*.dat", 0),  # No .dat files
            ("nonexistent.gz", 0),  # Specific file doesn't exist
        ],
    )
    def test_no_matches_returns_empty_list(self, tmp_path, pattern, expected_count):
        """Test that no matches returns an empty list."""
        # Create files with different extensions
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.json").touch()

        result = get_file_paths_in_folder(tmp_path, pattern)
        assert len(result) == expected_count

    @pytest.mark.parametrize("path_type", ["string", "pathlib"])
    def test_accepts_different_path_types(self, tmp_path, path_type):
        """Test that the function accepts both string and pathlib.Path."""
        (tmp_path / "test.dat").touch()

        # Convert path based on parameter
        folder = str(tmp_path) if path_type == "string" else tmp_path

        result = get_file_paths_in_folder(folder, "*.dat")
        assert len(result) == 1

    def test_ignores_subdirectories(self, tmp_path):
        """Test that subdirectories are not included in results."""
        # Create files and subdirectories
        (tmp_path / "file.dat").touch()
        subdir = tmp_path / "subdir.dat"
        subdir.mkdir()

        # Should only find the file, not the directory
        result = get_file_paths_in_folder(tmp_path, "*.dat")
        assert len(result) == 1
        assert pathlib.Path(result[0]).is_file()

    def test_wildcard_only_matches_specified_extension(self, tmp_path):
        """Test that wildcard only matches the specified extension."""
        # Create files with similar but different extensions
        (tmp_path / "data.csv").touch()
        (tmp_path / "data.tsv").touch()
        (tmp_path / "data.json").touch()

        # Each pattern should only match its extension
        csv_files = get_file_paths_in_folder(tmp_path, "*.csv")
        assert len(csv_files) == 1
        assert csv_files[0].endswith(".csv")

        tsv_files = get_file_paths_in_folder(tmp_path, "*.tsv")
        assert len(tsv_files) == 1
        assert tsv_files[0].endswith(".tsv")

    def test_returns_full_paths(self, tmp_path):
        """Test that returned paths are absolute."""
        (tmp_path / "test.dat").touch()

        result = get_file_paths_in_folder(tmp_path, "*.dat")
        assert len(result) == 1
        assert pathlib.Path(result[0]).is_absolute()
        assert pathlib.Path(result[0]).exists()


class TestLowercaseKeysInDict:
    def test_flat_dict(self):
        assert lowercase_keys_in_dict({"Foo": 1, "BAR": 2}) == {"foo": 1, "bar": 2}

    def test_nested_dict(self):
        result = lowercase_keys_in_dict({"Outer": {"Inner": "value"}})
        assert result == {"outer": {"inner": "value"}}

    def test_list_of_dicts(self):
        result = lowercase_keys_in_dict([{"Key": "v1"}, {"Key": "v2"}])
        assert result == [{"key": "v1"}, {"key": "v2"}]

    def test_non_dict_passthrough(self):
        assert lowercase_keys_in_dict("hello") == "hello"
        assert lowercase_keys_in_dict(42) == 42
        assert lowercase_keys_in_dict(None) is None

    def test_already_lowercase(self):
        d = {"foo": {"bar": [{"baz": 1}]}}
        assert lowercase_keys_in_dict(d) == d

    def test_mixed_nesting(self):
        """Realistic API payload shape with mixed-case keys."""
        payload = {"PvPlant": {"Transformers": [{"InverterCount": 5}]}}
        result = lowercase_keys_in_dict(payload)
        assert "pvplant" in result
        assert "transformers" in result["pvplant"]
        assert result["pvplant"]["transformers"][0]["invertercount"] == 5


def _payload(pvplant_dict: dict) -> str:
    return json.dumps({"pvPlant": pvplant_dict})


class TestCheckFor3dFiles:
    def test_2d_layouts_only_returns_false(self):
        payload = _payload({"Transformers": [{"Inverters": [{"Layouts": [{"layoutCount": 1}]}]}]})
        assert check_for_3d_files(payload) is False

    def test_racks_no_layouts_returns_true(self):
        payload = _payload({"Racks": [{"id": "rack1"}]})
        assert check_for_3d_files(payload) is True

    def test_trackers_no_layouts_returns_true(self):
        payload = _payload({"Trackers": [{"id": "tracker1"}]})
        assert check_for_3d_files(payload) is True

    def test_racks_and_trackers_returns_true(self):
        payload = _payload({"Racks": [{}], "Trackers": [{}]})
        assert check_for_3d_files(payload) is True

    def test_empty_pvplant_returns_false(self):
        """No racks, no trackers, no layouts → 2D, returns False."""
        payload = _payload({})
        assert check_for_3d_files(payload) is False

    def test_empty_racks_list_returns_false(self):
        """An empty list is falsy; should be treated as no racks."""
        payload = _payload({"Racks": []})
        assert check_for_3d_files(payload) is False

    def test_both_layouts_and_racks_returns_false(self):
        """Layouts present overrides racks; 2D path takes precedence."""
        payload = _payload(
            {
                "Transformers": [{"Inverters": [{"Layouts": [{"layoutCount": 1}]}]}],
                "Racks": [{"id": "rack1"}],
            }
        )
        assert check_for_3d_files(payload) is False


class TestPathExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        assert path_exists(f) is True

    def test_existing_directory(self, tmp_path):
        assert path_exists(tmp_path) is True

    def test_missing_path(self, tmp_path):
        assert path_exists(tmp_path / "nonexistent") is False

    def test_accepts_string(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        assert path_exists(str(f)) is True


class TestExtractPollFrequency:
    def test_custom_poll_time_extracted(self):
        freq, remaining = extract_poll_frequency(async_poll_time=2.5, other_param="x")
        assert freq == 2.5
        assert "async_poll_time" not in remaining
        assert remaining == {"other_param": "x"}

    def test_missing_poll_time_uses_default(self):
        freq, remaining = extract_poll_frequency(other_param="x")
        assert freq == MODELCHAIN_ASYNC_POLL_TIME
        assert remaining == {"other_param": "x"}

    def test_no_kwargs_uses_default(self):
        freq, remaining = extract_poll_frequency()
        assert freq == MODELCHAIN_ASYNC_POLL_TIME
        assert remaining == {}


class TestFormatTimedelta:
    @pytest.mark.parametrize(
        "seconds_total, fmt, expected",
        [
            (0, "{hours_total}:{minutes2}:{seconds2}", "0:00:00"),
            (90, "{hours_total}:{minutes2}:{seconds2}", "0:01:30"),
            (3661, "{hours_total}:{minutes2}:{seconds2}", "1:01:01"),
            (86400, "{days} days, {hours2}:{minutes2}:{seconds2}", "1 days, 00:00:00"),
            (3723, "{minutes_total}:{seconds2}", "62:03"),
        ],
    )
    def test_from_int_seconds(self, seconds_total, fmt, expected):
        assert format_timedelta(seconds_total, fmt) == expected

    def test_from_timedelta_object(self):
        td = timedelta(hours=1, minutes=2, seconds=3)
        result = format_timedelta(td, "{hours_total}:{minutes2}:{seconds2}")
        assert result == "1:02:03"

    def test_zero_timedelta(self):
        assert format_timedelta(timedelta(0), "{hours_total}:{minutes2}:{seconds2}") == "0:00:00"

    def test_two_digit_zero_padding(self):
        result = format_timedelta(65, "{hours2}:{minutes2}:{seconds2}")
        assert result == "00:01:05"


class TestExtractPart:
    # A realistic v6 status string
    STATUS = (
        "Running 1 chunks. "
        "Shading: 36/60 tasks complete. "
        "ModelChain: 0/46 tasks complete. "
        "Post chunking: 0/unknown tasks complete."
    )

    def test_shading_extracted(self):
        result = extract_part("Shading", self.STATUS)
        assert result == ["36", "60 tasks complete"]

    def test_model_chain_extracted(self):
        result = extract_part("ModelChain", self.STATUS)
        assert result == ["0", "46 tasks complete"]

    def test_post_chunking_extracted(self):
        result = extract_part("Post chunking", self.STATUS)
        assert result == ["0", "unknown tasks complete"]

    def test_missing_part_returns_none(self):
        assert extract_part("NonExistent", self.STATUS) is None

    def test_empty_string_returns_none(self):
        assert extract_part("Shading", "") is None

    def test_completed_shading(self):
        status = "Running 1 chunks. Shading: 60/60 tasks complete. ModelChain: 0/46 tasks complete. Post chunking: 0/unknown tasks complete."
        assert extract_part("Shading", status) == ["60", "60 tasks complete"]

    def test_part_without_slash_returns_none_via_except(self):
        """A part value with no '/' causes an IndexError; the except clause returns None."""
        assert extract_part("Shading", "Shading: no_slash_here") is None


class TestSummarizeCustomStatusString:
    def test_none_input_returns_none(self):
        assert summarize_custom_status_string(None) is None

    def test_v5_style_string_returned_unchanged(self):
        s = "SomeV5Status"
        assert summarize_custom_status_string(s) == s

    def test_zero_chunks_returns_pending(self):
        s = (
            "Running 0 chunks. "
            "Shading: 0/unknown tasks complete. "
            "ModelChain: 0/unknown tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert summarize_custom_status_string(s) == "Calculation pending..."

    def test_shading_unknown_returns_pending(self):
        s = (
            "Running 1 chunks. "
            "Shading: 0/unknown tasks complete. "
            "ModelChain: 0/unknown tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert summarize_custom_status_string(s) == "Calculation pending..."

    def test_shading_in_progress(self):
        s = (
            "Running 1 chunks. "
            "Shading: 36/60 tasks complete. "
            "ModelChain: 0/46 tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert (
            summarize_custom_status_string(s)
            == "Running shading pre-processing (36/60 tasks complete)"
        )

    def test_model_chain_in_progress(self):
        s = (
            "Running 1 chunks. "
            "Shading: 60/60 tasks complete. "
            "ModelChain: 4/46 tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert (
            summarize_custom_status_string(s)
            == "Running model chain calculation (4/46 tasks complete)"
        )

    def test_post_chunking_in_progress(self):
        s = (
            "Running 1 chunks. "
            "Shading: 60/60 tasks complete. "
            "ModelChain: 46/46 tasks complete. "
            "Post chunking: 41/46 tasks complete."
        )
        assert summarize_custom_status_string(s) == "Running post-processing (41/46 tasks complete)"

    def test_all_complete_returns_finishing(self):
        s = (
            "Running 1 chunks. "
            "Shading: 60/60 tasks complete. "
            "ModelChain: 46/46 tasks complete. "
            "Post chunking: 46/46 tasks complete."
        )
        assert summarize_custom_status_string(s) == "Finishing up."

    def test_model_chain_unknown_returns_pending(self):
        s = (
            "Running 1 chunks. "
            "Shading: 60/60 tasks complete. "
            "ModelChain: 0/unknown tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert summarize_custom_status_string(s) == "Model chain calculation pending..."

    def test_post_chunking_unknown_returns_pending(self):
        """When post-chunking total is 'unknown' a pending message is returned."""
        s = (
            "Running 1 chunks. "
            "Shading: 60/60 tasks complete. "
            "ModelChain: 46/46 tasks complete. "
            "Post chunking: 0/unknown tasks complete."
        )
        assert summarize_custom_status_string(s) == "Post-processing pending..."

    def test_non_integer_chunk_count_returns_pending(self):
        """A non-numeric chunk count falls through ValueError and yields pending."""
        s = "Running X chunks. Shading: 0/unknown tasks complete. ModelChain: 0/unknown tasks complete. Post chunking: 0/unknown tasks complete."
        assert summarize_custom_status_string(s) == "Calculation pending..."

    def test_missing_parts_returns_original_string(self):
        """A v6-style string where extract_part returns None falls back to the original."""
        # Use a chunk-containing string without Shading/ModelChain/Post chunking sections so
        # extract_part returns None for all three, triggering the guard-return.
        # The string must not contain " tasks complete" since the function strips it early.
        s = "Running 1 chunks. SomeOtherPart: 1/2."
        assert summarize_custom_status_string(s) == s


class TestGetPlantInfoString:
    @pytest.mark.parametrize(
        "plant_info, expected_substrings",
        [
            # 3D Trackers
            (
                {
                    "isPlant3D": True,
                    "isPlantTrackers": True,
                    "numberOf2DLayouts": 0,
                    "acCapacityOfPlantInMW": 5.0,
                },
                ["3D", "Trackers", "5.0 MW"],
            ),
            # 3D Racks
            (
                {
                    "isPlant3D": True,
                    "isPlantTrackers": False,
                    "numberOf2DLayouts": 0,
                    "acCapacityOfPlantInMW": 10.0,
                },
                ["3D", "Racks", "10.0 MW"],
            ),
            # 2D Racks with multiple layouts
            (
                {
                    "isPlant3D": False,
                    "isPlantTrackers": False,
                    "numberOf2DLayouts": 3,
                    "acCapacityOfPlantInMW": 2.5,
                },
                ["2D", "Racks", "2.5 MW", "3 2D layouts"],
            ),
            # 2D Single layout (singular)
            (
                {
                    "isPlant3D": False,
                    "isPlantTrackers": False,
                    "numberOf2DLayouts": 1,
                    "acCapacityOfPlantInMW": 1.0,
                },
                ["2D", "Racks", "1.0 MW", "1 2D layout"],
            ),
        ],
    )
    def test_plant_info_string_content(self, plant_info, expected_substrings):
        result = get_plant_info_string(plant_info)
        for substring in expected_substrings:
            assert substring in result

    def test_keys_are_case_insensitive(self):
        """Keys that arrive in mixed case from API must still be parsed."""
        plant_info = {
            "IsPlant3D": True,
            "IsPlantTrackers": True,
            "NumberOf2DLayouts": 0,
            "AcCapacityOfPlantInMW": 7.5,
        }
        result = get_plant_info_string(plant_info)
        assert "3D" in result
        assert "7.5 MW" in result

    def test_2d_layout_count_not_shown_for_3d(self):
        plant_info = {
            "isPlant3D": True,
            "isPlantTrackers": False,
            "numberOf2DLayouts": 4,
            "acCapacityOfPlantInMW": 5.0,
        }
        result = get_plant_info_string(plant_info)
        assert "layout" not in result


class TestGetFiles:
    """Tests for get_files(), which scans a folder for met/PAN/OND/HOR files."""

    def test_single_dat_file_mapped_as_tmyfile(self, tmp_path):
        (tmp_path / "weather.DAT").write_bytes(b"fake")
        files = get_files(tmp_path)
        try:
            assert any(name == "tmyFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_multiple_dat_files_raises(self, tmp_path):
        (tmp_path / "a.DAT").write_bytes(b"x")
        (tmp_path / "b.DAT").write_bytes(b"y")
        with pytest.raises(RuntimeError, match="DAT"):
            get_files(tmp_path)

    def test_pan_and_ond_files_included(self, tmp_path):
        (tmp_path / "weather.DAT").write_bytes(b"met")
        (tmp_path / "module.PAN").write_bytes(b"pan")
        (tmp_path / "inverter.OND").write_bytes(b"ond")
        files = get_files(tmp_path)
        try:
            names = [name for name, _ in files]
            assert "panFiles" in names
            assert "ondFiles" in names
        finally:
            for _, fh in files:
                fh.close()

    def test_two_met_file_types_raises(self, tmp_path):
        """DAT + TSV in the same folder triggers the multiple-met-files RuntimeError."""
        (tmp_path / "weather.DAT").write_bytes(b"met")
        (tmp_path / "weather.tsv").write_bytes(b"met2")
        with pytest.raises(RuntimeError, match="meteorological"):
            get_files(tmp_path)

    def test_empty_folder_returns_empty_list(self, tmp_path):
        assert get_files(tmp_path) == []

    def test_hor_file_mapped_as_horfile(self, tmp_path):
        (tmp_path / "horizon.HOR").write_bytes(b"hor")
        files = get_files(tmp_path)
        try:
            names = [name for name, _ in files]
            assert "horFile" in names
        finally:
            for _, fh in files:
                fh.close()

    def test_single_tsv_file_mapped_as_tmyfile(self, tmp_path):
        (tmp_path / "weather.tsv").write_bytes(b"met")
        files = get_files(tmp_path)
        try:
            assert any(name == "tmyFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_multiple_tsv_files_raises(self, tmp_path):
        (tmp_path / "a.tsv").write_bytes(b"met1")
        (tmp_path / "b.tsv").write_bytes(b"met2")
        with pytest.raises(RuntimeError, match="TSV"):
            get_files(tmp_path)

    def test_single_csv_file_mapped_as_pvsyst(self, tmp_path):
        (tmp_path / "weather.csv").write_bytes(b"met")
        files = get_files(tmp_path)
        try:
            assert any(name == "pvSystStandardFormatFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_multiple_csv_files_raises(self, tmp_path):
        (tmp_path / "a.csv").write_bytes(b"met1")
        (tmp_path / "b.csv").write_bytes(b"met2")
        with pytest.raises(RuntimeError, match="CSV"):
            get_files(tmp_path)

    def test_gz_protobuf_file_mapped_as_met_data_transfer(self, tmp_path):
        (tmp_path / "MeteorologicalConditionsDatasetDto_Protobuf.gz").write_bytes(b"proto")
        files = get_files(tmp_path)
        try:
            assert any(name == "metDataTransferFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_multiple_hor_files_raises(self, tmp_path):
        (tmp_path / "a.HOR").write_bytes(b"hor1")
        (tmp_path / "b.HOR").write_bytes(b"hor2")
        with pytest.raises(RuntimeError, match="HOR"):
            get_files(tmp_path)


class TestReadCalculationInputsFromFolder:
    """Tests for read_calculation_inputs_from_folder."""

    def test_reads_single_json_file_from_folder(self, tmp_path):
        data = {"location": {"latitude": 46.9}}
        (tmp_path / "inputs.json").write_text(json.dumps(data))
        result = read_calculation_inputs_from_folder(tmp_path, None)
        assert json.loads(result) == data

    def test_explicit_path_used_directly(self, tmp_path):
        data = {"pvPlant": {}}
        explicit = tmp_path / "explicit.json"
        explicit.write_text(json.dumps(data))
        # Add a second json file that should be ignored
        (tmp_path / "other.json").write_text("{}")
        result = read_calculation_inputs_from_folder(tmp_path, str(explicit))
        assert json.loads(result) == data

    def test_multiple_json_files_raises(self, tmp_path):
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        with pytest.raises(RuntimeError, match="JSON"):
            read_calculation_inputs_from_folder(tmp_path, None)

    def test_no_json_file_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="JSON"):
            read_calculation_inputs_from_folder(tmp_path, None)


class TestParseFilesFromFolder:
    """Tests for parse_files_from_folder which wraps get_files + read_calculation_inputs."""

    def test_happy_path_returns_request_content_and_files(self, tmp_path):
        """Happy path: folder with a met file and JSON returns serialized content and files."""
        (tmp_path / "weather.DAT").write_bytes(b"met")
        data = {"pvPlant": {}}
        (tmp_path / "inputs.json").write_text(json.dumps(data))

        request_content, files = parse_files_from_folder(str(tmp_path), None)
        try:
            assert json.loads(request_content) == data
            assert any(name == "tmyFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_exception_during_json_read_closes_stack_and_reraises(self, tmp_path):
        """When the JSON step fails, ExitStack is closed before re-raising."""
        (tmp_path / "weather.DAT").write_bytes(b"met")
        # No JSON file present — read_calculation_inputs_from_folder raises RuntimeError
        with pytest.raises(RuntimeError, match="JSON"):
            parse_files_from_folder(str(tmp_path), None)


class TestParseFilesFromPaths:
    """Tests for parse_files_from_paths error branches and file-type routing."""

    def test_pan_paths_none_raises(self, tmp_path):
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        with pytest.raises(FileNotFoundError, match="PAN"):
            parse_files_from_paths(
                str(met),
                None,
                pan_file_paths=None,
                ond_file_paths=[],
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )

    def test_ond_paths_none_raises(self, tmp_path):
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        pan = tmp_path / "module.PAN"
        pan.write_bytes(b"pan")
        with pytest.raises(FileNotFoundError, match="OND"):
            parse_files_from_paths(
                str(met),
                None,
                pan_file_paths=[str(pan)],
                ond_file_paths=None,
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )

    def test_unknown_met_extension_raises(self, tmp_path):
        met = tmp_path / "weather.xyz"
        met.write_bytes(b"met")
        with pytest.raises(ValueError, match=".xyz"):
            parse_files_from_paths(
                str(met),
                None,
                pan_file_paths=[],
                ond_file_paths=[],
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )

    @pytest.mark.parametrize(
        "ext,field",
        [(".tsv", "tmyFile"), (".dat", "tmyFile"), (".csv", "pvSystStandardFormatFile")],
    )
    def test_met_file_extension_determines_field_name(self, ext, field, tmp_path):
        met = tmp_path / f"weather{ext}"
        met.write_bytes(b"met")
        _, files = parse_files_from_paths(
            str(met),
            None,
            pan_file_paths=[],
            ond_file_paths=[],
            parse_energy_calc_inputs=False,
            energy_calculation_inputs_file_path=None,
        )
        try:
            names = [name for name, _ in files]
            assert field in names
        finally:
            for _, fh in files:
                fh.close()

    def test_gz_met_extension_mapped_as_met_data_transfer(self, tmp_path):
        """A .gz meteorological file is mapped to the 'metDataTransferFile' field."""
        met = tmp_path / "weather.gz"
        met.write_bytes(b"proto")
        _, files = parse_files_from_paths(
            str(met),
            None,
            pan_file_paths=[],
            ond_file_paths=[],
            parse_energy_calc_inputs=False,
            energy_calculation_inputs_file_path=None,
        )
        try:
            assert any(name == "metDataTransferFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_valid_horizon_file_included_as_hor_file(self, tmp_path):
        """A horizon file path that exists is appended as 'horFile'."""
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        hor = tmp_path / "horizon.HOR"
        hor.write_bytes(b"hor")
        _, files = parse_files_from_paths(
            str(met),
            str(hor),
            pan_file_paths=[],
            ond_file_paths=[],
            parse_energy_calc_inputs=False,
            energy_calculation_inputs_file_path=None,
        )
        try:
            assert any(name == "horFile" for name, _ in files)
        finally:
            for _, fh in files:
                fh.close()

    def test_nonexistent_horizon_file_raises(self, tmp_path):
        """A horizon_file_path that does not exist raises FileNotFoundError."""
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        with pytest.raises(FileNotFoundError, match="Path does not exist"):
            parse_files_from_paths(
                str(met),
                str(tmp_path / "missing.HOR"),
                pan_file_paths=[],
                ond_file_paths=[],
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )

    def test_nonexistent_pan_file_in_list_raises(self, tmp_path):
        """A PAN path in the list that does not exist raises FileNotFoundError."""
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        with pytest.raises(FileNotFoundError, match="Path does not exist"):
            parse_files_from_paths(
                str(met),
                None,
                pan_file_paths=[str(tmp_path / "ghost.PAN")],
                ond_file_paths=[],
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )

    def test_nonexistent_ond_file_in_list_raises(self, tmp_path):
        """An OND path in the list that does not exist raises FileNotFoundError."""
        met = tmp_path / "weather.tsv"
        met.write_bytes(b"met")
        with pytest.raises(FileNotFoundError, match="Path does not exist"):
            parse_files_from_paths(
                str(met),
                None,
                pan_file_paths=[],
                ond_file_paths=[str(tmp_path / "ghost.OND")],
                parse_energy_calc_inputs=False,
                energy_calculation_inputs_file_path=None,
            )
