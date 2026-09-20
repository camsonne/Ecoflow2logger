import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ecoflow_logger.logger import CSV_FIELDS, append_reading, poll_once, run_logger


def test_append_reading_writes_header_once(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc)

    append_reading(csv_path, t0, 80.0, 100.0, 0.0)
    append_reading(csv_path, t1, 81.0, None, 5.0)

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))

    assert list(rows[0].keys()) == CSV_FIELDS
    assert len(rows) == 2
    assert rows[0]["soc_percent"] == "80.0"
    assert rows[1]["watts_in"] == ""
    assert rows[1]["watts_out"] == "5.0"


class _StubClient:
    def __init__(self, quota):
        self.quota = quota
        self.calls = []

    def get_all_quota(self, device_sn):
        self.calls.append(device_sn)
        return self.quota


def test_poll_once_appends_one_row(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    client = _StubClient({"bmsMaster.soc": 55, "pd.wattsInSum": 10, "pd.wattsOutSum": 0})

    poll_once(client, "SN123", csv_path)

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["soc_percent"] == "55.0"


def test_poll_once_warns_with_available_keys_when_metric_missing(tmp_path: Path, caplog):
    csv_path = tmp_path / "log.csv"
    # None of these keys match any candidate in metrics.py, so soc_percent
    # comes back None even though the quota payload has real data.
    client = _StubClient({"some.unexpected.key": 55, "pd.wattsInSum": 10, "pd.wattsOutSum": 0})

    with caplog.at_level("WARNING"):
        poll_once(client, "SN123", csv_path)

    assert any("Available quota keys" in r.message for r in caplog.records)
    assert any("some.unexpected.key" in r.message for r in caplog.records)
    assert client.calls == ["SN123"]


class _AlwaysFailsClient:
    def get_all_quota(self, device_sn):
        raise RuntimeError("boom")


def test_run_logger_raises_when_bounded_run_never_succeeds(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    with pytest.raises(RuntimeError, match="boom"):
        run_logger(_AlwaysFailsClient(), "SN123", csv_path, interval_seconds=0, iterations=1)
    assert not csv_path.exists()


def test_run_logger_retries_all_iterations_before_raising(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    calls = []

    class _AlwaysFailsClientCounting:
        def get_all_quota(self, device_sn):
            calls.append(1)
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_logger(_AlwaysFailsClientCounting(), "SN123", csv_path, interval_seconds=0, iterations=3)
    assert len(calls) == 3


def test_run_logger_succeeds_if_any_bounded_iteration_succeeds(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    attempts = []

    class _FailsThenSucceedsClient:
        def get_all_quota(self, device_sn):
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("boom")
            return {"bmsMaster.soc": 42}

    run_logger(_FailsThenSucceedsClient(), "SN123", csv_path, interval_seconds=0, iterations=2)

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["soc_percent"] == "42.0"
