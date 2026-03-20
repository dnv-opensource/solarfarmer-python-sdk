"""
Defines a default structure for
the SDK PVSystem class when constructing the API JSON payload.
"""

from enum import Enum

# ------------------------------------------------------------------------------
# Enum definitions for inverter types, mounting types, and orientation types.
# ------------------------------------------------------------------------------


class InverterType(str, Enum):
    """Enumeration for inverter types."""

    STRING = "String"
    CENTRAL = "Central"


class MountingType(str, Enum):
    """Enumeration for mounting types."""

    FIXED = "Fixed"
    TRACKER = "Tracker"


class OrientationType(str, Enum):
    """Enumeration for module orientation types."""

    PORTRAIT = "Portrait"
    LANDSCAPE = "Landscape"


# ------------------------------------------------------------------------------
# Default transformer losses.
# ------------------------------------------------------------------------------

TRANSFORMER_DICT = {
    "Ideal": {"fixed": 0, "variable": 0},
    "FixedType1": {"fixed": 0.001, "variable": 0.01},
}

# ------------------------------------------------------------------------------
# Default bifaciality parameters.
# ------------------------------------------------------------------------------

BIFACIAL_DICT = {
    False: {
        "transmission": 0.0,
        "shade": 0.0,
        "mismatch": 0.0,
    },
    True: {
        "Fixed": {"transmission": 0.05, "shade": 0.200, "mismatch": 0.01},
        "Tracker": {"transmission": 0.05, "shade": 0.100, "mismatch": 0.005},
    },
}

# ------------------------------------------------------------------------------
# Default ohmic losses.
# ------------------------------------------------------------------------------

OHMIC_DICT = {"String": {"dc": 0.007, "ac": 0.010}, "Central": {"dc": 0.015, "ac": 0.005}}

# ------------------------------------------------------------------------------
# Other default values.
# ------------------------------------------------------------------------------
HEIGHT_FROM_GROUND_FIXED = 0.7
HEIGHT_FROM_GROUND_TRACKER = 1.5
Y_GAP = 0.03
NUMBER_OF_MODULES_HIGH = 1
CONSTANT_HEAT_COEFFICIENT = 29.0
CONVECTIVE_HEAT_COEFFICIENT = 0.0
MODULE_MISMATCH_FACTOR = 0.005

MIN_TEMP_VOC = -10.0  # Minimum temperature for Voc estimation.
DEFAULT_MUVOC_PCT = -0.25 / 100  # Default Voc (%/C)
TRANSFORMER_SPEC_ID = "Transformer Specification 1"
TRANSFORMER_NAME = "Transformer1"
TRANSFORMER_COUNT = 1
INVERTER_COUNT = 1
LAYOUT_COUNT = 1
STRINGS_IN_FRONT_ROW = 0
STRINGS_IN_BACK_ROW = 0
STRINGS_IN_RIGHT_ROW = 0
STRINGS_IN_LEFT_ROW = 0
STRINGS_IN_ISOLATED_ROW = 0
TERRAIN_AZIMUTH = 0.0
TERRAIN_SLOPE = 0.0
FRAME_BOTTOM_WIDTH = 0.0
IS_BACKTRACKING = True
