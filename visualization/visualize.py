from os import makedirs
from os.path import join

import numpy as np
from matplotlib import patheffects as pe, pyplot as plt

from utility.definitions import OptimizationType
from visualization.definitions import optimization_type_label

experiment = "controlled"


def display_figures(p_pv, p_bess_out, p_with, p_ue, p_bess_in, p_inj, e_bess_stor, p_elh_out,
                    p_ut, p_shared, p_cl_rec, p_cl_grid, p_cl_with, e_hss_stor, p_hss_out, p_hss_in, diff_hss_out,
                    diff_hss_in, d_cl, p_grid_in, p_grid_out, path, postfix=""):
    # %% Print for graphical check
    # One week in each season
    figsize = (20, 15)
    fontsize = 15
    t0s = [0, 2184, 4368, 6552]
    dt = 168
    titles = ['Winter', 'Spring', 'Summer', 'Autumn']
    path_effect = lambda lw: [pe.Stroke(linewidth=1.5 * lw, foreground='w'), pe.Normal()]
    bar_kw = dict(width=0.8, )
    plot_kw = dict(lw=3, path_effects=path_effect(3))
    area_kw = dict(alpha=0.6)
    for i, t0 in enumerate(t0s):
        # Useful time variables
        tf = t0 + dt
        time = np.arange(t0, tf)

        # Make figure
        fig, axes = plt.subplots(nrows=3, ncols=2, figsize=figsize, sharex=True,
                                 gridspec_kw=dict(width_ratios=[0.8, 0.2]))

        # Electric node of the condominium
        ax = axes[0, 0]

        # Plot "positive" half
        bottom = np.zeros_like(time, dtype=float)
        ax.bar(time, p_pv[t0:tf], bottom=bottom, label='$P_\mathrm{pv}$', **bar_kw)
        bottom += p_pv[t0:tf]
        ax.bar(time, p_bess_out[t0:tf], bottom=bottom, label='$P_\mathrm{bess,out}$', **bar_kw)
        bottom += p_bess_out[t0:tf]
        ax.bar(time, p_grid_out[t0:tf], bottom=bottom, label='$P_\mathrm{grid,out}$', **bar_kw)

        # Plot "negative" half
        bottom = np.zeros_like(time, dtype=float)
        ax.bar(time, -p_ue[t0:tf], bottom=bottom, label='$P_\mathrm{ue}$', **bar_kw)
        bottom -= p_ue[t0:tf]
        ax.bar(time, -p_bess_in[t0:tf], bottom=bottom, label='$P_\mathrm{bess,in}$', **bar_kw)
        bottom -= p_bess_in[t0:tf]
        ax.bar(time, -p_cl_grid[t0:tf], bottom=bottom, label='$P_\mathrm{cl,grid}$', **bar_kw)
        bottom -= p_cl_grid[t0:tf]
        ax.bar(time, -p_cl_rec[t0:tf], bottom=bottom, label='$P_\mathrm{cl,rec}$', **bar_kw)
        bottom -= p_cl_rec[t0:tf]
        ax.bar(time, -p_grid_in[t0:tf], bottom=bottom, label='$P_\mathrm{grid,in}$', **bar_kw)

        # Plot storage SOC
        axtw = ax.twinx()
        axtw.plot(time, e_bess_stor[t0:tf], color='lightgrey', ls='--')

        # Adjust and show
        ax.set_xlabel("Time (h)", fontsize=fontsize)
        ax.set_ylabel("Power (kW)", fontsize=fontsize)
        ax.set_title("Electric hub", fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax.grid()

        axtw.set_ylabel("Stored energy (kWh)")
        axtw.spines['right'].set_color('lightgrey')
        axtw.tick_params(axis='y', colors='lightgrey')
        axtw.yaxis.label.set_color('lightgrey')

        # Legend
        handles, labels = ax.get_legend_handles_labels()
        axes[0, 1].legend(handles, labels, fontsize=fontsize, loc='center')
        axes[0, 1].axis('off')

        # Thermal node
        ax = axes[1, 0]

        # # Plot "positive" half
        bottom = np.zeros_like(time, dtype=float)
        if p_elh_out is not None:
            ax.bar(time, p_elh_out[t0:tf], bottom=bottom, label='$P_\mathrm{elh,out}$', **bar_kw)
            bottom += p_elh_out[t0:tf]
        ax.bar(time, p_hss_out[t0:tf], bottom=bottom, label='$P_\mathrm{hss,out}$', **bar_kw)
        bottom += p_hss_out[t0:tf]
        if diff_hss_out is not None:
            ax.bar(time, diff_hss_out[t0:tf], bottom=bottom, label='$\Delta P_\mathrm{hss,out}$', color="cyan", **bar_kw)
            bottom += diff_hss_out[t0:tf]

        # # Plot "negative" half
        bottom = np.zeros_like(time, dtype=float)
        ax.bar(time, -p_hss_in[t0:tf], bottom=bottom, label='$P_\mathrm{hss,in}$', **bar_kw)
        bottom -= p_hss_in[t0:tf]
        ax.bar(time, -p_ut[t0:tf], bottom=bottom, label='$P_\mathrm{ut}$', **bar_kw)
        bottom -= p_ut[t0:tf]
        ax.bar(time, diff_hss_in[t0:tf], bottom=bottom, label='$\Delta P_\mathrm{hss,in}$', **bar_kw)
        bottom += diff_hss_in[t0:tf]

        # # Plot storage SOC
        axtw = ax.twinx()
        axtw.plot(time, e_hss_stor[t0:tf], color='black', ls='--', label="$\mathrm{E_{hss,stor}}$")

        # # Plot storage SOC
        axtd = ax.twinx()
        axtd.plot(time, d_cl[t0:tf], '.', ls='-', color='lightgrey', label="$\mathrm{control\ signal\ (on/off)}$")

        # # Adjust and show
        ax.set_xlabel("Time (h)", fontsize=fontsize)
        ax.set_ylabel("Power (kW)", fontsize=fontsize)
        ax.set_title("Thermal node", fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax.grid()

        axtw.set_ylabel("Stored energy (kWh)")
        axtw.spines['right'].set_color('black')
        axtw.tick_params(axis='y', colors='black')
        axtw.yaxis.label.set_color('black')
        axtw.legend().set_visible(False)

        axtd.spines["top"].set_visible(False)
        axtd.spines["right"].set_visible(False)
        axtd.spines["left"].set_visible(False)
        axtd.spines["bottom"].set_visible(False)
        axtd.tick_params(axis="both", which='both', length=0, labelcolor="none")
        axtd.legend().set_visible(False)

        # # Legend
        handles, labels = ax.get_legend_handles_labels()
        axtd_handles, axtd_labels = axtd.get_legend_handles_labels()
        axtw_handles, axtw_labels = axtw.get_legend_handles_labels()
        axes[1, 1].legend(handles + axtd_handles + axtw_handles, labels + axtd_labels + axtw_labels, fontsize=fontsize,
                          loc='center')
        axes[1, 1].axis('off')

        # CSC
        ax = axes[2, 0]

        # Interpolate for graphical purposes
        t_plot = np.linspace(t0, tf, 1000)
        f_plot = lambda x: np.interp(t_plot, time, x)
        p_inj_plot = f_plot(p_inj[t0:tf])
        p_with_plot = f_plot(p_with[t0:tf])
        p_shared_plot = np.minimum(p_inj_plot, p_with_plot)

        # Plot
        ax.plot(time, p_inj[t0:tf], label='$P_\mathrm{inj}$', color='tab:red', **plot_kw)
        ax.plot(time, p_with[t0:tf], label='$P_\mathrm{with}$', color='tab:blue', **plot_kw)
        ax.plot(time, p_shared[t0:tf], label='$P_\mathrm{shared}$', color='tab:green', ls='', marker='s', **plot_kw)
        ax.fill_between(t_plot, p_shared_plot, p_with_plot, where=p_with_plot > p_shared_plot,
                        label='E$_\mathrm{\\leftarrow grid}$', color='tab:blue', **area_kw)
        ax.fill_between(t_plot, p_shared_plot, p_inj_plot, where=p_inj_plot > p_shared_plot,
                        label='E$_\mathrm{\\rightarrow grid}$', color='tab:red', **area_kw)
        ax.fill_between(t_plot, 0, p_shared_plot, where=p_shared_plot > 0, label='E$_\mathrm{shared}$',
                        color='tab:green')

        # Adjust and show
        ax.set_xlabel("Time (h)", fontsize=fontsize)
        ax.set_ylabel("Power (kW)", fontsize=fontsize)
        ax.set_title("CSC", fontsize=fontsize)
        ax.tick_params(labelsize=fontsize)
        ax.grid()

        # Legend
        handles, labels = ax.get_legend_handles_labels()
        axes[2, 1].legend(handles, labels, fontsize=fontsize, loc='center')
        axes[2, 1].axis('off')

        # Adjust and show
        plt.subplots_adjust(top=0.55)  # Adjust the position of the overall title
        fig.suptitle(titles[i], fontsize=fontsize)
        fig.tight_layout()
        plt.savefig(join(path, f"{titles[i]}_{experiment}{postfix}.png"))
        plt.close()
        # plt.show()


def side_by_side_comp(results_optimized, results_profile, path, suffix):
    # %% Print for graphical check
    # One week in each season
    figsize = (20, 15)
    fontsize = 25
    t0s = [72, 2256, 4440, 6624]
    dt = 48
    titles = ['Winter', 'Spring', 'Summer', 'Autumn']
    path_effect = lambda lw: [pe.Stroke(linewidth=1.5 * lw, foreground='w'), pe.Normal()]
    bar_kw = dict(width=0.8, )
    plot_kw = dict(lw=3, path_effects=path_effect(3))
    area_kw = dict(alpha=0.6)
    for j, t0 in enumerate(t0s):
        # Useful time variables
        tf = t0 + dt
        time = np.arange(t0, tf)

        # Make figure
        fig, axes = plt.subplots(nrows=2, ncols=3, figsize=figsize, sharex=True,
                                 gridspec_kw=dict(width_ratios=[0.45, 0.45, 0.1]))

        axes[0, 0].get_shared_y_axes().join(axes[0, 0], axes[0, 1])
        axes[1, 0].get_shared_y_axes().join(axes[1, 0], axes[1, 1])
        # Electric node
        for i, (opt, results) in enumerate(zip(("profile", "optimized"), (results_profile, results_optimized))):
            ax = axes[0, i]

            # Plot "positive" half
            bottom = np.zeros_like(time, dtype=float)
            ax.bar(time, results["p_pv"][t0:tf], bottom=bottom, label='$P_\mathrm{pv}$', **bar_kw)
            bottom += results["p_pv"][t0:tf]
            ax.bar(time, results["p_bess_out"][t0:tf], bottom=bottom, label='$P_\mathrm{bess,out}$', **bar_kw)
            bottom += results["p_bess_out"][t0:tf]
            ax.bar(time, results["p_grid_out"][t0:tf], bottom=bottom, label='$P_\mathrm{grid,out}$', **bar_kw)

            # Plot "negative" half
            bottom = np.zeros_like(time, dtype=float)
            ax.bar(time, -results["p_ue"][t0:tf], bottom=bottom, label='$P_\mathrm{ue}$', **bar_kw)
            bottom -= results["p_ue"][t0:tf]
            ax.bar(time, -results["p_bess_in"][t0:tf], bottom=bottom, label='$P_\mathrm{bess,in}$', **bar_kw)
            bottom -= results["p_bess_in"][t0:tf]
            ax.bar(time, -results["p_cl_grid"][t0:tf], bottom=bottom, label='$P_\mathrm{cl,grid}$', **bar_kw)
            bottom -= results["p_cl_grid"][t0:tf]
            ax.bar(time, -results["p_cl_rec"][t0:tf], bottom=bottom, label='$P_\mathrm{cl,rec}$', **bar_kw)
            bottom -= results["p_cl_rec"][t0:tf]
            ax.bar(time, -results["p_grid_in"][t0:tf], bottom=bottom, label='$P_\mathrm{grid,in}$', **bar_kw)

            # Plot storage SOC
            axtw = ax.twinx()
            axtw.plot(time, results["e_bess_stor"][t0:tf], color='darkgrey', ls='--')

            # Adjust and show
            # ax.set_xlabel("Time (h)", fontsize=fontsize)
            ax.set_ylabel("Power (kW)" if i == 0 else "", fontsize=fontsize)
            if i == 1:
                ax.set_title(f"2.) {optimization_type_label[OptimizationType.OPTIMAL_CONTROL]}", fontsize=fontsize + 4)
            else:
                ax.set_title(f"1.) {optimization_type_label[OptimizationType.PROFILE]}", fontsize=fontsize + 4)

            ax.tick_params(labelsize=fontsize)
            ax.grid()

            axtw.set_ylabel("Stored energy (kWh)")
            axtw.spines['right'].set_color('darkgrey')
            axtw.tick_params(axis='y', colors='darkgrey')
            axtw.yaxis.label.set_color('darkgrey')

            # Legend
            if i == 0:
                handles, labels = ax.get_legend_handles_labels()
                axes[0, 2].legend(handles, labels, fontsize=fontsize, loc='center')
                axes[0, 2].axis('off')

            # Thermal node
            ax = axes[1, i]

            # # Plot "positive" half
            bottom = np.zeros_like(time, dtype=float)
            if i == 1 or "p_elh_out" in results:
                ax.bar(time, results["p_elh_out"][t0:tf], bottom=bottom, label='$P_\mathrm{elh,out}$', **bar_kw)
                bottom += results["p_elh_out"][t0:tf]
            else:
                col = "p_elh_in" if "p_elh_in" in results else "p_ut"
                ax.bar(time, results[col][t0:tf], bottom=bottom, label='$P_\mathrm{elh,out}$', **bar_kw)
                bottom += results[col][t0:tf]

            ax.bar(time, results["p_hss_out"][t0:tf], bottom=bottom, label='$P_\mathrm{hss,out}$', **bar_kw)
            bottom += results["p_hss_out"][t0:tf]

            if "diff_hss_out" in results:
                ax.bar(time, results["diff_hss_out"][t0:tf], bottom=bottom, label='$\Delta P_\mathrm{hss,out}$',
                       color="cyan", **bar_kw)
                bottom += results["diff_hss_out"][t0:tf]

            # # Plot "negative" half
            bottom = np.zeros_like(time, dtype=float)

            if "p_hss_in" in results and not all(results["p_hss_in"] == 0):
                ax.bar(time, -results["p_hss_in"][t0:tf], bottom=bottom, label='$P_\mathrm{hss,in}$', **bar_kw)
                bottom -= results["p_hss_in"][t0:tf]
                ax.bar(time, -results["p_ut"][t0:tf], bottom=bottom, label='$P_\mathrm{ut}$', **bar_kw)
                bottom -= results["p_ut"][t0:tf]
            else:
                ax.bar(time, -results["p_ut"][t0:tf], bottom=bottom, label='$P_\mathrm{hss,in}$', **bar_kw)

            if "diff_hss_in" in results and not all(results["diff_hss_in"] == 0):
                ax.bar(time, results["diff_hss_in"][t0:tf], bottom=bottom, label='$\Delta P_\mathrm{hss,in}$', **bar_kw)
                bottom += results["diff_hss_in"][t0:tf]

            axtw, axtd = None, None
            axtw = ax.twinx()
            # # Plot storage SOC
            if "e_hss_stor" in results:
                axtw.plot(time, results["e_hss_stor"][t0:tf], color='black', ls='--', label="$\mathrm{E_{stor}}$")
                axtw.set_ylabel("Stored energy (kWh)")
                axtw.spines['right'].set_color('black')
                axtw.tick_params(axis='y', colors='black')
                axtw.yaxis.label.set_color('black')
                axtw.legend().set_visible(False)

            if i == 1:
                axtd = ax.twinx()
                # # Plot storage SOC
                axtd.plot(time, results["d_cl"][t0:tf], '.', ls='-', color='lightgrey',
                          label="$\mathrm{control\ signal}$")

                axtd.spines["top"].set_visible(False)
                axtd.spines["right"].set_visible(False)
                axtd.spines["left"].set_visible(False)
                axtd.spines["bottom"].set_visible(False)
                axtd.tick_params(axis="both", which='both', length=0, labelcolor="none")
                axtd.legend().set_visible(False)

            # # Adjust and show
            ax.set_xlabel("Time (h)", fontsize=fontsize)
            ax.set_ylabel("Power (kW)" if i == 0 else "", fontsize=fontsize)
            ax.set_title("Thermal node", fontsize=fontsize - 2)
            ax.tick_params(labelsize=fontsize)
            ax.grid()

            if i == 1:
                # # Legend
                handles, labels = ax.get_legend_handles_labels()
                if axtd is not None:
                    axtd_handles, axtd_labels = axtd.get_legend_handles_labels()
                    axtw_handles, axtw_labels = axtw.get_legend_handles_labels()
                    handles = handles + axtd_handles + axtw_handles
                    labels = labels + axtd_labels + axtw_labels

                axes[1, 2].legend(handles, labels, fontsize=fontsize, loc='center')
                axes[1, 2].axis('off')

        # Adjust and show
        plt.subplots_adjust(top=0.55)  # Adjust the position of the overall title
        # fig.suptitle(titles[j], fontsize=fontsize)
        fig.tight_layout()
        plt.subplots_adjust(top=0.945, bottom=0.126, left=0.065, right=0.945, hspace=0.311, wspace=0.384)
        # plt.show()
        makedirs(path, exist_ok=True)
        plt.savefig(join(path, f"{suffix}_{titles[j]}_comp.pdf"), transparent=True)
        plt.close()
