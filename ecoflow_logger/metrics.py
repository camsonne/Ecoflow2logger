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
# EcoFlow as a "slave" BMS pack.
#
# The device exposes a status block per slave slot and keeps a stale one
# around for a slot that is not actually attached -- on a real DELTA 2 Max
# (2026-09-20) both blocks even carried the same packSn, while block 1 sat
# frozen at 63% / 160W for hours and block 2 correctly tracked the pack as
# full and idle. bms_kitInfo.watts is the authoritative slot list, with
# avaFlag marking the slot that is really present, so the live block is
# resolved through that rather than assumed to be slot 1.
KIT_INFO_KEY = "bms_kitInfo.watts"

# Only consulted when the device reports no kit info to resolve the slot
# from. pd.bpPowerSoc mirrored the stale block on the device above, so it
# is a last resort rather than a peer of the slave-status keys.
FALLBACK_EXTRA_BATTERY_SOC_KEYS = [
    "bms_slave_bmsSlaveStatus_1.soc",
    "bms_slave_bmsSlaveStatus_1.f32ShowSoc",
    "pd.bpPowerSoc",
]
FALLBACK_EXTRA_BATTERY_WATTS_IN_KEYS = ["bms_slave_bmsSlaveStatus_1.inputWatts"]
FALLBACK_EXTRA_BATTERY_WATTS_OUT_KEYS = ["bms_slave_bmsSlaveStatus_1.outputWatts"]

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


def _attached_extra_battery_slot(quota_data: dict[str, Any]) -> int | None:
    """Return the slave-slot number of the extra battery that is present.

    ``bms_kitInfo.watts`` is a list with one entry per slot; the attached
    one is flagged ``avaFlag == 1``. Slot numbering in the
    ``bms_slave_bmsSlaveStatus_N`` keys is 1-based against that list.
    """
    kits = quota_data.get(KIT_INFO_KEY)
    if not isinstance(kits, list):
        return None
    for index, kit in enumerate(kits):
        if isinstance(kit, dict) and kit.get("avaFlag") == 1:
            return index + 1
    return None


def _extra_battery_values(
    quota_data: dict[str, Any],
) -> tuple[float | None, float | None, float | None]:
    slot = _attached_extra_battery_slot(quota_data)
    if slot is None:
        return (
            _first_present(quota_data, FALLBACK_EXTRA_BATTERY_SOC_KEYS),
            _first_present(quota_data, FALLBACK_EXTRA_BATTERY_WATTS_IN_KEYS),
            _first_present(quota_data, FALLBACK_EXTRA_BATTERY_WATTS_OUT_KEYS),
        )
    prefix = f"bms_slave_bmsSlaveStatus_{slot}."
    return (
        _first_present(quota_data, [f"{prefix}soc", f"{prefix}f32ShowSoc"]),
        _first_present(quota_data, [f"{prefix}inputWatts"]),
        _first_present(quota_data, [f"{prefix}outputWatts"]),
    )


def extract_reading(quota_data: dict[str, Any]) -> Reading:
    """Pull SoC and power in/out out of a raw ``get_all_quota()`` payload."""
    extra_soc, extra_in, extra_out = _extra_battery_values(quota_data)
    return Reading(
        soc_percent=_first_present(quota_data, SOC_KEYS),
        watts_in=_first_present(quota_data, WATTS_IN_KEYS),
        watts_out=_first_present(quota_data, WATTS_OUT_KEYS),
        extra_battery_soc_percent=extra_soc,
        extra_battery_watts_in=extra_in,
        extra_battery_watts_out=extra_out,
        pv1_watts=_first_present(quota_data, PV1_WATTS_KEYS),
        pv2_watts=_first_present(quota_data, PV2_WATTS_KEYS),
    )
