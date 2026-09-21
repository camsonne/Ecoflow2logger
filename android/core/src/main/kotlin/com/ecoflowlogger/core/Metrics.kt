package com.ecoflowlogger.core

/**
 * Extracts the metrics this app cares about from a raw EcoFlow quota
 * payload. Ported field-for-field from ecoflow_logger/metrics.py, which
 * carries the verification history for each key list below (see that
 * file's comments and git history for the real-device evidence).
 */
object Metrics {

    val SOC_KEYS = listOf(
        "pd.soc",
        "bms_emsStatus.lcdShowSoc",
        "bms_bmsStatus.soc",
        "bmsMaster.soc",
        "bmsMaster.f32ShowSoc",
        "soc",
    )

    val WATTS_IN_KEYS = listOf("pd.wattsInSum", "inv.inputWatts")
    val WATTS_OUT_KEYS = listOf("pd.wattsOutSum", "inv.outputWatts")

    private const val KIT_INFO_KEY = "bms_kitInfo.watts"

    // Only consulted when the device reports no kit info to resolve the
    // attached slot from (see attachedExtraBatterySlot). A real DELTA 2 Max
    // was observed reporting a stale bms_slave_bmsSlaveStatus_1 block
    // (frozen at a wrong SoC/wattage for hours) alongside a correct
    // bms_slave_bmsSlaveStatus_2 block for the pack that was actually
    // attached -- both carrying the same packSn. Assuming slot 1 is wrong
    // often enough that it's a last resort, not a primary key list.
    val FALLBACK_EXTRA_BATTERY_SOC_KEYS = listOf(
        "bms_slave_bmsSlaveStatus_1.soc",
        "bms_slave_bmsSlaveStatus_1.f32ShowSoc",
        "pd.bpPowerSoc",
    )
    val FALLBACK_EXTRA_BATTERY_WATTS_IN_KEYS = listOf("bms_slave_bmsSlaveStatus_1.inputWatts")
    val FALLBACK_EXTRA_BATTERY_WATTS_OUT_KEYS = listOf("bms_slave_bmsSlaveStatus_1.outputWatts")

    val PV1_WATTS_KEYS = listOf("mppt.inWatts", "pd.pv1ChargeWatts")
    val PV2_WATTS_KEYS = listOf("mppt.pv2InWatts", "pd.pv2ChargeWatts")

    private fun toDoubleOrNull(value: Any?): Double? = when (value) {
        is Number -> value.toDouble()
        is String -> value.toDoubleOrNull()
        else -> null
    }

    private fun firstPresent(data: Map<String, Any?>, keys: List<String>): Double? {
        for (key in keys) {
            if (!data.containsKey(key)) continue
            val num = toDoubleOrNull(data[key]) ?: continue
            return num
        }
        return null
    }

    /**
     * Returns the slave-slot number (1-based, matching the
     * bms_slave_bmsSlaveStatus_N key naming) of the extra battery that is
     * actually attached, per bms_kitInfo.watts' 0-based list -- the
     * authoritative slot list, where the attached pack is flagged
     * avaFlag == 1. Returns null if the device reports no kit info at all.
     */
    private fun attachedExtraBatterySlot(data: Map<String, Any?>): Int? {
        val kits = data[KIT_INFO_KEY] as? List<*> ?: return null
        for ((index, kit) in kits.withIndex()) {
            val kitMap = kit as? Map<*, *> ?: continue
            if (toDoubleOrNull(kitMap["avaFlag"]) == 1.0) return index + 1
        }
        return null
    }

    private data class ExtraBatteryValues(val soc: Double?, val wattsIn: Double?, val wattsOut: Double?)

    private fun extraBatteryValues(data: Map<String, Any?>): ExtraBatteryValues {
        val slot = attachedExtraBatterySlot(data)
            ?: return ExtraBatteryValues(
                soc = firstPresent(data, FALLBACK_EXTRA_BATTERY_SOC_KEYS),
                wattsIn = firstPresent(data, FALLBACK_EXTRA_BATTERY_WATTS_IN_KEYS),
                wattsOut = firstPresent(data, FALLBACK_EXTRA_BATTERY_WATTS_OUT_KEYS),
            )
        val prefix = "bms_slave_bmsSlaveStatus_$slot."
        return ExtraBatteryValues(
            soc = firstPresent(data, listOf("${prefix}soc", "${prefix}f32ShowSoc")),
            wattsIn = firstPresent(data, listOf("${prefix}inputWatts")),
            wattsOut = firstPresent(data, listOf("${prefix}outputWatts")),
        )
    }

    fun extractReading(data: Map<String, Any?>): Reading {
        val extra = extraBatteryValues(data)
        return Reading(
            socPercent = firstPresent(data, SOC_KEYS),
            wattsIn = firstPresent(data, WATTS_IN_KEYS),
            wattsOut = firstPresent(data, WATTS_OUT_KEYS),
            extraBatterySocPercent = extra.soc,
            extraBatteryWattsIn = extra.wattsIn,
            extraBatteryWattsOut = extra.wattsOut,
            pv1Watts = firstPresent(data, PV1_WATTS_KEYS),
            pv2Watts = firstPresent(data, PV2_WATTS_KEYS),
        )
    }
}
