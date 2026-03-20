import pytest

from solarfarmer.models.pvsystem.validation import ERRORS, ValidationMessage


class TestValidationMessage:
    """Unit tests for the ValidationMessage data-holder class."""

    def test_init_stores_field_and_message(self):
        """Constructor stores field and message as attributes."""
        vm = ValidationMessage(field="latitude", message="is required")
        assert vm.field == "latitude"
        assert vm.message == "is required"

    def test_init_default_severity_is_error(self):
        """Default severity is 'error' when not supplied."""
        vm = ValidationMessage(field="f", message="m")
        assert vm.severity == "error"

    def test_init_accepts_custom_severity(self):
        """A caller-supplied severity is stored as-is."""
        vm = ValidationMessage(field="f", message="m", severity="warning")
        assert vm.severity == "warning"

    @pytest.mark.parametrize(
        "field,message,severity,expected",
        [
            ("latitude", "is required", "error", "ERROR: latitude: is required"),
            ("count", "must be positive", "warning", "WARNING: count: must be positive"),
            ("name", "too short", "info", "INFO: name: too short"),
        ],
    )
    def test_repr_format(self, field, message, severity, expected):
        """__repr__ produces '<SEVERITY>: <field>: <message>'."""
        vm = ValidationMessage(field=field, message=message, severity=severity)
        assert repr(vm) == expected

    def test_repr_uppercases_severity(self):
        """Severity is always uppercased in __repr__, even when stored lowercase."""
        vm = ValidationMessage(field="x", message="y", severity="error")
        assert repr(vm).startswith("ERROR:")


class TestErrors:
    """Unit tests for the ERRORS format-string dictionary."""

    @pytest.mark.parametrize(
        "key",
        ["required", "min_length", "invalid_value", "out_of_range"],
    )
    def test_all_expected_keys_present(self, key):
        """Every expected error key exists in the ERRORS dict."""
        assert key in ERRORS

    def test_required_formats_with_field_name(self):
        """'required' template accepts a single positional argument."""
        msg = ERRORS["required"].format("latitude")
        assert "latitude" in msg

    def test_min_length_formats_with_field_and_length(self):
        """'min_length' template accepts field name and minimum length."""
        msg = ERRORS["min_length"].format("name", 3)
        assert "name" in msg
        assert "3" in msg

    def test_out_of_range_formats_with_four_arguments(self):
        """'out_of_range' template accepts field, value, min, and max."""
        msg = ERRORS["out_of_range"].format("pitch", -1, 0, 100)
        assert "pitch" in msg
        assert "-1" in msg
        assert "0" in msg
        assert "100" in msg
