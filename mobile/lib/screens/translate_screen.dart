import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';
import 'package:manggo_pro/services/translation_service.dart';
import 'package:manggo_pro/services/vocab_store.dart';
import 'package:manggo_pro/widgets/language_chip.dart';
import 'package:manggo_pro/widgets/translate_card.dart';
import 'package:manggo_pro/screens/language_select_screen.dart';

class TranslateScreen extends StatefulWidget {
  /// 点右上角相机时切到「拍照」Tab（由 main.dart 注入）
  final VoidCallback? onOpenCamera;

  /// 从历史页点条目复用：把原文/译文送回翻译页（由 main.dart 注入）
  final ValueListenable<TranslateSeed?>? seed;

  const TranslateScreen({super.key, this.onOpenCamera, this.seed});

  @override
  State<TranslateScreen> createState() => _TranslateScreenState();
}

/// 历史页回填用的一对文本
class TranslateSeed {
  final String src;
  final String dst;
  const TranslateSeed(this.src, this.dst);
}

class _TranslateScreenState extends State<TranslateScreen> {
  Language _src = Language.zh;
  Language _dst = Language.en;
  final _srcController = TextEditingController(text: '你好，世界');
  String _dstText = 'Hello, world';
  bool _translating = false;
  bool _spaceGuard = false;

  /// 上次翻译的错误信息；非空时译文卡显示错误而不是空白
  String? _dstErr;

  /// 星标状态直接从生词本推导，不再各自存一份 bool——
  /// 否则「收藏」只改本地状态，生词本里永远看不到。
  bool get _favSrc => VocabStore.contains(_srcController.text);

  bool get _favDst => VocabStore.contains(_dstText);

  /// 输入框末尾连续三个空格（半角或全角）即触发翻译
  static final RegExp _tripleSpace = RegExp(r'[ \u3000]{3,}$');

  @override
  void initState() {
    super.initState();
    _srcController.addListener(_onInputChanged);
    // 生词本在别处被删/被标记时，本页星标同步刷新
    VocabStore.entries.addListener(_onVocabChanged);
    widget.seed?.addListener(_applySeed);
  }

  @override
  void dispose() {
    widget.seed?.removeListener(_applySeed);
    VocabStore.entries.removeListener(_onVocabChanged);
    _srcController.removeListener(_onInputChanged);
    _srcController.dispose();
    super.dispose();
  }

  TranslateSeed? _lastSeed;

  /// 历史页点了某条记录：把原文/译文塞回输入框与译文卡
  void _applySeed() {
    final seed = widget.seed?.value;
    if (seed == null || identical(seed, _lastSeed)) return;
    _lastSeed = seed;
    _spaceGuard = true;
    _srcController.value = TextEditingValue(
      text: seed.src,
      selection: TextSelection.collapsed(offset: seed.src.length),
    );
    _spaceGuard = false;
    setState(() => _dstText = seed.dst);
    _toast('已载入这条历史');
  }

  void _onVocabChanged() {
    if (mounted) setState(() {});
  }

  void _onInputChanged() {
    if (_spaceGuard) return;
    final text = _srcController.text;
    if (!_tripleSpace.hasMatch(text)) return;
    _spaceGuard = true;
    // 吃掉触发用的空格，避免它们混进译文内容
    final stripped = text.replaceFirst(_tripleSpace, '');
    _srcController.value = TextEditingValue(
      text: stripped,
      selection: TextSelection.collapsed(offset: stripped.length),
    );
    _spaceGuard = false;
    _translate();
  }

  Future<void> _translate() async {
    final src = _srcController.text.trim();
    if (src.isEmpty) {
      _toast('先输入要翻译的内容');
      return;
    }
    if (_translating) return;
    setState(() {
      _translating = true;
      _dstErr = null;
    });

    final r = await TranslationService.translate(
      text: src,
      from: _src.code,
      to: _dst.code,
    );
    if (!mounted) return;
    setState(() {
      _translating = false;
      if (r.isOk) {
        _dstText = r.text!;
        _dstErr = null;
      } else {
        // 失败就明确报错，绝不用「[EN] 原文」冒充译文
        _dstErr = r.error;
      }
    });
    if (!r.isOk) _toast(r.error ?? '翻译失败');
  }

