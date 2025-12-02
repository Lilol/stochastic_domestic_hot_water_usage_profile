from os import makedirs
from os.path import join
import matplotlib.pyplot as plt
from matplotlib import dates, ticker

import pandas as pd
import seaborn as sns

plt.rcParams['figure.constrained_layout.use'] = True


def plot_yearly_heatmap(input_df, to_plot, metric, output_dir, postfix):
    df = input_df.copy()
    df['hour'] = pd.to_timedelta(df.index, unit='h')
    df['date'] = pd.to_datetime('2021-01-01') + df['hour']
    df.index = pd.to_datetime(df["date"])
    df['day'] = pd.to_datetime(df.index.floor("d"))
    df['hour_of_day'] = df.index.hour
    df_pivot = df.pivot(index='hour_of_day', columns='day', values=to_plot)
    fig, axes = plt.subplots(1, 2, figsize=(10, 8), width_ratios=[9, 1])
    sns.heatmap(df_pivot, ax=axes[0], cmap='viridis', cbar=True, cbar_kws={"label": f"{metric}".title()},
                cbar_ax=axes[1])

    ax = axes[0]
    ax.set_yticks([i for i in range(1, 25, 2)])
    ax.set_yticklabels([f"{i:2d}:00" for i in range(1, 25, 2)], rotation=45)
    ax.xaxis.set_major_locator(dates.MonthLocator())
    # 16 is a slight approximation since months differ in number of days.
    ax.xaxis.set_minor_locator(dates.MonthLocator(bymonthday=16))

    ax.xaxis.set_major_formatter(ticker.NullFormatter())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%b'))

    for tick in ax.xaxis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment('center')

    ax.set_xlabel("")
    ax.set_ylabel("Hour")
    makedirs(output_dir, exist_ok=True)
    plt.savefig(join(output_dir, f"heatmap_{metric}_{postfix}.png"))
