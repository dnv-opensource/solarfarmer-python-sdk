from pydantic import Field

from ._base import SolarFarmerBaseModel
from .module_index_range import ModuleIndexRange


class ModuleString(SolarFarmerBaseModel):
    """A string of modules defined as an ordered list of module index ranges.

    Used in 3D calculations to describe the physical arrangement of one
    series-connected string across one or more racks or trackers. Each
    :class:`ModuleIndexRange` entry defines a contiguous segment of modules;
    multiple ranges are taken in order to form the complete string.

    Attributes
    ----------
    module_index_ranges : list[ModuleIndexRange]
        Ordered list of index ranges that together define all modules in
        this string. Ranges are traversed in sequence: the string begins
        at the first index of the first range and ends at the last index
        of the final range
    """

    module_index_ranges: list[ModuleIndexRange] = Field(default_factory=list)
