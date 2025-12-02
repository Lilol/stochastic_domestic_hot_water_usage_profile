from os.path import isdir, join

import pandas as pd
from pandas import date_range, read_csv, concat

from domestic_hot_water.domestic_hot_water_profile import DomesticHotWaterProfile, IndividualHotWaterProfile
from optimization_configuration.in_out.profile_reader import FileReader
from optimization_configuration.in_out.results_writer import UnclusteredResultsWriter
from optimization_configuration.network.definitions import Network
from optimization_configuration.network.network_reader import NetworkReader, NetworkReaderForZNetwork
from optimization_configuration.network.network_version import NetworkVersion
from optimization_configuration.network.network_writer import NetworkWriter
from utility.configuration import config
from visualization.plot_water_usage import plot_water_usage

# This script generates network configurations and profiles for different scenarios.
output_directory = config.get("path", "network")
input_directory = config.get("path", "input")
year = config.getint("time", "simulation_year")
resolution = config.get("time", "resolution")

# Initialize readers and writers for network data and profiles.
reader = NetworkReader(output_directory)
reader_for_z = NetworkReaderForZNetwork(output_directory)
network_writer = NetworkWriter(input_directory, output_directory)
profile_writer = UnclusteredResultsWriter(output_directory)
networks = (Network.ZSOMBO,)

# individual, aggregated or use_file
# Configuration for water profile generation.
water_profile = "individual"
file = join(config.get("path", "input"), f"Profiles_{year}.csv")
ihwp, dhw, domestic_hot_water_profile = None, None, None
if water_profile in ("aggregated", "individual"):
    domestic_hot_water_profile = DomesticHotWaterProfile(join(input_directory, "dhwp.txt"), year)
    dhw = domestic_hot_water_profile.return_yearly_profile(date_range(start=f"{year}-01-01",
                                                                             end=f"{year}-12-31"), resolution)
    ihwp = IndividualHotWaterProfile(domestic_hot_water_profile) if water_profile == "individual" else None

if water_profile == "use_file":
    dhw = read_csv(join(output_directory, "dhw.csv"), header=0, index_col=0, parse_dates=True)

# DataFrame to store a summary of the generated network versions.
summary = pd.DataFrame(
    columns=["pv_power_addition", "pv_power_ratio", "controlled_positioning_method",
             "e_yearly_residential", "e_yearly_controlled", "e_yearly_pv"], index=range(20))
i = 0
# Read and preprocess the input data.
data, dates, original_data = FileReader(file).read_and_preprocess(sample_count=365, preprocess_for_clustering=False)
# Iterate over the specified networks.
for nw in networks:
    if not isdir(join(output_directory, f"{nw.value}")):
        continue
    print(f"Processing network '{nw.name}'")
    # Read the network data.
    network_data = reader.read(nw) if nw != Network.ZSOMBO else reader_for_z.read(nw)
    # Create a NetworkVersion object to manage different versions of the network.
    nwv = NetworkVersion(nw, network_data)
    all_profiles = []
    # Iterate over the different versions of the network.
    for v, modified_data in nwv.versions():
        print(f"Generating configuration for network version: {v.to_dict()}")
        # Write the network configuration and measurements for the current version.
        network_writer.write(modified_data, network=nw, bess_size=50, **v.to_dict())
        network_writer.write_measurements(modified_data, network=nw, **v.to_dict())
        # Store summary information for the current version.
        summary.loc[i] = (*v[
            ["pv_power_distribution_method", "pv_ratio", "controlled_positioning_method"]].values,
                          *modified_data.households[
                              ["e_yearly_residential", "e_yearly_controlled", "pv_power"]].sum(
                              axis="rows").values)
        i += 1
        print(f"Generating profiles...")
        # Generate individual hot water profiles.
        individual_profiles = ihwp.get_individual_profiles(modified_data, year)
        # Write out the generated profiles.
        profile_writer.write_out(dates, original_data,
                                                             individual_profiles,
                                                             network=nw, filename="profiles.csv",
                                                             **v.to_dict())
        profile_writer.write_out(dates, None, individual_profiles, network=nw, filename="dhw.csv",
                                 **v.to_dict())
        all_profiles.append(
            individual_profiles["Total"].rename(f"{'_'.join(f'{value}' for key, value in v.to_dict().items())}"))
        print("Processing finished\n")

    # Concatenate all generated profiles and write them out.
    all_profiles = concat(all_profiles, axis="columns")
    profile_writer.write_out(dates, all_profiles,
                     None, filename="dhw.csv", network=nw)
    UnclusteredResultsWriter(output_directory).write_out(dates, original_data, dhw, network=nw)
    print(f"Processing network finished\n")
    # Visualize the generated network versions.
    nwv.visualize_network_versions(savepath=join(output_directory, f"{nw.value}"))

# Plot the water usage.
plot_water_usage()
