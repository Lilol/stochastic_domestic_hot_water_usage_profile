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
        self.yearly_dhw = domestic_hot_water_profile

    def get_individual_profiles(self, network_data, year=None):
        if year is None:
            year = self.year
        yearly_profile = self.yearly_dhw.return_yearly_profile(
            pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31"))
        all_profiles = []
        for consumer_id, consumption in network_data.households.iterrows():
            if np.isnan(consumption.e_yearly_controlled) or consumption.e_yearly_controlled == 0.:
                continue
            vol_water_used, n_people = IndividualHotWaterProfile.calc_number_of_occupants(
                consumption.e_yearly_controlled)
            discrete_water_usage_occurrences = self._get_discrete_water_usage(vol_water_used)
            occupant_profile = self._get_occupant_profile(yearly_profile, n_people)
            individual_continuous_profile = occupant_profile.copy() * vol_water_used
            heater = self.calc_heater_size(n_people, consumption.e_yearly_controlled,
                                           network_data.get_measurement(consumer_id, 3))
            individual_discrete_profile = self._construct_individual_discrete_profile(discrete_water_usage_occurrences,
                                                                                      individual_continuous_profile,
                                                                                      consumer_id,
                                                                                      heater.Volume)
            all_profiles.append(individual_discrete_profile)
            if np.any(individual_discrete_profile > heater.Volume):
                raise ValueError(f"Withdrawn water amount exceeded hot water storage size {heater.Volume}")

        all_profiles = pd.concat(all_profiles, axis="columns")
        all_profiles.loc[:, "Total"] = all_profiles.sum(axis="columns")
        return all_profiles

    @classmethod
    def calc_number_of_occupants(cls, e_yearly):
        yearly_heat_consumption = e_yearly * cls.loss_coefficient
        vol_water_used \
            = yearly_heat_consumption / (cls.c * (cls.hot_water_temp - cls.cold_water_temp))
        n_people = round(vol_water_used / (cls.water_consumption_per_person_per_day * 365))
        return vol_water_used, n_people

    @staticmethod
    def calc_heater_size(n_people, e_yearly_controlled, measurement):
        if n_people <= 1:
            vol = 80
        elif n_people in (2, 3):
            vol = 120
        elif n_people == 4:
            vol = 150
        elif n_people <= 7:
            vol = 200
        elif n_people <= 14:
            # Two 200-l boilers
            vol = 400
        elif n_people <= 21:
            vol = 600
        else:
            raise ValueError(f"Number of people is too large {n_people}")
        heater_data = IndividualHotWaterProfile.water_heater_data.get_heater_data(vol)
        if heater_data.Power < measurement.max():
            heater_data = IndividualHotWaterProfile.water_heater_data.find_heater_by_power(measurement.max())
        return heater_data

    @staticmethod
    def _get_discrete_water_usage(vol_water_l):
        profile_type = IndividualHotWaterProfile._get_discrete_water_usage_profile(vol_water_l)
        if profile_type != DiscreteProfile.MULTIPLE_HEAVY:
            return draw_off_statistics[profile_type]
        return multiply_heavy_profile(vol_water_l/365.)

    @staticmethod
    def _get_discrete_water_usage_profile(vol_water_l):
        vol_water_l /= 365.
        if vol_water_l <= _l_per_discrete_profile[DiscreteProfile.LIGHT]:
            return DiscreteProfile.LIGHT
        elif vol_water_l <= _l_per_discrete_profile[DiscreteProfile.MEDIUM]:
            return DiscreteProfile.MEDIUM
        elif vol_water_l <= _l_per_discrete_profile[DiscreteProfile.HEAVY]:
            return DiscreteProfile.HEAVY
        else:
            return DiscreteProfile.MULTIPLE_HEAVY

    def _get_occupant_profile(self, yearly_profile, n_people):
        if n_people == 1:
            return yearly_profile[ContinuousProfile.Per1.value]
        elif n_people in (2, 3):
            return yearly_profile[ContinuousProfile.Per3.value]
        elif 3 < n_people < 50:
            return yearly_profile[ContinuousProfile.Per10.value]
        else:
            # This is also used for the '0' occupant profile, when there is extremely little water usage
            return yearly_profile[ContinuousProfile.Per50P.value]

    def _construct_individual_discrete_profile(self, discrete_water_usage_occurrences, individual_continuous_profile,
                                               consumer_id, max_drawoff):
        dfs = []
        for date, daily_profile in individual_continuous_profile.groupby(pd.Grouper(freq='D')):
            df = self._distribute_water_usage_occurrences(discrete_water_usage_occurrences,
                                                                              daily_profile, max_drawoff)
            df.name = f"{consumer_id}"
            dfs.append(df)
        dfs = pd.concat(dfs, axis="rows")
        return dfs

    def _distribute_water_usage_occurrences(self, discrete_water_usage_occurrences, daily_continuous_profile,
                                            max_drawoff):
        daily_discrete_profile = daily_continuous_profile.copy()
        daily_discrete_profile[:] = 0
        d_idx, c_idx = None, None
        for do in ("bath", "shower", "medium", "short"):
            d_idx, c_idx = self._add_draw_off_to_profile(do, daily_discrete_profile, daily_continuous_profile,
                                                         discrete_water_usage_occurrences.copy(), max_drawoff,
                                                         d_idx=(d_idx if do == "shower" else None),
                                                         c_idx=(c_idx if do == "shower" else None))
        self.check_for_remaining_water(daily_continuous_profile, daily_discrete_profile)
        return daily_discrete_profile

    def _add_draw_off_to_profile(self, do, daily_discrete_profile, daily_continuous_profile,
                                 discrete_water_usage_occurrences, max_drawoff, d_idx=None, c_idx=None):
        occurrences = discrete_water_usage_occurrences.loc[do, "occurrence"]
        if occurrences == 0:
            return None, None
        if d_idx is None:
            d_idx, c_idx = self._get_index(do, daily_continuous_profile)
        for i in range(occurrences):
            volume = discrete_water_usage_occurrences.loc[do, "volume_l"]
            if self.check_for_remaining_water(daily_continuous_profile, daily_discrete_profile, volume, do):
                return None, None
            daily_discrete_profile[d_idx] += volume
            daily_continuous_profile[c_idx] -= volume
            self._check_for_maximum_drawoff(daily_continuous_profile, daily_discrete_profile, d_idx, c_idx, max_drawoff)
            self._redistribute_negative_draw_off(daily_continuous_profile, c_idx)
            self._redistribute_max_draw_off(daily_continuous_profile, max_drawoff)
            discrete_water_usage_occurrences.loc[do, "occurrence"] -= 1
            if discrete_water_usage_occurrences.loc[do, "occurrence"] != 0:
                d_idx, c_idx = self._get_index(do, daily_continuous_profile)
        return d_idx, c_idx

    def _check_for_maximum_drawoff(self, daily_continuous_profile, daily_discrete_profile, d_idx, c_idx, max_drawoff):
        if daily_discrete_profile[d_idx] > max_drawoff:
            daily_continuous_profile[c_idx] += daily_discrete_profile[d_idx] - max_drawoff
            daily_discrete_profile[d_idx] = max_drawoff

    def _get_index(self, do, daily_continuous_profile):
        if do == "shower":
            i = daily_continuous_profile.idxmax()
            return i + pd.Timedelta(hours=self.__get_rand_time_offset(i)), i
        elif do == "bath":
            i = daily_continuous_profile.nlargest(2).index[1]
            return i + pd.Timedelta(hours=self.__get_rand_time_offset(i)), i
        else:
            i = random.choices(daily_continuous_profile.index, daily_continuous_profile, k=1)[0]
            return i, i

    def __get_rand_time_offset(self, i):
        if i.hour == 0:
            return random.choices([0, 1, 2], [1, 0.75, 0.5], k=1)[0]
        elif i.hour == 23:
            return random.choices([-2, -1, 0], [0.5, 0.75, 1], k=1)[0]
        return random.choices([-1, 0, 1], [0.75, 1, 0.75], k=1)[0]

    def check_for_remaining_water(self, daily_continuous_profile, daily_discrete_profile, volume=None, do=None):
        if volume is None and do is None:
            d_idx, _ = self._get_index(do, daily_continuous_profile)
            daily_discrete_profile[d_idx] = daily_continuous_profile.sum()
            return True
        if volume > daily_continuous_profile.sum():
            if do == "short":
                d_idx, _ = self._get_index(do, daily_continuous_profile)
                daily_discrete_profile[d_idx] = daily_continuous_profile.sum()
            return True
        else:
            return False

    def _redistribute_negative_draw_off(self, daily_continuous_profile, idx):
        if daily_continuous_profile[idx] > 0:
            return

        # TODO: Fix daily drawoffs, could results in more than maxdrawoff
        vol_diff = -1 * daily_continuous_profile[idx]
        daily_continuous_profile[idx] = 0
        non_diff_values = daily_continuous_profile[daily_continuous_profile.index != idx]
        daily_continuous_profile[
            daily_continuous_profile.index != idx] -= non_diff_values / non_diff_values.sum() * vol_diff

    def _redistribute_max_draw_off(self, daily_continuous_profile, max_drawoff):
        if not any(daily_continuous_profile > max_drawoff):
            return
        indices = daily_continuous_profile[daily_continuous_profile > max_drawoff].index
        vol_diff = daily_continuous_profile[indices].sum()
        non_diff_values = daily_continuous_profile[~daily_continuous_profile.index.isin(indices)]
        daily_continuous_profile[non_diff_values.index] += non_diff_values / non_diff_values.sum() * vol_diff
        if not all(daily_continuous_profile <=max_drawoff):
            logger.error(f"Error in redistributing water drawoffs, remaining volume is removed from the profile: "
                         f"{(daily_continuous_profile[daily_continuous_profile > max_drawoff] - max_drawoff).sum()} l")
            daily_continuous_profile[daily_continuous_profile > max_drawoff] = max_drawoff
