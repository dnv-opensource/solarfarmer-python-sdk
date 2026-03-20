import json
from pathlib import Path

import pytest

from solarfarmer import PVSystem
from solarfarmer.models.pvsystem.pvsystem import construct_plant


class TestPVSystemInitialization:
    """Test cases for PVSystem initialization."""

    def test_pvsystem_creation_with_defaults(self):
        """Test creating PVSystem with default parameters."""
        plant = PVSystem()

        assert plant is not None
        assert isinstance(plant, PVSystem)

    def test_pvsystem_with_basic_metadata(self):
        """Test creating PVSystem with basic metadata."""
        plant = PVSystem(name="Test Solar Farm", latitude=45.5, longitude=10.3, altitude=200)

        assert plant.name == "Test Solar Farm"
        assert plant.latitude == 45.5
        assert plant.longitude == 10.3
        assert plant.altitude == 200

    def test_pvsystem_with_plant_definition(self):
        """Test creating PVSystem with plant definition parameters."""
        plant = PVSystem(
            name="Test Plant",
            latitude=45.5,
            longitude=10.3,
            dc_capacity_MW=10.0,
            ac_capacity_MW=10.0,
            grid_limit_MW=10.0,
        )

        assert plant.dc_capacity_MW == 10.0
        assert plant.ac_capacity_MW == 10.0
        assert plant.grid_limit_MW == 10.0

    def test_pvsystem_with_mounting_parameters(self):
        """Test creating PVSystem with mounting parameters."""
        plant = PVSystem(
            name="Test Plant", latitude=45.5, longitude=10.3, tilt=30.0, azimuth=180.0, gcr=0.5
        )

        assert plant.tilt == 30.0
        assert plant.azimuth == 180.0
        assert plant.gcr == 0.5


class TestPVSystemLocationProperties:
    """Test cases for PVSystem location properties."""

    def test_pvsystem_latitude_range(self):
        """Test PVSystem accepts valid latitude values."""
        # Valid latitudes
        plant1 = PVSystem(latitude=-90)  # South Pole
        plant2 = PVSystem(latitude=0)  # Equator
        plant3 = PVSystem(latitude=90)  # North Pole

        assert plant1.latitude == -90
        assert plant2.latitude == 0
        assert plant3.latitude == 90

    def test_pvsystem_longitude_range(self):
        """Test PVSystem accepts valid longitude values."""
        # Valid longitudes
        plant1 = PVSystem(longitude=-180)  # International date line (west)
        plant2 = PVSystem(longitude=0)  # Prime meridian
        plant3 = PVSystem(longitude=180)  # International date line (east)

        assert plant1.longitude == -180
        assert plant2.longitude == 0
        assert plant3.longitude == 180

    def test_pvsystem_altitude_default(self):
        """Test PVSystem default altitude."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default altitude should be 0.0
        assert plant.altitude == 0.0

    def test_pvsystem_timezone_default(self):
        """Test PVSystem default timezone."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default timezone should be UTC
        assert plant.timezone == "UTC"

    def test_pvsystem_timezone_custom(self):
        """Test PVSystem with custom timezone."""
        plant = PVSystem(latitude=45.0, longitude=10.0, timezone="Europe/Rome")

        assert plant.timezone == "Europe/Rome"


