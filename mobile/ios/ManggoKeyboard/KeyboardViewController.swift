import UIKit

/// Manggo 翻译键盘（iOS Keyboard Extension）。
///
/// 交互与 Android 的 `ManggoImeService` 完全一致：在任意 App 的输入框里打字，
/// **连按三次空格**就把光标所在这一行翻译并原地替换。前两次空格照常输入，
/// 第三次不输入空格，而是触发翻译（触发用的空格一并被替换掉）。
final class KeyboardViewController: UIInputViewController {

    // MARK: - 尺寸与配色（与 Android / Flutter 侧的芒果绿一致）

    private enum Metrics {
        static let keyHeight: CGFloat = 46
        static let rowSpacing: CGFloat = 6
        static let sidePadding: CGFloat = 4
        static let corner: CGFloat = 8
        static let sideKeyWidth: CGFloat = 52
        static var totalHeight: CGFloat { keyHeight * 4 + rowSpacing * 3 + sidePadding * 2 + 6 }
    }

    private enum Palette {
        static let background = UIColor(red: 0.933, green: 0.941, blue: 0.953, alpha: 1) // #EEF0F3
        static let key = UIColor.white
        static let accentKey = UIColor(red: 0.890, green: 0.965, blue: 0.925, alpha: 1) // #E3F6EC
        static let label = UIColor(red: 0.122, green: 0.137, blue: 0.157, alpha: 1) // #1F2328
        static let accentLabel = UIColor(red: 0.059, green: 0.482, blue: 0.310, alpha: 1) // #0F7B4F
    }

    // MARK: - 状态

    private static let statusIdle = "空格 ×3 翻译这一段"
    private static let spaceWindow: TimeInterval = 1.5

    private var isShiftOn = false
    private var spaceTaps = 0
    private var isTranslating = false
    /// 每次翻译递增；结果回来时若已不是最新一次就丢弃
    private var translateToken = 0

    private var spaceButton: UIButton?
    private var shiftButton: UIButton?
    private var letterButtons: [(button: UIButton, letter: String)] = []
    private var resetTapsWorkItem: DispatchWorkItem?

    // MARK: - 生命周期

    override func viewDidLoad() {
        super.viewDidLoad()
        buildKeyboard()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        spaceTaps = 0
        isTranslating = false
        setStatus(Self.statusIdle)
    }

    deinit {
        resetTapsWorkItem?.cancel()
        translateToken += 1
    }

    // MARK: - 键盘 UI

