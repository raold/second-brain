import AppKit
import Foundation
import PDFKit
import Vision

/// Turns a file into plain text. Media without text yields nil (indexed by name only).
enum Extract {
    static let plainExts: Set<String> = ["md", "markdown", "txt", "csv", "tsv", "ics"]
    static let richExts: Set<String> = ["rtf", "rtfd", "docx", "doc", "odt"]
    static let imageExts: Set<String> = ["png", "jpg", "jpeg", "heic", "tiff", "gif", "webp"]
    static let maxChars = 2_000_000

    static func kind(of url: URL) -> String {
        let e = url.pathExtension.lowercased()
        if plainExts.contains(e) { return "text" }
        if e == "pdf" { return "pdf" }
        if richExts.contains(e) { return "rich" }
        if e == "html" || e == "htm" { return "html" }
        if imageExts.contains(e) { return "image" }
        return "other"
    }

    static func text(of url: URL) async -> String? {
        let s: String?
        switch kind(of: url) {
        case "text": s = readPlain(url)
        case "pdf": s = pdfText(url)
        case "rich": s = try? NSAttributedString(url: url, options: [:], documentAttributes: nil).string
        case "html": s = readPlain(url).map(stripHTML)
        case "image": s = await ocr(url)
        default: s = nil
        }
        guard let t = s?.trimmingCharacters(in: .whitespacesAndNewlines), !t.isEmpty else { return nil }
        return t.count > maxChars ? String(t.prefix(maxChars)) : t
    }

    static func readPlain(_ url: URL) -> String? {
        guard let d = try? Data(contentsOf: url) else { return nil }
        return String(data: d, encoding: .utf8) ?? String(data: d, encoding: .isoLatin1)
    }

    static func pdfText(_ url: URL) -> String? {
        guard let doc = PDFDocument(url: url) else { return nil }
        var out = ""
        for i in 0..<doc.pageCount {
            if let t = doc.page(at: i)?.string { out += t + "\n\n" }
            if out.count > maxChars { break }
        }
        return out
    }

    static func stripHTML(_ s: String) -> String {
        var t = s.replacingOccurrences(of: "(?is)<(script|style)[^>]*>.*?</\\1>", with: " ", options: .regularExpression)
        t = t.replacingOccurrences(of: "(?i)<br\\s*/?>|</(p|div|li|h[1-6]|tr)>", with: "\n", options: .regularExpression)
        t = t.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
        t = t.replacingOccurrences(of: "&nbsp;", with: " ").replacingOccurrences(of: "&amp;", with: "&")
        return t.replacingOccurrences(of: "[ \\t]+", with: " ", options: .regularExpression)
    }

    /// On-device OCR (Vision), so screenshots and photos of documents become searchable.
    static func ocr(_ url: URL) async -> String? {
        var req = RecognizeTextRequest()
        req.recognitionLanguages = [Locale.Language(identifier: "fr-FR"), Locale.Language(identifier: "en-US")]
        req.usesLanguageCorrection = true
        guard let obs = try? await req.perform(on: url) else { return nil }
        let lines = obs.compactMap { $0.topCandidates(1).first?.string }
        return lines.count < 3 ? nil : lines.joined(separator: "\n")
    }
}

/// A retrieval unit: ~180 words under the nearest heading.
struct Chunk {
    let heading: String
    let text: String
}

enum Chunker {
    static let target = 180
    static let overlap = 30

    static func chunks(_ text: String) -> [Chunk] {
        var out: [Chunk] = []
        var heading = ""
        var buf: [String] = []
        var bufWords = 0

        func flush() {
            let t = buf.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
            if !t.isEmpty { out.append(Chunk(heading: heading, text: t)) }
            buf = []; bufWords = 0
        }

        for para in text.components(separatedBy: "\n\n") {
            let p = para.trimmingCharacters(in: .whitespacesAndNewlines)
            if p.isEmpty { continue }
            if p.hasPrefix("#"), !p.contains("\n"), p.count < 200 {
                flush()
                heading = p.trimmingCharacters(in: CharacterSet(charactersIn: "# "))
                continue
            }
            let words = p.split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" })
            if words.count > target + 40 {
                flush()
                var i = 0
                while i < words.count {
                    let j = min(i + target, words.count)
                    out.append(Chunk(heading: heading, text: words[i..<j].joined(separator: " ")))
                    if j == words.count { break }
                    i = j - overlap
                }
                continue
            }
            if bufWords + words.count > target { flush() }
            buf.append(p); bufWords += words.count
        }
        flush()
        return out
    }
}
