import Foundation

/// 一次翻译的结果。`online == false` 表示走的是本地词表兜底。
struct KeyboardTranslation {
    let text: String
    let online: Bool
}

/// 键盘扩展用的翻译客户端，与 Android 的 `RemoteTranslator` 完全对齐：
/// 同一个翻译接口、同样的源/目标语言判定、同样的分块拼接、同样的离线兜底顺序。
///
/// 关键顺序：**先请求网络，失败才查词表**。反过来会把「没网」误报成「这个词没收录」。
enum KeyboardTranslator {

    // MARK: - 常量

    private static let endpoint = URL(string: "https://translate.googleapis.com/translate_a/single")!
    private static let timeout: TimeInterval = 12
    /// 单次请求上限，超长按句切分
    private static let chunkLimit = 1800

    private static let session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = timeout
        config.timeoutIntervalForResource = timeout
        config.waitsForConnectivity = false
        return URLSession(configuration: config)
    }()

    // MARK: - 对外入口

    /// 异步翻译。`completion` 一定在主线程回调；全部失败时传 `nil`。
    static func translate(_ text: String, completion: @escaping (KeyboardTranslation?) -> Void) {
        let input = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty else {
            DispatchQueue.main.async { completion(nil) }
            return
        }

        let source = hasCJK(input) ? "zh-CN" : "en"
        let target = hasCJK(input) ? "en" : "zh-CN"

        requestAll(chunks: split(input), source: source, target: target) { online in
            DispatchQueue.main.async {
                if let onlineText = online {
                    completion(KeyboardTranslation(text: onlineText, online: true))
                } else if let offline = offlineLookup(input) {
                    completion(KeyboardTranslation(text: offline, online: false))
                } else {
                    completion(nil)
                }
            }
        }
    }

    // MARK: - 网络

    /// 逐块请求并拼接；任何一块失败整体返回 nil（与 Android 一致，不做半截替换）
    private static func requestAll(chunks: [String],
                                   source: String,
                                   target: String,
                                   completion: @escaping (String?) -> Void) {
        var collected: [String] = []
        var index = 0

        func next() {
            guard index < chunks.count else {
                let joined = collected.joined(separator: " ")
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                completion(joined.isEmpty ? nil : joined)
                return
            }
            let chunk = chunks[index]
            index += 1
            requestOnce(chunk, source: source, target: target) { part in
                guard let part = part, !part.isEmpty else {
                    completion(nil)
                    return
                }
                collected.append(part)
                next()
            }
        }

        next()
    }

    private static func requestOnce(_ text: String,
                                    source: String,
                                    target: String,
                                    completion: @escaping (String?) -> Void) {
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = timeout
        request.setValue("application/x-www-form-urlencoded; charset=utf-8",
                         forHTTPHeaderField: "Content-Type")
        request.setValue("ManggoPro/1.0 (iOS Keyboard)", forHTTPHeaderField: "User-Agent")

        let fields: [(String, String)] = [
            ("client", "gtx"),
            ("sl", source),
            ("tl", target),
            ("dt", "t"),
            ("q", text),
        ]
        request.httpBody = fields
            .map { "\($0.0)=\(percentEncode($0.1))" }
            .joined(separator: "&")
            .data(using: .utf8)

        session.dataTask(with: request) { data, response, error in
            guard error == nil,
                  let http = response as? HTTPURLResponse,
                  http.statusCode == 200,
                  let data = data else {
                completion(nil)
                return
            }
            completion(parse(data))
        }.resume()
    }

    private static func percentEncode(_ value: String) -> String {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    /// 响应形如 `[[["译文","原文",null,...]],null,"en",...]`，长句分多段需拼接
    private static func parse(_ data: Data) -> String? {
        guard let root = try? JSONSerialization.jsonObject(with: data),
              let top = root as? [Any],
              let segments = top.first as? [Any] else {
            return nil
        }

        var output = ""
        for segment in segments {
            guard let parts = segment as? [Any],
                  let piece = parts.first as? String else { continue }
            output += piece
        }
        let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    // MARK: - 分块

    /// 只在超长时才按句末标点切分，再超长就硬切
    private static func split(_ text: String) -> [String] {
        guard text.count > chunkLimit else { return [text] }

        var pieces: [String] = []
        var buffer = ""
        for ch in text {
            buffer.append(ch)
            if "。！？.!?\n".contains(ch) && buffer.count >= chunkLimit / 3 {
                pieces.append(buffer)
                buffer = ""
            }
        }
        if !buffer.isEmpty { pieces.append(buffer) }

        var result: [String] = []
        for piece in pieces {
            if piece.count <= chunkLimit {
                result.append(piece)
            } else {
                var start = piece.startIndex
                while start < piece.endIndex {
                    let end = piece.index(start, offsetBy: chunkLimit, limitedBy: piece.endIndex)
                        ?? piece.endIndex
                    result.append(String(piece[start..<end]))
                    start = end
                }
            }
        }
        return result.isEmpty ? [text] : result
    }

    // MARK: - 离线词表（与 DemoTranslator.kt 一致）

    private static let zhToEn: [String: String] = [
        "你好": "Hello",
        "你好，世界": "Hello, world",
        "你好世界": "Hello world",
        "早上好": "Good morning",
        "晚安": "Good night",
        "谢谢": "Thank you",
        "谢谢你的帮助": "Thank you for your help",
        "今天天气真好": "The weather is nice today",
        "请帮我翻译这段": "Please translate this for me",
        "我们几点见面": "What time shall we meet",
        "多少钱": "How much is it?",
        "我不明白": "I don't understand",
        "再见": "Goodbye",
        "好久不见": "Long time no see",
    ]

    private static let enToZh: [String: String] = {
        var map: [String: String] = [:]
        for (zh, en) in zhToEn {
            map[normalize(en)] = zh
        }
        return map
    }()

    private static func normalize(_ input: String) -> String {
        var text = input.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        while let last = text.last, ".,!?".contains(last) {
            text.removeLast()
        }
        return text
    }

    private static func offlineLookup(_ text: String) -> String? {
        if hasCJK(text) {
            if let hit = zhToEn[text] { return hit }
            return zhToEn[text.replacingOccurrences(of: "，", with: ",")]
        }
        return enToZh[normalize(text)]
    }

    private static func hasCJK(_ text: String) -> Bool {
        for scalar in text.unicodeScalars {
            let value = scalar.value
            if (0x4E00...0x9FFF).contains(value) || (0x3400...0x4DBF).contains(value) {
                return true
            }
        }
        return false
    }
}
