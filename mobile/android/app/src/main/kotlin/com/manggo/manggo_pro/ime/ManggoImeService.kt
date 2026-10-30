package com.manggo.manggo_pro.ime

import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.inputmethodservice.InputMethodService
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Manggo 翻译输入法。
 *
 * 核心交互：在任意 App 的输入框里打字，**连按三次空格**就把光标所在这一行的内容
 * 翻译并原地替换（前两次空格照常输入，第三次触发翻译并把触发用的空格一并吃掉）。
 *
 * 三端对应实现：
 * - Android：本文件（InputMethodService）
 * - iOS：Keyboard Extension + textDocumentProxy
 * - HarmonyOS NEXT：InputMethodExtensionAbility
 */
class ManggoImeService : InputMethodService() {

    private var shiftOn = false
    private var spaceTaps = 0
    private var translating = false
    private var spaceKey: TextView? = null

    private val handler = Handler(Looper.getMainLooper())
    private val resetSpaceTaps = Runnable { spaceTaps = 0 }

    override fun onCreateInputView(): View = buildKeyboard()

    /**
     * 有实体键盘（模拟器、平板键盘、外接键盘）时，基类会返回 false 从而**完全不显示**
     * 输入法界面。翻译键盘在这类设备上同样需要，所以固定为 true。
     */
    override fun onEvaluateInputViewShown(): Boolean = true

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        spaceTaps = 0
        translating = false
        handler.removeCallbacks(resetSpaceTaps)
        setStatus(STATUS_IDLE)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    // ---------------- 键盘 UI ----------------

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    private fun rounded(color: Int, radiusDp: Int): GradientDrawable =
        GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(radiusDp).toFloat()
        }

    private fun buildKeyboard(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#EEF0F3"))
            setPadding(dp(3), dp(6), dp(3), dp(8))
        }

        val letterRows = listOf("qwertyuiop", "asdfghjkl", "zxcvbnm")
        letterRows.forEachIndexed { index, chars ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }
            if (index == 2) {
                row.addView(makeKey("⇧", 1.3f, accent = true) { toggleShift() })
            }
            for (c in chars) {
                val label = if (shiftOn) c.uppercaseChar().toString() else c.toString()
                row.addView(makeKey(label, 1f) { onLetter(c) })
            }
            if (index == 2) {
                row.addView(makeKey("⌫", 1.3f, accent = true) { deleteBackward() })
            }
            root.addView(row, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(50)))
        }

        val functionRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        val space = makeKey(STATUS_IDLE, 4.6f) { onSpace() }
        space.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f)
        spaceKey = space
        functionRow.addView(space)
        functionRow.addView(makeKey("↵", 1.3f, accent = true) { commitEnter() })
        root.addView(functionRow, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(50)))

        return root
    }

    private fun makeKey(
        label: String,
        weight: Float,
        accent: Boolean = false,
        onClick: () -> Unit
    ): TextView = TextView(this).apply {
        text = label
        gravity = Gravity.CENTER
        setTextColor(if (accent) Color.parseColor("#0F7B4F") else Color.parseColor("#1F2328"))
        setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f)
        background = rounded(if (accent) Color.parseColor("#E3F6EC") else Color.WHITE, 8)
        isClickable = true
        isFocusable = false
        setOnClickListener { onClick() }
        layoutParams = LinearLayout.LayoutParams(
            0,
            LinearLayout.LayoutParams.MATCH_PARENT,
            weight
        ).apply { setMargins(dp(2), dp(3), dp(2), dp(3)) }
    }

    // ---------------- 输入行为 ----------------

    private fun onLetter(ch: Char) {
        val text = if (shiftOn) ch.uppercaseChar().toString() else ch.toString()
        currentInputConnection?.commitText(text, 1)
        spaceTaps = 0
        if (shiftOn) {
            shiftOn = false
            refreshKeyboard()
        }
    }

    private fun toggleShift() {
        shiftOn = !shiftOn
        refreshKeyboard()
    }

    private fun refreshKeyboard() {
        setInputView(buildKeyboard())
        setStatus(STATUS_IDLE)
    }

    private fun deleteBackward() {
        val ic = currentInputConnection ?: return
        val selected = ic.getSelectedText(0)
        if (!selected.isNullOrEmpty()) {
            ic.commitText("", 1)
        } else {
            ic.deleteSurroundingText(1, 0)
        }
        spaceTaps = 0
    }

    private fun commitEnter() {
        val ic = currentInputConnection ?: return
        ic.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER))
        ic.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER))
        spaceTaps = 0
    }

    /**
     * 空格键：第 1、2 次正常输入空格；第 3 次不输入空格，
     * 改为把光标所在行的内容翻译后原地替换。
     */
    private fun onSpace() {
        if (translating) return
        val ic = currentInputConnection ?: return
        spaceTaps += 1
        if (spaceTaps >= 3) {
            spaceTaps = 0
            handler.removeCallbacks(resetSpaceTaps)
            translateCurrentLine()
        } else {
            ic.commitText(" ", 1)
            handler.removeCallbacks(resetSpaceTaps)
            handler.postDelayed(resetSpaceTaps, SPACE_WINDOW_MS)
        }
    }

    private fun translateCurrentLine() {
        val ic = currentInputConnection ?: return
        if (isPasswordField(currentInputEditorInfo)) {
            setStatus("密码框不翻译")
            return
        }

        val before = ic.getTextBeforeCursor(MAX_SCAN, 0)?.toString().orEmpty()
        if (before.isBlank()) {
            setStatus("先输入内容")
            return
        }

        // 只处理光标所在行，整行替换（触发用的尾部空格一并吃掉）
        val line = before.substringAfterLast('\n')
        val content = line.trim()
        if (content.isEmpty()) {
            setStatus("先输入内容")
            return
        }

        val translated = DemoTranslator.translate(content)
        if (translated == null) {
            setStatus("未覆盖：$content")
            return
        }

        translating = true
        setStatus("翻译中…")
        handler.postDelayed({
            try {
                if (line.isNotEmpty()) {
                    ic.deleteSurroundingText(line.length, 0)
                }
                ic.commitText(translated, 1)
                setStatus("已翻译 ✓")
            } catch (e: Exception) {
                setStatus("替换失败")
            } finally {
                translating = false
            }
        }, TRANSLATE_DELAY_MS)
    }

    private fun isPasswordField(info: EditorInfo?): Boolean {
        val type = info?.inputType ?: return false
        val cls = type and InputType.TYPE_MASK_CLASS
        if (cls != InputType.TYPE_CLASS_TEXT) return false
        val variation = type and InputType.TYPE_MASK_VARIATION
        return variation == InputType.TYPE_TEXT_VARIATION_PASSWORD ||
            variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD ||
            variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
    }

    private fun setStatus(text: String) {
        spaceKey?.text = text
    }

    companion object {
        private const val STATUS_IDLE = "空格 ×3 翻译这一段"
        private const val SPACE_WINDOW_MS = 1500L
        private const val TRANSLATE_DELAY_MS = 180L
        private const val MAX_SCAN = 1000
    }
}
