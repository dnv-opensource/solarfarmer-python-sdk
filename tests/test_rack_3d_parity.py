"""Live checks that 3D racks are read the way QuadDouble and ModuleIndexRange document.

Each test runs small, unshaded or deliberately shaded plants on the SolarFarmer API. They reuse
the Bern sample's weather, PAN and OND files but build their own payloads, so the 2D and 3D runs
differ only in how the geometry is described: same equipment, electrical layout and losses.

A rack whose corners are in the reverse order passes validation and completes normally, but the
engine then treats the back of the modules as the front (about 15% of the expected energy in an
unshaded control). A serialization test cannot catch that; only a calculation can.

Every plant here has at least two racks. In our runs (API 7.0.15), each of the four single-rack 3D
plants we tried (different wiring, with and without a shading object) ended with runtime status
"Failed" and no reason given, while the same racks in two-rack plants completed.
"""

import functools
import math
from pathlib import Path

import pytest

import solarfarmer as sf
from solarfarmer.models import (
    IndexedObject3D,
    InverterInput,
    MiniSimpleTerrainDto,
    ModuleIndexRange,
    ModuleString,
    QuadDouble,
    Rack,
    SimpleTerrain,
    TerrainRowDto,
    TerrainRowStartEndColumnsDto,
    Vector3Double,
)

pytestmark = pytest.mark.integration

BERN = Path(__file__).parent.parent / "docs" / "notebooks" / "sample_data" / "Inputs_Bern_2D_racks"
MODULE = "CanadianSolar_CS6U-330M_APP"  # 0.992 m x 1.960 m, Vmp 37.5 V, monofacial
INVERTER = "Sungrow_SG125HV_APP"  # MPPT window 860-1450 V
STRING_LENGTH = 30  # 30 x 37.5 V = 1125 V
DEAD_STRING_LENGTH = 18  # Voc 18 x 45.9 V = 826 V, below the MPPT window: produces almost nothing
MODULE_WIDTH = 0.992
MODULE_LENGTH = 1.960
LOW_EDGE_HEIGHT = 1.0
# Racks in one row are this far apart, end to end. A neighbour can then shade a rack only with
# the sun within about 6 degrees of the horizon in the east or west, mostly behind these
# south-facing modules.
RACK_GAP = 20.0

# Tolerances for unshaded racks, 3D against the equivalent 2D layout. In our runs (API 7.0.15)
# the largest difference was 0.0034% (annual AC energy, mixed orientations) and near shading
# was at most 0.00003. A reversed rack is off by about 85%, so 0.1% leaves room for numerical
# changes in the engine while still catching that.
ENERGY_TOLERANCE = 0.001  # relative, for both effective irradiation and annual AC energy
MAX_NEAR_SHADING = 0.001  # absolute annual near-shading irradiance effect


def _vec(p):
    return Vector3Double(x=p[0], y=p[1], z=p[2])


def _rack_quad(p1, azimuth, tilt, width, depth):
    """Corners for a rack facing ``azimuth`` (clockwise from north) at ``tilt``.

    P1 is the low corner, P1->P4 runs along the row and P1->P2 runs up the slope, so the front
    face points toward ``azimuth``.
    """
    a, t = math.radians(azimuth), math.radians(tilt)
    along = (-math.cos(a), math.sin(a), 0.0)
    up = (-math.sin(a) * math.cos(t), -math.cos(a) * math.cos(t), math.sin(t))
    p2 = [c + depth * u for c, u in zip(p1, up, strict=True)]
    p4 = [c + width * v for c, v in zip(p1, along, strict=True)]
    p3 = [c + depth * u for c, u in zip(p4, up, strict=True)]
    # Round away floating-point noise such as sin(180°) = 1.2e-16, for readable payloads.
    p1, p2, p3, p4 = ([round(c, 9) + 0.0 for c in p] for p in (p1, p2, p3, p4))
    quad = QuadDouble(p1=_vec(p1), p2=_vec(p2), p3=_vec(p3), p4=_vec(p4))
    assert quad.tilt == pytest.approx(tilt)
    assert quad.azimuth == pytest.approx(azimuth % 360)
    return quad


