"""Matplotlib figures for the app and the PDF report (one shared style)."""

import matplotlib.pyplot as plt
import numpy as np

from fuzzy.membership import DOMAINS, INPUT_SETS, trapmf


def plot_membership(var):
    """Plot the three fuzzy sets of one input variable."""
    lo, hi = DOMAINS[var]
    xs = np.linspace(lo, hi, 500)
    figure, axis = plt.subplots(figsize=(5, 2.5))
    for label, params in INPUT_SETS[var].items():
        axis.plot(xs, [trapmf(x, params) for x in xs], label=label)
    axis.set_title(f"Membership: {var}")
    axis.set_ylim(-0.05, 1.05)
    axis.set_xlabel(var)
    axis.set_ylabel("μ")
    axis.legend(loc="upper right", fontsize=8)
    figure.tight_layout()
    return figure


def plot_aggregation(trace):
    """Plot the aggregated output area and mark the centroid score."""
    figure, axis = plt.subplots(figsize=(5, 2.5))
    axis.fill_between(trace.xs, trace.agg, alpha=0.4)
    axis.plot(trace.xs, trace.agg)
    axis.axvline(
        trace.score,
        color="red",
        linestyle="--",
        label=f"score = {trace.score:.1f}",
    )
    axis.set_title("Aggregated output & centroid")
    axis.set_xlim(*DOMAINS["Prioritas"])
    axis.set_ylim(-0.05, 1.05)
    axis.set_xlabel("Prioritas Beasiswa")
    axis.set_ylabel("μ")
    axis.legend(loc="upper right", fontsize=8)
    figure.tight_layout()
    return figure
