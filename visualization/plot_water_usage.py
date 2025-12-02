from collections import defaultdict
from os.path import join, isdir

import numpy as np
import pandas
from pandas import read_csv, concat, to_datetime

from domestic_hot_water.domestic_hot_water_definitions import DiscreteProfile
from domestic_hot_water.domestic_hot_water_profile import DomesticHotWaterProfile, IndividualHotWaterProfile
from optimization_configuration.network.network_reader import NetworkReader, NetworkReaderForZNetwork
from optimization_configuration.network.definitions import Network
from utility import configuration
from visualization.plot import plot_rand_water_profiles, plot_water_profiles


scenario = "distribute_1.00_typical_most_pv"
def plot_water_usage():
    network_directory = configuration.config.get("path", "network")
    reader_for_z = NetworkReaderForZNetwork(network_directory)
    reader = NetworkReader(network_directory)
    output_directory = configuration.config.get("path", "input")
    dhwp_input = configuration.config.get("path", "input")
    year = configuration.config.getint("time", "simulation_year")

    dhw = read_csv(join(output_directory, "dhw.csv"), header=0, index_col=0)
    dhw.index = to_datetime(dhw.index)
    domestic_hot_water_profile = DomesticHotWaterProfile(join(dhwp_input, "dhwp.txt"), year)
    original_dhw = domestic_hot_water_profile.return_yearly_profile(
        pandas.date_range(start=f"{year}-01-01", end=f"{year}-12-31"), configuration.config.get("time", "resolution"))
    original_dhw /= original_dhw.sum()

    for nw in (Network.ZSOMBO,):
        if not isdir(join(network_directory, f"{nw.value}")):
            print(f"Skipping network '{nw.name}' as directory not found")
            continue
        print(f"Processing network '{nw.name}'")
        network_data = reader.read(nw) if nw != Network.ZSOMBO else reader_for_z.read(nw)
        nw_sum = network_data.households.sum(axis="rows")
        original_dhw.loc[:, f"{nw.value}_Orig"] = nw_sum.e_yearly_controlled * 0.9 * original_dhw.P50_Per / (35 * 0.00116667)
    original_dhw.index = to_datetime(original_dhw.index)

    dhw = concat([dhw, original_dhw], axis="columns")

    n_prof_in_each_cat = 2
    for nw in (Network.ZSOMBO,):
        if not isdir(join(network_directory, f"{nw.value}")):
            print(f"Skipping network '{nw.name}' as directory not found")
            continue
        print(f"Processing network '{nw.name}'")
        network_data = reader.read(nw) if nw != Network.ZSOMBO else reader_for_z.read(nw)
        print(nw.value)
        print(network_data.households.e_yearly_controlled.sum() / network_data.households.e_yearly_residential.sum())
        print(network_data.households.e_yearly_controlled.sum())
        profile_types = defaultdict(list)
        for consumer_id, consumption in network_data.households.iterrows():
            if np.isnan(consumption.e_yearly_controlled) or consumption.e_yearly_controlled == 0.:
                continue
            vol_water, n_people = \
                IndividualHotWaterProfile.calc_number_of_occupants(consumption.e_yearly_controlled)
            profile_types[IndividualHotWaterProfile._get_discrete_water_usage_profile(vol_water)].append(f"{consumer_id}")

        consumers = []
        lines = {}
        for p in DiscreteProfile:
            for n in range(n_prof_in_each_cat):
                try:
                    c = profile_types[p][n]
                except IndexError as e:
                    print(f"Profile type: '{p.value}' not found in dataset\nError: {e}")
                else:
                    consumers.append(f"{c}")
                    lines[f"{c}"] = p.value

        individual_profiles = read_csv(join(network_directory, f"{nw.value}", scenario, "dhw.csv"), header=0, index_col=0, dtype=str)
        individual_profiles.index = to_datetime(individual_profiles.index)
        plot_rand_water_profiles(individual_profiles, consumers, nw, lines)

        print(dhw[f"{nw.value}"].sum() / dhw[f"{nw.value}_Orig"].sum())


if __name__ == "__main__":
    plot_water_usage()
