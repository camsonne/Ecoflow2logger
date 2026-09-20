"""Plots a logged CSV of EcoFlow readings: charge % and power in/out vs time.

Renders two stacked panels sharing a time axis rather than one panel with
two y-scales, since state of charge (%) and power (W) are different units
and a dual-axis chart makes trends between them impossible to compare
honestly.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# Reference palette (see dataviz skill): categorical slots + chart chrome.
COLOR_SOC = "#2a78d6"  # slot 1, blue
COLOR_WATTS_IN = "#1baf7a"  # slot 3, aqua
COLOR_WATTS_OUT = "#eb6834"  # slot 2, orange

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"


class LogRow:
    __slots__ = ("timestamp", "soc_percent", "watts_in", "watts_out")

    def __init__(self, timestamp: datetime, soc_percent, watts_in, watts_out):
        self.timestamp = timestamp
        self.soc_percent = soc_percent
        self.watts_in = watts_in
        self.watts_out = watts_out


def _parse_float(value: str):
    if value is None or value == "":
        return None
    return float(value)


def load_log(csv_path: Path) -> list[LogRow]:
    rows: list[LogRow] = []
    with Path(csv_path).open(newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                LogRow(
                    timestamp=datetime.fromisoformat(raw["timestamp"]),
                    soc_percent=_parse_float(raw.get("soc_percent")),
                    watts_in=_parse_float(raw.get("watts_in")),
                    watts_out=_parse_float(raw.get("watts_out")),
                )
            )
    rows.sort(key=lambda r: r.timestamp)
    return rows


def _style_axis(ax) -> None:
    ax.set_facecolor(SURFACE)
    for spine_name, spine in ax.spines.items():
        if spine_name in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(BASELINE)
            spine.set_linewidth(1)
    ax.grid(True, axis="y", color=GRIDLINE, linewidth=1, linestyle="-")
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.xaxis.label.set_color(TEXT_SECONDARY)
    ax.yaxis.label.set_color(TEXT_SECONDARY)


def _label_line_end(ax, x, y, text, color) -> None:
    if x is None or y is None:
        return
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(6, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        color=TEXT_PRIMARY,
        fontweight="bold",
    )
    ax.plot([x], [y], marker="o", markersize=5, color=color, markeredgecolor=SURFACE, markeredgewidth=1.5)


def plot_log(rows: list[LogRow], title: str = "EcoFlow DELTA 2 Max") -> plt.Figure:
    if not rows:
        raise ValueError("No rows to plot")

    times = [r.timestamp for r in rows]
    soc = [r.soc_percent for r in rows]
    watts_in = [r.watts_in for r in rows]
    watts_out = [r.watts_out for r in rows]

    fig, (ax_soc, ax_power) = plt.subplots(
        2, 1, figsize=(11, 7), sharex=True, facecolor=SURFACE,
        gridspec_kw={"height_ratios": [1, 1.2], "hspace": 0.12},
        layout="constrained",
    )
    fig.suptitle(title, fontsize=14, fontweight="bold", color=TEXT_PRIMARY, x=0.02, ha="left")

    # --- Panel 1: state of charge ---
    ax_soc.plot(times, soc, color=COLOR_SOC, linewidth=2, solid_capstyle="round", solid_joinstyle="round")
    ax_soc.fill_between(times, soc, 0, color=COLOR_SOC, alpha=0.10, linewidth=0)
    ax_soc.set_ylabel("Charge (%)")
    ax_soc.set_ylim(0, 100)
    last_soc_x, last_soc_y = _last_valid(times, soc)
    if last_soc_y is not None:
        _label_line_end(ax_soc, last_soc_x, last_soc_y, f"{last_soc_y:.0f}%", COLOR_SOC)
    _style_axis(ax_soc)

    # --- Panel 2: power in / out ---
    ax_power.plot(
        times, watts_in, color=COLOR_WATTS_IN, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Power in",
    )
    ax_power.plot(
        times, watts_out, color=COLOR_WATTS_OUT, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Power out",
    )
    ax_power.axhline(0, color=BASELINE, linewidth=1)
    ax_power.set_ylabel("Power (W)")
    ax_power.set_xlabel("Time")

    last_in_x, last_in_y = _last_valid(times, watts_in)
    if last_in_y is not None:
        _label_line_end(ax_power, last_in_x, last_in_y, f"{last_in_y:.0f} W", COLOR_WATTS_IN)
    last_out_x, last_out_y = _last_valid(times, watts_out)
    if last_out_y is not None:
        _label_line_end(ax_power, last_out_x, last_out_y, f"{last_out_y:.0f} W", COLOR_WATTS_OUT)

    legend = ax_power.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
        frameon=False, fontsize=9, labelcolor=TEXT_SECONDARY,
    )
    for handle in legend.legend_handles:
        handle.set_linewidth(3)

    _style_axis(ax_power)

    ax_power.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax_power.xaxis.get_major_locator()))
    fig.autofmt_xdate()
    return fig


def _last_valid(xs, ys):
    for x, y in zip(reversed(xs), reversed(ys)):
        if y is not None:
            return x, y
    return None, None


def plot_csv(csv_path: Path, output_path: Path | None = None, title: str = "EcoFlow DELTA 2 Max") -> Path | None:
    rows = load_log(csv_path)
    fig = plot_log(rows, title=title)
    if output_path is not None:
        fig.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        return Path(output_path)
    plt.show()
    plt.close(fig)
    return None
