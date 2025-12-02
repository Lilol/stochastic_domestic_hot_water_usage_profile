from copy import copy, deepcopy
from os import makedirs
from os.path import join

import numpy as np
import yaml
from pandas import isna, DataFrame

from domestic_hot_water.domestic_hot_water_profile import IndividualHotWaterProfile
from optimization_configuration.network.configuration_file_names import NetworkConfigFileNames
from optimization_configuration.network.network_elements import UserPrototype, SimpleUserPrototype, hss
from utility.definitions import config_prototype_filename


def numpy_representer(dumper, data):
    """A representer for dumping numpy types to YAML."""
    if isinstance(data, (np.floating,)):
        return dumper.represent_float(float(data))
    elif isinstance(data, (np.integer,)):
        return dumper.represent_int(int(data))
    return dumper.represent_data(data)


yaml.add_representer(np.float64, numpy_representer)
yaml.add_representer(np.int64, numpy_representer)


class NetworkWriter:
    """Writes network configuration files."""
    filename = "load"
    measurement_filename = "measurements"

    def __init__(self, input_dir, output_directory, simplified_network=True):
        """Initializes the NetworkWriter."""
        self.__output_directory = output_directory
        prototype_file = open(join(input_dir, f"{config_prototype_filename}.yaml"), "r")
        self.config_proto = yaml.load(prototype_file, yaml.Loader)
        self.data_prototype = SimpleUserPrototype() if simplified_network else UserPrototype()
        self.simplified = simplified_network
        self.file_name_generator = NetworkConfigFileNames(output_directory)

    def write(self, network_data, **kwargs):
        """Writes the network configuration."""
        hss_data = kwargs.pop("hss_data", None)
        aggregation_level = kwargs.pop("aggregation_level", "both")
        if aggregation_level == "low" and not self.simplified:
            user_list = self.__write_aggregated(network_data, **kwargs)
        elif aggregation_level == "high":
            user_list = self.__write_disaggregated(network_data, **kwargs)
        elif aggregation_level == "both":
            user_list, hss_data = self.__write_both(network_data, **kwargs)
        else:
            raise ValueError(f"aggregation level value ('{aggregation_level}') is invalid!")
        self.write_config(user_list, network_data, hss_data, **kwargs)

    def write_measurements(self, network_data, **kwargs):
        """Writes the network measurement data."""
        aggregation_level = kwargs.pop("aggregation_level", "both")
        if aggregation_level in ("low", "both"):
            self.sum_network_measurements_by_type(network_data).to_csv(
                self.file_name_generator.profile_filename(f"{self.measurement_filename}_aggregated", **kwargs))
        if aggregation_level in ("high", "both"):
            network_data.measurements.to_csv(
                self.file_name_generator.profile_filename(f"{self.measurement_filename}_disaggregated", **kwargs))

    @staticmethod
    def sum_network_measurements_by_type(network_data):
        """Sums network measurements by load type."""
        measurement = DataFrame(columns=["PV", "Residential", "Controlled"])
        measurement["Controlled"] = network_data.measurements[network_data.get_controlled()].sum(axis="columns")
        measurement["Residential"] = network_data.measurements[network_data.get_residential()].sum(axis="columns")
        measurement["PV"] = network_data.measurements[network_data.get_pvs().astype(int)].sum(axis="columns")
        return measurement

    def __write_aggregated(self, network_data, **kwargs):
        """Writes the aggregated network configuration."""
        pv_filename = f"{self.filename}_pv"
        directory = self.file_name_generator.assemble_output_directory(**kwargs)
        makedirs(directory, exist_ok=True)
        data = self.sum_network_measurements_by_type(network_data)
        with open(join(directory, f"{pv_filename}.yaml"), "w") as file:
            tmp = data.copy()
            tmp.e_yearly_residential = 0.0
            tmp.e_yearly_controlled = 0.0
            to_dump = self.mod_prototype(tmp, network_data)
            yaml.dump(
                {"units": {name: element.__dict__ for name, element in to_dump.data.items() if not element.is_null()}},
                file)

        battery_filename = f"{self.filename}_battery"
        with open(join(directory, f"{battery_filename}.yaml"), "w") as file:
            data.pv_power = 0.0
            to_dump = self.mod_prototype(data, network_data)
            yaml.dump(
                {"units": {name: element.__dict__ for name, element in to_dump.data.items() if not element.is_null()}},
                file)
        return [pv_filename, battery_filename]

    def __write_disaggregated(self, network_data, **kwargs):
        """Writes the disaggregated network configuration."""
        bess_size = kwargs.pop("bess_size") if "bess_size" in kwargs else 0
        directory = self.file_name_generator.assemble_output_directory(**kwargs)
        makedirs(directory, exist_ok=True)

        loads = []
        hss_data = hss().reset()
        if bess_size > 0:
            loads.append(self.write_out_bess(directory, bess_size))
        for i, row in network_data.households.iterrows():
            load_name = f"{self.filename}_{i}"
            loads.append(load_name)
            with open(join(directory, f"{load_name}.yaml"), "w") as file:
                to_dump = self.mod_prototype(row, network_data, i)
                hss_data = hss_data + to_dump.data["hss"]
                yaml.dump({"units": {name: element.to_dict() for name, element in to_dump.data.items() if
                                     not element.is_null()}}, file)
        return loads, hss_data

    def write_out_bess(self, directory, bess_size):
        name = f"{self.filename}_battery"
        with open(join(directory, f"{name}.yaml"), "w") as file:
            modified = deepcopy(self.data_prototype)
            modified["bess"].size = bess_size
            modified["name"].name = "battery"
            self.__delete_components(modified.data)
            yaml.dump(
                {"units": {name: element.__dict__ for name, element in modified.data.items() if not element.is_null()}},
                file)
        return name

    @staticmethod
    def __delete_components(data, components=None):
        if components is None:
            components = ("pv", "ut", "ue", "hss")
        for c in components:
            del data[c]

    def __write_both(self, network_data, **kwargs):
        return self.__write_disaggregated(network_data, **kwargs)

    @staticmethod
    def __calc_hss_size(e_yearly_controlled, measurement):
        _, n_people = IndividualHotWaterProfile.calc_number_of_occupants(e_yearly_controlled)
        return IndividualHotWaterProfile.calc_heater_size(n_people, e_yearly_controlled, measurement)

    def mod_prototype(self, data, network_data, user_name=None):
        modified = deepcopy(self.data_prototype)
        modified["name"].name = user_name
        if data.e_yearly_controlled != 0 and not isna(data.e_yearly_controlled):
            modified["ut"].size = data.e_yearly_controlled
            modified["ut"].profile = network_data.get_measurement_id_controlled(user_name)
            if not self.simplified:
                modified["boil"].size = data.e_yearly_controlled
            else:
                heater_data = self.__calc_hss_size(data.e_yearly_controlled, network_data.get_measurement(user_name, 3))
                modified["hss"].size = heater_data.Volume
                modified["hss"].hss_params["vol_hss_water"] = heater_data.Volume
                modified["hss"].hss_params["size_elh"] = heater_data.Power
                modified["hss"].hss_params["t_hss_in"] = heater_data["Heatup time"]
                modified["hss"].hss_params["T_max"] = heater_data["Max temperature"]
                modified["hss"].hss_params["a_hss"] = heater_data["Heat transfer coefficient"]
                modified["hss"].profile = user_name
        if data.e_yearly_residential != 0 and not isna(data.e_yearly_residential):
            modified["ue"].size = data.e_yearly_residential
            modified["ue"].profile = network_data.get_measurement_id_residential(user_name)
            if not self.simplified and modified["grid"].size < modified["ue"].size + modified["ut"].size:
                modified["grid"].size = modified["ue"].size
                modified["grid"].p_inj_max = modified["ue"].size
                modified["grid"].p_with_max = modified["ue"].size
        if data.pv_power != 0 and not isna(data.pv_power):
            modified["pv"].size = data.pv_power
            modified["pv"].profile = network_data.get_measurement_id_pv(user_name)

        return modified

    def write_config(self, user_list, network_data=None, hss_data=None, **kwargs):
        proto = copy(self.config_proto)
        if "network" in kwargs:
            proto["sim_name"] = str(kwargs["network"].value)
        aggregation_level = kwargs.get("aggregation_level", "both")
        if aggregation_level in ("high", "both"):
            self.__write_disaggregated_config(user_list, **kwargs)
        if aggregation_level in ("low", "both"):
            self.__write_aggregated_config(network_data.households.sum(), hss_data, **kwargs)

    def __write_disaggregated_config(self, user_list, **kwargs):
        proto = copy(self.config_proto)
        self.__delete_components(proto, ("pv", "ut", "ue", "hss", "bess"))
        if "network" in kwargs:
            proto["sim_name"] = str(kwargs["network"].value)
        proto["users_list"] = user_list
        if "bess_size" in kwargs:
            kwargs.pop("bess_size")
        with open(self.file_name_generator.generic_network_filename(f"{config_prototype_filename}_disaggregated",
                                                                    **kwargs), "w") as file:
            yaml.dump(proto, file)

    def __write_aggregated_config(self, network_data, hss_data, **kwargs):
        assert network_data is not None, "Network data should be passed with simplified_framework option!"
        proto = copy(self.config_proto)
        if "network" in kwargs:
            proto["sim_name"] = str(kwargs["network"].value)
        proto["ut"]["size"] = float(network_data.e_yearly_controlled)
        proto["ue"]["size"] = float(network_data.e_yearly_residential)
        proto["pv"]["size"] = float(network_data.pv_power)
        proto["bess"]["size"] = kwargs.pop("bess_size", 0)
        proto["hss"]["vol_hss_water"] = hss_data.hss_params["vol_hss_water"]
        proto["hss"]["size_elh"] = hss_data.hss_params["size_elh"]
        proto["hss"]["T_max"] = hss_data.hss_params["T_max"]
        proto["hss"]["T_set"] = hss_data.hss_params["T_set"]
        proto["hss"]["T_min"] = hss_data.hss_params["T_min"]
        proto["hss"]["T_out"] = hss_data.hss_params["T_out"]
        proto["hss"]["T_in"] = hss_data.hss_params["T_in"]
        proto["hss"]["a_hss"] = hss_data.hss_params["a_hss"]
        proto["hss"]["profile"] = "Total"
        with open(self.file_name_generator.generic_network_filename(f"{config_prototype_filename}_disaggregated",
                                                                    **kwargs), "w") as file:
            yaml.dump(proto, file)
