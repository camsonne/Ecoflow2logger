import csv
from datetime import datetime, timezone
from pathlib import Path

from ecoflow_logger.logger import CSV_FIELDS, append_reading, poll_once


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
    assert client.calls == ["SN123"]
