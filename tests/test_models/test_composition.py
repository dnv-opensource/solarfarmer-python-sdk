import json

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
    TrackerSystem,
    Transformer,
    TransformerLossModelTypes,
    TransformerSpecification,
)


def _build_full_inputs() -> EnergyCalculationInputs:
    """Build a complete EnergyCalculationInputs for testing."""
    layout = Layout(
        layout_count=1,
        module_specification_id="mod1",
        mounting_type_id="mount1",
        is_trackers=False,
        azimuth=180.0,
        pitch=5.0,
        total_number_of_strings=10,
        string_length=20,
        inverter_input=[0],
        dc_ohmic_connector_loss=0.007,
        module_mismatch_loss=0.005,
    )

    inverter = Inverter(
        inverter_spec_id="inv1",
        inverter_count=5,
        layouts=[layout],
        ac_wiring_ohmic_loss=0.01,
    )

    transformer = Transformer(
        transformer_count=1,
        inverters=[inverter],
        transformer_spec_id="tspec1",
    )

    mounting_spec = MountingTypeSpecification(
        is_tracker=False,
        number_of_modules_high=1,
        modules_are_landscape=False,
        rack_height=0.7,
        y_spacing_between_modules=0.03,
        frame_bottom_width=0.0,
        constant_heat_transfer_coefficient=29.0,
        convective_heat_transfer_coefficient=0.0,
        monthly_soiling_loss=[0.02] * 12,
        tilt=25.0,
        height_of_lowest_edge_from_ground=0.7,
    )

    transformer_spec = TransformerSpecification(
        model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
        loss_factor=0.01,
    )

    pv_plant = PVPlant(
        transformers=[transformer],
        mounting_type_specifications={"mount1": mounting_spec},
        transformer_specifications={"tspec1": transformer_spec},
        auxiliary_losses=AuxiliaryLosses(simple_loss_factor=0.01),
    )

    calc_options = EnergyCalculationOptions(
        diffuse_model=DiffuseModel.PEREZ,
        include_horizon=True,
    )

    return EnergyCalculationInputs(
        location=Location(latitude=51.5, longitude=-0.1, altitude=10.0),
        pv_plant=pv_plant,
        monthly_albedo=MonthlyAlbedo(values=[0.2] * 12),
        energy_calculation_options=calc_options,
        horizon_azimuths=[0, 45, 90, 135, 180, 225, 270, 315],
        horizon_angles=[5, 10, 5, 3, 2, 3, 5, 8],
        pan_file_supplements={"mod1": PanFileSupplements(lid_loss=0.02)},
        ond_file_supplements={"inv1": OndFileSupplements()},
    )


class TestFullComposition:
    """Test building and serializing a complete EnergyCalculationInputs."""

    def test_build_full_inputs(self) -> None:
        inputs = _build_full_inputs()
        assert inputs.location.latitude == 51.5
        assert len(inputs.pv_plant.transformers) == 1
        assert len(inputs.monthly_albedo.values) == 12

    def test_serialize_full_inputs(self) -> None:
        inputs = _build_full_inputs()
        d = inputs.model_dump(by_alias=True, exclude_none=True)

        # Top-level keys
        assert "location" in d
        assert "pvPlant" in d
        assert "monthlyAlbedo" in d
        assert "energyCalculationOptions" in d
        assert "horizonAzimuths" in d
        assert "horizonAngles" in d
        assert "panFileSupplements" in d
        assert "ondFileSupplements" in d

        # Nested structure
        pv_plant = d["pvPlant"]
        assert "transformers" in pv_plant
        assert "mountingTypeSpecifications" in pv_plant
        transformer = pv_plant["transformers"][0]
        assert "inverters" in transformer
        inverter = transformer["inverters"][0]
        assert inverter["inverterSpecID"] == "inv1"
        layout = inverter["layouts"][0]
        assert layout["layoutCount"] == 1

    def test_json_round_trip(self) -> None:
        inputs = _build_full_inputs()
        json_str = inputs.model_dump_json(by_alias=True, exclude_none=True)
        parsed = json.loads(json_str)
        rebuilt = EnergyCalculationInputs.model_validate(parsed)

        assert rebuilt.location.latitude == inputs.location.latitude
        assert rebuilt.pv_plant.transformers[0].inverters[0].inverter_spec_id == "inv1"
        assert rebuilt.energy_calculation_options.diffuse_model == "Perez"

    def test_full_inputs_with_files(self) -> None:
        inputs = _build_full_inputs()
        wrapper = EnergyCalculationInputsWithFiles(
            energy_calculation_inputs=inputs,
            meteo_file_format=MeteoFileFormat.TSV,
            meteo_file_path_or_contents="path/to/met.tsv",
            pan_file_paths_or_contents={"mod1": "PAN file contents here"},
            ond_file_paths_or_contents={"inv1": "OND file contents here"},
        )
        d = wrapper.model_dump(by_alias=True, exclude_none=True)
        assert d["meteoFileFormat"] == "tsv"
        assert "energyCalculationInputs" in d
        assert d["panFilePathsOrContents"]["mod1"] == "PAN file contents here"


class TestWithTrackers:
    """Test composition with tracker-based plant."""

    def test_tracker_plant(self) -> None:
        layout = Layout(
            layout_count=1,
            module_specification_id="mod1",
            mounting_type_id="tracker_mount",
            is_trackers=True,
            azimuth=180.0,
            pitch=7.0,
            total_number_of_strings=10,
            string_length=20,
            inverter_input=[0],
            tracker_system_id="ts1",
        )

        tracker = TrackerSystem(
            system_plane_azimuth=0.0,
            system_plane_tilt=0.0,
            rotation_min_deg=-60.0,
            rotation_max_deg=60.0,
            is_backtracking=True,
        )

        mounting = MountingTypeSpecification(
            is_tracker=True,
            number_of_modules_high=1,
            modules_are_landscape=True,
            rack_height=1.5,
            y_spacing_between_modules=0.03,
            frame_bottom_width=0.0,
            constant_heat_transfer_coefficient=29.0,
            convective_heat_transfer_coefficient=0.0,
            monthly_soiling_loss=[0.02] * 12,
            height_of_tracker_center_from_ground=1.5,
        )

        inverter = Inverter(inverter_spec_id="inv1", inverter_count=1, layouts=[layout])
        transformer = Transformer(inverters=[inverter])

        plant = PVPlant(
            transformers=[transformer],
            mounting_type_specifications={"tracker_mount": mounting},
            tracker_systems={"ts1": tracker},
        )

        d = plant.model_dump(by_alias=True, exclude_none=True)
        assert "trackerSystems" in d
        assert d["trackerSystems"]["ts1"]["rotationMinDeg"] == -60.0
