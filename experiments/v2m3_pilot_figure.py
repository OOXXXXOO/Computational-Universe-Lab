#!/usr/bin/env python3
"""Render the frozen M3′ 30-cell pilot collapse diagnostic.

This script is visualization-only: it reads the final result JSON and never
participates in the measured protocol or its SHA chain.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/results/v2m3_pilot.json"
DEFAULT_OUTPUT = ROOT / "visualizations/figs/v2m3_pilot_map.png"

GROUND = "#0B1013"
PANEL = "#111B22"
LINE = "#1E2C35"
INK = "#DDE6EC"
DIM = "#AEBAC4"
MUTED = "#7F909D"
METRIC = "#45D4C6"
MATTER = "#E7A24E"
SEALED = "#E5687A"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        result = json.load(handle)
    if result.get("status") != "HALT-PILOT-UNRESOLVED":
        raise ValueError("figure is frozen for HALT-PILOT-UNRESOLVED only")
    cells = result.get("cells", [])
    if len(cells) != 30 or not all(cell.get("valid") for cell in cells):
        raise ValueError("figure requires the complete 30/30 valid pilot")
    return result


def _style_axes(axis: plt.Axes) -> None:
    axis.set_facecolor(PANEL)
    axis.tick_params(colors=MUTED, labelsize=9)
    for spine in axis.spines.values():
        spine.set_color(LINE)
    axis.grid(color=LINE, linewidth=0.7, alpha=0.72)
    axis.set_axisbelow(True)


def render(result: dict, output: Path) -> None:
    cells = result["cells"]
    summary = result["summary"]
    criteria = result["resolvability"]["criteria"]

    q_values = np.array([cell["construction"]["q"] for cell in cells])
    kappa_values = np.array([cell["construction"]["kappa_c"] for cell in cells])
    epsilon_values = np.array(
        [cell["coordinates"]["epsilon_geo"]["min_max"][0] for cell in cells]
    )
    a_values = np.array(
        [
            sigma["A"]
            for cell in cells
            for sigma in cell["coordinates"]["sigma"].values()
        ]
    )
    direction_fail_count = sum(
        sigma["verdict"] == "FAIL"
        for cell in cells
        for sigma in cell["coordinates"]["sigma"].values()
    )

    fig = plt.figure(figsize=(13.8, 7.8), facecolor=GROUND)
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[0.32, 1.0],
        left=0.065,
        right=0.96,
        bottom=0.21,
        top=0.94,
        wspace=0.23,
        hspace=0.19,
    )
    title_axis = fig.add_subplot(grid[0, :])
    grid_axis = fig.add_subplot(grid[1, 0])
    map_axis = fig.add_subplot(grid[1, 1])

    title_axis.set_facecolor(GROUND)
    title_axis.axis("off")
    title_axis.text(
        0,
        0.98,
        "COMPUTATIONAL UNIVERSE LAB · PROJECTIVE RULE-SPACE PROGRAM",
        color=MUTED,
        family="monospace",
        fontsize=9.5,
        va="top",
    )
    title_axis.text(
        0,
        0.70,
        "M3′ 30-cell pilot: the family has no measured teeth",
        color=INK,
        family="serif",
        fontsize=25,
        weight="semibold",
        va="top",
    )
    title_axis.text(
        0,
        0.04,
        "HALT-PILOT-UNRESOLVED",
        color=SEALED,
        family="monospace",
        fontsize=11,
        weight="bold",
        va="bottom",
        bbox={
            "boxstyle": "round,pad=0.38,rounding_size=0.08",
            "facecolor": PANEL,
            "edgecolor": SEALED,
            "linewidth": 1.0,
        },
    )
    title_axis.text(
        0.265,
        0.055,
        "30/30 valid · formal preregistration locked · formal scan locked",
        color=DIM,
        family="monospace",
        fontsize=10,
        va="bottom",
    )

    _style_axes(grid_axis)
    grid_axis.scatter(
        kappa_values,
        q_values,
        s=118,
        facecolors=PANEL,
        edgecolors=METRIC,
        linewidths=1.5,
        zorder=3,
    )
    grid_axis.scatter(
        kappa_values,
        q_values,
        s=42,
        marker="x",
        color=SEALED,
        linewidths=1.7,
        zorder=4,
    )
    grid_axis.set_title(
        "Construction grid executed in full",
        loc="left",
        color=INK,
        family="serif",
        fontsize=16,
        pad=14,
    )
    grid_axis.text(
        0.965,
        0.96,
        "every q × κC cell is valid\nall map to the same ε signature",
        transform=grid_axis.transAxes,
        color=DIM,
        family="monospace",
        fontsize=9.5,
        va="top",
        ha="right",
        bbox={
            "boxstyle": "round,pad=0.3,rounding_size=0.08",
            "facecolor": PANEL,
            "edgecolor": LINE,
            "alpha": 0.92,
        },
    )
    grid_axis.set_xlabel("constraint-clearance dial  κC", color=DIM, labelpad=10)
    grid_axis.set_ylabel("local shear prefix  q", color=DIM, labelpad=10)
    grid_axis.set_xticks(sorted(set(kappa_values)))
    grid_axis.set_xticklabels(
        [f"{value:g}" for value in sorted(set(kappa_values))],
        family="monospace",
        rotation=30,
        ha="right",
    )
    grid_axis.set_yticks(sorted(set(q_values)))
    grid_axis.set_yticklabels(
        [str(value) for value in sorted(set(q_values))],
        family="monospace",
    )
    grid_axis.set_xlim(-0.007, 0.087)
    grid_axis.set_ylim(-0.45, 4.55)

    _style_axes(map_axis)
    # Deliberately use a macroscopic y range: the measured A spread is only
    # round-off scale, so showing a 1e-15 offset axis would overstate structure.
    map_axis.scatter(
        epsilon_values,
        np.ones_like(epsilon_values),
        s=260,
        color=SEALED,
        alpha=0.09,
        linewidths=0,
        zorder=2,
    )
    map_axis.scatter(
        [epsilon_values[0]],
        [1.0],
        s=205,
        facecolors=PANEL,
        edgecolors=SEALED,
        linewidths=2.0,
        zorder=4,
    )
    map_axis.scatter(
        [epsilon_values[0]],
        [1.0],
        s=45,
        marker="x",
        color=SEALED,
        linewidths=2.1,
        zorder=5,
    )
    map_axis.annotate(
        "30 cells × 3 directions collapse here\nεgeo = 1/3 · A = 1 within fp64 round-off",
        xy=(epsilon_values[0], 1.0),
        xytext=(0.302, 1.067),
        color=INK,
        family="monospace",
        fontsize=8.7,
        arrowprops={"arrowstyle": "-", "color": METRIC, "lw": 1.1},
        va="center",
    )
    map_axis.text(
        0.03,
        0.08,
        f"constant model wins {direction_fail_count}/90 direction fits\n"
        "fitted α is therefore non-identifiable",
        transform=map_axis.transAxes,
        color=MATTER,
        family="monospace",
        fontsize=10,
        va="bottom",
    )
    map_axis.set_title(
        "Measured (εgeo, σ) map collapses",
        loc="left",
        color=INK,
        family="serif",
        fontsize=16,
        pad=14,
    )
    map_axis.set_xlabel("measured geometric emergence  εgeo", color=DIM, labelpad=10)
    map_axis.set_ylabel("measured amplitude  A", color=DIM, labelpad=10)
    map_axis.set_xlim(0.29, 0.38)
    map_axis.set_ylim(0.90, 1.10)
    map_axis.ticklabel_format(axis="both", style="plain", useOffset=False)
    map_axis.set_xticks([0.30, 1 / 3, 0.36])
    map_axis.set_xticklabels(["0.30", "1/3", "0.36"], family="monospace")
    map_axis.set_yticks([0.90, 0.95, 1.00, 1.05, 1.10])
    map_axis.set_yticklabels(
        ["0.90", "0.95", "1.00", "1.05", "1.10"],
        family="monospace",
    )

    passed = [
        name.replace("_", " ")
        for name, item in criteria.items()
        if item["pass"]
    ]
    failed = [
        name.replace("_", " ")
        for name, item in criteria.items()
        if not item["pass"]
    ]
    fig.text(
        0.065,
        0.105,
        "PASS  " + " · ".join(passed),
        color=METRIC,
        family="monospace",
        fontsize=8.5,
    )
    fig.text(
        0.065,
        0.073,
        "NO TEETH  " + " · ".join(failed),
        color=SEALED,
        family="monospace",
        fontsize=8.5,
    )
    fig.text(
        0.96,
        0.073,
        f"support r≤{summary['max_support_radius']} · "
        f"Floquet |Δ|≤{summary['max_floquet_modulus_error']:.2e}",
        color=MUTED,
        family="monospace",
        fontsize=8.5,
        ha="right",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor=GROUND)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    render(_load(args.input), args.output)


if __name__ == "__main__":
    main()
