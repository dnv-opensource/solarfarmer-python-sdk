import pytest
from pydantic import ValidationError

from solarfarmer.models import (
    AuxiliaryLosses,
    Inverter,
    Layout,
    MountingTypeSpecification,
    PVPlant,
    Transformer,
    TransformerLossModelTypes,
    TransformerSpecification,
)


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
def transformer() -> Transformer:
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
    )
    inverter = Inverter(
        inverter_spec_id="inv1",
        inverter_count=1,
        layouts=[layout],
    )
    return Transformer(transformer_count=1, inverters=[inverter])


@pytest.fixture()
def pv_plant(transformer: Transformer, mounting_spec: MountingTypeSpecification) -> PVPlant:
    return PVPlant(
        transformers=[transformer],
        mounting_type_specifications={"mount1": mounting_spec},
        transformer_specifications={
            "tspec1": TransformerSpecification(
                model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
                loss_factor=0.02,
            )
        },
        auxiliary_losses=AuxiliaryLosses(simple_loss_factor=0.01),
        grid_connection_limit=5.0,
    )


class TestPVPlantSerialization:
    def test_camel_case_keys(self, pv_plant: PVPlant) -> None:
        d = pv_plant.model_dump(by_alias=True)
        assert "transformers" in d
        assert "mountingTypeSpecifications" in d
        assert "gridConnectionLimit" in d
        assert "trackerSystems" in d
        assert "transformerSpecifications" in d
        assert "auxiliaryLosses" in d

    def test_round_trip(self, pv_plant: PVPlant) -> None:
        data = pv_plant.model_dump(by_alias=True)
        rebuilt = PVPlant.model_validate(data)
        assert rebuilt == pv_plant

    def test_exclude_none_omits_optional_fields(
        self, transformer: Transformer, mounting_spec: MountingTypeSpecification
    ) -> None:
        plant = PVPlant(
            transformers=[transformer],
            mounting_type_specifications={"mount1": mounting_spec},
        )
        d = plant.model_dump(by_alias=True, exclude_none=True)
        assert "trackerSystems" not in d
        assert "transformerSpecifications" not in d
        assert "auxiliaryLosses" not in d
        assert "gridConnectionLimit" not in d

    def test_frozen_immutability(self, pv_plant: PVPlant) -> None:
        with pytest.raises(ValidationError, match="frozen"):
            pv_plant.grid_connection_limit = 10.0  # type: ignore[misc]


class TestAuxiliaryLossesSerialization:
    def test_all_none_construction(self) -> None:
        aux = AuxiliaryLosses()
        assert aux.simple_loss_factor is None
        assert aux.night_consumption is None

    def test_camel_case_keys(self) -> None:
        aux = AuxiliaryLosses(
            simple_loss_factor=0.02,
            apply_simple_loss_factor_at_night=True,
            night_consumption=500.0,
        )
        d = aux.model_dump(by_alias=True)
        assert "simpleLossFactor" in d
        assert "applySimpleLossFactorAtNight" in d
        assert "nightConsumption" in d

    def test_round_trip(self) -> None:
        aux = AuxiliaryLosses(
            simple_loss_factor=0.02,
            fixed_daytime=100.0,
            threshold_for_fixed=50.0,
            night_consumption=500.0,
        )
        data = aux.model_dump(by_alias=True)
        rebuilt = AuxiliaryLosses.model_validate(data)
        assert rebuilt == aux

    def test_exclude_none_only_includes_set_fields(self) -> None:
        aux = AuxiliaryLosses(simple_loss_factor=0.01, night_consumption=200.0)
        d = aux.model_dump(by_alias=True, exclude_none=True)
        assert set(d.keys()) == {"simpleLossFactor", "nightConsumption"}
