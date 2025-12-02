from enum import Enum


class Network(Enum):
    """Enumeration for different network identifiers."""
    BARACS = 18680
    GYOR = 20667
    BALATONAKALI = 44333
    BALATONSZEPEZD = 44600
    ZSOMBO = 99999
    INVALID = 22222


class PvPlacement(Enum):
    """Enumeration for different PV placement strategies."""
    TYPICAL_LEAST_PV = "typical_least_pv"
    TYPICAL_MOST_PV = "typical_most_pv"
    ALL_HOUSEHOLDS = "all_households"
    ORIGINAL = "original"
