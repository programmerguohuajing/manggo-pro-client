package com.manggo.manggo_pro

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.view.inputmethod.InputMethodManager
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.MessageDigest
import java.util.Locale

class MainActivity : FlutterActivity() {

    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var pendingSpeak: Pair<String, String>? = null

    /** 安装包哈希要读整个文件（几十 MB），不能占主线程 */
    private val ioExecutor = java.util.concurrent.Executors.newSingleThreadExecutor()

    /** 流式计算 SHA-256，避免把整个 APK 读进内存 */
    private fun sha256Of(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buf = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buf)
                if (n <= 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // manggo/platform：语音播报、系统分享、输入法设置
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result -> handle(call, result) }

        // 旧通道，保留兼容
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, LEGACY_CHANNEL)
            .setMethodCallHandler { call, result -> handle(call, result) }
    }

    private fun handle(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "openImeSettings" -> {
                startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
                result.success(true)
            }

            "showImePicker" -> {
                val imm = getSystemService(INPUT_METHOD_SERVICE) as? InputMethodManager
                imm?.showInputMethodPicker()
                result.success(imm != null)
            }

            "speak" -> {
                val text = call.argument<String>("text").orEmpty()
                val lang = call.argument<String>("lang").orEmpty()
                if (text.isEmpty()) {
                    result.success(false)
                } else {
                    ensureTts()
                    if (ttsReady) {
                        doSpeak(text, lang)
                    } else {
                        pendingSpeak = text to lang
                    }
                    result.success(true)
                }
            }

            "stopSpeak" -> {
                tts?.stop()
                result.success(true)
            }

            "share" -> {
                val text = call.argument<String>("text").orEmpty()
                val subject = call.argument<String>("subject").orEmpty()
                if (text.isEmpty()) {
                    result.success(false)
                } else {
                    val send = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, text)
                        if (subject.isNotEmpty()) putExtra(Intent.EXTRA_SUBJECT, subject)
                    }
                    startActivity(Intent.createChooser(send, "分享"))
                    result.success(true)
                }
            }

            // ---- 在线更新 ----

            "appVersion" -> {
                val info = packageManager.getPackageInfo(packageName, 0)
                val code = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    info.longVersionCode.toInt()
                } else {
                    @Suppress("DEPRECATION")
                    info.versionCode
                }
                result.success(mapOf(
                    "versionCode" to code,
                    "versionName" to (info.versionName ?: ""),
                ))
            }

            "sha256" -> {
                val path = call.argument<String>("path").orEmpty()
                ioExecutor.execute {
                    val digest = runCatching { sha256Of(File(path)) }.getOrNull()
                    runOnUiThread { result.success(digest) }
                }
            }

            "canInstallPackages" -> {
                val ok = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    packageManager.canRequestPackageInstalls()
                } else {
                    true
                }
                result.success(ok)
            }

            "openInstallPermission" -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startActivity(
                        Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                            .setData(Uri.parse("package:$packageName"))
                    )
                }
                result.success(true)
            }

            "installApk" -> {
                val path = call.argument<String>("path").orEmpty()
                val src = File(path)
                if (!src.exists() || src.length() == 0L) {
                    result.error("NO_FILE", "安装包不存在或为空：$path", null)
                } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                    !packageManager.canRequestPackageInstalls()
                ) {
                    // 未授予「安装未知应用」权限，安装器会被系统拦掉
                    result.success("need_permission")
                } else {
                    try {
                        // 统一复制到 FileProvider 明确声明过的 cacheDir/updates/。
                        // Dart 侧用的 Directory.systemTemp 不保证等于 cacheDir，
                        // 路径对不上时 getUriForFile 会直接抛 IllegalArgumentException。
                        val dir = File(cacheDir, "updates").apply { mkdirs() }
                        val dst = File(dir, "update.apk")
                        src.copyTo(dst, overwrite = true)

                        val uri = FileProvider.getUriForFile(
                            this, "$packageName.fileprovider", dst
                        )
                        startActivity(
                            Intent(Intent.ACTION_VIEW).apply {
                                setDataAndType(
                                    uri, "application/vnd.android.package-archive"
                                )
                                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            }
                        )
                        result.success("ok")
                    } catch (e: Exception) {
                        result.success("err:${e.javaClass.simpleName}: ${e.message}")
                    }
                }
            }

            else -> result.notImplemented()
        }
    }

    private fun ensureTts() {        if (tts != null) return
        tts = TextToSpeech(applicationContext) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            val pending = pendingSpeak
            if (ttsReady && pending != null) {
                pendingSpeak = null
                doSpeak(pending.first, pending.second)
            }
        }
    }

    private fun doSpeak(text: String, lang: String) {
        val engine = tts ?: return
        val tag = lang.ifEmpty { "en" }
        engine.setLanguage(Locale.forLanguageTag(tag))
        engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "manggo")
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
        ioExecutor.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL = "manggo/platform"
        private const val LEGACY_CHANNEL = "manggo/ime"
    }
}
