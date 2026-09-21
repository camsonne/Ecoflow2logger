package com.ecoflowlogger.app

import android.app.Application
import com.ecoflowlogger.app.data.SettingsRepository
import com.ecoflowlogger.app.work.WorkScheduler

class EcoFlowLoggerApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Re-arm periodic polling on process start (covers app updates and
        // WorkManager's own database being restored after a reboot). A
        // no-op if credentials haven't been entered yet -- there's nothing
        // useful to poll.
        val settings = SettingsRepository(this)
        if (settings.isConfigured()) {
            WorkScheduler.schedule(this, settings.pollIntervalMinutes)
        }
    }
}
