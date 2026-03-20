import pytest
from pydantic import ValidationError

from solarfarmer.models import (
    DiffuseModel,
    EnergyCalculationOptions,
    Inverter,
    Layout,
    Location,
    MountingTypeSpecification,
    OndFileSupplements,
    PanFileSupplements,
    TrackerSystem,
    TransformerLossModelTypes,
    TransformerSpecification,
)

# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


class TestLocationValidation:
    def test_longitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="longitude"):
            Location(latitude=0, longitude=200)

    def test_latitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="latitude"):
            Location(latitude=100, longitude=0)

    def test_altitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="altitude"):
            Location(latitude=0, longitude=0, altitude=20000)

    def test_valid_extremes(self) -> None:
        loc = Location(latitude=-90, longitude=-180, altitude=-450)
        assert loc.latitude == -90
        assert loc.longitude == -180


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


class TestLayoutValidation:
    def test_layout_count_zero(self) -> None:
        with pytest.raises(ValidationError, match="layout_count"):
            Layout(
                layout_count=0,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
            )

    def test_empty_module_spec_id(self) -> None:
        with pytest.raises(ValidationError, match="module_specification_id"):
            Layout(
                layout_count=1,
                module_specification_id="",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
            )

    def test_dc_ohmic_loss_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="dc_ohmic_connector_loss"):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
                dc_ohmic_connector_loss=1.5,
            )

    def test_module_mismatch_loss_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="module_mismatch_loss"):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
                module_mismatch_loss=0.5,
            )

    def test_module_quality_factor_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="module_quality_factor"):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
                module_quality_factor=0.5,
            )

    def test_azimuth_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="azimuth"):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=400,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
            )


# ---------------------------------------------------------------------------
# Inverter
# ---------------------------------------------------------------------------


class TestInverterValidation:
    def test_empty_spec_id(self) -> None:
        with pytest.raises(ValidationError, match="inverter_spec_id"):
            Inverter(inverter_spec_id="", inverter_count=1)

    def test_count_zero(self) -> None:
        with pytest.raises(ValidationError, match="inverter_count"):
            Inverter(inverter_spec_id="inv1", inverter_count=0)

    def test_ac_loss_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="ac_wiring_ohmic_loss"):
            Inverter(inverter_spec_id="inv1", inverter_count=1, ac_wiring_ohmic_loss=2.0)


# ---------------------------------------------------------------------------
# TransformerSpecification
# ---------------------------------------------------------------------------


class TestTransformerSpecValidation:
    def test_simple_loss_requires_loss_factor(self) -> None:
        with pytest.raises(ValidationError, match="loss_factor is required"):
            TransformerSpecification(
                model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
            )

    def test_no_load_requires_all_three(self) -> None:
        with pytest.raises(ValidationError, match="rated_power.*no_load_loss.*full_load_ohmic"):
            TransformerSpecification(
                model_type=TransformerLossModelTypes.NO_LOAD_AND_OHMIC,
            )

    def test_no_load_partial_missing(self) -> None:
        with pytest.raises(ValidationError, match="full_load_ohmic_loss"):
            TransformerSpecification(
                model_type=TransformerLossModelTypes.NO_LOAD_AND_OHMIC,
                rated_power=1000.0,
                no_load_loss=10.0,
            )

    def test_loss_factor_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="loss_factor"):
            TransformerSpecification(
                model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
                loss_factor=2.0,
            )

    def test_valid_simple_loss(self) -> None:
        spec = TransformerSpecification(
            model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
            loss_factor=0.02,
        )
        assert spec.loss_factor == 0.02

    def test_valid_no_load(self) -> None:
        spec = TransformerSpecification(
            model_type=TransformerLossModelTypes.NO_LOAD_AND_OHMIC,
            rated_power=1000.0,
            no_load_loss=10.0,
            full_load_ohmic_loss=20.0,
        )
        assert spec.rated_power == 1000.0


# ---------------------------------------------------------------------------
# MountingTypeSpecification
# ---------------------------------------------------------------------------


