import 'package:flutter/foundation.dart';

/// 生词本条目
class VocabEntry {
  VocabEntry({required this.word, required this.meaning, this.starred = false});

  final String word;
  final String meaning;

  /// 是否标记为「重点复习」
  bool starred;
}

/// 全局生词本（骨架期为内存态）。
///
/// 之前「翻译页收藏」只翻转了一个局部 bool，弹了句「已加入生词本」，
/// 但生词本页读的是自己写死的示例列表——两个页面各存一份，收藏等于没生效。
/// 这里改成单一数据源：翻译页的收藏写入本 Store，生词本页监听后重建。
///
/// 接入持久化时，在 [_load] / 每次变更后落盘（Hive / sqlite / 服务端）即可，
/// 页面侧不用改。
class VocabStore {
  VocabStore._();

  /// 词表变更会通知所有监听方（翻译页的星标、生词本页的列表）
  static final ValueNotifier<List<VocabEntry>> entries =
      ValueNotifier<List<VocabEntry>>(<VocabEntry>[
    VocabEntry(word: 'serendipity', meaning: '意外发现美好事物的能力', starred: true),
    VocabEntry(word: 'ubuntu', meaning: '人道精神；我因你而存在（祖鲁谚语）', starred: true),
    VocabEntry(word: 'schadenfreude', meaning: '幸灾乐祸', starred: true),
    VocabEntry(word: 'hinode', meaning: '日出（日语：日の出）', starred: true),
  ]);

  static bool contains(String word) {
    final key = word.trim();
    if (key.isEmpty) return false;
    return entries.value.any((e) => e.word == key);
  }

  /// 已存在则移出，否则插入到顶部。返回操作后是否在生词本里。
  static bool toggle({required String word, required String meaning}) {
    final key = word.trim();
    if (key.isEmpty) return false;
    final list = List<VocabEntry>.of(entries.value);
    final index = list.indexWhere((e) => e.word == key);
    if (index >= 0) {
      list.removeAt(index);
      entries.value = list;
      return false;
    }
    list.insert(
      0,
      VocabEntry(
        word: key,
        meaning: meaning.trim().isEmpty ? '（暂无释义）' : meaning.trim(),
      ),
    );
    entries.value = list;
    return true;
  }

  static void remove(String word) {
    final key = word.trim();
    entries.value = List<VocabEntry>.of(entries.value)
      ..removeWhere((e) => e.word == key);
  }

  /// 切换重点复习标记，返回切换后的状态；词条不存在返回 false。
  static bool toggleStar(String word) {
    final key = word.trim();
    final list = List<VocabEntry>.of(entries.value);
    final index = list.indexWhere((e) => e.word == key);
    if (index < 0) return false;
    list[index].starred = !list[index].starred;
    entries.value = list;
    return list[index].starred;
  }
}
