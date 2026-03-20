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


class TestExcludeNone:
    """Optional None values can be excluded from output."""

    def test_layout_exclude_none(self, layout: Layout) -> None:
        d = layout.model_dump(by_alias=True, exclude_none=True)
        assert "name" not in d
        assert "trackerSystemId" not in d
        assert "moduleQualityFactor" not in d

    def test_inverter_exclude_none(self, inverter: Inverter) -> None:
        d = inverter.model_dump(by_alias=True, exclude_none=True)
        assert "inverterInputs" not in d
        assert "name" not in d

    def test_calc_options_exclude_none(self, calc_options: EnergyCalculationOptions) -> None:
        d = calc_options.model_dump(by_alias=True, exclude_none=True)
        assert "horizonType" not in d


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
