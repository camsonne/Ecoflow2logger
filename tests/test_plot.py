import matplotlib

matplotlib.use("Agg")

from pathlib import Path

from ecoflow_logger.plot import load_log, plot_csv

SAMPLE_CSV = """timestamp,soc_percent,watts_in,watts_out
2024-01-01T00:00:00+00:00,80,0,150
2024-01-01T00:05:00+00:00,79,0,150
2024-01-01T00:10:00+00:00,79,300,0
2024-01-01T00:15:00+00:00,82,,0
"""


def test_load_log_parses_rows_and_blanks(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    csv_path.write_text(SAMPLE_CSV)

    rows = load_log(csv_path)

    assert len(rows) == 4
    assert rows[0].soc_percent == 80.0
    assert rows[0].watts_out == 150.0
    assert rows[3].watts_in is None


def test_plot_csv_writes_image_file(tmp_path: Path):
    csv_path = tmp_path / "log.csv"
    csv_path.write_text(SAMPLE_CSV)
    out_path = tmp_path / "plot.png"

    result = plot_csv(csv_path, out_path)

    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_plot_csv_handles_missing_soc(tmp_path: Path):
    # Regression test: a real device omitted soc_percent entirely (its
    # quota field name didn't match any of our candidate keys), and
    # matplotlib/numpy raised TypeError on None values instead of
    # treating them as gaps, since fill_between/plot need NaN, not None.
    csv_path = tmp_path / "log.csv"
    csv_path.write_text("timestamp,soc_percent,watts_in,watts_out\n2026-09-20T16:06:31+00:00,,598.0,249.0\n")
    out_path = tmp_path / "plot.png"

    result = plot_csv(csv_path, out_path)

    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
