from os.path import join

import matplotlib.pyplot as plt
import pandas as pd
from pandas import date_range

from domestic_hot_water.domestic_hot_water_profile import DomesticHotWaterProfile, IndividualHotWaterProfile
from utility.configuration import config


def main():
    """Generate a single DHW profile for a given yearly controlled energy and plot it."""
    # --- Read basic settings from config.ini ---
    input_directory = config.get("path", "input")
    output_directory = config.get("path", "network")  # reuse existing key for output dir
    year = config.getint("time", "simulation_year")
    resolution = config.get("time", "resolution")  # e.g. "1h" or "15min"

    # Example parameter: yearly electric energy used for DHW (kWh)
    # You can add this to config.ini under [domestic_hot_water] if you want it configurable
    try:
        e_yearly_controlled = config.getfloat("domestic_hot_water", "e_yearly_controlled")
    except KeyError:
        # fallback example – corresponds roughly to a small apartment
        e_yearly_controlled = 1500.0

    dhwp_file = join(input_directory, "dhwp.txt")

    # --- Build base stochastic daily/seasonal DHW shape ---
    dhwp = DomesticHotWaterProfile(dhwp_file, year)
    base_profile = dhwp.return_yearly_profile(
        date_range(start=f"{year}-01-01", end=f"{year}-12-31"), resolution
    )

    # --- Create an individual hot water profile from yearly energy ---
    ihwp = IndividualHotWaterProfile(dhwp)
    individual_profile = ihwp.get_individual_profile_from_e_yearly(e_yearly_controlled, year)

    if individual_profile is None:
        print("Yearly controlled energy is zero or NaN, nothing to generate.")
        return

    # --- Save profiles to CSV for further use ---
    output_profile_file = join(output_directory, f"dhw_profile_{year}.csv")
    # individual_profile is a DataFrame with column "Hot water [l/h]"
    individual_profile.to_csv(output_profile_file)
    print(f"DHW profile written to: {output_profile_file}")

    # --- Minimal visualization ---
    # 1) plot full-year time series (may be dense, but useful for sanity check)
    plt.figure(figsize=(10, 4))
    plt.plot(individual_profile.index, individual_profile["Hot water [l/h]"], linewidth=0.3)
    plt.title(f"Yearly DHW profile (year={year}, E_controlled={e_yearly_controlled:.0f} kWh)")
    plt.xlabel("Time")
    plt.ylabel("Hot water [l/h]")
    plt.tight_layout()

    # 2) zoom into first week for better visibility
    first_week_end = individual_profile.index.min() + pd.Timedelta(days=7)
    first_week = individual_profile.loc[individual_profile.index <= first_week_end]

    plt.figure(figsize=(10, 4))
    plt.plot(first_week.index, first_week["Hot water [l/h]"], linewidth=0.6)
    plt.title("DHW profile – first week")
    plt.xlabel("Time")
    plt.ylabel("Hot water [l/h]")
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
