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
    assert reading == (None, None, None, None, None, None, None, None)


def test_extract_reading_extracts_extra_battery():
    data = {
        "bms_slave_bmsSlaveStatus_1.soc": 88,
        "bms_slave_bmsSlaveStatus_1.inputWatts": 162,
        "bms_slave_bmsSlaveStatus_1.outputWatts": 0,
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent == 88.0
    assert reading.extra_battery_watts_in == 162.0
    assert reading.extra_battery_watts_out == 0.0


def test_extract_reading_reads_attached_slot_not_stale_one():
    # Regression test from a real DELTA 2 Max payload (2026-09-20). The
    # device reported two slave status blocks carrying the SAME packSn:
    # block 1 was a stale leftover frozen at 63% / 160W for hours, while
    # the pack was actually full and idle. bms_kitInfo.watts flags the
    # attached slot with avaFlag=1 -- here slot 2.
    data = {
        "bms_kitInfo.watts": [
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
            {"avaFlag": 1, "soc": 100, "sn": "R361Z11APH7E0147", "curPower": 0},
        ],
        "bms_slave_bmsSlaveStatus_1.soc": 63,
        "bms_slave_bmsSlaveStatus_1.f32ShowSoc": 62.5,
        "bms_slave_bmsSlaveStatus_1.inputWatts": 160,
        "bms_slave_bmsSlaveStatus_1.outputWatts": 0,
        "bms_slave_bmsSlaveStatus_2.soc": 100,
        "bms_slave_bmsSlaveStatus_2.inputWatts": 0,
        "bms_slave_bmsSlaveStatus_2.outputWatts": 0,
        "pd.bpPowerSoc": 63,
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent == 100.0
    assert reading.extra_battery_watts_in == 0.0
    assert reading.extra_battery_watts_out == 0.0


def test_extract_reading_extra_battery_uses_slot_one_when_it_is_attached():
    data = {
        "bms_kitInfo.watts": [
            {"avaFlag": 1, "soc": 88, "sn": "R361Z11APH7E0147", "curPower": 162},
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
        ],
        "bms_slave_bmsSlaveStatus_1.soc": 88,
        "bms_slave_bmsSlaveStatus_1.inputWatts": 162,
        "bms_slave_bmsSlaveStatus_1.outputWatts": 0,
        "bms_slave_bmsSlaveStatus_2.soc": 12,
        "bms_slave_bmsSlaveStatus_2.inputWatts": 999,
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent == 88.0
    assert reading.extra_battery_watts_in == 162.0


def test_extract_reading_extra_battery_falls_back_without_kit_info():
    # Other EcoFlow models may not report bms_kitInfo.watts at all.
    data = {
        "bms_slave_bmsSlaveStatus_1.soc": 88,
        "bms_slave_bmsSlaveStatus_1.inputWatts": 162,
        "bms_slave_bmsSlaveStatus_1.outputWatts": 0,
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent == 88.0
    assert reading.extra_battery_watts_in == 162.0


def test_extract_reading_uses_cell_data_when_avaflag_is_ambiguous():
    # Regression test from a real DELTA 2 Max payload (2026-09-24). Both
    # bms_kitInfo.watts entries reported avaFlag=0 (unlike the avaFlag=1
    # case above), so slot resolution fell through to the old "always
    # slot 1" fallback -- and slot 1 was the stale mirror here, frozen at
    # 64% / 25W in for hours while slot 2 (empty in the app's UI as "no
    # change") correctly tracked the pack as full and idle. The live slot
    # is identified by its populated cellVol array; the stale mirror's is
    # empty.
    data = {
        "bms_kitInfo.watts": [
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
        ],
        "bms_slave_bmsSlaveStatus_1.soc": 64,
        "bms_slave_bmsSlaveStatus_1.inputWatts": 25,
        "bms_slave_bmsSlaveStatus_1.outputWatts": 0,
        "bms_slave_bmsSlaveStatus_1.cellVol": [],
        "bms_slave_bmsSlaveStatus_2.soc": 100,
        "bms_slave_bmsSlaveStatus_2.inputWatts": 0,
        "bms_slave_bmsSlaveStatus_2.outputWatts": 0,
        "bms_slave_bmsSlaveStatus_2.cellVol": [3330, 3330, 3331],
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent == 100.0
    assert reading.extra_battery_watts_in == 0.0
    assert reading.extra_battery_watts_out == 0.0


def test_extract_reading_extra_battery_none_attached():
    data = {
        "bms_kitInfo.watts": [
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
            {"avaFlag": 0, "soc": 0, "sn": "", "curPower": 0},
        ],
        "pd.soc": 50,
    }
    reading = extract_reading(data)
    assert reading.extra_battery_soc_percent is None
    assert reading.extra_battery_watts_in is None


def test_extract_reading_extra_battery_missing_returns_none():
    reading = extract_reading({"pd.soc": 50})
    assert reading.extra_battery_soc_percent is None
    assert reading.extra_battery_watts_in is None
    assert reading.extra_battery_watts_out is None


def test_extract_reading_ignores_unparseable_values():
    data = {"bmsMaster.soc": "not-a-number"}
    reading = extract_reading(data)
    assert reading.soc_percent is None


def test_extract_reading_extracts_pv_channels():
    data = {"mppt.inWatts": 497.0, "mppt.pv2InWatts": 500.0}
    reading = extract_reading(data)
    assert reading.pv1_watts == 497.0
    assert reading.pv2_watts == 500.0


def test_extract_reading_pv_missing_returns_none():
    reading = extract_reading({"pd.soc": 50})
    assert reading.pv1_watts is None
    assert reading.pv2_watts is None
