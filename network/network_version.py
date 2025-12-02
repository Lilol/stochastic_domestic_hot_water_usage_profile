from copy import deepcopy
from itertools import chain, repeat

import numpy as np
from pandas import Index, concat, DataFrame, Series

from utility.configuration import config


def plot_cont_res(data):
    import matplotlib.pyplot as plt
    plt.plot(data.households.loc[data.households.e_yearly_residential < 50000, "e_yearly_residential"],
             label="E yearly residential (kWh)")
    plt.plot(data.households.loc[data.households.e_yearly_residential < 50000, "e_yearly_controlled"],
             label="E yearly controlled (kWh)")
    plt.legend()
    plt.xlabel("Household")
    plt.xticks([], [])
    plt.show()


def plot_cont_res_scat(data, cl_m, cl_y0):
    import matplotlib.pyplot as plt
    plt.scatter(data.households.loc[data.households.e_yearly_residential < 50000, "e_yearly_residential"],
                data.households.loc[data.households.e_yearly_residential < 50000, "e_yearly_controlled"])
    plt.ylabel("E yearly controlled (kWh)")
    plt.xlabel("E yearly residential (kWh)")
    plt.show()

    import matplotlib.pyplot as plt
    plt.close()
    filter = (data.households.e_yearly_residential < 6000) & (data.households.e_yearly_controlled > 700)
    plt.scatter(data.households.loc[filter, "e_yearly_residential"], data.households.loc[filter, "e_yearly_controlled"],
                label="original points")
    plt.plot(data.households.loc[filter, "e_yearly_residential"],
             data.households.loc[filter, "e_yearly_residential"] * cl_m + cl_y0, "r", label="fitted line")
    plt.legend()
    plt.ylabel("E yearly controlled (kWh)")
    plt.xlabel("E yearly residential (kWh)")
    plt.show()


def remove_original_controlled(data):
    data.households.loc[:, "e_yearly_controlled"] = 0
    controlled = data.get_controlled()
    data.identifiers = data.identifiers.drop(index=controlled.astype(int))
    data.measurements = data.measurements.drop(columns=controlled)


