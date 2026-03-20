import pytest

from solarfarmer.models.pvsystem.plant_defaults import DEFAULT_MUVOC_PCT, MIN_TEMP_VOC
from solarfarmer.models.pvsystem.plant_utils import (
    calculate_module_parameters,
    calculate_voc_at_min_temp,
    get_inverter_mppt,
    get_module_muvoc,
    is_blank,
    read_ond_file,
    read_pan_file,
)


@pytest.mark.parametrize(
    "reader,ext",
    [(read_pan_file, "PAN"), (read_ond_file, "OND")],
    ids=["PAN", "OND"],
)
class TestReadComponentFile:
    """Parametrized tests for read_pan_file and read_ond_file, which share the same interface."""

    def test_basic_key_value_pairs(self, reader, ext, tmp_path):
        content = "Manufacturer=TestCo\nModel=M-100\nCapacity=100\nType=Mono\n"
        (tmp_path / f"component.{ext}").write_text(content)
        result = reader(f"component.{ext}", str(tmp_path))
        assert isinstance(result, dict)
        assert result["Manufacturer"] == "TestCo"
        assert result["Model"] == "M-100"
        assert result["Capacity"] == "100"

    def test_special_characters_in_values(self, reader, ext, tmp_path):
        content = "Manufacturer=AB/CD\nModel=X-2024\nDescription=High (80% eff)\n"
        (tmp_path / f"special.{ext}").write_text(content)
        result = reader(f"special.{ext}", str(tmp_path))
        assert result["Manufacturer"] == "AB/CD"
        assert "80%" in result["Description"]

    def test_empty_lines_are_skipped(self, reader, ext, tmp_path):
        content = "Manufacturer=TestCo\n\nModel=M-100\n\nType=Mono\n"
        (tmp_path / f"gaps.{ext}").write_text(content)
        result = reader(f"gaps.{ext}", str(tmp_path))
        assert result["Manufacturer"] == "TestCo"
        assert result["Model"] == "M-100"
        assert result["Type"] == "Mono"

    def test_all_values_are_strings(self, reader, ext, tmp_path):
        content = "Key1=Value1\nKey2=Value2\nKey3=123\n"
        (tmp_path / f"types.{ext}").write_text(content)
        result = reader(f"types.{ext}", str(tmp_path))
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_latin1_bytes_silently_ignored(self, reader, ext, tmp_path):
        """Non-ASCII latin-1 bytes exercise the errors='ignore' code path without raising."""
        raw = "Manufacturer=\u00c9nerg\u00ede\nModel=Test\n".encode("latin-1")
        (tmp_path / f"latin1.{ext}").write_bytes(raw)
        result = reader(f"latin1.{ext}", str(tmp_path))
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result)


class TestIsBlank:
    def test_empty_string_returns_true(self):
        assert is_blank("") is True

    def test_nonempty_string_returns_false(self):
        assert is_blank("hello") is False

    def test_whitespace_string_is_not_blank(self):
        """Only exact empty string triggers True; whitespace is treated as non-blank."""
        assert is_blank(" ") is False

    @pytest.mark.parametrize("value", ["a", "0", " x ", "none", "null"])
    def test_various_nonempty_strings_return_false(self, value):
        assert is_blank(value) is False


class TestCalculateVocAtMinTemp:
    @pytest.mark.parametrize(
        "voc, muvoc, min_temp, expected",
        [
            # Standard: muvoc = voc * DEFAULT_MUVOC_PCT
            (
                40.0,
                40.0 * DEFAULT_MUVOC_PCT,
                MIN_TEMP_VOC,
                40.0 + 40.0 * DEFAULT_MUVOC_PCT * (MIN_TEMP_VOC - 25),
            ),
            # min_temp == 25 → no change
            (50.0, -0.1, 25.0, 50.0),
            # Positive muvoc edge case
            (30.0, 0.05, 0.0, 30.0 + 0.05 * (0.0 - 25)),
        ],
    )
    def test_formula(self, voc, muvoc, min_temp, expected):
        result = calculate_voc_at_min_temp(
            module_voc=voc, module_muvoc=muvoc, min_temp_voc=min_temp
        )
        assert result == pytest.approx(expected)

    def test_negative_temperature_increases_voc_with_negative_muvoc(self):
        """With negative muvoc and min_temp < 25, Voc should be higher than at STC."""
        voc = 40.0
        muvoc = -0.1  # V/°C
        result = calculate_voc_at_min_temp(voc, muvoc, -10.0)
        assert result > voc


class TestGetModuleMuvoc:
    def test_nonzero_voc_uses_default_pct(self):
        pan_dict = {"Voc": "40.0"}
        result = get_module_muvoc(pan_dict)
        assert result == pytest.approx(40.0 * DEFAULT_MUVOC_PCT)

    def test_zero_voc_reads_muVocSpec(self):
        """When Voc is 0.0, the function reads muVocSpec/1000."""
        pan_dict = {"Voc": "0", "muVocSpec": "-250"}
        result = get_module_muvoc(pan_dict)
        assert result == pytest.approx(-250 / 1000)


class TestGetInverterMppt:
    def test_nb_mppt_present(self):
        inverter_info = {"data": {"NbMPPT": "3"}}
        assert get_inverter_mppt(inverter_info) == 3

    def test_nb_mppt_missing_returns_1(self):
        inverter_info = {"data": {}}
        assert get_inverter_mppt(inverter_info) == 1

    def test_data_key_missing_returns_1(self):
        inverter_info = {}
        assert get_inverter_mppt(inverter_info) == 1


class TestCalculateModuleParameters:
    def _make_pan_info(self, voc="40.0", name="TestModule"):
        return {
            "name": name,
            "data": {"Voc": voc},
        }

    def test_adds_module_voc_at_min_temp(self):
        pan_info = self._make_pan_info(voc="40.0")
        result = calculate_module_parameters(pan_info)
        assert "module_voc_at_min_temp" in result
        assert isinstance(result["module_voc_at_min_temp"], float)

    def test_adds_module_spec_id(self):
        pan_info = self._make_pan_info(name="MySolarModule")
        result = calculate_module_parameters(pan_info)
        assert result["module_spec_id"] == "MySolarModule"

    def test_voc_at_min_temp_value_is_correct(self):
        voc = 40.0
        expected_muvoc = voc * DEFAULT_MUVOC_PCT
        expected_voc_at_min = voc + expected_muvoc * (MIN_TEMP_VOC - 25)
        pan_info = {"name": "mod", "data": {"Voc": str(voc)}}
        result = calculate_module_parameters(pan_info)
        assert result["module_voc_at_min_temp"] == pytest.approx(expected_voc_at_min)

    def test_returns_same_dict_object(self):
        pan_info = {"name": "mod", "data": {"Voc": "45.0"}}
        result = calculate_module_parameters(pan_info)
        assert result is pan_info
