pimport warnings
from enum import Enum

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

from numpy import random

seed = 0
random.seed(seed)

config_prototype_filename = "simulation_config"

def suffix_or_empty(name, suffix='', no_trailing_separator=False, sep='_'):
    """Creates a suffix for a filename, or returns an empty string."""
    if isinstance(name, Enum):
        name = name.value
    try:
        name = f"{float(name):.2f}"
    except ValueError:
        name = name
    return f"{suffix_or_empty(suffix, sep='' if no_trailing_separator else sep)}{sep}{name}" if name is not None and name != "" else ""

def filename_ending(params):
    """Creates a filename ending from a dictionary of parameters."""
    ending = f""
    for key, value in params.items():
        ending += f"_{key}_{value}"


class RunPhaseType(Enum):
    """Enumeration for the different run phase types."""
    AGG = "aggregated"
    DETAILED = "detailed"
    DISAGG = "disaggregated"


class RunPhase:
    """A base class for run phases."""
    type = type
    name = ''


class RunPhaseDetailed(RunPhase):
    """A run phase for detailed simulation."""
    type = RunPhaseType.DETAILED


class RunPhaseAgg(RunPhase):
    """A run phase for aggregated simulation."""
    type = RunPhaseType.AGG


class RunPhaseDisagg(RunPhase):
    """A run phase for disaggregated simulation."""
    type = RunPhaseType.DISAGG


class DET(RunPhaseDetailed):
    """A detailed run phase."""
    name = ""


class AGG(RunPhaseAgg):
    """An aggregated run phase."""
    name = ""


class DD(RunPhaseDisagg):
    """A disaggregated run phase with demand decrease."""
    name = "decrease_demand"


class SG(RunPhaseDisagg):
    """A disaggregated run phase with grid supplement."""
    name = "supplement_from_grid"


class OptimizationType(Enum):
    """Enumeration for the optimization type."""
    PROFILE = "profile"
    OPTIMAL_CONTROL = "optimized"


def get_all_strategies(cls=RunPhase, type=None):
    """Gets all run phase strategies."""
    all_subclasses = []

    for subclass in cls.__subclasses__():
        if type is None or subclass.type == type:
            all_subclasses.extend(subclass.__subclasses__())

    return all_subclasses


class PvSource(Enum):
    """Enumeration for the source of PV data."""
    MEASURED = "measured"
    TMY = "tmy"
    CLEAR_SKY = "clear_sky"
    ESTIMATED = "estimated"


class PvDistribution(Enum):
    """Enumeration for the PV distribution method."""
    DISTRIBUTE = "distribute"
    INCREASE = "increase"
    ORIGINAL = "original"
