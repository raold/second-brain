import Foundation

/// Paths and vault conventions shared by every command.
enum Config {
    static let vault: URL = {
        if let p = ProcessInfo.processInfo.environment["BRAIN_VAULT"], !p.isEmpty {
            return URL(fileURLWithPath: (p as NSString).expandingTildeInPath).standardizedFileURL
        }
        return URL(fileURLWithPath: NSHomeDirectory()
            + "/Library/Mobile Documents/iCloud~md~obsidian/Documents/Second Brain")
    }()

    static let supportDir: URL = {
        let u = URL(fileURLWithPath: NSHomeDirectory() + "/Library/Application Support/AppleBrain")
        try? FileManager.default.createDirectory(at: u, withIntermediateDirectories: true)
        return u
    }()

    static var dbURL: URL { supportDir.appendingPathComponent("index.sqlite") }
    static var journalURL: URL { supportDir.appendingPathComponent("moves.jsonl") }

    /// Folder names (any depth) that are never indexed nor proposed as destinations.
    static let ignoredDirs: Set<String> = ["graphify-out", "node_modules", "__pycache__"]
    /// Root-level files that configure agents rather than hold knowledge.
    static let ignoredRootFiles: Set<String> = ["AGENTS.md", "CLAUDE.md"]
    static let ignoredExts: Set<String> = ["lock", "log", "ds_store", "tmp", "icloud"]

    /// True when a vault-relative path should be skipped entirely.
    static func isIgnored(_ rel: String) -> Bool {
        let parts = rel.split(separator: "/").map(String.init)
        if parts.contains(where: { $0.hasPrefix(".") || ignoredDirs.contains($0) }) { return true }
        if parts.count == 1 && ignoredRootFiles.contains(parts[0]) { return true }
        let ext = (rel as NSString).pathExtension.lowercased()
        return ignoredExts.contains(ext)
    }

    static func rel(_ url: URL) -> String {
        let base = vault.standardizedFileURL.path
        let p = url.standardizedFileURL.path
        if p == base { return "" }
        if p.hasPrefix(base + "/") { return String(p.dropFirst(base.count + 1)) }
        return p
    }

    static func abs(_ rel: String) -> URL {
        rel.hasPrefix("/") ? URL(fileURLWithPath: rel) : vault.appendingPathComponent(rel)
    }

    /// The "Current filing map" section of the vault's AGENTS.md, used to guide filing.
    static func filingMap() -> String {
        let url = vault.appendingPathComponent("AGENTS.md")
        guard let s = try? String(contentsOf: url, encoding: .utf8),
              let start = s.range(of: "## Current filing map") else { return "" }
        let rest = s[start.upperBound...]
        let end = rest.range(of: "\n## ")?.lowerBound ?? rest.endIndex
        return String(rest[..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

func eprint(_ items: Any..., terminator: String = "\n") {
    let s = items.map { "\($0)" }.joined(separator: " ") + terminator
    FileHandle.standardError.write(s.data(using: .utf8)!)
}

struct BrainError: Error, CustomStringConvertible {
    let description: String
    init(_ d: String) { description = d }
}
