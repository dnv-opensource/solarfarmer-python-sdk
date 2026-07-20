import json

import pytest

from solarfarmer.models import (
    AuxiliaryLosses,
    DiffuseModel,
    EnergyCalculationInputs,
    EnergyCalculationInputsWithFiles,
    EnergyCalculationOptions,
    Inverter,
    Layout,
    Location,
    MeteoFileFormat,
    MonthlyAlbedo,
    MountingTypeSpecification,
    OndFileSupplements,
    PanFileSupplements,
    PVPlant,
    TrackerAlgorithm,
    TrackerCondition,
    TrackersConditionsDataset,
    TrackerSystem,
    Transformer,
    TransformerLossModelTypes,
    TransformerSpecification,
)


@pytest.fixture()
def location() -> Location:
    return Location(latitude=51.5, longitude=-0.1, altitude=10.0)


@pytest.fixture()
def layout() -> Layout:
    return Layout(
        layout_count=1,
        module_specification_id="mod1",
        mounting_type_id="mount1",
        is_trackers=False,
        azimuth=180.0,
        pitch=5.0,
        total_number_of_strings=10,
        string_length=20,
        inverter_input=[0],
        dc_ohmic_connector_loss=0.01,
        module_mismatch_loss=0.005,
    )


@pytest.fixture()
def inverter(layout: Layout) -> Inverter:
    return Inverter(
        inverter_spec_id="inv1",
        inverter_count=1,
        layouts=[layout],
    )


@pytest.fixture()
def transformer(inverter: Inverter) -> Transformer:
    return Transformer(inverter_count=1, inverters=[inverter])


@pytest.fixture()
def mounting_spec() -> MountingTypeSpecification:
    return MountingTypeSpecification(
        is_tracker=False,
        number_of_modules_high=1,
        modules_are_landscape=False,
        rack_height=0.7,
        y_spacing_between_modules=0.03,
        frame_bottom_width=0.0,
        constant_heat_transfer_coefficient=29.0,
        convective_heat_transfer_coefficient=0.0,
        monthly_soiling_loss=[0.0] * 12,
        tilt=25.0,
    )


@pytest.fixture()
def calc_options() -> EnergyCalculationOptions:
    return EnergyCalculationOptions(
        diffuse_model=DiffuseModel.PEREZ,
        include_horizon=False,
    )


class TestCamelCaseSerialization:
    """All models serialize field names as camelCase."""

    def test_location_keys(self, location: Location) -> None:
        d = location.model_dump(by_alias=True)
        assert set(d.keys()) == {"latitude", "longitude", "altitude"}

    def test_layout_keys(self, layout: Layout) -> None:
        d = layout.model_dump(by_alias=True)
        assert "layoutCount" in d
        assert "moduleSpecificationId" not in d  # alias is moduleSpecificationID
        assert "moduleSpecificationID" in d

    def test_inverter_keys(self, inverter: Inverter) -> None:
        d = inverter.model_dump(by_alias=True)
        assert "inverterSpecID" in d
        assert "inverterCount" in d
        assert "acWiringOhmicLoss" in d

    def test_transformer_keys(self, transformer: Transformer) -> None:
        d = transformer.model_dump(by_alias=True)
        assert "transformerCount" in d
        assert "inverters" in d

    def test_energy_calculation_options_keys(self, calc_options: EnergyCalculationOptions) -> None:
        d = calc_options.model_dump(by_alias=True)
        assert "diffuseModel" in d
        assert "includeHorizon" in d
        assert "calculationYear" in d

    def test_mounting_spec_keys(self, mounting_spec: MountingTypeSpecification) -> None:
        d = mounting_spec.model_dump(by_alias=True)
        assert "isTracker" in d
        assert "numberOfModulesHigh" in d
        assert "monthlySoilingLoss" in d


