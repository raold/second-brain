import Foundation
import FoundationModels

/// Files items into vault folders: embeddings shortlist the folders, Apple Intelligence picks one
/// (constrained to that shortlist), and moves are journaled so `brain undo` can revert them.
struct Organizer {
    let searcher: Searcher
    static let stay = "(laisser en place)"

    struct Proposal: Codable {
        let source: String        // vault-relative, or absolute when outside the vault
        let destination: String   // vault-relative folder, or Organizer.stay
        let reason: String
        let confidence: String    // haute | moyenne | basse
    }

    // MARK: Candidates

    /// Loose items at the vault root plus inbox-like folders; raw/ sources are immutable.
    static func defaultSources() -> [URL] {
        let fm = FileManager.default
        var out: [URL] = []
        let rootItems = (try? fm.contentsOfDirectory(at: Config.vault, includingPropertiesForKeys: [.isDirectoryKey])) ?? []
        for u in rootItems where !Config.isIgnored(Config.rel(u)) {
            if (try? u.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory != true { out.append(u) }
        }
        for name in ["Inbox", "inbox", "À trier", "A trier", "_inbox", "Nouveaux"] {
            let d = Config.vault.appendingPathComponent(name)
            out += (try? fm.contentsOfDirectory(at: d, includingPropertiesForKeys: nil))?
                .filter { !$0.lastPathComponent.hasPrefix(".") } ?? []
        }
        return out
    }

    /// Expands a user argument: a folder means its direct children (files and sub-folders).
    static func sources(from args: [String]) -> [URL] {
        if args.isEmpty { return defaultSources() }
        var out: [URL] = []
        for a in args {
            let u = a.hasPrefix("/") || a.hasPrefix("~")
                ? URL(fileURLWithPath: (a as NSString).expandingTildeInPath) : Config.abs(a)
            var isDir: ObjCBool = false
            guard FileManager.default.fileExists(atPath: u.path, isDirectory: &isDir) else {
                eprint("⚠️  introuvable : \(a)"); continue
            }
            if isDir.boolValue {
                out += ((try? FileManager.default.contentsOfDirectory(at: u, includingPropertiesForKeys: nil)) ?? [])
                    .filter { !$0.lastPathComponent.hasPrefix(".") }
            } else { out.append(u) }
        }
        return out
    }

    static func vaultFolders() -> [String] {
        Indexer.walk(includeDirs: true)
            .filter { (try? $0.url.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true }
            .map(\.rel)
            .filter { !$0.hasPrefix("raw/processed") && !$0.hasPrefix("raw/") }
            .sorted()
    }

    // MARK: Planning

    func plan(_ items: [URL], shortlist: Int = 12) async throws -> [Proposal] {
        try Assistant.checkModel()
        let folders = Self.vaultFolders()
        var profiles = try searcher.folderProfiles()
        for f in folders where profiles[f] == nil {
            profiles[f] = Vec.centered(searcher.embedder.embed(f), mean: searcher.mean)
        }
        let map = Config.filingMap()
        var out: [Proposal] = []
        for (i, url) in items.enumerated() {
            let rel = Config.rel(url)
            if rel.hasPrefix("raw/") { continue }
            eprint("[\(i + 1)/\(items.count)] \(url.lastPathComponent)")
            let current = (rel as NSString).deletingLastPathComponent
            let excerpt = await Self.describe(url)
            let q = Vec.centered(searcher.embedder.embed("\(url.lastPathComponent)\n\(excerpt)"), mean: searcher.mean)

            // Shortlist: folders whose content resembles the item, plus folders named like its words.
            let words = Set(Searcher.terms(url.deletingPathExtension().lastPathComponent).filter { $0.count > 3 })
            let ranked = folders.map { f -> (String, Float) in
                let pv = profiles[f] ?? []
                let nameBonus: Float = Searcher.terms(f).contains(where: words.contains) ? 0.15 : 0
                return (f, Vec.dot(q, pv) + nameBonus)
            }.sorted { $0.1 > $1.1 }
            var choices = ranked.prefix(shortlist).map(\.0)
            if !current.isEmpty, folders.contains(current), !choices.contains(current) { choices.append(current) }
            choices.append(Self.stay)

            let p = try await classify(name: url.lastPathComponent, location: current.isEmpty ? "racine du coffre" : current,
                                       excerpt: excerpt, choices: choices, filingMap: map)
            let dest = p.destination == current ? Self.stay : p.destination
            out.append(Proposal(source: rel, destination: dest, reason: p.reason, confidence: p.confidence))
        }
        return out
    }

    static func describe(_ url: URL) async -> String {
        var isDir: ObjCBool = false
        FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir)
        if isDir.boolValue {
            let kids = ((try? FileManager.default.contentsOfDirectory(atPath: url.path)) ?? []).filter { !$0.hasPrefix(".") }
            return "Dossier contenant \(kids.count) éléments : " + kids.prefix(25).joined(separator: ", ")
        }
        let text = await Extract.text(of: url) ?? ""
        return text.isEmpty ? "(pas de texte, type \(url.pathExtension))" : String(text.prefix(1500))
    }

    private func classify(name: String, location: String, excerpt: String,
                          choices: [String], filingMap: String) async throws -> (destination: String, reason: String, confidence: String) {
        let root = DynamicGenerationSchema(name: "Rangement", properties: [
            .init(name: "destination", description: "Dossier de destination, ou \(Self.stay) si aucun ne convient clairement",
                  schema: DynamicGenerationSchema(name: "Dossier", anyOf: choices)),
            .init(name: "raison", description: "Une phrase courte en français",
                  schema: DynamicGenerationSchema(type: String.self)),
            .init(name: "confiance", description: "haute seulement si le contenu correspond sans ambiguïté",
                  schema: DynamicGenerationSchema(name: "Confiance", anyOf: ["haute", "moyenne", "basse"])),
        ])
        let schema = try GenerationSchema(root: root, dependencies: [])
        let instructions = """
        Tu ranges les fichiers d'un coffre Obsidian selon ce plan de classement :
        \(filingMap)
        Choisis le dossier le plus spécifique qui correspond au CONTENU (pas seulement au nom).
        En cas de doute, choisis \(Self.stay).
        """
        let prompt = "Fichier : \(name)\nEmplacement actuel : \(location)\nContenu :\n\(excerpt)"
        func run(_ permissive: Bool) async throws -> GeneratedContent {
            let s = LanguageModelSession(model: Assistant.model(permissive: permissive), instructions: instructions)
            return try await s.respond(to: prompt, schema: schema, options: GenerationOptions(temperature: 0)).content
        }
        let c: GeneratedContent
        do { c = try await run(false) } catch where Assistant.isGuardrail(error) { c = try await run(true) }
        return (try c.value(String.self, forProperty: "destination"),
                (try? c.value(String.self, forProperty: "raison")) ?? "",
                (try? c.value(String.self, forProperty: "confiance")) ?? "basse")
    }

    // MARK: Moving

    struct Move: Codable {
        let batch: String
        let from: String          // absolute paths
        let to: String
        let rewritten: [String]   // vault-relative notes whose links were updated
    }

    /// Moves `src` into the vault folder `destFolder`, never overwriting, and rewrites path links.
    @discardableResult
    static func move(_ src: URL, toFolder destFolder: String, batch: String) throws -> Move {
        let fm = FileManager.default
        let dir = Config.abs(destFolder)
        try fm.createDirectory(at: dir, withIntermediateDirectories: true)
        let dst = dir.appendingPathComponent(src.lastPathComponent)
        if fm.fileExists(atPath: dst.path) { throw BrainError("existe déjà : \(Config.rel(dst))") }
        try fm.moveItem(at: src, to: dst)
        let oldRel = Config.rel(src), newRel = Config.rel(dst)
        let rewritten = oldRel.hasPrefix("/") ? [] : rewriteLinks(from: oldRel, to: newRel)
        let m = Move(batch: batch, from: src.path, to: dst.path, rewritten: rewritten)
        appendJournal(m)
        return m
    }

    /// Updates path-style links (`[[dir/Note]]`, `[x](dir/Note.md)`); bare `[[Note]]` links keep working.
    static func rewriteLinks(from old: String, to new: String) -> [String] {
        func noExt(_ s: String) -> String { s.hasSuffix(".md") ? String(s.dropLast(3)) : s }
        func enc(_ s: String) -> String { s.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? s }
        var pairs: [(String, String)] = []
        for (o, n) in [(old, new), (noExt(old), noExt(new))] {
            for suffix in ["]]", "|", "#", "/"] { pairs.append(("[[\(o)\(suffix)", "[[\(n)\(suffix)")) }
            // APFS paths come back decomposed (e + ◌́) while Obsidian encodes "é" precomposed: try both.
            let forms = [o, o.precomposedStringWithCanonicalMapping, o.decomposedStringWithCanonicalMapping]
            let target = enc(n.precomposedStringWithCanonicalMapping)
            for v in Set(forms + forms.map(enc)) { pairs.append(("](\(v))", "](\(target))")); pairs.append(("](\(v)/", "](\(target)/")) }
        }
        var changed: [String] = []
        for e in Indexer.walk() where e.url.pathExtension.lowercased() == "md" {
            guard var s = try? String(contentsOf: e.url, encoding: .utf8) else { continue }
            let before = s
            for (o, n) in pairs where s.contains(o) { s = s.replacingOccurrences(of: o, with: n) }
            if s != before, (try? s.write(to: e.url, atomically: true, encoding: .utf8)) != nil { changed.append(e.rel) }
        }
        return changed
    }

    static func appendJournal(_ m: Move) {
        guard var line = try? JSONEncoder().encode(m) else { return }
        line.append(0x0A)
        if let h = try? FileHandle(forWritingTo: Config.journalURL) {
            h.seekToEndOfFile(); h.write(line); try? h.close()
        } else {
            try? line.write(to: Config.journalURL)
        }
    }

    static func journal() -> [Move] {
        guard let s = try? String(contentsOf: Config.journalURL, encoding: .utf8) else { return [] }
        return s.split(separator: "\n").compactMap { try? JSONDecoder().decode(Move.self, from: Data($0.utf8)) }
    }

    /// Reverts the most recent batch of moves (links included).
    static func undo() throws -> [Move] {
        var all = journal()
        guard let last = all.last?.batch else { return [] }
        let batch = all.filter { $0.batch == last }
        for m in batch.reversed() {
            let from = URL(fileURLWithPath: m.from), to = URL(fileURLWithPath: m.to)
            guard !FileManager.default.fileExists(atPath: from.path) else {
                eprint("⚠️  \(from.path) existe déjà, je ne l'écrase pas"); continue
            }
            try FileManager.default.createDirectory(at: from.deletingLastPathComponent(), withIntermediateDirectories: true)
            try FileManager.default.moveItem(at: to, to: from)
            if !Config.rel(from).hasPrefix("/") { _ = rewriteLinks(from: Config.rel(to), to: Config.rel(from)) }
        }
        all.removeAll { $0.batch == last }
        let body = all.compactMap { try? JSONEncoder().encode($0) }.map { String(decoding: $0, as: UTF8.self) }.joined(separator: "\n")
        try (body.isEmpty ? "" : body + "\n").write(to: Config.journalURL, atomically: true, encoding: .utf8)
        return batch
    }
}
