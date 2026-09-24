from pathlib import Path

from ecoflow_logger.dashboard import build_device_specs, write_dashboards


def test_build_device_specs_uses_legacy_names_for_device_one():
    specs = build_device_specs(["SNAAA"])
    assert len(specs) == 1
    spec = specs[0]
    assert spec.html_name == "index.html"
    assert spec.csv_path == "data/ecoflow_log.csv"
    assert spec.png_path == "data/ecoflow_plot.png"
    assert spec.title == "EcoFlow DELTA 2 Max"


def test_build_device_specs_numbers_additional_devices():
    specs = build_device_specs(["SNAAA", "SNBBB", "SNCCC"])
    assert [s.index for s in specs] == [1, 2, 3]
    assert specs[1].html_name == "device2.html"
    assert specs[1].csv_path == "data/ecoflow_log_2.csv"
    assert specs[1].png_path == "data/ecoflow_plot_2.png"
    assert specs[2].html_name == "device3.html"
    assert specs[2].csv_path == "data/ecoflow_log_3.csv"


def test_build_device_specs_skips_blank_entries():
    specs = build_device_specs(["SNAAA", "  ", "", "SNBBB"])
    assert len(specs) == 2
    assert specs[1].index == 2


def test_write_dashboards_writes_one_html_per_device_plus_service_worker(tmp_path: Path):
    written = write_dashboards(["SNAAA", "SNBBB"], tmp_path)
    names = {p.name for p in written}
    assert names == {"index.html", "device2.html", "sw.js"}
    for path in written:
        assert path.exists()


def test_write_dashboards_cross_links_devices(tmp_path: Path):
    write_dashboards(["SNAAA", "SNBBB"], tmp_path)
    index_html = (tmp_path / "index.html").read_text()
    device2_html = (tmp_path / "device2.html").read_text()

    assert 'href="device2.html"' in index_html
    assert "EcoFlow Device 2" in index_html
    assert 'href="index.html"' in device2_html
    assert "EcoFlow DELTA 2 Max" in device2_html


def test_write_dashboards_three_devices_each_link_to_the_other_two(tmp_path: Path):
    write_dashboards(["SNAAA", "SNBBB", "SNCCC"], tmp_path)
    index_html = (tmp_path / "index.html").read_text()

    assert 'href="device2.html"' in index_html
    assert 'href="device3.html"' in index_html
    # A page never links to itself.
    assert 'href="index.html"' not in index_html


def test_write_dashboards_references_correct_data_files(tmp_path: Path):
    write_dashboards(["SNAAA", "SNBBB"], tmp_path)
    device2_html = (tmp_path / "device2.html").read_text()
    assert "data/ecoflow_log_2.csv" in device2_html
    assert "data/ecoflow_plot_2.png" in device2_html


def test_write_dashboards_service_worker_caches_every_page(tmp_path: Path):
    write_dashboards(["SNAAA", "SNBBB", "SNCCC"], tmp_path)
    sw = (tmp_path / "sw.js").read_text()
    assert '"./index.html"' in sw
    assert '"./device2.html"' in sw
    assert '"./device3.html"' in sw


def test_write_dashboards_rejects_empty_device_list(tmp_path: Path):
    import pytest

    with pytest.raises(ValueError):
        write_dashboards([], tmp_path)
