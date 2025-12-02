import logging
import random

import holidays
import numpy as np
import pandas as pd

from domestic_hot_water.domestic_hot_water_definitions import DiscreteProfile, ContinuousProfile, draw_off_statistics, \
    _l_per_discrete_profile, multiply_heavy_profile, WaterHeaterData
from utility.configuration import config

random.seed(42)
logger = logging.getLogger(__name__)

class DomesticHotWaterProfile:
    # Statistical analysis, András Horkai
    _daily_consumption_per_apartment = 90.34
    # _monthly_consumption_difference = np.array(
    #    [6.47, 8.99, 6.61, 4.73, 1.28, -5.85, -16.20, -15.52, -3.13, 1.26, 4.57, 6.80])
    _monthly_consumption_multiplier = [0.94446941, 1., 0.93948275, 0.9306488, 0.80683964,
                                       0.80902368, 0.64041671, 0.61290937, 0.70255069, 0.79941814,
                                       0.85474001, 0.9720252]
    # Based on: A review of domestic hot water clustering profiles for application in
    # systems and buildings energy performance analysis; based on: Monthly domestic hot water profiles for energy
    # calculation in Finnish... (Ahmed et al.)
    _weekend_consumption_coefficient = 1.18

    def __init__(self, input_file, year):
        self.year = year
        self.df = pd.read_csv(input_file, header=None).transpose()
        self.df.columns = pd.MultiIndex.from_arrays(self.df.iloc[0:3].values)
        self.df = self.df.iloc[3:]
        self.df = self.df[self.df.columns[self.df.columns.get_level_values(0) == "August"]]
        self.df /= self.df.sum()
        self.df = self.df.apply(pd.to_numeric, errors="coerce")
        self.daily_consumption = self._monthly_consumption_multiplier
        self._hungary_holidays = holidays.country_holidays("Hungary", years=year)

    def is_holiday(self, day):
        return day in self._hungary_holidays

    def is_weekend(self, day):
        return not day.weekday() >= 5

    def is_weekday(self, day):
        return day.weekday() < 5

    def get_day(self, day):
        consumption_coefficient = 1
        if self.is_holiday(day):
            consumption_coefficient = self._weekend_consumption_coefficient
            df = self.df[self.df.columns[self.df.columns.get_level_values(1) == "Weekend"]]
        elif self.is_weekday(day):
            df = self.df[self.df.columns[self.df.columns.get_level_values(1) == "Weekday"]]
        else:
            consumption_coefficient = self._weekend_consumption_coefficient
            df = self.df[self.df.columns[self.df.columns.get_level_values(1) == "Weekend"]]
        df.columns = df.columns.get_level_values(2)
        df *= self._monthly_consumption_multiplier[day.month - 1] * consumption_coefficient
        df.index = pd.date_range(start=day, end=day + pd.Timedelta(hours=23), freq='h')
        return df

    def return_yearly_profile(self, days_of_year, resolution=config.get("time", "resolution")):
        output_df = pd.concat([self.get_day(day) for day in days_of_year], axis="rows")
        if resolution == "1h":
            output_df /= output_df.sum()
            return output_df
        elif resolution == "15min":
            output_df = output_df.resample('15min').mean().interpolate(method="spline", order=3)
            output_df /= output_df.sum()
            return output_df
        else:
            raise ValueError(f"Unknown resolution {resolution}")


