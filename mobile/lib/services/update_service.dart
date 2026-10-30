import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:manggo_pro/services/platform_service.dart';

/// 一个可用的新版本
class UpdateInfo {
  final String versionName;
  final int versionCode;
  final String apkUrl;
  final String apkName;
  final int size;
  final String sha256;
  final String notes;
  final String publishedAt;

  const UpdateInfo({
    required this.versionName,
    required this.versionCode,
    required this.apkUrl,
    required this.apkName,
    required this.size,
    required this.sha256,
    required this.notes,
    required this.publishedAt,
  });

  String get sizeText =>
      size <= 0 ? '' : '${(size / 1024 / 1024).toStringAsFixed(1)} MB';

  factory UpdateInfo.fromJson(Map<String, dynamic> json) => UpdateInfo(
        versionName: json['versionName'] as String? ?? '',
        versionCode: (json['versionCode'] as num?)?.toInt() ?? 0,
        apkUrl: json['apkUrl'] as String? ?? '',
        apkName: json['apkName'] as String? ?? 'manggo-update.apk',
        size: (json['size'] as num?)?.toInt() ?? 0,
        sha256: json['sha256'] as String? ?? '',
        notes: json['notes'] as String? ?? '',
        publishedAt: json['publishedAt'] as String? ?? '',
      );
}

/// 检查更新的结果
class UpdateCheck {
  final UpdateInfo? info;
  final int currentCode;
  final String currentName;
  final String? error;

  const UpdateCheck({
    this.info,
    required this.currentCode,
    required this.currentName,
    this.error,
  });

  bool get hasUpdate => info != null && info!.versionCode > currentCode;
  bool get failed => error != null;
}

/// 在线更新。
///
/// 发布侧：GitHub Releases 的滚动 tag `android-latest`，资产含 `version.json`
/// 与 APK（见 .github/workflows/android.yml）。
///
/// 国内网络问题：github.com / objects.githubusercontent.com 直连经常超时，
/// 所以这里维护一组**加速镜像前缀**，把原始地址接在前缀后面即可。
/// 检查更新时多家并发竞速，谁先成功用谁；下载时优先复用刚命中的那家，
/// 失败再依次回退，避免让用户看到一次必然超时的等待。
class UpdateService {
  UpdateService._();

  /// 仓库与发布信息。改仓库/换自建 CDN 只需动这里。
  static const String repo = 'programmerguohuajing/manggo-pro-client';
  static const String releaseTag = 'android-latest';
  static const String _versionUrl =
      'https://github.com/$repo/releases/download/$releaseTag/version.json';

  /// 加速前缀，空串表示直连。国内优先走前几个镜像。
  ///
  /// 2026-10 实测（直连、不走系统代理）：8 个常见公共加速站里只有
  /// gh-proxy.com 返回 200，其余 ghfast / ghproxy.net / moeyy / gitmirror
  /// 等均已失效或不可达。公共镜像本身寿命有限，所以这里：
  /// 1) 保留多家做冗余，任一可用即可，不做单点依赖；
  /// 2) 检查更新时并发竞速，靠前的挂了也不会拖慢整体；
  /// 3) [_preferred] 记住本次成功的那家，后续下载直接复用。
  ///
  /// 要换成自有 CDN（例如 Cloudflare R2 / 对象存储），改这个列表即可，
  /// 只要能以 `<前缀><原始 GitHub URL>` 的形式代理下载就行。
  static const List<String> mirrors = <String>[
    'https://gh-proxy.com/',
    'https://ghfast.top/',
    'https://ghproxy.net/',
    'https://github.moeyy.xyz/',
    '',
  ];

  static const Duration _probeTimeout = Duration(seconds: 8);

  /// 上一次成功的镜像前缀，下载时优先使用
  static String _preferred = '';

  static String mirrorName(String prefix) {
    if (prefix.isEmpty) return 'GitHub 直连';
    final host = Uri.tryParse(prefix)?.host ?? prefix;
    return host;
  }

  /// 把原始地址套上镜像前缀
  static String proxied(String url, String prefix) => '$prefix$url';

  // ---------------- 检查更新 ----------------

  static Future<UpdateCheck> check() async {
    final v = await PlatformService.appVersion();
    if (v == null) {
      return const UpdateCheck(
        currentCode: 0,
        currentName: '',
        error: '当前平台暂不支持在线更新',
      );
    }

    // 多家镜像并发竞速，取第一个成功解析的结果
    final fetched = await _race(versionUrl: _versionUrl);
    if (fetched == null) {
      return UpdateCheck(
        currentCode: v.code,
        currentName: v.name,
        error: '检查更新失败，请检查网络（已尝试 ${mirrors.length} 个更新源）',
      );
    }

    return UpdateCheck(
      info: fetched.info,
      currentCode: v.code,
      currentName: v.name,
    );
  }

