from dataclasses import dataclass, asdict
from datetime import datetime
from os import makedirs
from os.path import join
from typing import Optional

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import rc
from numpy import sqrt
from pandas import DataFrame

from optimization_configuration.network.definitions import Network
from utility.configuration import config
from utility.definitions import OptimizationType, RunPhaseType, get_all_strategies, RunPhase
from visualization.definitions import optimization_type_label, run_phase_label
from visualization.visualize import display_figures

t0s = [0, 2184, 4368, 6552]
dt = 168
seasons = ['Winter', 'Spring', 'Summer', 'Autumn']
day_type = ["Weekday", "Weekend"]
year = config.getint("time", "simulation_year")
t0_days = {"Weekend": [datetime(year, 1, 20), datetime(year, 4, 21), datetime(year, 7, 21), datetime(year, 10, 20)],
           "Weekday": [datetime(year, 1, 21), datetime(year, 4, 23), datetime(year, 7, 22), datetime(year, 10, 21)]}

font_size = 15
font_scale = 2
rc('text', usetex=True)
rc('font', size=font_size, family='sans')
rc('legend', fontsize=16)

fig_width_pt = 1000
inches_per_pt = 1.0 / 72.27
golden_mean = (sqrt(5) - 1.0) / 2.0
fig_width = fig_width_pt * inches_per_pt
fig_height = fig_width * golden_mean
fig_size = [fig_width, fig_height]
plt.rcParams['figure.figsize'] = fig_size
matplotlib.use('Qt5Agg')

name = {Network.BARACS: "A", Network.GYOR: "B", Network.BALATONAKALI: "C", Network.BALATONSZEPEZD: "D"}


