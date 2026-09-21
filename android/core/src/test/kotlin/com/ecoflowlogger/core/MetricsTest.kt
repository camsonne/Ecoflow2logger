package com.ecoflowlogger.core

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class MetricsTest {

    @Test
    fun extractReadingUsesPrimaryKeys() {
        val data = mapOf(
            "pd.soc" to 87,
            "pd.wattsInSum" to 120.5,
            "pd.wattsOutSum" to 0,
            "inv.inputWatts" to 999, // should be ignored, primary key present
        )
        val reading = Metrics.extractReading(data)
        assertEquals(87.0, reading.socPercent)
        assertEquals(120.5, reading.wattsIn)
        assertEquals(0.0, reading.wattsOut)
    }

    @Test
    fun extractReadingMatchesRealDelta2MaxResponse() {
        val data = mapOf("pd.soc" to 57, "pd.wattsInSum" to 598.0, "pd.wattsOutSum" to 249.0)
        val reading = Metrics.extractReading(data)
        assertEquals(57.0, reading.socPercent)
        assertEquals(598.0, reading.wattsIn)
        assertEquals(249.0, reading.wattsOut)
    }

    @Test
    fun extractReadingFallsBackWhenPrimaryKeyMissing() {
        val data = mapOf("bmsMaster.f32ShowSoc" to 42, "inv.inputWatts" to 30, "inv.outputWatts" to 15)
        val reading = Metrics.extractReading(data)
        assertEquals(42.0, reading.socPercent)
        assertEquals(30.0, reading.wattsIn)
        assertEquals(15.0, reading.wattsOut)
    }

    @Test
    fun extractReadingMissingEverythingReturnsNull() {
        val reading = Metrics.extractReading(emptyMap())
        assertNull(reading.socPercent)
        assertNull(reading.wattsIn)
        assertNull(reading.wattsOut)
        assertNull(reading.extraBatterySocPercent)
        assertNull(reading.extraBatteryWattsIn)
        assertNull(reading.extraBatteryWattsOut)
        assertNull(reading.pv1Watts)
        assertNull(reading.pv2Watts)
    }

    @Test
    fun extractReadingIgnoresUnparseableValues() {
        val reading = Metrics.extractReading(mapOf("bmsMaster.soc" to "not-a-number"))
        assertNull(reading.socPercent)
    }

    @Test
    fun extractReadingExtractsPvChannels() {
        val data = mapOf("mppt.inWatts" to 497.0, "mppt.pv2InWatts" to 500.0)
        val reading = Metrics.extractReading(data)
        assertEquals(497.0, reading.pv1Watts)
        assertEquals(500.0, reading.pv2Watts)
    }

    @Test
    fun extractReadingPvMissingReturnsNull() {
        val reading = Metrics.extractReading(mapOf("pd.soc" to 50))
        assertNull(reading.pv1Watts)
        assertNull(reading.pv2Watts)
    }

    @Test
    fun extractReadingReadsAttachedSlotNotStaleOne() {
        // Regression test from a real DELTA 2 Max payload (2026-09-20). The
        // device reported two slave status blocks carrying the SAME
        // packSn: block 1 was a stale leftover frozen at 63% / 160W for
        // hours, while the pack was actually full and idle.
        // bms_kitInfo.watts flags the attached slot with avaFlag=1 -- here
        // slot 2.
        val data = mapOf(
            "bms_kitInfo.watts" to listOf(
                mapOf("avaFlag" to 0, "soc" to 0, "sn" to "", "curPower" to 0),
                mapOf("avaFlag" to 1, "soc" to 100, "sn" to "R361Z11APH7E0147", "curPower" to 0),
            ),
            "bms_slave_bmsSlaveStatus_1.soc" to 63,
            "bms_slave_bmsSlaveStatus_1.f32ShowSoc" to 62.5,
            "bms_slave_bmsSlaveStatus_1.inputWatts" to 160,
            "bms_slave_bmsSlaveStatus_1.outputWatts" to 0,
            "bms_slave_bmsSlaveStatus_2.soc" to 100,
            "bms_slave_bmsSlaveStatus_2.inputWatts" to 0,
            "bms_slave_bmsSlaveStatus_2.outputWatts" to 0,
            "pd.bpPowerSoc" to 63,
        )
        val reading = Metrics.extractReading(data)
        assertEquals(100.0, reading.extraBatterySocPercent)
        assertEquals(0.0, reading.extraBatteryWattsIn)
        assertEquals(0.0, reading.extraBatteryWattsOut)
    }

    @Test
    fun extractReadingExtraBatteryUsesSlotOneWhenItIsAttached() {
        val data = mapOf(
            "bms_kitInfo.watts" to listOf(
                mapOf("avaFlag" to 1, "soc" to 88, "sn" to "R361Z11APH7E0147", "curPower" to 162),
                mapOf("avaFlag" to 0, "soc" to 0, "sn" to "", "curPower" to 0),
            ),
            "bms_slave_bmsSlaveStatus_1.soc" to 88,
            "bms_slave_bmsSlaveStatus_1.inputWatts" to 162,
            "bms_slave_bmsSlaveStatus_1.outputWatts" to 0,
            "bms_slave_bmsSlaveStatus_2.soc" to 12,
            "bms_slave_bmsSlaveStatus_2.inputWatts" to 999,
        )
        val reading = Metrics.extractReading(data)
        assertEquals(88.0, reading.extraBatterySocPercent)
        assertEquals(162.0, reading.extraBatteryWattsIn)
    }

    @Test
    fun extractReadingExtraBatteryFallsBackWithoutKitInfo() {
        // Other EcoFlow models may not report bms_kitInfo.watts at all.
        val data = mapOf(
            "bms_slave_bmsSlaveStatus_1.soc" to 88,
            "bms_slave_bmsSlaveStatus_1.inputWatts" to 162,
            "bms_slave_bmsSlaveStatus_1.outputWatts" to 0,
        )
        val reading = Metrics.extractReading(data)
        assertEquals(88.0, reading.extraBatterySocPercent)
        assertEquals(162.0, reading.extraBatteryWattsIn)
    }

    @Test
    fun extractReadingExtraBatteryNoneAttached() {
        val data = mapOf(
            "bms_kitInfo.watts" to listOf(
                mapOf("avaFlag" to 0, "soc" to 0, "sn" to "", "curPower" to 0),
                mapOf("avaFlag" to 0, "soc" to 0, "sn" to "", "curPower" to 0),
            ),
            "pd.soc" to 50,
        )
        val reading = Metrics.extractReading(data)
        assertNull(reading.extraBatterySocPercent)
        assertNull(reading.extraBatteryWattsIn)
    }

    @Test
    fun extractReadingExtraBatteryMissingReturnsNull() {
        val reading = Metrics.extractReading(mapOf("pd.soc" to 50))
        assertNull(reading.extraBatterySocPercent)
        assertNull(reading.extraBatteryWattsIn)
        assertNull(reading.extraBatteryWattsOut)
    }
}
