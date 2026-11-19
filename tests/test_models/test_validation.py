import json
import math
import warnings
from datetime import UTC

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
    QuadDouble,
    Rack,
    RackOrientationWarning,
    TrackerCondition,
    TrackerSystem,
    TransformerLossModelTypes,
    TransformerSpecification,
    Vector3Double,
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

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("terrain_azimuth", -360.1),
            ("terrain_azimuth", 360.1),
            ("terrain_slope", -90.1),
            ("terrain_slope", 90.1),
        ],
    )
    def test_terrain_out_of_range(self, field: str, value: float) -> None:
        with pytest.raises(ValidationError, match=field):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
                **{field: value},
            )

    @pytest.mark.parametrize(
        ("azimuth", "slope"), [(-360.0, -90.0), (360.0, 90.0), (-90.0, -5.0), (0.0, 0.0)]
    )
    def test_terrain_limits_are_inclusive(self, azimuth: float, slope: float) -> None:
        layout = Layout(
            layout_count=1,
            module_specification_id="m",
            mounting_type_id="mt",
            is_trackers=False,
            azimuth=180,
            pitch=5,
            total_number_of_strings=1,
            string_length=1,
            terrain_azimuth=azimuth,
            terrain_slope=slope,
        )
        assert layout.terrain_azimuth == azimuth
        assert layout.terrain_slope == slope

    def test_dc_ohmic_resistance_and_loss_both_set_raises(self) -> None:
        with pytest.raises(ValidationError, match="dc_ohmic_connector_resistance"):
            Layout(
                layout_count=1,
                module_specification_id="m",
                mounting_type_id="mt",
                is_trackers=False,
                azimuth=180,
                pitch=5,
                total_number_of_strings=1,
                string_length=1,
                dc_ohmic_connector_loss=0.01,
                dc_ohmic_connector_resistance=0.5,
            )

    def test_dc_ohmic_resistance_alone_is_valid(self) -> None:
        layout = Layout(
            layout_count=1,
            module_specification_id="m",
            mounting_type_id="mt",
            is_trackers=False,
            azimuth=180,
            pitch=5,
            total_number_of_strings=1,
            string_length=1,
            dc_ohmic_connector_resistance=0.5,
        )
        assert layout.dc_ohmic_connector_resistance == 0.5
        assert layout.dc_ohmic_connector_loss == 0.0

    def test_dc_ohmic_resistance_with_loss_zero_is_valid(self) -> None:
        layout = Layout(
            layout_count=1,
            module_specification_id="m",
            mounting_type_id="mt",
            is_trackers=False,
            azimuth=180,
            pitch=5,
            total_number_of_strings=1,
            string_length=1,
            dc_ohmic_connector_loss=0.0,
            dc_ohmic_connector_resistance=0.3,
        )
        assert layout.dc_ohmic_connector_resistance == 0.3


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


# ---------------------------------------------------------------------------
# TrackerCondition
# ---------------------------------------------------------------------------


class TestTrackerConditionValidation:
    def test_both_rotation_fields_raises(self) -> None:
        from datetime import datetime

        with pytest.raises(ValidationError, match="tracker_rotations_array_values"):
            TrackerCondition(
                period_in_minutes=60.0,
                start_of_period=datetime(2020, 1, 1, tzinfo=UTC),
                tracker_rotations_array_values=[1234, -500],
                tracker_rotation_unique_value=0,
            )

    def test_unique_value_out_of_range_raises(self) -> None:
        from datetime import datetime

        with pytest.raises(ValidationError, match="tracker_rotation_unique_value"):
            TrackerCondition(
                period_in_minutes=5.0,
                start_of_period=datetime(2018, 1, 1, tzinfo=UTC),
                tracker_rotation_unique_value=9000,  # > 8990
            )

    def test_unique_value_negative_out_of_range_raises(self) -> None:
        from datetime import datetime

        with pytest.raises(ValidationError, match="tracker_rotation_unique_value"):
            TrackerCondition(
                period_in_minutes=5.0,
                start_of_period=datetime(2018, 1, 1, tzinfo=UTC),
                tracker_rotation_unique_value=-9000,  # < -8990
            )

    def test_array_value_out_of_range_raises(self) -> None:
        from datetime import datetime

        with pytest.raises(ValidationError, match="tracker_rotations_array_values"):
            TrackerCondition(
                period_in_minutes=5.0,
                start_of_period=datetime(2018, 1, 1, tzinfo=UTC),
                tracker_rotations_array_values=[-1570, 9000],  # 9000 > 8990
            )

    def test_boundary_values_are_valid(self) -> None:
        from datetime import datetime

        cond = TrackerCondition(
            period_in_minutes=5.0,
            start_of_period=datetime(2018, 1, 1, tzinfo=UTC),
            tracker_rotations_array_values=[-8990, 0, 8990],
        )
        assert cond.tracker_rotations_array_values == [-8990, 0, 8990]


# ---------------------------------------------------------------------------
# QuadDouble / Rack orientation
# ---------------------------------------------------------------------------


