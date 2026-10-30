package com.manggo.manggo_pro

import android.content.Intent
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.view.inputmethod.InputMethodManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

class MainActivity : FlutterActivity() {

    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var pendingSpeak: Pair<String, String>? = null

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

            else -> result.notImplemented()
        }
    }

    private fun ensureTts() {
        if (tts != null) return
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
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL = "manggo/platform"
        private const val LEGACY_CHANNEL = "manggo/ime"
    }
}