class TestMountingSpecValidation:
    def test_soiling_wrong_length(self) -> None:
        with pytest.raises(ValidationError, match="12 values"):
            MountingTypeSpecification(
                is_tracker=False,
                number_of_modules_high=1,
                modules_are_landscape=False,
                rack_height=0.7,
                y_spacing_between_modules=0.03,
                frame_bottom_width=0.0,
                constant_heat_transfer_coefficient=29.0,
                convective_heat_transfer_coefficient=0.0,
                monthly_soiling_loss=[0.0] * 6,
            )

    def test_soiling_value_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="between 0 and 1"):
            MountingTypeSpecification(
                is_tracker=False,
                number_of_modules_high=1,
                modules_are_landscape=False,
                rack_height=0.7,
                y_spacing_between_modules=0.03,
                frame_bottom_width=0.0,
                constant_heat_transfer_coefficient=29.0,
                convective_heat_transfer_coefficient=0.0,
                monthly_soiling_loss=[1.5] * 12,
            )

    def test_rack_height_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="rack_height"):
            MountingTypeSpecification(
                is_tracker=False,
                number_of_modules_high=1,
                modules_are_landscape=False,
                rack_height=200.0,
                y_spacing_between_modules=0.03,
                frame_bottom_width=0.0,
                constant_heat_transfer_coefficient=29.0,
                convective_heat_transfer_coefficient=0.0,
                monthly_soiling_loss=[0.0] * 12,
            )


# ---------------------------------------------------------------------------
# TrackerSystem
# ---------------------------------------------------------------------------


class TestTrackerSystemValidation:
    def test_rotation_min_positive(self) -> None:
        with pytest.raises(ValidationError, match="rotation_min_deg"):
            TrackerSystem(system_plane_azimuth=0, system_plane_tilt=0, rotation_min_deg=10)

    def test_rotation_max_negative(self) -> None:
        with pytest.raises(ValidationError, match="rotation_max_deg"):
            TrackerSystem(system_plane_azimuth=0, system_plane_tilt=0, rotation_max_deg=-10)


# ---------------------------------------------------------------------------
# PanFileSupplements
# ---------------------------------------------------------------------------


class TestPanSupplementsValidation:
    def test_correction_factor_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="modeling_correction_factor"):
            PanFileSupplements(modeling_correction_factor=2.0)

    def test_lid_loss_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="lid_loss"):
            PanFileSupplements(lid_loss=0.5)

    def test_bifaciality_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="bifaciality_factor"):
            PanFileSupplements(bifaciality_factor=1.5)


# ---------------------------------------------------------------------------
# OndFileSupplements
# ---------------------------------------------------------------------------


class TestOndSupplementsValidation:
    def test_negative_derate_voltages(self) -> None:
        with pytest.raises(ValidationError, match="must be >= 0"):
            OndFileSupplements(dc_voltage_derate_voltages=[-1.0, 100.0])

    def test_negative_derate_output(self) -> None:
        with pytest.raises(ValidationError, match="must be >= 0"):
            OndFileSupplements(dc_voltage_derate_output=[-5.0])


# ---------------------------------------------------------------------------
# EnergyCalculationOptions
# ---------------------------------------------------------------------------


class TestCalcOptionsValidation:
    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            EnergyCalculationOptions()  # type: ignore[call-arg]

    def test_solar_zenith_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="solar_zenith_angle_limit"):
            EnergyCalculationOptions(
                diffuse_model=DiffuseModel.PEREZ,
                include_horizon=False,
                solar_zenith_angle_limit=95.0,
            )

    def test_defaults_match_csharp(self) -> None:
        opts = EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
        )
        assert opts.calculation_year == 1990
        assert opts.treat_circumsolar_as_direct is True
        assert opts.apply_spectral_mismatch_modifier is False
        assert opts.include_soiling_loss_in_temperature_model is True
        assert opts.use_iam_for_temperature_model is True
        assert opts.return_pv_syst_format_time_series_results is True

    def test_is_mutable(self) -> None:
        opts = EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
        )
        opts.calculation_year = 2024
        assert opts.calculation_year == 2024
