import matplotlib

matplotlib.use("Agg")

from pathlib import Path

from ecoflow_logger.plot import DISPLAY_TZ, load_log, plot_csv, plot_log

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


def test_plot_log_displays_times_in_eastern(tmp_path: Path):
    # Stored timestamps are UTC; the chart should display them converted
    # to America/New_York (EST in January, UTC-5), not raw UTC.
    csv_path = tmp_path / "log.csv"
    csv_path.write_text("timestamp,soc_percent,watts_in,watts_out\n2024-01-15T17:00:00+00:00,50,100,0\n")
    rows = load_log(csv_path)

    fig = plot_log(rows)
    soc_line = fig.axes[0].lines[0]
    plotted_time = soc_line.get_xdata()[0]  # original datetimes, not yet unit-converted

    assert plotted_time.tzinfo == DISPLAY_TZ
    assert plotted_time.hour == 12  # 17:00 UTC -> 12:00 EST (UTC-5)
    assert plotted_time.utcoffset().total_seconds() == -5 * 3600


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
