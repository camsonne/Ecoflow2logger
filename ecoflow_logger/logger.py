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

CSV_FIELDS = ["timestamp", "soc_percent", "watts_in", "watts_out"]


def append_reading(csv_path: Path, timestamp: datetime, soc, watts_in, watts_out) -> None:
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
            }
        )


def poll_once(client: EcoFlowClient, device_sn: str, csv_path: Path) -> None:
    quota = client.get_all_quota(device_sn)
    reading = extract_reading(quota)
    now = datetime.now(timezone.utc)
    append_reading(csv_path, now, reading.soc_percent, reading.watts_in, reading.watts_out)
    logger.info(
        "%s soc=%s%% in=%sW out=%sW",
        now.isoformat(timespec="seconds"),
        reading.soc_percent,
        reading.watts_in,
        reading.watts_out,
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
    """
    count = 0
    while iterations is None or count < iterations:
        try:
            poll_once(client, device_sn, csv_path)
        except Exception:
            logger.exception("Failed to poll EcoFlow device %s", device_sn)
        count += 1
        if iterations is None or count < iterations:
            time.sleep(interval_seconds)