def _mounting(tilt, modules_long, modules_high=1):
    """Portrait modules with no frame or gaps, so the quad is exactly modules_long x modules_high."""
    return sf.MountingTypeSpecification(
        is_tracker=False,
        number_of_modules_high=modules_high,
        number_of_modules_long=modules_long,
        modules_are_landscape=False,
        rack_height=modules_high * MODULE_LENGTH,
        y_spacing_between_modules=MODULE_LENGTH,
        x_spacing_between_modules=MODULE_WIDTH,
        frame_bottom_width=0.0,
        frame_top_width=0.0,
        frame_end_width=0.0,
        tilt=tilt,
        height_of_lowest_edge_from_ground=LOW_EDGE_HEIGHT,
        constant_heat_transfer_coefficient=29.0,
        convective_heat_transfer_coefficient=0.0,
        monthly_soiling_loss=[0.0] * 12,
    )


def _flat_terrain(points, margin=100.0):
    """A flat ground plane at z = 0: a 2 x 2 vertex grid, which is one terrain cell."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, x1 = min(xs) - margin, max(xs) + margin
    y0, y1 = min(ys) - margin, max(ys) + margin
    return SimpleTerrain(
        mini_simple_terrains=[
            MiniSimpleTerrainDto(
                num_vertices_across=2,
                num_vertices_down=2,
                vertices=[_vec((x, y, 0.0)) for y in (y0, y1) for x in (x0, x1)],
                terrain_rows=[
                    TerrainRowDto(
                        start_end_columns=[
                            TerrainRowStartEndColumnsDto(start_column_index=0, end_column_index=0)
                        ]
                    )
                ],
            )
        ]
    )


def _box(name, x0, x1, y0, y1, height):
    """A closed box standing on the ground, as a shading object."""
    footprint = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]  # anticlockwise from above
    n = len(footprint)
    vertices = [_vec((x, y, z)) for z in (0.0, height) for x, y in footprint]
    sides = [[i, (i + 1) % n, (i + 1) % n + n, i + n] for i in range(n)]
    caps = [[0, 2, 1], [0, 3, 2], [n, n + 1, n + 2], [n, n + 2, n + 3]]
    return IndexedObject3D(name=name, vertices=vertices, quad_indices=sides, triangle_indices=caps)


@functools.cache
def _bern():
    return sf.EnergyCalculationInputs.model_validate_json(
        (BERN / "EnergyCalcInputs.json").read_text()
    )


def _inputs(pv_plant):
    """Bern's location, albedo, options and PAN supplements around ``pv_plant``."""
    base = _bern()
    options = base.energy_calculation_options.model_copy(
        update={
            "return_pv_syst_format_time_series_results": False,
            "return_detailed_time_series_results": False,
            "return_loss_tree_time_series_results": False,
        }
    )
    return base.model_copy(update={"pv_plant": pv_plant, "energy_calculation_options": options})


def _plant(inverters, mounting_types, **geometry):
    """Bern's transformer around ``inverters``, plus any 3D geometry."""
    base = _bern()
    transformer = base.pv_plant.transformers[0].model_copy(update={"inverters": inverters})
    return sf.PVPlant(
        transformers=[transformer],
        transformer_specifications=base.pv_plant.transformer_specifications,
        mounting_type_specifications=mounting_types,
        **geometry,
    )


def _inverter_2d(name, mounting_id, azimuth, strings=1):
    return sf.Inverter(
        name=name,
        inverter_spec_id=INVERTER,
        inverter_count=1,
        ac_wiring_ohmic_loss=0.0,
        layouts=[
            sf.Layout(
                layout_count=1,
                module_specification_id=MODULE,
                mounting_type_id=mounting_id,
                is_trackers=False,
                azimuth=azimuth,
                pitch=10.0,
                total_number_of_strings=strings,
                string_length=STRING_LENGTH,
                inverter_input=[0],
                number_of_strings_in_isolated_row=strings,
                dc_ohmic_connector_loss=0.0,
                module_mismatch_loss=0.0,
            )
        ],
    )


def _inverter_3d(name, strings):
    """One inverter input; ``strings`` is a list of strings, each a list of ModuleIndexRange."""
    return sf.Inverter(
        name=name,
        inverter_spec_id=INVERTER,
        inverter_count=1,
        ac_wiring_ohmic_loss=0.0,
        inverter_inputs=[
            InverterInput(
                module_specification_id=MODULE,
                module_strings=[ModuleString(module_index_ranges=r) for r in strings],
                dc_ohmic_connector_loss=0.0,
                module_mismatch_loss=0.0,
            )
        ],
    )


