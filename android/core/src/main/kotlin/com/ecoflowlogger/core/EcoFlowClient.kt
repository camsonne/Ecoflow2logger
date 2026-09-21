package com.ecoflowlogger.core

import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.security.SecureRandom

class EcoFlowApiException(message: String) : RuntimeException(message)

/**
 * Minimal client for the EcoFlow Open Platform API. Ported from
 * ecoflow_logger/api.py.
 */
class EcoFlowClient(
    private val accessKey: String,
    private val secretKey: String,
    private val baseUrl: String = DEFAULT_BASE_URL,
    private val httpClient: OkHttpClient = OkHttpClient(),
) {
    init {
        require(accessKey.isNotBlank() && secretKey.isNotBlank()) {
            "accessKey and secretKey are required"
        }
    }

    private fun authParams(): Map<String, String> {
        // A 6-digit nonce, matching EcoFlow's expected format. Drawn from
        // SecureRandom rather than a predictable PRNG since the nonce is
        // replay protection.
        val nonce = (100000 + SecureRandom().nextInt(900000)).toString()
        return mapOf(
            "accessKey" to accessKey,
            "nonce" to nonce,
            "timestamp" to System.currentTimeMillis().toString(),
        )
    }

    /**
     * Fetches every reported quota value for a device. Returns the flat
     * "data" map from the API, e.g. with keys such as "pd.soc",
     * "pd.wattsInSum" and "pd.wattsOutSum".
     */
    fun getAllQuota(deviceSn: String): Map<String, Any?> {
        val requestParams = mapOf("sn" to deviceSn)
        val auth = authParams()
        val sign = EcoFlowSigning.sign(requestParams, auth, secretKey)

        val urlBuilder = (baseUrl.trimEnd('/') + QUOTA_ALL_PATH).toHttpUrl().newBuilder()
        requestParams.forEach { (key, value) -> urlBuilder.addQueryParameter(key, value) }

        val requestBuilder = Request.Builder().url(urlBuilder.build())
        auth.forEach { (key, value) -> requestBuilder.addHeader(key, value) }
        requestBuilder.addHeader("sign", sign)

        httpClient.newCall(requestBuilder.build()).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("HTTP ${response.code} from EcoFlow API")
            }
            val body = response.body?.string() ?: throw IOException("Empty response body")
            val json = JSONObject(body)
            val code = json.opt("code")?.toString() ?: ""
            if (code != "0" && code != "0000") {
                throw EcoFlowApiException("EcoFlow API error (code=$code): ${json.optString("message")}")
            }
            return jsonObjectToMap(json.optJSONObject("data") ?: JSONObject())
        }
    }

    companion object {
        const val DEFAULT_BASE_URL = "https://api-e.ecoflow.com"
        private const val QUOTA_ALL_PATH = "/iot-open/sign/device/quota/all"
    }
}

private fun jsonObjectToMap(obj: JSONObject): Map<String, Any?> {
    val map = LinkedHashMap<String, Any?>()
    for (key in obj.keys()) {
        map[key] = jsonValueToAny(obj.get(key))
    }
    return map
}

private fun jsonValueToAny(value: Any?): Any? = when {
    value == null || value == JSONObject.NULL -> null
    value is JSONObject -> jsonObjectToMap(value)
    value is JSONArray -> (0 until value.length()).map { jsonValueToAny(value.get(it)) }
    // org.json returns Integer/Long for whole numbers but BigDecimal for
    // anything with a decimal point, which is an unpredictable type for
    // callers to handle consistently. Normalizing to Double here means
    // every numeric quota field looks the same regardless of how EcoFlow
    // happened to format it on the wire.
    value is Number -> value.toDouble()
    else -> value
}
