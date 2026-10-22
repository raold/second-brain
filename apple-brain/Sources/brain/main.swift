import Foundation
import FoundationModels

let usage = """
brain — Second Brain + Apple Intelligence (100 % local, sur ce Mac)

  brain ask "question"            Réponse d'Apple Intelligence à partir de tes notes, avec sources
  brain chat                      Questions en boucle (Entrée vide pour quitter)
  brain search "texte" [-n 10]    Recherche hybride (mots-clés + sens) — fichiers et passages
  brain find "nom"                Fichiers et dossiers par nom (Spotlight, audio/vidéo compris)
  brain organize [chemins…]       Propose où ranger (défaut : racine du coffre + Inbox)
        --apply                   … et déplace ceux de confiance haute (--min moyenne pour élargir)
  brain mv <source> <dossier>     Déplace en mettant à jour les liens Obsidian
  brain undo                      Annule le dernier lot de déplacements
  brain index [--rebuild]         Met à jour l'index (incrémental)
  brain status                    État d'Apple Intelligence et de l'index
  brain mcp                       Serveur MCP (Claude Code / Claude Desktop)

Options : --json (sortie machine), --no-expand (ask sans expansion de requête)
Coffre : \(Config.vault.path)   (variable BRAIN_VAULT pour en changer)
"""

final class App {
    private var _store: Store?
    private var _embedder: Embedder?
    private var _searcher: Searcher?

    func store() throws -> Store {
        if let s = _store { return s }
        let s = try Store(); _store = s; return s
    }

    func embedder() async throws -> Embedder {
        if let e = _embedder { return e }
        let e = try await Embedder(); _embedder = e; return e
    }

    func searcher() throws -> Searcher {
        guard let s = _searcher else { throw BrainError("searcher not loaded") }
        return s
    }

    /// Loads the index for querying, building it on first use.
    func loadSearcher() async throws {
        let st = try store()
        var n = 0
        try st.query("SELECT count(*) FROM chunks") { n = Int($0.int(0)) }
        if n == 0 {
            eprint("Premier lancement : indexation du coffre…")
            _ = try await index()
        }
        _searcher = try Searcher(store: st, embedder: try await embedder())
    }

    func index(rebuild: Bool = false, quiet: Bool = false) async throws -> (added: Int, removed: Int, chunks: Int) {
        let r = try await Indexer(store: try store(), embedder: try await embedder(), quiet: quiet).run(rebuild: rebuild)
        if _searcher != nil { _searcher = try Searcher(store: try store(), embedder: try await embedder()) }
        return r
    }

    static func format(_ hits: [Hit]) -> String {
        hits.enumerated().map { i, h in
            let snippet = h.text.replacingOccurrences(of: "\n", with: " ").prefix(220)
            let head = h.heading.isEmpty ? "" : " › \(h.heading)"
            return "\(i + 1). \(h.path)\(head)\n   \(snippet)"
        }.joined(separator: "\n")
    }

    static func spotlight(_ name: String) -> [String] {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/mdfind")
        p.arguments = ["-onlyin", Config.vault.path, "-name", name]
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = FileHandle.nullDevice
        try? p.run()
        let out = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        p.waitUntilExit()
        var lines = out.split(separator: "\n").map(String.init).map { Config.rel(URL(fileURLWithPath: $0)) }
            .filter { !Config.isIgnored($0) }
        if lines.isEmpty {
            // Spotlight may not index iCloud placeholders: fall back to walking the vault.
            let folded = name.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
            lines = Indexer.walk(includeDirs: true).map(\.rel).filter {
                ($0 as NSString).lastPathComponent.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
                    .contains(folded)
            }
        }
        return lines.map { rel in
            var isDir: ObjCBool = false
            FileManager.default.fileExists(atPath: Config.abs(rel).path, isDirectory: &isDir)
            return (isDir.boolValue ? "📁 " : "📄 ") + rel
        }.sorted()
    }
}