class TestPVSystemCapacityProperties:
    """Test cases for PVSystem capacity properties."""

    def test_pvsystem_dc_capacity_default(self):
        """Test PVSystem default DC capacity."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default DC capacity should be 10.0 MW
        assert plant.dc_capacity_MW == 10.0

    def test_pvsystem_ac_capacity_default(self):
        """Test PVSystem default AC capacity."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default AC capacity should be 10.0 MW
        assert plant.ac_capacity_MW == 10.0

    def test_pvsystem_grid_limit_default(self):
        """Test PVSystem default grid limit."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default grid limit should be 10.0 MW
        assert plant.grid_limit_MW == 10.0

    def test_pvsystem_custom_capacities(self):
        """Test PVSystem with custom capacity values."""
        plant = PVSystem(
            latitude=45.0,
            longitude=10.0,
            dc_capacity_MW=50.0,
            ac_capacity_MW=40.0,
            grid_limit_MW=35.0,
        )

        assert plant.dc_capacity_MW == 50.0
        assert plant.ac_capacity_MW == 40.0
        assert plant.grid_limit_MW == 35.0


class TestPVSystemMountingProperties:
    """Test cases for PVSystem mounting properties."""

    def test_pvsystem_gcr_default(self):
        """Test PVSystem default GCR (Ground Coverage Ratio)."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default GCR should be 0.5
        assert plant.gcr == 0.5

    def test_pvsystem_tilt_default(self):
        """Tilt defaults to None (set by the caller or kept unspecified)."""
        plant = PVSystem(latitude=45.0, longitude=10.0)
        assert plant.tilt is None

    def test_pvsystem_azimuth_default(self):
        """Test PVSystem default azimuth."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default azimuth should be 180 (south-facing)
        assert plant.azimuth == 180

    def test_pvsystem_custom_tilt_and_azimuth(self):
        """Test PVSystem with custom tilt and azimuth."""
        plant = PVSystem(latitude=45.0, longitude=10.0, tilt=25.0, azimuth=170.0)

        assert plant.tilt == 25.0
        assert plant.azimuth == 170.0

    def test_pvsystem_mounting_type_fixed(self):
        """Test PVSystem with fixed mounting."""
        plant = PVSystem(latitude=45.0, longitude=10.0, mounting="Fixed")

        assert plant.mounting == "Fixed"

    def test_pvsystem_mounting_type_tracker(self):
        """Test PVSystem with tracker mounting."""
        plant = PVSystem(latitude=45.0, longitude=10.0, mounting="Tracker")

        assert plant.mounting == "Tracker"


class TestPVSystemTechnologyProperties:
    """Test cases for PVSystem technology properties."""

    def test_pvsystem_flush_mount_default(self):
        """Test PVSystem default flush mount setting."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default should be False (not flush-mounted)
        assert plant.flush_mount is False

    def test_pvsystem_flush_mount_custom(self):
        """Test PVSystem with flush mount enabled."""
        plant = PVSystem(latitude=45.0, longitude=10.0, flush_mount=True)

        assert plant.flush_mount is True

    def test_pvsystem_bifacial_default(self):
        """Test PVSystem default bifacial setting."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default should be False (not bifacial)
        assert plant.bifacial is False

    def test_pvsystem_inverter_type_central(self):
        """Test PVSystem with central inverter."""
        plant = PVSystem(latitude=45.0, longitude=10.0, inverter_type="Central")

        assert plant.inverter_type == "Central"

    def test_pvsystem_inverter_type_string(self):
        """Test PVSystem with string inverter."""
        plant = PVSystem(latitude=45.0, longitude=10.0, inverter_type="String")

        assert plant.inverter_type == "String"

    def test_pvsystem_transformer_stages_default(self):
        """Test PVSystem default transformer stages."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Default should be 1
        assert plant.transformer_stages == 1

    def test_pvsystem_transformer_stages_custom(self):
        """transformer_stages=1 is a valid explicit value and must be stored."""
        plant = PVSystem(latitude=45.0, longitude=10.0, transformer_stages=1)
        assert plant.transformer_stages == 1


class TestPVSystemComplexScenarios:
    """Test cases for complex PVSystem scenarios."""

    def test_pvsystem_fixed_tilt_vs_tracker(self):
        """Test PVSystem behavior with fixed-tilt vs tracker."""
        fixed_plant = PVSystem(latitude=45.0, longitude=10.0, mounting="Fixed", tilt=30.0)

        tracker_plant = PVSystem(
            latitude=45.0,
            longitude=10.0,
            mounting="Tracker",
            tilt=60.0,  # Max rotation angle for trackers
        )

        assert fixed_plant.mounting == "Fixed"
        assert tracker_plant.mounting == "Tracker"

    def test_pvsystem_small_vs_large_plant_payload_capacity(self, bern_2d_racks_inputs):
        """A larger dc_capacity_MW results in a larger acCapacityW in the serialized payload."""
        small_plant = PVSystem(
            name="Small Plant",
            latitude=45.0,
            longitude=10.0,
            dc_capacity_MW=5.0,
            ac_capacity_MW=5.0,
        )
        small_plant.pan_files = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        small_plant.ond_files = {
            "Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"
        }

        large_plant = PVSystem(
            name="Large Plant",
            latitude=45.0,
            longitude=10.0,
            dc_capacity_MW=20.0,
            ac_capacity_MW=20.0,
        )
        large_plant.pan_files = small_plant.pan_files.copy()
        large_plant.ond_files = small_plant.ond_files.copy()

        small_payload = json.loads(construct_plant(small_plant))
        large_payload = json.loads(construct_plant(large_plant))

        small_ac = small_payload["pvPlant"]["transformers"][0]["inverters"][0]["inverterCount"]
        large_ac = large_payload["pvPlant"]["transformers"][0]["inverters"][0]["inverterCount"]
        assert small_ac < large_ac

    def test_pvsystem_hemisphere_latitude_in_payload(self, bern_2d_racks_inputs):
        """Latitude is faithfully emitted in the serialized payload for both hemispheres."""
        for lat in (50.0, -35.0):
            plant = PVSystem(latitude=lat, longitude=10.0, tilt=abs(lat))
            plant.pan_files = {
                "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
            }
            plant.ond_files = {
                "Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"
            }
            payload = json.loads(construct_plant(plant))
            assert payload["location"]["latitude"] == lat


