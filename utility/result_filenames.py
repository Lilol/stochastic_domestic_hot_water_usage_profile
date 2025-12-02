from os import makedirs
from os.path import join

from utility.configuration import config
from utility.definitions import RunPhaseType, suffix_or_empty


class ResultFileNames:
    run_phase_type = None

    def __init__(self, directory):
        self._directory = directory
        makedirs(directory, exist_ok=True)

    @classmethod
    def make(cls, run_phase_type):
        return AggregatedResultFilenames if run_phase_type == RunPhaseType.AGG else (
            DetailedResultFilenames if run_phase_type == RunPhaseType.DETAILED else DisaggregatedResultFilenames)

    @classmethod
    def summary_filename(cls):
        if cls.run_phase_type is None:
            raise NotImplementedError
        return join(config.get("path", "output"), cls.run_phase_type.value, "summary.csv")

    @classmethod
    def simulation_filename(cls):
        if cls.run_phase_type is None:
            raise NotImplementedError
        return join(config.get("path", "output"), cls.run_phase_type.value, "simulation.csv")

    def _dir(self, network, optim_type):
        return join(self._directory, f"{optim_type.value}", f"{network.value}")

    def assemble_output_directory(self, network, optim_type, network_version=None, pv_ratio=None, bess_size=None,
                                  pv_power_addition=None, pv_estimation=None):
        out_dir = join(self._dir(network, optim_type), f"{suffix_or_empty(network_version)}")
        makedirs(out_dir, exist_ok=True)
        return out_dir

    def get_filename(self, base_filename, network_version=None, pv_ratio=None, bess_size=None, pv_power_addition=None,
                     pv_estimation=None):
        return (f"{base_filename}{suffix_or_empty(pv_estimation)}{suffix_or_empty(pv_power_addition)}"
                f"{suffix_or_empty(pv_ratio)}{suffix_or_empty(bess_size)}")

    def get_full_filename(self, base_filename, network, optim_type, pv_ratio, bess_size, pv_power_addition=None,
                          network_version=None, pv_estimation=None, extension="csv"):
        return join(self.assemble_output_directory(network, optim_type, network_version),
                    self.get_filename(base_filename, network_version, pv_ratio, bess_size, pv_power_addition,
                                      pv_estimation) + f".{extension}")


class AggregatedResultFilenames(ResultFileNames):
    run_phase_type = RunPhaseType.AGG

    def __init__(self, directory):
        super().__init__(directory)

    def _dir(self, network, optim_type):
        return join(self._directory, self.run_phase_type.value, f"{optim_type.value}", f"{network.value}")


class DisaggregatedResultFilenames(ResultFileNames):
    run_phase_type = RunPhaseType.DISAGG

    def __init__(self, directory):
        super().__init__(directory)

    def _dir(self, network, optim_type):
        return join(self._directory, self.run_phase_type.value, f"{network.value}", f"{optim_type.value}")

    def assemble_output_directory(self, network, optim_type, network_version=None, pv_ratio=None, bess_size=None,
                                  pv_power_addition=None, pv_estimation=None):
        return join(super().assemble_output_directory(network, optim_type, network_version, pv_ratio, bess_size,
                                                      pv_power_addition, pv_estimation),
                    f"{suffix_or_empty(pv_ratio)}", f"{suffix_or_empty(pv_estimation)}",
                    f"{suffix_or_empty(pv_power_addition)}", f"{suffix_or_empty(bess_size)}")

    def get_filename(self, base_filename, network_version=None, pv_ratio=None, bess_size=None, pv_power_addition=None,
                     pv_estimation=None):
        return f"{base_filename}"


class DetailedResultFilenames(DisaggregatedResultFilenames):
    run_phase_type = RunPhaseType.DETAILED

    def __init__(self, directory):
        super().__init__(directory)

    def _dir(self, network, optim_type):
        return join(self._directory, RunPhaseType.DETAILED.value, f"{network.value}", f"{optim_type.value}")
