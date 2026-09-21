package com.ecoflowlogger.app.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ListenableWorker.Result
import androidx.work.WorkerParameters
import com.ecoflowlogger.app.data.ReadingsStore
import com.ecoflowlogger.app.data.SettingsRepository
import com.ecoflowlogger.core.EcoFlowClient
import com.ecoflowlogger.core.Metrics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Polls the configured EcoFlow device once and appends the reading to
 * local storage. Scheduled periodically by WorkScheduler; also usable for
 * a manual "poll now" action from the UI.
 *
 * Errors are swallowed and reported as a WorkManager retry rather than a
 * permanent failure -- a single transient network error shouldn't stop
 * future scheduled polls, mirroring ecoflow_logger.logger's
 * error-tolerant polling loop.
 */
class PollWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val settings = SettingsRepository(applicationContext)
        if (!settings.isConfigured()) {
            return@withContext Result.failure()
        }

        return@withContext try {
            val client = EcoFlowClient(settings.accessKey, settings.secretKey, settings.baseUrl)
            val quota = client.getAllQuota(settings.deviceSn)
            val reading = Metrics.extractReading(quota)

            val store = ReadingsStore(File(applicationContext.filesDir, READINGS_FILE_NAME))
            store.append(System.currentTimeMillis(), reading)

            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    companion object {
        const val READINGS_FILE_NAME = "readings.jsonl"
        const val UNIQUE_WORK_NAME = "ecoflow_poll"
    }
}