    private func buildKeyboard() {
        view.backgroundColor = Palette.background

        let root = UIStackView()
        root.axis = .vertical
        root.spacing = Metrics.rowSpacing
        root.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(root)

        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: view.leadingAnchor,
                                          constant: Metrics.sidePadding),
            root.trailingAnchor.constraint(equalTo: view.trailingAnchor,
                                           constant: -Metrics.sidePadding),
            root.topAnchor.constraint(equalTo: view.topAnchor, constant: 3),
        ])

        // 输入法高度由自己决定（默认会被压成一行）
        let height = view.heightAnchor.constraint(equalToConstant: Metrics.totalHeight)
        height.priority = UILayoutPriority(999)
        height.isActive = true

        addRow(root, letters: Array("qwertyuiop").map(String.init), inset: 0)
        addRow(root, letters: Array("asdfghjkl").map(String.init), inset: 12)
        addLetterBottomRow(root, letters: Array("zxcvbnm").map(String.init))
        addFunctionRow(root)
    }

    private func makeKeyButton(title: String,
                               accent: Bool,
                               fontSize: CGFloat) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.setTitleColor(accent ? Palette.accentLabel : Palette.label, for: .normal)
        button.titleLabel?.font = UIFont.systemFont(ofSize: fontSize)
        button.titleLabel?.adjustsFontSizeToFitWidth = true
        button.titleLabel?.minimumScaleFactor = 0.6
        button.backgroundColor = accent ? Palette.accentKey : Palette.key
        button.layer.cornerRadius = Metrics.corner
        button.translatesAutoresizingMaskIntoConstraints = false
        button.heightAnchor.constraint(equalToConstant: Metrics.keyHeight).isActive = true
        return button
    }

    private func addRow(_ parent: UIStackView, letters: [String], inset: CGFloat) {
        let row = UIStackView()
        row.axis = .horizontal
        row.spacing = Metrics.rowSpacing
        row.distribution = .fillEqually
        row.translatesAutoresizingMaskIntoConstraints = false
        row.isLayoutMarginsRelativeArrangement = inset > 0
        if inset > 0 {
            row.layoutMargins = UIEdgeInsets(top: 0, left: inset, bottom: 0, right: inset)
        }

        for letter in letters {
            let button = makeKeyButton(title: letter, accent: false, fontSize: 20)
            letterButtons.append((button, letter))
            button.addAction(UIAction { [weak self] _ in
                self?.onLetter(letter)
            }, for: .touchUpInside)
            row.addArrangedSubview(button)
        }
        parent.addArrangedSubview(row)
    }

    private func addLetterBottomRow(_ parent: UIStackView, letters: [String]) {
        let row = UIStackView()
        row.axis = .horizontal
        row.spacing = Metrics.rowSpacing
        row.distribution = .fillEqually
        row.translatesAutoresizingMaskIntoConstraints = false

        let shift = makeKeyButton(title: "⇧", accent: true, fontSize: 18)
        shift.addAction(UIAction { [weak self] _ in
            self?.toggleShift()
        }, for: .touchUpInside)
        shiftButton = shift
        row.addArrangedSubview(shift)

        for letter in letters {
            let button = makeKeyButton(title: letter, accent: false, fontSize: 20)
            letterButtons.append((button, letter))
            button.addAction(UIAction { [weak self] _ in
                self?.onLetter(letter)
            }, for: .touchUpInside)
            row.addArrangedSubview(button)
        }

        let delete = makeKeyButton(title: "⌫", accent: true, fontSize: 18)
        delete.addAction(UIAction { [weak self] _ in
            self?.deleteBackward()
        }, for: .touchUpInside)
        row.addArrangedSubview(delete)

        parent.addArrangedSubview(row)
    }

    private func addFunctionRow(_ parent: UIStackView) {
        let row = UIStackView()
        row.axis = .horizontal
        row.spacing = Metrics.rowSpacing
        row.distribution = .fill
        row.translatesAutoresizingMaskIntoConstraints = false

        let space = makeKeyButton(title: Self.statusIdle, accent: false, fontSize: 13)
        space.setContentHuggingPriority(.defaultLow, for: .horizontal)
        space.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        space.addAction(UIAction { [weak self] _ in
            self?.onSpace()
        }, for: .touchUpInside)
        spaceButton = space
        row.addArrangedSubview(space)

        let globe = makeKeyButton(title: "🌐", accent: true, fontSize: 16)
        globe.widthAnchor.constraint(equalToConstant: Metrics.sideKeyWidth).isActive = true
        globe.addAction(UIAction { [weak self] _ in
            self?.advanceToNextInputMode()
        }, for: .touchUpInside)
        row.addArrangedSubview(globe)

        let enter = makeKeyButton(title: "↵", accent: true, fontSize: 18)
        enter.widthAnchor.constraint(equalToConstant: Metrics.sideKeyWidth).isActive = true
        enter.addAction(UIAction { [weak self] _ in
            self?.commitEnter()
        }, for: .touchUpInside)
        row.addArrangedSubview(enter)

        parent.addArrangedSubview(row)
    }

    // MARK: - 输入行为

    private func onLetter(_ letter: String) {
        textDocumentProxy.insertText(isShiftOn ? letter.uppercased() : letter)
        spaceTaps = 0
        resetStatusIfIdle()
        if isShiftOn { setShift(false) }
    }

    private func toggleShift() {
        setShift(!isShiftOn)
    }

    private func setShift(_ on: Bool) {
        isShiftOn = on
        shiftButton?.backgroundColor = on ? Palette.accentLabel : Palette.accentKey
        shiftButton?.setTitleColor(on ? UIColor.white : Palette.accentLabel, for: .normal)
        for entry in letterButtons {
            entry.button.setTitle(on ? entry.letter.uppercased() : entry.letter, for: .normal)
        }
    }

    private func deleteBackward() {
        textDocumentProxy.deleteBackward()
        spaceTaps = 0
        resetStatusIfIdle()
    }

    private func commitEnter() {
        textDocumentProxy.insertText("\n")
        spaceTaps = 0
    }

    /// 译完后继续打字时把「已翻译 ✓」换回提示，避免状态一直挂着。
    /// 请求进行中不改，免得把「翻译中…」冲掉。
    private func resetStatusIfIdle() {
        guard !isTranslating else { return }
        if spaceButton?.title(for: .normal) != Self.statusIdle {
            setStatus(Self.statusIdle)
        }
    }

    // MARK: - 三连空格

    private func onSpace() {
        guard !isTranslating else { return }
        spaceTaps += 1

        if spaceTaps >= 3 {
            spaceTaps = 0
            resetTapsWorkItem?.cancel()
            translateCurrentLine()
            return
        }

        textDocumentProxy.insertText(" ")
        resetTapsWorkItem?.cancel()
        let item = DispatchWorkItem { [weak self] in
            self?.spaceTaps = 0
        }
        resetTapsWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + Self.spaceWindow, execute: item)
    }

    private func translateCurrentLine() {
        guard !isTranslating else { return }

        // 没有「允许完全访问」时扩展拿不到网络，直接给出可执行的提示
        if !hasFullAccess {
            setStatus("需开启「允许完全访问」")
            return
        }

        guard let before = textDocumentProxy.documentContextBeforeInput else {
            // 密码框 / 安全输入：系统根本不把内容交给键盘
            setStatus("此输入框不支持读取")
            return
        }

        let line = before.components(separatedBy: "\n").last ?? before
        let content = line.trimmingCharacters(in: .whitespaces)
        if content.isEmpty {
            setStatus("先输入内容")
            return
        }

        isTranslating = true
        translateToken += 1
        let token = translateToken
        setStatus("翻译中…")

        KeyboardTranslator.translate(content) { [weak self] result in
            guard let self = self else { return }
            guard token == self.translateToken else { return }
            defer { self.isTranslating = false }

            guard let result = result else {
                self.setStatus("翻译失败，请检查网络")
                return
            }

            // 请求期间用户可能继续打字，确认光标前仍是原文再删
            let now = self.textDocumentProxy.documentContextBeforeInput ?? ""
            guard now.hasSuffix(line) else {
                self.setStatus("内容已变化，已取消")
                return
            }

            for _ in 0..<line.count {
                self.textDocumentProxy.deleteBackward()
            }
            self.textDocumentProxy.insertText(result.text)
            self.setStatus(result.online ? "已翻译 ✓" : "已翻译 ✓（离线词表）")
        }
    }

    private func setStatus(_ text: String) {
        spaceButton?.setTitle(text, for: .normal)
    }
}
