import json

import pytest

from solarfarmer import PVSystem
from solarfarmer.models import PVPlant
from solarfarmer.models.pvsystem.pvsystem import construct_plant, design_plant


@pytest.fixture
def plant(bern_2d_racks_inputs):
    p = PVSystem(latitude=46.95, longitude=7.44)
    p.pan_files = {
        "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
    }
    p.ond_files = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}
    return p


class TestConstructPlant:
    """Tests for construct_plant() → JSON string."""

    def test_returns_valid_json_string(self, plant):
        result = construct_plant(plant)
        assert isinstance(result, str)
        json.loads(result)  # must not raise

    def test_required_top_level_keys_present(self, plant):
        payload = json.loads(construct_plant(plant))
        for key in ("location", "pvPlant", "monthlyAlbedo", "energyCalculationOptions"):
            assert key in payload

    def test_location_coordinates_round_trip(self, plant):
        payload = json.loads(construct_plant(plant))
        assert payload["location"]["latitude"] == pytest.approx(46.95)
        assert payload["location"]["longitude"] == pytest.approx(7.44)

    def test_default_monthly_albedo_is_0_2(self, plant):
        payload = json.loads(construct_plant(plant))
        # monthlyAlbedo serializes as a bare JSON array
        values = payload["monthlyAlbedo"]
        assert len(values) == 12
        assert all(v == pytest.approx(0.2) for v in values)

    def test_diffuse_model_is_perez(self, plant):
        payload = json.loads(construct_plant(plant))
        assert payload["energyCalculationOptions"]["diffuseModel"] == "Perez"

    def test_spectral_modeling_off_by_default(self, plant):
        payload = json.loads(construct_plant(plant))
        opts = payload["energyCalculationOptions"]
        # Expected absent (exclude_none=True) or explicitly False
        assert opts.get("applySpectralMismatchModifier", False) is False

    def test_spectral_modeling_on_when_enabled(self, plant):
        plant.enable_spectral_modeling = True
        payload = json.loads(construct_plant(plant))
        assert payload["energyCalculationOptions"]["applySpectralMismatchModifier"] is True

    def test_horizon_keys_absent_when_not_set(self, plant):
        payload = json.loads(construct_plant(plant))
        assert "horizonAzimuths" not in payload
        assert "horizonAngles" not in payload

    def test_horizon_keys_present_when_set(self, plant):
        plant.horizon([5.0, 10.0, 5.0], [90.0, 180.0, 270.0])
        payload = json.loads(construct_plant(plant))
        assert "horizonAzimuths" in payload
        assert "horizonAngles" in payload

    def test_tracker_plant_serializes_successfully(self, bern_2d_racks_inputs):
        p = PVSystem(latitude=46.95, longitude=7.44, mounting="Tracker", tilt=55.0)
        p.pan_files = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        p.ond_files = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}
        payload = json.loads(construct_plant(p))
        assert "pvPlant" in payload


class TestDesignPlant:
    """Tests for design_plant() → (PVPlant, supplements dict)."""

    def test_returns_pvplant_and_supplements_dict(self, plant):
        pv_plant, supplements = design_plant(plant)
        assert isinstance(pv_plant, PVPlant)
        assert isinstance(supplements, dict)

    def test_higher_capacity_produces_more_inverters(self, bern_2d_racks_inputs):
        pan = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        ond = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}

        small = PVSystem(latitude=46.95, longitude=7.44, dc_capacity_MW=2.0, ac_capacity_MW=2.0)
        small.pan_files = pan
        small.ond_files = ond

        large = PVSystem(latitude=46.95, longitude=7.44, dc_capacity_MW=50.0, ac_capacity_MW=50.0)
        large.pan_files = pan
        large.ond_files = ond

        def total_inverters(pv_plant):
            return sum(inv.inverter_count for t in pv_plant.transformers for inv in t.inverters)

        small_plant, _ = design_plant(small)
        large_plant, _ = design_plant(large)
        assert total_inverters(small_plant) < total_inverters(large_plant)