def _annual(inputs, api_key, label):
    result = sf.run_energy_calculation(
        plant_builder=inputs,
        meteorological_data_file_path=str(BERN / "Bern-hour.dat"),
        pan_file_paths=[str(BERN / f"{MODULE}.PAN")],
        ond_file_paths=[str(BERN / f"{INVERTER}.OND")],
        project_id=f"test_sdk_rack_parity_{label}",
        print_summary=False,
        save_outputs=False,
        api_key=api_key,
    )
    assert result is not None
    annual = result.AnnualData[0]
    energy = annual["energyYieldResults"]
    effects = annual["annualEffects"]
    summary = {
        "effective_irradiation": energy["globalEffectiveIrradiance"],
        "net_energy": energy["netEnergy"],
        "near_shading": effects["nearShadingIrradiance"],
    }
    print(f"{label}: {summary}")
    # Reject non-producing or invalid results, which the relative comparisons would accept.
    for key in ("effective_irradiation", "net_energy"):
        assert math.isfinite(summary[key]) and summary[key] > 0, f"{label}: {key} = {summary[key]}"
    assert math.isfinite(summary["near_shading"]), (
        f"{label}: near_shading = {summary['near_shading']}"
    )
    return summary


def _assert_parity(result_3d, result_2d):
    assert result_3d["effective_irradiation"] == pytest.approx(
        result_2d["effective_irradiation"], rel=ENERGY_TOLERANCE
    )
    assert result_3d["net_energy"] == pytest.approx(result_2d["net_energy"], rel=ENERGY_TOLERANCE)
    assert abs(result_3d["near_shading"]) <= MAX_NEAR_SHADING


def test_two_row_racks_match_2d(api_key):
    """Two identical south-facing racks of two portrait rows, one string per row.

    The wiring follows the ModelChainAsync documentation example: each string is one row, and
    the first runs from the last index back to 0. The racks stand in one row, RACK_GAP apart,
    each on its own inverter.
    """
    tilt, azimuth, long, high = 30.0, 180.0, STRING_LENGTH, 2
    mounting = {"rack": _mounting(tilt, long, high)}

    plant_2d = _plant(
        [_inverter_2d(f"2D {i}", "rack", azimuth, strings=high) for i in range(2)], mounting
    )

    racks, inverters, corners = [], [], []
    for rack_id, x in enumerate((0.0, long * MODULE_WIDTH + RACK_GAP)):
        quad = _rack_quad(
            (x, 0.0, LOW_EDGE_HEIGHT), azimuth, tilt, long * MODULE_WIDTH, high * MODULE_LENGTH
        )
        racks.append(Rack(id=rack_id, mounting_type_id="rack", quad=quad))
        corners += [(p.x, p.y) for p in (quad.p1, quad.p2, quad.p3, quad.p4)]
        strings = [
            [ModuleIndexRange(mounting_id=rack_id, start_x=long - 1, end_x=0, y=0)],
            [ModuleIndexRange(mounting_id=rack_id, start_x=0, end_x=long - 1, y=1)],
        ]
        inverters.append(_inverter_3d(f"3D {rack_id}", strings))
    plant_3d = _plant(inverters, mounting, racks=racks, simple_terrain=_flat_terrain(corners))

    _assert_parity(
        _annual(_inputs(plant_3d), api_key, "two_row_3d"),
        _annual(_inputs(plant_2d), api_key, "two_row_2d"),
    )


