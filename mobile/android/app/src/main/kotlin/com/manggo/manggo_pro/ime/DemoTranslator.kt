package com.manggo.manggo_pro.ime

/**
 * 骨架期的本地词表。
 *
 * 接入真实翻译服务时，把 [translate] 改成异步网络请求即可：
 * 1. 改为 suspend 函数或带回调；
 * 2. 在 [ManggoImeService.translateCurrentLine] 里先删原文、显示「翻译中…」，
 *    请求返回后再 commitText 把译文写回光标处。
 */
object DemoTranslator {

    private val dict: Map<String, String> = mapOf(
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

    /** 命中返回译文，未命中返回 null（调用方据此提示，避免写出垃圾内容）。 */
    fun translate(text: String): String? = dict[text.trim()]
}
