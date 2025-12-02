from textwrap import wrap

from utility.definitions import OptimizationType, RunPhaseType, DD, SG, AGG

run_phase_label = {
    RunPhaseType.AGG: "Aggregated",
    RunPhaseType.DISAGG: "Disaggregated",
    AGG: "",
    DD: r"Decrease\ demand",
    SG: r"Supplement\ from\ grid"
}


optimization_type_label = {
    OptimizationType.OPTIMAL_CONTROL: r"Optimal\ control",
    OptimizationType.PROFILE: r"Profile"
}


def wrap_label(label):
    lines = wrap(f"{label}", 15)
    return '\n'.join(lines)
