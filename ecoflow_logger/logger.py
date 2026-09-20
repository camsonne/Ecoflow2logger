"""Polling loop that appends EcoFlow readings to a CSV log file."""

from __future__ import annotations

import csv
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from .api import EcoFlowClient
from .metrics import extract_reading

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "timestamp",
    "soc_percent",
    "watts_in",
    "watts_out",
    "extra_battery_soc_percent",
    "extra_battery_watts_in",
    "extra_battery_watts_out",
    "pv1_watts",
    "pv2_watts",
]


def _migrate_header_if_needed(csv_path: Path) -> None:
    """Rewrite an existing CSV onto the current ``CSV_FIELDS`` schema.

    Older logs were written before the extra-battery/PV columns existed;
    appending new-schema rows under their old header would silently
    misalign columns. Missing values on pre-existing rows are left blank.
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return
    with csv_path.open(newline="") as f:
        existing_header = next(csv.reader(f), None)
    if existing_header == CSV_FIELDS:
        return
    with csv_path.open(newline="") as f:
        old_rows = list(csv.DictReader(f))
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in old_rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def append_reading(
    csv_path: Path,
    timestamp: datetime,
    soc,
    watts_in,
    watts_out,
    extra_battery_soc=None,
    extra_battery_watts_in=None,
    extra_battery_watts_out=None,
    pv1_watts=None,
    pv2_watts=None,
) -> None:
    _migrate_header_if_needed(csv_path)
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": timestamp.isoformat(),
                "soc_percent": "" if soc is None else soc,
                "watts_in": "" if watts_in is None else watts_in,
                "watts_out": "" if watts_out is None else watts_out,
                "extra_battery_soc_percent": "" if extra_battery_soc is None else extra_battery_soc,
                "extra_battery_watts_in": "" if extra_battery_watts_in is None else extra_battery_watts_in,
                "extra_battery_watts_out": "" if extra_battery_watts_out is None else extra_battery_watts_out,
                "pv1_watts": "" if pv1_watts is None else pv1_watts,
                "pv2_watts": "" if pv2_watts is None else pv2_watts,
            }
        )


def poll_once(client: EcoFlowClient, device_sn: str, csv_path: Path) -> None:
    quota = client.get_all_quota(device_sn)
    reading = extract_reading(quota)
    now = datetime.now(timezone.utc)
    append_reading(
        csv_path,
        now,
        reading.soc_percent,
        reading.watts_in,
        reading.watts_out,
        reading.extra_battery_soc_percent,
        reading.extra_battery_watts_in,
        reading.extra_battery_watts_out,
        reading.pv1_watts,
        reading.pv2_watts,
    )
    logger.info(
        "%s soc=%s%% in=%sW out=%sW extra_soc=%s%% extra_in=%sW extra_out=%sW pv1=%sW pv2=%sW",
        now.isoformat(timespec="seconds"),
        reading.soc_percent,
        reading.watts_in,
        reading.watts_out,
        reading.extra_battery_soc_percent,
        reading.extra_battery_watts_in,
        reading.extra_battery_watts_out,
        reading.pv1_watts,
        reading.pv2_watts,
    )
    if reading.soc_percent is None or reading.watts_in is None or reading.watts_out is None:
        logger.warning(
            "One or more metrics were missing from the quota response for "
            "device %s; none of the candidate field names matched. Available "
            "quota keys: %s",
            device_sn,
            sorted(quota.keys()),
        )


def run_logger(
    client: EcoFlowClient,
    device_sn: str,
    csv_path: Path,
    interval_seconds: float,
    iterations: int | None = None,
) -> None:
    """Poll the device forever (or ``iterations`` times) at a fixed interval.

    Errors from a single poll are logged and swallowed so a transient
    network or API failure doesn't kill a long-running logging session.
    A bounded run (``iterations`` set, e.g. a single CI invocation) that
    never manages a single successful poll re-raises the last error
    instead of exiting cleanly with nothing logged, so the failure is
    visible rather than silently producing an empty CSV.
    """
    count = 0
    successes = 0
    last_error: Exception | None = None
    while iterations is None or count < iterations:
        try:
            poll_once(client, device_sn, csv_path)
            successes += 1
            last_error = None
        except Exception as exc:
            logger.exception("Failed to poll EcoFlow device %s", device_sn)
            last_error = exc
        count += 1
        if iterations is None or count < iterations:
            time.sleep(interval_seconds)

    if iterations is not None and successes == 0 and last_error is not None:
        raise last_error
