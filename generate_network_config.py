from os.path import join

import matplotlib.pyplot as plt
import pandas as pd
from pandas import date_range

from domestic_hot_water.domestic_hot_water_profile import DomesticHotWaterProfile, IndividualHotWaterProfile
from utility.configuration import config


def main():
    """Generate one or more DHW profiles for given yearly energies and plot them."""
    # --- Read basic settings from config.ini ---
    input_directory = config.get("path", "input")
    output_directory = config.get("path", "network")  # reuse existing key for output dir
    year = config.getint("time", "simulation_year")
    resolution = config.get("time", "resolution")  # e.g. "1h" or "15min"

    # Example parameters: list of yearly electric energies used for DHW (kWh)
    # You can add this to config.ini under [domestic_hot_water] as comma-separated values, e.g.
    # e_yearly_list = 1000,1500,2000
    try:
        e_yearly_list = config.getarray("domestic_hot_water", "e_yearly_list", dtype=float)
    except KeyError:
        # fallback example – small set of typical apartment values
        e_yearly_list = [1000.0, 1500.0, 2000.0]

    dhwp_file = join(input_directory, "dhwp.txt")

    # --- Build base stochastic daily/seasonal DHW shape (keeps original DHW logic intact) ---
    dhwp = DomesticHotWaterProfile(dhwp_file, year)
    base_profile = dhwp.return_yearly_profile(
        date_range(start=f"{year}-01-01", end=f"{year}-12-31"), resolution
    )

    # --- Create individual profiles for all requested yearly energies ---
    ihwp = IndividualHotWaterProfile(dhwp)
    profiles = {}

    for e_yearly in e_yearly_list:
        profile = ihwp.get_individual_profile_from_e_yearly(e_yearly, year)
        if profile is None:
            continue
        key = f"{int(e_yearly)}kWh"
        profiles[key] = profile["Hot water [l/h]"]  # store as Series for easy concat

        # Save individual profile
        single_profile_file = join(output_directory, f"dhw_profile_{year}_{int(e_yearly)}kWh.csv")
        profile.to_csv(single_profile_file)
        print(f"DHW profile written to: {single_profile_file}")

    if not profiles:
        print("No valid yearly energies provided, nothing to generate.")
        return

    # --- Combine all profiles into one DataFrame ---
    all_profiles = pd.concat(profiles, axis="columns")
    combined_file = join(output_directory, f"dhw_profiles_{year}_combined.csv")
    all_profiles.to_csv(combined_file)
    print(f"Combined DHW profiles written to: {combined_file}")

    # --- Minimal visualization ---
    # Use the first generated profile as reference for full-year plot
    first_key = next(iter(profiles))
    first_profile = profiles[first_key]

    # 1) plot full-year time series for one representative profile
    plt.figure(figsize=(10, 4))
    plt.plot(first_profile.index, first_profile.values, linewidth=0.3)
    plt.title(f"Yearly DHW profile (year={year}, example={first_key})")
    plt.xlabel("Time")
    plt.ylabel("Hot water [l/h]")
    plt.tight_layout()

    # 2) zoom into first week and show all profiles as a bundle
    first_week_end = first_profile.index.min() + pd.Timedelta(days=7)
    first_week_profiles = all_profiles.loc[all_profiles.index <= first_week_end]

    plt.figure(figsize=(10, 4))
    for key in first_week_profiles.columns:
        plt.plot(first_week_profiles.index, first_week_profiles[key], linewidth=0.7, alpha=0.8, label=key)
    plt.title("DHW profiles – first week (multiple yearly energies)")
    plt.xlabel("Time")
    plt.ylabel("Hot water [l/h]")
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()

    # 3) plot daily-average profile (averaged over the year) for each energy level
    daily_avg = all_profiles.copy()
    # convert to average day-of-year curve
    daily_avg["day"] = daily_avg.index.dayofyear
    daily_means = daily_avg.groupby("day").mean()

    plt.figure(figsize=(10, 4))
    for key in daily_means.columns:
        plt.plot(daily_means.index, daily_means[key], label=key)
    plt.title("Average daily DHW usage vs. day of year")
    plt.xlabel("Day of year")
    plt.ylabel("Hot water [l/h]")
    plt.legend(loc="upper right", fontsize=8)
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