  static Future<({UpdateInfo info, String mirror})?> _race({
    required String versionUrl,
  }) async {
    final completer = Completer<({UpdateInfo info, String mirror})?>();
    var pending = mirrors.length;

    // 必须带 cache buster：加速镜像普遍会缓存 version.json（实测加上
    // Cache-Control: no-cache 请求头无效，镜像直接忽略），不加的话发版后
    // 很长一段时间仍会读到旧版本号，用户永远收不到更新。
    final bust = DateTime.now().millisecondsSinceEpoch;

    for (final prefix in mirrors) {
      _fetchJson('${proxied(versionUrl, prefix)}?t=$bust')
          .then((info) {
            if (info != null && !completer.isCompleted) {
              _preferred = prefix;
              completer.complete((info: info, mirror: prefix));
            }
          })
          .catchError((_) {})
          .whenComplete(() {
            pending -= 1;
            // 全部失败才认定失败；成功的已在上面 complete
            if (pending == 0 && !completer.isCompleted) {
              completer.complete(null);
            }
          });
    }

    return completer.future
        .timeout(const Duration(seconds: 20))
        .catchError((Object _) => null);
  }

  static Future<UpdateInfo?> _fetchJson(String url) async {
    final client = HttpClient()..connectionTimeout = _probeTimeout;
    try {
      final req = await client.getUrl(Uri.parse(url)).timeout(_probeTimeout);
      req.headers.set('User-Agent', 'ManggoPro/1.0 (Flutter)');
      // 镜像会缓存，加个随机参数避免拿到旧的版本号
      req.headers.set('Cache-Control', 'no-cache');
      final res = await req.close().timeout(_probeTimeout);
      if (res.statusCode != 200) return null;
      final body =
          await res.transform(utf8.decoder).join().timeout(_probeTimeout);
      final json = jsonDecode(body);
      if (json is! Map<String, dynamic>) return null;
      final info = UpdateInfo.fromJson(json);
      return info.apkUrl.isEmpty ? null : info;
    } catch (_) {
      return null;
    } finally {
      client.close(force: true);
    }
  }

  // ---------------- 下载 ----------------

  /// 下载 APK 到缓存目录并校验。
  ///
  /// [onProgress] 回调 (已下载字节, 总字节, 当前镜像名)。
  /// 返回本地文件路径；失败返回 null 并给出 [error]。
  static Future<({String? path, String? error})> download(
    UpdateInfo info, {
    void Function(int received, int total, String mirror)? onProgress,
  }) async {
    final dir = Directory('${Directory.systemTemp.path}/updates');
    if (!await dir.exists()) await dir.create(recursive: true);
    final file = File('${dir.path}/${info.apkName}');

    // 优先上次命中的镜像，其余按原顺序补位
    final order = <String>[
      if (_preferred.isNotEmpty) _preferred,
      ...mirrors.where((m) => m != _preferred),
    ];

    final urlsToTry = [info.apkUrl];
    String lastError = '下载失败';
    for (final prefix in order) {
      for (final raw in urlsToTry) {
        final url = proxied(raw, prefix);
        final name = mirrorName(prefix);
        try {
          final ok = await _downloadOne(url, file, info.size, (r, t) {
            onProgress?.call(r, t, name);
          });
          if (!ok) {
            lastError = '$name 下载中断';
            continue;
          }
          // 校验哈希：镜像有时会返回错误页/旧文件
          if (info.sha256.isNotEmpty) {
            final actual = await PlatformService.sha256(file.path);
            if (actual != null &&
                actual.toLowerCase() != info.sha256.toLowerCase()) {
              lastError = '$name 校验失败';
              await file.delete().catchError((_) => file);
              continue;
            }
          }
          _preferred = prefix;
          return (path: file.path, error: null);
        } catch (e) {
          lastError = '$name：$e';
        }
      }
    }
    return (path: null, error: '下载失败（$lastError）');
  }

  static Future<bool> _downloadOne(
    String url,
    File target,
    int expectedSize,
    void Function(int, int) onProgress,
  ) async {
    final client = HttpClient()..connectionTimeout = _probeTimeout;
    IOSink? sink;
    try {
      final req = await client.getUrl(Uri.parse(url)).timeout(_probeTimeout);
      req.headers.set('User-Agent', 'ManggoPro/1.0 (Flutter)');
      final res = await req.close().timeout(_probeTimeout);
      if (res.statusCode != 200) return false;

      final total = res.contentLength > 0
          ? res.contentLength
          : (expectedSize > 0 ? expectedSize : 0);

      var received = 0;
      sink = target.openWrite();
      await for (final chunk in res) {
        sink.add(chunk);
        received += chunk.length;
        onProgress(received, total);
      }
      await sink.flush();
      await sink.close();
      sink = null;

      if (total > 0 && received < total) return false;
      return received > 0;
    } catch (_) {
      return false;
    } finally {
      await sink?.close().catchError((_) {});
      client.close(force: true);
    }
  }

  /// 清理上次残留的安装包
  static Future<void> cleanCache() async {
    final dir = Directory('${Directory.systemTemp.path}/updates');
    if (await dir.exists()) {
      await dir.delete(recursive: true).catchError((_) => dir);
    }
  }
}
