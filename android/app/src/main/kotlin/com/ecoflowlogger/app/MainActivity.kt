package com.ecoflowlogger.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.ecoflowlogger.app.data.ReadingsStore
import com.ecoflowlogger.app.data.SettingsRepository
import com.ecoflowlogger.app.ui.DashboardScreen
import com.ecoflowlogger.app.ui.SettingsScreen
import com.ecoflowlogger.app.ui.theme.EcoFlowLoggerTheme
import com.ecoflowlogger.app.work.PollWorker
import java.io.File

private enum class Screen { Dashboard, Settings }

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val settings = SettingsRepository(applicationContext)
        val readingsStore = ReadingsStore(File(applicationContext.filesDir, PollWorker.READINGS_FILE_NAME))

        setContent {
            EcoFlowLoggerTheme {
                var screen by remember {
                    mutableStateOf(if (settings.isConfigured()) Screen.Dashboard else Screen.Settings)
                }

                when (screen) {
                    Screen.Dashboard -> DashboardScreen(
                        readingsStore = readingsStore,
                        onOpenSettings = { screen = Screen.Settings },
                    )
                    Screen.Settings -> SettingsScreen(
                        settings = settings,
                        onDone = { screen = Screen.Dashboard },
                    )
                }
            }
        }
    }
}
