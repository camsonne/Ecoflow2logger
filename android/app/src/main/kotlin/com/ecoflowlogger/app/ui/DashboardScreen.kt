package com.ecoflowlogger.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.ecoflowlogger.app.data.ReadingsStore
import com.ecoflowlogger.app.data.TimestampedReading
import com.ecoflowlogger.app.work.PollWorker
import kotlin.math.roundToInt

private data class Stat(val label: String, val value: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(readingsStore: ReadingsStore, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    var readings by remember { mutableStateOf<List<TimestampedReading>>(emptyList()) }

    // Reloads once on first composition. A background poll writes to the
    // same file independently of this screen's lifecycle; the manual
    // refresh button below is the deliberate way to pick that up rather
    // than polling the file on a timer.
    LaunchedEffect(Unit) {
        readings = readingsStore.readAll()
    }

    val latest = readings.lastOrNull()?.reading

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("EcoFlow Logger") },
                actions = {
                    IconButton(onClick = { readings = readingsStore.readAll() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
                    }
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize().padding(16.dp)) {
            if (readings.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "No readings yet. Poll now, or wait for the next scheduled poll.",
                        textAlign = TextAlign.Center,
                    )
                }
                return@Column
            }

            val stats = buildList {
                add(Stat("Charge", latest?.socPercent?.let { "${it.roundToInt()}%" } ?: "–"))
                add(Stat("Power in", latest?.wattsIn?.let { "${it.roundToInt()} W" } ?: "–"))
                add(Stat("Power out", latest?.wattsOut?.let { "${it.roundToInt()} W" } ?: "–"))
                if (latest?.extraBatterySocPercent != null) {
                    add(Stat("Extra battery", "${latest.extraBatterySocPercent.roundToInt()}%"))
                }
                if (latest?.pv1Watts != null || latest?.pv2Watts != null) {
                    add(Stat("Solar 1", latest.pv1Watts?.let { "${it.roundToInt()} W" } ?: "–"))
                    add(Stat("Solar 2", latest.pv2Watts?.let { "${it.roundToInt()} W" } ?: "–"))
                }
            }

            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(vertical = 8.dp),
                modifier = Modifier.height(if (stats.size > 4) 220.dp else 120.dp),
            ) {
                items(stats) { stat -> StatTile(stat) }
            }

            SocChart(
                readings = readings,
                modifier = Modifier.fillMaxWidth().height(200.dp).padding(top = 16.dp),
            )

            Button(
                onClick = {
                    val request = OneTimeWorkRequestBuilder<PollWorker>().build()
                    WorkManager.getInstance(context).enqueue(request)
                },
                modifier = Modifier.padding(top = 16.dp),
            ) {
                Text("Poll now")
            }
        }
    }
}

@Composable
private fun StatTile(stat: Stat) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(stat.label, style = androidx.compose.material3.MaterialTheme.typography.labelMedium)
            Text(stat.value, style = androidx.compose.material3.MaterialTheme.typography.headlineSmall)
        }
    }
}

@Composable
private fun SocChart(readings: List<TimestampedReading>, modifier: Modifier = Modifier) {
    val points = readings.mapNotNull { r -> r.reading.socPercent?.let { r.timestampMillis to it } }
    Canvas(modifier) {
        if (points.size < 2) return@Canvas
        val minTime = points.first().first.toFloat()
        val maxTime = points.last().first.toFloat().coerceAtLeast(minTime + 1f)

        fun xFor(t: Long) = (t.toFloat() - minTime) / (maxTime - minTime) * size.width
        fun yFor(soc: Double) = size.height - (soc.toFloat() / 100f) * size.height

        for (i in 1 until points.size) {
            val (t0, soc0) = points[i - 1]
            val (t1, soc1) = points[i]
            drawLine(
                color = Color(0xFF2A78D6),
                start = Offset(xFor(t0), yFor(soc0)),
                end = Offset(xFor(t1), yFor(soc1)),
                strokeWidth = 4f,
            )
        }
    }
}
