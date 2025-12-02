from configparser import RawConfigParser, ExtendedInterpolation
from os import getcwd
from os.path import join
from sys import argv

from pandas import read_excel, to_datetime, Timedelta

from optimization_configuration.network.definitions import Network, PvPlacement
from utility.definitions import PvSource, PvDistribution, RunPhaseType, DD, SG, OptimizationType


class ConfigurationManager:
    def __init__(self, config_filename=join(getcwd(), "config", "config.ini")):
        self.__config = RawConfigParser(allow_no_value=True, interpolation=ExtendedInterpolation())
        self.__config.read_file(open(config_filename))
        self._registered_entries = {
            "simulation":
                {"networks": self._process_networks,
                 "pv_distribution": self._process_pv_distribution,
                 "disaggregation_strategy": self._process_disaggregation_strategy,
                 "simulation_step": self._process_simulation_step,
                 "network_versions": self._process_network_version,
                 "optimization": self._process_optimization_type,
                 "pv_estimation": self._process_pv_estimation},
        }

    def _process_pv_estimation(self):
        return self.getarray("simulation", "pv_estimation", dtype=PvSource)

    def _process_optimization_type(self):
        return self.getarray("simulation", "optimization", dtype=OptimizationType)

    def _process_pv_distribution(self):
        return self.getarray("simulation", "pv_distribution", dtype=PvDistribution)

    def _process_networks(self):
        return [Network(nw) for nw in self.getarray("simulation", "networks", dtype=int)]

    def _process_network_version(self):
        return self.getarray("simulation", "network_versions", dtype=PvPlacement)

    def _process_simulation_step(self):
        return self.getarray("simulation", "simulation_step", dtype=RunPhaseType)

    def _process_disaggregation_strategy(self):
        disagg_strategy = self.get("simulation", "disaggregation_strategy")
        if disagg_strategy == "decrease_demand":
            return DD
        elif disagg_strategy == "supplement_from_grid":
            return SG
        else:
            raise ValueError(f"Unknown disaggregation type {disagg_strategy}")

    def getarray(self, section, key, dtype=str, fallback=None):
        val = self._get(section, key, fallback=fallback)
        try:
            return [dtype(v) for v in val]
        except TypeError:
            return [dtype(val), ]

    def get(self, section, key, fallback=None):
        if section not in self._registered_entries or key not in self._registered_entries[section]:
            return self._get(section, key, fallback)
        return self._registered_entries[section][key]()

    def _get(self, section, key, fallback=None):
        try:
            value = self.__config.get(section, key, fallback=fallback)
        except Exception as e:
            raise KeyError(f"Section '{section}', key '{key}' problem in configuration: '{e}'")
        if value is None:
            raise KeyError(f"Section '{section}', key '{key}' not found in configuration")

        if "," not in value:
            return value

        return list(filter(len, value.strip('][').split(',')))

    def set(self, section, key, value):
        self.__config.set(section, key, value)

    def setboolean(self, section, key, value):
        boolean_str = 'True' if value else 'False'
        self.__config.set(section, key, boolean_str)

    def getboolean(self, section, key, fallback=None):
        return self.__config.getboolean(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        return self.__config.getint(section, key, fallback=fallback)

    def getfloat(self, section, key, fallback=None):
        return self.__config.getfloat(section, key, fallback=fallback)

    def has_option(self, section, option):
        return self.__config.has_option(section, option)


# init_config
config_file = argv[2] if len(argv) >= 3 else join(getcwd(), 'config', 'config.ini')
config = ConfigurationManager(config_filename=config_file)


def read_slp():
    # Ugly ass code
    prof_file = join(config.get("path", "root"), "Profiles.csv")
    profiles = read_excel(prof_file, header=0, index_col=0)
    profiles.loc[:, "Datetime"] = profiles.index.astype("str") + " " + profiles["Time"].astype("str")
    profiles.loc[profiles['Datetime'].str.contains('24:00'), "Datetime"] = to_datetime(
        profiles.loc[profiles['Datetime'].str.contains('24:00'), 'Datetime'].str.replace('24:00', '00:00')) + Timedelta(
        days=1)
    profiles.index = to_datetime(profiles["Datetime"])
    return profiles
