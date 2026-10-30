import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:manggo_pro/app_theme.dart';

/// OCR 拍照/选图：取景框 + 快门。真实实现接入相机插件（camera / ohos 相机能力）。
class OcrScreen extends StatelessWidget {
  const OcrScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // 状态栏高度：深色背景要铺到状态栏之后，只让文字内容避让
    final topInset = MediaQuery.of(context).padding.top;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      // 相机页恒为深色底，状态栏固定用浅色图标（覆盖全局按主题的设置）
      value: SystemUiOverlayStyle.light,
      child: Stack(
        children: [
          // 取景背景
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0E140D), Color(0xFF0A0D09)],
              ),
            ),
          ),
          // 取景框
          Center(
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white54, width: 2),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Center(
                child: Text('将文本放入框内',
                    style: TextStyle(color: Colors.white70, fontSize: 14)),
              ),
            ),
          ),
          // 顶部提示
          Positioned(
            top: topInset + 12,
            left: 0,
            right: 0,
            child: Center(
              child: Text('拍照取词 / 从相册选图',
                  style: TextStyle(color: Colors.white70, fontSize: 14)),
            ),
          ),
          // 快门
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Center(
              child: GestureDetector(
                onTap: () => _toast(context, '相机能力待接入：iOS/Android 需授权后调用原生拍照'),
                child: Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    border: Border.all(color: Manggo.accent, width: 4),
                  ),
                  child: const Icon(Icons.camera_alt_rounded,
                      size: 28, color: Colors.black87),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _toast(BuildContext context, String message) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(
      content: Text(message),
      duration: const Duration(milliseconds: 1800),
      behavior: SnackBarBehavior.floating,
    ));
  }
}
