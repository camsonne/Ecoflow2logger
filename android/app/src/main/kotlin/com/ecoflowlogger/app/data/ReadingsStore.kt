package com.ecoflowlogger.app.data

import com.ecoflowlogger.core.Reading
import org.json.JSONObject
import java.io.File

/**
 * Appends polled readings to a JSON-lines file in the app's private
 * storage (one JSON object per line) and reads them back for the
 * dashboard chart. Mirrors ecoflow_logger.logger's CSV-append approach --
 * a plain append-only file rather than a database, since this app has no
 * query needs beyond "give me everything, in order."
 */
class ReadingsStore(private val file: File) {

    @Synchronized
    fun append(timestampMillis: Long, reading: Reading) {
        val json = JSONObject().apply {
            put("timestampMillis", timestampMillis)
            putOrNull("socPercent", reading.socPercent)
            putOrNull("wattsIn", reading.wattsIn)
            putOrNull("wattsOut", reading.wattsOut)
            putOrNull("extraBatterySocPercent", reading.extraBatterySocPercent)
            putOrNull("extraBatteryWattsIn", reading.extraBatteryWattsIn)
            putOrNull("extraBatteryWattsOut", reading.extraBatteryWattsOut)
            putOrNull("pv1Watts", reading.pv1Watts)
            putOrNull("pv2Watts", reading.pv2Watts)
        }
        file.appendText(json.toString() + "\n")
    }

    @Synchronized
    fun readAll(): List<TimestampedReading> {
        if (!file.exists()) return emptyList()
        return file.readLines()
            .filter { it.isNotBlank() }
            .mapNotNull { line -> runCatching { parseLine(line) }.getOrNull() }
            .sortedBy { it.timestampMillis }
    }

    private fun parseLine(line: String): TimestampedReading {
        val json = JSONObject(line)
        return TimestampedReading(
            timestampMillis = json.getLong("timestampMillis"),
            reading = Reading(
                socPercent = json.getOrNull("socPercent"),
                wattsIn = json.getOrNull("wattsIn"),
                wattsOut = json.getOrNull("wattsOut"),
                extraBatterySocPercent = json.getOrNull("extraBatterySocPercent"),
                extraBatteryWattsIn = json.getOrNull("extraBatteryWattsIn"),
                extraBatteryWattsOut = json.getOrNull("extraBatteryWattsOut"),
                pv1Watts = json.getOrNull("pv1Watts"),
                pv2Watts = json.getOrNull("pv2Watts"),
            ),
        )
    }

    private fun JSONObject.putOrNull(key: String, value: Double?) {
        if (value != null) put(key, value) else put(key, JSONObject.NULL)
    }

    private fun JSONObject.getOrNull(key: String): Double? =
        if (isNull(key)) null else optDouble(key).takeUnless { it.isNaN() }
}

data class TimestampedReading(val timestampMillis: Long, val reading: Reading)