def _quad(*corners: tuple[float, float, float]) -> QuadDouble:
    p1, p2, p3, p4 = (Vector3Double(x=x, y=y, z=z) for x, y, z in corners)
    return QuadDouble(p1=p1, p2=p2, p3=p3, p4=p4)


# South-facing rack in the documented order (P1 SW-low, P2 NW-high, P3 NE-high,
# P4 SE-low): 10 m wide, 5 m deep, rising 3 m over 4 m
SOUTH_FACING = ((0.0, 0.0, 0.0), (0.0, 4.0, 3.0), (10.0, 4.0, 3.0), (10.0, 0.0, 0.0))
# The same corners in the reverse order (P1 SW-low, P2 SE-low, P3 NE-high, P4 NW-high)
SOUTH_FACING_REVERSED = tuple(SOUTH_FACING[i] for i in (0, 3, 2, 1))


class TestQuadDoubleGeometry:
    def test_south_facing_rack(self) -> None:
        quad = _quad(*SOUTH_FACING)
        assert quad.width == pytest.approx(10.0)
        assert quad.depth == pytest.approx(5.0)
        assert quad.front_normal == pytest.approx((0.0, -0.6, 0.8))
        assert quad.tilt == pytest.approx(math.degrees(math.atan2(3.0, 4.0)))
        assert quad.azimuth == pytest.approx(180.0)

    def test_modelchainasync_documentation_example(self) -> None:
        """The rack in the web API's ModelChainAsync example faces south at about 34 degrees."""
        quad = _quad(
            (633616.55525403516, 4502376.1064225091, 308.44455607951465),
            (633616.60684414359, 4502378.5736383246, 310.10791430261804),
            (633640.11553953763, 4502378.5736383246, 309.37877723037911),
            (633640.0639494292, 4502376.1064225091, 307.71541900727573),
        )
        assert quad.tilt == pytest.approx(34.0, abs=0.1)
        assert quad.azimuth == pytest.approx(177.4, abs=0.1)
        assert quad.depth == pytest.approx(2.976, abs=0.001)

    def test_east_facing_rack(self) -> None:
        # Low edge on the east side; seen from the front, P1 is the south end of it
        quad = _quad((4.0, 0.0, 0.0), (0.0, 0.0, 3.0), (0.0, 10.0, 3.0), (4.0, 10.0, 0.0))
        assert quad.azimuth == pytest.approx(90.0)
        assert quad.tilt == pytest.approx(math.degrees(math.atan2(3.0, 4.0)))

    def test_horizontal_quad_faces_up(self) -> None:
        quad = _quad((0.0, 0.0, 0.0), (0.0, 5.0, 0.0), (10.0, 5.0, 0.0), (10.0, 0.0, 0.0))
        assert quad.front_normal == pytest.approx((0.0, 0.0, 1.0))
        assert quad.tilt == pytest.approx(0.0)

    def test_reversed_order_faces_down(self) -> None:
        quad = _quad(*SOUTH_FACING_REVERSED)
        assert quad.front_normal[2] < 0
        assert quad.tilt > 90.0

    def test_collinear_corners_have_no_normal(self) -> None:
        quad = _quad((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (3.0, 0.0, 0.0))
        with pytest.raises(ValueError, match="no area"):
            _ = quad.front_normal


class TestRackOrientation:
    def test_documented_order_does_not_warn(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RackOrientationWarning)
            Rack(id=0, mounting_type_id="m1", quad=_quad(*SOUTH_FACING))

    def test_reversed_order_warns(self) -> None:
        with pytest.warns(RackOrientationWarning, match="reverse order") as record:
            Rack(id=7, mounting_type_id="m1", quad=_quad(*SOUTH_FACING_REVERSED))
        assert "Rack 7" in str(record[0].message)
        assert record[0].filename == __file__  # points at the caller, not pydantic

    def test_reversed_order_warns_when_loaded_from_json(self) -> None:
        corners = {
            f"p{i}": dict(zip("xyz", c, strict=True))
            for i, c in enumerate(SOUTH_FACING_REVERSED, 1)
        }
        payload = json.dumps({"id": 0, "mountingTypeID": "m1", "quad": corners})

        with pytest.warns(RackOrientationWarning):
            Rack.model_validate_json(payload)

    def test_vertical_rack_does_not_warn(self) -> None:
        """A vertical (e.g. bifacial fence) rack faces the horizon, not below it."""
        quad = _quad((0.0, 0.0, 0.0), (0.0, 0.0, 2.0), (10.0, 0.0, 2.0), (10.0, 0.0, 0.0))
        with warnings.catch_warnings():
            warnings.simplefilter("error", RackOrientationWarning)
            rack = Rack(id=0, mounting_type_id="m1", quad=quad)
        assert rack.quad.tilt == pytest.approx(90.0)
        assert rack.quad.azimuth == pytest.approx(180.0)

    def test_zero_area_quad_warns(self) -> None:
        quad = _quad((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (3.0, 0.0, 0.0))
        with pytest.warns(RackOrientationWarning, match="no area"):
            Rack(id=0, mounting_type_id="m1", quad=quad)