class TestRoundTrip:
    """Models survive a dump/validate round-trip."""

    def test_location_round_trip(self, location: Location) -> None:
        data = location.model_dump(by_alias=True)
        rebuilt = Location.model_validate(data)
        assert rebuilt == location

    def test_layout_round_trip(self, layout: Layout) -> None:
        data = layout.model_dump(by_alias=True)
        rebuilt = Layout.model_validate(data)
        assert rebuilt == layout

    def test_inverter_round_trip(self, inverter: Inverter) -> None:
        data = inverter.model_dump(by_alias=True)
        rebuilt = Inverter.model_validate(data)
        assert rebuilt == inverter

    def test_transformer_round_trip(self, transformer: Transformer) -> None:
        data = transformer.model_dump(by_alias=True)
        rebuilt = Transformer.model_validate(data)
        assert rebuilt == transformer

    def test_calc_options_round_trip(self, calc_options: EnergyCalculationOptions) -> None:
        data = calc_options.model_dump(by_alias=True)
        rebuilt = EnergyCalculationOptions.model_validate(data)
        assert rebuilt.diffuse_model == calc_options.diffuse_model
        assert rebuilt.include_horizon == calc_options.include_horizon

    def test_mounting_spec_round_trip(self, mounting_spec: MountingTypeSpecification) -> None:
        data = mounting_spec.model_dump(by_alias=True)
        rebuilt = MountingTypeSpecification.model_validate(data)
        assert rebuilt == mounting_spec

    def test_tracker_system_round_trip(self) -> None:
        ts = TrackerSystem(
            system_plane_azimuth=0.0,
            system_plane_tilt=0.0,
            rotation_min_deg=-60.0,
            rotation_max_deg=60.0,
            is_backtracking=True,
        )
        rebuilt = TrackerSystem.model_validate(ts.model_dump(by_alias=True))
        assert rebuilt == ts

    def test_tracker_algorithm_serializes(self) -> None:
        ts = TrackerSystem(
            system_plane_azimuth=0.0,
            system_plane_tilt=0.0,
            tracker_algorithm=TrackerAlgorithm.CUSTOM_ROTATIONS,
        )
        d = ts.model_dump(by_alias=True, exclude_none=True)
        assert d["trackerAlgorithm"] == "CustomRotations"

    def test_tracker_algorithm_absent_when_none(self) -> None:
        ts = TrackerSystem(system_plane_azimuth=0.0, system_plane_tilt=0.0)
        d = ts.model_dump(by_alias=True, exclude_none=True)
        assert "trackerAlgorithm" not in d

    def test_return_tracker_time_series_fields_serialize(self) -> None:
        opts = EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
            return_tracker_rotations_time_series=True,
            return_tracker_incidence_angles_time_series=True,
        )
        d = opts.model_dump(by_alias=True)
        assert d["returnTrackerRotationsTimeSeries"] is True
        assert d["returnTrackerIncidenceAnglesTimeSeries"] is True

    def test_custom_tracker_rotations_at_middle_round_trip(self) -> None:
        opts = EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
            custom_tracker_rotations_are_at_middle_of_period=True,
        )
        d = opts.model_dump(by_alias=True)
        assert d["customTrackerRotationsAreAtMiddleOfPeriod"] is True
        rebuilt = EnergyCalculationOptions.model_validate(d)
        assert rebuilt.custom_tracker_rotations_are_at_middle_of_period is True

    def test_auxiliary_losses_round_trip(self) -> None:
        aux = AuxiliaryLosses(simple_loss_factor=0.02, night_consumption=500.0)
        rebuilt = AuxiliaryLosses.model_validate(aux.model_dump(by_alias=True))
        assert rebuilt == aux

    def test_pan_supplements_round_trip(self) -> None:
        pan = PanFileSupplements(modeling_correction_factor=1.0, lid_loss=0.02)
        rebuilt = PanFileSupplements.model_validate(pan.model_dump(by_alias=True))
        assert rebuilt == pan

    def test_ond_supplements_round_trip(self) -> None:
        ond = OndFileSupplements(dc_voltage_derate_voltages=[100.0, 200.0])
        rebuilt = OndFileSupplements.model_validate(ond.model_dump(by_alias=True))
        assert rebuilt == ond

    def test_transformer_spec_round_trip(self) -> None:
        spec = TransformerSpecification(
            model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
            loss_factor=0.02,
        )
        rebuilt = TransformerSpecification.model_validate(spec.model_dump(by_alias=True))
        assert rebuilt == spec

    def test_tracker_condition_round_trip(self) -> None:
        from datetime import datetime, timezone

        # Mirrors the first data row in EnergyCalcInputsTrackerTest.json:
        # all trackers flat (angle = 0) early morning.
        cond = TrackerCondition(
            period_in_minutes=5.0,
            start_of_period=datetime(2018, 1, 1, 8, 0, tzinfo=timezone.utc),
            tracker_rotation_unique_value=0,
        )
        rebuilt = TrackerCondition.model_validate(cond.model_dump(by_alias=True))
        assert rebuilt == cond

    def test_tracker_condition_array_round_trip(self) -> None:
        from datetime import datetime, timezone

        # Mirrors the second data row in EnergyCalcInputsTrackerTest.json:
        # trackers have different angles, encoded as degrees × 100.
        cond = TrackerCondition(
            period_in_minutes=5.0,
            start_of_period=datetime(2018, 1, 1, 8, 5, tzinfo=timezone.utc),
            tracker_rotations_array_values=[-1570, -780, -1050],
        )
        d = cond.model_dump(by_alias=True)
        assert d["trackerRotationsArrayValues"] == [-1570, -780, -1050]
        assert d["trackerRotationUniqueValue"] is None
        rebuilt = TrackerCondition.model_validate(d)
        assert rebuilt == cond

    def test_trackers_conditions_dataset_round_trip(self) -> None:
        from datetime import datetime, timezone

        # Small 3-tracker / 2-timestep dataset representative of the JSON file.
        dataset = TrackersConditionsDataset(
            offset_from_utc=0.0,
            rotations_are_at_middle_of_period=False,
            tracker_rotation_ids=["Index_0", "Index_1", "Index_2"],
            data=[
                TrackerCondition(
                    period_in_minutes=5.0,
                    start_of_period=datetime(2018, 1, 1, 8, 0, tzinfo=timezone.utc),
                    tracker_rotation_unique_value=0,
                ),
                TrackerCondition(
                    period_in_minutes=5.0,
                    start_of_period=datetime(2018, 1, 1, 8, 5, tzinfo=timezone.utc),
                    tracker_rotations_array_values=[-1570, -780, -1050],
                ),
            ],
        )
        d = dataset.model_dump(by_alias=True)
        assert d["offsetFromUtc"] == 0.0
        assert d["rotationsAreAtMiddleOfPeriod"] is False
        assert d["trackerRotationIds"] == ["Index_0", "Index_1", "Index_2"]
        assert len(d["data"]) == 2
        rebuilt = TrackersConditionsDataset.model_validate(d)
        assert rebuilt == dataset


