package com.ecoflowlogger.core

import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class EcoFlowClientTest {

    @Test
    fun getAllQuotaParsesSuccessfulResponse() {
        val server = MockWebServer()
        server.enqueue(
            MockResponse().setBody(
                """{"code":"0","message":"success","data":{"pd.soc":87,"pd.wattsInSum":120.5,"nested":{"inner":[1,2]}}}""",
            ),
        )
        server.start()
        try {
            val client = EcoFlowClient("ak", "sk", baseUrl = server.url("/").toString())
            val data = client.getAllQuota("SN123")

            // Numeric quota values are normalized to Double regardless of
            // whether they arrived on the wire as a whole number or a
            // decimal -- see the comment on jsonValueToAny.
            assertEquals(87.0, data["pd.soc"])
            assertEquals(120.5, data["pd.wattsInSum"])
            @Suppress("UNCHECKED_CAST")
            val nested = data["nested"] as Map<String, Any?>
            assertEquals(listOf(1.0, 2.0), nested["inner"])

            val request = server.takeRequest()
            assertTrue(request.path!!.contains("/iot-open/sign/device/quota/all"))
            assertTrue(request.path!!.contains("sn=SN123"))
            assertEquals("ak", request.getHeader("accessKey"))
            assertTrue(request.getHeader("sign")!!.isNotEmpty())
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun getAllQuotaThrowsOnApiErrorCode() {
        val server = MockWebServer()
        server.enqueue(
            MockResponse().setBody("""{"code":"8513","message":"accessKey is invalid"}"""),
        )
        server.start()
        try {
            val client = EcoFlowClient("ak", "sk", baseUrl = server.url("/").toString())
            val exception = assertFailsWith<EcoFlowApiException> { client.getAllQuota("SN123") }
            assertTrue(exception.message!!.contains("8513"))
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun constructorRejectsBlankCredentials() {
        assertFailsWith<IllegalArgumentException> { EcoFlowClient("", "sk") }
        assertFailsWith<IllegalArgumentException> { EcoFlowClient("ak", "") }
    }
}
