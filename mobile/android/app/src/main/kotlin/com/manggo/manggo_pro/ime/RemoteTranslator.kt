package com.manggo.manggo_pro.ime

import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import org.json.JSONArray

/**
 * 真实翻译（供输入法使用）。
 *
 * 之前这里只有一张手写词表，用户打任何没收录的句子都只会看到「未覆盖」，
 * 等于功能不可用。现在改为调用线上翻译接口；词表退化为**离线兜底**，
 * 只有网络失败时才查，避免把「网络挂了」误报成「这个词没收录」。
 *
 * 与 Flutter 侧的 lib/services/translation_service.dart 使用同一接口与同样的
 * 语言码映射，两端译文保持一致。
 */
object RemoteTranslator {

    private const val ENDPOINT =
        "https://translate.googleapis.com/translate_a/single"

    private const val TIMEOUT_MS = 12000

    /** 单次请求上限，超长按句切分 */
    private const val CHUNK_LIMIT = 1800

    /** 源文本含中日韩字符时译成英文，否则译成中文（自绘键盘只能打拉丁字母） */
    fun targetFor(text: String): String = if (hasCjk(text)) "en" else "zh-CN"

    private fun sourceFor(text: String): String = if (hasCjk(text)) "zh-CN" else "en"

    /**
     * 阻塞调用，**必须在子线程执行**。
     * @return 译文；失败返回 null（调用方负责提示）
     */
    fun translate(text: String): String? {
        val input = text.trim()
        if (input.isEmpty()) return null
        val source = sourceFor(input)
        val target = targetFor(input)

        val out = StringBuilder()
        for (chunk in split(input)) {
            val part = request(chunk, source, target) ?: return null
            if (out.isNotEmpty() && !out.endsWith("\n")) out.append(' ')
            out.append(part)
        }
        return out.toString().trim().ifEmpty { null }
    }

    /** 按句末标点切分，只在超长时才切 */
    private fun split(text: String): List<String> {
        if (text.length <= CHUNK_LIMIT) return listOf(text)
        val parts = mutableListOf<String>()
        val buf = StringBuilder()
        for (ch in text) {
            buf.append(ch)
            if ("。！？.!?\n".indexOf(ch) >= 0 && buf.length >= CHUNK_LIMIT / 3) {
                parts.add(buf.toString())
                buf.setLength(0)
            }
        }
        if (buf.isNotEmpty()) parts.add(buf.toString())

        val out = mutableListOf<String>()
        for (p in parts) {
            if (p.length <= CHUNK_LIMIT) {
                out.add(p)
            } else {
                var i = 0
                while (i < p.length) {
                    val end = minOf(i + CHUNK_LIMIT, p.length)
                    out.add(p.substring(i, end))
                    i = end
                }
            }
        }
        return out
    }

    private fun request(text: String, source: String, target: String): String? {
        var conn: HttpURLConnection? = null
        try {
            val body = listOf(
                "client" to "gtx",
                "sl" to source,
                "tl" to target,
                "dt" to "t",
                "q" to text
            ).joinToString("&") { (k, v) ->
                URLEncoder.encode(k, "UTF-8") + "=" + URLEncoder.encode(v, "UTF-8")
            }

            conn = (URL(ENDPOINT).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = TIMEOUT_MS
                readTimeout = TIMEOUT_MS
                doOutput = true
                setRequestProperty(
                    "Content-Type",
                    "application/x-www-form-urlencoded; charset=utf-8"
                )
                setRequestProperty("User-Agent", "ManggoPro/1.0 (Android)")
            }
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }

            if (conn.responseCode != 200) return null
            val raw = BufferedReader(InputStreamReader(conn.inputStream, Charsets.UTF_8))
                .use { it.readText() }

            return parse(raw)
        } catch (e: Exception) {
            return null
        } finally {
            conn?.disconnect()
        }
    }

    /** 响应形如 [[["译文","原文",null,...]],null,"en",...]，长句会分多段 */
    private fun parse(raw: String): String? = try {
        val data = JSONArray(raw)
        val segs = data.optJSONArray(0) ?: return null
        val sb = StringBuilder()
        for (i in 0 until segs.length()) {
            val seg = segs.optJSONArray(i) ?: continue
            val piece = seg.optString(0, "")
            if (piece.isNotEmpty()) sb.append(piece)
        }
        sb.toString().trim().ifEmpty { null }
    } catch (e: Exception) {
        null
    }

    private fun hasCjk(text: String): Boolean = text.any {
        it.code in 0x4E00..0x9FFF || it.code in 0x3400..0x4DBF
    }
}