class TestJsonSerialization:
    """Models can be serialized to/from JSON strings."""

    def test_location_json_round_trip(self, location: Location) -> None:
        json_str = location.model_dump_json(by_alias=True)
        parsed = json.loads(json_str)
        assert parsed["latitude"] == 51.5
        rebuilt = Location.model_validate_json(json_str)
        assert rebuilt == location

    def test_nested_json(self, transformer: Transformer) -> None:
        json_str = transformer.model_dump_json(by_alias=True)
        parsed = json.loads(json_str)
        assert "inverters" in parsed
        assert parsed["inverters"][0]["inverterSpecID"] == "inv1"

    def test_parse_tracker_conditions_large_dataset(self) -> None:
        """TrackersConditionsDataset handles large tracker counts and mixed condition types."""
        from datetime import datetime, timezone

        n_trackers = 536
        tracker_ids = [f"Index_{i}" for i in range(n_trackers)]

        dataset = TrackersConditionsDataset(
            offset_from_utc=0.0,
            rotations_are_at_middle_of_period=False,
            tracker_rotation_ids=tracker_ids,
            data=[
                TrackerCondition(
                    period_in_minutes=5.0,
                    start_of_period=datetime(2018, 1, 1, 8, 0, tzinfo=timezone.utc),
                    tracker_rotation_unique_value=0,
                ),
                TrackerCondition(
                    period_in_minutes=5.0,
                    start_of_period=datetime(2018, 1, 1, 8, 5, tzinfo=timezone.utc),
                    tracker_rotations_array_values=list(range(n_trackers)),
                ),
            ],
        )

        assert len(dataset.tracker_rotation_ids) == n_trackers
        assert len(dataset.data) == 2
        # First timestep: all trackers horizontal (unique value 0)
        assert dataset.data[0].tracker_rotation_unique_value == 0
        assert dataset.data[0].tracker_rotations_array_values == []
        # Second timestep: per-tracker angles
        assert dataset.data[1].tracker_rotation_unique_value is None
        assert len(dataset.data[1].tracker_rotations_array_values) == n_trackers


