package com.ecoflowlogger.app.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.ecoflowlogger.core.EcoFlowClient

/**
 * Holds the user's own EcoFlow credentials and polling preferences.
 *
 * Backed by EncryptedSharedPreferences rather than plain SharedPreferences,
 * since the secret key is a live credential capable of authenticating
 * requests against the user's EcoFlow account -- it shouldn't sit in
 * plaintext on disk any more than a password would.
 */
class SettingsRepository(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "ecoflow_settings",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    var accessKey: String
        get() = prefs.getString(KEY_ACCESS_KEY, "") ?: ""
        set(value) = prefs.edit().putString(KEY_ACCESS_KEY, value).apply()

    var secretKey: String
        get() = prefs.getString(KEY_SECRET_KEY, "") ?: ""
        set(value) = prefs.edit().putString(KEY_SECRET_KEY, value).apply()

    var deviceSn: String
        get() = prefs.getString(KEY_DEVICE_SN, "") ?: ""
        set(value) = prefs.edit().putString(KEY_DEVICE_SN, value).apply()

    var baseUrl: String
        get() = prefs.getString(KEY_BASE_URL, EcoFlowClient.DEFAULT_BASE_URL) ?: EcoFlowClient.DEFAULT_BASE_URL
        set(value) = prefs.edit().putString(KEY_BASE_URL, value).apply()

    /** Android's WorkManager cannot run periodic work more often than 15 minutes. */
    var pollIntervalMinutes: Long
        get() = prefs.getLong(KEY_POLL_INTERVAL_MINUTES, 15L).coerceAtLeast(15L)
        set(value) = prefs.edit().putLong(KEY_POLL_INTERVAL_MINUTES, value.coerceAtLeast(15L)).apply()

    fun isConfigured(): Boolean = accessKey.isNotBlank() && secretKey.isNotBlank() && deviceSn.isNotBlank()

    companion object {
        private const val KEY_ACCESS_KEY = "access_key"
        private const val KEY_SECRET_KEY = "secret_key"
        private const val KEY_DEVICE_SN = "device_sn"
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_POLL_INTERVAL_MINUTES = "poll_interval_minutes"
    }
}
