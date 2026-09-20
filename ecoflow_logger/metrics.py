"""Extracts the metrics we care about from a raw EcoFlow quota payload.

The DELTA 2 Max reports dozens of quota fields; the exact set of keys
that are populated can vary slightly by firmware version. Each metric
below is looked up via an ordered list of candidate keys, and the first
one present in the payload wins.
"""

from __future__ import annotations

from typing import Any, NamedTuple

# State of charge, in percent. `pd.soc` confirmed against a real DELTA 2
# Max (2026-09-20); the bmsMaster.* keys were an unverified guess that
# never matched any real device response and are kept as fallbacks for
# other EcoFlow models that may use them.
SOC_KEYS = [
    "pd.soc",
    "bms_emsStatus.lcdShowSoc",
    "bms_bmsStatus.soc",
    "bmsMaster.soc",
    "bmsMaster.f32ShowSoc",
    "soc",
]

# Total power flowing into the device, in watts (AC + solar + car input).
WATTS_IN_KEYS = ["pd.wattsInSum", "inv.inputWatts"]

# Total power flowing out of the device, in watts (AC + USB + DC output).
WATTS_OUT_KEYS = ["pd.wattsOutSum", "inv.outputWatts"]

# Extra/expansion battery pack ("Smart Extra Battery"), reported by
# EcoFlow as a "slave" BMS pack. bms_slave_bmsSlaveStatus_1.* and
# pd.bpPowerSoc were both confirmed present in a real DELTA 2 Max +
# extra-battery quota response (2026-09-20) -- unverified which one
# actually holds the live value, so both are tried.
EXTRA_BATTERY_SOC_KEYS = [
    "bms_slave_bmsSlaveStatus_1.soc",
    "bms_slave_bmsSlaveStatus_1.f32ShowSoc",
    "pd.bpPowerSoc",
]
EXTRA_BATTERY_WATTS_IN_KEYS = ["bms_slave_bmsSlaveStatus_1.inputWatts"]
EXTRA_BATTERY_WATTS_OUT_KEYS = ["bms_slave_bmsSlaveStatus_1.outputWatts"]

# Individual solar (PV) input channels -- the DELTA 2 Max has two separate
# MPPT inputs, shown as two "Solar" tiles in the app. mppt.inWatts /
# mppt.pv2InWatts confirmed present in a real quota response (2026-09-20);
# pd.pv1ChargeWatts/pd.pv2ChargeWatts are the pd-namespace mirrors seen for
# other metrics (e.g. pd.wattsInSum vs inv.inputWatts) and kept as fallbacks.
PV1_WATTS_KEYS = ["mppt.inWatts", "pd.pv1ChargeWatts"]
PV2_WATTS_KEYS = ["mppt.pv2InWatts", "pd.pv2ChargeWatts"]


class Reading(NamedTuple):
    soc_percent: float | None
    watts_in: float | None
    watts_out: float | None
    extra_battery_soc_percent: float | None
    extra_battery_watts_in: float | None
    extra_battery_watts_out: float | None
    pv1_watts: float | None
    pv2_watts: float | None


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
        extra_battery_soc_percent=_first_present(quota_data, EXTRA_BATTERY_SOC_KEYS),
        extra_battery_watts_in=_first_present(quota_data, EXTRA_BATTERY_WATTS_IN_KEYS),
        extra_battery_watts_out=_first_present(quota_data, EXTRA_BATTERY_WATTS_OUT_KEYS),
        pv1_watts=_first_present(quota_data, PV1_WATTS_KEYS),
        pv2_watts=_first_present(quota_data, PV2_WATTS_KEYS),
    )
