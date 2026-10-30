import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// 翻译结果：成功时 [text] 有值，失败时 [error] 说明原因。
///
/// 刻意不用「返回带语言前缀的原文」之类的兜底——那会让界面看起来像翻译成功了，
/// 实际是把原文原样还回来（历史 bug：长句永远显示 `[EN] 原文`）。
class TranslationResult {
  final String? text;
  final String? error;

  const TranslationResult.ok(String this.text) : error = null;
  const TranslationResult.fail(String this.error) : text = null;

  bool get isOk => text != null;
}

/// 真实翻译服务。
///
/// 说明：目前走公开的 translate_a/single 接口（无需 API Key），
/// 后期换成自建/商业 API 时只需替换 [_endpoint] 与 [_parse]。
class TranslationService {
  TranslationService._();

  static const String _endpoint =
      'https://translate.googleapis.com/translate_a/single';

  /// 单次请求超时。移动网络下 12 秒足够，再久不如直接报错重试。
  static const Duration _timeout = Duration(seconds: 12);

  /// BCP-47 短码 → 该接口认的地区码
  static const Map<String, String> _locale = {
    'zh': 'zh-CN',
    'en': 'en',
    'ja': 'ja',
    'ko': 'ko',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
    'ru': 'ru',
  };

  /// 超过这个长度就按句号切段，避免单次 URL/表单过长被拒
  static const int _chunkLimit = 1800;

  static Future<TranslationResult> translate({
    required String text,
    required String from,
    required String to,
  }) async {
    final input = text.trim();
    if (input.isEmpty) return const TranslationResult.fail('没有可翻译的内容');
    if (from == to) return TranslationResult.ok(input);

    final chunks = _split(input);
    final buffer = StringBuffer();
    for (var i = 0; i < chunks.length; i++) {
      final r = await _once(chunks[i], from, to);
      if (!r.isOk) return r;
      if (i > 0 && !buffer.toString().endsWith('\n')) buffer.write(' ');
      buffer.write(r.text);
    }
    final out = buffer.toString().trim();
    return out.isEmpty
        ? const TranslationResult.fail('翻译服务返回了空结果')
        : TranslationResult.ok(out);
  }

  /// 按句末标点切段，只在超长时才切
  static List<String> _split(String text) {
    if (text.length <= _chunkLimit) return [text];
    final parts = <String>[];
    final buf = StringBuffer();
    for (final ch in text.split('')) {
      buf.write(ch);
      if ('。！？.!?\n'.contains(ch) && buf.length >= _chunkLimit ~/ 3) {
        parts.add(buf.toString());
        buf.clear();
      }
    }
    if (buf.isNotEmpty) parts.add(buf.toString());
    // 兜底：单段仍超限则硬切
    final out = <String>[];
    for (final p in parts) {
      if (p.length <= _chunkLimit) {
        out.add(p);
      } else {
        for (var i = 0; i < p.length; i += _chunkLimit) {
          out.add(p.substring(
              i, i + _chunkLimit > p.length ? p.length : i + _chunkLimit));
        }
      }
    }
    return out;
  }

  static Future<TranslationResult> _once(
      String text, String from, String to) async {
    final client = HttpClient()..connectionTimeout = _timeout;
    try {
      final req = await client.postUrl(Uri.parse(_endpoint)).timeout(_timeout);
      req.headers.contentType =
          ContentType('application', 'x-www-form-urlencoded', charset: 'utf-8');
      req.headers.set('User-Agent', 'ManggoPro/1.0 (Flutter)');
      final body = <String, String>{
        'client': 'gtx',
        'sl': _locale[from] ?? from,
        'tl': _locale[to] ?? to,
        'dt': 't',
        'q': text,
      };
      final encoded = body.entries
          .map((e) =>
              '${Uri.encodeQueryComponent(e.key)}=${Uri.encodeQueryComponent(e.value)}')
          .join('&');
      req.add(utf8.encode(encoded));

      final res = await req.close().timeout(_timeout);
      final raw = await res.transform(utf8.decoder).join().timeout(_timeout);

      if (res.statusCode != 200) {
        return TranslationResult.fail('翻译服务返回 ${res.statusCode}');
      }
      final parsed = _parse(raw);
      return parsed == null
          ? const TranslationResult.fail('翻译服务返回了无法解析的结果')
          : TranslationResult.ok(parsed);
    } on SocketException {
      return const TranslationResult.fail('网络不可用，无法连接翻译服务');
    } on TimeoutException {
      return const TranslationResult.fail('翻译超时，请检查网络后重试');
    } on HandshakeException {
      return const TranslationResult.fail('安全连接失败，请检查网络或代理');
    } catch (e) {
      return TranslationResult.fail('翻译失败：$e');
    } finally {
      client.close(force: true);
    }
  }

  /// 响应形如 [[["译文","原文",null,null,10]],null,"en",...]
  /// 长句会被切成多段，需要按顺序拼回去。
  static String? _parse(String raw) {
    try {
      final data = jsonDecode(raw);
      if (data is! List || data.isEmpty) return null;
      final segs = data[0];
      if (segs is! List) return null;
      final sb = StringBuffer();
      for (final seg in segs) {
        if (seg is List && seg.isNotEmpty && seg[0] is String) {
          sb.write(seg[0] as String);
        }
      }
      final out = sb.toString().trim();
      return out.isEmpty ? null : out;
    } catch (_) {
      return null;
    }
  }
}
