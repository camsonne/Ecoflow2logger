package com.ecoflowlogger.core

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * HMAC-SHA256 request signing for the EcoFlow Open Platform API.
 *
 * EcoFlow sorts the request params and the auth params (accessKey/nonce/
 * timestamp) *separately* and concatenates the two query strings -- request
 * params first -- rather than merging everything into one map and sorting
 * the combined set. Ported from the reference Python implementation
 * (ecoflow_logger/api.py), which was itself verified against a real
 * DELTA 2 Max account.
 */
object EcoFlowSigning {

    fun sign(requestParams: Map<String, Any?>, authParams: Map<String, Any?>, secretKey: String): String {
        val parts = mutableListOf<String>()
        if (requestParams.isNotEmpty()) parts += queryString(requestParams)
        parts += queryString(authParams)
        val signStr = parts.joinToString("&")

        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secretKey.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        return mac.doFinal(signStr.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }

    /**
     * Flattens nested maps/lists the way EcoFlow's signing scheme expects.
     * Nested map keys become "parent.child" and list items become
     * "parent[0]". Only used for request bodies with nested params; the
     * quota-all GET request this app makes has none.
     */
    @Suppress("UNCHECKED_CAST")
    private fun flatten(params: Map<String, Any?>, prefix: String = ""): Map<String, Any?> {
        val flat = LinkedHashMap<String, Any?>()
        for ((key, value) in params) {
            val fullKey = if (prefix.isEmpty()) key else "$prefix.$key"
            when (value) {
                is Map<*, *> -> flat.putAll(flatten(value as Map<String, Any?>, fullKey))
                is List<*> -> value.forEachIndexed { i, item ->
                    if (item is Map<*, *>) {
                        flat.putAll(flatten(item as Map<String, Any?>, "$fullKey[$i]"))
                    } else {
                        flat["$fullKey[$i]"] = item
                    }
                }
                else -> flat[fullKey] = value
            }
        }
        return flat
    }

    private fun queryString(params: Map<String, Any?>): String {
        val flat = flatten(params)
        return flat.keys.sorted().joinToString("&") { key -> "$key=${flat[key]}" }
    }
}
