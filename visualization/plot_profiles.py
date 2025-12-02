from datetime import datetime
from os.path import join

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from numpy import sqrt
from pandas import to_datetime, date_range, DateOffset, DataFrame, read_csv, concat

from utility.configuration import config, read_slp
from post_evaluation.result_reader import ResultReader
from utility.definitions import AGG, OptimizationType
from optimization_configuration.network.definitions import Network

font_size = 20
font_scale = 2
matplotlib.rc('text', usetex=True)
matplotlib.rc('font', size=font_size, family='sans-serif')
plt.rcParams.update({'axes.facecolor': "#f4f4f4"})
plt.rcParams.update({'figure.facecolor': "#f4f4f4"})
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = 'cm'
matplotlib.rc('legend', fontsize=16)
# matplotlib.rcParams['mathtext.fontset'] = 'custom'
# matplotlib.rcParams['mathtext.rm'] = 'Bitstream Vera Sans'
# matplotlib.rcParams['mathtext.it'] = 'Bitstream Vera Sans:italic'
# matplotlib.rcParams['mathtext.bf'] = 'Bitstream Vera Sans:bold'
# matplotlib.rcParams['mathtext.fontset'] = 'stix'
# matplotlib.rcParams['font.family'] = 'STIXGeneral'
output_directory = config.get("path", "input")

fig_width_pt = 500
inches_per_pt = 1.0 / 72.27
golden_mean = (sqrt(5) - 1.0) / 2.0
fig_width = fig_width_pt * inches_per_pt
fig_height = fig_width * golden_mean
fig_size = [fig_width, fig_height]
plt.rcParams['figure.figsize'] = fig_size

profiles = read_slp()


def plot_control_signal():
    control_signal = [1] * 5 + [0] * 7 + [1] * 2 + [0] * 6 + [1] * 4
    day = datetime(2019, 7, 19)
    dates = date_range(day, day + DateOffset(hours=23), freq='H')
    control_signal = DataFrame(control_signal, index=dates, columns=["Control signal"])

    matplotlib.use("Qt5Agg")
    fig, ax = plt.subplots()
    ax.plot(control_signal, "o-", color="darkgrey")
    # ax.plot(cont, "o-", color="blue")
    myFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["OFF", "ON"])
    plt.tight_layout()
    plt.subplots_adjust(top=0.93, bottom=0.229, left=0.074, right=0.959, hspace=0.2, wspace=0.2)
    plt.show()
    fig.savefig(join(config.get("path", "figures"), "control_signal.pdf"))
    plt.close()


def plot_profiles(day=datetime(2019, 7, 19), nw=Network.BARACS):
    fontsize = 20
    individual_profiles = read_csv(join(output_directory, f"{nw.value}", "profiles.csv"), header=0, index_col=0)
    individual_profiles.loc[:, "Hot water profile"] = individual_profiles.sum(axis="columns")
    individual_profiles.index = to_datetime(individual_profiles.index)

    dates = date_range(day, day + DateOffset(hours=23), freq='H')
    cont = profiles.loc[dates, ["Vezérelt", "Lakosság vidék", "PV"]]
    ind = individual_profiles.loc[dates, ["Hot water profile"]]
    cont = concat([cont, ind], axis="columns")
    cont /= cont.max()
    fig, ax = plt.subplots()
    colors = ("#7A0017", "grey", "green", "blue")
    markers = ("--", "-", ":", "-.")
    labels = ("$\mathrm{Controlled}$", "$\mathrm{Residential}$", "$\mathrm{PV}$", "$\mathrm{Hot\ water}$")
    for c, color, m, l in zip(cont.columns, colors, markers, labels):
        ax.plot(cont[c], m, color=color, label=l, linewidth=3)

    myFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, fontsize=fontsize)
    ax.legend(loc="upper left", fontsize=fontsize + 2)
    plt.tight_layout()
    plt.subplots_adjust(top=0.95, bottom=0.164, left=0.058, right=0.959, hspace=0.2, wspace=0.2)
    plt.show()
    fig.savefig(join(config.get("path", "output"), "profiles.pdf"))
    plt.close()


def plot_hot_water_and_controlled_together(day=datetime(2019, 1, 12), nw=Network.BARACS, bess_size=200, pv=1):
    fontsize = 24
    input_dir = join(config.get("path", "output"), "aggregated", "optimized", f"{nw.value}", f"{pv}",
                     f"{bess_size}")
    result_reader = ResultReader(input_dir)
    df = DataFrame()
    ut_input_optimized = result_reader.read(bess_size, pv, AGG, OptimizationType.OPTIMAL_CONTROL)[
        ["p_elh_in", "p_ut"]]
    ut_input_optimized.index = date_range(start=datetime(2019, 1, 1), end=datetime(2020, 1, 1), freq="H")[:-1]

    ut_input_profile = result_reader.read(bess_size, pv, AGG, OptimizationType.OPTIMAL_CONTROL)[["p_cl_with"]]
    ut_input_profile = ut_input_profile.rename(columns={"p_cl_with": "p_elh_profile"})
    ut_input_profile.index = to_datetime(
        date_range(start=datetime(2019, 1, 1), end=datetime(2020, 1, 1), freq="H")[:-1])

    ut_ptofile = concat([ut_input_optimized, ut_input_profile], axis="columns")
    dates = date_range(day, day + DateOffset(hours=23), freq='H')
    ut_ptofile = ut_ptofile.loc[dates, :]

    fig, ax = plt.subplots(figsize=(13, 8))
    cols = ["p_elh_in", "p_elh_profile", "p_ut"]
    colors = ("grey", "green", "blue")
    markers = ("--", "-", ":")
    labels = ("$\mathrm{Heater\ clustering\--2.)\ {optimization_type_label[OptimizationType.OPTIMAL_CONTROL]}}$", "$\mathrm{Heater\ clustering-1.)\ Profile}$",
              "$\mathrm{Hot\ water\ usage}$")

    for c, color, m, l in zip(cols, colors, markers, labels):
        ax.plot(ut_ptofile[c], m, color=color, label=l, linewidth=4)

    myFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_ylabel("$\mathrm{Energy\ consumed\ (kWh)}$", fontsize=fontsize)
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, fontsize=fontsize)
    ax.legend(loc="upper left", fontsize=fontsize + 2)
    plt.tight_layout()
    plt.subplots_adjust(top=0.955, bottom=0.139, left=0.067, right=0.964, hspace=0.2, wspace=0.2)
    # plt.show()
    fig.savefig(join(config.get("path", "output"), f"ut_profiles_{nw.value}_{day:%Y-%m-%d}.pdf"))
    plt.close()


def plot_very_small_profile(kind="Lakosság vidék", suffix=None):
    fig, ax = plt.subplots(figsize=(2, 1))
    ax.plot(profiles[kind].iloc[0:96].values, color="grey")

    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.set_yticks([])
    ax.set_yticklabels([])
    plt.tight_layout()
    ax.spines['top'].set_color('none')
    ax.spines['bottom'].set_color('none')
    ax.spines['left'].set_color('none')
    ax.spines['right'].set_color('none')
    plt.show()
    fig.savefig(join(config.get("path", "output"), f"small_profile_{suffix}.pdf"), transparent=True)
    plt.close()


# plot_very_small_profile("PV", "pv")

# plot_hot_water_and_controlled_together()

# plot_profiles()

for nw in Network:
    for day in (datetime(2019, 1, 15), datetime(2019, 7, 15)):
        plot_hot_water_and_controlled_together(day=day, nw=nw)
