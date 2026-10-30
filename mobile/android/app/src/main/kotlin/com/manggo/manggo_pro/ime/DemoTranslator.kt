package com.manggo.manggo_pro.ime

/**
 * 骨架期的本地词表，**双向**翻译：
 * - 源文本含中日韩汉字 → 译成英文
 * - 源文本是拉丁字母 → 译成中文
 *
 * 因为自绘键盘目前只能输入拉丁字母，所以「英文 → 中文」是主路径，
 * 中文 → 英文留给系统剪贴板粘贴或后续接入拼音输入后的场景。
 *
 * 接入真实翻译服务时，把 [translate] 改成异步请求即可：
 * 在 [ManggoImeService.translateCurrentLine] 里先删原文、显示「翻译中…」，
 * 请求返回后再 commitText 把译文写回光标处。
 */
object DemoTranslator {

    /** 中文 -> 英文 */
    private val zhToEn: Map<String, String> = mapOf(
        "你好" to "Hello",
        "你好，世界" to "Hello, world",
        "你好世界" to "Hello world",
        "早上好" to "Good morning",
        "晚安" to "Good night",
        "谢谢" to "Thank you",
        "谢谢你的帮助" to "Thank you for your help",
        "今天天气真好" to "The weather is nice today",
        "请帮我翻译这段" to "Please translate this for me",
        "我们几点见面" to "What time shall we meet",
        "多少钱" to "How much is it?",
        "我不明白" to "I don't understand",
        "再见" to "Goodbye",
        "好久不见" to "Long time no see"
    )

    /** 英文 -> 中文（大小写不敏感，忽略句末标点差异） */
    private val enToZh: Map<String, String> = zhToEn.entries
        .associate { (zh, en) -> normalize(en) to zh }

    private fun normalize(input: String): String =
        input.trim().trimEnd('.', '!', '?', ',').lowercase()

    private fun hasCjk(text: String): Boolean =
        text.any { ch -> ch.code in 0x4E00..0x9FFF || ch.code in 0x3400..0x4DBF }

    /**
     * 命中返回译文，未命中返回 null —— 调用方据此提示，
     * 不会把原文或垃圾内容写回输入框。
     */
    fun translate(text: String): String? {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return null
        if (hasCjk(trimmed)) {
            return zhToEn[trimmed] ?: zhToEn[trimmed.replace("，", ",")]
        }
        return enToZh[normalize(trimmed)]
    }
}
