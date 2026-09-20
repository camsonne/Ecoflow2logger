"""Plots a logged CSV of EcoFlow readings: charge % and power in/out vs time.

Renders two stacked panels sharing a time axis rather than one panel with
two y-scales, since state of charge (%) and power (W) are different units
and a dual-axis chart makes trends between them impossible to compare
honestly. When the log includes per-PV solar data and/or extra-battery
data, more panels are added below in the same style, rather than
overlaying more series on the existing panels.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# America/New_York rather than a fixed UTC-5 offset so the chart tracks
# EST/EDT correctly across the DST switch; data is stored in UTC and
# only converted for display.
DISPLAY_TZ = ZoneInfo("America/New_York")

# Reference palette (see dataviz skill): categorical slots + chart chrome.
COLOR_SOC = "#2a78d6"  # slot 1, blue
COLOR_WATTS_IN = "#1baf7a"  # slot 3, aqua
COLOR_WATTS_OUT = "#eb6834"  # slot 2, orange
COLOR_PV1 = "#008300"  # slot 6, green
COLOR_PV2 = "#eda100"  # slot 4, yellow

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TEXT_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"


class LogRow:
    __slots__ = (
        "timestamp",
        "soc_percent",
        "watts_in",
        "watts_out",
        "extra_battery_soc_percent",
        "extra_battery_watts_in",
        "extra_battery_watts_out",
        "pv1_watts",
        "pv2_watts",
    )

    def __init__(
        self,
        timestamp: datetime,
        soc_percent,
        watts_in,
        watts_out,
        extra_battery_soc_percent=None,
        extra_battery_watts_in=None,
        extra_battery_watts_out=None,
        pv1_watts=None,
        pv2_watts=None,
    ):
        self.timestamp = timestamp
        self.soc_percent = soc_percent
        self.watts_in = watts_in
        self.watts_out = watts_out
        self.extra_battery_soc_percent = extra_battery_soc_percent
        self.extra_battery_watts_in = extra_battery_watts_in
        self.extra_battery_watts_out = extra_battery_watts_out
        self.pv1_watts = pv1_watts
        self.pv2_watts = pv2_watts


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
                    extra_battery_soc_percent=_parse_float(raw.get("extra_battery_soc_percent")),
                    extra_battery_watts_in=_parse_float(raw.get("extra_battery_watts_in")),
                    extra_battery_watts_out=_parse_float(raw.get("extra_battery_watts_out")),
                    pv1_watts=_parse_float(raw.get("pv1_watts")),
                    pv2_watts=_parse_float(raw.get("pv2_watts")),
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


def _plot_soc_panel(ax, times, soc, label_suffix: str = "") -> None:
    soc_plot = _nans_for_none(soc)
    ax.plot(times, soc_plot, color=COLOR_SOC, linewidth=2, solid_capstyle="round", solid_joinstyle="round")
    ax.fill_between(times, soc_plot, 0, color=COLOR_SOC, alpha=0.10, linewidth=0)
    ax.set_ylabel(f"Charge{label_suffix} (%)")
    ax.set_ylim(0, 100)
    last_x, last_y = _last_valid(times, soc)
    if last_y is not None:
        _label_line_end(ax, last_x, last_y, f"{last_y:.0f}%", COLOR_SOC)
    _style_axis(ax)


def _plot_power_panel(ax, times, watts_in, watts_out, label_suffix: str = "") -> None:
    watts_in_plot = _nans_for_none(watts_in)
    watts_out_plot = _nans_for_none(watts_out)
    ax.plot(
        times, watts_in_plot, color=COLOR_WATTS_IN, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Power in",
    )
    ax.plot(
        times, watts_out_plot, color=COLOR_WATTS_OUT, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Power out",
    )
    ax.axhline(0, color=BASELINE, linewidth=1)
    ax.set_ylabel(f"Power{label_suffix} (W)")

    last_in_x, last_in_y = _last_valid(times, watts_in)
    if last_in_y is not None:
        _label_line_end(ax, last_in_x, last_in_y, f"{last_in_y:.0f} W", COLOR_WATTS_IN)
    last_out_x, last_out_y = _last_valid(times, watts_out)
    if last_out_y is not None:
        _label_line_end(ax, last_out_x, last_out_y, f"{last_out_y:.0f} W", COLOR_WATTS_OUT)

    legend = ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
        frameon=False, fontsize=9, labelcolor=TEXT_SECONDARY,
    )
    for handle in legend.legend_handles:
        handle.set_linewidth(3)

    _style_axis(ax)


def _plot_pv_panel(ax, times, pv1, pv2) -> None:
    pv1_plot = _nans_for_none(pv1)
    pv2_plot = _nans_for_none(pv2)
    ax.plot(
        times, pv1_plot, color=COLOR_PV1, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Solar 1",
    )
    ax.plot(
        times, pv2_plot, color=COLOR_PV2, linewidth=2,
        solid_capstyle="round", solid_joinstyle="round", label="Solar 2",
    )
    ax.axhline(0, color=BASELINE, linewidth=1)
    ax.set_ylabel("Solar power (W)")

    last_pv1_x, last_pv1_y = _last_valid(times, pv1)
    if last_pv1_y is not None:
        _label_line_end(ax, last_pv1_x, last_pv1_y, f"{last_pv1_y:.0f} W", COLOR_PV1)
    last_pv2_x, last_pv2_y = _last_valid(times, pv2)
    if last_pv2_y is not None:
        _label_line_end(ax, last_pv2_x, last_pv2_y, f"{last_pv2_y:.0f} W", COLOR_PV2)

    legend = ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=2,
        frameon=False, fontsize=9, labelcolor=TEXT_SECONDARY,
    )
    for handle in legend.legend_handles:
        handle.set_linewidth(3)

    _style_axis(ax)


def plot_log(rows: list[LogRow], title: str = "EcoFlow DELTA 2 Max") -> plt.Figure:
    if not rows:
        raise ValueError("No rows to plot")

    times = [r.timestamp.astimezone(DISPLAY_TZ) for r in rows]
    soc = [r.soc_percent for r in rows]
    watts_in = [r.watts_in for r in rows]
    watts_out = [r.watts_out for r in rows]
    extra_soc = [r.extra_battery_soc_percent for r in rows]
    extra_in = [r.extra_battery_watts_in for r in rows]
    extra_out = [r.extra_battery_watts_out for r in rows]
    pv1 = [r.pv1_watts for r in rows]
    pv2 = [r.pv2_watts for r in rows]

    has_extra_battery = any(v is not None for v in (*extra_soc, *extra_in, *extra_out))
    has_pv = any(v is not None for v in (*pv1, *pv2))

    main_suffix = " — Main" if has_extra_battery else ""
    # (height_ratio, render_fn) pairs; panels beyond the always-present main
    # soc/power pair are only added when that data is actually present, so
    # a log without solar or an extra battery still renders the original
    # two-panel chart.
    panels: list[tuple[float, object]] = [
        (1, lambda ax: _plot_soc_panel(ax, times, soc, label_suffix=main_suffix)),
        (1.2, lambda ax: _plot_power_panel(ax, times, watts_in, watts_out, label_suffix=main_suffix)),
    ]
    if has_pv:
        panels.append((1.2, lambda ax: _plot_pv_panel(ax, times, pv1, pv2)))
    if has_extra_battery:
        panels.append((1, lambda ax: _plot_soc_panel(ax, times, extra_soc, label_suffix=" — Extra Battery")))
        panels.append(
            (1.2, lambda ax: _plot_power_panel(ax, times, extra_in, extra_out, label_suffix=" — Extra Battery"))
        )

    n_panels = len(panels)
    height_ratios = [ratio for ratio, _ in panels]
    fig, axes = plt.subplots(
        n_panels, 1, figsize=(11, 3.5 + 3.25 * (n_panels - 1)), sharex=True, facecolor=SURFACE,
        gridspec_kw={"height_ratios": height_ratios, "hspace": 0.12 if n_panels == 2 else 0.25},
        layout="constrained",
    )
    fig.suptitle(title, fontsize=14, fontweight="bold", color=TEXT_PRIMARY, x=0.02, ha="left")

    for ax, (_, render) in zip(axes, panels):
        render(ax)

    last_ax = axes[-1]
    last_ax.set_xlabel("Time (Eastern)")
    # ConciseDateFormatter formats using its own tz (UTC by default),
    # ignoring the tzinfo already on the plotted datetimes, so it has to
    # be told explicitly or the tick labels silently revert to UTC.
    last_ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(last_ax.xaxis.get_major_locator(), tz=DISPLAY_TZ)
    )
    fig.autofmt_xdate()
    return fig


def _last_valid(xs, ys):
    for x, y in zip(reversed(xs), reversed(ys)):
        if y is not None:
            return x, y
    return None, None


def _nans_for_none(values: list[float | None]) -> list[float]:
    return [math.nan if v is None else v for v in values]


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