class NetworkVersion:
    # KSH https://www.portfolio.hu/uzlet/20230129/b-es-h-tarifa-igy-allunk-az-ejszakai-es-hoszivattyus-aram-fogyasztasaval-593310
    # 0.29
    typical_controlled_penetration = 0.42
    id_type = int

    def __init__(self, nw, network_data):
        self.nw = nw
        self.controlled_consumer_penetration_type = (
            "original", "typical_least_pv", "typical_most_pv", "all_households")
        # Maybe skip 'central' and only consider in terms of economics: is there a difference?
        # Test this with one experiment
        self.pv_power_distribution_method = ("increase", "distribute", "original")
        self.pv_power_ratio = config.getarray("simulation", "pv_ratios", float)
        self.universal_production = None
        self.added_pvs = None
        self.added_cl = None
        self.cl_m = 0
        self.cl_y0 = 0
        self.boiler_power = np.array([1.2, 1.5, 1.8, 2, 2.4, 2.8, 3, 3.5, 4.8])
        self.n_different_powers = len(self.boiler_power)
        self.available_yearly_power_values = None
        self.network_data = deepcopy(network_data)
        self.network_data.convert_identifier_type(NetworkVersion.id_type)
        # container to store stats for each generated network version
        self.collected_versions = []

    def register_possible_controlled_power(self, data):
        cm = data.identifiers.loc[data.identifiers.load_type == 3, "MeterNo"]
        self.available_yearly_power_values = DataFrame(
            columns=["meter", "scale", "yearly_energy", "original_likely_power"],
            index=range(self.n_different_powers * len(cm)))
        controlled = data.measurements[cm.index]
        likely_power = DataFrame(index=controlled.columns, columns=["max", "mode"])
        likely_power["mode"] = controlled[controlled > 0.2].mode().loc[0]
        likely_power["max"] = controlled[controlled > 0.2].max()
        self.available_yearly_power_values["meter"] = cm.loc[cm.index.repeat(self.n_different_powers)].reset_index(
            drop=True)
        self.available_yearly_power_values["id"] = cm.index.repeat(self.n_different_powers)
        self.available_yearly_power_values["original_likely_power"] = likely_power["max"].loc[
            likely_power.index.repeat(self.n_different_powers)].reset_index(drop=True)
        self.available_yearly_power_values["original_likely_power"] = self.available_yearly_power_values[
            "original_likely_power"].apply(
            lambda x: self.boiler_power[np.abs(self.boiler_power - x).argmin()])
        self.available_yearly_power_values["scale"] = list(chain.from_iterable(repeat(self.boiler_power, len(cm))))
        self.available_yearly_power_values["yearly_energy"] = controlled.sum().repeat(len(self.boiler_power)).values
        self.available_yearly_power_values["yearly_energy"] = self.available_yearly_power_values["yearly_energy"] * \
                                                              self.available_yearly_power_values["scale"] / \
                                                              self.available_yearly_power_values[
                                                                  "original_likely_power"]

        pv_id_max = self.added_pvs.index.astype(int).max() if self.added_pvs is not None else 0
        max_id = data.identifiers.index.astype(int).max() + pv_id_max + 1
        cl_free_households = data.households[data.households.e_yearly_controlled == 0].index
        self.added_cl = data.identifiers.loc[
            data.identifiers.MeterNo.isin(cl_free_households) & (data.identifiers.load_type == 2)].copy()
        self.added_cl.index = Index(list(range(max_id, max_id + len(cl_free_households)))).astype(self.id_type)
        self.added_cl["load_type"] = 3
        households_without_outliers = (data.households.e_yearly_residential < 6000) & (
                data.households.e_yearly_controlled > 700) & (
                                              data.households.e_yearly_controlled < 5000)
        self.cl_m, self.cl_y0 = np.polyfit(
            data.households.loc[households_without_outliers, "e_yearly_residential"],
            data.households.loc[households_without_outliers, "e_yearly_controlled"], 1)

    def modify_controlled(self, controlled, pv_power_addition, data):
        new_data = deepcopy(data)
        self.mod_controlled(controlled, new_data, pv_power_addition)
        return new_data

    def modify_pv(self, pv_power_addition, pv_mult, data):
        new_data = deepcopy(data)
        if pv_power_addition != "original":
            self.mod_production(new_data, pv_mult, pv_power_addition)
        return new_data

    # noinspection PyTupleAssignmentBalance
    def mod_controlled(self, controlled, data, pv_power_addition):
        n_controlled = (data.households.e_yearly_controlled > 0).sum()
        n_households = len(data.households)
        r_controlled = n_controlled / n_households

        if controlled == "original" or r_controlled > self.typical_controlled_penetration:
            return

        if self.added_cl is None:
            self.register_possible_controlled_power(data)

        if controlled in ("typical_least_pv", "typical_most_pv"):
            # self.remove_original_controlled(data)
            new_cl_count = int(n_households * self.typical_controlled_penetration) - n_controlled
            if new_cl_count <= 0:
                return
            sort_by = "e_yearly_residential" if pv_power_addition == "distribute" else "pv_power"
            new_cl_meters = data.households.loc[self.added_cl.MeterNo].sort_values(by=sort_by,
                                                                                   ascending=controlled ==
                                                                                             "typical_least_pv").index[
                            :new_cl_count]
        elif controlled == "all_households":
            new_cl_meters = self.added_cl.MeterNo
        else:
            raise ValueError(f"Unknown controlled scenario encountered: '{controlled}'")

        new_controlled_consumers = self.added_cl[self.added_cl.MeterNo.isin(new_cl_meters)]
        data.measurements.loc[:, new_controlled_consumers.index] = self.select_controlled_profiles(
            new_controlled_consumers.MeterNo, data).values
        data.identifiers = concat([data.identifiers, new_controlled_consumers])
        data.households.loc[new_controlled_consumers.MeterNo, "e_yearly_controlled"] = data.measurements.loc[:,
                                                                                       new_controlled_consumers.index].sum().values

    def select_controlled_profiles(self, new_cl_households, data):
        estimated_yearly_controlled_energy = data.households.loc[
                                                 new_cl_households, "e_yearly_residential"] * self.cl_m + self.cl_y0
        new_meters = estimated_yearly_controlled_energy.apply(
            lambda x: self.available_yearly_power_values.loc[
                (self.available_yearly_power_values.yearly_energy - x).abs().sort_values().index[0]])
        return data.measurements.loc[:, new_meters.id].mul(
            (new_meters.scale / new_meters.original_likely_power).values, axis="columns")

    def register_possible_new_pvs(self, data):
        self.universal_production = data.measurements.loc[:, data.get_pvs()].mean(axis="columns")
        self.universal_production /= self.universal_production.sum()

        controlled_id_max = self.added_cl.index.astype(int).max() if self.added_cl is not None else 0
        max_id = data.identifiers.index.max() + controlled_id_max + 1
        pv_free_households = data.households[data.households.pv_power == 0].index
        self.added_pvs = data.identifiers.loc[data.identifiers.MeterNo.isin(pv_free_households) &
                                              (data.identifiers.load_type == 2)].copy()
        self.added_pvs.index = Index(list(range(max_id, max_id + len(pv_free_households)))).astype(self.id_type)
        self.added_pvs["load_type"] = 4

    def mod_production(self, data, pv_mult, pv_power_addition):
        yearly_total = data.measurements.sum(axis=0)
        yearly_consumption = yearly_total.loc[data.get_consumption()].sum()
        yearly_production = yearly_total[data.get_pvs()].sum()
        if pv_power_addition == "original":
            return
        elif pv_power_addition == "increase":
            data.measurements.loc[:, data.get_pvs()] *= yearly_consumption / yearly_production * pv_mult
            data.households.pv_power *= yearly_consumption / yearly_production * pv_mult
        elif pv_power_addition == "distribute":
            if self.universal_production is None:
                self.register_possible_new_pvs(data)

            data.households.pv_power = (data.households.e_yearly_residential
                                        + data.households.e_yearly_controlled) * pv_mult
            data.identifiers = concat([data.identifiers, self.added_pvs])
            pv_id = Index.union(data.get_pvs(), self.added_pvs.index).astype(self.id_type)
            b = data.households.loc[data.identifiers.loc[pv_id, :].MeterNo].pv_power
            a = self.universal_production
            data.measurements.loc[:, pv_id] = np.tensordot(a.to_numpy(), b.to_numpy(), axes=0)
        else:
            raise ValueError(f"Unknown PV power addition encountered: '{pv_power_addition}'")

    def versions(self):
        for controlled in self.controlled_consumer_penetration_type:
            for pv_addition in self.pv_power_distribution_method:
                new_network_data = self.modify_controlled(controlled, pv_addition, self.network_data)
                pv_ratios = self.pv_power_ratio if pv_addition != "original" else [
                    (new_network_data.households.pv_power.sum() /
                     (new_network_data.households.e_yearly_residential + new_network_data.households.e_yearly_controlled).sum()), ]
                for pv_ratio in pv_ratios:
                    info = Series(
                        index=["pv_power_distribution_method", "pv_ratio", "controlled_positioning_method"],
                        data=(pv_addition, pv_ratio, controlled))
                    # create the modified data for this version
                    modified_data = self.modify_pv(pv_addition, float(pv_ratio), new_network_data)
                    # collect useful statistics
                    try:
                        n_households = len(modified_data.households)
                        n_controlled = (modified_data.households.e_yearly_controlled > 0).sum()
                        total_pv_power = float(modified_data.households.pv_power.sum()) if "pv_power" in modified_data.households.columns else np.nan
                        total_residential = float(modified_data.households.e_yearly_residential.sum())
                        total_controlled = float(modified_data.households.e_yearly_controlled.sum())
                        r_controlled = n_controlled / n_households if n_households else np.nan
                    except Exception:
                        # If modified_data does not have expected structure, store NaNs
                        n_households = n_controlled = 0
                        total_pv_power = total_residential = total_controlled = r_controlled = np.nan

                    self.collected_versions.append({
                        "pv_power_distribution_method": pv_addition,
                        "pv_ratio": float(pv_ratio),
                        "controlled_positioning_method": controlled,
                        "n_households": n_households,
                        "n_controlled": int(n_controlled),
                        "r_controlled": float(r_controlled),
                        "total_pv_power": float(total_pv_power),
                        "total_residential_energy": float(total_residential),
                        "total_controlled_energy": float(total_controlled),
                        "cl_m": float(self.cl_m),
                        "cl_y0": float(self.cl_y0),
                    })

                    yield info, modified_data

    def visualize_network_versions(self, show=True, savepath=None):
        """Visualize collected statistics for all generated network versions.
        Call this after iterating over versions()."""
        import matplotlib.pyplot as plt
        import pandas as pd

        if not self.collected_versions:
            print("No collected network version data to visualize.")
            return

        df = pd.DataFrame(self.collected_versions)

        # Basic plots: controlled ratio vs pv_ratio colored by pv distribution method
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        ax = axes[0, 0]
        for method, g in df.groupby("pv_power_distribution_method"):
            ax.scatter(g.pv_ratio, g.r_controlled, label=method)
        ax.set_xlabel("pv_ratio")
        ax.set_ylabel("controlled ratio")
        ax.legend()
        ax.set_title("Controlled ratio vs PV ratio")

        ax = axes[0, 1]
        for method, g in df.groupby("controlled_positioning_method"):
            ax.bar(method, g.n_controlled.mean())
        ax.set_ylabel("avg number controlled households")
        ax.set_title("Average # controlled by positioning method")

        ax = axes[1, 0]
        df.boxplot(column="total_pv_power", by="pv_power_distribution_method", ax=ax)
        ax.set_title("Total PV power by distribution method")
        ax.set_xlabel("")

        ax = axes[1, 1]
        df.plot(kind="scatter", x="total_residential_energy", y="total_controlled_energy", ax=ax)
        ax.set_title("Total controlled vs residential energy")

        plt.suptitle("Network versions summary")
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        if savepath:
            fig.savefig(savepath)
        if show:
            plt.show()
