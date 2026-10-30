import 'package:flutter/foundation.dart';

/// 骨架期的轻量全局设置（内存单例）。
/// 后续接 shared_preferences 时，只需在这里读写持久化即可，调用方不用改。
class AppSettings {
  AppSettings._();

  /// 语音播报总开关，设置页与各处的喇叭按钮共享同一份状态
  static final ValueNotifier<bool> speechEnabled = ValueNotifier<bool>(true);
}
