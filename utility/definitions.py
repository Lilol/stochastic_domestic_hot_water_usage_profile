import warnings
from enum import Enum

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

from numpy import random

seed = 0
random.seed(seed)

config_prototype_filename = "simulation_config"

def suffix_or_empty(name, suffix='', no_trailing_separator=False, sep='_'):
    if isinstance(name, Enum):
        name = name.value
    try:
        name = f"{float(name):.2f}"
    except ValueError:
        name = name
    return f"{suffix_or_empty(suffix, sep='' if no_trailing_separator else sep)}{sep}{name}" if name is not None and name != "" else ""

def filename_ending(params):
    ending = f""
    for key, value in params.items():
        ending += f"_{key}_{value}"


class RunPhaseType(Enum):
    AGG = "aggregated"
    DETAILED = "detailed"
    DISAGG = "disaggregated"


class RunPhase:
    type = type
    name = ''


class RunPhaseDetailed(RunPhase):
    type = RunPhaseType.DETAILED


class RunPhaseAgg(RunPhase):
    type = RunPhaseType.AGG


class RunPhaseDisagg(RunPhase):
    type = RunPhaseType.DISAGG


class DET(RunPhaseDetailed):
    name = ""


class AGG(RunPhaseAgg):
    name = ""


class DD(RunPhaseDisagg):
    name = "decrease_demand"


class SG(RunPhaseDisagg):
    name = "supplement_from_grid"


class OptimizationType(Enum):
    PROFILE = "profile"
    OPTIMAL_CONTROL = "optimized"


def get_all_strategies(cls=RunPhase, type=None):
    all_subclasses = []

    for subclass in cls.__subclasses__():
        if type is None or subclass.type == type:
            all_subclasses.extend(subclass.__subclasses__())

    return all_subclasses


class PvSource(Enum):
    MEASURED = "measured"
    TMY = "tmy"
    CLEAR_SKY = "clear_sky"
    ESTIMATED = "estimated"


class PvDistribution(Enum):
    DISTRIBUTE = "distribute"
    INCREASE = "increase"
    ORIGINAL = "original"
