import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from .analysis import load_integrated_df, compute_basic_stats, prepare_timeseries
from .config import PROCESSED_DIR

def plot_scatter_crime_vs_rent():
    df = load_integrated_df()
    fig, ax = plt.subplots()
    sns.regplot(data=df, x="median_rent", y="crime_total", ax=ax)
    ax.set_title("Crime total vs. renda mediana por county-ano-trimestre")
    ax.set_xlabel("Renda mediana (€)")
    ax.set_ylabel("Crime total")
    out = PROCESSED_DIR / "scatter_crime_vs_rent.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return str(out)

def plot_timeseries():
    ts = prepare_timeseries()
    fig, ax1 = plt.subplots()
    ax1.plot(ts["year"], ts["crime_total"], marker="o")
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("Crime total", rotation=90)

    ax2 = ax1.twinx()
    ax2.plot(ts["year"], ts["rent_mean"], marker="x", linestyle="--")
    ax2.set_ylabel("Renda média (€)", rotation=90)
    ax1.set_title("Evolução de crime e renda na Irlanda")

    out = PROCESSED_DIR / "timeseries_crime_rent.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return str(out)
