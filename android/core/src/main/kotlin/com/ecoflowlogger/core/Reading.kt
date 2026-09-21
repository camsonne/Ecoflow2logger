package com.ecoflowlogger.core

/**
 * Mirrors ecoflow_logger.metrics.Reading. Deliberately has no timestamp --
 * that's a polling-time concern, added by the caller, not something a
 * single quota snapshot carries.
 */
data class Reading(
    val socPercent: Double?,
    val wattsIn: Double?,
    val wattsOut: Double?,
    val extraBatterySocPercent: Double?,
    val extraBatteryWattsIn: Double?,
    val extraBatteryWattsOut: Double?,
    val pv1Watts: Double?,
    val pv2Watts: Double?,
)
