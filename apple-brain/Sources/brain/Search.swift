import Foundation

struct Hit: Codable {
    let chunkId: Int64
    let path: String
    let heading: String
    let text: String
    var score: Double
}

/// Hybrid retrieval: BM25 (SQLite FTS5) + Apple embeddings, fused with reciprocal rank fusion.
final class Searcher {
    let store: Store
    let embedder: Embedder
    private var ids: [Int64] = []
    private var matrix: [[Float]] = []
    private(set) var mean: [Float] = []

    init(store: Store, embedder: Embedder) throws {
        self.store = store
        self.embedder = embedder
        mean = (try store.meta("mean")).map { [Float](data: $0) } ?? []
        var ids: [Int64] = [], matrix: [[Float]] = []
        let mean = self.mean
        try store.query("SELECT id, vec FROM chunks") { row in
            ids.append(row.int(0))
            matrix.append(Vec.centered([Float](data: row.data(1)), mean: mean))
        }
        self.ids = ids
        self.matrix = matrix
    }

    var chunkCount: Int { ids.count }

    static let stopwords: Set<String> = Set("""
    le la les un une des du de d l et ou à a au aux en dans sur pour par avec sans ce cet cette ces \
    que qui quoi quel quelle quels quelles est sont été être ai as avons avez ont mon ma mes ton ta tes son sa ses \
    notre nos votre vos leur leurs je tu il elle on nous vous ils elles me te se y ne pas plus moins comment \
    pourquoi quand où combien faut-il dois doit the of and or to in on for with is are what when where how which \
    my your it this that be do does did can i you we they qu c s n j m t
    """.split(whereSeparator: { $0 == " " || $0 == "\n" }).map(String.init))

    static func terms(_ text: String) -> [String] {
        let folded = text.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
        let words = folded.components(separatedBy: CharacterSet.alphanumerics.inverted)
        var seen = Set<String>()
        return words.filter { w in
            w.count > 1 && !stopwords.contains(w) && seen.insert(w).inserted
        }
    }

    func ftsRanks(_ terms: [String], limit: Int) throws -> [Int64] {
        guard !terms.isEmpty else { return [] }
        let expr = terms.map { $0.count >= 4 ? "\"\($0)\"*" : "\"\($0)\"" }.joined(separator: " OR ")
        var out: [Int64] = []
        try store.query("""
            SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts, 6.0, 3.0, 2.0, 1.0) LIMIT ?
            """, [expr, limit]) { out.append($0.int(0)) }
        return out
    }

    func vectorRanks(_ text: String, limit: Int) -> [Int64] {
        let q = Vec.centered(embedder.embed(text), mean: mean)
        var scored = [(Int64, Float)]()
        scored.reserveCapacity(ids.count)
        for (i, v) in matrix.enumerated() { scored.append((ids[i], Vec.dot(q, v))) }
        scored.sort { $0.1 > $1.1 }
        return scored.prefix(limit).map(\.0)
    }

    /// Best chunks for `query`; `extraTerms` (e.g. from Apple Intelligence) widen the keyword side.
    func search(_ query: String, extraTerms: [String] = [], limit: Int = 20) throws -> [Hit] {
        let pool = max(limit * 4, 60)
        let fts = try ftsRanks(Self.terms(query + " " + extraTerms.joined(separator: " ")), limit: pool)
        let vec = vectorRanks(query, limit: pool)
        var score: [Int64: Double] = [:]
        for (r, id) in fts.enumerated() { score[id, default: 0] += 1.0 / Double(60 + r) }
        for (r, id) in vec.enumerated() { score[id, default: 0] += 1.0 / Double(60 + r) }
        let top = score.sorted { $0.value > $1.value }.prefix(limit)
        var hits: [Hit] = []
        for (id, s) in top {
            try store.query("""
                SELECT f.path, c.heading, c.text FROM chunks c JOIN files f ON f.id = c.file_id WHERE c.id = ?
                """, [id]) { row in
                hits.append(Hit(chunkId: id, path: row.string(0), heading: row.string(1), text: row.string(2), score: s))
            }
        }
        return hits
    }

    /// One line per file (its best chunk), for "where is…" style lookups.
    func searchFiles(_ query: String, extraTerms: [String] = [], limit: Int = 10) throws -> [Hit] {
        var seen = Set<String>()
        return try search(query, extraTerms: extraTerms, limit: limit * 5)
            .filter { seen.insert($0.path).inserted }
            .prefix(limit).map { $0 }
    }

    /// Mean centred vector of the chunks of files sitting directly in each folder.
    func folderProfiles() throws -> [String: [Float]] {
        var sums: [String: [Float]] = [:]
        let index = Dictionary(uniqueKeysWithValues: zip(ids, matrix))
        try store.query("SELECT c.id, f.path FROM chunks c JOIN files f ON f.id = c.file_id") { row in
            guard let v = index[row.int(0)] else { return }
            let folder = (row.string(1) as NSString).deletingLastPathComponent
            if sums[folder] == nil { sums[folder] = [Float](repeating: 0, count: v.count) }
            for i in v.indices { sums[folder]![i] += v[i] }
        }
        return sums.mapValues { var v = $0; Vec.normalize(&v); return v }
    }
}
