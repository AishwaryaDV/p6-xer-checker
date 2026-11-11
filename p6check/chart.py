"""The one chart: distribution of total float across all activities.

A histogram of total float (in working days) visualises two of the three
checks at once: the red zone on the left is negative float, the orange line
marks the high-float threshold. Everything to its right is high float.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: save to file, no display needed
import matplotlib.pyplot as plt

from .checks import HOURS_PER_DAY, Activity


def plot_float_distribution(
    activities: list[Activity],
    out_path: str,
    title: str,
    high_float_days: int = 44,
) -> str:
    floats_days = [
        a.total_float_hr / HOURS_PER_DAY
        for a in activities
        if a.total_float_hr is not None
    ]

    fig, ax = plt.subplots(figsize=(10, 5.5))

    if floats_days:
        ax.hist(floats_days, bins=40, color="#4C72B0", edgecolor="white")

    # Negative-float zone (left of 0).
    ax.axvspan(
        min(floats_days + [0]) - 1,
        0,
        color="#C44E52",
        alpha=0.12,
        label="negative float zone",
    )
    ax.axvline(0, color="#C44E52", linestyle="--", linewidth=1)

    # High-float threshold line.
    ax.axvline(
        high_float_days,
        color="#DD8452",
        linestyle="--",
        linewidth=1.5,
        label=f"high-float threshold ({high_float_days}d)",
    )

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Total float (working days)")
    ax.set_ylabel("Number of activities")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
