import json

from solarfarmer.models import (
    AuxiliaryLosses,
    DiffuseModel,
    EnergyCalculationInputs,
    EnergyCalculationInputsWithFiles,
    EnergyCalculationOptions,
    IndexedObject3D,
    Inverter,
    InverterInput,
    Layout,
    Location,
    MeteoFileFormat,
    MiniSimpleTerrainDto,
    ModuleIndexRange,
    ModuleString,
    MonthlyAlbedo,
    MountingTypeSpecification,
    OndFileSupplements,
    PanFileSupplements,
    PowerOptimizerOperationType,
    PVPlant,
    QuadDouble,
    Rack,
    SimpleTerrain,
    TerrainRowDto,
    TerrainRowStartEndColumnsDto,
    Tracker,
    Trackers,
    TrackerSystem,
    Transformer,
    TransformerLossModelTypes,
    TransformerSpecification,
    Vector3Double,
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


class TestWithTrackers3d:
    """Test composition of a 3D tracker plant using Tracker and related models."""

    def test_tracker_objects_serialized(self) -> None:
        """PVPlant.trackers serializes Tracker objects with correct camelCase keys."""
        tracker = Tracker(
            id=0,
            mounting_type_id="mount_t",
            north_point=Vector3Double(x=0.0, y=10.0, z=0.5),
            south_point=Vector3Double(x=0.0, y=0.0, z=0.0),
            pitch_to_right=7.5,
            tracker_rotation_id="rot1",
            tracker_system_id="ts1",
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

        plant = PVPlant(
            transformers=[
                Transformer(inverters=[Inverter(inverter_spec_id="inv1", inverter_count=1)])
            ],
            mounting_type_specifications={"mount_t": mounting},
            tracker_systems={
                "ts1": TrackerSystem(
                    system_plane_azimuth=0.0,
                    system_plane_tilt=0.0,
                    rotation_min_deg=-60.0,
                    rotation_max_deg=60.0,
                )
            },
            trackers=[tracker],
        )

        d = plant.model_dump(by_alias=True, exclude_none=True)
        assert "trackers" in d
        t = d["trackers"][0]
        assert t["id"] == 0
        assert t["mountingTypeID"] == "mount_t"
        assert t["trackerRotationID"] == "rot1"
        assert t["trackerSystemID"] == "ts1"
        assert t["northPoint"] == {"x": 0.0, "y": 10.0, "z": 0.5}
        assert t["pitchToRight"] == 7.5
        assert "pitchToLeft" not in t  # None fields excluded

    def test_trackers_collection_roundtrip(self) -> None:
        """Trackers collection round-trips through JSON."""
        trackers = Trackers(
            trackers=[
                Tracker(
                    id=0,
                    mounting_type_id="m1",
                    north_point=Vector3Double(x=1.0, y=5.0, z=0.0),
                    south_point=Vector3Double(x=1.0, y=0.0, z=0.0),
                    tracker_rotation_id="r1",
                    tracker_system_id="ts1",
                ),
                Tracker(
                    id=1,
                    mounting_type_id="m1",
                    north_point=Vector3Double(x=9.0, y=5.0, z=0.0),
                    south_point=Vector3Double(x=9.0, y=0.0, z=0.0),
                    tracker_rotation_id="r1",
                    tracker_system_id="ts1",
                ),
            ]
        )

        json_str = trackers.model_dump_json(by_alias=True, exclude_none=True)
        rebuilt = Trackers.model_validate_json(json_str)
        assert len(rebuilt.trackers) == 2
        assert rebuilt.trackers[1].id == 1


class TestWithRacks3d:
    """Test composition of a 3D fixed-tilt plant using Rack and related models."""

    def test_rack_objects_serialized(self) -> None:
        """PVPlant.racks serializes Rack objects with correct camelCase keys."""
        quad = QuadDouble(
            p1=Vector3Double(x=0.0, y=0.0, z=0.0),
            p2=Vector3Double(x=4.0, y=0.0, z=0.0),
            p3=Vector3Double(x=4.0, y=2.0, z=1.0),
            p4=Vector3Double(x=0.0, y=2.0, z=1.0),
        )
        rack = Rack(id=0, mounting_type_id="mount_r", pitch_to_front=5.0, quad=quad)

        mounting = MountingTypeSpecification(
            is_tracker=False,
            number_of_modules_high=2,
            modules_are_landscape=False,
            rack_height=0.7,
            y_spacing_between_modules=0.02,
            frame_bottom_width=0.0,
            constant_heat_transfer_coefficient=29.0,
            convective_heat_transfer_coefficient=0.0,
            monthly_soiling_loss=[0.02] * 12,
            tilt=25.0,
            height_of_lowest_edge_from_ground=0.5,
        )

        shading_obj = IndexedObject3D(
            is_building=True,
            name="warehouse",
            vertices=[
                Vector3Double(x=20.0, y=0.0, z=0.0),
                Vector3Double(x=30.0, y=0.0, z=0.0),
                Vector3Double(x=30.0, y=10.0, z=0.0),
                Vector3Double(x=20.0, y=10.0, z=0.0),
                Vector3Double(x=20.0, y=0.0, z=8.0),
                Vector3Double(x=30.0, y=0.0, z=8.0),
                Vector3Double(x=30.0, y=10.0, z=8.0),
                Vector3Double(x=20.0, y=10.0, z=8.0),
            ],
            quad_indices=[[0, 1, 2, 3], [4, 5, 6, 7]],
        )

        terrain = SimpleTerrain(
            mini_simple_terrains=[
                MiniSimpleTerrainDto(
                    num_vertices_across=2,
                    num_vertices_down=2,
                    vertices=[
                        Vector3Double(x=0.0, y=0.0, z=0.0),
                        Vector3Double(x=10.0, y=0.0, z=0.0),
                        Vector3Double(x=0.0, y=10.0, z=0.5),
                        Vector3Double(x=10.0, y=10.0, z=0.5),
                    ],
                    terrain_rows=[
                        TerrainRowDto(
                            start_end_columns=[
                                TerrainRowStartEndColumnsDto(
                                    start_column_index=0, end_column_index=1
                                )
                            ]
                        ),
                        TerrainRowDto(
                            start_end_columns=[
                                TerrainRowStartEndColumnsDto(
                                    start_column_index=0, end_column_index=1
                                )
                            ]
                        ),
                    ],
                )
            ]
        )

        plant = PVPlant(
            transformers=[
                Transformer(inverters=[Inverter(inverter_spec_id="inv1", inverter_count=1)])
            ],
            mounting_type_specifications={"mount_r": mounting},
            racks=[rack],
            shading_objects=[shading_obj],
            simple_terrain=terrain,
        )

        d = plant.model_dump(by_alias=True, exclude_none=True)

        # Racks
        assert "racks" in d
        r = d["racks"][0]
        assert r["id"] == 0
        assert r["mountingTypeID"] == "mount_r"
        assert r["pitchToFront"] == 5.0
        assert "pitchToBack" not in r  # None excluded
        assert r["quad"]["p1"] == {"x": 0.0, "y": 0.0, "z": 0.0}

        # Shading objects
        assert "shadingObjects" in d
        s = d["shadingObjects"][0]
        assert s["isBuilding"] is True
        assert s["name"] == "warehouse"
        assert len(s["vertices"]) == 8
        assert len(s["quadIndices"]) == 2

        # Terrain
        assert "simpleTerrain" in d
        tile = d["simpleTerrain"]["miniSimpleTerrains"][0]
        assert tile["numVerticesAcross"] == 2
        assert tile["numVerticesDown"] == 2
        assert len(tile["vertices"]) == 4
        assert tile["terrainRows"][0]["startEndColumns"][0]["startColumnIndex"] == 0

    def test_racks_collection_roundtrip(self) -> None:
        """Racks collection round-trips through JSON."""
        from solarfarmer.models import Racks

        racks = Racks(
            racks=[
                Rack(
                    id=0,
                    mounting_type_id="m1",
                    quad=QuadDouble(
                        p1=Vector3Double(x=0.0, y=0.0, z=0.0),
                        p2=Vector3Double(x=4.0, y=0.0, z=0.0),
                        p3=Vector3Double(x=4.0, y=2.0, z=1.0),
                        p4=Vector3Double(x=0.0, y=2.0, z=1.0),
                    ),
                ),
                Rack(
                    id=1,
                    mounting_type_id="m1",
                    quad=QuadDouble(
                        p1=Vector3Double(x=0.0, y=6.0, z=0.0),
                        p2=Vector3Double(x=4.0, y=6.0, z=0.0),
                        p3=Vector3Double(x=4.0, y=8.0, z=1.0),
                        p4=Vector3Double(x=0.0, y=8.0, z=1.0),
                    ),
                ),
            ]
        )

        json_str = racks.model_dump_json(by_alias=True, exclude_none=True)
        rebuilt = Racks.model_validate_json(json_str)
        assert len(rebuilt.racks) == 2
        assert rebuilt.racks[1].id == 1
        assert rebuilt.racks[0].quad.p3.z == 1.0


class TestWith3DInverterInputs:
    """Test 3D plant composition using InverterInput, ModuleString, and ModuleIndexRange."""

    def _build_3d_plant(self) -> PVPlant:
        """Build a minimal 3D fixed-tilt plant using InverterInput wiring.

        Inspired by a real 3-inverter, 19-rack site but reduced to 3 racks and
        2 strings per MPPT input for clarity.
        """
        # String A spans the full first rack and part of the second
        string_a = ModuleString(
            module_index_ranges=[
                ModuleIndexRange(mounting_id=100, start_x=13, end_x=0, y=0),
                ModuleIndexRange(mounting_id=101, start_x=0, end_x=9, y=0),
            ]
        )
        # String B picks up from the middle of the second rack through the third
        string_b = ModuleString(
            module_index_ranges=[
                ModuleIndexRange(mounting_id=101, start_x=10, end_x=13, y=0),
                ModuleIndexRange(mounting_id=102, start_x=0, end_x=13, y=0),
            ]
        )

        inv_input = InverterInput(
            module_specification_id="MyModule_400W",
            module_strings=[string_a, string_b],
            dc_ohmic_connector_loss=0.0166,
            module_mismatch_loss=0.0,
            optimizer_specification_id="MyOptimizer_S440",
            optimizers_per_module=PowerOptimizerOperationType.ONE_PER_TWO_MODULES_IN_SERIES,
            fixed_voltage_from_inverter=850.0,
        )

        inverter = Inverter(
            inverter_spec_id="MyInverter_110kW",
            inverter_count=1,
            inverter_inputs=[inv_input],
            ac_wiring_ohmic_loss=0.0174,
        )

        transformer = Transformer(
            name="Transformer 1",
            transformer_count=1,
            inverters=[inverter],
            transformer_spec_id="TSpec_0",
        )

        mounting_spec = MountingTypeSpecification(
            is_tracker=False,
            number_of_modules_high=1,
            number_of_modules_long=14,
            modules_are_landscape=True,
            rack_height=1.134,
            y_spacing_between_modules=1.134,
            x_spacing_between_modules=2.462,
            frame_bottom_width=0.0,
            frame_top_width=0.0,
            frame_end_width=0.0,
            constant_heat_transfer_coefficient=20.0,
            convective_heat_transfer_coefficient=1.0,
            monthly_soiling_loss=[
                0.09,
                0.07,
                0.03,
                0.0,
                0.0,
                0.0,
                0.01,
                0.01,
                0.01,
                0.01,
                0.01,
                0.06,
            ],
            tilt=10.0,
            height_of_lowest_edge_from_ground=0.111,
            transmission_factor=0.0,
            bifacial_shade_loss_factor=0.02,
            bifacial_mismatch_loss_factor=0.005,
        )

        transformer_spec = TransformerSpecification(
            model_type=TransformerLossModelTypes.SIMPLE_LOSS_FACTOR,
            loss_factor=0.0,
        )

        quad = QuadDouble(
            p1=Vector3Double(x=0.0, y=0.0, z=10.0),
            p2=Vector3Double(x=30.0, y=0.0, z=10.0),
            p3=Vector3Double(x=30.0, y=2.0, z=10.2),
            p4=Vector3Double(x=0.0, y=2.0, z=10.2),
        )
        rack_a = Rack(id=100, mounting_type_id="FT_Rack_14", pitch_to_front=1.55, quad=quad)
        rack_b = Rack(
            id=101,
            mounting_type_id="FT_Rack_14",
            pitch_to_front=1.55,
            pitch_to_back=1.55,
            quad=quad,
        )
        rack_c = Rack(id=102, mounting_type_id="FT_Rack_14", pitch_to_back=1.55, quad=quad)

        return PVPlant(
            transformers=[transformer],
            mounting_type_specifications={"FT_Rack_14": mounting_spec},
            transformer_specifications={"TSpec_0": transformer_spec},
            racks=[rack_a, rack_b, rack_c],
        )

    def test_build_3d_plant(self) -> None:
        """3D plant is constructed with the correct nested structure."""
        plant = self._build_3d_plant()
        inv_input = plant.transformers[0].inverters[0].inverter_inputs[0]
        assert inv_input.module_specification_id == "MyModule_400W"
        assert len(inv_input.module_strings) == 2
        assert len(inv_input.module_strings[0].module_index_ranges) == 2
        assert inv_input.module_strings[0].module_index_ranges[0].mounting_id == 100
        assert inv_input.optimizers_per_module == "OnePerTwoModulesInSeries"
        assert plant.racks is not None
        assert len(plant.racks) == 3

    def test_inverter_input_serializes_with_correct_aliases(self) -> None:
        """InverterInput fields use camelCase aliases and not layouts."""
        plant = self._build_3d_plant()
        d = plant.model_dump(by_alias=True, exclude_none=True)

        inverter = d["transformers"][0]["inverters"][0]
        assert "inverterInputs" in inverter
        assert "layouts" not in inverter  # 3D uses inverterInputs, not layouts

        inv_input = inverter["inverterInputs"][0]
        assert inv_input["moduleSpecificationID"] == "MyModule_400W"
        assert inv_input["optimizerSpecificationID"] == "MyOptimizer_S440"
        assert inv_input["optimizersPerModule"] == "OnePerTwoModulesInSeries"
        assert inv_input["fixedVoltageFromInverter"] == 850.0
        assert inv_input["dcOhmicConnectorLoss"] == 0.0166
        assert "moduleStrings" in inv_input

    def test_module_index_range_uses_mounting_id_alias(self) -> None:
        """ModuleIndexRange serializes mounting_id as mountingID (explicit alias)."""
        plant = self._build_3d_plant()
        d = plant.model_dump(by_alias=True, exclude_none=True)

        range_0 = d["transformers"][0]["inverters"][0]["inverterInputs"][0]["moduleStrings"][0][
            "moduleIndexRanges"
        ][0]
        assert "mountingID" in range_0
        assert "mountingId" not in range_0  # must not fall back to to_camel default
        assert range_0["mountingID"] == 100
        assert range_0["startX"] == 13
        assert range_0["endX"] == 0
        assert range_0["y"] == 0

    def test_optimizer_enum_all_variants_serialize(self) -> None:
        """All three PowerOptimizerOperationType values serialize to their API string."""
        cases = [
            (PowerOptimizerOperationType.ONE_PER_MODULE, "OnePerModule"),
            (
                PowerOptimizerOperationType.ONE_PER_TWO_MODULES_IN_PARALLEL,
                "OnePerTwoModulesInParallel",
            ),
            (PowerOptimizerOperationType.ONE_PER_TWO_MODULES_IN_SERIES, "OnePerTwoModulesInSeries"),
        ]
        for variant, expected in cases:
            inp = InverterInput(
                module_specification_id="mod",
                dc_ohmic_connector_loss=0.0,
                module_mismatch_loss=0.0,
                optimizers_per_module=variant,
            )
            d = inp.model_dump(by_alias=True, exclude_none=True)
            assert d["optimizersPerModule"] == expected

    def test_inverter_input_without_optimizer_omits_optional_fields(self) -> None:
        """Optional optimizer fields are absent from the payload when not set."""
        inp = InverterInput(
            module_specification_id="MyModule_400W",
            module_strings=[
                ModuleString(
                    module_index_ranges=[
                        ModuleIndexRange(mounting_id=5, start_x=0, end_x=13, y=0),
                    ]
                )
            ],
            dc_ohmic_connector_loss=0.007,
            module_mismatch_loss=0.005,
        )
        d = inp.model_dump(by_alias=True, exclude_none=True)
        assert "optimizerSpecificationID" not in d
        assert "optimizersPerModule" not in d
        assert "fixedVoltageFromInverter" not in d
        assert d["moduleSpecificationID"] == "MyModule_400W"
        assert d["dcOhmicConnectorLoss"] == 0.007

    def test_json_round_trip_3d_plant(self) -> None:
        """Full 3D PVPlant survives a JSON round-trip with all nested 3D models intact."""
        plant = self._build_3d_plant()
        json_str = plant.model_dump_json(by_alias=True, exclude_none=True)
        rebuilt = PVPlant.model_validate_json(json_str)

        inv_input = rebuilt.transformers[0].inverters[0].inverter_inputs[0]
        assert inv_input.module_specification_id == "MyModule_400W"
        assert inv_input.optimizers_per_module == "OnePerTwoModulesInSeries"
        assert inv_input.fixed_voltage_from_inverter == 850.0

        # String B starts mid-rack on rack 101
        range_b0 = inv_input.module_strings[1].module_index_ranges[0]
        assert range_b0.mounting_id == 101
        assert range_b0.start_x == 10

        # rack_c has no pitch_to_front
        d = rebuilt.model_dump(by_alias=True, exclude_none=True)
        assert "pitchToFront" not in d["racks"][2]
        assert d["racks"][2]["pitchToBack"] == 1.55

    def test_multiple_inverter_inputs_per_inverter(self) -> None:
        """An inverter can hold multiple InverterInput instances (one per MPPT)."""
        make_input = lambda rack_id, spec: InverterInput(  # noqa: E731
            module_specification_id=spec,
            module_strings=[
                ModuleString(
                    module_index_ranges=[
                        ModuleIndexRange(mounting_id=rack_id, start_x=0, end_x=13, y=0)
                    ]
                )
            ],
            dc_ohmic_connector_loss=0.01,
            module_mismatch_loss=0.0,
        )

        inverter = Inverter(
            inverter_spec_id="DualMPPT_Inv",
            inverter_count=1,
            inverter_inputs=[
                make_input(200, "ModuleA_380W"),
                make_input(201, "ModuleB_400W"),
            ],
        )

        d = inverter.model_dump(by_alias=True, exclude_none=True)
        assert len(d["inverterInputs"]) == 2
        assert d["inverterInputs"][0]["moduleSpecificationID"] == "ModuleA_380W"
        assert d["inverterInputs"][1]["moduleSpecificationID"] == "ModuleB_400W"
        assert (
            d["inverterInputs"][0]["moduleStrings"][0]["moduleIndexRanges"][0]["mountingID"] == 200
        )
