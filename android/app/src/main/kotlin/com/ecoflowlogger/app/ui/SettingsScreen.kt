package com.ecoflowlogger.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.ecoflowlogger.app.data.SettingsRepository
import com.ecoflowlogger.app.work.WorkScheduler
import com.ecoflowlogger.core.EcoFlowClient

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(settings: SettingsRepository, onDone: () -> Unit) {
    val context = LocalContext.current
    var accessKey by remember { mutableStateOf(settings.accessKey) }
    var secretKey by remember { mutableStateOf(settings.secretKey) }
    var deviceSn by remember { mutableStateOf(settings.deviceSn) }
    var baseUrl by remember { mutableStateOf(settings.baseUrl) }
    var pollIntervalMinutes by remember { mutableStateOf(settings.pollIntervalMinutes.toString()) }

    Scaffold(topBar = { TopAppBar(title = { Text("Settings") }) }) { padding ->
        Column(
            Modifier.padding(padding).fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Your EcoFlow Open API access key, secret key and device serial " +
                    "number, from the EcoFlow IoT developer portal. These are stored " +
                    "encrypted on this device only and never sent anywhere except " +
                    "directly to EcoFlow's API.",
            )

            OutlinedTextField(
                value = accessKey,
                onValueChange = { accessKey = it },
                label = { Text("Access key") },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = secretKey,
                onValueChange = { secretKey = it },
                label = { Text("Secret key") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = deviceSn,
                onValueChange = { deviceSn = it },
                label = { Text("Device serial number") },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = baseUrl,
                onValueChange = { baseUrl = it },
                label = { Text("API base URL (region)") },
                supportingText = {
                    Text(
                        "Default is Europe (${EcoFlowClient.DEFAULT_BASE_URL}). " +
                            "Use https://api-a.ecoflow.com for the Americas if you get " +
                            "an 'accessKey is invalid' error.",
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = pollIntervalMinutes,
                onValueChange = { pollIntervalMinutes = it.filter(Char::isDigit) },
                label = { Text("Poll interval (minutes)") },
                supportingText = { Text("Android won't run background polling more often than every 15 minutes.") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )

            Button(
                onClick = {
                    settings.accessKey = accessKey.trim()
                    settings.secretKey = secretKey.trim()
                    settings.deviceSn = deviceSn.trim()
                    settings.baseUrl = baseUrl.trim().ifBlank { EcoFlowClient.DEFAULT_BASE_URL }
                    settings.pollIntervalMinutes = pollIntervalMinutes.toLongOrNull() ?: 15L

                    if (settings.isConfigured()) {
                        WorkScheduler.schedule(context, settings.pollIntervalMinutes)
                    }
                    onDone()
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Save")
            }
        }
    }
}
