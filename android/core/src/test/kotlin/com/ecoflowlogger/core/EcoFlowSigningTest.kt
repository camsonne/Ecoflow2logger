package com.ecoflowlogger.core

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlin.test.Test
import kotlin.test.assertEquals

private fun hmacHex(message: String, secret: String): String {
    val mac = Mac.getInstance("HmacSHA256")
    mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
    return mac.doFinal(message.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
}

class EcoFlowSigningTest {

    @Test
    fun signOrdersRequestParamsBeforeAuthParams() {
        // EcoFlow signs (sorted request params) + "&" + (sorted auth params),
        // not one big map of everything sorted together. Confirmed against
        // a known-working reference implementation and mirrors
        // ecoflow_logger/api.py's own regression test.
        val requestParams = mapOf("sn" to "SN1")
        val authParams = mapOf("accessKey" to "ak", "nonce" to "123", "timestamp" to "1000")
        val expected = hmacHex("sn=SN1&accessKey=ak&nonce=123&timestamp=1000", "secret")

        assertEquals(expected, EcoFlowSigning.sign(requestParams, authParams, "secret"))
    }

    @Test
    fun signWithNoRequestParamsUsesAuthParamsOnly() {
        val authParams = mapOf("accessKey" to "ak", "nonce" to "123", "timestamp" to "1000")
        val expected = hmacHex("accessKey=ak&nonce=123&timestamp=1000", "secret")

        assertEquals(expected, EcoFlowSigning.sign(emptyMap(), authParams, "secret"))
    }

    @Test
    fun signSortsWithinEachGroupIndependentOfInputOrder() {
        val a = EcoFlowSigning.sign(
            mapOf("b" to 2, "a" to 1),
            mapOf("z" to 1, "y" to 2),
            "secret",
        )
        val b = EcoFlowSigning.sign(
            mapOf("a" to 1, "b" to 2),
            mapOf("y" to 2, "z" to 1),
            "secret",
        )
        assertEquals(a, b)
    }

    @Test
    fun signFlattensNestedMaps() {
        val a = EcoFlowSigning.sign(emptyMap(), mapOf("outer" to mapOf("inner" to 1)), "secret")
        val b = EcoFlowSigning.sign(emptyMap(), mapOf("outer.inner" to 1), "secret")
        assertEquals(a, b)
    }
}
