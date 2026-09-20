from ecoflow_logger.metrics import extract_reading


def test_extract_reading_uses_primary_keys():
    data = {
        "pd.soc": 87,
        "pd.wattsInSum": 120.5,
        "pd.wattsOutSum": 0,
        "inv.inputWatts": 999,  # should be ignored, primary key present
    }
    reading = extract_reading(data)
    assert reading.soc_percent == 87.0
    assert reading.watts_in == 120.5
    assert reading.watts_out == 0.0


def test_extract_reading_matches_real_delta2_max_response():
    # Regression test: pd.soc is the confirmed real field on a live
    # DELTA 2 Max (bmsMaster.soc, the original guess, never matched).
    data = {"pd.soc": 57, "pd.wattsInSum": 598.0, "pd.wattsOutSum": 249.0}
    reading = extract_reading(data)
    assert reading.soc_percent == 57.0
    assert reading.watts_in == 598.0
    assert reading.watts_out == 249.0


def test_extract_reading_falls_back_when_primary_key_missing():
    data = {"bmsMaster.f32ShowSoc": 42, "inv.inputWatts": 30, "inv.outputWatts": 15}
    reading = extract_reading(data)
    assert reading.soc_percent == 42.0
    assert reading.watts_in == 30.0
    assert reading.watts_out == 15.0


def test_extract_reading_missing_everything_returns_none():
    reading = extract_reading({})
    assert reading == (None, None, None)


def test_extract_reading_ignores_unparseable_values():
    data = {"bmsMaster.soc": "not-a-number"}
    reading = extract_reading(data)
    assert reading.soc_percent is None