class IndividualHotWaterProfile:
    """Generates individual hot water profiles for households."""
    # Based on KSH 2014 -- did not change radically since then
    water_consumption_per_person_per_day = 58.58
    c = 0.00116667  # kWh/kg/°C
    loss_coefficient = config.getfloat("domestic_hot_water", "loss_coefficient")
    stored_water_temp = config.getfloat("domestic_hot_water", "stored_water_temp")
    cold_water_temp = config.getfloat("domestic_hot_water", "cold_water_temp")
    hot_water_temp = config.getfloat("domestic_hot_water", "hot_water_temp")
    water_heater_data = WaterHeaterData()
    year = config.getint("time", "simulation_year")

    def __init__(self, domestic_hot_water_profile):
        """Initializes the IndividualHotWaterProfile with a DHW profile object."""
        self.yearly_dhw = domestic_hot_water_profile

    def get_individual_profile_from_e_yearly(self, e_yearly_controlled, year=None):
        """Generates an individual hot water profile based on yearly energy consumption."""
        if year is None:
            year = self.year
        yearly_profile = self.yearly_dhw.return_yearly_profile(
            pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31"))

        if np.isnan(e_yearly_controlled) or e_yearly_controlled == 0.:
            return None

        vol_water_used, n_people = IndividualHotWaterProfile.calc_number_of_occupants(
            e_yearly_controlled)
        discrete_water_usage_occurrences = self._get_discrete_water_usage(vol_water_used)

        return self._create_final_profile(yearly_profile, discrete_water_usage_occurrences, vol_water_used)

    @staticmethod
    def _get_discrete_water_usage_profile(vol_water_l):
        vol_water_l /= 365.
        if vol_water_l <= _l_per_discrete_profile[DiscreteProfile.LIGHT] * 1.2:
            return DiscreteProfile.LIGHT
        elif vol_water_l <= _l_per_discrete_profile[DiscreteProfile.MEDIUM] * 1.2:
            return DiscreteProfile.MEDIUM
        elif vol_water_l <= _l_per_discrete_profile[DiscreteProfile.HEAVY] * 1.2:
            return DiscreteProfile.HEAVY
        else:
            return DiscreteProfile.MULTIPLE_HEAVY

    def _get_discrete_water_usage(self, vol_water_l):
        profile = IndividualHotWaterProfile._get_discrete_water_usage_profile(vol_water_l)
        if profile == DiscreteProfile.MULTIPLE_HEAVY:
            return multiply_heavy_profile(vol_water_l)
        return draw_off_statistics[profile]

    def _create_final_profile(self, yearly_profile, discrete_water_usage_occurrences, vol_water_used):
        """Creates the final hot water profile from the yearly profile and usage occurrences."""
        df = pd.DataFrame(0, index=yearly_profile.index, columns=["Hot water [l/h]"])
        for draw_off_type, occurrences in discrete_water_usage_occurrences.iterrows():
            if occurrences.occurrence == 0:
                continue
            for i in range(int(occurrences.occurrence)):
                profile_selector = random.choice(yearly_profile.columns)
                random_day = random.choice(yearly_profile.index.dayofyear)
                random_hour = yearly_profile[profile_selector].nlargest(365 * 24).iloc[
                    random.randint(0, int(len(yearly_profile[profile_selector]) / 2))
                ]
                while random_hour == 0:
                    random_hour = yearly_profile[profile_selector].nlargest(365 * 24).iloc[
                        random.randint(0, int(len(yearly_profile[profile_selector]) / 2))
                    ]
                random_time = random_hour.name
                df.loc[random_time, "Hot water [l/h]"] += occurrences.volume_l

        df = df.resample(config.get("time", "resolution")).sum()
        df["Hot water [l/h]"] *= vol_water_used / df["Hot water [l/h]"].sum()
        return df

    @staticmethod
    def calc_number_of_occupants(e_yearly_controlled):
        """Calculates the number of occupants based on yearly controlled energy."""
        yearly_heat_consumption = e_yearly_controlled * IndividualHotWaterProfile.loss_coefficient
        vol_water_used = e_yearly_controlled / (
                (IndividualHotWaterProfile.hot_water_temp - IndividualHotWaterProfile.cold_water_temp) *
                IndividualHotWaterProfile.c * IndividualHotWaterProfile.loss_coefficient)
        n_people = round(vol_water_used / (IndividualHotWaterProfile.water_consumption_per_person_per_day * 365))
        return vol_water_used, n_people

    @staticmethod
    def calc_heater_size(n_people, e_yearly_controlled, measurement=None):
        """Calculates the required water heater size."""
        if n_people == 0:
            vol_water_l = 50
        else:
            vol_water_l = n_people * IndividualHotWaterProfile.water_consumption_per_person_per_day
        if measurement is not None:
            power = measurement[measurement > 0.2].max()
            if not np.isnan(power):
                heater = IndividualHotWaterProfile.water_heater_data.find_heater_by_power(power)
                if heater.Volume > vol_water_l:
                    return heater
        return IndividualHotWaterProfile.water_heater_data.get_heater_data(vol_water_l)