class TestExcludeNone:
    """Optional None values can be excluded from output."""

    def test_layout_exclude_none(self, layout: Layout) -> None:
        d = layout.model_dump(by_alias=True, exclude_none=True)
        assert "name" not in d
        assert "trackerSystemId" not in d
        assert "moduleQualityFactor" not in d
        assert "trackerRotationID" not in d
        assert "dcOhmicConnectorResistance" not in d

    def test_layout_tracker_rotation_id_present_when_set(self, layout: Layout) -> None:
        updated = layout.model_copy(update={"tracker_rotation_id": "Index_101"})
        d = updated.model_dump(by_alias=True, exclude_none=True)
        assert d["trackerRotationID"] == "Index_101"

    def test_layout_dc_ohmic_connector_resistance_present_when_set(self, layout: Layout) -> None:
        updated = layout.model_copy(update={"dc_ohmic_connector_resistance": 0.05})
        d = updated.model_dump(by_alias=True, exclude_none=True)
        assert d["dcOhmicConnectorResistance"] == pytest.approx(0.05)

    def test_inverter_exclude_none(self, inverter: Inverter) -> None:
        d = inverter.model_dump(by_alias=True, exclude_none=True)
        assert "inverterInputs" not in d
        assert "name" not in d

    def test_calc_options_exclude_none(self, calc_options: EnergyCalculationOptions) -> None:
        d = calc_options.model_dump(by_alias=True, exclude_none=True)
        assert "horizonType" not in d

    def test_custom_tracker_rotations_absent_when_none(
        self, calc_options: EnergyCalculationOptions
    ) -> None:
        d = calc_options.model_dump(by_alias=True, exclude_none=True)
        assert "customTrackerRotationsAreAtMiddleOfPeriod" not in d

    def test_custom_tracker_rotations_present_when_false(self) -> None:
        opts = EnergyCalculationOptions(
            diffuse_model=DiffuseModel.PEREZ,
            include_horizon=False,
            custom_tracker_rotations_are_at_middle_of_period=False,
        )
        d = opts.model_dump(by_alias=True, exclude_none=True)
        assert "customTrackerRotationsAreAtMiddleOfPeriod" in d
        assert d["customTrackerRotationsAreAtMiddleOfPeriod"] is False


class TestEnumSerialization:
    """Enums serialize as their string values."""

    def test_diffuse_model_value(self, calc_options: EnergyCalculationOptions) -> None:
        d = calc_options.model_dump(by_alias=True)
        assert d["diffuseModel"] == "Perez"

    def test_transformer_model_type_value(self) -> None:
        spec = TransformerSpecification(
            model_type=TransformerLossModelTypes.NO_LOAD_AND_OHMIC,
            rated_power=1000.0,
            no_load_loss=10.0,
            full_load_ohmic_loss=20.0,
        )
        d = spec.model_dump(by_alias=True)
        assert d["modelType"] == "NoLoadAndOhmic"

    def test_meteo_file_format_value(self) -> None:
        wrapper = EnergyCalculationInputsWithFiles(
            energy_calculation_inputs=EnergyCalculationInputs(
                location=Location(latitude=0, longitude=0),
                pv_plant=PVPlant(
                    transformers=[],
                    mounting_type_specifications={},
                ),
                monthly_albedo=MonthlyAlbedo(values=[0.2] * 12),
                energy_calculation_options=EnergyCalculationOptions(
                    diffuse_model=DiffuseModel.PEREZ,
                    include_horizon=False,
                ),
            ),
            meteo_file_format=MeteoFileFormat.TSV,
        )
        d = wrapper.model_dump(by_alias=True, exclude_none=True)
        assert d["meteoFileFormat"] == "tsv"