class OutputPlotter:
    naming_convention = {"pv": r"PV\ ratio", "pv_ratio": r"PV\ ratio", "bess_size": r"Battery\ size\ [kWh]",
                         "capex": r"CAPEX\ [Eur]", "opex": r"OPEX\ [Eur]", "network": r"Location\ code", "ssi": "SSI",
                         "sci": "SCI"}

    @dataclass
    class PlottingConfig:
        hue: Optional[str]
        size: Optional[str]
        style: Optional[str]
        x_axis: Optional[str]
        y_axis: Optional[str]

        def __post_init__(self):
            for k, i in asdict(self).items():
                if i in OutputPlotter.naming_convention:
                    i = OutputPlotter.naming_convention[i]
                self.__setattr__(k, i)

    def __init__(self, output_directory):
        self.fig = None
        self.output_dir = output_directory
        makedirs(output_directory, exist_ok=True)

    def plot_network(self, result, network, to_plot="ssi"):
        self.fig = plt.figure(figsize=(8, 10))
        # hue = None if to_plot in ("capex", "opex") else "bess_size"
        sns.barplot(result, x="pv_ratio", y=to_plot, hue="bess_size")
        plt.title(fr'$\mathrm{{Demo\ location\ {network.value}}}$' f"")
        plt.xlabel(r"$\mathrm{Sum\ PV\ production/Sum\ consumption}$")
        plt.ylabel(fr"$\mathrm{{{to_plot}}}$")
        self.save_nw(self.output_dir, network, to_plot)

    def save_nw(self, output_directory, nw, metric):
        self.fig.tight_layout()
        makedirs(join(output_directory, f"{nw.value}"), exist_ok=True)
        self.fig.savefig(join(output_directory, f"{nw.value}", f"result_{metric}.pdf"))
        plt.close(self.fig)

    def plot_separated_by_config_param(self, result, separate_by):
        plotting_config = {
            "pv": self.PlottingConfig("pv", "bess_size", "optimization", "ssi", "sci"),
            "bess_size": self.PlottingConfig("bess_size", "pv", "optimization", "ssi", "sci"),
            "pv_estimation": self.PlottingConfig("bess_size", "pv", "pv_estimation", "ssi", "sci")
        }

        x_lim = [0.1, 1.2]
        y_lim = [0.1, 1.2]
        x_ticks = [0.2, 0.4, 0.6, 0.8, 1]
        y_ticks = [0.2, 0.4, 0.6, 0.8, 1]
        conf = plotting_config[separate_by]
        self.fig, axes = plt.subplots(nrows=1, ncols=5, figsize=(fig_height * 2.5, fig_height // 2 + 1),
                                      gridspec_kw=dict(width_ratios=[0.225] * len(result.network.unique()) + [0.4]),
                                      sharey=True, sharex=True)
        result = result[::-1]

        def to_value(x):
            try:
                val = x.value
            except:
                val = x
            return val

        result = result.rename(columns=self.naming_convention).applymap(to_value)
        sns.set(font_scale=font_scale)
        for i, nw in enumerate(Network):
            ax = axes[i]
            filtered = result[result[r"Location\ code"] == nw.value]
            sns.set_palette("tab10")
            markers = {"optimized": 'o', "profile": 's'} if conf.style == "optimization" else {"measured": 'o',
                                                                                               'estimated': 'd',
                                                                                               'tmy': '^',
                                                                                               'clear_sky': 's'}
            sns.scatterplot(filtered, x=conf.x_axis, y=conf.y_axis, style=conf.style,
                            hue=conf.hue, size=conf.size, markers=markers, edgecolor="gray", alpha=0.7,
                            sizes=(10, 400), ax=ax, palette="muted", ec="face")
            if i == 0:
                ax.set_ylabel(fr"$\mathrm{{{conf.y_axis}}}$", fontsize=font_size + 2)
            else:
                ax.set_ylabel("")
            ax.set_xlabel(fr"$\mathrm{{{conf.x_axis}}}$", fontsize=font_size + 2)
            ax.set_xlim(x_lim)
            ax.set_ylim(y_lim)
            ax.legend().set_visible(False)
            ax.set_xticks(x_ticks)
            ax.set_xticklabels([rf"${i:.1f}$" for i in x_ticks], fontsize=font_size + 2, rotation=45)
            ax.set_yticks(y_ticks)
            ax.set_yticklabels([rf"${i:.1f}$" for i in y_ticks], fontsize=font_size + 2)

        handles, labels = axes[0].get_legend_handles_labels()
        for t in range(len(labels)):
            if "$" in labels[t]:
                continue
            text = labels[t].replace("_", r"\ ")
            labels[t] = fr'$\mathrm{{{text}}}$'
        ax = axes[-1]
        ax.axis("off")
        ax.legend(handles, labels, loc='upper left', frameon=False, fontsize=font_size + 2, ncols=2)

        self.fig.tight_layout()
        plt.subplots_adjust(top=0.94, bottom=0.17, left=0.045, right=1.0, hspace=0.2, wspace=0.14)
        self.fig.savefig(join(self.output_dir, f"ssi_sci_{separate_by}.pdf"), transparent=True)
        plt.close(self.fig)

    def plot_ssi_sci(self, result, generate="PV"):
        if type(generate) is not list:
            generate = [generate]

        if "PV" in generate:
            self.plot_separated_by_config_param(result, "pv")

        if "PV_EST" in generate:
            self.plot_separated_by_config_param(result, "pv_estimation")

        if "BESS" in generate:
            self.plot_separated_by_config_param(result, "bess_size")

    def plot_capex(self, result):
        def plot_fig(config):
            sns.set(font_scale=font_scale)
            self.fig = plt.figure(figsize=(12, 12), facecolor='w')
            sns.scatterplot(result, x="ssi", y="sci", hue=config.hue, size=config.size,
                            palette=sns.color_palette("tab10"), sizes=(200, 1000))
            plt.xlabel(fr"$\mathrm{config.x_axis}$")
            plt.ylabel(fr"$\mathrm{config.y_axis}$")
            self.fig.tight_layout()
            self.fig.savefig(join(self.output_dir, f"ssi_sci_{config.hue}.pdf"))
            plt.close(self.fig)

        result = result.rename(columns=self.naming_convention)
        plot_fig(self.PlottingConfig("network", "capex", None, "ssi", "sci"))
        plot_fig(self.PlottingConfig("network", "opex", None, "ssi", "sci"))

    def save(self, output_directory, metric):
        self.fig.tight_layout()
        self.fig.savefig(join(output_directory, f"full_result_{metric}.pdf"))
        plt.close(self.fig)


def show_optim(results, path, postfix):
    p_inj = results.get('p_inj')
    p_with = results.get('p_with')
    p_bess_in = results.get('p_bess_in')
    p_bess_out = results.get('p_bess_out')
    e_bess_stor = results.get('e_bess_stor')
    p_elh_in = results.get('p_elh_in')
    p_elh_out = results.get('p_elh_out')
    p_hss_in = results.get('p_hss_in')
    p_hss_out = results.get('p_hss_out')
    diff_hss_out = results.get('diff_hss_out', pd.Series(0, index=range(len(results))))
    diff_hss_in = results.get('diff_hss_in', pd.Series(0, index=range(len(results))))
    e_hss_stor = results.get('e_hss_stor', pd.Series(0, index=range(len(results))))
    p_shared = results.get('p_shared')
    p_cl_grid = results.get('p_cl_grid')
    p_cl_rec = results.get('p_cl_rec')
    p_cl_with = results.get('p_cl_with')
    d_cl = results.get('d_cl')
    p_grid_in = results.get('p_grid_in')
    p_grid_out = results.get('p_grid_out')
    p_pv = results.get('p_pv')
    p_ue = results.get('p_ue')
    p_ut = results.get('p_ut')

    if p_ut is None:
        if p_hss_out is not None:
            p_ut = p_hss_out
        elif p_elh_in is not None:
            p_ut = p_elh_in
    display_figures(p_pv, p_bess_out, p_with, p_ue, p_bess_in, p_inj, e_bess_stor, p_elh_out, p_ut, p_shared, p_cl_rec,
                    p_cl_grid, p_cl_with, e_hss_stor, p_hss_out, p_hss_in, diff_hss_out, diff_hss_in, d_cl, p_grid_in,
                    p_grid_out, path, postfix)


def plot_profile_and_optimized(p_ut_from_profile, p_ut, network, pv_ratio, bess, **kwargs):
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=fig_size, facecolor='w', sharey=True)
    for season, t0, i in zip(seasons, t0s, range(4)):
        ax = axes[i // 2, i % 2]
        ax.plot(p_ut_from_profile[t0:t0 + dt], label=r"$\mathrm{From\ profile}$")
        ax.plot(p_ut.iloc[t0:t0 + dt].values, label=r"$\mathrm{From\ optimized\ simulation}$")
        ax.set_xlabel(r"$\mathrm{Time\ step}$")
        ax.set_ylabel(r"$\mathrm{Consumption}$")
        ax.legend()
        ax.set_title(fr"$\mathrm{{{season}}}$")
    plt.tight_layout()
    plt.title(f"{network.value}, pv: {pv_ratio}, batt: {bess}")
    # plt.show()
    output_path = join(config.get("path", "figures"), "profiles")
    makedirs(output_path, exist_ok=True)
    fig.savefig(join(output_path, f"p_ut_profile_optimized_{network.value}_{pv_ratio}_{bess}.pdf"))
    plt.close(fig)


def plot_water_profiles(p_50_per, p_our_profile, nw):
    for _, dt in enumerate(day_type):
        fig, axes = plt.subplots(nrows=2, ncols=3, figsize=fig_size, facecolor='w', sharey=True,
                                 gridspec_kw=dict(width_ratios=[0.45, 0.45, 0.1]))
        for i, season in enumerate(seasons):
            ax = axes[i // 2, i % 2]
            time = pd.date_range(t0_days[dt][i], t0_days[dt][i] + pd.DateOffset(hours=23), freq='H')
            sns.lineplot(pd.concat([p_50_per[time], p_our_profile[time]], axis="columns"), ax=ax)
            ax.set_xticklabels(time.time, rotation=45, fontsize=font_size - 4)
            myFmt = mdates.DateFormatter('%H:%M')
            ax.xaxis.set_major_formatter(myFmt)
            ax.set_ylabel(r"$\mathrm{Water\ usage\ [l]}$", fontsize=font_size)
            ax.set_title(fr"$\mathrm{{{season}}}$", fontsize=font_size - 2)
            ax.legend().remove()

        # Legend
        ax = axes[0, 2]
        handles, labels = axes[0, 0].get_legend_handles_labels()
        ax.legend(handles, [r"$\mathrm{50P\ profile}$", r"$\mathrm{Aggregate\ profile}$"], fontsize=font_size,
                  loc='upper left')
        ax.axis('off')
        axes[1, 2].axis("off")
        # plt.title(rf"$\mathrm{{{dt}}}$", loc="center")

        plt.tight_layout()
        # plt.show()
        output_path = join(config.get("path", "figures"), "profiles")
        makedirs(output_path, exist_ok=True)
        fig.savefig(join(output_path, f"water_profiles_{dt}_{nw.value}.pdf"))
        plt.close(fig)


def plot_rand_water_profiles(profiles, to_plot, nw, line_types):
    font_size = 20
    for dt in day_type:
        fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(fig_width, fig_height), facecolor='w', sharey=True,
                                 gridspec_kw=dict(width_ratios=[0.4, 0.4, 0.2]))

        axt = None
        for i, season in enumerate(seasons):
            ax = axes[i // 2, i % 2]
            time = pd.date_range(t0_days[dt][i], t0_days[dt][i] + pd.DateOffset(hours=23), freq='h')
            df = profiles.loc[time, to_plot]
            total = DataFrame(df.sum(axis="columns"), columns=["Total"], index=df.index)
            df["time"] = df.index
            total["time"] = total.index
            df = df.melt(id_vars="time", value_vars=df.columns[df.columns != "time"], value_name="value")
            df.loc[:, "Profile type"] = [line_types[c] for c in df.variable]

            ax2 = ax.twinx()
            if i == 0:
                axt = ax2
            else:
                axt.get_shared_y_axes().join(axt, ax2)

            sns.lineplot(df, x="time", y="value", hue="variable", style="Profile type", ax=ax)
            sns.lineplot(data=total, x="time", y="Total", ax=ax2, color="darkgrey", label="Total")
            ax.set_ylabel(r"$\mathrm{Water\ usage\ [l]}$", fontsize=font_size)
            ax.set_xlabel("")
            if i in (1, 3):
                ax2.set_ylabel(r"$\mathrm{Total\ [l]}$", fontsize=font_size)
            else:
                ax2.set_yticks(ax2.get_yticks())
                ax2.set_yticklabels([""] * len(ax2.get_yticks()))
                ax2.set_ylabel("")
            ax2.yaxis.label.set_color('darkgrey')
            ax2.spines['right'].set_color('darkgrey')
            ax2.tick_params(axis='y', colors='darkgrey')

            ax.set_xticks(time[0:-1:4])
            ax.set_xticklabels(time.time[0:-1:4].astype("str"), rotation=45, fontsize=font_size)
            myFmt = mdates.DateFormatter('%H:%M')
            ax.xaxis.set_major_formatter(myFmt)
            ax.set_title(fr"$\mathrm{{{season}}}$", fontsize=font_size + 2)
            if i == 0:
                handles, labels = ax.get_legend_handles_labels()
                handles_twin, labels_twin = ax2.get_legend_handles_labels()
                handles = handles + handles_twin
                labels = labels + labels_twin
            ax.legend().remove()
            ax2.legend().remove()

        # Legend
        ax = axes[0, 2]
        ax.legend(handles[7:], labels[7:], fontsize=font_size + 2, loc='upper left')
        ax.axis('off')
        axes[1, 2].axis("off")

        # plt.title(rf"$\mathrm{{{dt}}}$")
        plt.tight_layout()
        # plt.subplots_adjust(top=0.941, bottom=0.096, left=0.064, right=1.0, hspace=0.35, wspace=0.18)
        plt.subplots_adjust(top=0.941, bottom=0.096, left=0.064, right=0.96, hspace=0.35, wspace=0.165)
        # plt.show()
        output_path = join(config.get("path", "output"), "figures", "profiles")
        makedirs(output_path, exist_ok=True)
        fig.savefig(join(output_path, f"individual_water_profiles_{dt}_{nw.value}.pdf"), transparent=True)
        plt.close(fig)


def plot_metric(data, metric, title="", inner_dir=""):
    fig, axes = plt.subplots(nrows=4, ncols=3, figsize=(fig_height - 0.9, fig_width), facecolor='w',
                             gridspec_kw=dict(width_ratios=[0.45, 0.45, 0.1]))
    names = ["A", "B", "C", "D"]
    for i, (nw, n) in enumerate(zip(Network, names)):
        vmin = data.loc[data.network == nw.value, metric].min()
        vmax = data.loc[data.network == nw.value, metric].max()

        for j, (optim, name) in enumerate(zip(("profile", "optimized"), (
                rf"1.)\ {optimization_type_label[OptimizationType.PROFILE]}",
                rf"2.)\ {optimization_type_label[OptimizationType.OPTIMAL_CONTROL]}"))):
            ax = axes[i, j]
            df = data[(data.network == nw.value) & (data.optimization == optim)].pivot(columns="bess_size",
                                                                                       index="pv_ratio",
                                                                                       values=metric)

            cbar = j == 1
            axcb = axes[i, 2] if j == 1 else None
            sns.heatmap(df, ax=ax, vmin=vmin, vmax=vmax, cmap="Spectral", cbar=cbar, cbar_ax=axcb, square=True,
                        cbar_kws={"label": rf"$\mathrm{{Network\ {n}}}$", "shrink": 0.5, "pad": 0.01})

            if j == 0:
                ax.set_ylabel("$\mathrm{PV\ ratio}$")
                ax.set_yticks(ax.get_yticks())
                ax.set_yticklabels(ax.get_yticklabels(), rotation=45)
            else:
                ax.set_ylabel("")
                ax.set_yticks([])
                ax.set_yticklabels([])

            if i == 3:
                ax.set_xlabel("$\mathrm{Bess\ size\ [kWh]}$")
                ax.set_xticks(ax.get_xticks())
                ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
            else:
                ax.set_xlabel("")
                ax.set_xticks([])
                ax.set_xticklabels([])

            if i == 0:
                ax.set_title(rf"$\mathrm{{{name}}}$", fontsize=font_size)
                axes[0, 2].set_title(title, fontsize=font_size - 2)

    plt.tight_layout()
    plt.subplots_adjust(top=0.966, bottom=0.067, left=0.124, right=0.893, hspace=0.076, wspace=0.319)
    plt.tight_layout()
    # plt.show()
    output_path = config.get("path", "figures")
    makedirs(join(output_path, inner_dir), exist_ok=True)
    fig.savefig(join(output_path, inner_dir, f"{metric}.pdf"), transparent=True)
    plt.close(fig)


def select_from_df(df, network, metric):
    df = df[df.network == network.value]
    vmin = df[metric].min()
    vmax = df[metric].max()
    return df, vmin, vmax


def plot_metric_compare(df, metric, network, inner_dir=""):
    nrows = len(get_all_strategies())
    ncols = len(OptimizationType) + 1
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_height, fig_width), facecolor='w',
                             gridspec_kw=dict(width_ratios=[0.45, 0.45, 0.1]))

    df, vmin, vmax = select_from_df(df, network, metric)
    for i, phase in enumerate(RunPhaseType):
        for s, strategy in enumerate(get_all_strategies(RunPhase, phase)):
            for j, optim in enumerate(OptimizationType, 1):
                ax = axes[i + s, j - 1]
                dft = df[(df.optimization == optim.value) & (df.strategy == strategy.name) & (
                        df.phase == phase.value)].pivot(
                    columns="bess_size", index="pv_ratio", values=metric)

                cbar = j == 1
                axcb = axes[0, 2] if j == 1 else None
                sns.heatmap(dft, ax=ax, vmin=vmin, vmax=vmax, cmap="Spectral", cbar=cbar, cbar_ax=axcb, square=True,
                            cbar_kws={"shrink": 0.5, "pad": 0.01})

                bx = ax.twinx()
                bx.set_ylabel(r"$\mathrm{PV\ ratio}$" if j == ncols - 1 else "")
                bx.set_yticks(ax.get_yticks())
                bx.set_yticklabels(ax.get_yticklabels(), rotation=45)
                ax.set_yticks([])
                ax.set_yticklabels([])

                if j == 1:
                    strategy_label = fr"$\mathrm{{{run_phase_label[strategy]}}}$" if run_phase_label[
                                                                                         strategy] != "" else ""
                    ax.set_ylabel(fr"$\mathrm{{{run_phase_label[phase]}}}$"
                                  "\n"
                                  fr"{strategy_label}",
                                  fontsize=font_size + 2)
                else:
                    ax.set_ylabel("")

                if i + s == nrows - 1:
                    ax.set_xlabel(r"$\mathrm{Bess\ size\ [kWh]}$")
                else:
                    ax.set_xlabel("")

                ax.set_xticks(ax.get_xticks())
                ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

                if i + s == 0:
                    optim_label = fr"{j}.)\ {optimization_type_label[optim]}"
                    ax.set_title(rf"$\mathrm{{{optim_label}}}$", fontsize=font_size)

    colorbar_title = rf"$\mathrm{{{metric}}}$" if '_' not in metric else \
        rf"$\mathrm{{{metric.split('_')[0]}_{{{metric.split('_')[1]}}}}}$"
    axes[0, 2].set_title(colorbar_title, fontsize=font_size - 2)

    for i in range(1, nrows):
        axes[i, 2].axis("off")

    plt.tight_layout()
    # plt.subplots_adjust(top=0.951, bottom=0.067, left=0.065, right=0.905, hspace=0.303, wspace=0.516)
    # plt.show()
    output_path = join(config.get("path", "output"), "figures")
    makedirs(join(output_path, inner_dir), exist_ok=True)
    fig.savefig(join(output_path, inner_dir, f"comparison_{metric}_{network.value}.pdf"), transparent=True)
    plt.close(fig)