class TestPVSystemPropertyDefaults:
    """Test cases for verifying property defaults."""

    def test_default_pvsystem_serializes_without_error(self, bern_2d_racks_inputs):
        """A default PVSystem with lat/lon and PAN/OND files produces a complete, parseable JSON payload."""
        plant = PVSystem(latitude=46.95, longitude=7.44)
        plant.pan_files = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        plant.ond_files = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}
        payload = json.loads(construct_plant(plant))
        for key in ("location", "pvPlant", "monthlyAlbedo", "energyCalculationOptions"):
            assert key in payload

    def test_pvsystem_none_optional_properties(self):
        """Test that optional properties can be None."""
        plant = PVSystem(latitude=45.0, longitude=10.0, name=None)

        assert plant.name is None

    def test_make_copy_produces_independent_instance(self):
        """make_copy() clones the plant; mutations on the copy do not affect the original."""
        original = PVSystem(latitude=45.0, longitude=10.0, tilt=20.0)
        copy = original.make_copy()
        copy.tilt = 35.0
        assert original.tilt == 20.0
        assert copy.tilt == 35.0


class TestPVSystemFileHandling:
    """Test cases for PVSystem auxiliary file handling (PAN and OND files)."""

    def test_pvsystem_set_pan_files(self):
        """Test setting PAN files mapping."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        pan_mapping = {"Module1": r"path/to/module1.PAN", "Module2": r"path/to/module2.PAN"}

        plant.pan_files = pan_mapping

        assert len(plant.pan_files) == 2
        assert "Module1" in plant.pan_files
        assert "Module2" in plant.pan_files
        assert str(plant.pan_files["Module1"]).endswith("module1.PAN")

    def test_pvsystem_set_ond_files(self):
        """Test setting OND files mapping."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        ond_mapping = {"Inverter1": r"path/to/inverter1.OND", "Inverter2": r"path/to/inverter2.OND"}

        plant.ond_files = ond_mapping

        assert len(plant.ond_files) == 2
        assert "Inverter1" in plant.ond_files
        assert "Inverter2" in plant.ond_files
        assert str(plant.ond_files["Inverter1"]).endswith("inverter1.OND")

    def test_pvsystem_add_pan_files(self):
        """Test adding PAN files with method chaining."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        result = plant.add_pan_files({"Module1": r"path/to/module1.PAN"})

        # Verify method chaining works
        assert result is plant
        assert "Module1" in plant.pan_files

    def test_pvsystem_add_ond_files(self):
        """Test adding OND files with method chaining."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        result = plant.add_ond_files({"Inverter1": r"path/to/inverter1.OND"})

        # Verify method chaining works
        assert result is plant
        assert "Inverter1" in plant.ond_files

    def test_pvsystem_add_multiple_pan_files_sequentially(self):
        """Test adding multiple PAN files in sequence."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.add_pan_files({"Module1": r"path/to/module1.PAN"}).add_pan_files(
            {"Module2": r"path/to/module2.PAN"}
        )

        assert len(plant.pan_files) == 2
        assert "Module1" in plant.pan_files
        assert "Module2" in plant.pan_files

    def test_pvsystem_add_multiple_ond_files_sequentially(self):
        """Test adding multiple OND files in sequence."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.add_ond_files({"Inverter1": r"path/to/inverter1.OND"}).add_ond_files(
            {"Inverter2": r"path/to/inverter2.OND"}
        )

        assert len(plant.ond_files) == 2
        assert "Inverter1" in plant.ond_files
        assert "Inverter2" in plant.ond_files

    def test_pvsystem_pan_files_accepts_string_paths(self):
        """Test that PAN files accepts string paths and converts to Path objects."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.pan_files = {"Module": r"path/to/module.PAN"}

        # Verify it's stored as a Path object internally
        from pathlib import Path as PathlibPath

        assert isinstance(plant.pan_files["Module"], PathlibPath)

    def test_pvsystem_ond_files_accepts_string_paths(self):
        """Test that OND files accepts string paths and converts to Path objects."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.ond_files = {"Inverter": r"path/to/inverter.OND"}

        # Verify it's stored as a Path object internally
        from pathlib import Path as PathlibPath

        assert isinstance(plant.ond_files["Inverter"], PathlibPath)

    def test_pvsystem_pan_files_property_returns_copy(self):
        """Test that pan_files property returns a shallow copy."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.pan_files = {"Module": r"path/to/module.PAN"}
        files1 = plant.pan_files
        files2 = plant.pan_files

        # Should be equal but not the same object
        assert files1 == files2
        assert files1 is not files2

    def test_pvsystem_ond_files_property_returns_copy(self):
        """Test that ond_files property returns a shallow copy."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.ond_files = {"Inverter": r"path/to/inverter.OND"}
        files1 = plant.ond_files
        files2 = plant.ond_files

        # Should be equal but not the same object
        assert files1 == files2
        assert files1 is not files2

    def test_pvsystem_pan_files_replace_existing(self):
        """Test that setting pan_files replaces existing mappings."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.pan_files = {"Module1": r"path/to/module1.PAN"}
        assert "Module1" in plant.pan_files

        plant.pan_files = {"Module2": r"path/to/module2.PAN"}
        assert "Module2" in plant.pan_files
        assert "Module1" not in plant.pan_files

    def test_pvsystem_ond_files_replace_existing(self):
        """Test that setting ond_files replaces existing mappings."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        plant.ond_files = {"Inverter1": r"path/to/inverter1.OND"}
        assert "Inverter1" in plant.ond_files

        plant.ond_files = {"Inverter2": r"path/to/inverter2.OND"}
        assert "Inverter2" in plant.ond_files
        assert "Inverter1" not in plant.ond_files

    def test_pvsystem_empty_pan_files_on_creation(self):
        """Test that PVSystem starts with empty pan_files."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Should be empty by default
        assert len(plant.pan_files) == 0
        assert isinstance(plant.pan_files, dict)

    def test_pvsystem_empty_ond_files_on_creation(self):
        """Test that PVSystem starts with empty ond_files."""
        plant = PVSystem(latitude=45.0, longitude=10.0)

        # Should be empty by default
        assert len(plant.ond_files) == 0
        assert isinstance(plant.ond_files, dict)


class TestPVSystemAuxiliaryLosses:
    """Test cases for PVSystem auxiliary loss fields and their payload serialization."""

    def test_aux_loss_defaults(self):
        """All three aux loss fields should default to None."""
        plant = PVSystem()

        assert plant.aux_loss_fixed_factor is None
        assert plant.aux_loss_power is None
        assert plant.aux_loss_apply_at_night is None

    def test_no_aux_loss_absent_from_payload(self, bern_2d_racks_inputs):
        """auxiliaryLosses key must be absent from the payload when no aux fields are set."""
        plant = PVSystem(latitude=46.9, longitude=7.4)
        plant.pan_files = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        plant.ond_files = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}

        payload = json.loads(construct_plant(plant))

        assert "auxiliaryLosses" not in payload["pvPlant"]

    def test_aux_loss_present_in_payload(self, bern_2d_racks_inputs):
        """auxiliaryLosses key must appear in the payload when an aux field is set."""
        plant = PVSystem(latitude=46.9, longitude=7.4, aux_loss_fixed_factor=0.01)
        plant.pan_files = {
            "CanadianSolar_CS6U-330M_APP": f"{bern_2d_racks_inputs}/CanadianSolar_CS6U-330M_APP.PAN"
        }
        plant.ond_files = {"Sungrow_SG125HV_APP": f"{bern_2d_racks_inputs}/Sungrow_SG125HV_APP.OND"}

        payload = json.loads(construct_plant(plant))

        assert "auxiliaryLosses" in payload["pvPlant"]
        assert payload["pvPlant"]["auxiliaryLosses"]["simpleLossFactor"] == 0.01


class TestPVSystemBifacial:
    """Tests for bifacial parameter initialization (Phase 1 bug fix)."""

    def test_bifacial_fixed_construction_does_not_raise(self):
        """PVSystem(bifacial=True) with default Fixed mounting must not raise KeyError."""
        plant = PVSystem(bifacial=True, mounting="Fixed")
        assert plant.bifacial is True

    def test_bifacial_tracker_construction_does_not_raise(self):
        """PVSystem(bifacial=True, mounting='Tracker') must not raise KeyError."""
        plant = PVSystem(bifacial=True, mounting="Tracker")
        assert plant.bifacial is True

    def test_bifacial_fixed_defaults_are_correct(self):
        """Fixed-tilt bifacial defaults must match BIFACIAL_DICT[True]['Fixed']."""
        plant = PVSystem(bifacial=True, mounting="Fixed")
        assert plant.bifacial_transmission == 0.05
        assert plant.bifacial_shade_loss == 0.200
        assert plant.bifacial_mismatch_loss == 0.01

    def test_bifacial_tracker_defaults_are_correct(self):
        """Tracker bifacial defaults must match BIFACIAL_DICT[True]['Tracker']."""
        plant = PVSystem(bifacial=True, mounting="Tracker")
        assert plant.bifacial_transmission == 0.05
        assert plant.bifacial_shade_loss == 0.100
        assert plant.bifacial_mismatch_loss == 0.005

    def test_bifacial_explicit_override_is_preserved(self):
        """Explicitly supplied bifacial params must not be overwritten by __post_init__."""
        plant = PVSystem(
            bifacial=True,
            mounting="Fixed",
            bifacial_transmission=0.03,
            bifacial_shade_loss=0.15,
            bifacial_mismatch_loss=0.008,
        )
        assert plant.bifacial_transmission == 0.03
        assert plant.bifacial_shade_loss == 0.15
        assert plant.bifacial_mismatch_loss == 0.008

    def test_non_bifacial_defaults_unchanged(self):
        """Regression: non-bifacial construction must still produce zero bifacial params."""
        plant = PVSystem(bifacial=False)
        assert plant.bifacial_transmission == 0.0
        assert plant.bifacial_shade_loss == 0.0
        assert plant.bifacial_mismatch_loss == 0.0


class TestPVSystemPersistence:
    """Tests for to_file() / from_file() round-trip (Phase 3 bug fix)."""

    def test_to_file_without_paths_succeeds(self, tmp_path):
        """Baseline: a plain PVSystem (no file paths) serializes without error."""
        plant = PVSystem(name="Plain", latitude=46.9, longitude=7.4)
        out = tmp_path / "plant.json"
        plant.to_file(out)
        assert out.exists()

    def test_to_file_with_weather_file_no_typeerror(self, tmp_path):
        """to_file() must not raise TypeError when weather_file is set."""
        plant = PVSystem(latitude=46.9, longitude=7.4)
        plant.weather_file = "/some/path/weather.dat"
        out = tmp_path / "plant.json"
        plant.to_file(out)
        saved = json.loads(out.read_text())
        assert isinstance(saved["_weather_file"], str)

    def test_to_file_with_pan_ond_files_no_typeerror(self, tmp_path):
        """to_file() must not raise TypeError when PAN/OND files are registered."""
        plant = PVSystem(latitude=46.9, longitude=7.4)
        plant.pan_files = {"Module": "/some/path/module.PAN"}
        plant.ond_files = {"Inverter": "/some/path/inverter.OND"}
        out = tmp_path / "plant.json"
        plant.to_file(out)
        saved = json.loads(out.read_text())
        assert isinstance(saved["_pan_files"]["Module"], str)
        assert isinstance(saved["_ond_files"]["Inverter"], str)

    def test_round_trip_restores_path_objects(self, tmp_path):
        """After to_file/from_file, file path fields must be Path objects again."""
        plant = PVSystem(latitude=46.9, longitude=7.4)
        plant.weather_file = "/some/path/weather.dat"
        plant.pan_files = {"Module": "/some/path/module.PAN"}
        plant.ond_files = {"Inverter": "/some/path/inverter.OND"}
        out = tmp_path / "plant.json"
        plant.to_file(out)

        loaded = PVSystem.from_file(out)

        assert isinstance(loaded.weather_file, Path)
        assert isinstance(loaded.pan_files["Module"], Path)
        assert isinstance(loaded.ond_files["Inverter"], Path)

    def test_round_trip_preserves_path_values(self, tmp_path):
        """Path values must be identical after to_file/from_file round-trip."""
        plant = PVSystem(latitude=46.9, longitude=7.4)
        plant.weather_file = "/some/path/weather.dat"
        plant.pan_files = {"Module": "/some/path/module.PAN"}
        plant.ond_files = {"Inverter": "/some/path/inverter.OND"}
        out = tmp_path / "plant.json"
        plant.to_file(out)

        loaded = PVSystem.from_file(out)

        assert loaded.weather_file == Path("/some/path/weather.dat")
        assert loaded.pan_files["Module"] == Path("/some/path/module.PAN")
        assert loaded.ond_files["Inverter"] == Path("/some/path/inverter.OND")

    def test_round_trip_preserves_non_path_fields(self, tmp_path):
        """Scalar configuration fields must survive the to_file/from_file round-trip."""
        plant = PVSystem(
            name="RoundTrip",
            latitude=46.9,
            longitude=7.4,
            altitude=550.0,
            dc_capacity_MW=15.0,
            ac_capacity_MW=12.0,
            gcr=0.4,
            bifacial=False,
        )
        out = tmp_path / "plant.json"
        plant.to_file(out)

        loaded = PVSystem.from_file(out)

        assert loaded.name == "RoundTrip"
        assert loaded.latitude == 46.9
        assert loaded.longitude == 7.4
        assert loaded.altitude == 550.0
        assert loaded.dc_capacity_MW == 15.0
        assert loaded.ac_capacity_MW == 12.0
        assert loaded.gcr == 0.4


class TestPVSystemValidation:
    """Tests for __post_init__ validation in PVSystem."""

    @pytest.mark.parametrize("lat", [91.0, -91.0, 180.0, -180.0])
    def test_invalid_latitude_raises(self, lat):
        with pytest.raises(ValueError, match="latitude"):
            PVSystem(latitude=lat, longitude=0.0)

    @pytest.mark.parametrize("lon", [181.0, -181.0, 360.0])
    def test_invalid_longitude_raises(self, lon):
        with pytest.raises(ValueError, match="longitude"):
            PVSystem(latitude=0.0, longitude=lon)

    @pytest.mark.parametrize("cap", [0.0, -1.0, -100.0])
    def test_nonpositive_ac_capacity_raises(self, cap):
        with pytest.raises(ValueError, match="ac_capacity_MW"):
            PVSystem(latitude=45.0, longitude=10.0, ac_capacity_MW=cap)

    @pytest.mark.parametrize("cap", [0.0, -5.0])
    def test_nonpositive_dc_capacity_raises(self, cap):
        with pytest.raises(ValueError, match="dc_capacity_MW"):
            PVSystem(latitude=45.0, longitude=10.0, dc_capacity_MW=cap)

    def test_invalid_mounting_type_raises(self):
        with pytest.raises(ValueError, match="MountingType"):
            PVSystem(latitude=45.0, longitude=10.0, mounting="Rooftop")

    def test_invalid_transformer_stages_raises(self):
        with pytest.raises(ValueError, match="transformer_stages"):
            PVSystem(latitude=45.0, longitude=10.0, transformer_stages=2)

    def test_nonpositive_modules_across_raises(self):
        with pytest.raises(ValueError, match="modules_across"):
            PVSystem(latitude=45.0, longitude=10.0, modules_across=0)

    def test_mismatched_horizon_array_lengths_raises(self):
        with pytest.raises(ValueError, match="[Hh]orizon"):
            PVSystem(
                latitude=45.0,
                longitude=10.0,
                horizon_elevation_angles=[5.0, 10.0],
                horizon_azimuth_angles=[90.0],
            )

    @pytest.mark.parametrize("mounting_str", ["Fixed", "Tracker"])
    def test_mounting_string_is_accepted(self, mounting_str):
        """String values for mounting are coerced to MountingType enum."""
        plant = PVSystem(latitude=45.0, longitude=10.0, mounting=mounting_str)
        assert plant.mounting.value == mounting_str
