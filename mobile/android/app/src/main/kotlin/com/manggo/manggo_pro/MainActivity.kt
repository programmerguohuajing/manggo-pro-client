package com.manggo.manggo_pro

import android.content.Intent
import android.provider.Settings
import android.view.inputmethod.InputMethodManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // 供 Flutter 侧「设置 → Manggo 输入法」调用：
        // openImeSettings 打开系统输入法管理页，showImePicker 直接弹切换面板
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "openImeSettings" -> {
                        startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
                        result.success(true)
                    }
                    "showImePicker" -> {
                        val imm =
                            getSystemService(INPUT_METHOD_SERVICE) as? InputMethodManager
                        imm?.showInputMethodPicker()
                        result.success(imm != null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    companion object {
        private const val CHANNEL = "manggo/ime"
    }
}
