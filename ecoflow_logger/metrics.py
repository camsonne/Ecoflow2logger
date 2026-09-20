"""Extracts the metrics we care about from a raw EcoFlow quota payload.

The DELTA 2 Max reports dozens of quota fields; the exact set of keys
that are populated can vary slightly by firmware version. Each metric
below is looked up via an ordered list of candidate keys, and the first
one present in the payload wins.
"""

from __future__ import annotations

from typing import Any, NamedTuple

# State of charge, in percent.
SOC_KEYS = ["bmsMaster.soc", "bmsMaster.f32ShowSoc", "soc"]

# Total power flowing into the device, in watts (AC + solar + car input).
WATTS_IN_KEYS = ["pd.wattsInSum", "inv.inputWatts"]

# Total power flowing out of the device, in watts (AC + USB + DC output).
WATTS_OUT_KEYS = ["pd.wattsOutSum", "inv.outputWatts"]


class Reading(NamedTuple):
    soc_percent: float | None
    watts_in: float | None
    watts_out: float | None


def _first_present(data: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        if key in data and data[key] is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                continue
    return None


def extract_reading(quota_data: dict[str, Any]) -> Reading:
    """Pull SoC and power in/out out of a raw ``get_all_quota()`` payload."""
    return Reading(
        soc_percent=_first_present(quota_data, SOC_KEYS),
        watts_in=_first_present(quota_data, WATTS_IN_KEYS),
        watts_out=_first_present(quota_data, WATTS_OUT_KEYS),
    )
