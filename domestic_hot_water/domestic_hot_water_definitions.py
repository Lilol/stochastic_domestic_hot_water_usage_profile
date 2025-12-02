from enum import Enum
from math import ceil
from os.path import join

import pandas as pd



class DiscreteProfile(Enum):
    """Enumeration for discrete hot water usage profiles."""
    LIGHT = "Light"
    MEDIUM = "Medium"
    HEAVY = "Heavy"
    MULTIPLE_HEAVY = "Multiple_Heavy"


_l_per_discrete_profile = {
    DiscreteProfile.LIGHT: 100,
    DiscreteProfile.MEDIUM: 180,
    DiscreteProfile.HEAVY: 320
}


class ContinuousProfile(Enum):
    """Enumeration for continuous hot water usage profiles."""
    Per1 = "1_Per"
    Per3 = "3_Per"
    Per10 = "10_Per"
    Per50P = "P50_Per"


def multiply_heavy_profile(vol_water_l):
    """Calculates the multiplied heavy usage profile based on water volume."""
    mult = ceil(vol_water_l / _l_per_discrete_profile[DiscreteProfile.HEAVY])
    prof = draw_off_statistics[DiscreteProfile.HEAVY].copy()
    prof["occurrence"] *= mult
    return prof


draw_offs = ["short", "medium", "shower", "bath"]


cols = ["occurrence", "volume_l"]
draw_off_statistics = {
    DiscreteProfile.LIGHT: pd.DataFrame([[18, 1], [7, 6], [1, 40], [0, 140]], columns=cols, index=draw_offs),
    DiscreteProfile.MEDIUM: pd.DataFrame([[28, 1], [12, 6], [2, 40], [0, 140]], columns=cols, index=draw_offs),
    DiscreteProfile.HEAVY: pd.DataFrame([[28, 1], [12, 6], [2, 40], [1, 140]], columns=cols, index=draw_offs),
}

class WaterHeaterData:
    """A class to manage data related to water heaters."""
    from utility.configuration import config

    water_heater_data = pd.read_csv(join(config.get("path", "input"), "water_heater.csv"), delimiter=';', header=0,
                                    index_col=0).transpose().sort_values(by="Volume")
    max_w_heater_size = water_heater_data["Volume"].max()
    max_power = water_heater_data["Power"].max()

    def get_heater_data(self, vol_water_l):
        """Retrieves heater data for a given water volume."""
        if vol_water_l in self.water_heater_data.Volume.values:
            return self.water_heater_data[self.water_heater_data.Volume == vol_water_l].iloc[0].squeeze()

        return self.get_multiple_water_heaters(vol_water_l = vol_water_l)

    def find_heater_by_power(self, power_kwh):
        """Finds a heater by its power rating."""
        if power_kwh <= self.max_power:
            return self.water_heater_data[self.water_heater_data.Power >= power_kwh].iloc[0].squeeze()

        return self.get_multiple_water_heaters(power_kwh=power_kwh)

    def get_multiple_water_heaters(self, vol_water_l=None, power_kwh=None):
        """Calculates data for multiple water heaters combined."""
        mul = 0
        heater = None
        if vol_water_l is not None:
            mul = ceil(vol_water_l / self.max_w_heater_size)
            heater = self.water_heater_data[self.water_heater_data.Volume == self.max_w_heater_size].iloc[0].copy()
        if power_kwh is not None:
            mul = ceil(power_kwh / self.max_power)
            heater = self.water_heater_data[self.water_heater_data.Power == self.max_power].iloc[0].copy()
        heater[["Volume", "Power", "Mass", "Area", "Energy loss kW", "Heat transfer coefficient"]] *= mul
        return heater.squeeze()

    def get_larger_heater_data(self, vol_water_l):
        """Retrieves data for a heater larger than the specified volume."""
        if vol_water_l > self.max_w_heater_size:
            return self.get_multiple_water_heaters(vol_water_l*2)

        return self.water_heater_data[self.water_heater_data.Volume > vol_water_l].iloc[0].squeeze()
