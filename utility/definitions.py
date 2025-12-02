import warnings
from enum import Enum

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

from numpy import random

seed = 0
random.seed(seed)


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