func flagValue(_ args: [String], _ name: String) -> String? {
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}

func positional(_ args: [String], valued: Set<String> = ["-n", "--min"]) -> [String] {
    var out: [String] = []
    var skip = false
    for a in args {
        if skip { skip = false; continue }
        if valued.contains(a) { skip = true; continue }
        if a.hasPrefix("--") || a == "-n" { continue }
        out.append(a)
    }
    return out
}

func printJSON<T: Encodable>(_ v: T) throws {
    print(String(decoding: try JSONEncoder.pretty.encode(v), as: UTF8.self))
}

func runCLI() async throws {
    var args = Array(CommandLine.arguments.dropFirst())
    guard !args.isEmpty, !["-h", "--help", "help"].contains(args[0]) else { print(usage); return }
    let cmd = args.removeFirst()
    let json = args.contains("--json")
    let app = App()
    let text = positional(args).joined(separator: " ")

    switch cmd {
    case "index":
        let t0 = Date()
        let r = try await app.index(rebuild: args.contains("--rebuild"), quiet: args.contains("--quiet"))
        print("✅ \(r.added) fichiers (ré)indexés (\(r.chunks) passages), \(r.removed) retirés — \(Int(Date().timeIntervalSince(t0))) s")

    case "search":
        guard !text.isEmpty else { throw BrainError("usage : brain search \"texte\"") }
        try await app.loadSearcher()
        let hits = try app.searcher().searchFiles(text, limit: Int(flagValue(args, "-n") ?? "") ?? 10)
        if json { try printJSON(hits) } else { print(App.format(hits)) }

    case "ask", "chat":
        try await app.loadSearcher()
        let assistant = Assistant(searcher: try app.searcher())
        func one(_ q: String) async throws {
            if json { try printJSON(try await assistant.ask(q, expand: !args.contains("--no-expand"))); return }
            let r = try await assistant.ask(q, expand: !args.contains("--no-expand")) { chunk in
                print(chunk, terminator: ""); fflush(stdout)
            }
            // Show the excerpts the answer cites; fall back to the five best when it cites none.
            let cited = Set(r.answer.matches(of: #/\[(\d+)\]/#).compactMap { Int($0.1) })
            let shown = r.sources.enumerated().filter { cited.isEmpty ? $0.offset < 5 : cited.contains($0.offset + 1) }
            print("\n\nSources :")
            for (i, h) in shown { print("  [\(i + 1)] \(h.path)\(h.heading.isEmpty ? "" : " › \(h.heading)")") }
        }
        if cmd == "ask" {
            guard !text.isEmpty else { throw BrainError("usage : brain ask \"question\"") }
            try await one(text)
        } else {
            print("💬 Pose tes questions (Entrée vide pour quitter)")
            while true {
                print("\n› ", terminator: ""); fflush(stdout)
                guard let q = readLine(), !q.trimmingCharacters(in: .whitespaces).isEmpty else { break }
                do { try await one(q) } catch { print("⚠️  \(error)") }
            }
        }

    case "find":
        guard !text.isEmpty else { throw BrainError("usage : brain find \"nom\"") }
        let r = App.spotlight(text)
        print(r.isEmpty ? "Aucun fichier ni dossier ne contient « \(text) »." : r.joined(separator: "\n"))

    case "organize":
        try await app.loadSearcher()
        _ = try await app.index(quiet: true)
        let items = Organizer.sources(from: positional(args))
        guard !items.isEmpty else { print("Rien à ranger : la racine du coffre est propre."); return }
        let plan = try await Organizer(searcher: try app.searcher()).plan(items)
        let levels = ["haute": 2, "moyenne": 1, "basse": 0]
        let minLevel = levels[flagValue(args, "--min") ?? "haute"] ?? 2
        if json { try printJSON(plan) } else {
            print("\nPlan de rangement (Apple Intelligence) :")
            for p in plan {
                let mark = p.destination == Organizer.stay ? "·" : ((levels[p.confidence] ?? 0) >= minLevel ? "→" : "?")
                print(" \(mark) \(p.source)\n     \(p.destination == Organizer.stay ? "reste en place" : p.destination)  [\(p.confidence)] \(p.reason)")
            }
        }
        guard args.contains("--apply") else {
            if !json { print("\nRien n'a été déplacé. Relance avec --apply pour appliquer les « → ».") }
            return
        }
        let batch = ISO8601DateFormatter().string(from: Date())
        var moved = 0
        for p in plan where p.destination != Organizer.stay && (levels[p.confidence] ?? 0) >= minLevel {
            do {
                let m = try Organizer.move(Config.abs(p.source), toFolder: p.destination, batch: batch)
                moved += 1
                print("✅ \(p.source) → \(p.destination)\(m.rewritten.isEmpty ? "" : " (\(m.rewritten.count) notes aux liens mis à jour)")")
            } catch { print("⚠️  \(p.source) : \(error)") }
        }
        if moved > 0 { _ = try await app.index(quiet: true); refreshGraph() }
        print("\(moved) élément(s) déplacé(s). `brain undo` pour annuler.")

    case "mv":
        let pos = positional(args)
        guard pos.count == 2 else { throw BrainError("usage : brain mv <source> <dossier du coffre>") }
        let src = pos[0].hasPrefix("/") || pos[0].hasPrefix("~")
            ? URL(fileURLWithPath: (pos[0] as NSString).expandingTildeInPath) : Config.abs(pos[0])
        let m = try Organizer.move(src, toFolder: pos[1], batch: ISO8601DateFormatter().string(from: Date()))
        print("✅ → \(Config.rel(URL(fileURLWithPath: m.to)))  (liens mis à jour dans \(m.rewritten.count) notes)")
        _ = try await app.index(quiet: true); refreshGraph()

    case "undo":
        let undone = try Organizer.undo()
        if undone.isEmpty { print("Aucun déplacement à annuler.") } else {
            for m in undone { print("↩️  \(Config.rel(URL(fileURLWithPath: m.to))) → \(Config.rel(URL(fileURLWithPath: m.from)))") }
            _ = try await app.index(quiet: true); refreshGraph()
        }

    case "status":
        let m = SystemLanguageModel.default
        print("Apple Intelligence (on-device) : \(m.availability)  · contexte \(m.contextSize) tokens · français : \(m.supportsLocale(Locale(identifier: "fr_FR")))")
        var files = 0, chunks = 0
        try app.store().query("SELECT (SELECT count(*) FROM files), (SELECT count(*) FROM chunks)") {
            files = Int($0.int(0)); chunks = Int($0.int(1))
        }
        let at = (try app.store().meta("indexed_at")).flatMap { Double(String(decoding: $0, as: UTF8.self)) }
        print("Index : \(files) fichiers, \(chunks) passages · \(Config.dbURL.path)")
        if let at { print("Dernière mise à jour : \(Date(timeIntervalSince1970: at).formatted(date: .abbreviated, time: .shortened))") }
        print("Coffre : \(Config.vault.path)")

    case "mcp":
        try await app.loadSearcher()
        await MCPServer(app: app).run()

    default:
        print(usage)
        throw BrainError("commande inconnue : \(cmd)")
    }
}

/// Keeps the vault's graphify graph in sync after moves (0 LLM tokens, see vault AGENTS.md).
func refreshGraph() {
    let g = Config.vault.appendingPathComponent("graphify-out/tools/g")
    guard FileManager.default.isExecutableFile(atPath: g.path) else { return }
    let p = Process()
    p.executableURL = g
    p.arguments = ["build"]
    p.standardOutput = FileHandle.nullDevice
    p.standardError = FileHandle.nullDevice
    try? p.run()
    p.waitUntilExit()
}

do {
    try await runCLI()
} catch {
    eprint("❌ \(error)")
    exit(1)
}