def plot_metric_network(data, metric, network, title="", inner_dir=""):
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(fig_height - 0.9, fig_width // 3), facecolor='w',
                             gridspec_kw=dict(width_ratios=[0.45, 0.45, 0.1]))

    data = data[data.network == network.value]
    vmin = data[metric].min()
    vmax = data[metric].max()

    for j, (optim, name) in enumerate(zip(("profile", "optimized"), (
            f"1.)\ {optimization_type_label[OptimizationType.PROFILE]}",
            f"2.)\ {optimization_type_label[OptimizationType.OPTIMAL_CONTROL]}"))):
        ax = axes[j]
        df = data[(data.optimization == optim)].pivot(columns="bess_size",
                                                      index="pv_ratio",
                                                      values=metric)

        cbar = j == 1
        axcb = axes[2] if j == 1 else None
        sns.heatmap(df, ax=ax, vmin=vmin, vmax=vmax, cmap="Spectral", cbar=cbar, cbar_ax=axcb, square=True,
                    cbar_kws={"shrink": 0.5, "pad": 0.01})

        if j == 0:
            ax.set_ylabel(r"$\mathrm{PV\ ratio}$")
            ax.set_yticks(ax.get_yticks())
            ax.set_yticklabels(ax.get_yticklabels(), rotation=45)
        else:
            ax.set_ylabel("")
            ax.set_yticks([])
            ax.set_yticklabels([])

        ax.set_xlabel(r"$\mathrm{Bess\ size\ [kWh]}$")
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

        ax.set_title(rf"$\mathrm{{{name}}}$", fontsize=font_size)
        axes[2].set_title(title, fontsize=font_size - 2)

    plt.tight_layout()
    plt.subplots_adjust(left=0.114, right=0.949)
    output_path = config.get("path", "figures")
    makedirs(join(output_path, inner_dir), exist_ok=True)
    fig.savefig(join(output_path, inner_dir, f"{metric}_{network.value}.pdf"), transparent=True)
    plt.close(fig)