def test_mixed_orientation_racks_match_2d(api_key):
    """Two racks with different azimuth and tilt, one inverter each.

    Their nearest corners are 40 m apart, so either can shade the other only with the sun within
    about 2 degrees of the horizon.
    """
    orientations = {"east": (90.0, 20.0, (0.0, 0.0)), "west_southwest": (250.0, 35.0, (40.0, 0.0))}
    mounting = {name: _mounting(tilt, STRING_LENGTH) for name, (_, tilt, _) in orientations.items()}

    plant_2d = _plant(
        [_inverter_2d(name, name, azimuth) for name, (azimuth, _, _) in orientations.items()],
        mounting,
    )

    racks, inverters, corners = [], [], []
    for rack_id, (name, (azimuth, tilt, (x, y))) in enumerate(orientations.items()):
        quad = _rack_quad(
            (x, y, LOW_EDGE_HEIGHT), azimuth, tilt, STRING_LENGTH * MODULE_WIDTH, MODULE_LENGTH
        )
        racks.append(Rack(id=rack_id, mounting_type_id=name, quad=quad))
        corners += [(p.x, p.y) for p in (quad.p1, quad.p2, quad.p3, quad.p4)]
        inverters.append(
            _inverter_3d(
                name,
                [[ModuleIndexRange(mounting_id=rack_id, start_x=0, end_x=STRING_LENGTH - 1, y=0)]],
            )
        )
    plant_3d = _plant(inverters, mounting, racks=racks, simple_terrain=_flat_terrain(corners))

    _assert_parity(
        _annual(_inputs(plant_3d), api_key, "mixed_3d"),
        _annual(_inputs(plant_2d), api_key, "mixed_2d"),
    )


def test_module_index_x_starts_at_p1(api_key):
    """Index x = 0 is the module at the P1 end of the rack.

    Energy parity cannot catch an indexing error, because every module on an unshaded rack sees
    the same irradiance. Here a wall shades the P1 (west) end of a south-facing rack of 48
    modules. The rack is fully wired: a 30-module string feeds one inverter, and the other 18
    modules feed a second inverter whose voltage stays below the MPPT window, so they produce
    almost nothing. A second rack, RACK_GAP east along the row, holds one more such string. The plant's
    energy is therefore the 30-module string's energy. With x = 0 at P1, that string is behind
    the wall when it starts at index 0, and in the open when it starts at index 18.
    """
    tilt, azimuth = 30.0, 180.0
    long = STRING_LENGTH + DEAD_STRING_LENGTH
    mounting = {"rack": _mounting(tilt, long), "spare": _mounting(tilt, DEAD_STRING_LENGTH)}
    quad = _rack_quad(
        (0.0, 0.0, LOW_EDGE_HEIGHT), azimuth, tilt, long * MODULE_WIDTH, MODULE_LENGTH
    )
    assert quad.p4.x > quad.p1.x  # P1 is the west end
    spare = _rack_quad(
        (long * MODULE_WIDTH + RACK_GAP, 0.0, LOW_EDGE_HEIGHT),
        azimuth,
        tilt,
        DEAD_STRING_LENGTH * MODULE_WIDTH,
        MODULE_LENGTH,
    )
    racks = [
        Rack(id=0, mounting_type_id="rack", quad=quad),
        Rack(id=1, mounting_type_id="spare", quad=spare),
    ]
    # In front of module positions 1-16 from the P1 end, 2 m south of the rack and 8 m tall.
    wall = _box("wall", MODULE_WIDTH, (DEAD_STRING_LENGTH - 1) * MODULE_WIDTH, -2.5, -2.0, 8.0)
    terrain = _flat_terrain([(p.x, p.y) for q in (quad, spare) for p in (q.p1, q.p2, q.p3, q.p4)])

    def run(live_start, dead_start, label):
        live = [
            ModuleIndexRange(
                mounting_id=0, start_x=live_start, end_x=live_start + STRING_LENGTH - 1, y=0
            )
        ]
        dead = [
            ModuleIndexRange(
                mounting_id=0, start_x=dead_start, end_x=dead_start + DEAD_STRING_LENGTH - 1, y=0
            )
        ]
        dead_spare = [ModuleIndexRange(mounting_id=1, start_x=0, end_x=DEAD_STRING_LENGTH - 1, y=0)]
        plant = _plant(
            [_inverter_3d("live", [live]), _inverter_3d("dead", [dead, dead_spare])],
            mounting,
            racks=racks,
            shading_objects=[wall],
            simple_terrain=terrain,
        )
        return _annual(_inputs(plant), api_key, label)

    live_at_p1_end = run(0, STRING_LENGTH, "index_live_at_p1_end")
    live_at_p4_end = run(DEAD_STRING_LENGTH, 0, "index_live_at_p4_end")

    # In our runs (API 7.0.15) the string in the open produced 9.1 times as much.
    assert live_at_p4_end["net_energy"] > 3 * live_at_p1_end["net_energy"]
