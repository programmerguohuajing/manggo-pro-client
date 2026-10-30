import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';
import 'package:manggo_pro/services/vocab_store.dart';
import 'package:manggo_pro/widgets/language_chip.dart';
import 'package:manggo_pro/widgets/translate_card.dart';
import 'package:manggo_pro/screens/language_select_screen.dart';

class TranslateScreen extends StatefulWidget {
  /// 点右上角相机时切到「拍照」Tab（由 main.dart 注入）
  final VoidCallback? onOpenCamera;

  const TranslateScreen({super.key, this.onOpenCamera});

  @override
  State<TranslateScreen> createState() => _TranslateScreenState();
}

class _TranslateScreenState extends State<TranslateScreen> {
  Language _src = Language.zh;
  Language _dst = Language.en;
  final _srcController = TextEditingController(text: '你好，世界');
  String _dstText = 'Hello, world';
  bool _translating = false;
  bool _spaceGuard = false;

  /// 星标状态直接从生词本推导，不再各自存一份 bool——
  /// 否则「收藏」只改本地状态，生词本里永远看不到。
  bool get _favSrc => VocabStore.contains(_srcController.text);

  bool get _favDst => VocabStore.contains(_dstText);

  /// 输入框末尾连续三个空格（半角或全角）即触发翻译
  static final RegExp _tripleSpace = RegExp(r'[ \u3000]{3,}$');

  /// 骨架期的本地词表；接入真实翻译 API 后只需替换 _localTranslate
  static const Map<String, String> _demoDict = {
    '你好，世界': 'Hello, world',
    '今天天气真好': 'The weather is nice today',
    '请帮我翻译这段': 'Please translate this for me',
    '谢谢你的帮助': 'Thank you for your help',
    '我们几点见面': 'What time shall we meet',
  };

  @override
  void initState() {
    super.initState();
    _srcController.addListener(_onInputChanged);
    // 生词本在别处被删/被标记时，本页星标同步刷新
    VocabStore.entries.addListener(_onVocabChanged);
  }

  @override
  void dispose() {
    VocabStore.entries.removeListener(_onVocabChanged);
    _srcController.removeListener(_onInputChanged);
    _srcController.dispose();
    super.dispose();
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
    if (src.isEmpty || _translating) return;
    setState(() => _translating = true);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    if (!mounted) return;
    setState(() {
      _dstText = _localTranslate(src);
      _translating = false;
    });
  }

  String _localTranslate(String src) =>
      _demoDict[src] ?? '[${_dst.code.toUpperCase()}] $src';

  void _pick(bool isSource) async {
    final chosen = await Navigator.of(context).push<Language>(
      MaterialPageRoute(builder: (_) => const LanguageSelectScreen()),
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
          // 双卡片 + 居中 FAB
          Stack(
            clipBehavior: Clip.none,
            children: [
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
                  const SizedBox(height: 36),
                  TranslateCard(
                    header: '译文 · ${_dst.name}',
                    text: _translating ? '翻译中…' : _dstText,
                    onSpeak: () => _speak(_dstText, _dst),
                    onCopy: () => _copy(_dstText),
                    onFavorite: () => _toggleFav(false),
                    favorited: _favDst,
                  ),
                ],
              ),
              Positioned(
                top: 78,
                left: 0,
                right: 0,
                child: Center(
                  child: GestureDetector(
                    onTap: _translate,
                    child: Container(
                      width: 48,
                      height: 48,
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
                ),
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
