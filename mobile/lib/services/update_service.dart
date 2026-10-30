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
    final r = await _race(versionUrl: _versionUrl);
    if (r.info == null) {
      return UpdateCheck(
        currentCode: v.code,
        currentName: v.name,
        error: '检查更新失败。${r.detail}',
      );
    }

    return UpdateCheck(
      info: r.info,
      currentCode: v.code,
      currentName: v.name,
    );
  }

  /// 竞速结果。[detail] 在失败时汇总每个源的具体原因——
  /// 只说「请检查网络」没法判断到底是断网、镜像挂了还是被墙。
  static Future<({UpdateInfo? info, String detail})> _race({
    required String versionUrl,
  }) async {
    final completer = Completer<UpdateInfo?>();
    final errors = <String>[];
    var pending = mirrors.length;

    // 必须带 cache buster：加速镜像普遍会缓存 version.json（实测加上
    // Cache-Control: no-cache 请求头无效，镜像直接忽略），不加的话发版后
    // 很长一段时间仍会读到旧版本号，用户永远收不到更新。
    final bust = DateTime.now().millisecondsSinceEpoch;

    for (final prefix in mirrors) {
      final name = mirrorName(prefix);
      _fetchJson('${proxied(versionUrl, prefix)}?t=$bust', name).then((res) {
        if (res.info != null && !completer.isCompleted) {
          _preferred = prefix;
          completer.complete(res.info);
        } else if (res.err != null) {
          errors.add('$name（${res.err}）');
        }
      }).catchError((Object e) {
        errors.add('$name（$e）');
      }).whenComplete(() {
        pending -= 1;
        // 全部失败才认定失败；成功的已在上面 complete
        if (pending == 0 && !completer.isCompleted) {
          completer.complete(null);
        }
      });
    }

    UpdateInfo? info;
    try {
      info = await completer.future.timeout(const Duration(seconds: 12));
    } catch (_) {
      info = null;
    }
    if (info != null) return (info: info, detail: '');

    final detail = errors.isEmpty
        ? '已尝试 ${mirrors.length} 个更新源，均无响应'
        : '已尝试 ${mirrors.length} 个更新源：${errors.join('、')}';
    return (info: null, detail: detail);
  }

  static Future<({UpdateInfo? info, String? err})> _fetchJson(
    String url,
    String mirrorLabel,
  ) async {
    final client = HttpClient()..connectionTimeout = _probeTimeout;
    try {
      final req = await client.getUrl(Uri.parse(url)).timeout(_probeTimeout);
      req.headers.set('User-Agent', 'ManggoPro/1.0 (Flutter)');
      final res = await req.close().timeout(_probeTimeout);
      if (res.statusCode != 200) {
        return (info: null, err: 'HTTP ${res.statusCode}');
      }
      final body =
          await res.transform(utf8.decoder).join().timeout(_probeTimeout);
      final json = jsonDecode(body);
      if (json is! Map<String, dynamic>) {
        return (info: null, err: '返回格式异常');
      }
      final info = UpdateInfo.fromJson(json);
      if (info.apkUrl.isEmpty) return (info: null, err: '缺少 apkUrl');
      return (info: info, err: null);
    } on TimeoutException {
      return (info: null, err: '超时');
    } on HandshakeException {
      return (info: null, err: 'TLS 握手失败');
    } on SocketException {
      return (info: null, err: '无法连接');
    } on FormatException {
      return (info: null, err: 'JSON 解析失败');
    } catch (e) {
      return (info: null, err: '$e');
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

    // 清掉上一版残留的包，避免缓存堆积
    await for (final entity in dir.list()) {
      if (entity is File &&
          entity.path.endsWith('.apk') &&
          !entity.path.endsWith(info.apkName)) {
        await entity.delete().catchError((_) => entity);
      }
    }

    // 优先上次命中的镜像，其余按原顺序补位
    final order = <String>[
      if (_preferred.isNotEmpty) _preferred,
      ...mirrors.where((m) => m != _preferred),
    ];

    final urlsToTry = [info.apkUrl];
    String lastError = '下载失败';
    for (final prefix in order) {
      final name = mirrorName(prefix);
      // 同一个源重试两次：国内链路下几十 MB 的包断流很常见，
      // 配合断点续传，重试通常能把剩下的部分补齐。
      for (var attempt = 0; attempt < 3; attempt++) {
        for (final raw in urlsToTry) {
          final url = proxied(raw, prefix);
          try {
            final ok = await _downloadOne(url, file, info.size, (r, t) {
              onProgress?.call(r, t, name);
            });
            if (!ok) {
              lastError = '$name 下载中断';
              continue;
            }
            // 校验哈希：镜像有时会返回错误页/旧文件，断点续传也可能拼错
            if (info.sha256.isNotEmpty) {
              final actual = await PlatformService.sha256(file.path);
              if (actual != null &&
                  actual.toLowerCase() != info.sha256.toLowerCase()) {
                lastError = '$name 校验失败';
                await file.delete().catchError((_) => file);
                break;
              }
            }
            _preferred = prefix;
            return (path: file.path, error: null);
          } catch (e) {
            lastError = '$name：$e';
          }
        }
        // 还有进度就继续续传，否则换下一个源
        final got = await file.exists() ? await file.length() : 0;
        if (got >= info.size && info.size > 0) break;
        await Future<void>.delayed(const Duration(seconds: 2));
      }
    }
    return (path: null, error: '下载失败（$lastError）');
  }

  /// 下载单个源，支持断点续传。
  ///
  /// 已下载的部分用 `Range: bytes=<n>-` 请求剩余内容；服务端返回 206 就追加写，
  /// 返回 200 说明不支持分段，只能整包重来。跨源也保留已下载部分——
  /// 最终有 sha256 兜底，续传错了会被校验拦下来。
  static Future<bool> _downloadOne(
    String url,
    File target,
    int expectedSize,
    void Function(int, int) onProgress,
  ) async {
    final client = HttpClient()
      ..connectionTimeout = _probeTimeout
      // 默认 idleTimeout 15s，慢速链路下容易被判空闲而掐断
      ..idleTimeout = const Duration(seconds: 60);
    IOSink? sink;
    try {
      final existing = await target.exists() ? await target.length() : 0;
      // 已经下满（上次下完但没装成）：不再发请求，交给上层做 sha 校验
      if (expectedSize > 0 && existing >= expectedSize) return true;

      final req = await client.getUrl(Uri.parse(url)).timeout(_probeTimeout);
      req.headers.set('User-Agent', 'ManggoPro/1.0 (Flutter)');
      if (existing > 0) {
        req.headers.set('Range', 'bytes=$existing-');
      }
      final res = await req.close().timeout(_probeTimeout);

      final resuming = res.statusCode == 206 && existing > 0;
      if (res.statusCode != 200 && res.statusCode != 206) return false;

      final total = expectedSize > 0
          ? expectedSize
          : (res.contentLength > 0
              ? res.contentLength + (resuming ? existing : 0)
              : 0);

      var received = resuming ? existing : 0;
      sink = target.openWrite(
        mode: resuming ? FileMode.append : FileMode.write,
      );
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