  void _pick(bool isSource) async {
    final chosen = await Navigator.of(context).push<Language>(
      MaterialPageRoute(
        builder: (_) =>
            LanguageSelectScreen(current: isSource ? _src.code : _dst.code),
      ),
    );
    if (chosen != null) {
      setState(() => isSource ? _src = chosen : _dst = chosen);
    }
  }

  void _swap() => setState(() {
        final t = _src;
        _src = _dst;
        _dst = t;
      });

  // ---------------- 按钮实际行为 ----------------

  void _toast(String message) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(
      content: Text(message),
      duration: const Duration(milliseconds: 1400),
      behavior: SnackBarBehavior.floating,
    ));
  }

  Future<void> _copy(String text) async {
    if (text.trim().isEmpty) {
      _toast('没有可复制的内容');
      return;
    }
    await Clipboard.setData(ClipboardData(text: text));
    _toast('已复制');
  }

  Future<void> _speak(String text, Language lang) async {
    if (!AppSettings.speechEnabled.value) {
      _toast('语音播报已在设置中关闭');
      return;
    }
    if (text.trim().isEmpty) {
      _toast('没有可播报的内容');
      return;
    }
    final ok = await PlatformService.speak(text, lang: lang.code);
    if (!ok) _toast('当前设备不支持语音播报');
  }

  void _toggleFav(bool isSource) {
    final word = isSource ? _srcController.text : _dstText;
    final meaning = isSource ? _dstText : _srcController.text;
    if (word.trim().isEmpty) {
      _toast(isSource ? '没有可收藏的内容' : '没有可收藏的译文');
      return;
    }
    final added = VocabStore.toggle(word: word, meaning: meaning);
    // 生词本变更会自己通知，这里兜底刷新一次本页星标
    setState(() {});
    _toast(added ? '已加入生词本' : '已从生词本移除');
  }

  Future<void> _share() async {
    final ok = await PlatformService.share(
      '${_srcController.text.trim()}\n$_dstText',
    );
    if (!ok) _toast('当前设备不支持分享');
  }

  void _showMore() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.clear_all_rounded),
              title: const Text('清空输入'),
              onTap: () {
                Navigator.pop(sheetContext);
                _srcController.clear();
                setState(() => _dstText = '');
              },
            ),
            ListTile(
              leading: const Icon(Icons.swap_horiz_rounded),
              title: const Text('交换语言'),
              onTap: () {
                Navigator.pop(sheetContext);
                _swap();
              },
            ),
            ListTile(
              leading: const Icon(Icons.keyboard_alt_outlined),
              title: const Text('切换输入法'),
              subtitle: const Text('启用 Manggo 翻译输入法后，任意 App 里连按三次空格即可翻译'),
              onTap: () {
                Navigator.pop(sheetContext);
                PlatformService.showImePicker();
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    // 顶部留出状态栏高度，内容可从状态栏下方滚过，由全局渐隐遮罩收边
    final topInset = MediaQuery.of(context).padding.top;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(16, 8 + topInset, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 顶部标题栏
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('翻译',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
              Row(
                children: [
                  _topAction(Icons.mic_none_rounded,
                      tooltip: '语音输入', onTap: () => _toast('语音输入待接入系统语音识别')),
                  _topAction(Icons.camera_alt_outlined,
                      tooltip: '拍照取词',
                      onTap: () => widget.onOpenCamera?.call()),
                  _topAction(Icons.more_horiz_rounded,
                      tooltip: '更多', onTap: _showMore),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          // 语言选择条 + 交换
          Row(
            children: [
              LanguageChip(label: _src.name, onTap: () => _pick(true)),
              const SizedBox(width: 8),
              InkWell(
                onTap: _swap,
                child: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: isDark
                        ? const Color(0xFF0E2419)
                        : const Color(0xFFEAFBF0),
                    border: Border.all(
                      color: isDark
                          ? const Color(0x1AFFFFFF)
                          : const Color(0x14000000),
                    ),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.swap_vert_rounded,
                      color: Manggo.primary),
                ),
              ),
              const SizedBox(width: 8),
              LanguageChip(label: _dst.name, onTap: () => _pick(false)),
            ],
          ),
          const SizedBox(height: 14),
          // 双卡片，翻译按钮骑在缝隙上
          Column(
            children: [
              TranslateCard(
                header: '源语言 · ${_src.name}',
                text: '',
                editable: true,
                controller: _srcController,
                onSpeak: () => _speak(_srcController.text, _src),
                onCopy: () => _copy(_srcController.text),
                onFavorite: () => _toggleFav(true),
                favorited: _favSrc,
              ),
              // 按钮放在固定 36 高的缝隙里居中，随源卡片高度自然下移；
              // 原先用 Stack + Positioned(top: 78) 是写死的，源文一变长就压住正文。
              SizedBox(
                height: 36,
                child: Stack(
                  clipBehavior: Clip.none,
                  alignment: Alignment.center,
                  children: [
                    GestureDetector(
                      onTap: _translate,
                      child: Container(
                        width: 48,
                        height: 48,
                        // 不设 alignment 时子节点会被撑到 48×48，
                        // 进度圈就跑到按钮边缘外、被绿底挡住只看得到半圈
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          gradient: Manggo.fabGradient,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(.25),
                              blurRadius: 12,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: _translating
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.translate_rounded,
                                color: Colors.white, size: 24),
                      ),
                    ),
                  ],
                ),
              ),
              TranslateCard(
                header: '译文 · ${_dst.name}',
                text: _translating ? '翻译中…' : _dstText,
                error: _translating ? null : _dstErr,
                onSpeak: () => _speak(_dstText, _dst),
                onCopy: () => _copy(_dstText),
                onFavorite: () => _toggleFav(false),
                favorited: _favDst,
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 快捷操作
          Row(
            children: [
              _quickBtn(
                  '复制', Icons.content_copy_outlined, () => _copy(_dstText)),
              _quickBtn(
                  '语音', Icons.volume_up_outlined, () => _speak(_dstText, _dst)),
              _quickBtn(
                  '收藏',
                  _favDst ? Icons.star_rounded : Icons.star_border_rounded,
                  () => _toggleFav(false)),
              _quickBtn('分享', Icons.share_outlined, _share),
            ],
          ),
        ],
      ),
    );
  }

  Widget _topAction(IconData icon, {String? tooltip, VoidCallback? onTap}) =>
      Tooltip(
        message: tooltip ?? '',
        child: InkResponse(
          onTap: onTap,
          radius: 22,
          child: Container(
            width: 34,
            height: 34,
            margin: const EdgeInsets.only(left: 6),
            alignment: Alignment.center,
            decoration: const BoxDecoration(shape: BoxShape.circle),
            child:
                Icon(icon, size: 22, color: Theme.of(context).iconTheme.color),
          ),
        ),
      );

  Widget _quickBtn(String label, IconData icon, VoidCallback onTap) => Expanded(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(Manggo.radiusSm),
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 5),
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              border: Border.all(
                color: Theme.of(context).dividerColor,
              ),
              borderRadius: BorderRadius.circular(Manggo.radiusSm),
            ),
            child: Column(
              children: [
                Icon(icon, size: 20, color: Theme.of(context).iconTheme.color),
                const SizedBox(height: 4),
                Text(label, style: const TextStyle(fontSize: 11.5)),
              ],
            ),
          ),
        ),
      );
}
