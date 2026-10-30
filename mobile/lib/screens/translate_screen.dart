import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/widgets/language_chip.dart';
import 'package:manggo_pro/widgets/translate_card.dart';
import 'package:manggo_pro/screens/language_select_screen.dart';

class TranslateScreen extends StatefulWidget {
  const TranslateScreen({super.key});

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
  }

  @override
  void dispose() {
    _srcController.removeListener(_onInputChanged);
    _srcController.dispose();
    super.dispose();
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

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 顶部标题栏
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('翻译',
                    style:
                        TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
                Row(
                  children: [
                    _topAction(Icons.mic_none_rounded),
                    _topAction(Icons.camera_alt_outlined),
                    _topAction(Icons.more_horiz_rounded),
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
                    ),
                    const SizedBox(height: 36),
                    TranslateCard(
                      header: '译文 · ${_dst.name}',
                      text: _translating ? '翻译中…' : _dstText,
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
                _quickBtn('复制', Icons.content_copy_outlined),
                _quickBtn('语音', Icons.volume_up_outlined),
                _quickBtn('收藏', Icons.star_border_rounded),
                _quickBtn('分享', Icons.share_outlined),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _topAction(IconData icon) => InkWell(
        onTap: () {},
        child: Container(
          width: 34,
          height: 34,
          margin: const EdgeInsets.only(left: 6),
          decoration: const BoxDecoration(shape: BoxShape.circle),
          child: Icon(icon, size: 22, color: Theme.of(context).iconTheme.color),
        ),
      );

  Widget _quickBtn(String label, IconData icon) => Expanded(
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
      );
}
