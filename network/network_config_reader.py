from os.path import join

from yaml import safe_load, YAMLError

import utility.configuration as configuration
from optimization_configuration import NetworkConfigFileNames
from optimization_configuration.network.network_elements import NetworkPrototype
from utility.definitions import config_prototype_filename, RunPhaseType


class NetworkConfigReader:
    """Reads network configuration from files."""
    def __init__(self):
        """Initializes the NetworkConfigReader."""
        self.path = configuration.config.get("path", "network")
        self.file_name_generator = NetworkConfigFileNames(self.path)

    def read(self, nw, network_version=None, aggregation_level=RunPhaseType.AGG, pv_power_addition=None):
        """Reads and parses the network configuration file."""
        network_config = self.file_name_generator.generic_network_filename(config_prototype_filename, nw, 1.0,
                                                                           aggregation_level, network_version,
                                                                           pv_power_addition)

        with open(network_config, 'r') as file:
            try:
                data = safe_load(file)
            except YAMLError as exc:
                print(exc)
                return None

        if "users_list" not in data:
            return data

        return NetworkPrototype.read(data["users_list"], join(self.path, f"{nw.value}", "Users"))
