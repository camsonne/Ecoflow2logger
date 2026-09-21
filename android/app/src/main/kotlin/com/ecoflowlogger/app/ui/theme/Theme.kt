package com.ecoflowlogger.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val EcoFlowBlue = Color(0xFF2A78D6)

private val LightColors = lightColorScheme(primary = EcoFlowBlue)
private val DarkColors = darkColorScheme(primary = EcoFlowBlue)

@Composable
fun EcoFlowLoggerTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
