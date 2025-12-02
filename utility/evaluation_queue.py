from optimization_configuration.network.definitions import Network
from utility.configuration import config
from utility.definitions import OptimizationType, PvSource


class EvaluationQueue:
    def __init__(self):
        networks = config.get("simulation", "networks")
        if len(networks) == 0:
            networks = (nw for nw in Network)
        optimization = config.get("simulation", "optimization")
        if len(optimization) == 0:
            optimization = (OptimizationType.OPTIMAL_CONTROL, OptimizationType.PROFILE)
        pv_estimation = config.get("simulation", "pv_estimation")
        if len(pv_estimation) == 0:
            pv_estimation = (PvSource.TMY,)
        pv_ratios = config.getarray("simulation", "pv_ratios", float)
        if len(pv_ratios) == 0:
            pv_ratios = (1.0,)
        bess_sizes = config.getarray("simulation", "bess_sizes", int)
        if len(bess_sizes) == 0:
            bess_sizes = (25, 50, 200)

        self.options = [{"network": nw, "opt": opt, "pv_ratio": pv, "pv_estimation": pv_est, "bess": bess} for bess in
                        bess_sizes for pv in pv_ratios for pv_est in pv_estimation for opt in optimization for nw in
                        networks]

        self.output_path = config.get("path", "output")
        self.input_path = config.get("path", "input")
        self.figures_output_path = config.get("path", "figures")

    def is_empty(self):
        return len(self.options) == 0

    def step(self):
        return self.options.pop()
