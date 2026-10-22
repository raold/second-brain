import Foundation

/// Incremental indexer: only new or modified files are re-read and re-embedded.
struct Indexer {
    let store: Store
    let embedder: Embedder
    var quiet = false

    struct Entry { let rel: String; let url: URL; let mtime: Double; let size: Int }

    static func walk(_ root: URL = Config.vault, includeDirs: Bool = false) -> [Entry] {
        let keys: [URLResourceKey] = [.isDirectoryKey, .contentModificationDateKey, .fileSizeKey]
        guard let en = FileManager.default.enumerator(at: root, includingPropertiesForKeys: keys,
                                                      options: [.skipsPackageDescendants]) else { return [] }
        var out: [Entry] = []
        for case let url as URL in en {
            let rel = Config.rel(url)
            if Config.isIgnored(rel) {
                if (try? url.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true { en.skipDescendants() }
                continue
            }
            guard let v = try? url.resourceValues(forKeys: Set(keys)) else { continue }
            if v.isDirectory == true && !includeDirs { continue }
            out.append(Entry(rel: rel, url: url,
                             mtime: v.contentModificationDate?.timeIntervalSince1970 ?? 0,
                             size: v.fileSize ?? 0))
        }
        return out
    }

    func run(rebuild: Bool = false) async throws -> (added: Int, removed: Int, chunks: Int) {
        if rebuild { try store.exec("DELETE FROM chunks_fts; DELETE FROM chunks; DELETE FROM files;") }
        var known: [String: (id: Int64, mtime: Double, size: Int)] = [:]
        try store.query("SELECT id, path, mtime, size FROM files") {
            known[$0.string(1)] = ($0.int(0), $0.double(2), Int($0.int(3)))
        }
        let entries = Self.walk()
        let present = Set(entries.map(\.rel))
        var removed = 0
        try store.transaction {
            for (path, k) in known where !present.contains(path) { try store.deleteFile(id: k.id); removed += 1 }
        }

        let todo = entries.filter { e in
            guard let k = known[e.rel] else { return true }
            return abs(k.mtime - e.mtime) > 0.5 || k.size != e.size
        }
        var chunkCount = 0
        for (i, e) in todo.enumerated() {
            if !quiet { eprint("\r[\(i + 1)/\(todo.count)] \(e.rel.prefix(90))", terminator: "\u{1B}[K") }
            let kind = Extract.kind(of: e.url)
            let title = e.url.deletingPathExtension().lastPathComponent
            let folder = (e.rel as NSString).deletingLastPathComponent
            var chunks: [Chunk] = []
            if let text = await Extract.text(of: e.url) { chunks = Chunker.chunks(text) }
            if chunks.isEmpty {
                // Audio, video, archives… still findable by name and folder.
                chunks = [Chunk(heading: "", text: "Fichier \(e.url.lastPathComponent) dans \(folder.isEmpty ? "la racine" : folder)")]
            }
            let vecs = chunks.map { embedder.embed("\(title)\n\($0.heading)\n\($0.text)") }
            try store.transaction {
                if let k = known[e.rel] { try store.deleteFile(id: k.id) }
                try store.query("INSERT INTO files(path, mtime, size, kind) VALUES(?,?,?,?)",
                                [e.rel, e.mtime, e.size, kind])
                let fid = store.lastInsertId
                for (n, c) in chunks.enumerated() {
                    try store.query("INSERT INTO chunks(file_id, ord, heading, text, vec) VALUES(?,?,?,?,?)",
                                    [fid, n, c.heading, c.text, vecs[n].data])
                    try store.query("INSERT INTO chunks_fts(rowid, title, path, heading, text) VALUES(?,?,?,?,?)",
                                    [store.lastInsertId, title, folder, c.heading, c.text])
                }
            }
            chunkCount += chunks.count
        }
        if !quiet && !todo.isEmpty { eprint("") }
        if !todo.isEmpty || removed > 0 || rebuild { try updateMean() }
        try store.setMeta("indexed_at", String(Date().timeIntervalSince1970).data(using: .utf8)!)
        return (todo.count, removed, chunkCount)
    }

    /// Corpus mean vector, used to centre embeddings at query time.
    func updateMean() throws {
        var sum = [Double](repeating: 0, count: embedder.dimension)
        var n = 0.0
        try store.query("SELECT vec FROM chunks") { row in
            let v = [Float](data: row.data(0))
            guard v.count == sum.count else { return }
            for i in v.indices { sum[i] += Double(v[i]) }
            n += 1
        }
        guard n > 0 else { return }
        try store.setMeta("mean", sum.map { Float($0 / n) }.data)
    }
}
